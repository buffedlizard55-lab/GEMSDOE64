"""Population-matched instruments for the lidar-scarp lane.

The competition's truth (expert-mapped *new* faults) cannot be observed locally,
so every number this module produces is a **proxy-instrument** result.  Two
instruments are used, and the receipt always says which one:

* ``sgmc_off`` -- USGS state-geological-map fault cells more than 300 m from the
  mapped catalogue.  This is the sibling projects' agreed like-for-like
  population ("real mapped faults the catalogue does not contain"), and it is
  known to *favour rock-exposed terrain*; a terrain-class-matched control is
  therefore mandatory before any gain is believed.
* ``catalogue_hide`` -- whole-component hide-and-recover on the mapped catalogue
  itself, using the shared ``gems57.spatial.folds`` split.  This instrument is
  blind to off-catalogue arms by construction; it is used as a no-harm check and
  as a sensitivity measure for faint-scarp recovery, never as an off-catalogue
  promotion target.

Metric arithmetic is the shared ``gems57.metric`` / ``gems57.evaluate_holdout``
implementation -- this module adds instruments and controls, never a second
metric.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from gems57 import evaluate_holdout, metric, spatial


def distance_px(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance in pixels from every cell to the nearest True cell."""
    return ndi.distance_transform_edt(~np.asarray(mask, bool))


def sgmc_off_truth(sgmc: np.ndarray, catalogue: np.ndarray, footprint: np.ndarray,
                   *, min_px: float = 3.0) -> tuple[np.ndarray, dict]:
    """Faults in the independent compilation that are off the mapped catalogue."""
    sgmc = np.asarray(sgmc, bool)
    catalogue = np.asarray(catalogue, bool)
    footprint = np.asarray(footprint, bool)
    if not (sgmc.shape == catalogue.shape == footprint.shape):
        raise ValueError("grid mismatch")
    off = (distance_px(catalogue) > float(min_px)) & footprint
    truth = sgmc & off
    receipt = dict(evidence_class="PROXY-INSTRUMENT", instrument="sgmc_off",
                   min_catalogue_distance_px=float(min_px),
                   sgmc_px_in_footprint=int((sgmc & footprint).sum()),
                   truth_px=int(truth.sum()),
                   note=("state-geological-map compilation, not the hidden panel; "
                         "favours rock-exposed terrain"))
    return truth, receipt


def catalogue_instrument(catalogue: np.ndarray, footprint: np.ndarray) -> tuple[dict, dict]:
    """Whole-component hide-and-recover split on the mapped catalogue."""
    catalogue = np.asarray(catalogue, bool)
    footprint = np.asarray(footprint, bool)
    folds = list(spatial.folds(catalogue, footprint))
    if len(folds) != 4:
        raise AssertionError("shared split must produce four folds")
    receipt = dict(evidence_class="PROXY-INSTRUMENT", instrument="catalogue_hide",
                   split="gems57.spatial.folds (label-blind quadrants, buffer 80 px)",
                   folds=[f["receipt"] for f in folds],
                   note="the catalogue is masked at scoring, so this instrument cannot "
                        "promote off-catalogue arms; it is a no-harm / sensitivity check")
    return {"folds": folds}, receipt


