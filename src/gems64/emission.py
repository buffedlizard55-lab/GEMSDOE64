"""Expected-DTI-optimal emission engine.

The decision rule
-----------------
Write ``T = TP_w``, ``S`` = emitted mass, ``M = sum_x p(x) kmax(x)``, ``K = |G|``,
``D = alpha*(T + S - M) + beta*K`` so that ``DTI = T/D`` (verified identity C3).

Adding one unit of mass at cell ``x`` changes exactly three quantities:

    dT(x) = sum_{g in G, d(x,g) <= R} max(0, k(d(x,g)) - best(g))
    dS    = 1
    dM(x) = kmax(x) = max_g k(d(x,g))          <- depends on G only, NOT on the current pick

where ``best(g) = max_y p(y) k(d(y,g))`` is the credit truth cell ``g`` already has.  Then

    dD(x)   = alpha * (dT(x) + 1 - kmax(x))
    gain(x) > 0  <=>  dT(x) * D  >  T * dD(x)
                 <=>  dT(x) * (1 - alpha*DTI)  >  alpha*DTI * (1 - kmax(x))          (RULE)

Two limits of (RULE), both checked numerically in ``scripts/verify_dti_optimal.py``:

* **Non-redundant pick** (``x`` is strictly the best cover of every truth cell in range, so
  ``dT = kmax = kappa``): (RULE) collapses to ``kappa > alpha*DTI`` — the marginal-inclusion
  bar of ``gems64.metric.marginal_bar`` and the Tversky generalisation of Lipton, Elkan &
  Narayanaswamy (ECML-PKDD 2014).
* **Fully redundant pick** (``dT = 0``): (RULE) gives ``0 > alpha*DTI*(1 - kmax) >= 0``, i.e.
  never emit.  This is the formal reason the 3-px kernel makes adjacent picks redundant and
  independent thresholding of a calibrated surface is the wrong decision rule: thresholding
  scores each cell as if ``dT = kmax``, ignoring that a neighbour may already hold the credit.

Monotonicity and lazy greedy
----------------------------
``dT(x)`` is non-increasing as mass is added (``best`` only grows), so the value computed at
any earlier state is a valid **upper bound** on the current value.  Lazy greedy (CELF,
Goyal et al. 2010) is therefore *exact*, not an approximation: pop the largest stale bound,
recompute it exactly, and accept only if it still dominates the heap head.

Backward pruning
----------------
After the forward pass, every accepted pick is re-costed: its marginal contribution is
recomputed with the pick *removed*.  Picks whose removal raises DTI are dropped, worst-first,
until no removal helps.  This is the "prune backward until marginal gain <= 0" step.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .metric import ALPHA, BETA, EPS, RADIUS_PX, best_cover, dti, kernel, lattice_kernel_values

_OFF = lattice_kernel_values()
DY = np.array([o[0] for o in _OFF], dtype=np.int64)
DX = np.array([o[1] for o in _OFF], dtype=np.int64)
KW = np.array([o[2] for o in _OFF], dtype=np.float64)


# ======================================================================================
# small-grid exact greedy (used by the synthetic verification and the holdout gate)
# ======================================================================================
def delta_tp_field(best: np.ndarray, gmask: np.ndarray) -> np.ndarray:
    """Exact ``dT(x)`` for unit mass added at every cell, given the current ``best`` field.

    ``dT(x) = sum_{offsets} 1[x+off in G] * max(0, k_off - best[x+off])``.
    """
    out = np.zeros(best.shape, dtype=np.float64)
    for dy, dx, k in zip(DY, DX, KW):
        # A(g) = 1[g in G] * max(0, k - best(g)); contribution to x = g - (dy,dx)
        A = np.where(gmask, np.maximum(0.0, k - best), 0.0)
        h, w = A.shape
        ys0, ys1 = max(0, -dy), min(h, h - dy)
        xs0, xs1 = max(0, -dx), min(w, w - dx)
        if ys0 >= ys1 or xs0 >= xs1:
            continue
        out[ys0:ys1, xs0:xs1] += A[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    return out


def greedy_exact(truth: np.ndarray, candidates: np.ndarray, budget: int,
                 p0: np.ndarray | None = None, alpha: float = ALPHA, beta: float = BETA,
                 stop_on_nonpositive: bool = True) -> tuple[np.ndarray, list[dict]]:
    """Exact greedy on the true DTI objective over a candidate mask.  Small grids only.

    Returns the emission raster and the per-step audit trail.
    """
    g = np.asarray(truth, bool)
    p = np.zeros(g.shape, dtype=np.float64) if p0 is None else p0.astype(np.float64).copy()
    best = best_cover(p)
    kmax = kernel(__import__("scipy.ndimage", fromlist=["distance_transform_edt"])
                  .distance_transform_edt(~g)) if g.any() else np.zeros(g.shape)
    T = float(best[g].sum())
    S = float(p.sum())
    M = float((p * kmax).sum())
    K = float(g.sum())
    D = alpha * (T + S - M) + beta * K + EPS
    elig = np.asarray(candidates, bool) & ~g & (p == 0)
    trail = []
    for _ in range(int(budget)):
        dTf = np.where(elig, delta_tp_field(best, g), -np.inf).ravel()
        j = int(np.argmax(dTf))
        if not np.isfinite(dTf[j]):
            break
        dTv = float(dTf[j])
        dMv = float(kmax.ravel()[j])
        dD = alpha * (dTv + 1.0 - dMv)
        cur = T / D
        new = (T + dTv) / (D + dD)
        if stop_on_nonpositive and new <= cur:
            break
        y, x = divmod(j, g.shape[1])
        p[y, x] = 1.0
        elig[y, x] = False
        for dy, dx, k in zip(DY, DX, KW):
            yy, xx = y + dy, x + dx
            if 0 <= yy < g.shape[0] and 0 <= xx < g.shape[1] and g[yy, xx] and k > best[yy, xx]:
                best[yy, xx] = k
        T += dTv
        S += 1.0
        M += dMv
        D += dD
        trail.append(dict(step=len(trail), y=int(y), x=int(x), dT=dTv, kmax=dMv,
                          dti_before=cur, dti_after=new, gain=new - cur))
    return p, trail


def backward_prune(truth: np.ndarray, p: np.ndarray, alpha: float = ALPHA, beta: float = BETA,
                   max_removed: int | None = None) -> tuple[np.ndarray, int]:
    """Drop picks whose removal raises DTI, worst-first, until no removal helps."""
    g = np.asarray(truth, bool)
    p = np.asarray(p, dtype=np.float64).copy()
    removed = 0
    while True:
        on = np.argwhere(p > 0)
        if on.size == 0:
            break
        base = dti(*_tf(p, g, alpha, beta))
        best_gain, best_idx = 0.0, None
        for i in range(len(on)):
            q = p.copy()
            q[on[i, 0], on[i, 1]] = 0.0
            gain = dti(*_tf(q, g, alpha, beta)) - base
            if gain > best_gain:
                best_gain, best_idx = gain, i
        if best_idx is None:
            break
        p[on[best_idx, 0], on[best_idx, 1]] = 0.0
        removed += 1
        if max_removed is not None and removed >= max_removed:
            break
    return p, removed


def _tf(p, g, alpha, beta):
    c_T = float(best_cover(p)[g].sum())
    from .metric import kmax_field

    km = kmax_field(g)
    S = float(p.sum())
    M = float((p * km).sum())
    K = float(g.sum())
    fp = S - M + 0.0  # T + S - M = TP + FP  (identity C3)
    fn = K - c_T
    return c_T, fp, fn


# ======================================================================================
# scalable multi-draw ensemble engine for the full 3730 x 3292 grid
# ======================================================================================
@dataclass
class TruthEnsemble:
    """``R`` plausible truth rasters, indexed through one shared union grid.

    Memory: ``uid`` int32 (H*W, 49 MB) + ``best`` float32 (R, |U|) + ``member`` uint32 (|U|).
    """

    height: int
    width: int
    uid: np.ndarray            # int32 flat, -1 outside the union of all draws
    best: np.ndarray           # float32 (R, |U|) credit already held by each truth cell
    member: np.ndarray         # uint32 (|U|) bitmask: bit r set if cell in draw r
    kmax_union: np.ndarray     # float32 (R, |U|) kernel weight of each truth cell to... (see below)
    R: int
    K: np.ndarray              # float64 (R,) |G_r|

    @classmethod
    def build(cls, draws: list[np.ndarray]) -> "TruthEnsemble":
        R = len(draws)
        if R > 32:
            raise ValueError("bitmask membership supports at most 32 draws")
        h, w = draws[0].shape
        union = np.zeros(h * w, bool)
        for d in draws:
            union |= np.asarray(d, bool).ravel()
        uid = np.full(h * w, -1, dtype=np.int32)
        idx = np.nonzero(union)[0]
        uid[idx] = np.arange(idx.size, dtype=np.int32)
        best = np.zeros((R, idx.size), dtype=np.float32)
        member = np.zeros(idx.size, dtype=np.uint32)
        K = np.zeros(R, dtype=np.float64)
        # position of each draw's truth cells inside the union numbering
        for r, d in enumerate(draws):
            fl = np.nonzero(np.asarray(d, bool).ravel())[0]
            member[uid[fl]] |= np.uint32(1) << np.uint32(r)
            K[r] = fl.size
        return cls(h, w, uid, best, member, None, R, K)

    # -- state -------------------------------------------------------------------
    def totals(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Per-draw (T, S, M, D) for the current emission state (S, M maintained by caller)."""
        T = (self.best * ((self.member >> np.arange(self.R, dtype=np.uint32)[None, :]) & 1)).sum(1)
        return T.astype(np.float64)

    def delta_T_batch(self, cells: np.ndarray, uid_of_cell: np.ndarray | None = None) -> np.ndarray:
        """``dT`` for a batch of candidate flat cells, per draw -> shape (len(cells), R)."""
        from scipy.ndimage import distance_transform_edt  # noqa: F401  (kept for API symmetry)

        B = cells.shape[0]
        W = self.width
        H = self.height
        cy, cx = np.divmod(cells, W)
        ny = cy[:, None] + DY[None, :]
        nx = cx[:, None] + DX[None, :]
        inside = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        nflat = np.where(inside, ny * W + nx, 0)
        u = self.uid[nflat]                       # (B, 37) int32
        valid = inside & (u >= 0)
        usafe = np.where(valid, u, 0)
        bits = np.arange(self.R, dtype=np.uint32)
        mem = ((self.member[usafe] >> bits[None, None, :]) & 1).astype(np.float32)  # (B,37,R)
        b = self.best[:, usafe.reshape(-1)].reshape(self.R, B, 37).transpose(1, 2, 0)  # (B,37,R)
        contrib = np.maximum(0.0, KW[None, :, None] - b) * mem * valid[:, :, None]
        return contrib.sum(axis=1).astype(np.float64)

    def commit(self, cell: int) -> np.ndarray:
        """Add unit mass at ``cell``; update ``best``; return the realised ``dT`` per draw."""
        W, H = self.width, self.height
        y, x = divmod(int(cell), W)
        dT = np.zeros(self.R, dtype=np.float64)
        bits = np.arange(self.R, dtype=np.uint32)
        for dy, dx, k in zip(DY, DX, KW):
            yy, xx = y + int(dy), x + int(dx)
            if not (0 <= yy < H and 0 <= xx < W):
                continue
            u = self.uid[yy * W + xx]
            if u < 0:
                continue
            m = ((self.member[u] >> bits) & 1).astype(bool)
            gain = np.maximum(0.0, k - self.best[:, u].astype(np.float64))
            dT += np.where(m, gain, 0.0)
            self.best[m, u] = np.float32(k)
        return dT

    def uncommit(self, cell: int, prev_best: np.ndarray) -> None:
        """Restore ``best`` for the neighbourhood of ``cell`` (used by backward pruning)."""
        W, H = self.width, self.height
        y, x = divmod(int(cell), W)
        bits = np.arange(self.R, dtype=np.uint32)
        for dy, dx, k in zip(DY, DX, KW):
            yy, xx = y + int(dy), x + int(dx)
            if not (0 <= yy < H and 0 <= xx < W):
                continue
            u = self.uid[yy * W + xx]
            if u < 0:
                continue
            m = ((self.member[u] >> bits) & 1).astype(bool)
            self.best[m, u] = prev_best[m]


def kmax_per_draw(draws: list[np.ndarray]) -> np.ndarray:
    """``kmax(x) = max_g k(d(x,g))`` for every draw, on the union support only.

    Returned as float32 (R, |U|) aligned to ``TruthEnsemble.uid`` numbering would need the
    union; here we return full grids because kmax is needed at *candidate* cells, which are
    not truth cells.  Callers with memory pressure should restrict to the candidate list.
    """
    from scipy.ndimage import distance_transform_edt

    out = np.empty((len(draws),) + draws[0].shape, dtype=np.float32)
    for r, d in enumerate(draws):
        d = np.asarray(d, bool)
        out[r] = kernel(distance_transform_edt(~d)) if d.any() else 0.0
    return out
