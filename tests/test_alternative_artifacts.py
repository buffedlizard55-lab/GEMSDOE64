"""Contract tests for the declared alternative (second) lane artifact.

The site may offer more than one download, but only if every offered raster is
hash-pinned in the run card, actually distinct from the primary artifact, and
carries its own measured gate.  These tests fail closed if any of that drifts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "evidence/run_card.json").read_text())


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _dots(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return np.nan_to_num(src.read(1)) >= 1.0


def test_alternatives_are_declared_hash_pinned_and_promoted():
    alts = CARD.get("alternative_artifacts") or []
    assert alts, "the second lane artifact must be declared in the run card"
    for alt in alts:
        assert alt["verdict"] == "promote" and alt["download_allowed"] is True
        assert alt["organizer_confirmed_score"] is None, "no organizer score may be claimed"
        assert alt["submission_slots_used"] == 0
        assert len(alt["note"]) <= 140
        for url_key, sha_key in (("download_url_tif", "raster_sha256"),
                                 ("download_url_zip", "zip_sha256")):
            path = ROOT / "docs" / alt[url_key]
            assert path.exists(), path
            assert _sha256(path) == alt[sha_key], path
        mirrors = ROOT / alt["file"]
        assert mirrors.exists() and _sha256(mirrors) == alt["raster_sha256"], mirrors


def test_alternative_gate_is_measured_not_asserted():
    for alt in CARD.get("alternative_artifacts") or []:
        gate = alt["gate"]
        assert gate["evidence_class"] == "HOLDOUT-DTI"
        assert gate["beats_two_se"] is True
        assert gate["pooled_dti"] > gate["area_matched_random_dti"]
        assert gate["ci95"][0] > 0.0
        assert gate["withheld_positive_pixels"] > 0


def test_alternatives_are_distinct_from_the_primary_artifact():
    """A second download is only defensible if it is a genuinely different raster."""
    primary = _dots(ROOT / "docs" / CARD["download_url_tif"])
    for alt in CARD.get("alternative_artifacts") or []:
        other = _dots(ROOT / "docs" / alt["download_url_tif"])
        assert other.sum() > 0
        inter = int((primary & other).sum())
        union = int((primary | other).sum())
        jaccard = inter / max(union, 1)
        assert jaccard < 0.5, f"alternative is a near-copy of the primary (Jaccard {jaccard:.4f})"
        assert not np.array_equal(primary, other)


def test_comparison_receipt_covers_every_offered_artifact():
    receipt = json.loads((ROOT / "evidence/artifact_comparison.json").read_text())
    assert receipt["not_a_score"] is True
    names = {r["artifact"] for r in receipt["artifact_comparison"]}
    assert "scarpcover60k" in names
    for row in receipt["artifact_comparison"]:
        for key in ("dti_cat", "dti_sgmc_off", "delta_vs_random_cat", "delta_vs_random_sgmc_off"):
            assert key in row, (row["artifact"], key)


@pytest.mark.parametrize("word", ["HOLDOUT-DTI", "No row is a competition score"])
def test_appendix_labels_its_evidence_class(word):
    text = (ROOT / "docs/research/findings.md").read_text()
    assert "Appendix A —" in text
    assert word in text
