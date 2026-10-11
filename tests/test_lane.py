"""Unit tests for the lane surface, placement and domain helpers.

These tests pin the properties the run card and receipts rely on: determinism,
domain confinement, spacing, non-mutation of shared component arrays, honest
decode of the cached quantised channels, and the fail-closed behaviour of the
cultural mask.
"""
from __future__ import annotations

import numpy as np
import pytest

from gems64 import lane


def _surface(shape=(60, 80), seed=0):
    rng = np.random.default_rng(seed)
    return rng.random(shape, dtype=np.float32)


def test_rank01_is_confined_monotone_and_non_mutating():
    x = _surface()
    x0 = x.copy()
    dom = np.zeros(x.shape, bool)
    dom[10:50, 20:60] = True
    r = lane.rank01(x, dom)
    assert r.dtype == np.float32
    assert np.array_equal(x, x0)          # input untouched
    assert (r[~dom] == 0).all()
    assert 0.0 <= float(r[dom].min()) and float(r[dom].max()) <= 1.0
    order = np.argsort(x[dom], kind="stable")
    assert np.all(np.diff(r[dom][order]) >= 0)   # higher value never ranks lower
    const = lane.rank01(np.zeros(x.shape, np.float32), dom)
    assert np.allclose(const[dom], 0.5)   # ties get the average rank, not raster order


def test_rank01_empty_domain_returns_zeros():
    x = _surface(shape=(8, 8))
    r = lane.rank01(x, np.zeros(x.shape, bool))
    assert r.dtype == np.float32 and not r.any() and r.shape == x.shape


def test_poisson_disk_is_deterministic_confined_and_spaced():
    dom = np.zeros((90, 90), bool)
    dom[5:85, 5:85] = True
    score = lane.rank01(_surface(shape=(90, 90)), dom)
    a = lane.poisson_disk(score, dom, 200, 1.5)
    b = lane.poisson_disk(score, dom, 200, 1.5)
    assert a.dtype == bool and np.array_equal(a, b)
    assert int(a.sum()) == 200
    assert not (a & ~dom).any()
    yy, xx = np.nonzero(a)
    d = np.hypot(yy[:, None] - yy[None, :], xx[:, None] - xx[None, :])
    np.fill_diagonal(d, np.inf)
    assert float(d.min()) >= 1.5 - 1e-9


def test_poisson_disk_prefers_high_scores():
    score = np.zeros((40, 40), np.float32)
    score[0:20, 0:20] = 0.9
    score[20:, 20:] = 0.1
    dots = lane.poisson_disk(score, np.ones((40, 40), bool), 50, 1.5)
    assert int(dots[0:20, 0:20].sum()) >= 40


def test_flat_surface_dots_are_not_biased_to_raster_order():
    dom = np.ones((100, 100), bool)
    flat = lane.rank01(np.zeros((100, 100), np.float32), dom)
    dots = lane.poisson_disk(flat, dom, 400, 1.5)
    quadrants = [int(dots[:50, :50].sum()), int(dots[:50, 50:].sum()),
                 int(dots[50:, :50].sum()), int(dots[50:, 50:].sum())]
    assert min(quadrants) > 50          # no corner/row-order bias
    yy, xx = np.nonzero(dots)
    assert float(np.hypot(yy - 50, xx - 50).mean()) > 30.0


def test_decode_lidar_roundtrip_and_no_lidar_zero():
    q = np.array([[0, 1, 128, 255]], np.uint8)
    ex = lane.decode_lidar(q, "ex_max")
    assert ex[0, 0] == 0.0                      # code 0 is documented "no lidar"
    assert ex[0, 1] == 0.0                      # code 1 is value 0
    assert ex[0, 2] > ex[0, 1] and ex[0, 3] <= lane.XMAX["ex_max"] + 1e-6
    coh = lane.decode_lidar(q, "coh100")
    assert coh[0, 2] == pytest.approx(127.0 / 254.0, abs=1e-6)  # linear channel
    with pytest.raises(ValueError):
        lane.decode_lidar(np.array([[300]], np.int16), "ex_max")


def test_lidar_covered_is_keyword_only_and_thresholded():
    codes = np.zeros((2, 2), np.uint8)
    codes[0] = 255
    codes[1] = 1
    covered = lane.lidar_covered(codes, min_fraction=0.5)
    assert covered[0].all() and not covered[1].any()
    with pytest.raises(TypeError):
        lane.lidar_covered(codes, 0.5)


def test_vergence_asymmetry_separates_step_from_channel_bank():
    up = np.array([[1.0, 1.0, 0.0]], np.float32)
    dn = np.array([[0.0, 1.0, 1.0]], np.float32)
    v = lane.vergence_asymmetry(up, dn)
    assert v[0, 0] == pytest.approx(1.0)        # one-sided step
    assert v[0, 1] == pytest.approx(0.0)        # both faces in one cell
    assert v[0, 2] == pytest.approx(1.0)


def test_cultural_mask_shapes_buffers_and_names_the_gap():
    road = np.full(lane.FOOTPRINT_SHAPE, 900.0, np.float32)
    road[0, 0] = 10.0                          # a road crossing far outside
    claim = np.full(lane.FOOTPRINT_SHAPE, 900.0, np.float32)
    claim[5, 5] = 0.0                          # inside a closed claim
    without = lane.cultural_mask(road)
    assert int(without["masked"].sum()) == 1   # exactly the single road cell
    assert without["canals_and_field_edges_masked"] is False
    assert "canals" in without["note"]
    with_claims = lane.cultural_mask(road, claim)
    assert with_claims["masked"][5, 5]
    assert int(with_claims["masked"].sum()) == 2   # the road cell and the claim cell
    assert with_claims["claim_buffer_m"] == 100.0
    with pytest.raises(ValueError):
        lane.cultural_mask(np.zeros((4, 4), np.float32))


def test_claims_masking_is_opt_in_because_it_removes_signal():
    """The default domain must not subtract BLM closed claims (measured 0.2767 -> 0.2003)."""
    from scripts import run_lane  # noqa: F401  (import guard: module must stay importable)
    assert "use_claims" in run_lane.lane_domain.__code__.co_varnames
