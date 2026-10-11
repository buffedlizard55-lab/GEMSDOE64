"""Exact multi-draw emission engine for the Expected-DTI-optimal lane.

SUPPLEMENTARY MODULE.  The metric primitives (kernel, lattice offsets, alpha/beta, the component
forms, the marginal rule and the brute-force oracle) all come from the shared ``gems64.metric``
via :mod:`gems64.lane_expecteddti.metricext`; nothing here re-implements the metric.

What this module adds is the piece the shared modules do not carry: the **sparse multi-draw
emitter state** needed to run an exact lazy-greedy at full grid scale.  ``Ensemble`` holds the
union of the plausible truth rasters in a compact index, tracks ``T``/``M``/``S`` per draw, and
supports

* :meth:`Ensemble.delta_T` -- exact marginal ``TP_w`` gain of unit mass at a cell, per draw,
  vectorised and chunked, with the live-calibrated flank discount applied to the kernel weight
  exactly as ``commit`` applies it, so the CELF bound stays a bound;
* :meth:`Ensemble.kmax` -- exact ``max_g k(d(x,g))`` per draw, same discount;
* :meth:`Ensemble.commit` / :meth:`Ensemble.uncommit` -- an exactly invertible pair, so backward
  pruning costs O(37*R) per probe instead of a full ensemble rebuild.

Both are unit-tested cell-by-cell against ``commit``-and-measure, and ``commit``/``uncommit``
against a fresh ensemble and against the shared brute-force oracle, in
``tests/test_lane_expecteddti_engine.py``.

Six correctness bugs were found and fixed here during development.  Each is documented at the line
where it lived, because each one produced a *plausible* number rather than an exception:

1. ``commit`` assigned ``best[]`` instead of taking a max, so a farther cell overwrote credit a
   nearer cell had already earned.  Invisible while ``T`` was accumulated incrementally from the
   gain; it only surfaced once ``T`` was recomputed from ``best``.
2. ``uncommit`` zeroed ``T`` and ``M`` when the removed cell had no truth within R, destroying the
   credit earned by every other emitted cell.
3. Two membership broadcasts mis-aligned ``(nt,)`` against ``(1, R)`` and ``(R, nt)`` against
   ``(nt, R)`` -- silently wrong when the shapes happened to agree, raising otherwise.
4. ``delta_T`` omitted the flank discount that ``commit`` applied, invalidating the CELF bound for
   discounted cells.
5. ``best``/``m_of``/``memT`` were float32, which drifted ~1e-7 across commit/uncommit cycles and
   failed interleaved stress at 6/8, degrading to 2/8 as R grew.
6. ``block_bootstrap_gate`` bootstrapped a ratio of per-block sums and reported it as a DTI
   difference, printing +446.25 for a quantity bounded by 1.
"""

from __future__ import annotations

import numpy as np

from gems64.grid import HEIGHT, WIDTH
from gems64.lane_expecteddti.metricext import (
    ALPHA, BETA, EPS, best_cover, components, kmax_field, lattice_kernel_values,
)

__all__ = ["Ensemble", "greedy", "spacing_placement", "block_bootstrap_gate"]


