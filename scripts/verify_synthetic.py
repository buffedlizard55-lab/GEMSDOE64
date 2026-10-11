#!/usr/bin/env python3
"""Mathematical tests only. No competition TIFF and no HOLDOUT-DTI claim."""
from itertools import product
from pathlib import Path
import json
import numpy as np
from gems64.expected_dti import ExpectedDTI, plugin_tversky
from gems57 import metric


def verify():
    rng = np.random.default_rng(64011)
    alpha = .2
    errors = []
    optimum_errors = []
    cases = 200
    for _ in range(cases):
        p = rng.uniform(.001, .999, 8)
        subsets = np.array(list(product((False, True), repeat=len(p))))
        scores = np.array([plugin_tversky(p, s, alpha) for s in subsets])
        optimal = subsets[scores.argmax()]
        bar = alpha * scores.max()
        optimum_errors.append(bool(np.any(p[optimal] < bar - 1e-12)
                                   or np.any(p[~optimal] > bar + 1e-12)))
        for s, before in zip(subsets, scores):
            for j in np.flatnonzero(~s):
                trial = s.copy(); trial[j] = True
                delta = plugin_tversky(p, trial, alpha) - before
                errors.append(bool((delta > 1e-12) != (p[j] > alpha * before + 1e-12)))
    # Exhaustive finite-distribution counterexample search, not a Monte Carlo score.
    states = np.array(list(product((0, 1), repeat=4)))
    counterexample = None
    for _ in range(200):
        p = rng.uniform(.005, .6, 4)
        probability = np.prod(np.where(states, p, 1 - p), axis=1)
        def expectation(selected):
            tp = (states * selected).sum(axis=1)
            den = alpha * selected.sum() + (1 - alpha) * states.sum(axis=1)
            return float(probability @ np.divide(tp, den, out=np.zeros(len(states)), where=den > 0))
        for s in states.astype(bool):
            base = expectation(s)
            for j in np.flatnonzero(~s):
                trial = s.copy(); trial[j] = True
                gain = expectation(trial) - base
                if (gain > 1e-12) != (p[j] > alpha * base + 1e-12):
                    counterexample = dict(probabilities=p.tolist(), selected=s.tolist(), added_pixel=int(j),
                        exact_expected_before=base, exact_expected_gain=gain,
                        probability_bar=alpha * base, candidate_probability=float(p[j]),
                        conclusion='Probability > alpha * expected score is NOT an exact finite-raster expectation rule.')
                    break
            if counterexample: break
        if counterexample: break
    assert counterexample is not None
    assert not any(errors) and not any(optimum_errors)

    # Thirty-two correlated, jittered line truths; synthetic, not model outputs.
    # Common and local offsets each vary by at most one pixel (two combined),
    # and repeated patterns are resampled so every truth raster is distinct.
    truths = np.zeros((32, 13, 13), bool)
    jitter_rng = np.random.default_rng(64012)
    seen_paths = set()
    rows = np.arange(3, 10)
    for i in range(len(truths)):
        while True:
            common_shift = int(jitter_rng.integers(-1, 2))
            local_shift = jitter_rng.integers(-1, 2, size=len(rows))
            path = tuple((6 + common_shift + local_shift).tolist())
            if path not in seen_paths:
                seen_paths.add(path)
                break
        truths[i, rows, path] = True
    candidates = np.zeros((13, 13), bool)
    candidates[3:10:2, 4:9:2] = True
    oracle = ExpectedDTI(truths, candidates)
    result = oracle.select()
    exact = [metric.dti_bruteforce(result.dots, t)['dti'] for t in truths]
    np.testing.assert_allclose(result.mean_synthetic_dti, np.mean(exact), atol=1e-12)
    # Deterministic sparse-spacing control, same candidates, synthetic demonstration only.
    control = np.zeros((13, 13), bool)
    control[3:10:3, 6] = True
    control &= candidates
    control_mean = float(np.mean([metric.dti_binary(control, t)['dti'] for t in truths]))
    return dict(evidence_class='SYNTHETIC-UNIT-TEST-NOT-HOLDOUT', seed=64011,
        plugin_rule=dict(probability_vectors=cases, exhaustive_subsets_per_vector=256,
                         addition_comparisons=len(errors), errors=sum(errors),
                         optimum_threshold_errors=sum(optimum_errors)),
        finite_expectation_counterexample=counterexample,
        kernel_selector=dict(truth_draws=32, candidates=int(candidates.sum()), selected=int(result.dots.sum()),
            exact_mean_synthetic_dti=result.mean_synthetic_dti,
            synthetic_spacing_control_mean=control_mean,
            oracle_absolute_error=abs(result.mean_synthetic_dti-float(np.mean(exact))),
            max_remaining_add_gain=result.max_remaining_add_gain,
            max_remaining_remove_gain=result.max_remaining_remove_gain,
            additions=result.additions, removals=result.removals),
        competition_inference='None. No holdout, no calibration claim, no promotion evidence.')


if __name__ == '__main__':
    result = verify()
    path = Path('evidence/synthetic_verification.json')
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2))
