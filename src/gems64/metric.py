"""Distance-weighted Tversky Index (DTI) — the DOE GEMS Prize performance metric.

Official definition, competition problem description page 967
(https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric),
transcribed literally here and verified against an O(|G|x|P|) brute force in
``tests/test_metric.py`` (agreement <= 1e-9 on randomized soft and binary rasters):

    k(d)   = max(1 - d / R, 0),                      R = 300 m = 3 px at 100 m
    TP_w   = sum_{g in G} max_{x : d(x,g) <= R} p(x) * k(d(x,g))
    FP_w   = sum_{x : p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FN_w   = sum_{g in G} [1 - max_{x : d(x,g) <= R} p(x) * k(d(x,g))]
    DTI    = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps),   alpha = 0.2, beta = 0.8

Two identities make this tractable (both verified numerically in this repository):

1. ``FN_w = |G| - TP_w`` exactly, because the max-term inside FN_w is the same quantity that
   builds TP_w.  Hence, writing ``T = TP_w``, ``S = sum_x p(x)`` (emitted mass) and
   ``M = sum_x p(x) * max_g k(d(x,g))`` (mass that is best-covering some truth pixel),

       DTI = T / ( alpha*(T + S - M) + beta*|G| + eps )                    (*)

   since ``TP_w + FP_w = T + S - M``.

2. Differentiating (*) with respect to one added unit of mass whose realised kernel weight is
   ``k`` (so ``dT = k`` and, because the denominator rises by ``alpha*(dT + dS - dM) =
   alpha*(k + 1 - k) = alpha`` regardless of where the mass lands):

       dDTI > 0   <=>   k * D > alpha * T   <=>   k > alpha * DTI            (**)

   This is the **marginal inclusion rule**.  At DTI = 0.30 the bar is 0.06; at 0.2778 it is
   0.05556; at the 2026-10-04 leaderboard #1 of 0.3262 it is 0.06524.

   (**) is the Tversky-family generalisation of Lipton, Elkan & Narayanaswamy (ECML-PKDD 2014),
   "Accuracy of Outlier Detection: The F1-optimal threshold is half the optimal F1", where
   alpha = beta = 1/2 gives the bar ``0.5 * F1*``.  ``scripts/verify_dti_optimal.py`` checks
   (**) numerically on synthetic rasters before any real emission is built.

NOTE ON A FORMER BUG IN THE FAMILY (carried forward deliberately as a regression test):
the bar is ``alpha * DTI``, **not** ``alpha*DTI/(1 - alpha*DTI)``.  The latter was propagated
through earlier sessions as ``tau_live = 0.05485``; at DTI = 0.2708 it gives 0.05726 instead of
0.05416 and rejects the legitimate (2,2)-diagonal kernel weight ``1 - 2*sqrt(2)/3 = 0.05719``.
``tests/test_metric.py::test_marginal_bar_form`` pins the correct form by brute force.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA: float = 0.2
BETA: float = 0.8
RADIUS_M: float = 300.0
RADIUS_PX: float = RADIUS_M / 100.0  # 3.0
EPS: float = 1e-12


def kernel(d, radius: float = RADIUS_PX) -> np.ndarray:
    """Triangular kernel ``k(d) = max(1 - d/R, 0)``; ``d`` and ``R`` in pixels."""
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


# The distinct kernel weights reachable on the 100 m lattice within R = 3 px, sorted descending.
# Only these values can ever be a marginal gain, which is what makes the decision rule a
# small discrete search rather than a continuous one.
def lattice_kernel_values(radius: float = RADIUS_PX) -> list[tuple[int, int, float]]:
    r = int(np.ceil(radius))
    out = []
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            k = float(kernel(np.hypot(dy, dx), radius))
            if k > 0.0:
                out.append((dy, dx, k))
    out.sort(key=lambda t: -t[2])
    return out


_OFFSETS = lattice_kernel_values()


def _shift(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Shift ``arr`` by (dy, dx) with zero fill (exact: all shifted arrays here are >= 0)."""
    out = np.zeros_like(arr)
    h, w = arr.shape
    ys0, ys1 = max(0, dy), min(h, h + dy)
    xs0, xs1 = max(0, dx), min(w, w + dx)
    out[ys0:ys1, xs0:xs1] = arr[max(0, -dy):min(h, h - dy), max(0, -dx):min(w, w - dx)]
    return out


