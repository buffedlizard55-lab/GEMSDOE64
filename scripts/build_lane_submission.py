#!/usr/bin/env python
"""End-to-end build of the GEMSDOE64 lane-64 lidar-scarp submission.

Pipeline (one process, auditable top to bottom):

1.  Load the pinned competition grid (``data/bridge``): footprint, catalogue.
2.  Load the lane feature stack (1 m lidar scarp aggregates + 10 m topography +
    GeoDAWN radiometrics/magnetics).
3.  Build the truth surrogate = independent-compilation (SGMC) faults more than
    300 m from the given catalogue, inside the footprint.
4.  Fit a truth-probability field with 16 spatially blocked out-of-fold fits.
5.  Greedy maximum-coverage dot selection on that field.
6.  Measure the surrogate DTI curve and the optimal-mass shape versus assumed
    hidden-truth size.
7.  Run the shared protocol instrument (``gems57.holdout`` buffered whole
    component hide-and-recover) for candidate, incumbent and controls, with a
    paired spatial-block bootstrap.
8.  Emit a unique float32 EPSG:32611 100 m GeoTIFF on the exact sample grid,
    all-finite, values in [0, 1].
9.  Validate the on-disk file and compare it against the whole local registry
    of prior rasters, including a matched random-null overlap control.
10. Write every receipt as JSON.

Nothing here writes a competition score.  Every numeric result is tagged
``surrogate-CV``, ``HOLDOUT-DTI`` or ``null-control``.
"""

from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import grid as gridmod          # noqa: E402
from gems57 import metric, validate as validatemod  # noqa: E402
from gems57 import gates, holdout           # noqa: E402
from gems64 import scarp_lane as lane       # noqa: E402

DATA = ROOT / "data"
REGISTRY = DATA / "registry"
EVID = ROOT / "evidence"
DOWNLOADS = ROOT / "docs" / "downloads"
WORK = ROOT / "work"
CACHE = WORK / "lane64_cache.npz"

# ---------------------------------------------------------------- configuration
LANE_NAME = "gems64-scarpcover90000"
SUBMISSION_NAME = "GEMSDOE64-scarp-cover-90000-dots"
NOTE = ("Native-resolution lidar scarp channels; blocked-CV field, greedy maximal "
        "coverage; 90000 p=1 dots; unique vs 62-raster registry")
TARGET_DOTS = 90_000           # dots shipped in the artifact
GREEDY_TARGET = 120_000        # selection drawn longer than shipped so the mass curve is closed
SURROGATE_MARGIN_PX = 3.0      # SGMC faults further than 300 m from the catalogue
KFOLD_GREEDY_POOL = 500_000
CURVE_SIZES = (10_000, 20_000, 40_000, 60_000, 80_000, 90_000, 100_000, 120_000)
K_GRID = (6_000, 8_000, 10_000, 12_226, 16_000, 25_000, 40_000, 61_664)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with Path(p).open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def dump(name: str, obj) -> Path:
    EVID.mkdir(parents=True, exist_ok=True)
    p = EVID / name
    p.write_text(json.dumps(obj, indent=2, allow_nan=False, default=str) + "\n", encoding="utf-8")
    return p


def build_features(lidar: np.ndarray, lid_valid: np.ndarray):
    """Lane feature stack.  Every band is lineage-documented in the receipts."""
    feats, names, lineage = [], [], []

    def add(name, arr, source):
        feats.append(np.asarray(arr, np.float32))
        names.append(name)
        lineage.append({"name": name, "source": source})
        return feats[-1]

    lid = {
        0: "ex_max", 1: "ex_mean", 2: "step_max", 3: "lapneg_max", 4: "lappos_max",
        5: "downface_max", 6: "upface_max", 7: "cross_max", 8: "relief", 9: "coh100",
        10: "strike", 11: "valid",
    }
    for i, n in lid.items():
        src = ("data/external/lidar_scarp_features_u8.tif "
               "(1 m lidar scarp aggregates on the 100 m grid)")
        a = lidar[i].astype(np.float32)
        if n not in ("valid", "strike"):
            a = np.where(lid_valid, a, 0.0)
        add("lidar_" + n, a, src)
    with rasterio.open(DATA / "external" / "topo_10m_derived_100m_u8.tif") as s:
        topo = s.read()
        tnames = list(s.descriptions)
    for i, n in enumerate(tnames):
        add("topo_" + n, topo[i], "data/external/topo_10m_derived_100m_u8.tif "
            "(USGS 3DEP 1/3 arc-second seamless DEM 13, https://prd-tnm.s3.amazonaws.com/"
            "StagedProducts/Elevation/13/TIFF/USGS_Seamless_DEM_13.vrt)")
    del topo
    with rasterio.open(DATA / "external" / "geodawn_rad_u8.tif") as s:
        rad = s.read(); rnames = list(s.descriptions)
    for i, n in enumerate(rnames):
        add("rad_" + n, rad[i], "data/external/geodawn_rad_u8.tif "
            "(USGS GeoDAWN airborne radiometrics)")
    del rad
    with rasterio.open(DATA / "external" / "geodawn_extensions_u8.tif") as s:
        ext = s.read(); enames = list(s.descriptions)
    for i, n in enumerate(enames):
        add("ext_" + n, ext[i], "data/external/geodawn_extensions_u8.tif "
            "(USGS GeoDAWN magnetic/radiometric ratios)")
    del ext
    gc.collect()
    return feats, names, lineage


