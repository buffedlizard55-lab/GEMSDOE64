from pathlib import Path
import json
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from gems57.uniqueness import saturation_certificate, dot_overlap, summarize_registry_rows
from gems64.promotion import promotion_decision


def test_missing_evidence_cannot_promote():
    result = promotion_decision({})
    assert result['verdict'] == 'negative'
    assert not result['download_allowed']
    assert not result['slot_authorized']


def good_evidence():
    checks = ['data_provenance_verified', 'buffered_oof_verified', 'feature_canaries_pass',
              'truth_ensemble_verified', 'surface_registry_pass', 'final_registry_pass',
              'all_prior_rasters_checked', 'validator_pass', 'hash_and_pixel_unique',
              'historical_best_comparable']
    return {**dict.fromkeys(checks, True), 'holdout': dict(evidence_class='HOLDOUT-DTI',
        evaluator_version='test-only', dti=.15, withheld_positive_pixels=25, ci95=[.1, .2],
        paired_comparisons={n: dict(same_surface_and_folds=True, delta=.1, bootstrap_se=.01)
                            for n in ['spacing', 'mclp', 'historical_best']})}


def test_strict_two_se_and_all_baselines():
    e = good_evidence()
    assert promotion_decision(e)['verdict'] == 'promote'
    e['holdout']['paired_comparisons']['mclp']['delta'] = .02
    assert promotion_decision(e)['verdict'] == 'negative'
    e['holdout']['paired_comparisons']['mclp']['delta'] = float('nan')
    assert promotion_decision(e)['verdict'] == 'negative'


@pytest.mark.parametrize('ci', [None, [], [.3, .2], [float('nan'), .4], [True, .5], [-.1, .2]])
def test_invalid_ci_cannot_pass(ci):
    e = good_evidence(); e['holdout']['ci95'] = ci
    assert promotion_decision(e)['verdict'] == 'negative'


def test_universal_witness_and_shifted_grid(tmp_path):
    path = tmp_path / 'witness.tif'
    shape = (9, 9)
    tr = from_origin(243350, 4508550, 100, 100)
    with rasterio.open(path, 'w', driver='GTiff', height=9, width=9, count=1,
                       dtype='float32', crs='EPSG:32611', transform=tr) as ds:
        ds.write(np.ones(shape, np.float32) * .001, 1)
    fp = np.ones(shape, bool)
    with rasterio.open(path) as ds: grid = (ds.shape, ds.crs, ds.transform)
    r = saturation_certificate(path, fp, expected_grid=grid)
    assert r['universal_overlap_blocker']
    candidate = np.zeros(shape); candidate[4, 4] = 1
    assert dot_overlap(candidate, np.ones(shape) * .001) == 1
    wrong_grid = (grid[0], grid[1], from_origin(243450, 4508550, 100, 100))
    with pytest.raises(ValueError, match='CRS/transform'):
        saturation_certificate(path, fp, expected_grid=wrong_grid)


def test_run_card_and_submission_consistency():
    path = Path('evidence/run_card.json')
    if path.exists():
        c = json.loads(path.read_text())
        if c['verdict'] == 'promote':
            assert c['download_allowed'] is True
            assert c['gate_passed'] is True
            assert c['raster_sha256'] == c['raster_zeros_sha256']
            assert len(c['submission_note']) <= 140
            assert Path(c['raster_zeros_file']).is_file()
            assert Path(c['raster_nan_file']).is_file()
            assert len(list(Path('docs/submissions').glob('*.tif'))) == 2
        else:
            assert c['verdict'] == 'negative'
            assert c['raster_sha256'] is None
            assert c['download_allowed'] is False
            assert not list(Path('docs').rglob('*.tif'))


def test_missing_score_and_null_evidence_cannot_promote():
    e = good_evidence(); e['holdout'].pop('dti')
    assert promotion_decision(e)['verdict'] == 'negative'
    e['holdout'] = None
    assert promotion_decision(e)['verdict'] == 'negative'


def test_registry_thresholds_are_strict_not_inclusive():
    common = dict(registry_rasters_expected=1, complete_accessible_scan=True, source_errors=[],
                  candidate_meta=dict(my_dots=10, candidate_rank_variation=True), scope='test fixture only')
    row = dict(submission='fixture', spearman_full_footprint=.9,
        my_dots_within_3px_of_theirs=.7, jaccard_dot_sets=.1, duplicate_by_rho=False,
        duplicate_by_overlap=False, identical_bytes=False, identical_decoded_predictions=False)
    assert summarize_registry_rows([row], **common)['unique']
    row['my_dots_within_3px_of_theirs'] = .70001; row['duplicate_by_overlap'] = True
    assert not summarize_registry_rows([row], **common)['unique']


def test_same_basename_prior_not_exempted(tmp_path):
    from gems57.gates import find_priors
    candidate = tmp_path / 'candidate' / 'same.tif'
    prior = tmp_path / 'registry' / 'same.tif'
    for p in (candidate, prior):
        p.parent.mkdir(); p.write_bytes(b'x' * 1200)
    paths = find_priors([tmp_path], exclude=candidate)
    assert prior in paths
    assert candidate not in paths


def test_file_comparison_rejects_candidate_grid_drift(tmp_path):
    from gems57.uniqueness import compare_to_registry
    path = tmp_path / 'candidate.tif'
    tr = from_origin(243350, 4508550, 100, 100)
    with rasterio.open(path, 'w', driver='GTiff', height=9, width=9, count=1,
                       dtype='float32', crs='EPSG:32611', transform=tr) as ds:
        ds.write(np.eye(9, dtype=np.float32), 1)
    with rasterio.open(path) as ds: crs = ds.crs
    with pytest.raises(ValueError, match='candidate CRS'):
        compare_to_registry(path, [], np.ones((9, 9), bool),
                            expected_grid=((9, 9), crs, from_origin(243450, 4508550, 100, 100)))
