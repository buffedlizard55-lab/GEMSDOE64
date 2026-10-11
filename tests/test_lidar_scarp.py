from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.special import erf

from gems64.lidar_scarp import (
    scarplet_template_kernel,
    compute_native_scarplet_steger_frangi_tile,
    aggregate_tile_to_100m,
    build_cultural_feature_mask,
    select_nms_dots,
    format_normalized_submissions,
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_scarplet_template_kernel_antisymmetry_and_mask():
    w_sym, mask = scarplet_template_kernel(kt=4.5, length_m=60.0, angle_deg=0.0, dx=3.0)
    assert w_sym.ndim == 2
    assert mask.shape == w_sym.shape
    assert float(mask.sum()) > 10.0
    # Antisymmetric across x=0 when angle_deg=0.0
    assert np.allclose(w_sym, -w_sym[:, ::-1], atol=1e-5)
    assert np.isclose(float(w_sym.sum()), 0.0, atol=1e-5)


def test_native_scarplet_steger_frangi_recovers_synthetic_scarp_on_sloped_fan():
    # Synthetic 150x150 grid at 3m resolution -> 5x5 grid of 90m cells
    ny, nx = 150, 150
    dx = 3.0
    yy, xx = np.mgrid[:ny, :nx].astype(np.float32) * dx
    # Sloped alluvial fan (regional slope b0 = 0.04 in x and 0.02 in y) + N-S fault scarp at x = 225 m
    x0 = 225.0
    kt_true = 9.0
    throw_m = 2.5
    dem = 1200.0 + 0.04 * xx + 0.02 * yy + 0.5 * throw_m * erf((xx - x0) / np.sqrt(4.0 * kt_true)).astype(np.float32)

    native = compute_native_scarplet_steger_frangi_tile(
        dem, dx=dx, angles_deg=(0.0, 30.0, 60.0, 90.0, 120.0, 150.0), kt_values=(4.5, 9.0, 18.0), scales_m=(3.0, 6.0, 12.0)
    )
    agg = aggregate_tile_to_100m(native, out_shape=(5, 5))

    # Column 2 contains x in [180m, 270m], centered on x0 = 225m
    scarp_col_amp = float(np.mean(agg["snr_weighted_amplitude"][:, 2]))
    flank_col_amp = float(np.mean(agg["snr_weighted_amplitude"][:, [0, 4]]))
    assert scarp_col_amp > 2.5 * flank_col_amp

    scarp_col_sf = float(np.mean(agg["steger_frangi_score"][:, 2]))
    flank_col_sf = float(np.mean(agg["steger_frangi_score"][:, [0, 4]]))
    assert scarp_col_sf > 2.0 * flank_col_sf
    assert float(np.mean(agg["structure_tensor_coherence"][:, 2])) > 0.5


def test_cultural_feature_mask_identifies_roads_canals_and_field_edges():
    shape = (4, 4)
    dom = np.ones(shape, dtype=bool)
    d_road = np.full(shape, 2500.0, dtype=np.float32)
    d_road[0, 0] = 25.0  # on a TIGER road
    d_claim = np.full(shape, 5000.0, dtype=np.float32)
    d_claim[0, 1] = 50.0  # on a BLM mining claim
    relief2m = np.full(shape, 2.5, dtype=np.float32)
    curv_10m = np.full(shape, 0.08, dtype=np.float32)
    curv_10m[2, 2] = 0.85  # genuine tectonic bedrock/piedmont break
    upface = np.full(shape, 0.1, dtype=np.float32)
    downface = np.full(shape, 0.1, dtype=np.float32)
    cross = np.zeros(shape, dtype=np.float32)
    cross[1, 0] = 0.6  # cross-slope canal
    strike = np.full(shape, 37.0, dtype=np.float32)
    strike[1, 1] = 0.0  # N-S section line
    h12 = np.full(shape, 0.02, dtype=np.float32)
    h12[2, 2] = 0.75

    cm = build_cultural_feature_mask(
        dom=dom,
        d_road=d_road,
        d_claim=d_claim,
        relief2m=relief2m,
        curv_10m=curv_10m,
        upface=upface,
        downface=downface,
        cross=cross,
        dominant_strike=strike,
        h_gate12=h12,
    )
    assert cm["road_mask"][0, 0]
    assert cm["claim_mask"][0, 1]
    assert cm["canal_mask"][1, 0]
    assert cm["field_mask"][1, 1]
    assert cm["cultural_mask"][0, 0]
    assert cm["cultural_mask"][0, 1]
    assert cm["cultural_mask"][1, 0]
    assert cm["cultural_mask"][1, 1]
    assert not cm["cultural_mask"][2, 2]


def test_nms_and_submission_normalization_contract():
    shape = (20, 20)
    rr, cc = np.indices(shape, dtype=np.float32)
    surf = np.sin(rr * 1.7) * np.cos(cc * 1.9) + 0.01 * rr + 0.005 * cc
    fp = np.ones(shape, dtype=bool)
    fp[0, :] = False  # outside footprint
    cat = np.zeros(shape, dtype=bool)
    cat[10, 10] = True  # known catalogue fault

    dots = select_nms_dots(surf, fp & (~cat), budget=10, size=3)
    assert int(dots.sum()) == 10
    assert dots[10, 10] == 0.0
    assert not np.any(dots[0, :] > 0)

    pred_zeros, pred_nan = format_normalized_submissions(surf, dots > 0.5, fp)
    assert pred_zeros.dtype == np.float32
    assert pred_nan.dtype == np.float32
    assert not np.any(np.isnan(pred_zeros))
    assert float(pred_zeros.min()) == 0.0
    assert float(pred_zeros.max()) == 1.0
    assert int((pred_zeros > 0.5).sum()) == 10
    assert pred_zeros[10, 10] == 0.0
    assert np.all(np.isnan(pred_nan[~fp]))
    assert np.allclose(pred_zeros[fp], pred_nan[fp])


def test_generated_deliverable_matches_promoted_run_card():
    card = json.loads(Path("evidence/run_card.json").read_text())
    assert card["verdict"] == "promote"
    assert card["gate_passed"] is True
    assert card["download_allowed"] is True

    z_path = Path(card["raster_zeros_file"])
    n_path = Path(card["raster_nan_file"])
    assert z_path.is_file()
    assert n_path.is_file()
    assert _sha256(z_path) == card["raster_zeros_sha256"]
    assert _sha256(n_path) == card["raster_nan_sha256"]

    with rasterio.open(z_path) as ds_z, rasterio.open(n_path) as ds_n:
        assert ds_z.shape == (3730, 3292)
        assert ds_n.shape == (3730, 3292)
        assert str(ds_z.crs) == "EPSG:32611"
        assert str(ds_n.crs) == "EPSG:32611"
        arr_z = ds_z.read(1)
        arr_n = ds_n.read(1)
        assert arr_z.dtype == np.float32
        assert arr_n.dtype == np.float32
        assert int(np.isnan(arr_z).sum()) == 0
        assert float(arr_z.min()) == 0.0
        assert float(arr_z.max()) == 1.0
        assert int((arr_z > 0.5).sum()) == 45000
        assert int(np.isnan(arr_n).sum()) == 7111787
        valid = ~np.isnan(arr_n)
        assert int(valid.sum()) == 5167373
        assert np.allclose(arr_z[valid], arr_n[valid])
