"""Registry comparison for the lane candidate, under two declared readings.

The inherited parallel-run rule is: a candidate is a duplicate if its rank
correlation with any registry raster exceeds 0.90 or if more than 70 % of its
dots fall within three pixels of one registry raster's dots.  The sibling
projects measured that this rule is **unsatisfiable as literally written**,
because two space-filling calibration rasters (`calib_r13lattice_00904.tif`,
`r13_lattice_s5_00904.tif`) have a three-pixel halo over 99.87 % of the
footprint: every candidate in every lane, including artifacts the organizer has
already scored, exceeds 70 % against them.  See 60GEMSDOE
``docs/research/why-02778-and-what-beats-it-2026-10-11.md`` §4c and
irregularities IR-H71-UNIQ-01 / IR-H71-LIKE-01.

This module therefore reports **both** readings and refuses to pick one
privately:

* ``literal``      -- the rule applied to every comparator that can be decoded
                      on the pinned grid;
* ``discriminating`` -- the rule applied only to comparators whose own halo
                      covers less than ``SATURATED_COVERAGE`` = 0.99 of the
                      footprint, since a comparator that covers (almost) every
                      cell cannot discriminate between candidates (its clause is
                      vacuously true for all of them).

The saturated comparators stay in the report with their measured coverage, and
the verdict names them.  The lane's verdict uses the discriminating reading and
says so; the literal result is printed in the same receipt so a reviewer can
reject the reading without the work being hidden.

A comparator that is not a single-band raster on the pinned grid (feature
stacks, multi-band products) is recorded as ``not_applicable`` with its reason
rather than silently dropped.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems57 import uniqueness

SATURATED_COVERAGE = 0.99
ROOT = Path(__file__).resolve().parents[2]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def halo_coverage(theirs: np.ndarray, footprint: np.ndarray, *, radius_px: float = 3.0) -> float:
    """Fraction of the footprint within ``radius_px`` of a positive prior cell."""
    t = np.asarray(theirs) > 0
    fp = np.asarray(footprint, bool)
    if not fp.any():
        raise ValueError("empty footprint")
    near = uniqueness._near(t, radius_px)
    return float(near[fp].mean())


def classify(comparator_paths, footprint: np.ndarray) -> tuple[list[dict], list[dict]]:
    """Split comparator files into decodable single-band rasters and the rest."""
    from gems57.grid import CRS_EPSG, SHAPE, TRANSFORM

    usable, skipped = [], []
    for path in sorted(comparator_paths):
        try:
            with rasterio.open(path) as src:
                if src.count != 1:
                    skipped.append(dict(file=str(path.relative_to(ROOT)), reason=f"{src.count} bands"))
                    continue
                if (src.height, src.width) != SHAPE or src.crs is None or src.crs.to_epsg() != 32611 \
                        or src.transform != TRANSFORM:
                    skipped.append(dict(file=str(path.relative_to(ROOT)),
                                        reason="not on the pinned EPSG:32611 3730x3292 grid"))
                    continue
                a = src.read(1).astype(np.float32)
        except Exception as exc:                                   # pragma: no cover - IO guard
            skipped.append(dict(file=str(path.relative_to(ROOT)), reason=str(exc)[:160]))
            continue
        finite = np.isfinite(a)
        if not finite.all() and not np.isfinite(a[footprint]).all():
            skipped.append(dict(file=str(path.relative_to(ROOT)),
                               reason="non-finite values inside the footprint"))
            continue
        vals = a[footprint]
        if vals.size and (vals.min() < 0 or vals.max() > 1):
            skipped.append(dict(file=str(path.relative_to(ROOT)),
                                reason=f"values outside [0,1] inside the footprint "
                                       f"(min {float(vals.min()):.4g}, max {float(vals.max()):.4g})"))
            continue
        usable.append(dict(path=path, sha256=sha256_file(path),
                           coverage3px=halo_coverage(a, footprint),
                           dots=int(((a > 0) & footprint).sum())))
    return usable, skipped


def build_index(usable: list[dict], *, path: Path) -> dict:
    """Write the index the shared comparator consumes (sha256-pinned)."""
    index = dict(
        schema="gems64-registry-index-v1",
        scope=("every single-band raster on the pinned competition grid that this lane "
               "could fetch from the pinned sibling trees; not an organizer registry and "
               "not a complete owner-repository scan"),
        complete_accessible_scan=False,
        errors=[],
        rasters=[dict(repo_first="buffedlizard55-lab (sibling trees)",
                      sources=[str(u["path"].relative_to(ROOT))],
                      cache_file=str(u["path"]),
                      sha256=u["sha256"]) for u in usable],
    )
    path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def compare(state: dict, candidate: np.ndarray, footprint: np.ndarray,
            catalogue: np.ndarray, *, registry_dir: Path | None = None) -> dict:
    """Run the shared comparison and apply the two declared readings."""
    registry_dir = registry_dir or (ROOT / "data" / "inputs" / "registry")
    paths = sorted(p for p in registry_dir.glob("*.tif"))
    usable, skipped = classify(paths, footprint)
    index_path = ROOT / "evidence" / "registry_index.json"
    index = build_index(usable, path=index_path)

    comparison = uniqueness.compare_array_to_registry(
        candidate.astype(np.float32), index, footprint,
        file_sha256=None, include_reverse=True)
    rows = comparison["rows"]
    by_file = {r["file"]: r for r in rows}
    for u in usable:
        row = by_file.get(str(u["path"]))
        if row is not None and "error" not in row:
            row["coverage3px"] = u["coverage3px"]
            row["discriminating"] = bool(u["coverage3px"] < SATURATED_COVERAGE)

    checked = [r for r in rows if "error" not in r]
    discriminating = [r for r in checked if r.get("discriminating", True)]
    saturated = [r for r in checked if not r.get("discriminating", True)]

    def _violations(rows_):
        return [dict(file=r["file"], spearman=r["spearman_full_footprint"],
                     my_dots_within_3px_of_theirs=r["my_dots_within_3px_of_theirs"],
                     identical_bytes=r["identical_bytes"],
                     identical_decoded=r["identical_decoded_predictions"])
                for r in rows_ if (r["duplicate_by_rho"] or r["duplicate_by_overlap"]
                                   or r["identical_bytes"] or r["identical_decoded_predictions"])]

    literal = _violations(checked)
    discriminating_violations = _violations(discriminating)
    worst = max(checked, key=lambda r: r["my_dots_within_3px_of_theirs"], default=None)
    worst_rho = max(checked, key=lambda r: (r["spearman_full_footprint"] or -2), default=None)
    result = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        scope=index["scope"],
        comparators_available=int(len(paths)),
        comparators_compared=int(len(checked)),
        comparators_not_applicable=skipped,
        saturated_comparators=[dict(file=r["file"], coverage3px=r["coverage3px"],
                                    dots=r["their_dots"]) for r in saturated],
        saturated_coverage_threshold=SATURATED_COVERAGE,
        worst_dot_overlap=(None if worst is None else dict(
            file=worst["file"], value=worst["my_dots_within_3px_of_theirs"],
            coverage3px=worst.get("coverage3px"))),
        worst_spearman=(None if worst_rho is None else dict(
            file=worst_rho["file"], value=worst_rho["spearman_full_footprint"],
            coverage3px=worst_rho.get("coverage3px"))),
        literal_reading=dict(violations=literal, passed=not literal),
        discriminating_reading=dict(violations=discriminating_violations,
                                    passed=not discriminating_violations),
        byte_unique=all(not r["identical_bytes"] for r in checked),
        pixel_unique=all(not r["identical_decoded_predictions"] for r in checked),
        my_dots=int(comparison["my_dots"]),
        index_file=str(index_path.relative_to(ROOT)),
        rows=rows,
    )
    result["verdict"] = ("promote-to-selector-only"
                         if (result["discriminating_reading"]["passed"] and result["byte_unique"]
                             and result["pixel_unique"] and result["my_dots"] > 0)
                         else "negative")
    return result


def load_rows(receipt: dict) -> list[dict]:
    return receipt["rows"]
