#!/usr/bin/env python3
"""Verify grid alignment, CRS, transform, and SHA-256 digests of all prepared layers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_RASTERS = [
    "data/reference/sample_submission.tif",
    "data/reference/existing_faults.tif",
    "data/external/lidar_scarp_features_u8.tif",
    "data/external/h52_scarp3m_100m.tif",
    "data/external/tiger_road_distance_m.tif",
    "data/external/blm_closed_claim_distance_m.tif",
    "data/external/topo_10m_derived_100m_u8.tif",
    "data/external/geodawn_extensions_u8.tif",
    "data/external/derived_sgmc_faults_100m_u8.tif",
]

PILOT_TILES = [
    "data/pilot/x40y427_3m.tif",
    "data/pilot/x42y425_3m.tif",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    missing = [p for p in (*REQUIRED_RASTERS, *PILOT_TILES, "data/external/lidar_scarp_features.json")
               if not (ROOT / p).is_file()]
    rasters_meta = {}
    ref_grid = None
    for rel in REQUIRED_RASTERS:
        p = ROOT / rel
        if not p.exists():
            continue
        with rasterio.open(p) as src:
            if ref_grid is None:
                ref_grid = (src.shape, str(src.crs), list(src.transform)[:6])
            else:
                if (src.shape, str(src.crs), list(src.transform)[:6]) != ref_grid:
                    raise ValueError(f"grid mismatch on {rel}")
            a1 = src.read(1)
            rasters_meta[rel] = dict(
                sha256=_sha256(p),
                shape=list(src.shape),
                crs=str(src.crs),
                transform=list(src.transform)[:6],
                count=src.count,
                dtype=src.dtypes[0],
                finite_cells_band1=int(np.isfinite(a1).sum()),
            )
    pilot_meta = {}
    for rel in PILOT_TILES:
        p = ROOT / rel
        if not p.exists():
            continue
        with rasterio.open(p) as src:
            pilot_meta[rel] = dict(
                sha256=_sha256(p),
                shape=list(src.shape),
                crs=str(src.crs),
                transform=list(src.transform)[:6],
                count=src.count,
                dtype=src.dtypes[0],
            )
    result = dict(
        ready=len(missing) == 0,
        missing=missing,
        reference_grid=dict(
            shape=list(ref_grid[0]) if ref_grid else None,
            crs=ref_grid[1] if ref_grid else None,
            transform=ref_grid[2] if ref_grid else None,
        ),
        rasters=rasters_meta,
        pilot_3m_tiles=pilot_meta,
        registry_rasters_count=len(list((ROOT / "data/registry").glob("*.tif"))),
    )
    (ROOT / "evidence/data_preflight.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
