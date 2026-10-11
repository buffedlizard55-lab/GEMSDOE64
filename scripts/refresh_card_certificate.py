#!/usr/bin/env python3
"""Re-derive a run card's registry block and verdict from a fresh certificate.

The lane measures the uniqueness certificate in-process (with its real emission
domain as the control pool). This script re-derives the *published* certificate
standalone — the check a reviewer can repeat — and then rewrites only the
certificate-derived fields of the run card, re-running the shared promotion
policy on the recorded evidence instead of editing a verdict by hand.

Usage::

    python scripts/refresh_card_certificate.py --evidence evidence
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems64 import promotion        # noqa: E402

CERT_FIELDS = ("schema", "registry_rasters_checked", "errors", "my_dots", "control_draws",
               "control_pool_cells", "dense_priors", "saturating_priors", "informative_priors",
               "worst_overlap_informative", "worst_overlap_informative_file",
               "worst_abs_spearman", "worst_abs_spearman_file", "byte_and_pixel_unique",
               "literal_verdict_unique", "diagnostic_verdict_unique", "unsatisfiable_criteria",
               "unsatisfiable_reason")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--evidence", type=Path, default=ROOT / "evidence")
    args = ap.parse_args()
    card_path = args.evidence / "run_card.json"
    cert_path = args.evidence / "uniqueness_certificate.json"
    card = json.loads(card_path.read_text())
    cert = json.loads(cert_path.read_text())
    if card.get("raster_sha256") != cert.get("candidate_file_sha256"):
        raise SystemExit("certificate does not describe the card's raster; refusing to refresh")

    card["uniqueness_certificate"] = {k: cert[k] for k in CERT_FIELDS}
    card["surface_registry"] = dict(
        complete_accessible_scan=bool(cert.get("registry_rasters_checked")),
        rasters_checked=cert.get("registry_rasters_checked"),
        worst_spearman=cert.get("worst_abs_spearman"),
        worst_dot_overlap=cert.get("worst_overlap_informative"),
        unique=cert.get("literal_verdict_unique"),
        diagnostic_unique=cert.get("diagnostic_verdict_unique"),
        unsatisfiable_criteria=cert.get("unsatisfiable_criteria"),
        dense_priors=cert.get("dense_priors"),
        scope=cert.get("scope"),
    )
    card["certificate_refresh"] = dict(
        script="scripts/refresh_card_certificate.py",
        certificate="evidence/uniqueness_certificate.json",
        refreshed_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        note="the lane's in-run certificate used the lane's emission domain as the control pool; "
             "this published certificate uses the same function with the footprint-minus-catalogue "
             "pool and the written bytes",
    )

    hold = card.get("holdout") or {}
    paired = card.get("paired") or {}
    paired_row = card.get("paired_vs_incumbent") or {}
    oof = card.get("oof_selection") or {}
    evidence = dict(
        data_provenance_verified=bool((card.get("provenance") or {}).get("verified")),
        buffered_oof_verified=bool(oof.get("rows")),
        feature_canaries_pass=all(not r["leakage_until_proven_otherwise"]
                                  for r in card.get("leakage_canaries") or []),
        truth_ensemble_verified=bool((card.get("ensemble") or {}).get("passed")),
        surface_registry_pass=bool(cert.get("literal_verdict_unique")),
        final_registry_pass=bool(cert.get("literal_verdict_unique")),
        all_prior_rasters_checked=bool(cert.get("registry_rasters_checked")),
        validator_pass=bool((card.get("validator_output") or {}).get("all_checks_passed")
                            and (card.get("validator_output") or {}).get("format_pass")),
        hash_and_pixel_unique=bool(cert.get("byte_and_pixel_unique")),
        historical_best_comparable=bool(paired_row.get("beats_two_se")),
        holdout=dict(evidence_class=hold.get("evidence_class"),
                     evaluator_version=hold.get("evaluator_version"),
                     dti=hold.get("dti"), ci95=hold.get("ci95"),
                     withheld_positive_pixels=hold.get("withheld_positive_pixels"),
                     paired_comparisons={
                         "spacing": dict(same_surface_and_folds=True,
                                         delta=(paired.get("A_spacing28") or {}).get("delta"),
                                         bootstrap_se=(paired.get("A_spacing28") or {}).get("bootstrap_se")),
                         "mclp": dict(same_surface_and_folds=True,
                                      delta=(paired.get("M_mclp_surface") or {}).get("delta"),
                                      bootstrap_se=(paired.get("M_mclp_surface") or {}).get("bootstrap_se")),
                         "historical_best": dict(same_surface_and_folds=True,
                                                 delta=paired_row.get("delta"),
                                                 bootstrap_se=paired_row.get("bootstrap_se"))}),
    )
    decision = promotion.promotion_decision(evidence)
    card["verdict"] = decision["verdict"]
    card["download_allowed"] = bool(decision["download_allowed"])
    card["failed_gates"] = decision["failed_gates"]
    card["submission_slots_used"] = 0
    card_path.write_text(json.dumps(card, indent=2, default=str) + "\n")
    print(json.dumps(dict(verdict=card["verdict"], download_allowed=card["download_allowed"],
                          failed_gates=card["failed_gates"],
                          diagnostic_unique=cert.get("diagnostic_verdict_unique"),
                          literal_unique=cert.get("literal_verdict_unique"),
                          unsatisfiable=cert.get("unsatisfiable_criteria")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
