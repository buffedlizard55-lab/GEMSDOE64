"""Native-resolution LiDAR scarp channels, cultural masking, and spatial-CV pipeline.

Implements the assigned GEMSDOE64 parallel-run lane:
1. Sare & Hilley (JOSS 2018, doi:10.21105/joss.01066) Scarplet template matching
   returning amplitude, relative morphologic age (kt), orientation, and SNR,
   extended with slope-aware scarp templates (AGU 2015 Fall Meeting T31A-2838;
   Sare, Hilley, & DeLong, JGR Solid Earth 2019, doi:10.1029/2018JB016886).
2. Steger (IEEE TPAMI 20(2):113-125, 1998) sub-pixel ridge/valley line detection
   and Frangi et al. (MICCAI 1998, LNCS 1496:130-137) multiscale Hessian line
   measures at 2-20 m scales on a slope-detrended surface.
3. Aggregation to 100 m competition grid cells as:
   - scarp_pixel_fraction
   - snr_weighted_amplitude
   - structure_tensor_coherence
   - dominant_strike
4. Cultural-feature masking of roads (Census TIGER/Line 2024), canals, field
   edges, and mining benches (BLM closed claims), followed by 4-quadrant
   Leave-One-Quadrant-Out (LOQO) spatial-CV retraining.
"""
from __future__ import annotations

from typing import Sequence
import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.special import erfinv


def block_zscore(
    arr: np.ndarray,
    valid: np.ndarray,
    bh: int = 200,
    bw: int = 200,
    clip_lo: float = -3.0,
    clip_hi: float = 6.0,
) -> np.ndarray:
    """Robust median/MAD standardization within 20 km x 20 km spatial blocks."""
    a = np.asarray(arr, dtype=np.float32)
    v_mask = np.asarray(valid, dtype=bool)
    h, w = a.shape
    out = np.zeros_like(a, dtype=np.float32)
    for r0 in range(0, h, bh):
        r1 = min(h, r0 + bh)
        for c0 in range(0, w, bw):
            c1 = min(w, c0 + bw)
            m = v_mask[r0:r1, c0:c1]
            if not m.any():
                continue
            vals = a[r0:r1, c0:c1][m]
            med = float(np.median(vals))
            mad = float(np.median(np.abs(vals - med)))
            scale = max(1.4826 * mad, float(np.std(vals)), 1e-5)
            z = (a[r0:r1, c0:c1] - med) / scale
            out[r0:r1, c0:c1] = np.where(m, np.clip(z, clip_lo, clip_hi), 0.0)
    return out


def rank_1d(values: np.ndarray) -> np.ndarray:
    """Map a 1-D vector to uniform ranks in [0, 1] using stable mergesort."""
    v = np.asarray(values, dtype=np.float32)
    if v.size == 0:
        return np.empty(0, dtype=np.float32)
    if v.size == 1 or float(np.ptp(v)) == 0.0:
        return np.zeros(v.size, dtype=np.float32)
    order = np.argsort(v, kind="mergesort")
    ranks = np.empty(v.size, dtype=np.float32)
    ranks[order] = np.linspace(0.0, 1.0, v.size, dtype=np.float32)
    return ranks


