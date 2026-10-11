#!/usr/bin/env python3
"""Experiment 3d — the gate, done honestly, plus the LANE uniqueness check.

The gate in ``lane_expecteddti_emit_and_ship.py`` compared two placement rules against 32 truth rasters that were
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
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems64.lane_expecteddti.gridext import (  # noqa: E402
    HEIGHT, WIDTH, load_catalogue, load_footprint,
)
SUB_NAME = "gems64-expecteddti-flank0158-14k"
SUB_NOTE = ("Expected-DTI-optimal greedy (a=0.2) on isotonic physical field, 32 jittered draws, "
            "live-calibrated 200m catalogue-flank discount rho=0.158")

from lane_expecteddti_emit_and_ship import (  # noqa: E402
    K_HIDDEN, N_CANDIDATES, N_DRAWS, OUTDIR, PROC, RHO_FLANK, SEED, block_bootstrap_gate,
    build_draws, score_grid, spacing_placement,
)

# The registry rasters live OUTSIDE this repository (sibling clones), so the LANE uniqueness check
# is only as good as their reachability.  Override with GEMS64_REGISTRY_ROOTS (os.pathsep-separated)
# to point at a different checkout; the defaults are the sandbox layout this lane was run in.
_DEFAULT_REGISTRY_ROOTS = [
    Path("/home/user/scratch/GEMSDOE32/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE28/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE29/docs/downloads"),
    Path("/home/user/scratch/GEMSDOE49/docs/downloads"),
]
_env_roots = os.environ.get("GEMS64_REGISTRY_ROOTS")
REGISTRY_ROOTS = ([Path(x) for x in _env_roots.split(os.pathsep) if x.strip()]
                  if _env_roots else _DEFAULT_REGISTRY_ROOTS)
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
    roots_present, roots_missing = [], []
    for root in REGISTRY_ROOTS:
        if not root.exists():
            roots_missing.append(str(root))
            continue
        roots_present.append(str(root))
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
    # A comparison against ZERO registry rasters is not evidence of uniqueness.  The previous
    # version left worst_overlap at its -1.0 sentinel in that case and returned duplicate=False,
    # which would have certified the artifact unique on an empty check -- the same class of silent
    # vacuous pass as the catalogue-truth gate arm.  Report UNVERIFIED instead.
    certified = len(rows) > 0
    if certified:
        duplicate = bool((worst_corr is not None and worst_corr > CORR_LIMIT)
                         or worst_overlap > OVERLAP_LIMIT)
    else:
        duplicate = None
    return dict(n_compared=len(rows), n_spearman_usable=n_usable,
                lane_certified=certified,
                registry_roots_present=roots_present, registry_roots_missing=roots_missing,
                unverified_note=(None if certified else
                                 "UNVERIFIED: no registry raster was reachable, so uniqueness was "
                                 "NOT established. duplicate is reported as null, not false."),
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
        print(f"  no shipped raster found in {OUTDIR}; run lane_expecteddti_emit_and_ship.py first")
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
    # Use the SHARED validator (gems64.validate), not a private one.  This lane originally shipped
    # its own src/gems64/validate.py (shared); main already has one, so the fork is dropped and the
    # shared tool is called with the footprint and catalogue so its in-footprint and
    # zero-dots-on-catalogue checks are exercised too.
    from gems64.validate import assert_submittable, validate

    vals = {}
    for tag, pth in (("zeros", zeros_tif), ("nan", nan_tif)):
        if pth is None:
            continue
        rec = validate(pth, footprint=fp, catalogue=cat)
        failed = sorted(k for k, v in rec["checks"].items() if not v)
        vals[tag] = dict(file=pth.name, ok=bool(rec["all_checks_passed"]),
                         sha256=rec["sha256"], bytes=rec["bytes"],
                         n_positive=rec["emitted_positive_pixels"],
                         vmin=rec["min"], vmax=rec["max"],
                         nodata=rec["meta"]["nodata"], crs=rec["meta"]["crs"],
                         shape=rec["meta"]["shape"], transform=rec["meta"]["transform"],
                         n_checks=len(rec["checks"]), failed=failed,
                         on_catalogue_positive_pixels=rec.get("on_catalogue_positive_pixels"),
                         validation_class=rec["validation_class"])
        print(f"    VALIDATE {tag}: {'PASS' if vals[tag]['ok'] else 'FAIL ' + str(failed)} "
              f"({len(rec['checks']) - len(failed)}/{len(rec['checks'])} checks) "
              f"| sha256 {rec['sha256'][:16]} | positive {rec['emitted_positive_pixels']:,}")
        # The zeros twin is the submittable one; assert_submittable is the shared hard gate.
        if tag == "zeros":
            assert_submittable(rec)

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
    out = ROOT / "evidence" / "lane_expecteddti_exp3d_gate.json"
    # format_valid concerns the SUBMITTABLE twin only.  The -nan twin is a comparison copy that is
    # EXPECTED to fail the shared validator's no_nan_anywhere / outside_footprint_zero checks; the
    # earlier version AND-ed both twins, so format_valid read false while the reason string below
    # still asserted "format-valid" -- a receipt that contradicted itself.
    zeros_ok = bool(vals.get("zeros", {}).get("ok"))
    nan_failed_as_expected = sorted(vals.get("nan", {}).get("failed") or []) == [
        "no_nan_anywhere", "outside_footprint_zero"] if "nan" in vals else True
    rule_ok = bool(gate1.get("z", 0) > 2.0)
    lane_ok = lane["duplicate"] is False and lane.get("lane_certified") is True
    surface_ok = bool(surface["pct_saturated"] < 0.5)
    promote = bool(rule_ok and gate1.get("draws_positive", 0) == gate1.get("n_draws")
                   and lane_ok and zeros_ok and surface_ok)
    failed_arms = [name for name, ok in (("rule gate", rule_ok), ("LANE uniqueness", lane_ok),
                                         ("format (submittable twin)", zeros_ok),
                                         ("surface usability", surface_ok)) if not ok]
    if promote:
        reason = "PROMOTE"
    else:
        parts = []
        if rule_ok:
            parts.append(f"the decision rule is verified and beats spacing on held-out draws "
                         f"(z = {gate1.get('z'):.2f}, "
                         f"{gate1.get('draws_positive')}/{gate1.get('n_draws')} draws)")
        if lane_ok:
            parts.append(f"the artifact is unique (worst 3-px overlap "
                         f"{lane.get('worst_overlap_frac'):.4f} over {lane.get('n_compared')} "
                         "registry rasters)")
        elif lane.get("lane_certified") is not True:
            parts.append("LANE uniqueness could NOT be certified (no registry raster reachable)")
        if zeros_ok:
            parts.append("the submittable twin passes the shared validator "
                         f"{vals['zeros'].get('n_checks')}/{vals['zeros'].get('n_checks')}")
        if not surface_ok:
            parts.append(f"but the calibrated surface is saturated "
                         f"({surface['pct_saturated']:.2f}% of cells at raw score 1.0, "
                         f"{surface['n_distinct_raw_in_candidates']:,} distinct values across the "
                         f"top {N_CANDIDATES:,} candidates), so the ranking that selects the dots "
                         "is decided by numpy's tie order, not by geology")
        reason = ("NEGATIVE RESULT — DO NOT PROMOTE. " + "; ".join(parts) +
                  ". Shipping this would spend a slot on a tie-break, not on a field. "
                  f"Failed arms: {', '.join(failed_arms)}.")
    res["verdict"] = dict(
        promote=promote,
        rule_gate_passed=rule_ok,
        lane_duplicate=bool(lane["duplicate"]),
        lane_certified=bool(lane.get("lane_certified")),
        format_valid=zeros_ok,
        nan_twin_fails_as_expected=nan_failed_as_expected,
        nan_twin_failed_checks=sorted(vals.get("nan", {}).get("failed") or []),
        surface_usable=surface_ok,
        failed_arms=failed_arms,
        reason=reason,
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
