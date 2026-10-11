"""Expected-DTI-optimal emission: greedy add under the exact kernel metric,
then backward prune until the marginal gain is non-positive.

The competition score is the distance-weighted Tversky index (DTI) with
alpha = 0.2, beta = 0.8 and a 300 m (3 px) triangular kernel
(``gems64.metric``).  Writing ``T`` for kernel-weighted true positives,
``F`` for kernel-weighted false positives and ``K`` for truth mass,

    DTI = T / (alpha*(T + F) + beta*K)

because ``FN_w = K - T``.  Adding one unit-mass dot at ``x`` changes

    dT = sum_g w_g * max(0, k(x,g) - C_g)          (marginal truth credit)
    dF = 1 - kappa(x),  kappa(x) = 1 - prod_g (1 - w_g*k(x,g))

and, with ``D0 = alpha*(T+F) + beta*K``,

    dDTI > 0  <=>  dT*(D0 - alpha*T) > alpha*T*dF
             <=>  dT > alpha*T*dF / (alpha*F + beta*K) =: tau

which for a non-redundant dot (``dT == kappa``, ``dF = 1 - kappa``) reduces to
the published bar ``kappa > alpha*DTI`` (Lipton, Elkan & Narayanaswamy,
ECML-PKDD 2014 for alpha = beta = 0.5; see ``scripts/e1_theorem.py`` for the
numerical verification on synthetic rasters).

Because the 3-px kernel makes adjacent picks redundant, pixels are *not*
thresholded independently: the greedy keeps the running credit field ``C`` and
only accepts a pixel whose **marginal** credit clears ``tau``.
"""

from __future__ import annotations

import heapq

import numpy as np

from .metric import ALPHA, BETA, EPS, RADIUS_PX, kernel, offsets

OFF_DY, OFF_DX, OFF_K = offsets(RADIUS_PX)


# --------------------------------------------------------------------- kernels
def kernel_levels(radius: float = RADIUS_PX) -> list[float]:
    """Distinct positive kernel values, descending (6 at R = 3 px)."""
    return sorted({float(k) for k in OFF_K if k > 0}, reverse=True)


LEVELS = kernel_levels()


def expected_self_credit_from(logp_ge, levels=LEVELS):
    """Turn per-level log-probabilities into ``E[max_g k(x,g) B_g]``.

    ``E[max] = sum_l (k_l - k_{l+1}) * P(max >= k_l)`` and, because the truth
    indicators are independent Bernoulli,
    ``P(max >= k_l) = 1 - prod_{g: k(x,g) >= k_l} (1 - w_g)``.  ``logp_ge[l]``
    holds ``sum_g log(1 - w_g)`` restricted to that level's offsets.
    """
    out = 0.0
    for li, lv in enumerate(levels):
        nxt = levels[li + 1] if li + 1 < len(levels) else 0.0
        out = out + (lv - nxt) * (1.0 - np.exp(logp_ge[li]))
    return out


