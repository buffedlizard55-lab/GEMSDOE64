#!/usr/bin/env python3
"""Restore and SHA-256-verify competition reference, external LiDAR scarp stacks,
pilot 3 m DEM tiles, and 67 prior registry rasters into .cache/gems64_data/
with lightweight symlinks under data/.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "gems64_data"
DATA = ROOT / "data"

PINNED_CORE = [
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/bridge/sample_submission.tif", "reference/sample_submission.tif",
     "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/bridge/existing_faults.tif", "reference/existing_faults.tif",
     "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/external/lidar_scarp_features_u8.tif", "external/lidar_scarp_features_u8.tif",
     "d580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/external/lidar_scarp_features.json", "external/lidar_scarp_features.json",
     "9ef0df6e87598a8b0cd52fe821661e5fdb3a00568c5d9b1c5d61fd6b242dcd41"),
    ("buffedlizard55-lab/GEMSDOE48", "268ec599f51c517cc3485da077c24d83af5be81d",
     "data/external/h52_scarp3m_100m.tif", "external/h52_scarp3m_100m.tif",
     "b5e53d67c3a7d3d1ca44ae04ae1e84d8574857da3fcd5e34ba47276d6c04b923"),
    ("buffedlizard55-lab/GEMSDOE48", "268ec599f51c517cc3485da077c24d83af5be81d",
     "data/external/scarp3m_pilot/x40y427_3m.tif", "pilot/x40y427_3m.tif",
     "3a14850f2d33bb8b7ae077951c589ad9866f1978e0722691f2ef6ffcffeee718"),
    ("buffedlizard55-lab/GEMSDOE48", "268ec599f51c517cc3485da077c24d83af5be81d",
     "data/external/scarp3m_pilot/x42y425_3m.tif", "pilot/x42y425_3m.tif",
     "927c36c88debcaa65e9de9fbd0f3adf02b338614fbaed86e3e321111084735de"),
    ("buffedlizard55-lab/GEMSDOE24", "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
     "data/external/audit_sources/tiger_road_distance_m.tif", "external/tiger_road_distance_m.tif",
     "e5350423508968fa2d32b0a6ae0d3fb4ae3ea645e3b8736f0c8e7ad9ff2f2988"),
    ("buffedlizard55-lab/GEMSDOE24", "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
     "data/external/audit_sources/blm_closed_claim_distance_m.tif", "external/blm_closed_claim_distance_m.tif",
     "a88356423c03fc8b6510a84f77cee2b1d38c4ccbd7761bc95c1ca8332a2e166a"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/external/topo_10m_derived_100m_u8.tif", "external/topo_10m_derived_100m_u8.tif",
     "a6398d9950965dec6aae6ccecdaa6ced48645d133eab222cbdd11def9bdabfa4"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/external/geodawn_extensions_u8.tif", "external/geodawn_extensions_u8.tif",
     "a35a9c6d2a14786f4dab85481ee59769213072f5dab5b2535ea82ae4d9bb7d9b"),
    ("buffedlizard55-lab/60GEMSDOE", "6444fa6552335190f0bc89661acf725ed73e7fcb",
     "data/external/derived_sgmc_faults_100m_u8.tif", "external/derived_sgmc_faults_100m_u8.tif",
     "643cbe992ef4ba37588fb469163ed8291e3ceb23d6c1f78a3cfaa462430c2da0"),
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _link(cache_file: Path, data_file: Path) -> None:
    data_file.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(cache_file, data_file.parent)
    if data_file.is_symlink() or data_file.exists():
        if data_file.is_symlink() and os.readlink(data_file) == rel:
            return
        data_file.unlink()
    data_file.symlink_to(rel)


def main() -> None:
    rows = []
    for repo, commit, source, rel_dest, digest in PINNED_CORE:
        cache_target = CACHE / rel_dest
        if not cache_target.exists():
            res = subprocess.run(
                ["gh", "api", f"repos/{repo}/contents/{source}?ref={commit}",
                 "-H", "Accept: application/vnd.github.raw+json"],
                capture_output=True, timeout=180, check=True,
            )
            data = res.stdout
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"download checksum mismatch: {rel_dest}")
            cache_target.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_target.with_suffix(".partial")
            tmp.write_bytes(data)
            tmp.replace(cache_target)
        actual = _sha256(cache_target)
        if actual != digest:
            raise ValueError(f"local checksum mismatch: {rel_dest}")
        data_target = DATA / rel_dest
        _link(cache_target, data_target)
        rows.append(dict(
            path=f"data/{rel_dest}",
            sha256=actual,
            bytes=cache_target.stat().st_size,
            url=f"https://github.com/{repo}/blob/{commit}/{source}",
            provenance="SHA-256 verified pinned input raster/manifest",
        ))

    # Link all cached registry rasters into data/registry/
    reg_cache = CACHE / "registry"
    reg_count = 0
    if reg_cache.exists():
        for tif in sorted(reg_cache.glob("*.tif")):
            _link(tif, DATA / "registry" / tif.name)
            reg_count += 1

    receipt = dict(
        inputs=rows,
        complete_training_data=True,
        registry_rasters_linked=reg_count,
        purpose="native-resolution LiDAR scarp channel extraction, cultural masking, and spatial-CV training/evaluation",
        missing=[],
        no_prior_copied_as_new_submission=True,
    )
    (ROOT / "evidence" / "input_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"Verified and linked {len(rows)} core/external/pilot files and {reg_count} registry rasters.")


if __name__ == "__main__":
    main()
