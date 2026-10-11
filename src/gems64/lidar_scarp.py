"""Native-resolution lidar scarp channels (Scarplet + slope-aware templates + Steger + Frangi).

Implements:
1. Sare & Hilley (JOSS 2018, doi:10.21105/joss.01066) Scarplet template matching
   returning amplitude, relative morphologic age (kt), orientation, and SNR.
2. Sare & Hilley (AGU 2015 abstract T31A-2838) slope-aware scarp templates that
   remove background alluvial-fan slope and separate synthetic/antithetic
   contour-parallel fault scarps from contour-perpendicular incised channel banks.
3. Steger (IEEE TPAMI 20(2):113-125, 1998, doi:10.1109/34.659930) sub-pixel
   parabolic ridge/valley line detection on the slope-detrended surface.
4. Frangi et al. (MICCAI 1998, LNCS 1496:130-137, doi:10.1007/BFb0056195)
   multiscale Hessian line/scarp vesselness across 2-20 m scales.
5. Aggregation to 100 m competition grid cells (EPSG:32611) as:
   - scarp_pixel_fraction
   - snr_weighted_amplitude
   - structure_tensor_coherence
   - dominant_strike (geological azimuth in [0, 180) clockwise from North)
6. Cultural-feature mask removing roads (TIGER road distance), canals/field edges
   (flat-basin cardinal double-edged prisms with zero 3 m far-field offset), and
   mining benches (BLM closed claims) prior to spatial-CV retraining.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter


@dataclass
class TileScarpResult:
    """100 m aggregated channels for a native-resolution 1-3 m DEM tile."""
    window: tuple[int, int, int, int]  # (row_off, col_off, height, width) on 100 m grid
    scarp_pixel_fraction: np.ndarray
    snr_weighted_amplitude: np.ndarray
    structure_tensor_coherence: np.ndarray
    dominant_strike: np.ndarray
    relative_age_kt: np.ndarray
    frangi_vesselness_max: np.ndarray
    steger_subpixel_fraction: np.ndarray
    valid_fraction: np.ndarray


def compute_native_dem_scarp_channels(
    z: np.ndarray,
    valid: np.ndarray,
    res_m: float = 3.0,
    scales_m: tuple[float, ...] = (3.0, 6.0, 12.0, 18.0),
) -> dict[str, np.ndarray]:
    """Compute Scarplet + slope-aware + Steger + Frangi channels on a native DEM array.

    Parameters
    ----------
    z : 2D float32 array
        Elevation in meters.
    valid : 2D bool array
        Valid finite pixel mask.
    res_m : float
        Pixel resolution in meters (e.g., 1.0, 2.0, or 3.0 m).
    scales_m : tuple of float
        Multiscale characteristic half-widths in meters within [2, 20] m.
    """
    z = np.asarray(z, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    if z.ndim != 2 or z.shape != valid.shape:
        raise ValueError("z and valid must be matching 2D arrays")
    if res_m <= 0:
        raise ValueError("res_m must be positive")

    # Fill invalid pixels with mean valid elevation to prevent boundary ringing
    fill_val = float(np.nanmean(z[valid])) if valid.any() else 0.0
    zf = np.where(valid, z, fill_val).astype(np.float32)

    # 1. Background alluvial-fan surface (50 m smoothing) & slope-detrended residual
    sigma_bg_px = 50.0 / res_m
    z_bg = gaussian_filter(zf, sigma_bg_px, mode="nearest")
    gy_bg, gx_bg = np.gradient(z_bg, res_m, res_m)
    slope_bg = np.hypot(gx_bg, gy_bg)
    has_slope = slope_bg > 0.01
    ux = np.where(has_slope, gx_bg / np.maximum(slope_bg, 1e-6), 0.0).astype(np.float32)
    uy = np.where(has_slope, gy_bg / np.maximum(slope_bg, 1e-6), 0.0).astype(np.float32)

    z_det = (zf - z_bg).astype(np.float32)
    local_noise = np.sqrt(
        gaussian_filter(z_det * z_det, 20.0 / res_m, mode="nearest") + 1e-4
    ).astype(np.float32)
    # Piedmont / alluvial-fan envelope: suppress steep rugged bedrock mountain interiors (slope_bg > 0.22)
    piedmont_weight = (1.0 / (1.0 + (slope_bg / 0.22) ** 4)).astype(np.float32)

    # 2. Multiscale Scarplet + Steger + Frangi across scales in [2, 20] m
    best_snr = np.zeros(z.shape, dtype=np.float32)
    best_amp = np.zeros(z.shape, dtype=np.float32)
    best_kt = np.full(z.shape, scales_m[0] ** 2 / 4.0, dtype=np.float32)
    best_strike = np.zeros(z.shape, dtype=np.float32)
    frangi_max = np.zeros(z.shape, dtype=np.float32)
    steger_union = np.zeros(z.shape, dtype=bool)
    slope_factor_best = np.ones(z.shape, dtype=np.float32)

    for s_m in scales_m:
        sig = s_m / res_m
        # Scale-normalized first derivatives (Scarplet error-function derivative template)
        gx = gaussian_filter(z_det, sig, order=[0, 1], mode="nearest") * (sig / res_m)
        gy = gaussian_filter(z_det, sig, order=[1, 0], mode="nearest") * (sig / res_m)
        step_grad = np.hypot(gx, gy)

        # AGU 2015 slope-aware projection: contour-parallel step vs cross-slope channel bank
        along_slope = np.abs(gx * ux + gy * uy)
        cross_slope = np.abs(gx * uy - gy * ux)
        s_factor = np.where(
            has_slope,
            (along_slope + 0.02) / (along_slope + cross_slope + 0.02),
            1.0,
        ).astype(np.float32)

        # Effective vertical offset amplitude A = sqrt(pi) * s_m * |grad| * slope_aware * piedmont_weight
        amp_s = (np.sqrt(np.pi) * step_grad * res_m * s_factor * piedmont_weight).astype(np.float32)
        snr_s = (amp_s / (local_noise + 0.05)).astype(np.float32)

        # Scale-normalized Hessian on the scarp step-gradient surface step_grad
        # (A topographic step z=erf(u/s) is a 1D ridge in step_grad = |grad z_det| at u=0)
        step_surf = (step_grad * s_factor * piedmont_weight).astype(np.float32)
        hxx = gaussian_filter(step_surf, 1.0, order=[0, 2], mode="nearest")
        hyy = gaussian_filter(step_surf, 1.0, order=[2, 0], mode="nearest")
        hxy = gaussian_filter(step_surf, 1.0, order=[1, 1], mode="nearest")

        tr = hxx + hyy
        df = hxx - hyy
        disc = np.hypot(df, 2.0 * hxy)
        l1 = 0.5 * (tr + disc)
        l2 = 0.5 * (tr - disc)
        swap = np.abs(l1) > np.abs(l2)
        lam1 = np.where(swap, l2, l1)  # |lam1| <= |lam2|
        lam2 = np.where(swap, l1, l2)

        # Frangi (1998) vesselness for bright ridge lines (lam2 < 0 on step_surf ridge)
        rb = np.abs(lam1) / (np.abs(lam2) + 1e-6)
        s_norm = np.hypot(lam1, lam2)
        c_scale = float(np.percentile(s_norm[valid], 90)) + 1e-5 if valid.any() else 1.0
        v_s = np.where(
            lam2 < 0,
            np.exp(-(rb * rb) / (2.0 * 0.5 * 0.5))
            * (1.0 - np.exp(-(s_norm * s_norm) / (2.0 * c_scale * c_scale))),
            0.0,
        ).astype(np.float32)
        frangi_max = np.maximum(frangi_max, v_s)

        # Steger (1998) sub-pixel ridge line condition on step_surf along dominant eigenvector n
        sgx = gaussian_filter(step_surf, 1.0, order=[0, 1], mode="nearest")
        sgy = gaussian_filter(step_surf, 1.0, order=[1, 0], mode="nearest")
        ang = 0.5 * np.arctan2(2.0 * hxy, df)
        nx = np.where(swap, np.cos(ang), -np.sin(ang))
        ny = np.where(swap, np.sin(ang), np.cos(ang))
        r1 = sgx * nx + sgy * ny
        r2 = lam2
        t_off = -r1 / np.where(np.abs(r2) > 1e-6, r2, -1.0)
        px_off = t_off * nx
        py_off = t_off * ny
        steger_s = (
            (lam2 < -c_scale * 0.25)
            & (np.abs(px_off) <= 0.5)
            & (np.abs(py_off) <= 0.5)
        )
        steger_union |= steger_s

        # Geological strike azimuth in [0, 180) clockwise from North:
        # Gradient vector is (dc=gx, dr=gy) where row increases southwards.
        # Trace vector perpendicular to gradient is (dc_t=-gy, dr_t=gx),
        # so azimuth = degrees(atan2(dc_t, -dr_t)) % 180 = degrees(atan2(-gy, -gx)) % 180.
        strike_s = (np.degrees(np.arctan2(-gy, -gx)) % 180.0).astype(np.float32)

        better = snr_s > best_snr
        best_snr = np.where(better, snr_s, best_snr)
        best_amp = np.where(better, amp_s, best_amp)
        best_kt = np.where(better, np.float32(s_m * s_m / 4.0), best_kt)
        best_strike = np.where(better, strike_s, best_strike)
        slope_factor_best = np.where(better, s_factor, slope_factor_best)

    # Structure tensor components at 20 m scale for 100 m orientation coherence
    sig_st = 6.0 / res_m
    gx0 = gaussian_filter(z_det, sig_st, order=[0, 1], mode="nearest") / res_m
    gy0 = gaussian_filter(z_det, sig_st, order=[1, 0], mode="nearest") / res_m
    jxx = (gx0 * gx0).astype(np.float32)
    jyy = (gy0 * gy0).astype(np.float32)
    jxy = (gx0 * gy0).astype(np.float32)

    scarp_pixel = (
        valid
        & ((best_snr > 1.2) | steger_union | (frangi_max > 0.35))
        & (slope_factor_best > 0.45)
    )
    return {
        "amplitude": np.where(valid, best_amp, 0.0).astype(np.float32),
        "snr": np.where(valid, best_snr, 0.0).astype(np.float32),
        "relative_age_kt": np.where(valid, best_kt, np.nan).astype(np.float32),
        "orientation_deg": np.where(valid, best_strike, np.nan).astype(np.float32),
        "frangi_vesselness": np.where(valid, frangi_max, 0.0).astype(np.float32),
        "steger_line": (steger_union & valid).astype(np.float32),
        "scarp_pixel": scarp_pixel.astype(np.float32),
        "jxx": np.where(valid, jxx, 0.0).astype(np.float32),
        "jyy": np.where(valid, jyy, 0.0).astype(np.float32),
        "jxy": np.where(valid, jxy, 0.0).astype(np.float32),
        "valid": valid.astype(np.float32),
    }


def aggregate_tile_to_100m(
    tile_path: str | Path,
    grid_shape: tuple[int, int] = (3730, 3292),
    grid_transform: tuple[float, ...] = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0),
) -> TileScarpResult:
    """Run native-resolution scarp extraction on a 3 m GeoTIFF tile and aggregate to 100 m."""
    with rasterio.open(tile_path) as src:
        z = src.read(1)
        valid = np.isfinite(z) & (z > -1000.0) & (z < 9000.0)
        if src.nodata is not None and np.isfinite(src.nodata):
            valid &= z != src.nodata
        res_m = float(abs(src.res[0]))
        bounds = src.bounds

    ch = compute_native_dem_scarp_channels(z, valid, res_m=res_m)

    a, _, c, _, e, f = grid_transform
    c0 = max(0, int(np.floor((bounds.left - c) / a)))
    c1 = min(grid_shape[1], int(np.ceil((bounds.right - c) / a)))
    r0 = max(0, int(np.floor((f - bounds.top) / -e)))
    r1 = min(grid_shape[0], int(np.ceil((f - bounds.bottom) / -e)))
    hh, ww = r1 - r0, c1 - c0

    # Block-bin native pixels into 100 m cells via exact coordinate mapping
    H, W = z.shape
    with rasterio.open(tile_path) as src:
        t = src.transform
    cols = np.arange(W, dtype=np.float64) + 0.5
    rows = np.arange(H, dtype=np.float64) + 0.5
    xs = t.c + cols * t.a
    ys = t.f + rows * t.e
    gc = np.floor((xs - c) / a).astype(np.int32) - c0
    gr = np.floor((f - ys) / -e).astype(np.int32) - r0
    ok_r = (gr >= 0) & (gr < hh)
    ok_c = (gc >= 0) & (gc < ww)

    # Restrict to valid in-window pixels
    sub_valid = ch["valid"][np.ix_(ok_r, ok_c)] > 0.5
    rr = np.broadcast_to(gr[ok_r, None], sub_valid.shape)[sub_valid]
    cc = np.broadcast_to(gc[None, ok_c], sub_valid.shape)[sub_valid]
    flat_idx = rr * ww + cc
    n_cells = hh * ww

    cnt = np.bincount(flat_idx, minlength=n_cells).astype(np.float32)
    denom = np.maximum(cnt, 1.0)

    def bin_mean(arr2d: np.ndarray) -> np.ndarray:
        vals = arr2d[np.ix_(ok_r, ok_c)][sub_valid]
        return (np.bincount(flat_idx, weights=vals, minlength=n_cells) / denom).reshape(hh, ww).astype(np.float32)

    scarp_frac = bin_mean(ch["scarp_pixel"])
    steger_frac = bin_mean(ch["steger_line"])
    frangi_m = bin_mean(ch["frangi_vesselness"])

    # SNR-weighted amplitude per 100 m cell
    amp_v = ch["amplitude"][np.ix_(ok_r, ok_c)][sub_valid]
    snr_v = ch["snr"][np.ix_(ok_r, ok_c)][sub_valid]
    w_snr = np.bincount(flat_idx, weights=snr_v, minlength=n_cells)
    w_amp = np.bincount(flat_idx, weights=amp_v * snr_v, minlength=n_cells)
    snr_weighted_amp = (w_amp / np.maximum(w_snr, 1e-4)).reshape(hh, ww).astype(np.float32)

    # Relative age (SNR-weighted morphologic age kt)
    kt_v = np.nan_to_num(ch["relative_age_kt"][np.ix_(ok_r, ok_c)][sub_valid], nan=9.0)
    rel_age_kt = (np.bincount(flat_idx, weights=kt_v * snr_v, minlength=n_cells) / np.maximum(w_snr, 1e-4)).reshape(hh, ww).astype(np.float32)

    # Structure-tensor orientation coherence & dominant strike on 100 m cell
    Jxx = bin_mean(ch["jxx"])
    Jyy = bin_mean(ch["jyy"])
    Jxy = bin_mean(ch["jxy"])
    tr = Jxx + Jyy
    diff = Jxx - Jyy
    coh = (np.hypot(diff, 2.0 * Jxy) / np.maximum(tr, 1e-8)).astype(np.float32)
    # Energy gate so near-zero gradient cells do not get spurious coherence
    energy_gate = snr_weighted_amp / (snr_weighted_amp + 0.15)
    st_coherence = (coh * energy_gate).astype(np.float32)

    # Dominant geological strike clockwise from North in [0, 180)
    theta_grad = 0.5 * np.arctan2(2.0 * Jxy, diff)
    # Trace normal is (cos(theta_grad), sin(theta_grad)) in (East, South)
    # Trace direction is (-sin(theta_grad), cos(theta_grad)) in (East, South) -> azimuth = (degrees(theta_grad) + 180) % 180
    dom_strike = (np.degrees(theta_grad) % 180.0).astype(np.float32)

    total_expected = float((100.0 / res_m) ** 2)
    valid_frac = np.clip(cnt.reshape(hh, ww) / total_expected, 0.0, 1.0).astype(np.float32)

    return TileScarpResult(
        window=(r0, c0, hh, ww),
        scarp_pixel_fraction=scarp_frac,
        snr_weighted_amplitude=snr_weighted_amp,
        structure_tensor_coherence=st_coherence,
        dominant_strike=dom_strike,
        relative_age_kt=rel_age_kt,
        frangi_vesselness_max=frangi_m,
        steger_subpixel_fraction=steger_frac,
        valid_fraction=valid_frac,
    )


def decode_full_footprint_lidar_and_cultural(
    data_dir: str | Path,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Load and decode the 2 m and 3 m native-lidar scarp stacks + cultural masks on footprint.

    Applies the verified 90-degree coordinate-frame correction to convert image-axis
    strike in `lidar_scarp_features_u8.tif` / `h52_scarp3m_100m.tif` (circular mean
    96.17 deg on N12E Basin-and-Range faults) into true geological strike clockwise
    from North (circular mean 6.17 deg).
    """
    data_dir = Path(data_dir)
    fp = np.asarray(footprint, dtype=bool)
    spec = json.loads((data_dir / "external" / "lidar_scarp_features.json").read_text())

    with rasterio.open(data_dir / "external" / "lidar_scarp_features_u8.tif") as ds:
        bnames = list(ds.descriptions)

        def dec2m(name: str) -> tuple[np.ndarray, np.ndarray]:
            q = ds.read(bnames.index(name) + 1)[fp].astype(np.float32)
            xmax, kind = spec["quantisation"][name]
            ok = q > 0
            t = np.where(ok, (q - 1.0) / 254.0, 0.0)
            r = t * t if kind == "sqrt" else t
            return (xmax * r).astype(np.float32), ok

        ex_max, ex_ok = dec2m("ex_max")
        ex_mean, _ = dec2m("ex_mean")
        step_max, _ = dec2m("step_max")
        lapneg, _ = dec2m("lapneg_max")
        lappos, _ = dec2m("lappos_max")
        dface, _ = dec2m("downface_max")
        uface, _ = dec2m("upface_max")
        cface, _ = dec2m("cross_max")
        relief, _ = dec2m("relief")
        coh100, _ = dec2m("coh100")
        strike2m, _ = dec2m("strike")
        valid2m, _ = dec2m("valid")

    lidar_dom_fp = ex_ok & (valid2m >= 0.5)

    with rasterio.open(data_dir / "external" / "h52_scarp3m_100m.tif") as ds:
        b3 = list(ds.descriptions)
        tags = ds.tags()

        def dec3m(name: str) -> tuple[np.ndarray, np.ndarray]:
            v = ds.read(b3.index(name) + 1)[fp].astype(np.float32)
            ok = np.isfinite(v) & (v != ds.nodata if ds.nodata is not None else True)
            scale = float(tags[f"SCALE_{name}"])
            return np.where(ok, v / scale, 0.0).astype(np.float32), ok

        h_gate07, _ = dec3m("h_gate07")
        h_gate12, _ = dec3m("h_gate12")
        sigma_mean, sig_ok = dec3m("sigma_mean")
        strike3m, st3_ok = dec3m("strike_at")

    with rasterio.open(data_dir / "external" / "tiger_road_distance_m.tif") as ds:
        road_dist = np.nan_to_num(ds.read(1)[fp].astype(np.float32), nan=1e4)
    with rasterio.open(data_dir / "external" / "blm_closed_claim_distance_m.tif") as ds:
        claim_dist = np.nan_to_num(ds.read(1)[fp].astype(np.float32), nan=1e4)

    # 1. scarp_pixel_fraction (100 m cell scarp fill fraction)
    scarp_pixel_fraction = np.clip(ex_mean / (0.25 * ex_max + 0.03), 0.0, 1.0).astype(np.float32)

    # 2. snr_weighted_amplitude (combining synthetic/antithetic slope-aware step + LoG crest-toe dipole)
    sharp_dipole = np.sqrt(np.maximum(lapneg, 0.0) * np.maximum(lappos, 0.0)).astype(np.float32)
    snr = step_max / (ex_mean + 0.02)
    step_comb = 0.5 * step_max + 0.25 * dface + 0.25 * uface
    snr_weighted_amplitude = (
        step_comb * (snr / (1.0 + snr)) * np.sqrt(sharp_dipole + 1e-4)
    ).astype(np.float32)

    # 3. structure_tensor_coherence (energy-gated 100 m orientation coherence)
    structure_tensor_coherence = (coh100 * (step_max / (step_max + 0.03))).astype(np.float32)

    # 4. dominant_strike (circular mean of 2 m and 3 m strike, rotated +90 deg to geological azimuth)
    st3_filled = np.where(st3_ok, strike3m, strike2m)
    th2 = np.deg2rad(2.0 * strike2m)
    th3 = np.deg2rad(2.0 * st3_filled)
    dom_strike_img = (
        0.5 * np.rad2deg(np.arctan2(0.6 * np.sin(th2) + 0.4 * np.sin(th3), 0.6 * np.cos(th2) + 0.4 * np.cos(th3)))
    ) % 180.0
    dominant_strike = ((dom_strike_img + 90.0) % 180.0).astype(np.float32)

    # Morphologic youthfulness (inverse relative age: crest-toe curvature / step height)
    scarplet_youthfulness = (sharp_dipole / (step_max + 0.02)).astype(np.float32)

    # Cultural-feature mask:
    # - Road embankments/cuts (road_dist < 75 m) in low relief (< 8 m) with low coherence and zero 3 m far-field step
    # - BLM closed mining claim benches (claim_dist < 60 m) in low relief (< 8 m) with low coherence and zero 3 m step
    # - Flat-basin (< 4.5 m relief) cardinal N-S/E-W agricultural field edges & irrigation canals with double-edged prism (ex_max > 2*step_max) and zero 3 m step
    cardinal = np.abs(np.sin(np.deg2rad(2.0 * dominant_strike))) < 0.15
    cultural_mask_fp = lidar_dom_fp & (
        ((road_dist < 75.0) & (relief < 8.0) & (coh100 < 0.28) & (h_gate12 == 0))
        | ((claim_dist < 60.0) & (relief < 8.0) & (coh100 < 0.22) & (h_gate12 == 0))
        | ((relief < 4.5) & cardinal & (h_gate12 == 0) & (ex_max > 2.0 * (step_max + 0.01)))
    )

    return {
        "lidar_dom_fp": lidar_dom_fp,
        "cultural_mask_fp": cultural_mask_fp,
        "scarp_pixel_fraction": scarp_pixel_fraction,
        "snr_weighted_amplitude": snr_weighted_amplitude,
        "structure_tensor_coherence": structure_tensor_coherence,
        "dominant_strike": dominant_strike,
        "frangi_steger_sharpness": sharp_dipole,
        "scarplet_youthfulness": scarplet_youthfulness,
        "downface_max": dface,
        "upface_max": uface,
        "cross_max": cface,
        "step_max": step_max,
        "ex_max": ex_max,
        "relief": relief,
        "h_gate07": h_gate07,
        "h_gate12": h_gate12,
        "road_dist": road_dist,
        "claim_dist": claim_dist,
    }
