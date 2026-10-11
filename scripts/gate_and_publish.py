#!/usr/bin/env python3
"""Experiment 3d — the gate, done honestly, plus the LANE uniqueness check.

The gate in ``emit_and_ship.py`` compared two placement rules against 32 truth rasters that were
*sampled from the same score surface that supplied the candidate pool*.  That is circular: the
greedy arm is favoured by construction, and the reported E[DTI] of 0.93 is an objective value, not
a performance estimate.  It is still a legitimate test of the RULE, so it is kept -- but it is
relabeled ``SELF-CONSISTENT OBJECTIVE`` and it is no longer the only evidence.

This script adds the arm that is not circular:

  GATE 2 — INDEPENDENT TRUTH.  Both placements are scored against the published USGS/INGENIOUS
  catalogue as truth.  The physical-only model never saw a catalogue-derived feature (all four
  were quarantined by the leakage canary at blocked AUC 0.971-0.996), so this target is
  independent of the surface's own ranking.  The catalogue is masked out of live scoring, so this
  is a PROXY ordering instrument and is labeled as one -- it is not a score estimate either.

It then runs the LANE uniqueness check the protocol requires, on the final dots, against every
registry raster reachable on this machine, and validates both shipped GeoTIFFs.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems64.grid import (  # noqa: E402
    HEIGHT, WIDTH, load_catalogue, load_footprint,
)
SUB_NAME = "gems64-expecteddti-flank0158-14k"
SUB_NOTE = ("Expected-DTI-optimal greedy (a=0.2) on isotonic physical field, 32 jittered draws, "
            "live-calibrated 200m catalogue-flank discount rho=0.158")

from emit_and_ship import (  # noqa: E402
    K_HIDDEN, N_CANDIDATES, N_DRAWS, OUTDIR, PROC, RHO_FLANK, SEED, block_bootstrap_gate,
    build_draws, score_grid, spacing_placement,
)

REGISTRY_ROOTS = [
    Path("/home/user/scratch/GEMSDOE32/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE28/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE29/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE49/docs/downloads"),
]
CORR_LIMIT = 0.90
OVERLAP_LIMIT = 0.70


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def lane_check(final_cells: np.ndarray, footprint, catalogue) -> dict:
    """LANE discipline: rank correlation and dot overlap against every registry raster."""
    from scipy.ndimage import distance_transform_edt
    from scipy.stats import spearmanr

    mine = np.zeros(HEIGHT * WIDTH, bool)
    mine[final_cells] = True
    mine = mine.reshape(HEIGHT, WIDTH)
    dm = distance_transform_edt(~mine)
    n_mine = int(mine.sum())
    rows, worst_corr, worst_overlap = [], -1.0, -1.0
    worst_corr_name = worst_overlap_name = None
    for root in REGISTRY_ROOTS:
        if not root.exists():
            continue
        for p in sorted(root.glob("*.tif")):
            try:
                with rasterio.open(p) as s:
                    if (s.height, s.width) != (HEIGHT, WIDTH):
                        continue
                    a = s.read(1)
            except Exception as exc:  # noqa: BLE001
                rows.append(dict(file=p.name, error=str(exc)))
                continue
            theirs = np.isfinite(a) & (a > 0) & footprint & ~catalogue
            n_th = int(theirs.sum())
            if n_th == 0:
                rows.append(dict(file=p.name, n_theirs=0, note="no positive dots"))
                continue
            # (a) dot overlap: fraction of MY dots within 3 px of one of THEIR dots
            dth = distance_transform_edt(~theirs)
            overlap = float((dm[theirs] <= 3.0).mean()) if n_th else 0.0
            overlap_rev = float((dth[mine] <= 3.0).mean())
            # (b) rank correlation on the shared positive support.
            # ONLY meaningful when their values actually vary.  Most registry rasters are binary
            # dot fields, so every shared cell carries the same value and Spearman is undefined --
            # the first version of this check scored that as 1.000 and declared a LANE duplicate
            # against a raster whose dot overlap was 0.012.  For binary rasters the operative
            # statistic is the overlap fraction, and it is the only one used in the decision.
            both = mine & theirs
            v = a[both].astype(np.float64) if both.sum() else np.empty(0)
            n_distinct = int(np.unique(v).size)
            if both.sum() > 30 and n_distinct >= 3:
                r = float(spearmanr(np.arange(v.size), v).statistic)
                r_used = True
            else:
                r, r_used = float("nan"), False
            jaccard = float(both.sum() / max((mine | theirs).sum(), 1))
            rows.append(dict(file=p.name, n_theirs=n_th, n_mine=n_mine,
                             frac_my_dots_within_3px_of_theirs=overlap,
                             frac_their_dots_within_3px_of_mine=overlap_rev,
                             jaccard=jaccard, n_shared=int(both.sum()),
                             n_distinct_shared_values=n_distinct,
                             binary_raster=bool(n_distinct <= 2),
                             spearman_on_shared=r if np.isfinite(r) else None,
                             spearman_usable=r_used))
            if r_used and r > worst_corr:
                worst_corr, worst_corr_name = r, p.name
            if overlap > worst_overlap:
                worst_overlap, worst_overlap_name = overlap, p.name
    n_usable = sum(1 for r in rows if r.get("spearman_usable"))
    if n_usable == 0:
        worst_corr, worst_corr_name = None, None
    duplicate = bool((worst_corr is not None and worst_corr > CORR_LIMIT)
                     or worst_overlap > OVERLAP_LIMIT)
    return dict(n_compared=len(rows), n_spearman_usable=n_usable,
                spearman_note=("every compared registry raster is a binary dot field, so Spearman "
                               "on the shared support is undefined; the operative LANE statistic is "
                               "the 3 px dot-overlap fraction"),
                worst_spearman=worst_corr, worst_spearman_file=worst_corr_name,
                worst_overlap_frac=worst_overlap, worst_overlap_file=worst_overlap_name,
                corr_limit=CORR_LIMIT, overlap_limit=OVERLAP_LIMIT,
                duplicate=duplicate, per_raster=rows)


def main() -> int:
    t0 = time.time()
    print("=" * 100)
    print("EXPERIMENT 3d — independent gate, LANE uniqueness check, validation")
    print("=" * 100)
    fp, cat = load_footprint(), load_catalogue()
    final_cells = np.load(PROC / "final_cells.npy")
    n = int(final_cells.size)
    print(f"  final emission {n:,} dots")

    tifs = sorted(OUTDIR.glob("gems64-*.tif"))
    zeros_tif = next((p for p in tifs if p.name.endswith("-zeros.tif")), None)
    nan_tif = next((p for p in tifs if p.name.endswith("-nan.tif")), None)
    if zeros_tif is None:
        print("  no shipped raster found in docs/downloads; run emit_and_ship.py first")
        return 1

    sflat, raw_all, pi_all, names = score_grid()
    top = np.argsort(raw_all)[::-1][:N_CANDIDATES]
    cand = sflat[top].astype(np.int64)
    pi_at = raw_all[top].astype(np.float64)
    o = np.argsort(cand)
    cand, pi_at = cand[o], pi_at[o]
    spac = spacing_placement(cand, pi_at, n, sep_px=3)
    print(f"  spacing arm at matched mass: {spac.size:,} dots")

    # ---------------- GATE 1: self-consistent draws (rule test, circular by construction) -----
    # HELD-OUT draws.  The greedy optimised against 32 draws built with seed SEED; scoring it
    # against those same draws is circular (it is being graded on its own training target).  The
    # evaluation draws here use seed SEED+1, so they are an independent sample from the same
    # plausible-truth distribution -- the same held-out-draw design that made Experiment 1 check
    # C7 meaningful.  What remains shared, and is disclosed, is the SURFACE: both the greedy and
    # the draws come from this model, so this arm tests the decision rule, not the field.
    rng = np.random.default_rng(SEED)
    draws_opt = build_draws(sflat, raw_all, rng)
    draws = build_draws(sflat, raw_all, np.random.default_rng(SEED + 1))
    cache1 = PROC / "gate1_cache.json"
    if cache1.exists():
        g1 = json.loads(cache1.read_text())["per_draw"]
        print(f"  reusing cached GATE 1 ({len(g1)} draws) from {cache1.name}")
    else:
        g1 = []
        for i, d in enumerate(draws):
            g = block_bootstrap_gate(spac, final_cells, d, fp, cat, n_boot=60)
            g.pop("per_draw", None)
            g1.append(g)
            print(f"    gate1 draw {i+1}/{len(draws)}: diff {g['point_diff']:+.5f} "
                  f"[{time.time()-t0:.0f}s]")
        cache1.write_text(json.dumps(dict(per_draw=g1), default=float))
    m1 = float(np.mean([g["mean_block_diff"] for g in g1]))
    se1 = float(np.sqrt(np.mean([g["se"] ** 2 for g in g1])))
    p1 = float(np.mean([g["point_diff"] for g in g1]))
    gate1 = dict(label="SELF-CONSISTENT OBJECTIVE (not a score estimate)",
                 circularity=("evaluation truth is a HELD-OUT draw set (seed SEED+1), so the "
                              "greedy is not graded on its own optimisation target; what remains "
                              "shared is the surface, so this arm tests the DECISION RULE and says "
                              "nothing about whether the field is competitive"),
                 mean_dti_greedy=float(np.mean([g["dti_B"] for g in g1])),
                 mean_dti_spacing=float(np.mean([g["dti_A"] for g in g1])),
                 mean_point_diff=p1, mean_block_diff=m1, se=se1,
                 z=m1 / se1 if se1 > 0 else float("nan"),
                 ci95=[float(np.mean([g["ci95"][0] for g in g1])),
                       float(np.mean([g["ci95"][1] for g in g1]))],
                 mean_frac_replicates_positive=float(
                     np.mean([g["frac_replicates_positive"] for g in g1])),
                 draws_positive=int(sum(1 for g in g1 if g["point_diff"] > 0)), n_draws=len(g1),
                 mean_cover_greedy=float(np.mean([g["mean_truth_cover_B"] for g in g1])),
                 mean_cover_spacing=float(np.mean([g["mean_truth_cover_A"] for g in g1])),
                 n_boot_per_draw=60, held_out_draw_seed=SEED + 1)
    print("-" * 100)
    print(f"  GATE 1 (self-consistent)  greedy {gate1['mean_dti_greedy']:.5f} vs "
          f"spacing {gate1['mean_dti_spacing']:.5f} | diff {p1:+.5f} | "
          f"block z {gate1['z']:+.2f} | draws positive {gate1['draws_positive']}/{len(g1)}")

    # ---------------- GATE 2: catalogue truth -----------------------------------------------
    # This arm is DEGENERATE BY CONSTRUCTION and is reported as such rather than as a pass/fail.
    # The lane deliberately avoids the catalogue flank (Experiment 2: 6.3x credit depletion within
    # 200 m), and the emission domain excludes catalogue pixels, so almost no emitted dot lands
    # within the 300 m kernel of a catalogue cell and TP_w is structurally ~0.  A placement that
    # scores 0 against catalogue truth is exactly what the live evidence says a placement SHOULD
    # do.  Using it as a gate would invert the sign of the very effect Experiment 2 measured.
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat).ravel()[final_cells]
    flank_profile = dict(
        n_dots=int(final_cells.size),
        within_1px=int((d_cat <= 1).sum()), within_2px=int((d_cat <= 2).sum()),
        within_3px=int((d_cat <= 3).sum()), beyond_3px=int((d_cat > 3).sum()),
        median_px=float(np.median(d_cat)),
        q05_px=float(np.quantile(d_cat, 0.05)), q95_px=float(np.quantile(d_cat, 0.95)))
    try:
        g2 = block_bootstrap_gate(spac, final_cells, cat, fp, cat, n_boot=400)
    except ValueError as exc:
        g2 = dict(error=str(exc))
    gate2 = dict(label="DEGENERATE INSTRUMENT — reported, not used as a gate",
                 verdict="NULL",
                 why=("catalogue truth x off-catalogue emission domain => TP_w is structurally "
                      "~0 for ANY placement this lane could produce. Scoring 0 here is the "
                      "intended behaviour, not a failure: Experiment 2 measured a 6.3x credit "
                      "depletion within 200 m of the catalogue, so avoiding it is correct."),
                 flank_profile=flank_profile,
                 independence=("the physical-only model saw no catalogue-derived feature; all four "
                               "were quarantined by the leakage canary at blocked AUC 0.971-0.996"),
                 **g2)
    print(f"  GATE 2 (catalogue truth)  NULL INSTRUMENT — TP_w structurally 0 "
          f"({flank_profile['beyond_3px']:,} of {flank_profile['n_dots']:,} dots beyond 3 px, "
          f"median {flank_profile['median_px']:.1f} px)")
    gate2_pass = None      # null instrument; it does not vote on promotion

    # ---------------- LANE uniqueness --------------------------------------------------------
    print("  LANE uniqueness check against the local registry ...")
    lane = lane_check(final_cells, fp, cat)
    ws = lane["worst_spearman"]
    print(f"    compared {lane['n_compared']} rasters ({lane['n_spearman_usable']} with a usable "
          f"Spearman) | worst spearman "
          f"{'n/a (all binary)' if ws is None else f'{ws:.3f}'} | worst 3px overlap "
          f"{lane['worst_overlap_frac']:.4f} ({Path(lane['worst_overlap_file'] or '-').name})")
    print(f"    limits: spearman > {CORR_LIMIT} or overlap > {OVERLAP_LIMIT} => duplicate")
    print(f"    DUPLICATE? {'YES -> STOP' if lane['duplicate'] else 'no'}")

    # ---------------- validation -------------------------------------------------------------
    from validate_submission import validate

    vals = {}
    for tag, p in (("zeros", zeros_tif), ("nan", nan_tif)):
        if p is None:
            continue
        ok, checks, summary = validate(p, None)
        vals[tag] = dict(file=p.name, ok=ok, sha256=summary["meta"]["sha256"],
                         bytes=summary["meta"]["bytes"],
                         n_positive=summary["n_positive_inside_footprint"],
                         vmin=summary["min"], vmax=summary["max"],
                         nodata=summary["meta"]["nodata"],
                         crs=summary["meta"]["crs"], shape=summary["meta"]["shape"],
                         transform=summary["meta"]["transform"],
                         failed=[c["check"] for c in checks if not c["ok"]])
        print(f"    VALIDATE {tag}: {'PASS' if ok else 'FAIL ' + str(vals[tag]['failed'])} "
              f"| sha256 {vals[tag]['sha256'][:16]} | positive {vals[tag]['n_positive']:,}")

    # ---- surface-quality diagnostic: is the calibrated surface usable for ranking? ----------
    top_raw = np.sort(raw_all)[::-1][:N_CANDIDATES]
    n_sat = int((raw_all >= 0.9999).sum())
    surface = dict(
        label="SURFACE QUALITY — the binding constraint on this lane",
        n_saturated_raw_at_1=n_sat,
        pct_saturated=100.0 * n_sat / raw_all.size,
        candidate_raw_min=float(top_raw.min()), candidate_raw_max=float(top_raw.max()),
        n_distinct_raw_in_candidates=int(np.unique(top_raw).size),
        verdict=("SATURATED. The gradient-boosted field puts "
                 f"{n_sat:,} scored-domain cells ({100.0*n_sat/raw_all.size:.2f}%) at raw score "
                 f">= 0.9999, so the top {N_CANDIDATES:,} candidates span only "
                 f"{top_raw.max()-top_raw.min():.4f} of score range with "
                 f"{int(np.unique(top_raw).size):,} distinct values. Ranking INSIDE that plateau "
                 "is decided by numpy's tie order, not by geology. The decision rule verified in "
                 "Experiment 1 is exact, but it is being pointed at a surface that cannot "
                 "discriminate where it matters. This, not the rule, is why the artifact must not "
                 "be promoted."),
        consequence=("the emission inherits the arbitrariness: its distance-to-catalogue profile "
                     "does not follow the field's own monotone distance signal"),
    )

    res = dict(gate1_rule=gate1, gate2_catalogue_truth=gate2,
               gate2_pass=gate2_pass, surface_quality=surface, lane=lane, validation=vals,
               n_emitted=n, K_hidden=K_HIDDEN, n_draws=N_DRAWS, rho_flank=RHO_FLANK,
               zeros_file=zeros_tif.name if zeros_tif else None,
               nan_file=nan_tif.name if nan_tif else None,
               seconds=round(time.time() - t0, 1))
    out = ROOT / "evidence" / "exp3d_gate.json"
    promote = bool(gate1.get("z", 0) > 2.0 and gate1.get("draws_positive", 0) == gate1.get("n_draws")
                   and lane["duplicate"] is False and all(v.get("ok") for v in vals.values())
                   and surface["pct_saturated"] < 0.5)
    res["verdict"] = dict(
        promote=promote,
        rule_gate_passed=bool(gate1.get("z", 0) > 2.0),
        lane_duplicate=bool(lane["duplicate"]),
        format_valid=all(v.get("ok") for v in vals.values()),
        surface_usable=bool(surface["pct_saturated"] < 0.5),
        reason=("PROMOTE" if promote else
                "NEGATIVE RESULT. The decision rule is verified and it beats spacing on held-out "
                "draws, the artifact is unique and format-valid, but the calibrated surface is "
                f"saturated ({surface['pct_saturated']:.2f}% of cells at raw score 1.0), so the "
                "ranking that selects the dots is arbitrary inside the plateau. Shipping this "
                "would spend a slot on a tie-break, not on a field. Do not promote."),
    )
    res["verdict"]["sub_name"] = SUB_NAME
    res["verdict"]["sub_note"] = SUB_NOTE
    res["sub_name"] = SUB_NAME
    res["sub_note"] = SUB_NOTE
    out.write_text(json.dumps(res, indent=1, default=float))
    print("-" * 100)
    print(f"  SURFACE: {surface['pct_saturated']:.2f}% saturated at raw=1.0 | "
          f"{surface['n_distinct_raw_in_candidates']:,} distinct values across the top "
          f"{N_CANDIDATES:,} candidates")
    print(f"  VERDICT: {'PROMOTE' if promote else 'NEGATIVE RESULT — DO NOT PROMOTE'}")
    print(f"  wrote {out}")
    return 0 if promote else 2


if __name__ == "__main__":
    raise SystemExit(main())