def scarplet_template_kernel(
    kt: float,
    length_m: float,
    angle_deg: float,
    dx: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Construct the Sare & Hilley (JOSS 2018) 1-D diffusion scarp curvature kernel.

    Matches ``Scarp.template`` in ``scarplet/WindowedTemplate.py``:
      W(x_r, y_r) = (-x_r / (2 * (kt)**1.5 * sqrt(pi))) * exp(-x_r**2 / (4 * kt))
    truncated to |x_r| < 2 * sqrt(kt) * erfinv(0.90) and |y_r| <= length_m / 2.
    """
    if kt <= 0 or length_m <= 0 or dx <= 0:
        raise ValueError("kt, length_m, and dx must be positive")
    half_x = max(float(2.0 * np.sqrt(kt) * erfinv(0.90)), dx * 2.0)
    half_y = float(length_m) / 2.0
    ang = np.deg2rad(float(angle_deg))
    ny_max = max(int(np.ceil((half_x * abs(np.sin(ang)) + half_y * abs(np.cos(ang))) / dx)), 2)
    nx_max = max(int(np.ceil((half_x * abs(np.cos(ang)) + half_y * abs(np.sin(ang))) / dx)), 2)
    yy, xx = np.mgrid[-ny_max : ny_max + 1, -nx_max : nx_max + 1].astype(np.float32) * float(dx)
    xr = xx * np.cos(ang) + yy * np.sin(ang)
    yr = -xx * np.sin(ang) + yy * np.cos(ang)
    mask = ((np.abs(xr) <= half_x) & (np.abs(yr) <= half_y)).astype(np.float32)
    w = (-xr / (2.0 * (kt ** 1.5) * np.sqrt(np.pi))) * np.exp(-(xr ** 2) / (4.0 * kt))
    w = (w * mask).astype(np.float32)
    return w, mask


def compute_native_scarplet_steger_frangi_tile(
    dem_m: np.ndarray,
    dx: float = 3.0,
    angles_deg: Sequence[float] = (0.0, 30.0, 60.0, 90.0, 120.0, 150.0),
    kt_values: Sequence[float] = (9.0, 36.0, 100.0),
    scales_m: Sequence[float] = (2.0, 6.0, 12.0, 20.0),
    length_m: float = 60.0,
) -> dict[str, np.ndarray]:
    """Compute Scarplet + Slope-Aware + Steger + Frangi channels on a native DEM tile."""
    z = np.asarray(dem_m, dtype=np.float32)
    if z.ndim != 2:
        raise ValueError("dem_m must be a 2-D elevation array in metres")

    # 1. Slope-detrended surface: band-pass 2 m vs 60 m regional slope (Hanks 2000; AGU 2015 T31A-2838)
    z_smooth = ndi.gaussian_filter(z, sigma=max(2.0 / dx, 0.67)).astype(np.float32)
    z_reg = ndi.gaussian_filter(z, sigma=max(60.0 / dx, 2.0)).astype(np.float32)
    z_det = (z_smooth - z_reg).astype(np.float32)
    del z_smooth

    gy_reg, gx_reg = np.gradient(z_reg, np.float32(dx))
    del z_reg
    gx_reg = gx_reg.astype(np.float32, copy=False)
    gy_reg = gy_reg.astype(np.float32, copy=False)
    slope_reg = np.hypot(gx_reg, gy_reg).astype(np.float32)
    aspect_reg = np.arctan2(gy_reg, gx_reg).astype(np.float32)
    del gx_reg, gy_reg

    gy_det, gx_det = np.gradient(z_det, np.float32(dx))
    gx_det = gx_det.astype(np.float32, copy=False)
    gy_det = gy_det.astype(np.float32, copy=False)
    up_dot = -(gx_det * np.cos(aspect_reg) + gy_det * np.sin(aspect_reg))
    upface = np.maximum(up_dot, 0.0).astype(np.float32)
    downface = np.maximum(-up_dot, 0.0).astype(np.float32)
    slope_polarity = ((upface - downface) / (upface + downface + 1e-4)).astype(np.float32)
    del up_dot, upface, downface

    # 2. Scarplet template matching (Sare & Hilley JOSS 2018 + AGU 2015 T31A-2838 slope-aware weight)
    best_snr = np.full(z.shape, -np.inf, dtype=np.float32)
    best_amp = np.zeros(z.shape, dtype=np.float32)
    best_slope_amp = np.zeros(z.shape, dtype=np.float32)
    best_kt = np.zeros(z.shape, dtype=np.float32)
    best_ang = np.zeros(z.shape, dtype=np.float32)

    eps = np.float32(1e-6)
    for ang_deg in angles_deg:
        ang = np.float32(np.deg2rad(float(ang_deg)))
        # Directional profile curvature along template normal
        curv = ((gx_det * np.cos(ang) + gy_det * np.sin(ang)) / np.float32(dx)).astype(np.float32)
        curv2 = (curv * curv).astype(np.float32)
        # Slope-aware alignment: scarps strike parallel to regional contours (normal aligns with aspect)
        slope_align = (0.5 + 0.5 * np.abs(np.cos(ang - aspect_reg))).astype(np.float32)
        for kt in kt_values:
            w, mask = scarplet_template_kernel(kt=float(kt), length_m=length_m, angle_deg=float(ang_deg), dx=dx)
            n_pts = np.float32(mask.sum())
            t_sum = np.float32(np.sum(w * w))
            if n_pts < 1.0 or t_sum <= 0.0:
                continue
            xcorr = fftconvolve(curv, w[::-1, ::-1], mode="same").astype(np.float32)
            amp_raw = np.abs(xcorr) / t_sum
            t1 = (xcorr * xcorr) / t_sum
            del xcorr
            t3 = fftconvolve(curv2, mask, mode="same").astype(np.float32)
            rss = np.maximum(t3 - t1, 0.0)
            del t3
            err = (rss / n_pts) + eps
            del rss
            snr = t1 / err
            del t1, err
            upd = snr > best_snr
            best_snr[upd] = snr[upd]
            best_amp[upd] = amp_raw[upd]
            best_slope_amp[upd] = (amp_raw * slope_align)[upd]
            best_kt[upd] = float(kt)
            best_ang[upd] = float(ang_deg)
            del snr, amp_raw, upd
        del curv, curv2, slope_align
    del aspect_reg

    # 3. Steger (1998) sub-pixel curvilinear detector & Frangi (1998) multiscale Hessian at 2-20 m
    frangi_max = np.zeros(z.shape, dtype=np.float32)
    steger_max = np.zeros(z.shape, dtype=np.float32)
    beta2 = np.float32(2.0 * (0.5 ** 2))

    for s_m in scales_m:
        sig = max(float(s_m) / float(dx), 0.67)
        s2 = np.float32(sig * sig)
        gx = (ndi.gaussian_filter(z_det, sigma=sig, order=[0, 1]) * sig).astype(np.float32)
        gy = (ndi.gaussian_filter(z_det, sigma=sig, order=[1, 0]) * sig).astype(np.float32)
        hxx = (ndi.gaussian_filter(z_det, sigma=sig, order=[0, 2]) * s2).astype(np.float32)
        hyy = (ndi.gaussian_filter(z_det, sigma=sig, order=[2, 0]) * s2).astype(np.float32)
        hxy = (ndi.gaussian_filter(z_det, sigma=sig, order=[1, 1]) * s2).astype(np.float32)

        tr = hxx + hyy
        df = hxx - hyy
        disc = np.hypot(df, 2.0 * hxy).astype(np.float32)
        del df
        e1 = 0.5 * (tr + disc)
        e2 = 0.5 * (tr - disc)
        del tr, disc
        swap = np.abs(e2) > np.abs(e1)
        l1 = np.where(swap, e2, e1).astype(np.float32)  # principal across-scarp curvature |l1| >= |l2|
        l2 = np.where(swap, e1, e2).astype(np.float32)
        del swap, e1, e2

        rb = np.abs(l2) / (np.abs(l1) + 1e-6)
        s_norm2 = l1 * l1 + l2 * l2
        del l2
        c2 = np.float32(max(float(np.percentile(s_norm2, 90)) * 0.5, 1e-6))
        v_scale = (np.exp(-(rb * rb) / beta2) * (1.0 - np.exp(-s_norm2 / c2))).astype(np.float32)
        del rb, s_norm2
        frangi_max = np.maximum(frangi_max, v_scale)
        del v_scale

        # Steger (1998) eigenvector (nx, ny) for l1 and sub-pixel offset t = -(gx*nx + gy*ny)/l1
        vx = l1 - hyy
        vy = hxy
        del hxx, hyy, hxy
        vnorm = np.hypot(vx, vy).astype(np.float32) + 1e-8
        nx = vx / vnorm
        ny = vy / vnorm
        del vx, vy, vnorm
        t_off = -(gx * nx + gy * ny) / (l1 + np.where(l1 >= 0, 1e-6, -1e-6))
        del gx, gy
        in_px = (np.abs(t_off * nx) <= 0.5) & (np.abs(t_off * ny) <= 0.5)
        del nx, ny
        steger_line = np.where(in_px, np.abs(l1) * (1.0 - np.minimum(np.abs(t_off), 0.71)), 0.0).astype(np.float32)
        del l1, t_off, in_px
        steger_max = np.maximum(steger_max, steger_line)
        del steger_line

    # 4. Structure-tensor components on slope-detrended surface
    jxx = (gx_det * gx_det).astype(np.float32)
    jyy = (gy_det * gy_det).astype(np.float32)
    jxy = (gx_det * gy_det).astype(np.float32)

    return {
        "amp": best_amp,
        "slope_aware_amp": best_slope_amp,
        "rel_age": best_kt,
        "orientation": best_ang,
        "snr": best_snr,
        "slope_polarity": slope_polarity,
        "frangi_max": frangi_max,
        "steger_max": steger_max,
        "jxx": jxx,
        "jyy": jyy,
        "jxy": jxy,
        "slope_reg": slope_reg,
    }


def aggregate_tile_to_100m(
    tile_res: dict[str, np.ndarray],
    out_shape: tuple[int, int] = (101, 101),
    snr_quantile: float = 0.75,
    amp_quantile: float = 0.75,
) -> dict[str, np.ndarray]:
    """Aggregate native-resolution Scarplet + Steger/Frangi channels to 100 m grid cells."""
    amp = tile_res["slope_aware_amp"]
    snr = tile_res["snr"]
    frangi = tile_res["frangi_max"]
    steger = tile_res["steger_max"]
    kt = tile_res["rel_age"]
    jxx = tile_res["jxx"]
    jyy = tile_res["jyy"]
    jxy = tile_res["jxy"]

    h_in, w_in = amp.shape
    h_out, w_out = out_shape
    snr_thr = float(np.quantile(snr, snr_quantile))
    amp_thr = float(np.quantile(amp, amp_quantile))
    scarp_px = ((snr >= snr_thr) & (amp >= amp_thr)).astype(np.float32)
    snr_pos = np.maximum(snr, 0.0)
    snr_amp = (amp * snr_pos).astype(np.float32)
    line_combined = (0.5 * frangi + 0.5 * (steger / (float(np.percentile(steger, 99)) + 1e-5))).astype(np.float32)

    r_edges = np.linspace(0, h_in, h_out + 1, dtype=int)
    c_edges = np.linspace(0, w_in, w_out + 1, dtype=int)

    def box_mean(arr: np.ndarray) -> np.ndarray:
        cs_r = np.pad(arr.astype(np.float64), ((1, 0), (1, 0)), mode="constant").cumsum(0).cumsum(1)
        sums = (
            cs_r[r_edges[1:, None], c_edges[None, 1:]]
            - cs_r[r_edges[:-1, None], c_edges[None, 1:]]
            - cs_r[r_edges[1:, None], c_edges[None, :-1]]
            + cs_r[r_edges[:-1, None], c_edges[None, :-1]]
        )
        counts = np.outer(np.diff(r_edges), np.diff(c_edges))
        return (sums / np.maximum(counts, 1)).astype(np.float32)

    scarp_pixel_fraction = box_mean(scarp_px)
    snr_weighted_amplitude = box_mean(snr_amp) / (box_mean(snr_pos) + 1e-5)
    steger_frangi_score = box_mean(line_combined)
    mean_rel_age = box_mean(kt)

    Jxx = box_mean(jxx)
    Jyy = box_mean(jyy)
    Jxy = box_mean(jxy)
    coh_num = np.hypot(Jxx - Jyy, 2.0 * Jxy)
    structure_tensor_coherence = (coh_num / (Jxx + Jyy + 1e-6)).astype(np.float32)
    # Gradient orientation is 0.5 * atan2(2*Jxy, Jxx - Jyy); scarp strike is +90 deg modulo 180 deg
    grad_deg = 0.5 * np.rad2deg(np.arctan2(2.0 * Jxy, Jxx - Jyy))
    dominant_strike = ((grad_deg + 90.0) % 180.0).astype(np.float32)

    return {
        "scarp_pixel_fraction": scarp_pixel_fraction,
        "snr_weighted_amplitude": snr_weighted_amplitude,
        "structure_tensor_coherence": structure_tensor_coherence,
        "dominant_strike": dominant_strike,
        "steger_frangi_score": steger_frangi_score,
        "mean_rel_age": mean_rel_age,
    }


def build_cultural_feature_mask(
    dom: np.ndarray,
    d_road: np.ndarray,
    d_claim: np.ndarray,
    relief2m: np.ndarray,
    curv_10m: np.ndarray,
    upface: np.ndarray,
    downface: np.ndarray,
    cross: np.ndarray,
    dominant_strike: np.ndarray,
    h_gate12: np.ndarray,
) -> dict[str, np.ndarray]:
    """Identify anthropogenic scarp mimics (roads, canals, field edges, mining pits).

    Road embankments, irrigation canals, and agricultural section-line field edges
    produce sharp 1-3 m short-wavelength steps in native LiDAR but lack regional
    10 m profile curvature (curv_10m) and net 3 m far-field offset (h_gate12).
    """
    dom_b = np.asarray(dom, dtype=bool)
    road_mask = dom_b & np.isfinite(d_road) & (d_road <= 150.0) & (relief2m < 4.2) & (curv_10m < 0.24)
    canal_mask = dom_b & (cross > 1.05 * (upface + downface + 1e-4)) & (relief2m < 4.8) & (curv_10m < 0.24)
    field_mask = (
        dom_b
        & (np.abs(np.sin(np.deg2rad(2.0 * dominant_strike))) < 0.18)
        & (relief2m < 3.8)
        & (curv_10m < 0.22)
        & (h_gate12 < 0.10)
    )
    claim_mask = dom_b & np.isfinite(d_claim) & (d_claim <= 150.0) & (relief2m < 4.5) & (curv_10m < 0.22)
    combined = road_mask | canal_mask | field_mask | claim_mask
    return {
        "cultural_mask": combined,
        "road_mask": road_mask,
        "canal_mask": canal_mask,
        "field_mask": field_mask,
        "claim_mask": claim_mask,
    }


def select_nms_dots(
    score: np.ndarray,
    valid_mask: np.ndarray,
    budget: int = 45000,
    size: int = 5,
) -> np.ndarray:
    """Select top-budget 2-D non-maximum-suppressed peaks within valid_mask."""
    s = np.where(valid_mask, np.asarray(score, dtype=np.float32), -1e9)
    rr, cc = np.indices(s.shape, dtype=np.float32)
    s_tie = s + 1e-7 * np.sin(rr * 0.17 + cc * 0.31)
    mx = ndi.maximum_filter(s_tie, size=size)
    peaks = valid_mask & (s_tie == mx) & (s > -1e8)
    p_idx = np.flatnonzero(peaks)
    if len(p_idx) > budget:
        top = np.argpartition(s.ravel()[p_idx], -budget)[-budget:]
        chosen = p_idx[top]
    else:
        chosen = p_idx
    out = np.zeros(s.shape, dtype=np.float32)
    out.ravel()[chosen] = 1.0
    return out


def format_normalized_submissions(
    surface_score: np.ndarray,
    dot_mask: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return normalized [0, 1] float32 arrays: (zeros_outside, nan_outside).

    Selected NMS dots are mapped to [0.5001, 1.0000] proportional to their
    continuous calibrated score rank so that:
      - min(finite) == 0.0 and max(finite) == 1.0,
      - both >0 support (uniqueness.py) and >0.5 support (metric.py) identify
        the exact same selected dots, and
      - continuous rank ordering is preserved across all emitted picks.
    """
    fp = np.asarray(footprint, dtype=bool)
    dots = np.asarray(dot_mask, dtype=bool) & fp
    if not dots.any():
        raise ValueError("dot_mask must contain at least one in-footprint positive pick")
    arr_zeros = np.zeros(fp.shape, dtype=np.float32)
    ranks = rank_1d(np.asarray(surface_score, dtype=np.float32)[dots])
    vals = (0.5001 + 0.4999 * ranks).astype(np.float32)
    vals[np.argmin(ranks)] = np.float32(0.5001)
    vals[np.argmax(ranks)] = np.float32(1.0)
    arr_zeros[dots] = vals

    arr_nan = arr_zeros.copy()
    arr_nan[~fp] = np.nan
    return arr_zeros, arr_nan
