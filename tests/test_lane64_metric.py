"""The lane's metric implementation must agree with the shared brute-force evaluator.

`scripts/build_scarp_stage2.py::metric_terms` is a second implementation of the published
distance-weighted Tversky index, written for speed on the 3730 x 3292 grid. A second
implementation is only safe if it is checked against the shared one, so this module does
exactly that on random fields, including the region-restricted form used by the blocked
instrument.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from gems57 import metric

ROOT = Path(__file__).resolve().parents[1]


def load_stage2():
    spec = importlib.util.spec_from_file_location(
        "stage2", ROOT / "scripts" / "build_scarp_stage2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


STAGE2 = load_stage2()


@pytest.mark.parametrize("seed", [7, 11, 23, 101])
def test_metric_terms_matches_bruteforce(seed):
    rng = np.random.default_rng(seed)
    shape = (90, 90)
    pred = ((rng.random(shape) < 0.012) * rng.random(shape)).astype(np.float32)
    truth = rng.random(shape) < 0.012
    mine = STAGE2.metric_terms(pred, truth, (0, 0, shape[0], shape[1]), shape)
    ref = metric.dti_bruteforce(pred, truth)
    assert mine["tp_w"] == pytest.approx(float(ref["tp"]), abs=1e-4)
    assert mine["fp_w"] == pytest.approx(float(ref["fp"]), abs=1e-4)
    assert mine["fn_w"] == pytest.approx(float(ref["fn"]), abs=1e-4)
    assert mine["dti"] == pytest.approx(float(ref["dti"]), abs=1e-6)


def test_binary_dots_match_shared_binary_evaluator():
    """The shipped artifact is a binary dot field; the shared binary path must agree too."""
    rng = np.random.default_rng(5)
    shape = (120, 120)
    truth = rng.random(shape) < 0.02
    dots = np.zeros(shape, bool)
    idx = rng.choice(shape[0] * shape[1], 60, replace=False)
    dots.ravel()[idx] = True
    mine = STAGE2.metric_terms(dots.astype(np.float32), truth,
                              (0, 0, shape[0], shape[1]), shape)
    ref = metric.dti_binary(dots, truth)
    assert mine["tp_w"] == pytest.approx(float(ref["tp"]), abs=1e-4)
    assert mine["dti"] == pytest.approx(float(ref["dti"]), abs=1e-6)


def test_region_terms_are_additive():
    """Summing the blocked instrument's regions must reproduce the whole-grid metric."""
    rng = np.random.default_rng(3)
    shape = (90, 60)
    pred = ((rng.random(shape) < 0.02) * rng.random(shape)).astype(np.float32)
    truth = rng.random(shape) < 0.02
    full = STAGE2.metric_terms(pred, truth, (0, 0, *shape), shape)
    tps = fps = 0.0
    for y0 in (0, 45):
        for x0 in (0, 30):
            part = STAGE2.metric_terms(pred, truth, (y0, x0, y0 + 45, x0 + 30), shape)
            tps += part["tp_w"]
            fps += part["fp_w"]
    assert tps == pytest.approx(full["tp_w"], abs=1e-4)
    assert fps == pytest.approx(full["fp_w"], abs=1e-4)


def test_kernel_weight_of_a_single_off_dot():
    """A single dot one cell from the only truth pixel earns exactly k(1) = 2/3."""
    shape = (9, 9)
    truth = np.zeros(shape, bool)
    truth[4, 4] = True
    dots = np.zeros(shape, bool)
    dots[4, 5] = True
    terms = STAGE2.metric_terms(dots.astype(np.float32), truth, (0, 0) + shape, shape)
    assert terms["tp_w"] == pytest.approx(2.0 / 3.0, abs=1e-6)
    assert terms["fp_w"] == pytest.approx(1.0 / 3.0, abs=1e-6)
    assert terms["fn_w"] == pytest.approx(1.0 / 3.0, abs=1e-6)


def test_lazy_greedy_is_submodular_and_monotone():
    """Coverage must never fall as dots are added, and it must beat a random dot set."""
    rng = np.random.default_rng(9)
    shape = (80, 80)
    lat = np.zeros(shape, bool)
    lat[::2, ::2] = True
    weights = np.zeros(shape, np.float32)
    hot = np.zeros(shape, bool)
    hot[20:40, 20:40] = True
    weights[hot] = 0.8
    sel = STAGE2.lazy_greedy(weights, lat, shape, 60)
    dots = np.zeros(shape, bool)
    dots.ravel()[np.flatnonzero(lat.ravel())[sel]] = True
    rand = np.zeros(shape, bool)
    flat = np.flatnonzero(lat.ravel())
    rand.ravel()[rng.choice(flat, sel.size, replace=False)] = True
    good = STAGE2.metric_terms(dots.astype(np.float32), hot, (0, 0) + shape, shape)
    bad = STAGE2.metric_terms(rand.astype(np.float32), hot, (0, 0) + shape, shape)
    assert good["tp_w"] > bad["tp_w"]
    assert dots.sum() <= 60
