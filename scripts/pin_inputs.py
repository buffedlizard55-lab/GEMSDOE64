#!/usr/bin/env python3
"""Pin the exact bytes of every input this lane consumes.

A pin is a claim about *identity*, not about authenticity: it records which
bytes were used and where they came from. The lane verifies its inputs against
the pins on every run, and the run card states the provenance class explicitly
("mirror-pinned, not organizer-authenticated").

Usage::

    python scripts/pin_inputs.py --bridge data/bridge \
        --features /tmp/training_features.tif \
        --lidar data/external/lidar_scarp_features_u8.tif \
        --road-distance data/external/tiger_road_distance_m.tif \
        --out evidence/input_pins.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SOURCES = {
    "training_features": dict(
        source="owner mirror: buffedlizard55-lab/GEMSDOE data/bridge/"
               "gems-geodawn-numerical-features.tif.part-000..004 (19-band stack, reassembled)",
        note="sha256 of the reassembled 418,912,844-byte file matches "
             "60GEMSDOE/registry/data_manifest.json"),
    "lidar_scarp_features": dict(
        source="owner mirror: buffedlizard55-lab/GEMSDOE24 data/external/"
               "lidar_scarp_features_u8.tif (owner-CI derivation from 706 USGS 3DEP 1 m tiles)",
        note="integer-quantised 12-channel lidar scarp layer; sha256 pinned in the same manifest"),
    "road_distance": dict(
        source="owner mirror: buffedlizard55-lab/GEMSDOE24 data/external/tiger_road_distance_m.tif",
        note="TIGER road distance in metres, used only for the cultural mask"),
    "sample_submission": dict(
        source="owner mirror: buffedlizard55-lab/GEMSDOE24 data/official/sample_submission.tif",
        note="grid/footprint template only; never scored as truth"),
    "existing_faults": dict(
        source="owner mirror: buffedlizard55-lab/GEMSDOE24 data/official/existing_faults.tif",
        note="published fault catalogue used for the visible-truth mask"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bridge", type=Path, required=True)
    ap.add_argument("--features", type=Path, required=True)
    ap.add_argument("--lidar", type=Path, required=True)
    ap.add_argument("--road-distance", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    paths = {
        "training_features": args.features,
        "lidar_scarp_features": args.lidar,
        "road_distance": args.road_distance,
        "sample_submission": args.bridge / "sample_submission.tif",
        "existing_faults": args.bridge / "existing_faults.tif",
    }
    pins = {}
    for label, path in paths.items():
        if not Path(path).exists():
            raise SystemExit(f"input missing, refusing to pin nothing: {path}")
        pins[label] = dict(path=str(path), sha256=sha256_file(path),
                           bytes=Path(path).stat().st_size, **SOURCES[label])
    payload = dict(schema="gems64-input-pins-v1",
                   provenance_class="mirror-pinned, not organizer-authenticated",
                   pins=pins)
    args.out.write_text(json.dumps(payload, indent=2) + "\n")
    for label, row in pins.items():
        print(f"{label:22s} {row['bytes']:>12,} B  {row['sha256'][:16]}…  {row['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
