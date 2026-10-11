#!/usr/bin/env python3
"""Re-derive the uniqueness certificate for a published raster, outside the lane.

The lane calls the same function in-process (with the emission domain it really
used as the control pool). This CLI re-derives the certificate from the written
bytes and the pinned registry index, which is the check a reviewer can run
without trusting the run card. Control pools differ (footprint minus catalogue
here, the lane's emission domain there), so compare the verdicts and the
per-prior rows, not the JSON bytes.

Usage::

    python scripts/build_uniqueness_certificate.py \
        --raster docs/downloads/g64-lidarscarp-strikeline-<sha12>.tif \
        --registry evidence/registry_index.json --bridge data/bridge \
        --out /tmp/recheck.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import grid as grid_mod     # noqa: E402
from gems57 import uniqueness           # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raster", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=ROOT / "evidence" / "registry_index.json")
    ap.add_argument("--bridge", type=Path, default=ROOT / "data" / "bridge")
    ap.add_argument("--control-draws", type=int, default=8)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    grid = grid_mod.load_grid(args.bridge)
    with rasterio.open(args.raster) as ds:
        raster = ds.read(1)
        if (ds.height, ds.width) != grid.shape:
            raise SystemExit("raster shape does not match the competition grid")
    digest = hashlib.sha256(args.raster.read_bytes()).hexdigest()
    index = json.loads(args.registry.read_text())
    certificate = uniqueness.dense_prior_certificate(
        raster, registry_index=index, footprint=grid.footprint,
        allowed=grid.footprint & ~grid.catalogue, file_sha256=digest,
        control_draws=args.control_draws,
        expected_grid=(grid.height, grid.width, grid.crs, grid.transform))
    args.out.write_text(json.dumps(certificate, indent=2, default=str) + "\n")
    print(json.dumps({k: certificate[k] for k in (
        "registry_rasters_checked", "my_dots", "byte_and_pixel_unique",
        "literal_verdict_unique", "diagnostic_verdict_unique",
        "worst_overlap_informative", "worst_abs_spearman",
        "unsatisfiable_criteria")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
