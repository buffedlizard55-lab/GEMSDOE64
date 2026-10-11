#!/usr/bin/env python3
"""Synthetic-only audit of the expected-DTI threshold intuition.

This is deliberately NOT a competition evaluator, holdout runner, raster writer,
or substitute for the template's metric code. It transcribes the published
300 m triangular-kernel equations only for tiny synthetic point rasters, because
this checkout contains no shared evaluator or competition data.

Run:
    python scripts/verify_expected_dti_rule.py

All emitted values are synthetic mathematical checks, never HOLDOUT-DTI or
ORGANIZER-CONFIRMED competition scores.
"""

from __future__ import annotations

import json
import math
from typing import Mapping, Set, Tuple

Pixel = Tuple[int, int]
TruthRaster = Set[Pixel]
PredictionRaster = Mapping[Pixel, float]

ALPHA = 0.2
BETA = 0.8
KERNEL_RADIUS_PIXELS = 3.0  # 300 m support on a synthetic 100 m grid


def triangular_kernel(a: Pixel, b: Pixel) -> float:
    """Published triangular distance kernel, using pixel-center Euclidean distance."""
    distance = math.hypot(a[0] - b[0], a[1] - b[1])
    return max(1.0 - distance / KERNEL_RADIUS_PIXELS, 0.0)


def dti_synthetic(truth: TruthRaster, prediction: PredictionRaster) -> float:
    """Evaluate one sparse synthetic raster by the published DTI equations.

    The function is intentionally small and slow. It must not be used on
    competition rasters: use the official/template evaluator for that.
    """
    if not truth:
        return 0.0
    if any(not (math.isfinite(value) and 0.0 <= value <= 1.0) for value in prediction.values()):
        raise ValueError("Synthetic prediction values must be finite and in [0, 1].")

    coverage_by_truth = {
        g: max(
            (
                value * triangular_kernel(pixel, g)
                for pixel, value in prediction.items()
                if value > 0.0
            ),
            default=0.0,
        )
        for g in truth
    }
    tp_w = sum(coverage_by_truth.values())
    fn_w = sum(1.0 - coverage for coverage in coverage_by_truth.values())
    fp_w = sum(
        value
        * (
            1.0
            - max(
                (triangular_kernel(pixel, g) for g in truth),
                default=0.0,
            )
        )
        for pixel, value in prediction.items()
        if value > 0.0
    )
    denominator = tp_w + ALPHA * fp_w + BETA * fn_w
    return tp_w / denominator if denominator > 0.0 else 0.0


def mean_score(truths: list[TruthRaster], prediction: PredictionRaster) -> float:
    return sum(dti_synthetic(truth, prediction) for truth in truths) / len(truths)


def run_probe() -> dict:
    # Published worked-example arithmetic, rounded to the two decimals shown
    # by the competition description. This is a formula check, not a score.
    worked_example = 3.00 / (3.00 + ALPHA * 1.89 + BETA * 2.00)
    assert round(worked_example, 2) == 0.60

    # Isolated, nonredundant case: three true cells in every world, with one
    # far-away truth swapped between x and y. A single fractional existing
    # prediction makes the common baseline exactly 0.30 in every world.
    anchor = (0, 0)
    shared_unpredicted = (20, 0)
    candidate = (40, 0)
    replacement = (60, 0)
    existing_mass = 36.0 / 47.0
    base = {anchor: existing_mass}
    truths_for = lambda positives, total=100: [
        {anchor, shared_unpredicted, candidate if i < positives else replacement}
        for i in range(total)
    ]

    positive_worlds = truths_for(7)
    negative_worlds = truths_for(5)
    q_above = 7.0 / 100.0
    q_below = 5.0 / 100.0
    baseline_above = mean_score(positive_worlds, base)
    baseline_below = mean_score(negative_worlds, base)
    assert abs(baseline_above - 0.30) < 1e-12
    assert abs(baseline_below - 0.30) < 1e-12

    with_candidate_above = mean_score(positive_worlds, {**base, candidate: 1.0})
    with_candidate_below = mean_score(negative_worlds, {**base, candidate: 1.0})
    gain_above = with_candidate_above - baseline_above
    gain_below = with_candidate_below - baseline_below
    threshold = ALPHA * 0.30
    assert q_above > threshold and gain_above > 0.0
    assert q_below < threshold and gain_below < 0.0

    # Exact-kernel redundancy counterexample. Candidate (3,0) is positive in
    # half the synthetic truth rasters (marginal q=0.50), yet it very slightly
    # lowers mean DTI after existing adjacent predictions have saturated much
    # of the local coverage. A raw per-pixel threshold would accept it; exact
    # expected marginal DTI correctly rejects it.
    redundant_truths = [{(0, 0)}, {(2, 0), (3, 0)}]
    current = {(0, 0): 1.0, (2, 0): 1.0}
    redundant_candidate = (3, 0)
    redundant_q = 0.5
    redundant_baseline = mean_score(redundant_truths, current)
    redundant_after = mean_score(
        redundant_truths,
        {**current, redundant_candidate: 1.0},
    )
    redundant_gain = redundant_after - redundant_baseline
    naive_bar = ALPHA * redundant_baseline
    assert redundant_q > naive_bar
    assert redundant_gain < 0.0

    return {
        "evidence_class": "SYNTHETIC CHECK ONLY — not HOLDOUT-DTI and not ORGANIZER-CONFIRMED",
        "not_a_competition_score": True,
        "published_worked_example": {
            "input_terms": {"TP_w": 3.0, "FP_w": 1.89, "FN_w": 2.0},
            "computed_dti": worked_example,
            "published_rounded_dti": 0.60,
            "check": "PASS",
        },
        "isolated_unit_case": {
            "baseline_dti_each_world": 0.30,
            "alpha_times_baseline": threshold,
            "synthetic_truth_frequency_above_threshold": q_above,
            "mean_dti_gain_above_threshold": gain_above,
            "synthetic_truth_frequency_below_threshold": q_below,
            "mean_dti_gain_below_threshold": gain_below,
            "check": "PASS — q > alpha*S helps and q < alpha*S hurts in the isolated case",
        },
        "kernel_redundancy_counterexample": {
            "truth_rasters": 2,
            "candidate_truth_frequency": redundant_q,
            "alpha_times_mean_baseline_dti": naive_bar,
            "mean_baseline_dti": redundant_baseline,
            "mean_dti_after_addition": redundant_after,
            "exact_mean_marginal_dti_gain": redundant_gain,
            "check": "PASS — exact greedy rule rejects the redundant candidate",
        },
        "interpretation": (
            "The q > alpha*S threshold is numerically correct for the isolated, "
            "nonredundant unit-count case. It is not a safe independent-pixel "
            "rule for the competition's max-over-neighborhood 300 m kernel. "
            "Use mean exact marginal DTI over plausible truth rasters; do not "
            "replace the template evaluator with this probe."
        ),
    }


def main() -> None:
    print(json.dumps(run_probe(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
