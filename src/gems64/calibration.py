"""Helpers for blocked OOF calibration; no claim of a trained model here."""
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score


def feature_canaries(features, labels, domain):
    labels, domain = np.asarray(labels, bool), np.asarray(domain, bool)
    if labels.shape != domain.shape or np.unique(labels[domain]).size != 2:
        raise ValueError('holdout requires positives and negatives')
    if not features:
        raise ValueError("at least one feature required for leakage screening")
    rows = []
    for name, feature in features.items():
        a = np.asarray(feature)
        if a.shape != labels.shape or not np.isfinite(a[domain]).all():
            raise ValueError(f'invalid holdout feature: {name}')
        auc = float(roc_auc_score(labels[domain], a[domain]))
        rows.append(dict(feature=name, auc=auc, directional_auc=max(auc, 1 - auc),
                         leakage_until_proven_otherwise=max(auc, 1 - auc) > .90))
    return rows


def crossfit_isotonic(oof_scores, labels, spatial_blocks):
    """Leave-block-out isotonic fit on ALREADY out-of-fold base predictions.

    Caller must supply buffered, segment-safe base OOF provenance. Cross-fitting
    this calibrator alone cannot turn in-sample model predictions into OOF data.
    Use un-rebalanced prevalence, or explicit inclusion weights before calling
    an appropriately weighted calibrator; this helper uses the whole population.
    """
    s, y, b = map(np.asarray, (oof_scores, labels, spatial_blocks))
    if s.ndim != 1 or s.shape != y.shape or s.shape != b.shape:
        raise ValueError('matching one-dimensional OOF arrays required')
    if not np.isfinite(s).all() or not np.isfinite(b).all() or not np.all((y == 0) | (y == 1)):
        raise ValueError('finite scores/block IDs and binary labels required')
    groups = np.unique(b)
    if len(groups) < 3:
        raise ValueError('at least three spatial blocks required')
    calibrated = np.empty(s.shape, float)
    for group in groups:
        test = b == group
        if np.unique(y[~test]).size < 2:
            raise ValueError('calibration training block lacks a label class')
        estimator = IsotonicRegression(y_min=0., y_max=1., out_of_bounds='clip')
        estimator.fit(s[~test], y[~test])
        calibrated[test] = estimator.predict(s[test])
    return calibrated
