"""Rewrite the STATUS block of README.md from evidence/*.json.

The block between <!-- STATUS:BEGIN --> and <!-- STATUS:END --> is generated;
hand edits inside it are overwritten.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name):
    p = ROOT / "evidence" / name
    return json.loads(p.read_text()) if p.is_file() else {}


def main() -> int:
    e2 = load("e2b_holdout.json") or load("e2_holdout.json")
    e3, card = load("e3_submission.json"), load("run_card.json")
    uniq = load("uniqueness_full.json")
    lines = []
    if not e3:
        lines.append("**No GeoTIFF has been built yet.** Run `scripts/e3_build_submission.py`.")
    else:
        ok = bool(card.get("verdict") == "promote-to-selector")
        head = ("**OK TO DOWNLOAD AND SUBMIT** — holdout gate and uniqueness both passed."
                if ok else
                "**OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT.** "
                "The lane gate was not met; this file is a research artifact.")
        lines += [
            head,
            "",
            f"* **Download:** [`docs/downloads/{e3['file_name']}`]"
            f"(docs/downloads/{e3['file_name']}) "
            f"(sha256 `{e3['raster_sha256']}`, {e3['n_dots']:,} dots)",
            f"* **Submission name:** `{e3['submission_name']}` — note: `{e3['note']}`",
        ]
    if e2:
        g = e2["gate"]
        pd = e2["pooled_dti"]
        top = ", ".join(f"{k} {v:.4f}" for k, v in list(pd.items())[:3])
        lines += [
            f"* **HOLDOUT-DTI** ({e2['evaluator_version']}, "
            f"{e2['withheld_positive_pixels']:,} withheld positives, pooled): {top}",
            f"* **Gate** vs `{g['baseline']}`: Δ = {g['delta']:+.5f}, SE = {g['se']:.5f}, "
            f"z = {g['z']:.2f}, 95% CI [{g['ci'][0]:+.5f}, {g['ci'][1]:+.5f}] — "
            f"{'PASS' if g['passed'] else 'FAIL'} (rule: Δ > 2×SE)",
        ]
    if uniq:
        lines.append(
            f"* **Uniqueness** vs {uniq['scanned']} registry rasters: max |Spearman| = "
            f"{uniq['max_abs_spearman_full_footprint']:.4f}, max 3-px dot overlap = "
            f"{uniq['max_dot_overlap_3px']:.4f} (lane limits 0.90 / 0.70) — "
            f"{'PASS' if uniq['lane_passed'] else 'FAIL'}")
    if card:
        lines.append(f"* **Run card verdict:** `{card.get('verdict')}` "
                     f"({card.get('verdict_reason')}); submission slots used: "
                     f"{card.get('submission_slots_used')}")
    block = "\n".join(lines)
    readme = (ROOT / "README.md").read_text()
    a = readme.index("<!-- STATUS:BEGIN -->") + len("<!-- STATUS:BEGIN -->")
    b = readme.index("<!-- STATUS:END -->")
    (ROOT / "README.md").write_text(readme[:a] + "\n" + block + "\n" + readme[b:])
    print(block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
