"""Metric helpers for the Expected-DTI-optimal lane.

SUPPLEMENTARY MODULE over the shared ``gems64.metric`` -- see the import block below.  Nothing
here redefines the kernel, the lattice offsets, the metric constants, the brute-force oracle or
the marginal rule; those are imported.  What is added is the whole-grid field helpers and the
component record this lane's inversion and emission scripts need.

Original header follows.

Distance-weighted Tversky Index (DTI) — the DOE GEMS Prize performance metric.

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

# The kernel, its lattice offsets and the metric constants come from the SHARED ``gems64.metric``
# module.  This lane keeps no private copy of them; it adds only the full-field helpers the shared
# module does not expose (``best_cover`` as a whole-grid field, ``kmax_field``, the ``components``
# record carrying S/M/K alongside tp/fp/fn, the closed-form ``dti_algebra``, and ``credit_audit``)
# plus the exact multi-draw emitter state used at full grid scale.
from gems64.metric import (  # noqa: F401  (re-exported for this lane's scripts)
    ALPHA, BETA, EPS, RADIUS_PX, kernel, dti_binary, dti_bruteforce, dti_from_components,
    marginal_accept, marginal_inclusion_threshold, max_cover, offsets,
)

RADIUS_M: float = RADIUS_PX * 100.0

# ``dti`` and ``marginal_bar`` are this lane's names for the shared functions; aliasing rather
# than reimplementing keeps one source of truth.
dti = dti_from_components
marginal_bar = marginal_inclusion_threshold


# The distinct kernel weights reachable on the 100 m lattice within R = 3 px, sorted descending.
# Only these values can ever be a marginal gain, which is what makes the decision rule a
# small discrete search rather than a continuous one.
def lattice_kernel_values(radius: float = RADIUS_PX) -> list[tuple[int, int, float]]:
    """Adapter over the shared :func:`gems64.metric.offsets`, sorted by descending weight.

    The lattice enumeration itself is the shared module's; this only re-shapes it into the list of
    ``(dy, dx, k)`` triples this lane's field helpers iterate over, highest weight first.
    """
    dy, dx, kw = offsets(radius)
    out = [(int(a), int(b), float(c)) for a, b, c in zip(dy, dx, kw)]
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


def dti_algebra(t: float, s: float, m: float, k: float,
                alpha: float = ALPHA, beta: float = BETA) -> float:
    """Closed form (*) ``T / (alpha*(T + S - M) + beta*K)`` -- identical to :func:`dti`,
    which is the shared ``dti_from_components``; verified equal to 1.1e-16."""
    return float(t / (alpha * (t + s - m) + beta * k + EPS))


def score(pred, truth, valid=None, known=None) -> float:
    c = components(pred, truth, valid, known)
    return c["dti"]


def _remap(rec: dict) -> dict:
    """Rename the shared metric's ``tp``/``fp``/``fn`` keys to this lane's ``TP_w``/``FP_w``/``FN_w``.

    A pure adapter: the arithmetic is the shared module's, so there is one implementation of the
    metric in this repository.  This lane's scripts and evidence files use the official subscripted
    names from the competition page, hence the rename.
    """
    out = dict(rec)
    for lo, hi in (("tp", "TP_w"), ("fp", "FP_w"), ("fn", "FN_w")):
        if lo in out:
            out[hi] = out.pop(lo)
    return out


def dti_binary(pred_bool, truth, valid=None, known=None) -> dict:
    """Adapter over the shared :func:`gems64.metric.dti_binary` with this lane's key names."""
    from gems64.metric import dti_binary as _shared

    return _remap(_shared(pred_bool, truth, valid=valid, known=known))


def dti_bruteforce(pred, truth, alpha: float = ALPHA, beta: float = BETA,
                   radius: float = RADIUS_PX) -> dict:
    """Adapter over the shared :func:`gems64.metric.dti_bruteforce` unit-test oracle."""
    from gems64.metric import dti_bruteforce as _shared

    return _remap(_shared(pred, truth, alpha=alpha, beta=beta, radius=radius))


# ``marginal_bar`` is aliased to the shared ``marginal_inclusion_threshold`` in the import block
# above; it is deliberately NOT redefined here.  The shared module documents the same historical
# bar bug this lane independently hit (its IR-57-BAR-01 warning), so both lanes converged on
# ``alpha * DTI`` and on rejecting the ``alpha*DTI/(1 - alpha*DTI)`` form.


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