def kappa_field(w: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    """Exact expected self-credit ``E[max_g k(x,g) B_g]`` of a unit dot at ``x``
    under an independent-Bernoulli truth with weights ``w`` (``B_g ~ w_g``).

    The false-positive term of the metric is ``1 - max_g k(x,g)``, so the
    expectation needs the *max*, not the "at least one" product
    ``1 - prod(1 - w_g k_g)`` -- that product over-states the credit whenever
    two truth pixels sit inside the kernel (caught by
    ``tests/test_gems64.py::test_expected_dti_matches_official_metric``).
    """
    w = np.asarray(w, np.float64)
    logp = [np.zeros(w.shape, np.float64) for _ in LEVELS]
    for j, i, k in zip(OFF_DY, OFF_DX, OFF_K):
        ws = np.clip(np.roll(np.roll(w, -j, axis=0), -i, axis=1), 0.0, 1.0 - 1e-15)
        lg = np.log1p(-ws)
        for li, lv in enumerate(LEVELS):
            if k >= lv - 1e-12:
                logp[li] += lg
    return np.asarray(expected_self_credit_from(logp), np.float32)


def expected_dti(T, F, K, alpha: float = ALPHA, beta: float = BETA):
    """DTI from components; scalar in -> float, array in -> array (used by the
    vectorised backward-prune sweep)."""
    val = np.asarray(T, np.float64) / (alpha * (np.asarray(T, np.float64) +
                                               np.asarray(F, np.float64)) +
                                       beta * K + EPS)
    return float(val) if val.ndim == 0 else val


# ----------------------------------------------------------------- DTI greedy
class ExpectedDtiGreedy:
    """Lazy greedy on the exact expected-DTI gain + backward pruning.

    ``w`` is the calibrated probability field (soft truth weights).  ``cand``
    is an ``(N, 2)`` int array of candidate ``(row, col)`` pixels.
    """

    def __init__(self, w: np.ndarray, cand: np.ndarray, allowed=None,
                 alpha: float = ALPHA, beta: float = BETA, radius: float = RADIUS_PX):
        self.w = np.asarray(w, np.float64)
        self.H, self.W = self.w.shape
        self.cand = np.asarray(cand, np.int32)
        self.cy, self.cx = self.cand[:, 0], self.cand[:, 1]
        self.alpha, self.beta, self.radius = alpha, beta, radius
        logp = [np.zeros(self.cand.shape[0], np.float64) for _ in LEVELS]
        for j, i, k in zip(OFF_DY, OFF_DX, OFF_K):
            ny = np.clip(self.cy + j, 0, self.H - 1)
            nx = np.clip(self.cx + i, 0, self.W - 1)
            lg = np.log1p(-np.clip(self.w[ny, nx], 0.0, 1.0 - 1e-15))
            for li, lv in enumerate(LEVELS):
                if k >= lv - 1e-12:
                    logp[li] += lg
        self.kappa = np.asarray(expected_self_credit_from(logp), np.float64)
        self.dF = 1.0 - self.kappa
        self.K = float(self.w.sum())
        self.C = np.zeros(self.w.shape, np.float32)       # running credit per pixel
        self.T = 0.0
        self.F = 0.0
        self.placed: list[int] = []
        self.idx_of = np.full(self.w.shape, -1, np.int32)
        self.idx_of[self.cy, self.cx] = np.arange(self.cand.shape[0], dtype=np.int32)
        self.allowed = allowed

    # -- marginal truth credit ------------------------------------------------
    def dT_single(self, i: int) -> float:
        y, x = int(self.cy[i]), int(self.cx[i])
        tot = 0.0
        for j, o, k in zip(OFF_DY, OFF_DX, OFF_K):
            ny, nx = y + int(j), x + int(o)
            if 0 <= ny < self.H and 0 <= nx < self.W:
                gap = k - float(self.C[ny, nx])
                if gap > 0.0:
                    tot += self.w[ny, nx] * gap
        return tot

    def dT_batch(self, idx: np.ndarray) -> np.ndarray:
        cy, cx = self.cy[idx], self.cx[idx]
        out = np.zeros(idx.size, np.float64)
        for j, o, k in zip(OFF_DY, OFF_DX, OFF_K):
            ny = np.clip(cy + j, 0, self.H - 1)
            nx = np.clip(cx + o, 0, self.W - 1)
            gap = np.maximum(k - self.C[ny, nx].astype(np.float64), 0.0)
            out += self.w[ny, nx] * gap
        return out

    # -- accept test ----------------------------------------------------------
    def tau(self) -> float:
        return self.alpha * self.T * 1.0 / (self.alpha * self.F + self.beta * self.K + EPS)

    def gain(self, dT: np.ndarray, dF: np.ndarray) -> np.ndarray:
        D0 = self.alpha * (self.T + self.F) + self.beta * self.K + EPS
        D1 = D0 + self.alpha * (dT + dF)
        return (self.T + dT) / D1 - self.T / D0

    def _place(self, i: int) -> None:
        y, x = int(self.cy[i]), int(self.cx[i])
        dT = 0.0
        for j, o, k in zip(OFF_DY, OFF_DX, OFF_K):
            ny, nx = y + int(j), x + int(o)
            if 0 <= ny < self.H and 0 <= nx < self.W and k > self.C[ny, nx]:
                dT += self.w[ny, nx] * (k - float(self.C[ny, nx]))
                self.C[ny, nx] = k
        self.T += dT
        self.F += float(self.dF[i])
        self.placed.append(i)

    def _unplace(self, i: int) -> None:
        """Remove dot ``i`` and rebuild the credit field from the remaining dots
        in its 2*radius neighbourhood (exact; used by the backward prune)."""
        self.placed = [q for q in self.placed if q != i]
        self.C[:] = 0.0
        self.T = 0.0
        self.F = 0.0
        for q in self.placed:
            self._place(q)

    # -- main loop ------------------------------------------------------------
    def run(self, max_dots: int = 200_000, min_gain: float = 0.0,
            prune: bool = True, prune_passes: int = 6, verbose: bool = False):
        gains = self.gain(self.dT_batch(np.arange(self.cand.shape[0])), self.dF)
        heap = [(-float(g), int(i)) for i, g in enumerate(gains) if g > 0]
        heapq.heapify(heap)
        dirty = np.zeros(self.cand.shape[0], bool)
        placed_flag = np.zeros(self.cand.shape[0], bool)
        while heap and len(self.placed) < max_dots:
            _, i = heapq.heappop(heap)
            if placed_flag[i]:
                continue
            if dirty[i]:
                g = float(self.gain(np.array([self.dT_single(i)]),
                                    np.array([self.dF[i]]))[0])
                dirty[i] = False
                if g > 0:
                    heapq.heappush(heap, (-g, i))
                continue
            dT = self.dT_single(i)
            thr = self.tau() * float(self.dF[i])
            if dT <= thr:
                continue
            self._place(i)
            placed_flag[i] = True
            # any candidate within the kernel radius now has stale credit
            y, x = int(self.cy[i]), int(self.cx[i])
            r = int(np.ceil(self.radius))
            y0, y1 = max(0, y - r), min(self.H, y + r + 1)
            x0, x1 = max(0, x - r), min(self.W, x + r + 1)
            blk = self.idx_of[y0:y1, x0:x1]
            hit = blk[blk >= 0]
            dirty[hit] = True
        if prune:
            self.backward_prune(passes=prune_passes, verbose=verbose)
        return self.result()

    # -- backward prune -------------------------------------------------------
    def top2_credit(self) -> tuple[np.ndarray, np.ndarray]:
        """Best and second-best kernel credit at every pixel from placed dots."""
        D = np.zeros(self.w.shape, np.float32)
        if self.placed:
            D[self.cy[self.placed], self.cx[self.placed]] = 1.0
        b1 = np.zeros(self.w.shape, np.float64)
        b2 = np.zeros(self.w.shape, np.float64)
        for j, o, k in zip(OFF_DY, OFF_DX, OFF_K):
            a = np.roll(np.roll(D, -j, axis=0), -o, axis=1).astype(np.float64) * k
            b2 = np.maximum(b2, np.minimum(b1, a))
            b1 = np.maximum(b1, a)
        return b1, b2

    def backward_prune(self, passes: int = 6, verbose: bool = False) -> int:
        removed_total = 0
        for _ in range(passes):
            if not self.placed:
                break
            b1, b2 = self.top2_credit()
            pl = np.array(self.placed, np.int32)
            cy, cx = self.cy[pl], self.cx[pl]
            dT = np.zeros(pl.size, np.float64)
            for j, o, k in zip(OFF_DY, OFF_DX, OFF_K):
                ny = np.clip(cy + j, 0, self.H - 1)
                nx = np.clip(cx + o, 0, self.W - 1)
                dT += self.w[ny, nx] * np.maximum(k - b2[ny, nx], 0.0)
            dF = self.dF[pl]
            base = expected_dti(self.T, self.F, self.K, self.alpha, self.beta)
            newT = self.T - dT
            newF = self.F - dF
            new = expected_dti(newT, newF, self.K, self.alpha, self.beta)
            better = new > base + 1e-15
            if not better.any():
                break
            # remove best-first; the stale dT under-estimates a surviving dot's
            # unique credit, so every accepted removal is conservative.
            order = np.argsort(-(new - base))
            dropped = set()
            removed = 0
            for q in order:
                if not better[q]:
                    continue
                dTi = float(dT[q])
                base2 = expected_dti(self.T, self.F, self.K, self.alpha, self.beta)
                cand = expected_dti(self.T - dTi, self.F - float(dF[q]), self.K,
                                    self.alpha, self.beta)
                if cand > base2 + 1e-15:
                    self.T -= dTi
                    self.F -= float(dF[q])
                    dropped.add(int(pl[q]))
                    removed += 1
            if removed == 0:
                break
            keep = [i for i in self.placed if i not in dropped]
            self.placed = []
            self.C[:] = 0.0
            self.T = 0.0
            self.F = 0.0
            for q in keep:
                self._place(q)
            removed_total += removed
            if verbose:
                print(f"  prune pass removed {removed}, DTI="
                      f"{expected_dti(self.T, self.F, self.K):.6f}")
        return removed_total

    # -- output ---------------------------------------------------------------
    def mask(self) -> np.ndarray:
        m = np.zeros(self.w.shape, bool)
        if self.placed:
            m[self.cy[self.placed], self.cx[self.placed]] = True
        return m

    def result(self) -> dict:
        return dict(n_dots=len(self.placed), T=float(self.T), F=float(self.F),
                    K=float(self.K),
                    expected_dti=expected_dti(self.T, self.F, self.K,
                                              self.alpha, self.beta),
                    mean_kappa=float(self.kappa[self.placed].mean()) if self.placed else 0.0)


# ------------------------------------------------------------------- baselines
def nms_topk(p: np.ndarray, cand: np.ndarray, sep_px: float, mass: int) -> np.ndarray:
    """Incumbent heuristic: rank by ``p`` and keep a pixel only if no already
    kept pixel lies within ``sep_px`` (the 'dotted spacing' family)."""
    order = np.argsort(-p[cand[:, 0], cand[:, 1]], kind="stable")
    out = np.zeros(p.shape, bool)
    Hh, Ww = p.shape
    r = int(np.ceil(sep_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disc = (yy ** 2 + xx ** 2) <= sep_px ** 2 + 1e-9
    taken = np.zeros((Hh + 2 * r + 1, Ww + 2 * r + 1), bool)
    kept = 0
    for q in order:
        y, x = int(cand[q, 0]), int(cand[q, 1])
        if taken[y + r, x + r]:
            continue
        out[y, x] = True
        taken[y:y + 2 * r + 1, x:x + 2 * r + 1] |= disc
        kept += 1
        if kept >= mass:
            break
    return out


class MaxCoverGreedy:
    """MCLP: lazy greedy that maximises kernel-weighted truth credit ``T``
    alone, subject to a mass budget (no false-positive term)."""

    def __init__(self, w: np.ndarray, cand: np.ndarray, radius: float = RADIUS_PX):
        self.g = ExpectedDtiGreedy(w, cand, radius=radius)

    def run(self, mass: int) -> dict:
        g = self.g
        gains = g.dT_batch(np.arange(g.cand.shape[0]))
        heap = [(-float(v), int(i)) for i, v in enumerate(gains) if v > 0]
        heapq.heapify(heap)
        dirty = np.zeros(g.cand.shape[0], bool)
        while heap and len(g.placed) < mass:
            _, i = heapq.heappop(heap)
            if i in g.placed:
                continue
            if dirty[i]:
                v = g.dT_single(i)
                dirty[i] = False
                if v > 0:
                    heapq.heappush(heap, (-v, i))
                continue
            if g.dT_single(i) <= 0:
                continue
            g._place(i)
            y, x = int(g.cy[i]), int(g.cx[i])
            r = int(np.ceil(g.radius))
            blk = g.idx_of[max(0, y - r):min(g.H, y + r + 1),
                           max(0, x - r):min(g.W, x + r + 1)]
            dirty[blk[blk >= 0]] = True
        return dict(n_dots=len(g.placed), T=float(g.T), F=float(g.F), K=float(g.K),
                    expected_dti=expected_dti(g.T, g.F, g.K),
                    mask=g.mask())
