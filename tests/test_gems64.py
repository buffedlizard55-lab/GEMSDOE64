"""Tests that execute the lane's changed code paths.

Run: ``python -m pytest tests -q``
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from gems64 import grid as gridmod, metric, theorem, validate
from gems64.select import (ExpectedDtiGreedy, MaxCoverGreedy, expected_dti,
                           kappa_field, nms_topk)

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _synthetic(size=16, seed=0):
    rng = np.random.default_rng(seed)
    w = np.zeros((size, size))
    w[4, 3:11] = 0.5
    w[9, 5:12] = 0.3
    w[rng.integers(0, size, 5), rng.integers(0, size, 5)] = 0.25
    return w


# ------------------------------------------------------------------ the algebra
def test_expected_dti_matches_official_metric():
    """expected_dti(T,F,K) must equal the shared metric on the same binary pair."""
    rng = np.random.default_rng(1)
    size = 24
    truth = np.zeros((size, size), bool)
    truth[5, 4:14] = True
    truth[15, 8:18] = True
    pred = np.zeros((size, size), bool)
    ys = rng.integers(0, size, 60)
    xs = rng.integers(0, size, 60)
    pred[ys, xs] = True
    r = metric.dti_binary(pred, truth)
    kap = kappa_field(truth.astype(np.float64))
    ys2, xs2 = np.nonzero(pred)
    F = float((1.0 - kap[ys2, xs2]).sum())
    # T from the metric's own credit field
    cred, _, _ = metric.max_cover(pred.astype(np.float64), truth)
    T = float(cred.sum())
    K = float(truth.sum())
    # kappa_field is stored float32, so the agreement floor is ~1e-6, not 1e-9
    assert abs(expected_dti(T, F, K) - r["dti"]) < 1e-6
    assert abs(T - r["tp"]) < 1e-9
    assert abs(F - r["fp"]) < 1e-5


def test_accept_bar_equals_alpha_times_dti():
    """Non-redundant dot: the exact accept test flips at kappa = alpha*DTI."""
    T, K, alpha = 3000.0, 10_000.0, 0.2
    dti = 0.30
    F = (T / dti - (1 - alpha) * K) / alpha - T
    D0 = alpha * (T + F) + (1 - alpha) * K
    assert abs(T / D0 - dti) < 1e-12
    for eps in (1e-4, 1e-3):
        k = alpha * dti - eps
        assert (T + k) / (D0 + alpha * (k + 1 - k)) < T / D0
        k = alpha * dti + eps
        assert (T + k) / (D0 + alpha * (k + 1 - k)) > T / D0


def test_threshold_rule_numeric():
    r = theorem.check_threshold_rule(dti=0.30, alpha=0.2)
    assert r["ok"], r
    assert abs(r["analytic_bar"] - 0.06) < 1e-12


def test_lipton_alpha_half():
    r = theorem.check_lipton_generalisation(alpha=0.5, draws=200)
    assert r["ok"], r


# ------------------------------------------------------------------- selectors
@pytest.mark.parametrize("seed", [3, 5])
def test_greedy_plus_prune_is_optimal(seed):
    r = theorem.check_greedy_vs_exhaustive(seed=seed)
    assert r["greedy_optimality_gap"] == 0.0, r


def test_greedy_beats_matched_mass_baselines_on_synthetic():
    w = _synthetic()
    cand = np.array([[a, b] for a in range(w.shape[0]) for b in range(w.shape[1])],
                    np.int32)
    sel = ExpectedDtiGreedy(w, cand)
    res = sel.run(max_dots=200, prune=True)
    mass = res["n_dots"]
    assert mass > 0
    ex = theorem._exact_expected_dti
    v_greedy = ex(w, sel.mask())
    v_nms = ex(w, nms_topk(w.astype(np.float32), cand, 2.8, mass))
    v_mclp = ex(w, MaxCoverGreedy(w, cand).run(mass)["mask"])
    # the DTI-optimal rule must not lose to either baseline on its own objective
    assert v_greedy >= v_nms - 1e-9, (v_greedy, v_nms)
    assert v_greedy >= v_mclp - 1e-9, (v_greedy, v_mclp)


def test_nms_respects_separation():
    p = np.random.default_rng(0).random((40, 40)).astype(np.float32)
    cand = np.array([[a, b] for a in range(40) for b in range(40)], np.int32)
    m = nms_topk(p, cand, 2.8, 60)
    ys, xs = np.nonzero(m)
    assert ys.size == 60
    d = np.hypot(ys[:, None] - ys[None, :], xs[:, None] - xs[None, :])
    np.fill_diagonal(d, 99)
    assert d.min() > 2.8


def test_backward_prune_removes_harmful_dots():
    w = _synthetic(seed=2)
    cand = np.array([[a, b] for a in range(w.shape[0]) for b in range(w.shape[1])],
                    np.int32)
    sel = ExpectedDtiGreedy(w, cand)
    sel.run(max_dots=200, prune=False)
    before = expected_dti(sel.T, sel.F, sel.K)
    n0 = len(sel.placed)
    sel.backward_prune(passes=4)
    after = expected_dti(sel.T, sel.F, sel.K)
    assert after >= before - 1e-12
    assert len(sel.placed) <= n0


# --------------------------------------------------------------- packaging/IO
def test_grid_pins_match_bridged_files():
    g = gridmod.load_grid(ROOT / "data" / "bridge")
    assert (g.height, g.width) == (3730, 3292)
    assert int(g.footprint.sum()) == 5_167_373
    assert int(g.catalogue.sum()) == 60_988


def test_writer_and_validator_roundtrip(tmp_path):
    from gems64 import submission_writer
    g = gridmod.load_grid(ROOT / "data" / "bridge")
    pred = np.zeros(g.shape, np.float32)
    ys, xs = np.nonzero(g.footprint & ~g.catalogue)
    sel = np.random.default_rng(0).choice(ys.size, 500, replace=False)
    pred[ys[sel], xs[sel]] = 1.0
    out = tmp_path / "t.tif"
    rcpt = submission_writer.write_submission(
        out, pred, ROOT / "data" / "bridge" / "sample_submission.tif", g.footprint,
        note="unit test raster", name="unit-test", catalogue=g.catalogue)
    rep = validate.validate(out, g.footprint, g.catalogue)
    validate.assert_submittable(rep)
    assert rcpt["sha256"]
    assert out.exists() and out.with_suffix(".zip").exists()


def test_writer_rejects_out_of_range(tmp_path):
    from gems64 import submission_writer
    g = gridmod.load_grid(ROOT / "data" / "bridge")
    pred = np.zeros(g.shape, np.float32)
    pred[100, 100] = 1.5
    with pytest.raises(ValueError):
        submission_writer.write_submission(
            tmp_path / "bad.tif", pred,
            ROOT / "data" / "bridge" / "sample_submission.tif", g.footprint,
            note="bad", name="bad")
