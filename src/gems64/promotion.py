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


def lane64_promotion_decision(run_card: dict) -> dict:
    """Evaluate the GEMSDOE64 Native-Resolution Lidar Scarp Channels lane gate and uniqueness criteria."""
    failures = []
    if not isinstance(run_card, dict):
        return dict(verdict='negative', download_allowed=False, failed_gates=['invalid_run_card'])

    h = run_card.get('holdout') or {}
    if h.get('evidence_class') != 'HOLDOUT-DTI' or not h.get('evaluator_version'):
        failures.append('holdout_provenance')
    dti = h.get('dti')
    if not isinstance(dti, (int, float)) or isinstance(dti, bool) or not math.isfinite(dti) or not (0.0 <= dti <= 1.0):
        failures.append('holdout_dti')
    n_pos = h.get('withheld_positive_pixels')
    if not isinstance(n_pos, int) or isinstance(n_pos, bool) or n_pos <= 0:
        failures.append('withheld_positives')
    ci = h.get('ci95')
    if not isinstance(ci, list) or len(ci) != 2 or ci[0] > ci[1]:
        failures.append('holdout_ci')

    if h.get('beats_two_se_vs_100m_baseline') is not True:
        failures.append('overall_holdout_gain')
    rf = h.get('range_front_blocks') or {}
    off_rf = h.get('off_range_front_blocks') or {}
    if rf.get('beats_two_se') is not True:
        failures.append('range_front_holdout_gain')
    if off_rf.get('beats_two_se') is not True:
        failures.append('off_range_front_holdout_gain')

    lg = run_card.get('lane_gate') or {}
    if lg.get('gate_met') is not True or (lg.get('off_range_front_gain') or 0.0) <= 0.0:
        failures.append('lane_gate_not_confined_to_range_fronts')

    reg = run_card.get('correlation_overlap_vs_registry') or {}
    if (reg.get('surface_spearman', 1.0) >= 0.90 or
            reg.get('final_dots_spearman', 1.0) >= 0.90 or
            reg.get('final_dot_overlap_vs_discrete_detectors', 1.0) >= 0.70 or
            reg.get('byte_unique') is not True or
            reg.get('pixel_unique') is not True):
        failures.append('registry_uniqueness')

    val = run_card.get('validator_output') or {}
    if (val.get('all_checks_passed') is not True or
            val.get('no_nan_inside_footprint') is not True or
            val.get('values_in_0_1') is not True or
            val.get('crs_shape_transform_match') is not True):
        failures.append('validator_checks')

    note = run_card.get('note') or ''
    if not isinstance(note, str) or not (1 <= len(note) <= 140):
        failures.append('submission_note_length')

    return dict(
        verdict='negative' if failures else 'promote',
        download_allowed=not failures,
        failed_gates=failures,
        slot_authorized=False,
        submission_slots_used=0,
    )
