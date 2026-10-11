#!/usr/bin/env python3
"""Exhaustive toy check of the plug-in Tversky threshold claim.

This dependency-free 1x5 synthetic raster enumerates all 32 binary truth maps under
independent calibrated Bernoulli probabilities. It compares (a) the mean of the
per-map, unweighted Tversky ratios with (b) the ratio of expected confusion counts.
It is deliberately NOT the competition's distance-weighted evaluator and must not be
used to validate or generate a submission. Its purpose is to test the scope of the
alpha * optimal-score shortcut before using it in a nonlinear, spatially coupled metric.
"""

from __future__ import annotations

from itertools import product
import json

ALPHA = 0.2
BETA = 0.8
PROBABILITIES = (0.90, 0.60, 0.20, 0.08, 0.05)
BASE_SELECTION = (True, True, False, False, False)
CANDIDATE_INDEX = 2
EPSILON = 1e-12


def expected_exact_mean_dti(probabilities: tuple[float, ...], selected: tuple[bool, ...]) -> float:
    """Mean exact per-truth-map unweighted DTI over all Bernoulli outcomes."""
    total = 0.0
    n = len(probabilities)
    for truth in product((False, True), repeat=n):
        weight = 1.0
        for probability, is_true in zip(probabilities, truth):
            weight *= probability if is_true else (1.0 - probability)

        tp = sum(is_true and is_selected for is_true, is_selected in zip(truth, selected))
        fp = sum((not is_true) and is_selected for is_true, is_selected in zip(truth, selected))
        fn = sum(is_true and (not is_selected) for is_true, is_selected in zip(truth, selected))
        denominator = tp + ALPHA * fp + BETA * fn + EPSILON
        total += weight * tp / denominator
    return total


def ratio_of_expected_counts(probabilities: tuple[float, ...], selected: tuple[bool, ...]) -> float:
    """Plug-in ratio of expected confusion counts (not E[DTI])."""
    tp = sum(p for p, is_selected in zip(probabilities, selected) if is_selected)
    fp = sum(1.0 - p for p, is_selected in zip(probabilities, selected) if is_selected)
    fn = sum(p for p, is_selected in zip(probabilities, selected) if not is_selected)
    return tp / (tp + ALPHA * fp + BETA * fn + EPSILON)


def best_selection(
    probabilities: tuple[float, ...], objective
) -> tuple[tuple[bool, ...], float]:
    best_mask: tuple[bool, ...] | None = None
    best_value = float("-inf")
    for mask in product((False, True), repeat=len(probabilities)):
        value = objective(probabilities, mask)
        if value > best_value:
            best_mask, best_value = mask, value
    assert best_mask is not None
    return best_mask, best_value


def main() -> None:
    candidate = CANDIDATE_INDEX
    current = BASE_SELECTION
    with_candidate = list(current)
    with_candidate[candidate] = True
    with_candidate = tuple(with_candidate)

    optimum_mask, optimum_mean = best_selection(
        PROBABILITIES, expected_exact_mean_dti
    )
    plugin_optimum_mask, plugin_optimum = best_selection(
        PROBABILITIES, ratio_of_expected_counts
    )
    current_mean = expected_exact_mean_dti(PROBABILITIES, current)
    added_mean = expected_exact_mean_dti(PROBABILITIES, with_candidate)
    marginal_mean = added_mean - current_mean
    threshold_from_mean = ALPHA * optimum_mean
    candidate_probability = PROBABILITIES[candidate]

    current_plugin = ratio_of_expected_counts(PROBABILITIES, current)
    added_plugin = ratio_of_expected_counts(PROBABILITIES, with_candidate)
    plugin_marginal = added_plugin - current_plugin

    assert current == optimum_mask, "the constructed baseline must be globally optimal for E[DTI]"
    assert plugin_optimum_mask == with_candidate, "the plug-in optimum must include the candidate"
    assert candidate_probability > threshold_from_mean, "candidate must pass alpha times exact mean optimum"
    assert candidate_probability > ALPHA * plugin_optimum, "candidate must pass alpha times plug-in optimum"
    assert marginal_mean < 0.0, "exact finite-ensemble mean DTI must reject the candidate"
    assert plugin_marginal > 0.0, "ratio-of-expected-counts must accept the candidate"

    result = {
        "status": "PASS: counterexample reproduced",
        "scope": "synthetic unweighted 1x5 raster; 32 possible truth maps; not a competition score",
        "alpha": ALPHA,
        "beta": BETA,
        "calibrated_probabilities": list(PROBABILITIES),
        "exact_mean_dti_optimal_selection": [int(value) for value in optimum_mask],
        "synthetic_exact_mean_dti_utility_at_optimum": optimum_mean,
        "ratio_expected_counts_optimal_selection": [int(value) for value in plugin_optimum_mask],
        "synthetic_ratio_expected_counts_optimum": plugin_optimum,
        "alpha_times_ratio_expected_counts_optimum": ALPHA * plugin_optimum,
        "candidate_index_zero_based": candidate,
        "candidate_probability": candidate_probability,
        "alpha_times_exact_mean_optimum": threshold_from_mean,
        "exact_mean_dti_utility_before_addition": current_mean,
        "exact_mean_dti_utility_after_addition": added_mean,
        "exact_mean_dti_marginal_utility": marginal_mean,
        "ratio_expected_counts_before_addition": current_plugin,
        "ratio_expected_counts_after_addition": added_plugin,
        "ratio_expected_counts_marginal_utility": plugin_marginal,
        "conclusion": (
            "The alpha*S cutoff passes this candidate, but the mean of exact per-map ratios "
            "falls. The shortcut is valid for the ratio-of-expected-counts formulation used "
            "in the algebraic derivation, not a universal acceptance rule for finite-sample "
            "mean DTI; a spatial kernel requires direct marginal-gain evaluation."
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
