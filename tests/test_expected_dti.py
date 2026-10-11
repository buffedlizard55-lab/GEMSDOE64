import numpy as np
import pytest
from gems57 import metric
from gems64.expected_dti import ExpectedDTI, plugin_tversky


@pytest.mark.parametrize('seed', range(8))
def test_exact_metric_matches_literal_oracle(seed):
    rng = np.random.default_rng(seed)
    truth = rng.random((7, 9)) < .1
    pred = rng.random((7, 9)) * (rng.random((7, 9)) < .1)
    actual = metric.dti_exact(pred, truth)
    literal = metric.dti_bruteforce(pred, truth)
    for k in ('tp', 'fp', 'fn', 'dti'):
        assert actual[k] == pytest.approx(literal[k])


def test_mean_ratio_is_not_ratio_of_means():
    truths = np.zeros((32, 7, 7), bool)
    truths[:16, 3, 3] = True
    truths[16:, 1:6, 1:6] = True
    cand = np.zeros((7, 7), bool); cand[3, 3] = True
    oracle = ExpectedDTI(truths, cand)
    exact = [metric.dti_binary(cand, t)['dti'] for t in truths]
    assert oracle.scores(np.array([True])).mean() == pytest.approx(np.mean(exact))
    terms = [metric.dti_binary(cand, t) for t in truths]
    pooled = metric.dti_from_components(*[np.mean([r[k] for r in terms]) for k in ('tp', 'fp', 'fn')])
    assert abs(pooled - np.mean(exact)) > .01


def test_selector_redundancy_and_backward_stop():
    truths = np.zeros((32, 11, 11), bool); truths[:, 5, 5] = True
    cand = np.zeros((11, 11), bool); cand[4:7, 4:7] = True; cand[0, 0] = True
    result = ExpectedDTI(truths, cand).select()
    assert result.dots.sum() == 1
    assert result.dots[5, 5]
    assert result.mean_synthetic_dti == pytest.approx(1)
    assert result.max_remaining_add_gain <= 1e-12
    assert result.max_remaining_remove_gain <= 1e-12


def test_kernel_can_credit_more_than_one_truth():
    t = np.zeros((7, 7), bool); t[3, 3:5] = True
    p = np.zeros((7, 7), bool); p[3, 3] = True
    assert metric.dti_binary(p, t)['tp'] > 1


def test_candidate_mask_known_cells_rejected():
    t = np.zeros((32, 3, 3), bool)
    cand = np.zeros((3, 3), bool); cand[1, 1] = True
    allowed = np.ones((3, 3), bool); allowed[1, 1] = False
    with pytest.raises(ValueError, match='allowed'):
        ExpectedDTI(t, cand, allowed=allowed)


def test_no_silent_truth_or_memory_substitution():
    t = np.ones((32, 3, 3), bool)
    with pytest.raises(ValueError, match='32'):
        ExpectedDTI(t[:2], t[0])
    with pytest.raises(ValueError, match='binary'):
        ExpectedDTI(t.astype(float) * .5, t[0])
    with pytest.raises(MemoryError):
        ExpectedDTI(t, t[0], max_matrix_elements=5)
    with pytest.raises(ValueError):
        plugin_tversky([np.nan], [True])


def test_empty_truth_draws_have_zero_score():
    oracle = ExpectedDTI(np.zeros((32, 3, 3), bool), np.ones((3, 3), bool))
    result = oracle.select()
    assert not result.dots.any()
    assert result.mean_synthetic_dti == 0


def test_backward_pruning_removes_early_redundant_center():
    truths = np.zeros((32, 9, 9), bool)
    truths[:, 3, 3] = True; truths[:, 3, 5] = True; truths[:, 5, 4] = True
    candidates = truths[0].copy(); candidates[4, 4] = True
    result = ExpectedDTI(truths, candidates).select()
    assert result.additions[0]['pixel'] == [4, 4]
    assert result.removals[0]['pixel'] == [4, 4]
    np.testing.assert_array_equal(result.dots, truths[0])
    assert result.mean_synthetic_dti == pytest.approx(1)
    assert result.max_remaining_remove_gain <= 0


def test_selector_never_returns_a_truncated_time_budget_result():
    truths = np.zeros((32, 5, 5), bool); truths[:, 2, 2] = True
    oracle = ExpectedDTI(truths, truths[0])
    with pytest.raises(TimeoutError):
        oracle.select(max_seconds=1e-30)
    with pytest.raises(ValueError):
        oracle.select(max_seconds=float('nan'))
