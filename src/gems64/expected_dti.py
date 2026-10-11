"""Exact mean-DTI selection on finite plausible truth rasters.

This is a bounded reference implementation, NOT a full-grid trained model.
It consumes binary truth draws rather than treating probability maps as truth.
Every candidate is re-scanned: the expectation of a ratio is not assumed
submodular, so stale lazy-greedy bounds would be unjustified.
"""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic

import numpy as np
from scipy.spatial.distance import cdist

from gems57 import metric


def plugin_tversky(probabilities, selected, alpha=0.2):
    """Ratio of expected counts, not the expected finite-sample score."""
    p = np.asarray(probabilities, float)
    selected = np.asarray(selected, bool)
    if p.shape != selected.shape or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("matching probabilities in [0,1] required")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie strictly between zero and one")
    denominator = alpha * selected.sum() + (1 - alpha) * p.sum()
    return float(p[selected].sum() / denominator) if denominator else 0.0


@dataclass
class Selection:
    dots: np.ndarray
    mean_synthetic_dti: float
    additions: list[dict]
    removals: list[dict]
    max_remaining_add_gain: float
    max_remaining_remove_gain: float
    truth_draws: int


class ExpectedDTI:
    """Bounded exact gain oracle using the shared triangular kernel.

    Storage is O(candidates * sum of truth pixels across draws). Fail rather
    than silently truncate candidates when this reference budget is exceeded.
    Truths and candidates must already have visible catalogue cells removed.
    At least 32 distinct binary truth rasters are required; repeated copies do
    not count toward the configured draw minimum.
    """

    def __init__(self, truths, candidates, *, allowed=None, min_draws=32,
                 max_matrix_elements=8_000_000):
        truth = np.asarray(truths)
        candidate = np.asarray(candidates)
        if truth.ndim != 3 or candidate.ndim != 2 or truth.shape[1:] != candidate.shape:
            raise ValueError("truth draws must be (draw, row, col), candidates (row, col)")
        if not isinstance(min_draws, (int, np.integer)) or min_draws < 32:
            raise ValueError("min_draws must be an integer of at least 32")
        if truth.shape[0] < min_draws:
            raise ValueError(f"at least {min_draws} plausible truth rasters required")
        if not np.all((truth == 0) | (truth == 1)) or not np.all((candidate == 0) | (candidate == 1)):
            raise ValueError("binary truth draws/candidate mask required; probabilities are not truth")
        truth_bool = truth.astype(bool, copy=False)
        packed_draws = np.packbits(truth_bool.reshape(truth.shape[0], -1), axis=1)
        distinct_draws = np.unique(packed_draws, axis=0).shape[0]
        if distinct_draws < min_draws:
            raise ValueError(
                f"at least {min_draws} distinct plausible truth rasters required; "
                f"received {distinct_draws}"
            )
        if allowed is not None:
            allowed = np.asarray(allowed, bool)
            if allowed.shape != candidate.shape or np.any(truth[:, ~allowed]) or np.any(candidate[~allowed]):
                raise ValueError("truth/candidate outside allowed footprint or on visible catalogue")
        self.truth = truth_bool
        self.shape = candidate.shape
        self.coords = np.argwhere(candidate)
        self.counts = self.truth.sum(axis=(1, 2)).astype(float)
        if len(self.coords) * self.counts.sum() > max_matrix_elements:
            raise MemoryError("reference selector matrix budget exceeded; no truncated result returned")
        self.weights = []
        self.fp = np.zeros((len(self.truth), len(self.coords)))
        for i, draw in enumerate(self.truth):
            # Distance rows are candidate pixels; columns are this draw's truth.
            w = metric.kernel(cdist(self.coords, np.argwhere(draw)))
            self.weights.append(w)
            self.fp[i] = 1.0 - (w.max(axis=1) if w.shape[1] else 0.0)

    def scores(self, support):
        support = np.asarray(support, bool)
        if support.shape != (len(self.coords),):
            raise ValueError("support length mismatch")
        tp = np.array([w[support].max(axis=0).sum() if support.any() else 0.0
                       for w in self.weights])
        fp = self.fp[:, support].sum(axis=1)
        fn = self.counts - tp
        return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)

    def select(self, *, tolerance=1e-12, max_seconds=60):
        if tolerance < 0 or not np.isfinite(tolerance) or not np.isfinite(max_seconds) or max_seconds <= 0:
            raise ValueError("nonnegative finite tolerance and positive budget required")
        deadline = monotonic() + max_seconds
        selected = np.zeros(len(self.coords), bool)
        additions, removals = [], []
        current = float(self.scores(selected).mean())

        def best_change(adding):
            best_gain, best_index = -np.inf, None
            for index in np.flatnonzero(~selected if adding else selected):
                if monotonic() > deadline:
                    raise TimeoutError("selection unfinished; no promotable artifact")
                trial = selected.copy()
                trial[index] = adding
                gain = float(self.scores(trial).mean()) - current
                # np.flatnonzero gives deterministic row-major tie-breaking.
                if gain > best_gain:
                    best_gain, best_index = gain, int(index)
            return (0.0, None) if best_index is None else (best_gain, best_index)

        while True:
            gain, index = best_change(True)
            if index is None or gain <= tolerance:
                break
            selected[index] = True
            current = float(self.scores(selected).mean())
            additions.append(dict(pixel=self.coords[index].tolist(), gain=gain))
        while True:
            gain, index = best_change(False)
            if index is None or gain <= tolerance:
                break
            selected[index] = False
            current = float(self.scores(selected).mean())
            removals.append(dict(pixel=self.coords[index].tolist(), gain=gain))
        remaining_add, _ = best_change(True)
        remaining_remove, _ = best_change(False)
        dots = np.zeros(self.shape, bool)
        if selected.any():
            dots[tuple(self.coords[selected].T)] = True
        return Selection(dots, current, additions, removals,
                         remaining_add, remaining_remove, len(self.truth))
