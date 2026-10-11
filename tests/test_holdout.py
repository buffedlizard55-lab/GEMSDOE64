import numpy as np
import pytest
from gems57.holdout import blocked_component_folds
from gems57.evaluate_holdout import evaluate, pooled_summary, from_terms
from gems57 import metric
from gems64.calibration import crossfit_isotonic, feature_canaries


def test_whole_components_buffers_and_visible_mask():
    fp = np.ones((80, 80), bool)
    cat = np.zeros_like(fp)
    cat[10:20, 10] = True; cat[10:20, 60] = True
    cat[60:70, 10] = True; cat[60:70, 60] = True
    cat[38:42, 35] = True  # cross-boundary component
    folds = blocked_component_folds(cat, fp, buffer_px=4)
    assert len(folds) == 4
    assert np.all(sum(f['region'].astype(int) for f in folds) == 1)
    for f in folds:
        assert not (f['truth'] & f['visible']).any()
        assert not (f['truth'] & f['train']).any()
        assert not (f['region'] & f['train']).any()
        assert not f['truth'][38:42, 35].any()
        if f['region'][38, 35] or f['region'][41, 35]:
            assert not f['train'][38:42, 35].any()
        result, terms = evaluate(cat.astype(float), f, fp, block_side=10)
        assert result['dti'] == pytest.approx(1)
        assert from_terms(terms.sum(axis=0)) == pytest.approx(result['dti'])
        assert result['n_emitted'] == f['truth'].sum()


def test_bootstrap_pools_not_mean_fold_scores():
    # Different-sized physical blocks; matched truths, varying false positives.
    a = np.array([[8, 1, 2, 10], [1, 1, 9, 10], [5, 0, 0, 5]], float)
    b = np.array([[4, 5, 6, 10], [.5, 8, 9.5, 10], [2, 5, 3, 5]], float)
    r = pooled_summary({'candidate': a, 'spacing': b}, candidate='candidate', draws=100)
    assert r['scores']['candidate']['dti'] == pytest.approx(metric.dti_from_components(14, 2, 11))
    delta = r['paired_differences']['spacing']
    assert delta['bootstrap_se'] >= 0
    assert delta['beats_two_se'] == (delta['delta'] > 2 * delta['bootstrap_se'])
    assert r['scores']['candidate']['withheld_positive_pixels'] == 25
    assert r['implementation_sha256']
    b[0, 3] += 1
    with pytest.raises(ValueError, match='truth count'):
        pooled_summary({'candidate': a, 'spacing': b}, candidate='candidate')


def test_calibrator_cannot_see_its_validation_labels():
    s = np.tile(np.arange(10, dtype=float), 4)
    y = np.tile(np.arange(10) >= 5, 4)
    b = np.repeat(np.arange(4), 10)
    first = crossfit_isotonic(s, y, b)
    y[b == 0] = ~y[b == 0]
    second = crossfit_isotonic(s, y, b)
    np.testing.assert_array_equal(first[b == 0], second[b == 0])
    assert np.all((first >= 0) & (first <= 1))


def test_canary_detects_positive_and_inverse_leakage():
    y = np.array([[0, 1], [1, 0]], bool)
    rows = feature_canaries({'leak': y, 'inverse': ~y, 'flat': y * 0}, y, np.ones_like(y))
    assert [r['leakage_until_proven_otherwise'] for r in rows] == [True, True, False]


def test_canary_empty_features_fail_closed():
    y = np.array([0, 1], bool)
    with pytest.raises(ValueError, match='at least one'):
        feature_canaries({}, y, np.ones(2, bool))
