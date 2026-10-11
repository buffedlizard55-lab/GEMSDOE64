#!/usr/bin/env python3
"""Assemble the GEMSDOE64 lane inputs from pinned public GitHub sources.

Everything this lane consumes is either (a) a cached feature raster published in
a sibling project's Git history at a pinned commit, or (b) the sample grid /
catalogue bridge files that the shared template already uses.  Nothing is
downloaded from anywhere except github.com (the only egress this runtime has),
and nothing is authenticated as organizer-origin.

The script is deliberately dumb about provenance: it records exactly what it
fetched, from which repository, commit and path, with the SHA-256 of the bytes
it wrote.  A human must decide what those bytes are worth.  It fails closed: if
a required input is missing the receipt records the failure and the lane stops.

Usage
-----
    python scripts/assemble_inputs.py            # fetch + verify + write receipt
    python scripts/assemble_inputs.py --check    # verify already-fetched files

Outputs
-------
    data/inputs/<name>                 fetched bytes (git-ignored)
    evidence/input_assembly.json       measured receipt for every input
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "inputs"
WORK = ROOT / "work" / "src_mirrors"
RECEIPT = ROOT / "evidence" / "input_assembly.json"

# ---------------------------------------------------------------------------
# Pinned sources.  Every entry names the repository, commit and path, plus what
# the file is claimed to be.  `role` is what this lane uses it for; `claim` is
# the evidence class of that use.
# ---------------------------------------------------------------------------
SOURCES = [
    # --- the shared grid: sample submission + mapped-fault catalogue ---------
    dict(name="sample_submission.tif", repo="buffedlizard55-lab/60GEMSDOE",
         commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         path="data/bridge/sample_submission.tif", role="scored grid + footprint",
         claim="bridge mirror of the official sample submission; identity not organizer-authenticated"),
    dict(name="existing_faults.tif", repo="buffedlizard55-lab/60GEMSDOE",
         commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         path="data/bridge/existing_faults.tif", role="mapped-fault catalogue (masked at scoring)",
         claim="bridge mirror; byte-identical to the sibling `labels.tif`"),
    # --- the lane's cached native-resolution lidar scarp stack ---------------
    dict(name="lidar_scarp_features_u8.tif", repo="buffedlizard55-lab/60GEMSDOE",
         commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         path="data/external/lidar_scarp_features_u8.tif", role="12-band 100 m aggregation of 1/2 m lidar scarp morphology",
         claim="cached sibling product; channel list recorded in data/external/lidar_scarp_features.json"),
    dict(name="h52_scarp3m_100m.tif", repo="buffedlizard55-lab/GEMSDOE48",
         commit="268ec599f51c517cc3485da077c24d83af5be81d",
         path="data/external/h52_scarp3m_100m.tif", role="independent 3 m-lidar scarp aggregation (697 tiles)",
         claim="cached sibling product; per-tile 3DEP 1 m hashes in data/external/h52_scarp3m_100m.json"),
    # --- independent population-matched truth instrument ---------------------
    dict(name="derived_sgmc_faults_100m.tif", repo="buffedlizard55-lab/60GEMSDOE",
         commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         path="data/external/derived_sgmc_faults_100m.tif", role="USGS state-geological-map faults (independent compilation)",
         claim="derived from USGS SGMC; sibling-derived raster, not an organizer truth file"),
    # --- cultural-feature masks (the lane's required road/canal/field mask) --
    dict(name="tiger_road_distance_m.tif", repo="buffedlizard55-lab/GEMSDOE24",
         commit="07345ea0604953d7efb858d9cfbc21e20c7aca0b",
         path="data/external/audit_sources/tiger_road_distance_m.tif", role="distance to TIGER roads (cultural mask)",
         claim="sibling-derived from the US Census TIGER/Line road layer"),
    dict(name="blm_closed_claim_distance_m.tif", repo="buffedlizard55-lab/GEMSDOE24",
         commit="07345ea0604953d7efb858d9cfbc21e20c7aca0b",
         path="data/external/audit_sources/blm_closed_claim_distance_m.tif", role="distance to closed mining claims (disturbance mask)",
         claim="sibling-derived from the BLM mining-claim layer"),
    # --- real 1 m-lidar-derived DEM pilot tiles (algorithm verification) -----
    dict(name="x40y427_3m.tif", repo="buffedlizard55-lab/GEMSDOE48",
         commit="268ec599f51c517cc3485da077c24d83af5be81d",
         path="data/pilot/dem3m/x40y427_3m.tif", role="3 m pilot DEM tile (1 m lidar x40y427)",
         claim="derived from USGS 3DEP 1 m NV_WestCentral_EarthMRI_2020_D20; source hash recorded by the sibling"),
    dict(name="x42y425_3m.tif", repo="buffedlizard55-lab/GEMSDOE48",
         commit="268ec599f51c517cc3485da077c24d83af5be81d",
         path="data/pilot/dem3m/x42y425_3m.tif", role="3 m pilot DEM tile (1 m lidar x42y425)",
         claim="derived from USGS 3DEP 1 m NV_WestCentral_EarthMRI_2020_D20; source hash recorded by the sibling"),
    # --- context only (strike of mapped segments, springs for controls) ------
    dict(name="trace_segments_utm11.csv", repo="buffedlizard55-lab/60GEMSDOE",
         commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         path="data/external/trace_segments_utm11.csv", role="mapped fault trace segments (context/controls)",
         claim="sibling-derived from the mapped catalogue geometry"),
    dict(name="lidar_scarp_features.json", repo="buffedlizard55-lab/GEMSDOE24",
         commit="07345ea0604953d7efb858d9cfbc21e20c7aca0b",
         path="data/external/lidar_scarp_features.json", role="channel manifest and quantisation rule",
         claim="sibling product manifest"),
    dict(name="h52_scarp3m_100m.json", repo="buffedlizard55-lab/GEMSDOE48",
         commit="268ec599f51c517cc3485da077c24d83af5be81d",
         path="data/external/h52_scarp3m_100m.json", role="3 m scarp product manifest",
         claim="sibling product manifest"),
    dict(name="dem_pilot_receipt.json", repo="buffedlizard55-lab/GEMSDOE48",
         commit="268ec599f51c517cc3485da077c24d83af5be81d",
         path="data/pilot/dem3m/dem_pilot_receipt.json", role="3DEP 1 m source hashes for the pilot tiles",
         claim="sibling receipt"),
    # --- the registry inventory (metadata only) ------------------------------
    dict(name="g65_prior_rasters.json", repo="buffedlizard55-lab/GEMSDOE65",
         commit="__HEAD__", path="registry/prior_rasters.json",
         role="sibling registry inventory (blob SHAs + aliases)",
         claim="sibling inventory; explicitly not organizer-complete"),
]

# Comparators whose bytes this lane compares against (fetched with a partial clone).
REGISTRY_SOURCES = [
    dict(repo="buffedlizard55-lab/60GEMSDOE", commit="6444fa6552335190f0bc89661acf725ed73e7fcb",
         prefix="registry/rasters/"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run(cmd, cwd=None, check=True):
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed ({proc.returncode}): {proc.stderr.strip()[:400]}")
    return proc


def mirror(repo: str) -> Path:
    """Partial (blobless) clone so single files can be shown without full fetch."""
    dest = WORK / repo.split("/")[-1]
    if not (dest / ".git").is_dir():
        WORK.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
             f"https://github.com/{repo}", str(dest)])
    return dest


def head_sha(repo: str) -> str:
    proc = run(["git", "ls-remote", f"https://github.com/{repo}", "HEAD"])
    return proc.stdout.split()[0]


def fetch_blob(repo: str, commit: str, path: str) -> bytes:
    """Read one blob from a pinned commit of a partial clone."""
    if commit == "__HEAD__":
        commit = head_sha(repo)
    src = mirror(repo)
    run(["git", "-C", str(src), "fetch", "--quiet", "origin", commit])
    proc = subprocess.run(["git", "-C", str(src), "show", f"{commit}:{path}"],
                          capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{repo}@{commit[:8]}:{path}: {proc.stderr.decode()[:200]}")
    return proc.stdout


def verify_raster(path: Path) -> dict:
    """Grid facts that every consumer must agree on; never inferred on trust."""
    import numpy as np
    import rasterio
    out = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
           "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    with rasterio.open(path) as ds:
        out.update(bands=ds.count, dtype=ds.dtypes[0], height=ds.height, width=ds.width,
                   crs=str(ds.crs) if ds.crs else None,
                   transform=[float(v) for v in tuple(ds.transform)[:6]],
                   nodata=None if ds.nodata is None else (float(ds.nodata) if np.isfinite(ds.nodata) else "nan"),
                   descriptions=[d for d in ds.descriptions if d])
        a = ds.read()
    finite = np.isfinite(a)
    out["finite_per_band"] = [int(finite[i].sum()) for i in range(a.shape[0])]
    out["positive_per_band"] = [int((a[i] > 0).sum()) for i in range(a.shape[0])]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify without downloading")
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    rows, failures = [], []
    for spec in SOURCES:
        dest = DATA / spec["name"]
        try:
            if not args.check and not dest.exists():
                dest.write_bytes(fetch_blob(spec["repo"], spec["commit"], spec["path"]))
            if not dest.exists():
                raise FileNotFoundError(f"{dest} missing (run without --check)")
            row = dict(name=spec["name"], **{k: spec[k] for k in
                       ("repo", "commit", "path", "role", "claim")})
            if dest.suffix.lower() in {".tif", ".tiff"}:
                row.update(verify_raster(dest))
            else:
                row.update(bytes=dest.stat().st_size,
                           sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
            rows.append(row)
        except Exception as exc:  # fail closed, but keep going to report all
            failures.append(dict(name=spec["name"], repo=spec["repo"],
                                 commit=spec["commit"], path=spec["path"], error=str(exc)[:300]))

    comparators = []
    for spec in REGISTRY_SOURCES:
        try:
            src = mirror(spec["repo"])
            run(["git", "-C", str(src), "fetch", "--quiet", "origin", spec["commit"]])
            names = subprocess.run(
                ["git", "-C", str(src), "ls-tree", "-r", "--name-only", spec["commit"], spec["prefix"]],
                capture_output=True, text=True, check=True).stdout.split()
            for name in names:
                if not name.lower().endswith((".tif", ".tiff")):
                    continue
                dest = DATA / "registry" / Path(name).name
                if not args.check and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(fetch_blob(spec["repo"], spec["commit"], name))
                comparators.append(dict(repo=spec["repo"], commit=spec["commit"], path=name,
                                        local=str(dest.relative_to(ROOT)) if dest.exists() else None,
                                        bytes=dest.stat().st_size if dest.exists() else None))
        except Exception as exc:
            failures.append(dict(repo=spec["repo"], prefix=spec["prefix"], error=str(exc)[:300]))

    receipt = {
        "schema": "gems64-input-assembly-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "egress": "github.com only (git partial clone + ls-remote)",
        "evidence_class": "FETCH-RECEIPT",
        "note": ("A hash proves which bytes this project read, not that the organizer published them. "
                 "Every row keeps its sibling provenance."),
        "inputs": rows,
        "registry_comparators": comparators,
        "failures": failures,
        "complete": not failures and len(rows) == len(SOURCES),
    }
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RECEIPT.relative_to(ROOT)}: {len(rows)} inputs, "
          f"{len(comparators)} comparators, {len(failures)} failures")
    for f in failures:
        print("  FAIL", f)
    return 0 if receipt["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