def best_cover(p: np.ndarray) -> np.ndarray:
    """``max_x p(x) k(d(x,g))`` evaluated at every cell ``g`` — the per-truth-cell credit field.

    This is a max-plus convolution of ``p`` with the kernel, computed exactly by 37 shifted
    maxima (offsets with k>0 inside R=3 px: a 7x7 box minus the corners).
    """
    best = np.zeros(p.shape, dtype=np.float64)
    for dy, dx, k in _OFFSETS:
        np.maximum(best, _shift(p, -dy, -dx) * k, out=best)
    return np.clip(best, 0.0, 1.0)


def kmax_field(truth: np.ndarray) -> np.ndarray:
    """``max_g k(d(x,g))`` at every cell ``x`` — the kernel weight of x toward nearest truth."""
    if not truth.any():
        return np.zeros(truth.shape, dtype=np.float64)
    return kernel(distance_transform_edt(~truth.astype(bool)))


def components(pred, truth, valid=None, known=None) -> dict:
    """Exact ``TP_w / FP_w / FN_w`` plus the algebra terms ``T, S, M, K``.

    ``known`` is the catalogue mask: those cells are excluded from scoring entirely (forum
    thread 11516), i.e. they are removed from both the prediction support and the truth set.
    """
    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(truth)
    if p.ndim != 2 or p.shape != t.shape:
        raise ValueError("prediction and truth must be equal-shaped 2-D grids")
    v = np.ones(p.shape, bool) if valid is None else np.asarray(valid, bool)
    kn = np.zeros(p.shape, bool) if known is None else np.asarray(known, bool)
    if v.shape != p.shape or kn.shape != p.shape:
        raise ValueError("mask grid mismatch")
    active = v & ~kn
    vals = p[active]
    if not np.isfinite(vals).all():
        raise ValueError("predictions inside the scored domain must be finite")
    if (vals < 0).any() or (vals > 1).any():
        raise ValueError("predictions inside the scored domain must be in [0, 1]")
    p = np.where(active & np.isfinite(p), p, 0.0)
    g = active & (t > 0)

    tp = float(best_cover(p)[g].sum())
    k_near = kmax_field(g)
    fp = float((p * (1.0 - k_near)).sum())
    n = int(g.sum())
    fn = float(n) - tp
    s = float(p.sum())
    m = float((p * k_near).sum())
    return {
        "TP_w": tp, "FP_w": fp, "FN_w": fn,
        "T": tp, "S": s, "M": m, "K": float(n), "n_truth": n,
        "dti": dti(tp, fp, fn),
        "credit_per_unit_mass": (tp / s) if s else 0.0,
        "coverage": (tp / n) if n else 0.0,
    }


def dti(tp: float, fp: float, fn: float, alpha: float = ALPHA, beta: float = BETA) -> float:
    """DTI from the three published components."""
    return float(tp / (tp + alpha * fp + beta * fn + EPS))


def dti_algebra(t: float, s: float, m: float, k: float,
                alpha: float = ALPHA, beta: float = BETA) -> float:
    """Closed form (*) ``T / (alpha*(T + S - M) + beta*K)`` — identical to :func:`dti`."""
    return float(t / (alpha * (t + s - m) + beta * k + EPS))


def score(pred, truth, valid=None, known=None) -> float:
    c = components(pred, truth, valid, known)
    return c["dti"]


