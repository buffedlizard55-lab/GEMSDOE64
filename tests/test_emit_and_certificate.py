"""Unit tests for the lane's emission baselines and the uniqueness certificate.

These are synthetic-only tests: they check the arithmetic and the fail-closed
behaviour of tools that later runs point at real rasters. No test here asserts
anything about competition data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import uniqueness           # noqa: E402
from gems64 import emit                 # noqa: E402


def _write(path: Path, array: np.ndarray) -> str:
    with rasterio.open(path, "w", driver="GTiff", height=array.shape[0], width=array.shape[1],
                       count=1, dtype="float32", crs="EPSG:32611",
                       transform=from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(array.astype("float32"), 1)
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_pack_respects_minimum_separation_and_budget():
    rng = np.random.default_rng(0)
    priority = rng.random((40, 40)).astype(np.float32)
    allowed = np.ones((40, 40), bool)
    dots = emit.poisson_disk_pack(priority, allowed, min_dist_px=3.0, max_dots=25)
    assert dots.sum() == 25
    coords = np.argwhere(dots)
    for i, (y, x) in enumerate(coords):
        d = np.hypot(coords[:i, 0] - y, coords[:i, 1] - x)
        assert d.min(initial=np.inf) >= 3.0


def test_pack_never_leaves_the_allowed_domain():
    priority = np.ones((30, 30), np.float32)
    allowed = np.zeros((30, 30), bool)
    allowed[5:15, 5:25] = True
    dots = emit.poisson_disk_pack(priority, allowed, min_dist_px=2.8)
    assert not (dots & ~allowed).any()
    assert dots.sum() > 0


def test_mclp_baseline_is_deterministic_and_capped():
    rng = np.random.default_rng(1)
    priority = rng.random((30, 30)).astype(np.float32)
    allowed = np.ones((30, 30), bool)
    a, info_a = emit.greedy_surface_coverage(priority, allowed, max_dots=12, cover_quantile=50)
    b, info_b = emit.greedy_surface_coverage(priority, allowed, max_dots=12, cover_quantile=50)
    assert np.array_equal(a, b)
    assert a.sum() <= 12
    assert info_a["accepted"] == int(a.sum()) == info_b["accepted"]
    assert not (a & ~allowed).any()


def test_mclp_places_dots_where_the_priority_is():
    priority = np.zeros((60, 60), np.float32)
    priority[10, 10] = 1.0
    priority[40, 40] = 0.5
    allowed = np.ones((60, 60), bool)
    dots, info = emit.greedy_surface_coverage(priority, allowed, max_dots=2, cover_quantile=90)
    coords = set(map(tuple, np.argwhere(dots)))
    assert (10, 10) in coords and (40, 40) in coords
    assert info["iteration_cap_hit"] is False


def _certificate(tmp_path: Path, priors, mine):
    index = dict(schema="test", scope="synthetic",
                 rasters=[dict(cache_file=str(p), sha256=s, repo_first="TEST",
                               submission=Path(p).name) for p, s in priors])
    return uniqueness.dense_prior_certificate(
        mine, registry_index=index, footprint=np.ones_like(mine, bool),
        control_draws=4, subsample=5_000, file_sha256=None)


def test_certificate_flags_a_dense_prior_as_unsatisfiable(tmp_path):
    dense = np.ones((50, 50), np.float32)
    p = tmp_path / "dense.tif"
    _write(p, dense)
    mine = np.zeros((50, 50), np.float32)
    mine[10, 10] = mine[20, 20] = 1.0
    cert = _certificate(tmp_path, [(p, _write(p, dense))], mine)
    assert cert["dense_priors"], "a whole-footprint prior must be classified as dense"
    assert cert["dense_priors"][0]["my_dots_within_3px_of_theirs"] > 0.70
    assert cert["dense_priors"][0]["control_overlap_min"] >= 0.70
    assert cert["unsatisfiable_criteria"] == ["dense.tif"]
    assert cert["literal_verdict_unique"] is False


def test_certificate_passes_for_a_disjoint_sparse_registry(tmp_path):
    other = np.zeros((50, 50), np.float32)
    other[40:45, 40:45] = 1.0
    p = tmp_path / "sparse.tif"
    digest = _write(p, other)
    mine = np.zeros((50, 50), np.float32)
    mine[5, 5] = mine[6, 9] = 1.0
    cert = _certificate(tmp_path, [(p, digest)], mine)
    assert cert["dense_priors"] == []
    assert cert["worst_overlap_informative"] == 0.0
    assert cert["literal_verdict_unique"] is True
    assert cert["diagnostic_verdict_unique"] is True
    assert cert["byte_and_pixel_unique"] is True


def test_certificate_refuses_an_empty_candidate(tmp_path):
    p = tmp_path / "sparse.tif"
    digest = _write(p, np.ones((20, 20), np.float32))
    with pytest.raises(ValueError):
        _certificate(tmp_path, [(p, digest)], np.zeros((20, 20), np.float32))