def fold_for_truth(truth: np.ndarray, footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    """One pooled evaluation domain: whole footprint, catalogue masked, given truth."""
    return dict(region=np.asarray(footprint, bool), visible=np.asarray(catalogue, bool),
                masked_known=np.asarray(catalogue, bool), truth=np.asarray(truth, bool))


def terms_for(dots: np.ndarray, fold: dict, footprint: np.ndarray, *,
              block_side: int = 200) -> np.ndarray:
    """Per-spatial-block (TP, FP, FN, truth) terms using the shared evaluator."""
    p = np.asarray(dots, np.float64)
    if p.shape != footprint.shape:
        raise ValueError("dot/footprint shape mismatch")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("dots must already be finite in [0,1]")
    _, terms = evaluate_holdout.evaluate(p, fold, footprint, block_side=block_side)
    return terms


def pooled_dti(terms: np.ndarray, *, n_dots: int | None = None) -> dict:
    """Pooled DTI of a per-block term array (all blocks)."""
    t = np.asarray(terms, float).sum(axis=0)
    out = dict(dti=float(evaluate_holdout.from_terms(t)), tp=float(t[0]), fp=float(t[1]),
               fn=float(t[2]), n_truth=int(round(t[3])))
    if n_dots is not None:
        out["n_dots"] = int(n_dots)
    return out


def credit_per_dot(terms: np.ndarray, n_dots: int) -> float:
    """``TP_w`` per emitted dot -- the competition algebra's credit/dot view.

    ``TP_w`` is a sum over *truth* pixels of their best kernel credit, so this
    ratio mixes truth coverage with dot count.  It is the same quantity the
    sibling projects report as "credit/dot"; the receipt names it exactly.
    """
    if int(n_dots) <= 0:
        raise ValueError("credit per dot needs a positive dot count")
    return float(np.asarray(terms, float).sum(axis=0)[0] / int(n_dots))


def _stratum_ids(relief: np.ndarray, slope_proxy: np.ndarray, footprint: np.ndarray,
                 *, n_relief: int = 8, n_slope: int = 4) -> np.ndarray:
    r = np.asarray(relief, float)
    s = np.asarray(slope_proxy, float)
    ids = np.full(r.shape, -1, np.int64)
    if not footprint.any():
        return ids
    rv = r[footprint]
    sv = s[footprint]
    r_edges = np.quantile(rv, np.linspace(0, 1, n_relief + 1)[1:-1])
    s_edges = np.quantile(sv, np.linspace(0, 1, n_slope + 1)[1:-1])
    ri = np.searchsorted(r_edges, r)
    si = np.searchsorted(s_edges, s)
    ids[footprint] = ri[footprint] * n_slope + si[footprint]
    return ids


def terrain_matched_control(dots: np.ndarray, relief: np.ndarray, slope_proxy: np.ndarray,
                            eligible: np.ndarray, *, seed: int = 11) -> np.ndarray:
    """Random dots drawn with the candidate's own terrain-class histogram.

    Classes are 8 relief x 4 slope quantile bands (32 classes) computed inside the
    eligible domain.  The control therefore matches *where the candidate put
    mass* by terrain class while destroying the scarp-geometry ranking -- the H52
    lesson is that an amplitude ranking can look good simply because it lives in
    the right terrain class.
    """
    dots = np.asarray(dots, bool)
    eligible = np.asarray(eligible, bool)
    ids = _stratum_ids(relief, slope_proxy, eligible)
    rng = np.random.default_rng(seed)
    out = np.zeros(dots.shape, bool)
    per_class = {int(v): int(c) for v, c in zip(*np.unique(ids[dots], return_counts=True)) if v >= 0}
    for cls, want in per_class.items():
        pool = np.flatnonzero((ids == cls) & eligible & ~dots)
        if pool.size == 0:
            continue
        take = min(want, pool.size)
        out.ravel()[rng.choice(pool, size=take, replace=False)] = True
    return out


def block_bootstrap_arms(arms: dict[str, np.ndarray], *, candidate: str, draws: int = 1000,
                         seed: int = 520810) -> dict:
    """Paired 20 km block bootstrap across arms on one instrument."""
    return evaluate_holdout.pooled_summary(arms, draws=draws, seed=seed, candidate=candidate)


def stratified_summary(terms_by_arm: dict[str, np.ndarray], block_mask: np.ndarray) -> dict:
    """Pooled DTI of each arm restricted to a subset of the spatial blocks."""
    block_mask = np.asarray(block_mask, bool)
    out = {}
    for name, terms in terms_by_arm.items():
        sub = np.asarray(terms, float)[block_mask]
        totals = sub.sum(axis=0)
        out[name] = dict(blocks=int(block_mask.sum()),
                         blocks_with_truth=int((sub[:, 3] > 0).sum()),
                         dti=float(evaluate_holdout.from_terms(totals)),
                         tp=float(totals[0]), fp=float(totals[1]), fn=float(totals[2]),
                         n_truth=int(round(totals[3])))
    return out


def stratified_paired(terms_by_arm: dict[str, np.ndarray], block_mask: np.ndarray,
                      candidate: str, *, draws: int = 1000) -> dict:
    """Paired block bootstrap of the candidate against every arm *inside* a stratum.

    The gates ask whether a gain survives where range-front terrain artifacts
    cannot explain it, so the comparison must carry a CI in the restricted
    stratum, not only pooled.
    """
    block_mask = np.asarray(block_mask, bool)
    sub = {name: np.asarray(terms, float)[block_mask] for name, terms in terms_by_arm.items()}
    if sub[candidate].shape[0] < 2:
        raise ValueError("a stratum needs at least two spatial blocks")
    return evaluate_holdout.pooled_summary(sub, draws=draws, candidate=candidate)


def range_front_blocks(catalogue: np.ndarray, relief: np.ndarray, footprint: np.ndarray,
                       *, quantile: float = 0.9, block_side: int = 200) -> tuple[np.ndarray, dict]:
    """Classify 20 km blocks as range-front or interior.

    A block is a range-front block when it contains mapped catalogue fault cells
    whose local relief is in the top ``1 - quantile`` of relief at catalogue
    cells -- a geographic stratification from public data, not a label-dependent
    selection of candidate cells.  The lane's gate requires the gain to survive
    *outside* these blocks, because the sibling H52 measurement showed detector
    top cells sitting on fan-head incision and terrace risers along range fronts
    (a terrain-class artifact) rather than on fault trace.
    """
    catalogue = np.asarray(catalogue, bool)
    relief = np.asarray(relief, float)
    footprint = np.asarray(footprint, bool)
    if not (catalogue & footprint).any():
        raise ValueError("no catalogue cells inside the footprint to define range fronts")
    relief_px = float(np.quantile(relief[catalogue & footprint], quantile))
    front_px = catalogue & (relief >= relief_px) & footprint
    h, w = footprint.shape
    ncols = (w + block_side - 1) // block_side
    nrows = (h + block_side - 1) // block_side
    counts = np.zeros(nrows * ncols, np.int64)
    y, x = np.nonzero(front_px)
    ids = (y // block_side) * ncols + (x // block_side)
    counts += np.bincount(ids, minlength=counts.size)
    yy, xx = np.mgrid[0:h, 0:w]
    block_id = (yy // block_side) * ncols + (xx // block_side)
    is_front = np.zeros_like(counts, bool)
    is_front[counts > 0] = True
    return is_front[block_id], dict(
        blocks_total=int(counts.size), blocks_range_front=int(is_front.sum()),
        front_positive_px=int(front_px.sum()), relief_threshold_m=float(relief_px),
        quantile=float(quantile),
        block_side_px=int(block_side), block_side_m=int(block_side * metric.PIXEL_M))


def auc(feature: np.ndarray, truth: np.ndarray, domain: np.ndarray) -> dict:
    """Leakage canary: single-feature AUC against an instrument's truth."""
    from sklearn.metrics import roc_auc_score
    f = np.asarray(feature, float)[domain]
    y = np.asarray(truth, bool)[domain]
    if np.unique(y).size != 2:
        raise ValueError("canary needs positives and negatives")
    a = float(roc_auc_score(y, f))
    return dict(auc=a, directional_auc=max(a, 1 - a),
                leakage_until_proven_otherwise=max(a, 1 - a) > 0.90)
