#!/usr/bin/env python3
"""Restore and SHA256-verify competition, lidar/cultural, pilot 3 m DEM, and registry rasters."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "gems_data"
DATA = ROOT / "data"

PINNED_CORE = {
    "reference/sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
    "reference/existing_faults.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "reference/training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "external/lidar_scarp_features_u8.tif": "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568",
    "external/lidar_scarp_features.json": "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41",
    "external/h52_scarp3m_100m.tif": "b5e53d67c3a7d3d1ca44ae04ae1e84d8574857da3fcd5e34ba47276d6c04b923",
    "external/topo_10m_derived_100m_u8.tif": "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4",
    "external/topo_10m_derived_100m_u8.manifest.json": "181d5527ba7ed2990031918a8b6c9d5d94e3998b2daf656de0c33322ca94120a",
    "external/derived_sgmc_faults_100m_u8.tif": "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0",
    "external/tiger_road_distance_m.tif": "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988",
    "external/blm_closed_claim_distance_m.tif": "a88356423c03fc8b6510a84f77cee2b1d38c4ccbd7761bc95c1ca8332a2e166a",
    "external/dem_tiles.json": "c23e17246dfceb12ccc3e7fbcd4d2da7fa738df322ad00d65a22304a7b21d506",
    "pilot/dem3m/x40y427_3m.tif": "3a14850f2d33bb8b7ae077951c589ad9866f1978e0722691f2ef6ffcffeee718",
    "pilot/dem3m/x42y425_3m.tif": "927c36c88debcaa65e9de9fbd0f3adf02b338614fbaed86e3e321111084735de",
}

TOP_LEVEL_ALIASES = {
    "example_submission.tif": "reference/sample_submission.tif",
    "existing_faults.tif": "reference/existing_faults.tif",
    "gems-geodawn-numerical-features.tif": "reference/training_features.tif",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def link_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        if dst.resolve() == src.resolve():
            return
        dst.unlink()
    rel = os.path.relpath(src, dst.parent)
    dst.symlink_to(rel)


def main() -> int:
    verified = {}
    for rel, expected_sha in PINNED_CORE.items():
        cpath = CACHE / rel
        if not cpath.exists():
            raise FileNotFoundError(f"Missing cached input: {cpath}")
        actual = sha256_file(cpath)
        if actual != expected_sha:
            raise ValueError(f"SHA256 mismatch for {rel}: expected {expected_sha}, got {actual}")
        dpath = DATA / rel
        link_file(cpath, dpath)
        verified[rel] = {"sha256": actual, "bytes": cpath.stat().st_size}

    for alias, target_rel in TOP_LEVEL_ALIASES.items():
        link_file(CACHE / target_rel, DATA / alias)

    # Link all registry comparator rasters
    reg_cache = CACHE / "registry"
    reg_data = DATA / "registry"
    reg_data.mkdir(parents=True, exist_ok=True)
    reg_records = []
    for tif in sorted(reg_cache.glob("*.tif")):
        dst = reg_data / tif.name
        link_file(tif, dst)
        reg_records.append({
            "file": f"data/registry/{tif.name}",
            "sha256": sha256_file(tif),
            "bytes": tif.stat().st_size,
        })
    # Also preserve alias expected by run_preflight.py if present
    w_src = reg_cache / "17GEMSDOE__E-proba-multiscale.tif"
    if w_src.exists():
        link_file(w_src, reg_data / "17GEMSDOE_E-proba-multiscale.tif")

    receipt = {
        "status": "verified",
        "core_inputs": verified,
        "registry_rasters_count": len(reg_records),
        "registry_rasters": reg_records,
    }
    out = ROOT / "evidence" / "input_receipt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified {len(verified)} core inputs and {len(reg_records)} registry rasters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
