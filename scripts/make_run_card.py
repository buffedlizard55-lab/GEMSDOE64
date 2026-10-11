"""Assemble the single JSON run card required by the parallel-run protocol.

    python scripts/make_run_card.py

Reads evidence/e1_theorem.json, evidence/e2_holdout.json and
evidence/e3_submission.json, and writes evidence/run_card.json plus a copy next
to the download so the site can link it.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def load(name):
    p = ROOT / "evidence" / name
    return json.loads(p.read_text()) if p.is_file() else {}


def main() -> int:
    e1 = load("e1_theorem.json")
    e2 = load("e2_holdout.json")
    e2b = load("e2b_holdout.json")
    e3 = load("e3_submission.json")
    uniq_full = load("uniqueness_full.json")
    governing = e2b or e2
    gate = governing.get("gate", {})
    uniq = e3.get("uniqueness", {})
    fr = e3.get("format_report", {})
    card = {
        "repo": "GEMSDOE64",
        "lane": "expected-DTI-optimal selection on a calibrated surface",
        "hypothesis": ("Emission placement, not detection, is the binding constraint: on a "
                       "calibrated probability surface the DTI-optimal dot set (greedy add "
                       "under the exact kernel metric, then backward prune) beats "
                       "fixed-spacing and maximal-coverage placement at matched mass."),
        "mechanism": ("Adding a unit-mass dot raises DTI iff dT > alpha*T*dF/(alpha*F+beta*K); "
                      "for a non-redundant dot that is kappa > alpha*DTI = 0.06 at DTI 0.30. "
                      "The 3-px kernel makes adjacent picks redundant, so the greedy tracks "
                      "the running credit field instead of thresholding pixels independently."),
        "mimic_non_fault_process": ("Linear drainage/valley axes and range-front alluvial "
                                    "fan edges: they are 1-2 px wide, strike-continuous and "
                                    "carry the same LiDAR scarp and profile-curvature "
                                    "signature as a buried fault scarp, and they are absent "
                                    "from the USGS/INGENIOUS catalogue."),
        "e1_theorem": {
            "alpha02_bar_analytic": e1.get("threshold_rule_alpha02", {}).get("analytic_bar"),
            "alpha02_bar_empirical": e1.get("threshold_rule_alpha02", {}).get("empirical_bar"),
            "lipton_alpha05": e1.get("lipton_alpha05"),
            "greedy_optimality_gaps": [r.get("greedy_optimality_gap")
                                       for r in e1.get("greedy_vs_exhaustive", [])],
            "all_ok": e1.get("all_ok"),
        },
        "holdout_dti": {
            "class": "HOLDOUT-DTI",
            "governing_arm": governing.get("experiment"),
            "evaluator_version": governing.get("evaluator_version"),
            "split": governing.get("split"),
            "withheld_positive_pixels": governing.get("withheld_positive_pixels"),
            "pooled_dti_by_rule": governing.get("pooled_dti"),
            "calibration_fix": governing.get("fix"),
            "gate": gate,
            "first_arm_uncorrected_prior": {
                "experiment": e2.get("experiment"),
                "pooled_dti_by_rule": e2.get("pooled_dti"),
                "gate": e2.get("gate"),
            },
            "note": ("Pooled DTI over four label-blind eroded quadrants with whole "
                     "catalogue components withheld and a 3-px feature buffer. Not an "
                     "organizer score and not a projection of one."),
        },
        "leakage_canary": {
            "rule": "any single feature with AUC > 0.90 is leakage until proven otherwise",
            "max_single_feature_auc_by_fold": [
                r.get("leakage_canary_max_single_feature_auc")
                for r in e2.get("fold_reports", [])],
            "heldout_quadrant_auc_by_fold": [r.get("calib_auc")
                                             for r in e2.get("fold_reports", [])],
            "surface_note": ("Single-feature AUCs are computed on the held-out "
                             "calibration quadrant of each fold."),
        },
        "correlation_vs_registry": {
            "scan": ("full registry directory (62 rasters)" if uniq_full
                     else "registry_index.json subset"),
            "registry_rasters_checked": (uniq_full.get("registry_rasters_checked")
                                         if uniq_full else uniq.get("n_registry_rasters_checked")),
            "max_abs_spearman_full": (uniq_full.get("max_abs_spearman_full_footprint")
                                      if uniq_full else None),
            "max_dot_overlap_3px_full": uniq_full.get("max_dot_overlap_3px") if uniq_full else None,
            "worst_overlap_submission_full": uniq_full.get("worst_overlap_submission") if uniq_full else None,
            "worst_jaccard_full": uniq_full.get("worst_jaccard_dot_sets") if uniq_full else None,
            "lane_passed_full_scan": uniq_full.get("lane_passed") if uniq_full else None,
            "literal_rule_note": (
                "The full scan fails the literal 70% 3-px overlap rule ONLY against the "
                "dense lattice comparator calib_r13lattice_00904 (overlap 0.9987, Spearman "
                "0.0005, Jaccard 0.0084, reverse overlap 0.157). A lattice that covers the "
                "footprint at <=3 px spacing puts every sparse emission inside its halo, so "
                "the rule as written is unmeetable by any sparse candidate. Logged for the "
                "owner as IR-64-LATTICE-01; not waived here." if uniq_full else ""),
            "registry_rasters_checked": uniq.get("n_registry_rasters_checked"),
            "max_abs_spearman_full_footprint": uniq.get("max_abs_spearman_full_footprint"),
            "worst_spearman_submission": uniq.get("worst_spearman_submission"),
            "max_dot_overlap_3px": uniq.get("max_dot_overlap_3px"),
            "worst_overlap_submission": uniq.get("worst_overlap_submission"),
            "byte_unique": uniq.get("byte_unique"),
            "pixel_unique": uniq.get("pixel_unique"),
            "lane_rule": "rho>0.90 or 3px overlap>0.70 => duplicate, stop",
            "passed": uniq.get("passed"),
        },
        "raster": {
            "file": e3.get("file_name"),
            "sha256": e3.get("raster_sha256"),
            "bytes": e3.get("raster_bytes"),
            "n_dots": e3.get("n_dots"),
            "expected_dti_mean_field": (e3.get("selector") or {}).get("expected_dti"),
        },
        "validator": {
            "template_format_ok": fr.get("ok"),
            "problems": fr.get("problems"),
            "crs": fr.get("crs"), "shape": fr.get("shape"),
            "dtype": fr.get("dtype"), "transform": fr.get("transform"),
            "value_min": fr.get("min"), "value_max": fr.get("max"),
            "nan_count": fr.get("nan_count"),
            "n_nonzero": fr.get("n_nonzero"),
        },
        "submission_name": e3.get("submission_name"),
        "submission_note": e3.get("note"),
        "submission_note_chars": e3.get("note_chars"),
        "verdict": ("promote-to-selector"
                    if (gate.get("passed") and (uniq_full.get("lane_passed") if uniq_full
                                                else uniq.get("passed")))
                    else "negative"),
        "verdict_reason": (
            "holdout gate " + ("PASSED" if gate.get("passed") else "NOT MET")
            + "; literal uniqueness " + ("PASSED" if (uniq_full.get("lane_passed") if uniq_full
                                                     else uniq.get("passed")) else "NOT MET")
            + (" (dense-lattice comparator only; see literal_rule_note)" if uniq_full
               and not uniq_full.get("lane_passed") else "")),
        "submission_slots_used": 0,
        "experiments_run": sum(1 for x in (e1, e2, e2b, e3) if x),
        "why_negative": (
            "On this holdout the DTI-optimal placement loses to fixed 2.8-px spacing at "
            "matched mass in all four folds, both before and after the exact "
            "negative-sub-sampling odds correction. The greedy concentrates dots on the "
            "highest-probability pixels, which cluster along the visible catalogue, while "
            "the withheld truth is spatially displaced from it; a spread-out covering "
            "recovers more distinct truth pixels per dot. Probability-optimal placement "
            "is only better when the surface is unbiased, and this one is not."
            if not gate.get("passed") else ""),
    }
    out = ROOT / "evidence" / "run_card.json"
    out.write_text(json.dumps(card, indent=2, default=float) + "\n")
    if e3.get("file_name"):
        copy = ROOT / "docs" / "downloads" / (e3["file_name"][:-4] + "-runcard.json")
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_text(json.dumps(card, indent=2, default=float) + "\n")
    print(json.dumps(card, indent=2, default=float)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