def dti_binary(pred_bool, truth, valid=None, known=None) -> dict:
    """Fast exact DTI for binary predictions via two Euclidean distance transforms."""
    p = np.asarray(pred_bool, bool)
    t = np.asarray(truth, bool)
    v = np.ones(p.shape, bool) if valid is None else np.asarray(valid, bool)
    kn = np.zeros(p.shape, bool) if known is None else np.asarray(known, bool)
    active = v & ~kn
    pm = p & active
    g = t & active
    n = int(g.sum())
    if n == 0:
        return dict(TP_w=0.0, FP_w=float(pm.sum()), FN_w=0.0, n_truth=0, dti=0.0, coverage=0.0)
    if not pm.any():
        return dict(TP_w=0.0, FP_w=0.0, FN_w=float(n), n_truth=n, dti=0.0, coverage=0.0)
    tp = float(kernel(distance_transform_edt(~pm))[g].sum())
    fn = float(n) - tp
    fp = float((1.0 - kernel(distance_transform_edt(~g))[pm]).sum())
    return dict(TP_w=tp, FP_w=fp, FN_w=fn, n_truth=n,
                dti=dti(tp, fp, fn), coverage=tp / n)


def dti_bruteforce(pred, truth, alpha: float = ALPHA, beta: float = BETA,
                   radius: float = RADIUS_PX) -> dict:
    """Literal O(|G|x|P|) transcription of the published equations.  Unit-test oracle only."""
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, bool)
    gs = np.argwhere(truth)
    xs = np.argwhere(pred > 0)
    tp = fn = 0.0
    for g in gs:
        best = 0.0
        for x in xs:
            d = float(np.hypot(*(x - g)))
            if d <= radius:
                best = max(best, pred[tuple(x)] * max(1.0 - d / radius, 0.0))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for x in xs:
        kmax = 0.0
        for g in gs:
            kmax = max(kmax, max(1.0 - float(np.hypot(*(x - g))) / radius, 0.0))
        fp += pred[tuple(x)] * (1.0 - kmax)
    return dict(TP_w=tp, FP_w=fp, FN_w=fn, dti=tp / (tp + alpha * fp + beta * fn + EPS))


def marginal_bar(current_dti: float, alpha: float = ALPHA) -> float:
    """Minimum realised kernel weight ``k`` for an added unit of mass to raise DTI: ``alpha*DTI``.

    See (**) in the module docstring.  Derived, not tuned; verified by brute force in
    ``scripts/verify_dti_optimal.py``.
    """
    return alpha * current_dti


def expected_gain(kbar: np.ndarray, current_dti: float, alpha: float = ALPHA) -> np.ndarray:
    """First-order expected DTI gain of adding unit mass at each cell, given its mean credit.

    ``kbar`` is ``E[max_g k(d(x,g))]`` under the truth ensemble.  Positive exactly where the
    Expected-DTI-optimal rule says to emit.
    """
    return np.asarray(kbar, dtype=np.float64) - marginal_bar(current_dti, alpha)


def credit_audit(mask) -> dict:
    """Kernel-structure audit of an emission mask (needs no truth).

    ``redundancy_fraction`` is the share of emitted cells that have another emitted cell within
    the kernel support — those cells are largely wasted because ``max`` (not ``sum``) builds
    ``TP_w``.  This is why the 3-px kernel makes adjacent picks redundant and why independent
    thresholding of a calibrated surface is the wrong decision rule.
    """
    m = np.asarray(mask, dtype=np.float64)
    pos = m > 0
    n = int(pos.sum())
    if n == 0:
        return dict(n_emitted=0, total_mass=0.0, redundancy_fraction=0.0, mean_self_kernel=0.0)
    best = np.zeros(m.shape, dtype=np.float64)
    for dy, dx, k in _OFFSETS:
        if dy == 0 and dx == 0:
            continue
        np.maximum(best, _shift(m, -dy, -dx) * k, out=best)
    red = np.clip(best, 0.0, 1.0)
    return dict(
        n_emitted=n,
        total_mass=float(m.sum()),
        redundancy_fraction=float((red[pos] > 0).mean()),
        mean_self_kernel=float(red[pos].mean()),
    )