def main() -> int:
    t0 = time.time()
    EVID.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- 1. grid
    g = gridmod.load_grid()
    fp, cat = g.footprint, g.catalogue
    active = fp & ~cat
    print(f"[1] grid {g.shape} footprint {int(fp.sum())} catalogue {int(cat.sum())} "
          f"active {int(active.sum())} t={time.time()-t0:.0f}s", flush=True)

    # ------------------------------------------------- 2. lane feature stack
    with rasterio.open(DATA / "external" / "lidar_scarp_features_u8.tif") as s:
        lidar = s.read()
        assert list(s.descriptions) == ["ex_max", "ex_mean", "step_max", "lapneg_max",
                                        "lappos_max", "downface_max", "upface_max",
                                        "cross_max", "relief", "coh100", "strike", "valid"]
    lid_valid = lidar[11] > 0
    feats, names, lineage = build_features(lidar, lid_valid)
    del lidar
    gc.collect()
    print(f"[2] {len(feats)} feature bands; lidar-covered cells "
          f"{int((lid_valid & fp).sum())} of {int(fp.sum())} "
          f"({100*float((lid_valid & fp).sum())/float(fp.sum()):.1f}%) t={time.time()-t0:.0f}s",
          flush=True)

    # --------------------------------------------------- 3. truth surrogate
    with rasterio.open(DATA / "external" / "sgmc_faults_100m.tif") as s:
        sgmc = s.read(1) > 0
    d_cat = ndi.distance_transform_edt(~cat)
    surrogate = sgmc & fp & (d_cat > SURROGATE_MARGIN_PX) & ~cat
    print(f"[3] surrogate SGMC-off pixels {int(surrogate.sum())} "
          f"({100*float(surrogate.sum())/float(sgmc.sum()):.1f}% of SGMC in-region)",
          flush=True)

    # ------------------------------------------- 4/5. field + greedy selection
    if CACHE.exists():
        z = np.load(CACHE)
        surf, order = z["surf"], z["order"]
        fold_receipts = json.loads(str(z["fold_receipts"])) if "fold_receipts" in z else []
        print(f"[4] cache hit {CACHE.name}", flush=True)
    else:
        fold = lane.fold_ids(g.shape)
        surf, fold_receipts = lane.fit_blocked_field(feats, names, surrogate, active, fold)
        dots, gains, order = lane.greedy_max_cover(surf, active, target=GREEDY_TARGET,
                                                   pool=KFOLD_GREEDY_POOL)
        np.savez_compressed(CACHE, surf=surf, order=order, gains=gains,
                            fold_receipts=json.dumps(fold_receipts))
        print(f"[4/5] field + greedy done, {order.size} dots t={time.time()-t0:.0f}s",
              flush=True)
    print(f"[4/5] field surface ready, selection length {order.size} "
          f"t={time.time()-t0:.0f}s", flush=True)

    # -------------------------------------------------- 6. surrogate DTI curve
    curve = lane.dti_curve(order, surrogate, active, CURVE_SIZES)
    mass_curve = lane.optimal_mass_curve(curve, K_GRID)
    print("[6] surrogate curve " + " ".join(
        f"S={s}:{v['surrogate_dti']:.4f}" for s, v in curve.items()), flush=True)

    # --------------------------------------------------------- 7. final dots
    dots = np.zeros(g.shape, bool)
    dots.ravel()[order[:TARGET_DOTS]] = True
    dots &= active
    assert not (dots & cat).any()

    # ------------------------------------- 8. protocol hide-and-recover folds
    folds, quad = holdout.buffered_component_draw(g, seed=20, hide_frac=0.20,
                                                 buffer_px=3, boundary_px=holdout.DOMAIN_ERODE)
    with rasterio.open(REGISTRY / "GEMSDOE32__h33-2-b2-zeros.tif") as s:
        incumbent = s.read(1) > 0
    rng = np.random.default_rng(4242)
    rand = np.zeros(g.shape, bool)
    rand.ravel()[rng.choice(np.flatnonzero(active.ravel()), TARGET_DOTS, replace=False)] = True
    arms = {"lane64_scarpcover": dots, "incumbent_h33_2_b2": incumbent, "random_control": rand}

    from gems57 import evaluate_holdout
    terms_by_arm = {}
    per_fold_rows = []
    for fold in folds:
        for arm, arr in arms.items():
            res, terms = evaluate_holdout.evaluate(arr, fold, g.footprint, block_side=200)
            terms_by_arm.setdefault(arm, []).append(terms)
            if arm == "lane64_scarpcover":
                per_fold_rows.append(dict(fold=fold["name"], **{
                    k: res[k] for k in ("tpw", "fpw", "fnw", "n_truth", "n_emitted", "dti")}))
    pooled_terms = {a: np.concatenate(v, axis=0) for a, v in terms_by_arm.items()}
    boots = evaluate_holdout.pooled_summary(pooled_terms, draws=1000, seed=520810,
                                            candidate="lane64_scarpcover")
    print("[7] catalogue-component instrument HOLDOUT-DTI " + " | ".join(
        f"{a}={boots['scores'][a]['dti']:.6f} [{boots['scores'][a]['ci95'][0]:.6f},"
        f"{boots['scores'][a]['ci95'][1]:.6f}]" for a in arms), flush=True)

    # ------------------- 7b. population-matched blocked instrument (lane-appropriate)
    # Target = the truth surrogate itself, hidden by whole 32 km super-blocks, with
    # the field re-derived only from the other blocks (it already is: the surface is
    # out-of-fold).  Each block gets a dot budget proportional to its active area, so
    # the pooled mass matches the shipped artifact.
    foldmap = lane.fold_ids(g.shape)
    budget_total = int(TARGET_DOTS)
    active_total = int(active.sum())
    lane_dots_blocked = np.zeros(g.shape, bool)
    dcat_active = np.where(active, d_cat, np.inf)
    dist_dots_blocked = np.zeros(g.shape, bool)
    budget_rows = []
    for q in np.unique(foldmap[active]):
        region = (foldmap == q) & active
        n_reg = int(region.sum())
        if n_reg == 0:
            continue
        budget = max(1, int(round(budget_total * n_reg / active_total)))
        sub, _g, sub_order = lane.greedy_max_cover(surf, region, target=budget, pool=n_reg + 1)
        lane_dots_blocked |= sub
        budget_rows.append(dict(fold=int(q), active_px=n_reg, budget=budget))
        reg_flat = np.flatnonzero(region.ravel())
        order_dist = reg_flat[np.argsort(dcat_active.ravel()[reg_flat])[:budget]]
        dsub = np.zeros(g.shape, bool)
        dsub.ravel()[order_dist] = True
        dist_dots_blocked |= dsub
        del sub, dsub, sub_order, reg_flat, order_dist
        gc.collect()
    boots_matched = {}
    matched_arms = {"lane64_scarpcover_blocked": lane_dots_blocked,
                    "incumbent_h33_2_b2": incumbent, "random_control": rand,
                    "distance_to_catalogue_only": dist_dots_blocked}
    terms2 = {}
    for q in np.unique(foldmap[active]):
        region = (foldmap == q) & active
        if not (surrogate & region).any():
            continue
        fdict = dict(name=f"SB{int(q)}", region=region, truth=surrogate & region,
                     visible=cat, masked_known=cat)
        for arm, arr in matched_arms.items():
            _res, terms = evaluate_holdout.evaluate(arr, fdict, g.footprint, block_side=200)
            terms2.setdefault(arm, []).append(terms)
    pooled2 = {a: np.concatenate(v, axis=0) for a, v in terms2.items()}
    boot_matched = evaluate_holdout.pooled_summary(
        pooled2, draws=1000, seed=520810, candidate="lane64_scarpcover_blocked")
    print("[7b] population-matched blocked instrument DTI " + " | ".join(
        f"{a}={boot_matched['scores'][a]['dti']:.6f} "
        f"[{boot_matched['scores'][a]['ci95'][0]:.6f},{boot_matched['scores'][a]['ci95'][1]:.6f}]"
        for a in matched_arms), flush=True)

    # ------------------------------------------------------ 9. write the file
    values = np.where(dots, 1.0, 0.0).astype(np.float32)
    assert np.isfinite(values).all() and values.min() >= 0 and values.max() <= 1
    tif = DOWNLOADS / f"{LANE_NAME}-{sha256_bytes(values.tobytes())[:8]}-zeros.tif"
    zip_path = tif.with_suffix(".zip")
    for p in (tif, zip_path, tif.with_suffix(".json")):
        if p.exists():
            p.unlink()
    gridmod.write_submission(tif, values, mode="zeros")
    receipt = validatemod.validate(tif, footprint=fp, catalogue=cat)
    validatemod.assert_submittable(receipt)
    fmt = gates.format_report(tif, DATA / "bridge" / "sample_submission.tif", footprint=fp)
    assert fmt["ok"], fmt["problems"]
    # single-TIFF zip
    import zipfile
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(tif.name, tif.read_bytes())
    print(f"[8] wrote {tif.name} sha256={receipt['sha256']} "
          f"positives={receipt['emitted_positive_pixels']} t={time.time()-t0:.0f}s", flush=True)

    # ------------------------------------------------- 10. registry uniqueness
    rows, null_rows = [], []
    idx = rng.choice(np.flatnonzero(active.ravel()), 20_000, replace=False)
    ny, nx = np.divmod(idx, g.shape[1])
    for p in sorted(REGISTRY.glob("*.tif")):
        with rasterio.open(p) as s:
            if s.shape != g.shape or s.count != 1:
                rows.append(dict(file=p.name, error=f"grid/band mismatch {s.shape}/{s.count}"))
                continue
            a = s.read(1)
        pos = np.isfinite(a) & (a > 0) & fp
        if not pos.any():
            rows.append(dict(file=p.name, their_dots=0, their_dots_within_3px=0.0))
            continue
        dg = ndi.distance_transform_edt(~pos)
        rows.append(dict(
            file=p.name, sha256=sha256_file(p), their_dots=int(pos.sum()),
            my_dots_within_3px_of_theirs=float((dg[dots] <= metric.RADIUS_PX).mean()),
            null_fraction_active_within_3px=float((dg[ny, nx] <= metric.RADIUS_PX).mean()),
            jaccard_dot_sets=float((dots & pos).sum() / max((dots | pos).sum(), 1)),
        ))
    for r in rows:
        if "my_dots_within_3px_of_theirs" in r:
            r["excess_over_null"] = r["my_dots_within_3px_of_theirs"] - r["null_fraction_active_within_3px"]
    worst_ov = max((r for r in rows if "my_dots_within_3px_of_theirs" in r),
                   key=lambda r: r["my_dots_within_3px_of_theirs"], default=None)
    worst_excess = max((r for r in rows if "excess_over_null" in r),
                       key=lambda r: r["excess_over_null"], default=None)
    unsat = [r["file"] for r in rows if r.get("null_fraction_active_within_3px", 0) > 0.70]
    print(f"[9] uniqueness: worst literal overlap "
          f"{worst_ov['my_dots_within_3px_of_theirs']:.4f} ({worst_ov['file']}); "
          f"worst excess over null {worst_excess['excess_over_null']:.4f} "
          f"({worst_excess['file']})", flush=True)

    # --------------------------------------- rank-correlation (surface check)
    rho_rows = []
    from scipy.stats import spearmanr
    for p in sorted(REGISTRY.glob("*.tif")):
        with rasterio.open(p) as s:
            if s.shape != g.shape or s.count != 1:
                continue
            b = s.read(1)
        b = np.where(np.isfinite(b), b, 0.0)
        b[~fp] = 0.0
        mine = values[fp]
        theirs = b[fp].astype(np.float64)
        if np.ptp(theirs) == 0 or np.ptp(mine) == 0:
            continue
        r = float(spearmanr(mine, theirs).statistic)
        rho_rows.append(dict(file=p.name, spearman_full_footprint=r, abs_rho=abs(r)))
    rho_rows.sort(key=lambda r: -r["abs_rho"])

    # ------------------------------------------------------------- receipts
    run_card = {
        "lane": "native-resolution lidar scarp channels (method paragraph)",
        "submission_name": SUBMISSION_NAME,
        "submission_note": NOTE,
        "note_chars": len(NOTE),
        "artifact": tif.name,
        "artifact_sha256": receipt["sha256"],
        "artifact_bytes": receipt["bytes"],
        "dots": int(dots.sum()),
        "dot_value": 1.0,
        "outside_footprint": 0.0,
        "hypothesis": ("1 m lidar resolves fresh fault scarps whose 100 m expression is "
                       "below the resolution of the shared stack; aggregated scarp amplitude, "
                       "ridge/valley (Laplace) and cross-scarp (Hessian) responses plus "
                       "structure-tensor coherence and strike therefore rank true fault "
                       "ground that the published catalogue does not carry."),
        "mechanism": ("scarplet-style template amplitude and Hessian line responses are "
                      "computed on bare-earth lidar, collapsed to 100 m as scarp-pixel "
                      "fraction, SNR-weighted amplitude, orientation coherence and dominant "
                      "strike; a spatially blocked logistic field is fitted to independent "
                      "compilation faults >300 m off the catalogue, then a lazy greedy "
                      "maximum-coverage selector places the dots."),
        "non_fault_mimic": ("anthropogenic linear features (roads, canals, field edges, "
                            "pipelines, cut banks) and lithology-controlled benches produce "
                            "identical scarp morphology; no cultural-feature mask is "
                            "available in this checkout, so this mimic is uncontrolled here "
                            "and is recorded as a limitation rather than claimed as masked."),
        "surrogate_truth": {"name": "USGS SGMC faults >300 m from the given catalogue",
                            "pixels": int(surrogate.sum()),
                            "evidence_class": "surrogate-CV (not HOLDOUT-DTI, not a score)"},
        "surrogate_cv_dti_curve": curve,
        "optimal_mass_shape": mass_curve,
        "instrument_A_catalogue_component_holdout": {
            "purpose": ("the shared reuse-template instrument: hide whole mapped catalogue "
                        "components and score recovery"),
            "evaluator_version": boots["evaluator_version"],
            "masks": "buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3)",
            "scores": boots["scores"],
            "paired_differences": boots["paired_differences"],
            "per_fold": per_fold_rows,
            "interpretation": ("this instrument's truth is the published catalogue, and the "
                               "lane's field is fitted to be OFF-catalogue by construction, "
                               "so the instrument is anti-correlated with the lane objective; "
                               "a covering random field wins it.  See instrument B."),
        },
        "instrument_B_population_matched_blocked": {
            "purpose": ("lane-appropriate hide-and-recover: withhold whole 32 km super-blocks "
                        "of the population-matched truth (independent-compilation faults "
                        ">300 m off the catalogue) and score blocks the field never saw"),
            "evaluator_version": boot_matched["evaluator_version"],
            "masks": "16 super-blocks, 32 km each, out-of-fold field, mass-matched budgets",
            "block_budgets": budget_rows,
            "scores": boot_matched["scores"],
            "paired_differences": boot_matched["paired_differences"],
        },
        "registry_worst_literal_overlap": worst_ov,
        "registry_worst_excess_over_null": worst_excess,
        "registry_rasters_compared": len(rows),
        "registry_rasters_whose_null_exceeds_the_rule": unsat,
        "worst_rank_correlation": rho_rows[0] if rho_rows else None,
        "verdict": ("promote-to-selector-only"
                    if boot_matched["scores"]["lane64_scarpcover_blocked"]["dti"]
                    > boot_matched["scores"]["random_control"]["dti"]
                    and boot_matched["paired_differences"]["random_control"]["beats_two_se"]
                    else "negative"),
        "verdict_rule": ("instrument B (population-matched blocked hide-and-recover) must beat "
                         "the mass-matched random control by more than two paired spatial-block "
                         "bootstrap standard errors; instrument A is reported but cannot gate "
                         "this lane because its truth is the published catalogue"),
        "evidence_class": "HOLDOUT-DTI and surrogate-CV; never an organizer score",
        "submission_slots_used": 0,
    }
    dump("lane64_run_card.json", run_card)
    dump("lane64_validator.json", {"local_preflight": receipt, "format_report": fmt})
    dump("lane64_uniqueness.json", {
        "candidate": tif.name, "candidate_sha256": receipt["sha256"],
        "my_dots": int(dots.sum()),
        "rows": rows,
        "worst_literal_overlap": worst_ov,
        "worst_excess_over_null": worst_excess,
        "rank_correlation_rows": rho_rows,
        "rule_rho_limit": 0.90, "rule_overlap_limit": 0.70,
        "literal_rule_unsatisfiable_against": unsat,
        "evidence_class": "REGISTRY-MEASUREMENT",
        "scope": ("the local registry copy of 62 prior rasters; not a complete organizer "
                  "registry, and not proof of uniqueness against unpublished work"),
    })
    dump("lane64_surrogate_curve.json", {
        "truth_surrogate": "SGMC faults >300 m off the given catalogue",
        "surrogate_pixels": int(surrogate.sum()),
        "footprint_pixels": int(fp.sum()),
        "curve": curve, "optimal_mass_shape": mass_curve,
        "feature_lineage": lineage,
        "fold_receipts": fold_receipts,
        "evidence_class": "surrogate-CV",
    })
    print(f"[done] t={time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
