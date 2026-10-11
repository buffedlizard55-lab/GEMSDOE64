"""Publication policy: evidence absence is a failure, never a default pass."""
import math


def promotion_decision(evidence):
    failures = []
    for key in ('data_provenance_verified', 'buffered_oof_verified',
                'feature_canaries_pass', 'truth_ensemble_verified',
                'surface_registry_pass', 'final_registry_pass',
                'all_prior_rasters_checked', 'validator_pass',
                'hash_and_pixel_unique', 'historical_best_comparable'):
        if evidence.get(key) is not True:
            failures.append(key)
    h = evidence.get('holdout') or {}
    if not isinstance(h, dict):
        h = {}
    score = h.get('dti')
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 1:
        failures.append('holdout_dti')
    if h.get('evidence_class') != 'HOLDOUT-DTI' or not h.get('evaluator_version'):
        failures.append('holdout_provenance')
    n = h.get('withheld_positive_pixels')
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        failures.append('withheld_positives')
    ci = h.get('ci95')
    if not isinstance(ci, list) or len(ci) != 2 or not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            and 0 <= v <= 1 for v in ci) or ci[0] > ci[1]:
        failures.append('holdout_ci')
    comparisons = h.get('paired_comparisons') or {}
    if not isinstance(comparisons, dict):
        comparisons = {}
    for baseline in ('spacing', 'mclp', 'historical_best'):
        comparison = comparisons.get(baseline) or {}
        if not isinstance(comparison, dict):
            comparison = {}
        delta, se = comparison.get('delta'), comparison.get('bootstrap_se')
        if (comparison.get('same_surface_and_folds') is not True or
            not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
                    for x in (delta, se)) or se < 0 or not delta > 2 * se):
            failures.append(f'improvement_vs_{baseline}')
    return dict(verdict='negative' if failures else 'promote',
                download_allowed=not failures, failed_gates=failures,
                slot_authorized=False, submission_slots_used=0)
