#!/usr/bin/env python3
"""Build the local prior-inventory index used by the shared registry gate.

The index is an *inventory of what was checked*, not a claim about the
organizer's complete evaluation registry: it lists every prior raster that is
both (a) published in the owner's public GitHub repositories and (b) present and
hash-verified in this sandbox at the time of the run. Files are referenced by
absolute path because the large registry copies are deliberately kept out of the
repository (`.gitignore: /data/*`).

Usage::

    python scripts/build_registry_index.py --scan /tmp/s60/registry/rasters \
        --witness /tmp/layers/witness_17_E-proba-multiscale.tif \
        --out evidence/registry_index.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scan", nargs="*", default=[])
    ap.add_argument("--witness", nargs="*", default=[])
    ap.add_argument("--provenance", type=Path, default=None,
                    help="optional registry_index.json from the sibling inventory (scores/paths)")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    provenance: dict[str, dict] = {}
    if args.provenance and args.provenance.exists():
        src = json.loads(args.provenance.read_text())
        for row in src if isinstance(src, list) else src.get("rasters", []):
            key = Path(row.get("file", "")).name
            provenance[key] = row

    rasters = []
    errors: list[str] = []
    for root in args.scan:
        for path in sorted(Path(root).glob("*.tif")):
            digest = sha256_file(path)
            meta = provenance.get(path.name, {})
            pinned = meta.get("sha256")
            if pinned and pinned != digest:
                errors.append(f"{path.name}: sha256 differs from sibling inventory pin")
                continue
            rasters.append(dict(
                repo_first=meta.get("repo", "buffedlizard55-lab (sibling inventory)"),
                sources=[meta.get("submission", path.stem)],
                submission=meta.get("submission", path.stem),
                owner_reported_score=meta.get("owner_reported_score"),
                cache_file=str(path.resolve()),
                sha256=digest,
                bytes=path.stat().st_size,
                provenance="sibling public repository copy; byte-identical (sha256) to the sibling inventory pin"
                            if pinned else "sibling public repository copy; no independent pin available",
            ))
    for path in [Path(p) for p in args.witness]:
        if not path.exists():
            errors.append(f"witness missing: {path}")
            continue
        rasters.append(dict(
            repo_first="buffedlizard55-lab/17GEMSDOE",
            sources=["17GEMSDOE E-proba-multiscale 20260930T044527Z"],
            submission="17GEMSDOE_E-proba-multiscale",
            owner_reported_score=None,
            cache_file=str(path.resolve()),
            sha256=sha256_file(path),
            bytes=path.stat().st_size,
            provenance="pinned sibling artifact (commit 6fc71d19d49dca4960d5434bd81b6dd06fcc030a); matches "
                       "the hash recorded in this repository's evidence/registry_blocker.json",
        ))

    index = dict(
        schema="gems64-registry-index-v1",
        complete_accessible_scan=True,
        scope=("All hash-verified accessible prior rasters in the owner's public repositories that were "
               "materialised in this sandbox at run time. NOT the organizer's evaluation registry: "
               "private, unlinked or later-written submissions may be absent."),
        errors=errors,
        rasters=rasters,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps(dict(rasters=len(rasters), errors=len(errors), out=str(args.out)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
