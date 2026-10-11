"""Lane 64 — native-resolution lidar scarp channels, aggregated to the 100 m grid.

Method paragraph this module implements (verbatim scope)
--------------------------------------------------------
"Native-resolution lidar scarp channels.  The 100 m stack discards the subtle
scarps visible in the 1 m GeoDAWN lidar, which plausibly is evidence geologists
use to add faults. ... (i) scarplet template matching ... (ii) Steger sub-pixel
ridge/valley lines and Frangi multiscale Hessian line measures at 2-20 m scales
on a slope-detrended surface.  Aggregate to 100 m cells as scarp-pixel fraction,
SNR-weighted amplitude, structure-tensor orientation coherence and dominant
strike. ..."

What is reused, not rebuilt
---------------------------
The 1 m -> 100 m reduction for this lane already exists in the shared auxiliary
cache as ``data/external/lidar_scarp_features_u8.tif`` (12 bands:
``ex_max, ex_mean, step_max, lapneg_max, lappos_max, downface_max, upface_max,
cross_max, relief, coh100, strike, valid``).  Those are exactly the lane's four
aggregates in quantised form: scarp-pixel fraction (``valid``),
SNR-weighted amplitude (``ex_mean`` / ``ex_max`` / ``step_max``),
structure-tensor orientation coherence (``coh100``) and dominant strike
(``strike``), plus Laplace (ridge/valley-line) and cross-scarp (Hessian)
responses.  Re-deriving them would require the 1 m tiles, which are gated
behind the competition data page and are not reachable from this sandbox.

Dots, not probabilities
-----------------------
The published metric (DrivenData competition 306, page 967) makes every term
linear in ``p``, so for any support the optimal value is 0 or 1: if a location
is worth predicting at all, it is worth predicting at full confidence (see
:mod:`gems57.metric` for the derivation).  The submission this module builds is
therefore a binary dot field, and the whole design problem becomes *which*
pixels to emit and *how many*.

The marginal rule
-----------------
With ``T = TP_w``, ``S = sum(p)`` and ``M = sum_x p(x) max_g k(d(x,g))``::

    DTI = T / (0.2*(T + S - M) + 0.8*|G|)

For sparse dots ``M = T`` and the ratio collapses to::

    DTI = c * S / (0.2*S + 0.8*|G|) = c / (0.2 + 0.8*|G|/S)

where ``c = T/S`` is the mean hidden-truth kernel credit per dot.  Adding one
dot with marginal credit ``dT`` and self-credit ``k`` raises DTI iff
``dT > 0.2*DTI*(dT + 1 - k)``.  Two consequences drive this lane:

1.  Mass alone cannot win: when ``c`` is flat in ``S`` the score rises with
    ``S`` only towards the asymptote ``c/0.2``; the empirical ladder in the
    sibling repositories shows ``c`` *is* flat because those fields saturate.
    The only large prize is a better ``c``, i.e. a better ranking field.
2.  The optimal support is a **maximum-coverage** set, not a top-k list:
    two dots closer than 2R share truth pixels, so plain top-k selection wastes
    mass.  Greedy marginal-coverage selection is the standard (1 - 1/e)
    approximation and is what :func:`greedy_max_cover` implements.

Truth surrogate and why it is only a surrogate
----------------------------------------------
The competition target is a *private* set of expert-mapped faults absent from
the published catalogue, so no local truth exists.  The best available
population-matched proxy is another independent compilation's off-catalogue
part: USGS State Geologic Map Compilation (SGMC) faults more than 300 m from the
given catalogue (``data/external/sgmc_faults_100m.tif``).  Those are real,
mapped faults that the competition catalogue does not carry.

Measured inconsistency, recorded here rather than hidden: under the metric
algebra the champion raster's observed public score is *impossible* if the
hidden truth were distributed like the SGMC-off set (the implied ceiling is
~0.112 versus an observed 0.2778).  The surrogate therefore measures
*population-matched fault-finding skill*, not the competition score, and every
number derived from it is reported as a surrogate diagnostic, never as a
HOLDOUT-DTI or a competition score.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

KERNEL_RADIUS_PX = 3.0            # 300 m at 100 m cells (official triangular kernel)
SUBPLOT = 40                      # 4 km field-fit spatial block
SUPERBLOCK = 8 * SUBPLOT          # 32 km cross-validation super-block


def kernel_offsets(radius: float = KERNEL_RADIUS_PX):
    """All integer offsets with non-zero triangular weight, and their weights."""
    offs = []
    for j in range(-int(radius), int(radius) + 1):
        for i in range(-int(radius), int(radius) + 1):
            k = max(1.0 - float(np.hypot(j, i)) / radius, 0.0)
            if k > 0.0:
                offs.append((j, i, k))
    return offs


OFFSETS = kernel_offsets()


def fold_ids(shape: tuple[int, int], block: int = SUBPLOT, groups: int = 8) -> np.ndarray:
    """Spatial fold label per pixel; folds are ``groups x groups`` super-blocks."""
    h, w = shape
    out = np.zeros(shape, np.int8)
    step = groups * block
    q = 0
    for iy in range(0, h, step):
        for ix in range(0, w, step):
            out[iy:iy + step, ix:ix + step] = q % (groups * groups)
            q += 1
    return out


def fit_blocked_field(features, names, target, active, fold, *, model="logit", C=0.05,
                      neg_ratio=6, seed=11):
    """Fit a truth-probability field with spatially blocked cross-validation.

    For every super-block the model sees only the other super-blocks, and only
    the *target* mask inside them.  The returned surface is a genuine
    out-of-fold prediction everywhere, so it contains no truth from the block
    it predicts.  Nothing catalogue-derived is used unless it is one of the
    caller's ``features``.
    """
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(seed)
    surf = np.zeros(active.shape, np.float32)
    folds = [f for f in np.unique(fold[active])]
    receipts = []
    for q in folds:
        test = (fold == q) & active
        tr = target & active & (fold != q)
        pos = np.flatnonzero(tr.ravel())
        if pos.size < 200:
            continue
        cand = np.flatnonzero((active & (fold != q)).ravel())
        neg = rng.choice(cand, size=min(cand.size, neg_ratio * pos.size), replace=False)
        del cand
        idx = np.concatenate([pos, neg])
        del pos, neg
        X = np.empty((idx.size, len(features)), np.float32)
        for j, a in enumerate(features):
            X[:, j] = a.ravel()[idx]
        y = target.ravel()[idx].astype(int)
        mu, sd = X.mean(0), X.std(0) + 1e-6
        clf = LogisticRegression(max_iter=300, C=C).fit((X - mu) / sd, y)
        del X, y, idx
        te = np.flatnonzero(test.ravel())
        Xt = np.empty((te.size, len(features)), np.float32)
        for j, a in enumerate(features):
            Xt[:, j] = a.ravel()[te]
        surf.ravel()[te] = clf.predict_proba((Xt - mu) / sd)[:, 1].astype(np.float32)
        del Xt
        receipts.append(dict(fold=int(q), train_truth_px=int(tr.sum()),
                             test_px=int(test.sum()),
                             coefficients={n: float(c) for n, c in zip(names, clf.coef_[0])},
                             intercept=float(clf.intercept_[0]),
                             n_features=len(features)))
    return surf, receipts


def greedy_max_cover(demand, active, *, target, pool=500_000, floor=0.02):
    """Lazy-greedy maximum-coverage selection on a demand surface.

    ``demand`` is the expected truth *presence* probability per cell.  The
    objective is the expected kernel credit of the emitted dots,
    ``E[T] = sum_dots sum_{x in N(dot)} demand(x) k``, which is monotone
    submodular; the lazy greedy is the standard approximation.  ``floor`` stops
    the greedy when no candidate can still add ``floor`` expected credit.

    Returns ``(dots, gains, order)`` with the selection order preserved.
    """
    h, w = demand.shape
    kern = np.zeros((7, 7), np.float32)
    for j, i, k in OFFSETS:
        kern[j + 3, i + 3] = k
    d = np.where(active, demand, 0.0).astype(np.float32)
    gain0 = ndi.convolve(d, kern, mode="constant")
    gain0[~active] = -1.0
    flat = np.argsort(gain0.ravel())[::-1][: int(pool)]
    flat = flat[gain0.ravel()[flat] > 0]
    covered = np.zeros((h, w), bool)
    import heapq
    heap = [(-float(gain0.ravel()[i]), int(i)) for i in flat]
    heapq.heapify(heap)
    del flat
    order: list[int] = []
    gains: list[float] = []
    while heap and len(order) < target:
        ng, i = heapq.heappop(heap)
        y, x = divmod(i, w)
        if covered[y, x]:
            continue
        if -ng < floor:
            break
        order.append(i)
        gains.append(-ng)
        for j, ix, _k in OFFSETS:
            yy, xx = y + j, x + ix
            if 0 <= yy < h and 0 <= xx < w:
                covered[yy, xx] = True
        for j in range(-6, 7):
            for ix in range(-6, 7):
                yy, xx = y + j, x + ix
                if not (0 <= yy < h and 0 <= xx < w) or not active[yy, xx] or covered[yy, xx]:
                    continue
                ng2 = 0.0
                for jj, ii, kk in OFFSETS:
                    y2, x2 = yy + jj, xx + ii
                    if 0 <= y2 < h and 0 <= x2 < w and not covered[y2, x2]:
                        ng2 += d[y2, x2] * kk
                heapq.heappush(heap, (-ng2, yy * w + xx))
    dots = np.zeros((h, w), bool)
    idx = np.asarray(order, np.int64)
    dots.ravel()[idx] = True
    return dots, np.asarray(gains), idx


def dti_curve(order, truth, active, sizes):
    """Surrogate DTI, TP_w, and credit-per-dot for the first ``S`` dots of ``order``."""
    from gems57 import metric

    rows = {}
    for S in sizes:
        m = np.zeros(active.shape, bool)
        m.ravel()[order[: int(S)]] = True
        r = metric.dti_binary(m, truth, valid=active)
        rows[int(S)] = dict(surrogate_dti=float(r["dti"]), tp_w=float(r["tp"]),
                            n_dots=int(r["n_emitted"]), n_truth=int(r["n_truth"]),
                            credit_per_dot=float(r["tp"] / max(r["n_emitted"], 1)))
    return rows


def optimal_mass_curve(curve, hidden_truth_pixels):
    """Score shape ``c(S)*S / (0.2*S + 0.8*K)`` as a function of assumed ``K``.

    The transfer factor from the surrogate density to the hidden density cancels
    in the argmax, so the optimal dot count is identified by the surrogate curve
    alone once ``K`` is assumed.  Returned values are proportional to the true
    score; they are **not** scores and must never be reported as such.
    """
    out = {}
    for K in hidden_truth_pixels:
        best_S, best_v = None, -1.0
        for S, row in curve.items():
            v = row["credit_per_dot"] * S / (0.2 * S + 0.8 * K)
            if v > best_v:
                best_S, best_v = S, v
        out[int(K)] = dict(argmax_dots=int(best_S), shape_value=float(best_v))
    return out


def quantile_summary(values) -> dict:
    v = np.asarray(values, np.float64)
    return dict(n=int(v.size), min=float(v.min()), p25=float(np.percentile(v, 25)),
                median=float(np.median(v)), p75=float(np.percentile(v, 75)),
                max=float(v.max()), mean=float(v.mean()))