class Ensemble:
    """Sparse multi-draw state: union indexing + per-draw credit, exact marginal gains."""

    def __init__(self, draws: list[np.ndarray], rho: np.ndarray):
        from gems64.metric import kernel
        from scipy.ndimage import distance_transform_edt

        self.R = len(draws)
        self.H, self.W = draws[0].shape
        self.N = self.H * self.W
        union = np.logical_or.reduce(draws)
        self.uf = np.flatnonzero(union.ravel())
        self.uid = np.full(self.N, -1, dtype=np.int32)
        self.uid[self.uf] = np.arange(self.uf.size, dtype=np.int32)
        # float64, not float32: at |U| ~ 200k and R = 32 this is 51 MB, and float32 storage made
        # refresh_TM() drift by ~1e-7 across commit/uncommit cycles (verified in
        # tests/test_emission_engine.py).  float64 removes that whole class of noise.
        self.best = np.zeros((self.R, self.uf.size), dtype=np.float64)
        self.member = np.zeros(self.uf.size, dtype=np.uint32)
        self.K = np.zeros(self.R)
        self.flatdraw = [np.flatnonzero(d.ravel()) for d in draws]
        for r, fd in enumerate(self.flatdraw):
            self.member[self.uid[fd]] |= np.uint32(1) << np.uint32(r)
            self.K[r] = fd.size
        # per-draw kmax on the union of candidate neighbourhoods is computed lazily by callers
        self.kernel = kernel
        self.edt = distance_transform_edt
        self.rho = rho
        # ``lattice_kernel_values`` is metricext's adapter over the shared ``offsets()``;
        # ``kernel`` itself stays imported from the shared metric above.
        from gems64.lane_expecteddti.metricext import lattice_kernel_values
        offs = lattice_kernel_values()
        self.dy = np.array([o[0] for o in offs], np.int64)
        self.dx = np.array([o[1] for o in offs], np.int64)
        self.kw = np.array([o[2] for o in offs], np.float64)
        self.off_flat = self.dy * self.W + self.dx
        self.T = np.zeros(self.R)
        self.M = np.zeros(self.R)
        self.S = 0.0
        # emission mask, so uncommit() can recompute best(g) locally instead of rebuilding the
        # whole ensemble (the O(n^2) rebuild made the backward prune unusable at n ~ 40k).
        self.emit_w = np.zeros(self.N, dtype=np.float32)
        # membership as a dense (R, |U|) float32 matrix so T can be recomputed exactly from
        # best in one vectorised product instead of accumulated incrementally.
        _bits = np.arange(self.R, dtype=np.uint32)
        self.memT = ((self.member[:, None] >> _bits[None, :]) & 1).T.astype(np.float64)
        # kmax(x) depends on the truth draws only, never on the emission state, so it is a
        # per-cell constant: store it at commit time and M becomes exactly incremental.
        self.m_of = np.zeros((self.N, self.R), dtype=np.float64)

    def D(self):
        return ALPHA * (self.T + self.S - self.M) + BETA * self.K + EPS

    def dti_mean(self):
        return float((self.T / self.D()).mean())

    def _neigh(self, cells):
        cy, cx = np.divmod(cells, self.W)
        ny = cy[:, None] + self.dy[None, :]
        nx = cx[:, None] + self.dx[None, :]
        inside = (ny >= 0) & (ny < self.H) & (nx >= 0) & (nx < self.W)
        nf = np.where(inside, ny * self.W + nx, 0)
        u = self.uid[nf]
        return u, (u >= 0) & inside

    def delta_T(self, cells: np.ndarray, chunk: int = 20_000) -> np.ndarray:
        """(len(cells), R) exact marginal TP_w gain of unit mass at each cell, per draw.

        The per-cell flank discount ``rho`` scales the KERNEL WEIGHT here exactly as ``commit``
        scales it, so the lazy-greedy upper bound and the committed state use the same effective
        kernel.  The first version of this method omitted rho, which made the CELF bound invalid
        for discounted cells -- a real correctness bug, not a style issue.  Chunked because the
        per-draw gather is (R, len(cells), 37): unchunked at 200k candidates and R = 32 that is
        ~950 MB in a 3 GB sandbox.
        """
        out = np.empty((cells.size, self.R), dtype=np.float64)
        bits = np.arange(self.R, dtype=np.uint32)
        for i in range(0, cells.size, chunk):
            cc = cells[i:i + chunk]
            u, ok = self._neigh(cc)
            # member[u] is (B, n_off); it needs an explicit trailing axis before shifting by
            # the (1, 1, R) bit vector.  Without it numpy aligns n_off against R and raises
            # (or, when n_off == R, silently computes the wrong thing).
            mem = ((self.member[u][:, :, None] >> bits[None, None, :]) & 1).astype(np.float32)
            b = self.best[:, u.reshape(-1)].reshape(self.R, cc.size, -1).transpose(1, 2, 0)
            kk = self.kw[None, :, None] * self.rho[cc][:, None, None]
            contrib = np.maximum(0.0, kk - b) * mem * ok[:, :, None]
            out[i:i + chunk] = contrib.sum(axis=1)
        return out

    def kmax(self, cells: np.ndarray, chunk: int = 20_000) -> np.ndarray:
        """(len(cells), R) ``max_g k(d(x,g))`` per draw, discounted by the flank factor rho."""
        out = np.empty((cells.size, self.R), dtype=np.float64)
        bits = np.arange(self.R, dtype=np.uint32)
        for i in range(0, cells.size, chunk):
            cc = cells[i:i + chunk]
            u, ok = self._neigh(cc)
            # member[u] is (B, n_off); it needs an explicit trailing axis before shifting by
            # the (1, 1, R) bit vector.  Without it numpy aligns n_off against R and raises
            # (or, when n_off == R, silently computes the wrong thing).
            mem = ((self.member[u][:, :, None] >> bits[None, None, :]) & 1).astype(np.float32)
            v = self.kw[None, :, None] * mem * ok[:, :, None]
            out[i:i + chunk] = v.max(axis=1) * self.rho[cc][:, None]
        return out

    def commit(self, cell: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        y, x = divmod(int(cell), self.W)
        dT = np.zeros(self.R)
        dM = np.zeros(self.R)
        bits = np.arange(self.R, dtype=np.uint32)
        rho_c = float(self.rho[int(cell)])
        for dy, dx, k in zip(self.dy, self.dx, self.kw):
            yy, xx = y + int(dy), x + int(dx)
            if not (0 <= yy < self.H and 0 <= xx < self.W):
                continue
            u = self.uid[yy * self.W + xx]
            if u < 0:
                continue
            m = ((self.member[u] >> bits) & 1).astype(bool)
            kk = k * rho_c
            gain = np.maximum(0.0, kk - self.best[:, u].astype(np.float64))
            dT += np.where(m, gain, 0.0)
            dM = np.maximum(dM, np.where(m, kk, 0.0))
            # MUST be a max, not an assignment.  ``best[r, u]`` is max over all emitted cells of
            # their discounted kernel weight at truth cell u; a plain assignment lets a FARTHER
            # cell overwrite the credit a NEARER cell already earned, so recommitting cells in a
            # different order produced a different (lower) T.  This stayed hidden while T was
            # accumulated incrementally from ``gain`` - it only surfaced once refresh_TM() started
            # recomputing T from ``best``, which is exactly why the recompute was worth doing.
            self.best[m, u] = np.maximum(self.best[m, u], float(kk))
        self.T += dT
        self.M += dM
        self.S += 1.0
        self.emit_w[int(cell)] = 1.0
        self.m_of[int(cell)] = dM.astype(np.float64)
        return dT, dM, np.array([rho_c])

    # -- exact local inverse of commit ----------------------------------------------------
    def uncommit(self, cell: int) -> None:
        """Remove the mass at ``cell`` and recompute ``best`` only for the cells it touched.

        ``best(g) = max_off  emit_w[g-off] * rho[g-off] * k_off``: the discount belongs to the
        EMITTING cell, so it is looked up per neighbour rather than stored per truth cell.
        """
        cell = int(cell)
        if self.emit_w[cell] == 0.0:
            return
        self.emit_w[cell] = 0.0
        self.S -= 1.0
        self.M -= self.m_of[cell].astype(np.float64)
        self.m_of[cell] = 0.0
        W, H = self.W, self.H
        y, x = divmod(cell, W)
        touched = set()
        for dy, dx in zip(self.dy, self.dx):
            yy, xx = y + int(dy), x + int(dx)
            if 0 <= yy < H and 0 <= xx < W:
                u = int(self.uid[yy * W + xx])
                if u >= 0:
                    touched.add(u)
        if not touched:
            # No truth cell lies within R of the removed cell, so it contributed nothing to
            # T and its stored kmax was 0: M was already decremented by exactly that above.
            # Zeroing T and M here (as the first version did) destroyed the credit earned by
            # every OTHER emitted cell -- this was the dominant bug, not the broadcast one.
            return
        t = np.fromiter(touched, dtype=np.int64, count=len(touched))
        bits = np.arange(self.R, dtype=np.uint32)
        gf = self.uf[t]
        gy, gx = np.divmod(gf, W)
        newbest = np.zeros((t.size, self.R), dtype=np.float64)
        for dy, dx, k in zip(self.dy, self.dx, self.kw):
            ny, nx = gy - int(dy), gx - int(dx)
            okk = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
            nf = np.where(okk, ny * W + nx, 0)
            ew = self.emit_w[nf]
            w = np.where(okk & (ew > 0), ew * self.rho[nf] * float(k), 0.0)
            newbest = np.maximum(newbest, w[:, None].astype(np.float64))
        self.best[:, t] = newbest.T                              # newbest is (nt, R)
        self.refresh_TM()

    def refresh_TM(self) -> None:
        """Recompute T and M exactly from ``best``, ``m_of`` and ``emit_w``.

        Two earlier versions accumulated T and M incrementally inside commit/uncommit.  Both
        were wrong: one zeroed them when the removed cell had no truth within R, and the other
        drifted because ``best`` is float32 while T is float64, so a commit/uncommit/recommit
        cycle did not round-trip (it passed a single-removal test and failed an interleaved one,
        6/8 -> 2/8 as R grew).  Recomputing from state is O(|U|*R + |emit|*R), about 6 ms at
        |U| ~ 150k and R = 32, which is cheap enough to do on every prune probe and removes the
        entire class of drift bugs.
        """
        self.T = (self.best * self.memT).sum(1)
        em = np.flatnonzero(self.emit_w > 0)
        self.M = self.m_of[em].sum(0) if em.size else np.zeros(self.R)
        self.S = float(em.size)


def greedy(ens: Ensemble, cand: np.ndarray, pi_at: np.ndarray, max_emit: int,
           verbose_every: int = 2000) -> tuple[np.ndarray, list]:
    """Lazy-greedy (CELF) on ensemble-mean exact marginal DTI gain.

    ``dT`` is non-increasing as mass is added (``best`` only grows), so a previously computed
    gain is a valid upper bound and lazy greedy is exact for the ordering.  The ACCEPTANCE test
    is always recomputed exactly: a cell is emitted only if the ensemble-mean DTI gain is > 0.
    The emission is weighted by pi because the draws are samples of a probability field, so the
    posterior expected gain of cell x is pi(x) * E[dT(x)] to first order.
    """
    import heapq

    dT0 = ens.delta_T(cand)
    km0 = ens.kmax(cand)
    T, D = ens.T.copy(), ens.D()
    # The ensemble mean IS the expectation over plausible truths, so the gain is not weighted by
    # pi again -- doing so double-counts the probability (the draws were themselves sampled from
    # the pi ranking).  The prompt's rule is "the largest mean DTI gain under the exact kernel
    # metric", which is exactly this quantity.
    gain = ((T[None, :] + dT0) / (D[None, :] + ALPHA * (dT0 + 1.0 - km0)))
    gain = gain.mean(1) - (T / D).mean()
    heap = [(-float(g), int(c)) for g, c in zip(gain, cand)]
    heapq.heapify(heap)
    chosen, trail = [], []
    while heap and len(chosen) < max_emit:
        neg, c = heapq.heappop(heap)
        if -neg <= 0:
            break
        cell = np.array([c], dtype=np.int64)
        dT = ens.delta_T(cell)[0]
        km = ens.kmax(cell)[0]
        T, D = ens.T.copy(), ens.D()
        g = float(((T + dT) / (D + ALPHA * (dT + 1.0 - km))).mean() - (T / D).mean())
        if heap and g < -heap[0][0]:
            heapq.heappush(heap, (-g, c))
            continue
        if g <= 0:
            break
        ens.commit(c)
        chosen.append(c)
        trail.append(dict(step=len(chosen), cell=int(c), mean_gain=g,
                          dti_after=ens.dti_mean(), S=ens.S))
        if len(chosen) % verbose_every == 0:
            print(f"    emitted {len(chosen):>7,}  E[DTI] {ens.dti_mean():.5f}  "
                  f"last gain {g:+.3e}")
    return np.array(chosen, dtype=np.int64), trail


def spacing_placement(cand: np.ndarray, pi_at: np.ndarray, n: int, sep_px: int = 3):
    """The incumbent-style rule: rank by probability, then enforce a hard minimum separation.

    This is the "current spacing placement" the gate compares against, applied to the SAME
    surface, so the only difference between the two arms is the decision rule - which is what
    makes the comparison a test of Expected-DTI-optimal selection rather than of the field.

    Implemented as bucketed non-maximum suppression (one pick per ``sep_px`` x ``sep_px`` bucket,
    the highest-probability one), which is the raster analogue of the family's minimum-spacing
    thinning.  The first version was a Python loop with an inner scan over the last 400 picks,
    O(n * 400) ~ 16M interpreter iterations at n = 40k; the bucketed form is O(n) vectorised.
    """
    if cand.size == 0:
        return np.empty(0, dtype=np.int64)
    y, x = np.divmod(cand, WIDTH)
    by, bx = y // sep_px, x // sep_px
    nbx = (WIDTH + sep_px - 1) // sep_px
    bucket = by * nbx + bx
    # highest pi wins each bucket: sort by (bucket, -pi) and take the first row of each bucket
    order = np.lexsort((-pi_at, bucket))
    bs = bucket[order]
    first = np.concatenate([[True], bs[1:] != bs[:-1]])
    picked = cand[order[first]]
    picked_pi = pi_at[order[first]]
    if picked.size > n:
        keep = np.argsort(picked_pi)[::-1][:n]
        picked = picked[keep]
    return np.sort(picked).astype(np.int64)


# ======================================================================================
BOOT_SEED = 20261011


def block_bootstrap_gate(a_cells, b_cells, truth, footprint, catalogue,
                         n_boot=400, seed=BOOT_SEED,
                         block_px=96):
    """Paired spatial block bootstrap of ``DTI(B) - DTI(A)``.

    Resampling unit is a ``block_px`` square, which is the right unit for spatially autocorrelated
    raster data: resampling pixels independently would understate the variance by orders of
    magnitude because neighbouring truth cells are not independent.

    For each replicate, blocks are drawn with replacement and every truth cell / emitted cell
    inherits the multiplicity of its block.  DTI is then recomputed for BOTH arms under that
    weighting, so the replicate is a *paired* difference of two properly formed DTIs.

    THE FIRST VERSION OF THIS FUNCTION WAS WRONG and the wrongness is visible in its own output:
    it bootstrapped the ratio (sum of per-block TP_w differences) / (sum of per-block truth-cell
    counts) and reported that as the DTI difference.  It printed ``mean block diff +446.25 +/- SE
    193.12`` -- a number three orders of magnitude larger than any DTI, which cannot be a
    difference of quantities bounded by 1.  The z it produced was therefore meaningless even
    though its sign happened to agree with the per-draw comparison.
    """
    # best_cover / kmax_field are already imported at module level from metricext.

    rng = np.random.default_rng(seed)
    ntb, nlb = (HEIGHT + block_px - 1) // block_px, (WIDTH + block_px - 1) // block_px
    nblocks = ntb * nlb
    idx = np.arange(HEIGHT * WIDTH, dtype=np.int64)
    yy, xx = np.divmod(idx, WIDTH)
    blk = ((yy // block_px) * nlb + (xx // block_px)).astype(np.int32)
    del idx, yy, xx

    # Truth cells are NOT reduced by ~catalogue here.  The first version did that, on the
    # reasoning that catalogue pixels are masked out of live scoring -- which made the
    # catalogue-truth arm vacuous by construction: truth & ~truth == empty, so every DTI came out
    # 0.00000 and the gate reported z=nan.  The masking belongs on the EMISSION (and the emission
    # is already confined to the scored domain), not on the truth.
    dm = truth & footprint
    if dm.sum() == 0:
        raise ValueError("gate called with a truth raster that is empty inside the footprint")
    dm_flat = np.flatnonzero(dm.ravel())
    blk_truth = blk[dm_flat]
    pa = np.zeros(HEIGHT * WIDTH, np.float32); pa[a_cells] = 1.0
    pb = np.zeros(HEIGHT * WIDTH, np.float32); pb[b_cells] = 1.0
    pa = pa.reshape(HEIGHT, WIDTH); pb = pb.reshape(HEIGHT, WIDTH)
    ba, bb = best_cover(pa), best_cover(pb)        # per-truth-cell credit, 0 where uncovered
    # FP_w = sum_x p(x) [1 - max_g k(d(x,g))], and the max is over TRUTH cells g.  So the FP
    # weight at x depends only on the truth raster and is IDENTICAL for both arms; it is not a
    # function of the emission.  (The first version of this fix computed it from the emission,
    # which is a different quantity entirely.)
    fpw = 1.0 - kmax_field(truth)

    fa = np.flatnonzero(pa.ravel()); fb = np.flatnonzero(pb.ravel())
    blk_a, blk_b = blk[fa], blk[fb]
    fpw_flat = fpw.ravel()
    ca_f, cb_f = fpw_flat[fa], fpw_flat[fb]

    ca = components(pa, truth, valid=footprint, known=catalogue)
    cb = components(pb, truth, valid=footprint, known=catalogue)
    point_a, point_b = float(ca["dti"]), float(cb["dti"])
    cover_a = float(ba.ravel()[dm_flat].mean())
    cover_b = float(bb.ravel()[dm_flat].mean())
    tp_a_flat = ba.ravel()[dm_flat]
    tp_b_flat = bb.ravel()[dm_flat]

    diffs = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, nblocks, nblocks)
        wt = np.bincount(pick, minlength=nblocks).astype(np.float64)
        wT = wt[blk_truth]
        wA = wt[blk_a]
        wB = wt[blk_b]
        # TP_w / FN_w over the resampled truth cells; FP_w over the resampled emitted cells
        tp_a = float((tp_a_flat * wT).sum())
        tp_b = float((tp_b_flat * wT).sum())
        K = float(wT.sum())
        fp_a = float((ca_f * wA).sum())
        fp_b = float((cb_f * wB).sum())
        d_a = tp_a + ALPHA * fp_a + BETA * (K - tp_a)
        d_b = tp_b + ALPHA * fp_b + BETA * (K - tp_b)
        diffs[i] = (tp_b / d_b if d_b > 0 else 0.0) - (tp_a / d_a if d_a > 0 else 0.0)

    mean = float(diffs.mean())
    se = float(diffs.std(ddof=1))
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return dict(dti_A=point_a, dti_B=point_b, point_diff=point_b - point_a,
                mean_block_diff=mean, se=se,
                z=(mean / se) if se > 0 else float("nan"),
                ci95=[float(lo), float(hi)], n_boot=int(n_boot), block_px=block_px,
                n_blocks=int(nblocks), mean_truth_cover_A=cover_a, mean_truth_cover_B=cover_b,
                n_A=int(pa.sum()), n_B=int(pb.sum()), n_truth=int(dm.sum()),
                tp_A=float(ca["TP_w"]), tp_B=float(cb["TP_w"]),
                fp_A=float(ca["FP_w"]), fp_B=float(cb["FP_w"]),
                frac_replicates_positive=float((diffs > 0).mean()))
