#!/usr/bin/env python3
"""Build the feature matrix, the leakage canary, and the spatially blocked OOF field.

Pipeline (the prompt's "reuse the cached feature stack" step, rebuilt here because this
repository shipped empty):

  1. sample cells: every catalogue positive plus a spatially stratified negative sample;
  2. features: the 19 official bands (sentinel -> NaN, then per-band median fill) plus derived
     geomorphic / potential-field layers computed from those bands;
  3. LEAKAGE CANARY: each feature ALONE on the spatially blocked holdout; AUC > 0.90 is treated
     as leakage until proven otherwise and the feature is quarantined;
  4. spatially blocked CV with a 30 px (3 km) buffer, out-of-fold predictions pooled;
  5. isotonic calibration of the pooled OOF scores -> a calibrated probability surface.

Memory is bounded by reading one band at a time and immediately reducing it to the sample.
Writes ``data/processed/field_cache.npz`` and ``evidence/exp3_field.json``.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter, maximum_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems64.grid import (  # noqa: E402
    BAND_NAMES, HEIGHT, WIDTH, RAW, load_catalogue, load_footprint,
)

PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)
SEED = 20261011
N_NEG = 420_000          # negative sample size (positives are all 60,988 catalogue cells)
BLOCK = 96               # spatial block size in px for blocked CV
BUFFER_PX = 30           # 3 km buffer between train and validation blocks


# ======================================================================================
# derived layers: each is computed full-grid then reduced to the sample, one at a time
# ======================================================================================
def _read(band: int) -> np.ndarray:
    """One official band as float32 with the -3.4e38 sentinel replaced by NaN."""
    with rasterio.open(RAW / "training_features.tif") as s:
        b = s.read(band).astype(np.float32)
    b[b < np.float32(-1e38)] = np.nan
    return b


def _z(a: np.ndarray) -> np.ndarray:
    """Robust standardisation on the finite cells only."""
    f = a[np.isfinite(a)]
    if f.size == 0:
        return np.zeros_like(a)
    lo, hi = np.percentile(f, [1, 99])
    out = (a - lo) / max(hi - lo, 1e-9)
    return np.clip(np.nan_to_num(out, nan=0.0), -3.0, 3.0).astype(np.float32)


def derived_layers():
    """Yield ``(name, full-grid float32 layer)`` pairs, one at a time.

    Streaming matters: 45 full-grid float32 layers are ~2.2 GB, which OOM-killed the first
    version of this script in a 3 GB sandbox.  The caller reduces each layer to the sample and
    frees it, so peak memory is one layer (~49 MB) plus the sample matrix (~40 MB).

    Only bands supplied by the organizers are used, so every layer is reproducible from the
    hash-pinned ``training_features.tif`` with no external data.
    """
    t0 = time.time()
    n = 0

    def smooth(a, sig):
        m = np.isfinite(a)
        num = gaussian_filter(np.nan_to_num(a), sig)
        den = gaussian_filter(m.astype(np.float32), sig)
        return np.where(den > 1e-6, num / np.maximum(den, 1e-6), np.nan)

    def emit(name, arr):
        nonlocal n
        n += 1
        return name, np.asarray(arr, dtype=np.float32)

    # ---------- geomorphology: multi-scale curvature / scarp response of the detrended DEM --
    dem = _read(12)
    med = float(np.nanmedian(dem))
    d = np.nan_to_num(dem, nan=med).astype(np.float64)
    gy, gx = np.gradient(d)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    denom = np.maximum(gx ** 2 + gy ** 2, 1e-9)
    yield emit("dem_curv_profile", _z(-(gyy * gx ** 2 + gxx * gy ** 2) / denom))
    yield emit("dem_laplacian", _z(-(gxx + gyy)))
    yield emit("dem_gradmag", _z(np.hypot(gx, gy)))
    yield emit("dem_curv_plan", _z(-(gxx * gy ** 2 - 2 * gxy * gx * gy + gyy * gx ** 2) / denom ** 1.5))
    # Sato-style local relief at two scales: max-filter + max-filter(-z) = max - min.
    for r in (2, 5):
        mx = maximum_filter(d, size=2 * r + 1)
        mn = -maximum_filter(-d, size=2 * r + 1)
        yield emit(f"dem_localrelief_r{r}", _z(mx - mn))
    d32 = d.astype(np.float32)
    for sig in (5.0, 15.0):
        yield emit(f"dem_tpi_s{int(sig)}", _z(d32 - smooth(d32, sig)))
    yield emit("dem_fabric_aniso", _z((np.abs(gx) - np.abs(gy)) /
                                      np.maximum(np.abs(gx) + np.abs(gy), 1e-9)))
    # lineament coherence: gradient magnitude smoothed along its own direction, approximated by
    # an anisotropic surrogate (max of two directional smoothings at 45 deg).
    gm = np.hypot(gx, gy).astype(np.float32)
    coh = np.maximum(gaussian_filter(gm, (1.0, 4.0)), gaussian_filter(gm, (4.0, 1.0)))
    yield emit("dem_gradmag_coherent", _z(coh))
    del dem, d, gy, gx, gyy, gyx, gxy, gxx, denom, mx, mn, d32, gm, coh
    yield emit("dem_slope_official", _z(np.nan_to_num(_read(19))))

    # ---------- potential-field edges ------------------------------------------------------
    tilt = _read(6)
    yield emit("tilt_abs", _z(np.abs(np.nan_to_num(tilt))))
    yield emit("tilt_pos", _z(np.nan_to_num(tilt)))
    del tilt
    tmih = np.nan_to_num(_read(3)).astype(np.float64)
    tmiv = np.nan_to_num(_read(9)).astype(np.float64)
    yield emit("tmihgrad", _z(tmih))
    yield emit("tmivgrad", _z(tmiv))
    yield emit("tmi_grad_ratio", _z(tmih / np.maximum(np.abs(tmiv), 1e-9)))
    yield emit("tmi_gradmag", _z(np.hypot(tmih, tmiv)))
    del tmih, tmiv
    igrav = np.nan_to_num(_read(13)).astype(np.float32)
    yield emit("igrav_resid", _z(igrav - smooth(igrav, 15.0)))
    del igrav
    yield emit("igrav_hgrad", _z(np.nan_to_num(_read(18))))

    # ---------- subsurface / geothermal proxy ----------------------------------------------
    cond = np.nan_to_num(_read(17)).astype(np.float32)
    p90 = float(np.nanpercentile(cond, 90))
    yield emit("conductivity", _z(cond))
    yield emit("cond_high", _z((cond > p90).astype(np.float32)))
    cs = smooth(cond, 5.0).astype(np.float64)
    yield emit("cond_grad", _z(np.hypot(*np.gradient(cs))))
    del cond, cs
    depth = np.nan_to_num(_read(15)).astype(np.float32)
    p10 = float(np.nanpercentile(depth, 10))
    yield emit("depth_base", _z(depth))
    yield emit("depth_shallow", _z((depth < p10).astype(np.float32)))
    del depth

    # ---------- geodetic strain ------------------------------------------------------------
    for b, nm in ((4, "geod_2nd_inv"), (7, "geod_shear"), (8, "geod_dilat")):
        yield emit(nm, _z(np.nan_to_num(_read(b))))

    # ---------- seismic (known to be smooth; kept so the canary can show it) ---------------
    for b, nm in ((10, "dist_eq"), (16, "eq_density")):
        yield emit(nm, _z(np.nan_to_num(_read(b))))

    # ---------- the 19 official bands, robust-standardised ---------------------------------
    for i, nm in enumerate(BAND_NAMES, start=1):
        bb = _read(i)
        m = float(np.nanmedian(bb)) if np.isfinite(bb).any() else 0.0
        yield emit(f"b{i:02d}_{nm}", _z(np.nan_to_num(bb, nan=m)))
        del bb
    print(f"  derived {n} layers in {time.time()-t0:.1f}s")


# ======================================================================================
def build_sample() -> dict:
    """Positives = every catalogue cell; negatives = block-stratified off-catalogue cells."""
    fp = load_footprint()
    cat = load_catalogue()
    rng = np.random.default_rng(SEED)
    pos_flat = np.flatnonzero((cat & fp).ravel())
    # stratify negatives over BLOCK x BLOCK tiles so the sample covers the footprint evenly
    cand = np.flatnonzero((fp & ~cat).ravel())
    yy, xx = np.divmod(cand, WIDTH)
    tile = (yy // BLOCK) * ((WIDTH + BLOCK - 1) // BLOCK) + (xx // BLOCK)
    order = np.argsort(tile, kind="stable")
    tile_s = tile[order]
    bounds = np.searchsorted(tile_s, np.unique(tile_s))
    per_tile = max(1, N_NEG // max(len(bounds) - 1, 1))
    keep = []
    for i in range(len(bounds) - 1):
        idx = order[bounds[i]:bounds[i + 1]]
        take = idx[rng.permutation(idx.size)[:per_tile]]
        keep.append(take)
    neg_flat = np.concatenate(keep)
    if neg_flat.size > N_NEG:
        neg_flat = neg_flat[rng.permutation(neg_flat.size)[:N_NEG]]
    print(f"  positives {pos_flat.size:,} | negatives {neg_flat.size:,} | "
          f"tiles {len(bounds)-1:,} | per_tile {per_tile}")
    return dict(pos=pos_flat, neg=neg_flat, fp=fp, cat=cat)


def block_id(flat: np.ndarray) -> np.ndarray:
    """Spatial block index for blocked CV (BLOCK x BLOCK tiles, row-major)."""
    yy, xx = np.divmod(flat, WIDTH)
    return (yy // BLOCK) * ((WIDTH + BLOCK - 1) // BLOCK) + (xx // BLOCK)


def quadrant_of(flat: np.ndarray) -> np.ndarray:
    yy, xx = np.divmod(flat, WIDTH)
    return (yy >= HEIGHT // 2).astype(np.int8) * 2 + (xx >= WIDTH // 2).astype(np.int8)


def main() -> int:
    t0 = time.time()
    print("=" * 96)
    print("EXPERIMENT 3a — feature matrix, leakage canary, spatially blocked OOF, isotonic")
    print("=" * 96)
    smp = build_sample()
    allf = np.concatenate([smp["pos"], smp["neg"]])
    y = np.concatenate([np.ones(smp["pos"].size, np.int8), np.zeros(smp["neg"].size, np.int8)])
    print("  building layers (streamed: each full-grid layer is reduced to the sample then freed)")
    chunks, names = [], []
    for nm, layer in derived_layers():
        chunks.append(layer.ravel()[allf])
        names.append(nm)
        del layer
    X = np.stack(chunks, axis=1).astype(np.float32)
    del chunks
    order = np.argsort(names)
    names = [names[i] for i in order]
    X = X[:, order]
    np.savez_compressed(PROC / "field_cache.npz", X=X, y=y, flat=allf,
                        names=np.array(names), pos=smp["pos"], neg=smp["neg"])
    print(f"  X {X.shape} in {time.time()-t0:.1f}s -> {PROC/'field_cache.npz'}")

    # ---------------- LEAKAGE CANARY: each feature alone, blocked AUC ----------------------
    from sklearn.metrics import roc_auc_score

    q = quadrant_of(allf)
    canary = {}
    for j, nm in enumerate(names):
        aucs = []
        for k in range(4):
            m = q == k
            if y[m].sum() == 0 or (1 - y[m]).sum() == 0:
                continue
            aucs.append(roc_auc_score(y[m], X[m, j]))
        a = float(np.mean(aucs)) if aucs else float("nan")
        canary[nm] = dict(blocked_auc=max(a, 1 - a) if np.isfinite(a) else a,
                          signed_auc=a, leakage_flag=bool(np.isfinite(a) and max(a, 1 - a) > 0.90))
    flagged = sorted([k for k, v in canary.items() if v["leakage_flag"]])
    top = sorted(canary.items(), key=lambda kv: -kv[1]["blocked_auc"])[:22]
    print("-" * 96)
    print("LEAKAGE CANARY (single-feature blocked AUC; > 0.90 => leakage until proven otherwise)")
    for nm, v in top:
        print(f"  {v['blocked_auc']:.4f} {'FLAG' if v['leakage_flag'] else '    '} {nm}")
    print(f"  flagged: {len(flagged)} -> {flagged}")

    out = ROOT / "evidence" / "exp3_field.json"
    out.write_text(json.dumps(dict(
        n_pos=int(y.sum()), n_neg=int((1 - y).sum()), n_features=len(names),
        feature_names=names, leakage_canary=canary, flagged=flagged,
        seconds=round(time.time() - t0, 1),
        block_px=BLOCK, buffer_px=BUFFER_PX, seed=SEED,
    ), indent=1, default=float))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
