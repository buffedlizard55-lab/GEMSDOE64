#!/usr/bin/env python3
"""Native-resolution lidar scarp lane -> 100 m dot submission (GEMSDOE64).

End-to-end, single-command run of the assigned lane:

  1. reference grid + catalogue + footprint            (data/bridge, hash-pinned)
  2. lane features                                     (src/gems64/lidar_scarp.py)
     * scarp template matching with the slope-aware term (scarplet convention)
     * Steger sub-pixel ridge/valley measure
     * Frangi multiscale Hessian line measure
     * structure-tensor coherence + dominant strike
     * 100 m aggregation: scarp fraction, SNR-weighted amplitude, coherence, strike
  3. cultural-feature mask                             (TIGER roads / BLM claims distance)
  4. spatial hide-and-recover instrument               (gems57.holdout.buffered_component_draw)
  5. emission arms                                     (src/gems64/emit.py)
  6. gates: format, validator, registry uniqueness, leakage canaries
  7. fail-closed writer + receipts                     (gems57.submission_writer, gems57.validate)
  8. one JSON run card                                 (gems64.promotion.promotion_decision)

Nothing here uploads, and no submission slot is used. The verdict is computed
from measured evidence; missing evidence is recorded as null, never as a pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout, grid as grid_mod, holdout, metric, uniqueness  # noqa: E402
from gems57 import gates as gates_mod  # noqa: E402
from gems57.validate import assert_submittable, validate  # noqa: E402
from gems64 import calibration, emit, lidar_scarp, promotion  # noqa: E402

NATIVE_SCALES_M = (2.0, 4.0, 8.0, 14.0, 20.0)   # the lane's 2-20 m scale band
LIDAR_MIN_LINE_HITS = 3
CULTURAL_ROAD_M = 30.0                          # mask cells within 30 m of a mapped road
FLANK_PX = 2                                    # catalogue-flank buffer of the 0.2708->0.2778 step


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_u8(path: Path) -> tuple[np.ndarray, list[str]]:
    """Read an integer-quantised layer stack **without** float64 promotion.

    Holding 12 float64 bands of a 12.3 M-cell grid would be ~1.2 GB; the layers
    stay in their storage dtype and are promoted per use.
    """
    with rasterio.open(path) as ds:
        a = ds.read()
        names = [str(d) if d else f"band{i+1}" for i, d in enumerate(ds.descriptions)]
    return a, names


def zscore(a: np.ndarray, valid: np.ndarray) -> np.ndarray:
    x = np.asarray(a, dtype=np.float64)
    v = valid & np.isfinite(x)
    if not v.any():
        return np.zeros_like(x)
    lo, hi = np.percentile(x[v], [2.0, 98.0])
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def _rss_mb() -> float:
    try:
        with open("/proc/self/statm") as fh:
            return int(fh.read().split()[1]) * 4096 / 1e6
    except OSError:
        return float("nan")


def build_features(args, grid, log):
    """Lane features on the finest available lidar/topography grids.

    Memory discipline is explicit: at 3 GB of RAM a naive float64 pipeline on the
    12.3 M-cell grid is OOM-killed, so every stage runs in float32, drops its
    intermediate derivative stacks immediately, and the DEM stage is released
    before the lidar stage allocates.
    """
    import gc

    pixel_m = 100.0
    thetas = list(range(0, 180, 15))
    widths_px = lidar_scarp.scales_px(NATIVE_SCALES_M, pixel_m, minimum=1.0)
    frangi_scales = widths_px

    # ---- official 100 m stack: det_elev second-order structure ---------------
    with rasterio.open(args.features) as ds:
        names = [str(d).split(" - ")[0] for d in ds.descriptions]
        fi = {n: i for i, n in enumerate(names)}
        det_elev = ds.read(fi["det_elev"] + 1).astype(np.float32)
        det_elev_slope = ds.read(fi["det_elev_slope"] + 1).astype(np.float32)
        nodata = ds.nodata
    finite_feat = np.isfinite(det_elev) & (det_elev > -1e30) if nodata is None else (det_elev != nodata)
    detrended_dem = lidar_scarp.slope_detrend(np.where(finite_feat, det_elev, np.nan),
                                             sigma=args.dem_detrend_sigma).astype(np.float32)
    dem_steg, _o1, _o2 = lidar_scarp.steger_ridge(detrended_dem, sigma=args.steger_sigma, polarity="ridge")
    dem_frangi, _i1 = lidar_scarp.frangi_vesselness(detrended_dem, frangi_scales, polarity="dark")
    dem_steg01 = zscore(dem_steg, finite_feat)
    del dem_steg, _o1, _o2
    dem_frangi01 = zscore(dem_frangi, finite_feat)
    del dem_frangi, detrended_dem
    log(f"[mem] dem block done: {_rss_mb():.0f} MB")
    gc.collect()

    # ---- lidar scarp layer --------------------------------------------------
    lidar, lidar_names = load_u8(args.lidar)
    lidx = {n: i for i, n in enumerate(lidar_names)}
    log(f"[features] lidar channels: {lidar_names}")
    valid_lidar = lidar[lidx.get("valid", 0)] > 0

    relief = lidar[lidx["relief"]] if "relief" in lidx else np.zeros(grid.shape, np.uint8)
    relief_m = np.where(valid_lidar, relief.astype(np.float64) * args.relief_scale_m_per_unit, np.nan)
    detrended = lidar_scarp.slope_detrend(relief_m, sigma=args.detrend_sigma).astype(np.float32)
    del relief_m, relief

    step_raw = lidar[lidx["step_max"]] if "step_max" in lidx else np.zeros(grid.shape, np.uint8)
    lap_raw = np.maximum(lidar[lidx["lapneg_max"]], lidar[lidx["lappos_max"]]) \
        if "lapneg_max" in lidx else np.zeros(grid.shape, np.uint8)
    hp_evidence = np.where(valid_lidar, np.maximum(step_raw, lap_raw), 0)
    thr = np.percentile(hp_evidence[valid_lidar], args.high_prior_pct) if valid_lidar.any() else np.inf
    high_prior = valid_lidar & (hp_evidence >= thr)
    log(f"[features] high-prior cells (top {100 - args.high_prior_pct:g}%): {int(high_prior.sum()):,}")

    # --- lane (i): scarp template matching with the slope-aware term ---------
    scarp = lidar_scarp.scarplet_step_fit(detrended, thetas, half_len=int(args.template_half_len),
                                          width_px=float(widths_px.min()), mask=high_prior)
    scarp_amp = np.asarray(scarp["amplitude"], dtype=np.float32)
    scarp_snr = np.asarray(scarp["snr"], dtype=np.float32)
    del scarp
    log("[features] scarp template matching: %d orientations, width %.1f px, requested scales %s m -> %s px"
        % (len(thetas), float(widths_px.min()), list(NATIVE_SCALES_M), [float(v) for v in widths_px]))
    gc.collect()

    # --- lane (ii): Steger + Frangi on the slope-detrended surface -----------
    steg_r, _a1, _a2 = lidar_scarp.steger_ridge(detrended, sigma=args.steger_sigma, polarity="ridge")
    steg_v, _b1, _b2 = lidar_scarp.steger_ridge(detrended, sigma=args.steger_sigma, polarity="valley")
    steg_max = zscore(np.maximum(steg_r, steg_v), valid_lidar)
    steg_r = steg_v = _a1 = _a2 = _b1 = _b2 = None
    del steg_r, steg_v, _a1, _a2, _b1, _b2
    gc.collect()
    log(f"[mem] steger done: {_rss_mb():.0f} MB")
    fr_dark, _i2 = lidar_scarp.frangi_vesselness(detrended, frangi_scales, polarity="dark")
    fr_bright, _i3 = lidar_scarp.frangi_vesselness(detrended, frangi_scales, polarity="bright")
    fr_max = zscore(np.maximum(fr_dark, fr_bright), valid_lidar)
    del fr_dark, fr_bright, _i2, _i3
    gc.collect()
    log(f"[mem] frangi done: {_rss_mb():.0f} MB")

    ev01 = zscore(np.maximum(np.abs(scarp_amp), np.maximum(np.abs(steg_max), np.maximum(fr_max, 0.0))),
                  valid_lidar & np.isfinite(detrended))
    del detrended
    gc.collect()

    # --- structure tensor on the scarp evidence field -----------------------
    coh_lidar = lidar[lidx["coh100"]].astype(np.float32) / np.float32(255.0) if "coh100" in lidx \
        else np.zeros(grid.shape, np.float32)
    strike_lidar = lidar[lidx["strike"]].astype(np.float32) / np.float32(255.0) * np.float32(180.0) \
        if "strike" in lidx else np.full(grid.shape, np.nan, np.float32)
    strike_lidar = np.where(valid_lidar, strike_lidar, np.nan)
    coh_tensor, orient_tensor, _energy = lidar_scarp.structure_tensor(np.nan_to_num(ev01), sigma=1.0, rho=2.0)
    orient_coh = np.where(np.isfinite(coh_tensor) & (coh_tensor > 0), coh_tensor, coh_lidar).astype(np.float32)
    strike_used = np.where(np.isfinite(strike_lidar), strike_lidar, orient_tensor).astype(np.float32)
    del coh_tensor, orient_tensor, _energy, coh_lidar, strike_lidar
    gc.collect()

    step01 = zscore(step_raw, valid_lidar)
    lap01 = zscore(lap_raw, valid_lidar)
    down01 = zscore(lidar[lidx["downface_max"]], valid_lidar) if "downface_max" in lidx else np.zeros(grid.shape, np.float32)
    up01 = zscore(lidar[lidx["upface_max"]], valid_lidar) if "upface_max" in lidx else np.zeros(grid.shape, np.float32)
    cross01 = zscore(lidar[lidx["cross_max"]], valid_lidar) if "cross_max" in lidx else np.zeros(grid.shape, np.float32)
    slope01 = zscore(det_elev_slope, finite_feat)
    del step_raw, lap_raw, hp_evidence, det_elev, det_elev_slope
    gc.collect()

    # --- the run's new line-coherence statistic -----------------------------
    line_coh = lidar_scarp.line_consistency(strike_used, ev01, half_len=2,
                                            max_strike_dev_deg=args.strike_tol_deg,
                                            min_hits=LIDAR_MIN_LINE_HITS)
    line_coh = np.nan_to_num(line_coh).astype(np.float32)
    gc.collect()
    log(f"[mem] line coherence done: {_rss_mb():.0f} MB")

    components = {
        "scarp_template": np.clip(ev01, 0, 1).astype(np.float32),
        "step": step01, "laplacian": lap01,
        "polarity": np.abs(down01 - up01).astype(np.float32), "cross": cross01,
        "steger_lidar": np.clip(steg_max, 0, 1).astype(np.float32),
        "frangi_lidar": np.clip(fr_max, 0, 1).astype(np.float32),
        "frangi_dem": dem_frangi01, "steger_dem": dem_steg01, "slope": slope01,
    }
    best = np.zeros(grid.shape, np.float32)
    second = np.zeros(grid.shape, np.float32)
    for arr in components.values():
        gt_best = arr > best
        second = np.where(gt_best, best, np.maximum(second, np.minimum(arr, best)))
        best = np.where(gt_best, arr, best)
    prior = np.cbrt(np.clip(components["scarp_template"].astype(np.float32)
                            * np.clip(line_coh, 0, 1)
                            * np.clip(second, 0, 1), 0, 1)).astype(np.float32)
    agg = lidar_scarp.aggregate_to_grid(
        factor=1,
        layers={"amplitude": np.where(np.isfinite(ev01), ev01, np.nan),
                "snr": np.where(np.isfinite(scarp_snr), scarp_snr, np.nan)},
        weights={"amplitude": np.where(np.isfinite(scarp_snr), scarp_snr, np.float32(1.0))},
        orientation_layer=None)
    scarp_fraction = np.nan_to_num(agg["scarp_fraction"]).astype(np.float32)
    snr_amp = np.nan_to_num(agg["snr_weighted_amplitude"]).astype(np.float32)
    del lidar
    gc.collect()
    log(f"[mem] features complete: {_rss_mb():.0f} MB")
    return dict(valid=valid_lidar, prior=prior, line_coh=line_coh, components=components,
                dominant_strike=strike_used, orient_coh=orient_coh,
                scarp_fraction=scarp_fraction, snr_amp=snr_amp, finite_feat=finite_feat,
                scale_audit=dict(requested_scales_m=list(NATIVE_SCALES_M), pixel_m=pixel_m,
                                 resolvable_scales_px=[float(v) for v in widths_px],
                                 scale_note="100 m input grid: the lane's 2-20 m band is not "
                                            "physically resolvable; the native-resolution path is "
                                            "implemented and unit-tested but blocked by egress "
                                            "(evidence/access_blockers.json)"))


def cultural_mask(args, grid, log):
    """Mask roads / canals / field edges using the owner-audited TIGER road distance layer."""
    if not args.road_distance.exists():
        log("[cultural] road-distance layer absent -> cultural mask NOT applied (recorded as null)")
        return np.zeros(grid.shape, bool), None
    with rasterio.open(args.road_distance) as ds:
        d = ds.read(1).astype(np.float64)
        if (ds.height, ds.width) != grid.shape:
            raise ValueError("road-distance grid does not match the competition grid")
    mask = np.isfinite(d) & (d <= CULTURAL_ROAD_M)
    log(f"[cultural] {int(mask.sum())} cells within {CULTURAL_ROAD_M:g} m of a mapped road")
    return mask, sha256_file(args.road_distance)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, default=ROOT / "data" / "bridge")
    ap.add_argument("--features", type=Path,
                    default=ROOT / "data" / "official" / "training_features.tif")
    ap.add_argument("--lidar", type=Path, default=ROOT / "data" / "external" / "lidar_scarp_features_u8.tif")
    ap.add_argument("--road-distance", type=Path,
                    default=ROOT / "data" / "external" / "tiger_road_distance_m.tif")
    ap.add_argument("--registry-index", type=Path, default=ROOT / "evidence" / "registry_index.json")
    ap.add_argument("--incumbent", type=Path, default=ROOT / "data" / "registry" / "g28-base.tif")
    ap.add_argument("--outdir", type=Path, default=ROOT / "docs" / "downloads")
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence")
    ap.add_argument("--name", default="g64-lidarscarp-strikeline")
    ap.add_argument("--note", default="")
    ap.add_argument("--detrend-sigma", type=float, default=6.0)
    ap.add_argument("--dem-detrend-sigma", type=float, default=8.0)
    ap.add_argument("--steger-sigma", type=float, default=1.5)
    ap.add_argument("--template-half-len", type=int, default=2)
    ap.add_argument("--strike-tol-deg", type=float, default=30.0)
    ap.add_argument("--relief-scale-m-per-unit", type=float, default=0.25)
    ap.add_argument("--min-flank-px", type=float, default=FLANK_PX)
    ap.add_argument("--max-dots", type=int, default=42000)
    ap.add_argument("--quick", action="store_true", help="skip registry scan and bootstrap draws")
    ap.add_argument("--high-prior-pct", type=float, default=75.0)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--seeds", default="20,21,22", help="truth-ensemble draw seeds (comma separated)")
    ap.add_argument("--cover-quantile", type=float, default=90.0)
    ap.add_argument("--control-draws", type=int, default=8)
    args = ap.parse_args()

    started = time.time()
    args.evidence.mkdir(parents=True, exist_ok=True)
    args.outdir.mkdir(parents=True, exist_ok=True)
    messages: list[str] = []

    def log(msg: str) -> None:
        print(msg, flush=True)
        messages.append(msg)

    grid = grid_mod.load_grid(args.bridge)
    log(f"[grid] footprint {int(grid.footprint.sum()):,} cells, catalogue {int(grid.catalogue.sum()):,} cells")

    feats = build_features(args, grid, log)
    cult_mask, cult_sha = cultural_mask(args, grid, log)
    # free everything the emission/scoring stages do not need (3 GB sandbox)
    import gc
    for key in ("scarp_fraction", "snr_amp", "orient_coh", "finite_feat"):
        feats.pop(key, None)
    gc.collect()
    log(f"[mem] after feature pruning: {_rss_mb():.0f} MB")

    # ---------------------------------------------------------------- instrument
    t0 = time.time()
    folds, quad = holdout.buffered_component_draw(grid, seed=20, hide_frac=0.20, buffer_px=3)
    log(f"[instrument] 4 whole-component folds built in {time.time()-t0:.1f}s; "
        f"withheld positives: {[int(f['truth'].sum()) for f in folds]}")

    # ------------------------------------------------------------------- canaries
    canary_rows = []
    canary_domain = grid.footprint          # labels = mapped catalogue inside the footprint
    for name, layer in feats["components"].items():
        a = np.where(np.isfinite(layer), layer, 0.0)
        rows = calibration.feature_canaries({name: a}, grid.catalogue.astype(np.int8), canary_domain)
        canary_rows.extend(rows)
    log("[canary] " + ", ".join(f"{r['feature']} AUC={r['auc']:.3f}" for r in canary_rows))
    feats.pop("components", None)
    gc.collect()

    # ------------------------------------------------------------ candidate arms
    valid = feats["valid"] & grid.footprint & ~cult_mask
    prior = np.where(valid, feats["prior"], 0.0).astype(np.float32)
    line_coh = np.asarray(feats["line_coh"], np.float32)
    scale_audit = feats.get("scale_audit")
    for key in ("dominant_strike", "orient_coh", "scarp_fraction", "snr_amp", "finite_feat",
                "line_coh", "prior", "valid", "scale_audit"):
        feats.pop(key, None)
    gc.collect()
    log(f"[mem] features released: {_rss_mb():.0f} MB")
    # Emission domain: finite lidar coverage, outside the cultural mask, and never
    # on a published catalogue pixel (the shared writer refuses positive mass there).
    allowed_base = valid & (prior > 0) & ~grid.catalogue
    log(f"[emit] emission domain {int(allowed_base.sum()):,} cells "
        f"({100*allowed_base.sum()/max(int(valid.sum()),1):.1f}% of lidar-valid)")

    packs = {}
    for dist in (2.8, 3.4):
        packs[dist] = emit.poisson_disk_pack(prior, allowed_base, min_dist_px=dist, max_dots=args.max_dots)
        log(f"[emit] packed {int(packs[dist].sum()):,} dots at min separation {dist} px")
    mclp, mclp_info = emit.greedy_surface_coverage(
        prior, allowed_base, max_dots=args.max_dots, cover_quantile=args.cover_quantile)
    log(f"[emit] MCLP surface-coverage baseline: {int(mclp.sum()):,} dots {mclp_info}")

    rng = np.random.default_rng(64)
    pool = np.argwhere(allowed_base)
    chosen = rng.choice(len(pool), size=min(int(packs[2.8].sum()), len(pool)), replace=False)
    control = np.zeros(grid.shape, bool)
    control[pool[chosen, 0], pool[chosen, 1]] = True

    incumbent = np.zeros(grid.shape, bool)
    if args.incumbent.exists():
        with rasterio.open(args.incumbent) as ds:
            inc = ds.read(1)
        incumbent = np.isfinite(inc) & (inc > 0) & ~grid.catalogue

    def flank(dots, visible):
        return dots & (ndi.distance_transform_edt(~visible) > args.min_flank_px)

    def line_keep(dots, frac):
        """Keep the top ``frac`` of the packed dots by the lane's line-coherence statistic."""
        keep = np.zeros_like(dots)
        values = line_coh[dots]
        if values.size == 0:
            return keep
        threshold = np.quantile(values, 1.0 - frac)
        keep[dots] = line_coh[dots] >= threshold
        return keep

    arm_choices = {
        "A_spacing28": lambda fold: packs[2.8],
        "B_spacing28_flank2": lambda fold: flank(packs[2.8], fold["visible"]),
        "C1_flank2_linekeep60": lambda fold: line_keep(flank(packs[2.8], fold["visible"]), 0.60),
        "C2_flank2_linekeep35": lambda fold: line_keep(flank(packs[2.8], fold["visible"]), 0.35),
        "D_spacing34_flank2": lambda fold: flank(packs[3.4], fold["visible"]),
        "M_mclp_surface": lambda fold: mclp,
        "Z_random_control": lambda fold: control,
    }
    if incumbent.any():
        arm_choices["INC_historical_base"] = lambda fold: incumbent
    lane_arms = ["A_spacing28", "B_spacing28_flank2", "C1_flank2_linekeep60",
                 "C2_flank2_linekeep35", "D_spacing34_flank2", "M_mclp_surface"]

    # ------------------------------------------------------- truth ensemble folds
    instruments = []
    for seed in [int(s) for s in str(args.seeds).split(",")]:
        folds, quad = holdout.buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
        instruments.append((seed, folds))
        log(f"[instrument] seed {seed}: withheld positives {[int(f['truth'].sum()) for f in folds]}")

    # A fold never sees the full catalogue: dots landing on the *hidden* set are
    # removed before scoring, because the real artifact is built without them.
    terms: dict = {arm: {seed: [] for seed, _ in instruments} for arm in arm_choices}
    fold_dti: dict = {arm: {} for arm in arm_choices}
    for seed, folds in instruments:
        for fi, fold in enumerate(folds):
            hidden_all = fold["hidden_all"]
            for arm in arm_choices:
                dots = arm_choices[arm](fold) & ~hidden_all
                result, t = evaluate_holdout.evaluate(
                    dots.astype(np.float32), fold, grid.footprint, block_side=200,
                    origin=(0, 0), global_shape=grid.shape)
                terms[arm][seed].append(t)
                fold_dti[arm][(seed, fi)] = float(result["dti"])
        log(f"[score] seed {seed} fold DTIs done")

    totals = {arm: np.sum(np.stack([np.sum(np.stack(terms[arm][seed]), axis=0)
                                    for seed, _ in instruments]), axis=0) for arm in arm_choices}
    def pooled_score(arm, keys):
        t = np.sum([terms[arm][seed][fi] for seed, fi in keys], axis=0)
        tp, fp, fn = float(t[:, 0].sum()), float(t[:, 1].sum()), float(t[:, 2].sum())
        return tp / (tp + metric.ALPHA * fp + metric.BETA * fn + metric.EPS)

    all_keys = [(seed, fi) for seed, folds in instruments for fi in range(len(folds))]
    preliminary = {arm: pooled_score(arm, all_keys) for arm in arm_choices}
    for arm in sorted(preliminary, key=lambda a: -preliminary[a]):
        log(f"[score] {arm:24s} dots={int(arm_choices[arm](instruments[0][1][0]).sum()):6d} "
            f"ensemble holdout DTI={preliminary[arm]:.5f}")

    primary = max(lane_arms, key=lambda a: preliminary[a])
    summary = evaluate_holdout.pooled_summary(totals, draws=args.draws, seed=520810, candidate=primary)
    log(f"[score] pooled summary (candidate {primary}):")
    for arm, row in summary["scores"].items():
        log(f"[score] {arm:24s} DTI={row['dti']:.5f} CI95=[{row['ci95'][0]:.5f},{row['ci95'][1]:.5f}] "
            f"withheld_positives={row['withheld_positive_pixels']}")
    paired = summary["paired_differences"]
    for arm, row in paired.items():
        log(f"[paired] {primary} - {arm:24s} delta={row['delta']:+.5f} se={row['bootstrap_se']:.5f} "
            f"beats2se={row['beats_two_se']}")

    # ------------------------------------------------------- cross-fitted selection
    oof_rows = []
    for seed, folds in instruments:
        for fi in range(len(folds)):
            train = [k for k in all_keys if k != (seed, fi)]
            pick = max(lane_arms, key=lambda a: pooled_score(a, train))
            oof_rows.append(dict(seed=seed, fold=fi, arm=pick,
                                 heldout_dti=pooled_score(pick, [(seed, fi)]),
                                 best_in_train=max(pooled_score(a, train) for a in lane_arms)))
    oof_selected = [r["arm"] for r in oof_rows]
    oof_score = float(np.mean([r["heldout_dti"] for r in oof_rows]))
    log(f"[oof] cross-fitted arm selection: mean held-out DTI {oof_score:.5f} over {len(oof_rows)} "
        f"held-out folds; selection counts {dict((a, oof_selected.count(a)) for a in set(oof_selected))}")

    # ------------------------------------------------------------- per-seed checks
    per_seed = {}
    for seed, folds in instruments:
        one = {arm: np.sum(np.stack(terms[arm][seed]), axis=0) for arm in arm_choices}
        s = evaluate_holdout.pooled_summary(one, draws=max(200, args.draws // 4), seed=520810 + seed,
                                            candidate=primary)
        per_seed[seed] = dict(dti=s["scores"][primary]["dti"],
                              deltas={k: dict(delta=v["delta"], se=v["bootstrap_se"],
                                              beats_two_se=v["beats_two_se"])
                                      for k, v in s["paired_differences"].items()})
        log(f"[ensemble] seed {seed}: {primary} DTI={per_seed[seed]['dti']:.5f} "
            + ", ".join(f"{k}:{v['delta']:+.5f}" for k, v in per_seed[seed]["deltas"].items()))

    # ------------------------------------------------------------- final candidate
    final_name = primary
    final_rule = arm_choices[final_name]
    # The shipped artifact applies the same rule with the PUBLISHED catalogue in
    # place of a fold's visible subset (strictly more pruning than what was scored).
    dots = final_rule(dict(visible=grid.catalogue)) & grid.footprint & ~grid.catalogue
    log(f"[final] selected arm {final_name} with {int(dots.sum())} dots "
        f"(scored counts were per-fold; the shipped rule uses the published catalogue)")

    raster = np.zeros(grid.shape, np.float32)
    raster[dots & grid.footprint] = 1.0

    # ------------------------------------------------------------------- gates
    tmp_path = args.outdir / f"{args.name}-{hashlib.sha256(str(int(started)).encode()).hexdigest()[:10]}.tif"
    grid_mod.write_geotiff(tmp_path, raster, nodata=None)
    fmt = gates_mod.format_report(tmp_path, args.bridge / "sample_submission.tif", footprint=grid.footprint)
    log(f"[gate] format ok={fmt['ok']} problems={fmt['problems']}")
    local = validate(tmp_path, grid.footprint, grid.catalogue)
    assert_submittable(local)
    log(f"[gate] local validator all_checks_passed={local['all_checks_passed']} "
        f"on_catalogue_positive_pixels={local.get('on_catalogue_positive_pixels')}")

    # ------------------------------------------------- uniqueness certificate
    certificate = None
    if args.registry_index.exists() and not args.quick:
        index = json.loads(args.registry_index.read_text())
        t0 = time.time()
        certificate = uniqueness.dense_prior_certificate(
            raster, registry_index=index, footprint=grid.footprint, allowed=allowed_base,
            file_sha256=local["sha256"], control_draws=args.control_draws,
            expected_grid=(grid.height, grid.width, grid.crs, grid.transform))
        log(f"[gate] uniqueness certificate in {time.time()-t0:.1f}s: "
            f"checked={certificate['registry_rasters_checked']} "
            f"literal_unique={certificate['literal_verdict_unique']} "
            f"diagnostic_unique={certificate['diagnostic_verdict_unique']} "
            f"worst_informative_overlap={certificate['worst_overlap_informative']} "
            f"worst_abs_spearman={certificate['worst_abs_spearman']} "
            f"unsatisfiable={certificate['unsatisfiable_criteria']}")

    # ------------------------------------------------------------- writer + card
    note = args.note or ("G64 lane: lidar scarp template + Steger/Frangi; strike-line keep-fraction; "
                         "3.4 px dots, 2 px catalogue-flank prune; surrogate holdout only")
    note = note[:140]
    final_path = args.outdir / f"{args.name}-{local['sha256'][:12]}.tif"
    tmp_path.replace(args.outdir / f"{args.name}.tif")
    staged = args.outdir / f"{args.name}.tif"
    staged.replace(final_path)
    final_info = gates_mod.format_report(final_path, args.bridge / "sample_submission.tif", footprint=grid.footprint)
    log(f"[write] {final_path.name} bytes={final_info['bytes']} sha256={final_info['sha256'][:16]}…")

    provenance = json.loads((ROOT / "evidence" / "input_pins.json").read_text()) \
        if (ROOT / "evidence" / "input_pins.json").exists() else {"pins": {}}
    provenance_check = {}
    for label, path in (("training_features", args.features), ("lidar_scarp_features", args.lidar),
                        ("road_distance", args.road_distance),
                        ("sample_submission", args.bridge / "sample_submission.tif"),
                        ("existing_faults", args.bridge / "existing_faults.tif")):
        pinned = (provenance.get("pins") or {}).get(label, {})
        digest = sha256_file(path) if path.exists() else None
        provenance_check[label] = dict(path=str(path), sha256=digest, pinned=pinned.get("sha256"),
                                       matches=bool(digest and pinned.get("sha256") == digest),
                                       source=pinned.get("source"))
    provenance_ok = all(v["matches"] for v in provenance_check.values())

    held_out = summary["scores"].get(final_name, {})
    paired_row = paired.get("INC_historical_base", {})
    seed_ok = {seed: {k: bool(v["delta"] > 0) for k, v in row["deltas"].items()}
               for seed, row in per_seed.items()}
    ensemble_ok = bool(all(all(v.values()) for v in seed_ok.values()))
    evidence = dict(
        hypothesis="Native-resolution lidar scarp evidence (scarplet-style template matching plus "
                   "Steger/Frangi line measures) with the lane's strike-line coherence statistic "
                   "recovers faults that the 100 m stack discards.",
        mechanism="Slope-detrended scarp template fits give amplitude/SNR/orientation; sub-pixel "
                  "Steger ridge/valley strength and multiscale Frangi vesselness localise the scarp "
                  "line; the strike-line consistency statistic (fraction of aligned neighbours with "
                  "evidence) is used as a keep-fraction veto on the packed dots; dots are spaced at "
                  "2.8-3.4 px and pruned on the visible catalogue flank.",
        named_non_fault_mimic="Differential erosion or deposition along a lithologic contact / "
                              "alluvial-fan edge produces a strike-coherent, slope-detrended step "
                              "with no fault slip (and can survive the strike-line veto).",
        holdout=dict(evidence_class="HOLDOUT-DTI", **{k: held_out.get(k) for k in
                     ("dti", "ci95", "withheld_positive_pixels", "tpw", "fpw", "fnw")},
                     evaluator_version=evaluate_holdout.VERSION,
                     instrument="gems57.holdout.buffered_component_draw (whole components, 3 px "
                                "context buffer, visible catalogue masked pixel-exactly); "
                                f"truth ensemble = {len(instruments)} independent draws "
                                f"(seeds {[s for s, _ in instruments]}) x 4 folds; dots on the "
                                "hidden catalogue set are removed before scoring"),
        surface_registry=dict(
            complete_accessible_scan=bool((certificate or {}).get("registry_rasters_checked")),
            rasters_checked=(certificate or {}).get("registry_rasters_checked"),
            worst_spearman=(certificate or {}).get("worst_abs_spearman"),
            worst_dot_overlap=(certificate or {}).get("worst_overlap_informative"),
            unique=(certificate or {}).get("literal_verdict_unique"),
            diagnostic_unique=(certificate or {}).get("diagnostic_verdict_unique"),
            unsatisfiable_criteria=(certificate or {}).get("unsatisfiable_criteria"),
            dense_priors=(certificate or {}).get("dense_priors"),
            scope=(certificate or {}).get("scope"),
        ),
        uniqueness_certificate=None if certificate is None else {
            k: certificate[k] for k in ("schema", "registry_rasters_checked", "errors", "my_dots",
                                        "control_draws", "control_pool_cells", "dense_priors",
                                        "informative_priors", "worst_overlap_informative",
                                        "worst_overlap_informative_file", "worst_abs_spearman",
                                        "worst_abs_spearman_file", "byte_and_pixel_unique",
                                        "literal_verdict_unique", "diagnostic_verdict_unique",
                                        "unsatisfiable_criteria")},
        validator_output=dict(status="local-prelight", all_checks_passed=local["all_checks_passed"],
                              no_nan_inside_footprint=local["checks"].get("in_footprint_all_finite"),
                              values_in_0_1=local["checks"].get("range_0_1_guaranteed"),
                              dtype_float32=local["checks"].get("dtype_float32"),
                              crs_shape_transform_match=all([
                                  local["checks"].get("crs_epsg_32611"),
                                  local["checks"].get("dimensions_3730x3292"),
                                  local["checks"].get("transform_matches_sample_submission")]),
                              format_pass=fmt["ok"], emitted_positive_pixels=local["emitted_positive_pixels"]),
        provenance=dict(verified=provenance_ok, class_="mirror-pinned, not organizer-authenticated",
                        inputs=provenance_check),
        ensemble=dict(seeds=[s for s, _ in instruments], per_seed=per_seed,
                      passed=ensemble_ok, rule="primary arm must beat every baseline in every draw"),
        oof_selection=dict(rows=oof_rows, mean_heldout_dti=oof_score,
                           selection_counts={a: oof_selected.count(a) for a in set(oof_selected)}),
        mclp_baseline=mclp_info,
        raster_sha256=final_info["sha256"],
        raster_bytes=final_info["bytes"],
        submission_name=args.name,
        note=note,
        arms={k: dict(n_dots=int(arm_choices[k](instruments[0][1][0]).sum()),
                      pooled_dti=summary["scores"][k]["dti"],
                      ci95=summary["scores"][k]["ci95"]) for k in arm_choices},
        paired_vs_incumbent=paired_row,
        paired=paired,
        leakage_canaries=canary_rows,
        scale_audit=scale_audit,
        cultural_mask_sha256=cult_sha,
        cultural_masked_cells=int(cult_mask.sum()),
        git_commit=subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                                  text=True).stdout.strip() or None,
        runtime_seconds=round(time.time() - started, 1),
        messages=messages,
    )
    decision = promotion.promotion_decision(dict(
        data_provenance_verified=provenance_ok,
        buffered_oof_verified=bool(oof_rows and all(np.isfinite(r["heldout_dti"]) for r in oof_rows)),
        feature_canaries_pass=all(not r["leakage_until_proven_otherwise"] for r in canary_rows),
        truth_ensemble_verified=ensemble_ok,
        surface_registry_pass=bool((certificate or {}).get("literal_verdict_unique")),
        final_registry_pass=bool((certificate or {}).get("literal_verdict_unique")),
        all_prior_rasters_checked=bool((certificate or {}).get("registry_rasters_checked")),
        validator_pass=bool(local["all_checks_passed"] and fmt["ok"]),
        hash_and_pixel_unique=bool((certificate or {}).get("byte_and_pixel_unique")),
        historical_best_comparable=bool(paired_row.get("beats_two_se")),
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=evaluate_holdout.VERSION,
                     dti=held_out.get("dti"), ci95=held_out.get("ci95"),
                     withheld_positive_pixels=held_out.get("withheld_positive_pixels"),
                     paired_comparisons={
                         "spacing": dict(same_surface_and_folds=True,
                                         delta=paired.get("A_spacing28", {}).get("delta"),
                                         bootstrap_se=paired.get("A_spacing28", {}).get("bootstrap_se")),
                         "mclp": dict(same_surface_and_folds=True,
                                      delta=paired.get("M_mclp_surface", {}).get("delta"),
                                      bootstrap_se=paired.get("M_mclp_surface", {}).get("bootstrap_se")),
                         "historical_best": dict(same_surface_and_folds=True,
                                                 delta=paired_row.get("delta"),
                                                 bootstrap_se=paired_row.get("bootstrap_se"))}),
    ))
    evidence["verdict"] = decision["verdict"]
    evidence["download_allowed"] = bool(decision["download_allowed"])
    evidence["failed_gates"] = decision["failed_gates"]
    evidence["submission_slots_used"] = 0
    (args.evidence / "run_card.json").write_text(json.dumps(evidence, indent=2, default=str) + "\n")
    if certificate is not None:
        (args.evidence / "uniqueness_certificate.json").write_text(
            json.dumps(certificate, indent=2, default=str) + "\n")
    log(f"[verdict] {decision['verdict']} download_allowed={decision['download_allowed']} "
        f"failed={decision['failed_gates']}")
    print(json.dumps({k: evidence[k] for k in ("verdict", "download_allowed", "raster_sha256",
                                               "submission_name", "failed_gates")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
