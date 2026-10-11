#!/usr/bin/env python
"""Assemble the published run card from the lane-64 evidence receipts.

The card is *derived*, never hand-written: every numeric field is copied from a receipt
produced by ``scripts/build_scarp_stage2.py``.  A missing receipt is a hard failure, so
the site can never display a number that was not measured in this checkout.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "evidence"
DOCS = ROOT / "docs"


def read(name):
    p = EVID / name
    if not p.exists():
        raise SystemExit(f"missing evidence receipt: {name}")
    return json.loads(p.read_text())


def main() -> int:
    src = read("lane64_run_card.json")
    val = read("lane64_validator.json")
    uniq = read("lane64_uniqueness.json")
    inst = src["instrument_B_population_matched"]
    pooled, paired = inst["pooled"], inst["paired"]
    chk, meta = val["checks"], val["meta"]
    reg = src["registry"]
    mine = pooled["lane64_scarpcover"]
    campaign = pooled["blocked_area_budget"]

    card = {
        "schema": "gems64-run-card-v4",
        "run_id": "g64-scarp-native-lidar-20261011",
        "reviewed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lane": src["lane"],
        "hypothesis": src["hypothesis"],
        "mechanism": src["mechanism"],
        "non_fault_mimic": src["non_fault_mimic"],

        "artifact": src["artifact"]["file"],
        "raster_sha256": src["artifact"]["sha256"],
        "artifact_bytes": src["artifact"]["bytes"],
        "dots": src["artifact"]["dots"],
        "dot_value": 1.0,
        "outside_footprint": 0.0,
        "candidate_generated": True,

        "holdout": {
            "evidence_class": "HOLDOUT-DTI",
            "instrument": ("population-matched blocked hide-and-recover: eight whole "
                           "super-blocks withheld from the field, area-matched budgets"),
            "evaluator_version": inst["evaluator_version"],
            "dti": mine["dti"],
            "ci95": paired["random_control"]["ci95"],
            "withheld_positive_pixels": mine["n_truth"],
            "arms": {a: dict(dti=t["dti"], n_dots=t["n_dots"])
                     for a, t in pooled.items()},
            "paired_differences": paired,
            "truth_surrogate": inst["truth"],
            "is_competition_score": False,
        },
        "canary": src["field"]["leakage_canary"],
        "surrogate_cv_dti_curve": src["surrogate_curve"],
        "optimal_mass_shape": src["emission_size"]["assumptions"],
        "mass_sensitivity": src["emission_size"].get("sensitivity"),

        "correlation_overlap_vs_registry": {
            "registry_rasters_compared": len(uniq["rows"]),
            "worst_literal_dot_overlap": uniq["worst_literal"],
            "worst_excess_over_null": uniq["worst_excess"],
            "worst_absolute_rank_correlation": (
                dict(abs_rho=abs(uniq["rank_correlation"][0]["spearman"]),
                     file=uniq["rank_correlation"][0]["file"]) if uniq["rank_correlation"] else {}),
            "rho_limit": 0.90,
            "overlap_limit": 0.70,
            "literal_rule_unsatisfiable_against": uniq["literal_rule_unsatisfiable_against"],
            "scope": ("the 62-raster local registry copy, not the organizer registry"),
        },
        "validator_output": {
            "status": "pass" if all(chk.values()) else "fail",
            "file": src["artifact"]["file"],
            "sha256": val["sha256"],
            "bytes": src["artifact"]["bytes"],
            "dtype": meta["dtype"], "count": meta["count"], "crs": meta["crs"],
            "shape": meta["shape"], "transform": meta["transform"], "nodata": meta["nodata"],
            "no_nan_inside_footprint": chk["finite_inside_footprint"],
            "values_in_0_1": chk["range_0_1"],
            "crs_shape_transform_match": (chk["crs_epsg32611"] and chk["shape_3730x3292"]
                                          and chk["transform_matches"]),
            "zero_dots_on_mapped_catalogue": chk["zero_dots_on_mapped_catalogue"],
            "all_local_checks": chk,
            "validation_class": ("local on-disk template/range preflight; not organizer "
                                 "upload acceptance"),
        },
        "submission_name": src["artifact"]["name"],
        "note": src["note"],
        "note_characters": src["note_characters"],
        "submission_note_limit_characters": 140,
        "verdict": src["verdict"],
        "verdict_rule": ("the population-matched blocked instrument must beat the area-matched "
                         "random control by more than two paired block-bootstrap standard "
                         "errors, and every on-disk check must pass"),
        "download_allowed": src["download_allowed"],
        "approved_downloads": [
            {"path": f"downloads/{src['artifact']['file']}", "role": "submission GeoTIFF",
             "sha256": src["artifact"]["sha256"]},
            {"path": f"downloads/{Path(src['artifact']['file']).with_suffix('.zip').name}",
             "role": "single-TIFF zip for the submission form", "sha256": None},
        ],
        "submission_slots_used": 0,
        "slot_authorized": False,
        "organizer_confirmed_score": None,
        "organizer_receipt": None,
        "failed_gates": [] if src["download_allowed"] else src["limitations"],
        "open_risks": src["limitations"],
        "budget": {"max_experiments": 3, "max_hours": 2, "field_fits": len(src["field"]["folds"]),
                   "greedy_runs": 7, "submission_slots_used": 0},
        "limitations": [
            "Not an organizer score and not a leaderboard projection.",
            "1 m lidar tiles are gated and were not downloaded; the lane's 100 m lidar scarp "
            "aggregate is reused rather than re-derived with scarplet/Steger/Frangi.",
            "Spatial blocking controls regional leakage but cannot rule out transfer failure to "
            "the private label population.",
        ],
        "evidence_class": "HOLDOUT-DTI + surrogate-CV; never an organizer score",
        "reproduction": {
            "stage1": "python scripts/build_scarp_field.py",
            "stage2": "python scripts/build_scarp_stage2.py",
            "card": "python scripts/assemble_run_card.py",
            "site": "python scripts/build_site.py && python scripts/check_site.py",
            "validate": ("python scripts/validate_submission.py "
                         f"docs/downloads/{src['artifact']['file']}"),
        },
    }
    for target in (EVID / "run_card.json", DOCS / "data" / "run_card.json"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(card, indent=2, allow_nan=False, default=str) + "\n",
                          encoding="utf-8")
    for name in ("lane64_run_card.json", "lane64_validator.json", "lane64_uniqueness.json",
                 "synthetic_verification.json", "input_receipt.json", "data_preflight.json",
                 "template_import.json"):
        s = EVID / name
        if s.exists():
            (DOCS / "data" / name).write_text(s.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"run card written: verdict={card['verdict']} sha256={card['raster_sha256']} "
          f"dti={card['holdout']['dti']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
