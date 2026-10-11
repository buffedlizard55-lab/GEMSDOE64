"""Full-registry uniqueness scan of one written submission TIFF.

The inherited ``registry_index.json`` pins 19 rasters; the registry directory
holds 62.  This script scans **every** ``.tif`` in the registry directory so the
overlap/rank-correlation statement in the run card covers the whole accessible
inventory, and records which entries were indexed vs directory-derived.

    python scripts/check_uniqueness.py docs/downloads/<file>.tif
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import numpy as np  # noqa: E402
import rasterio  # noqa: E402

from gems64 import grid as gridmod, uniqueness as U  # noqa: E402

REGISTRY = pathlib.Path(os.environ.get("GEMS64_REGISTRY",
                                       "/home/user/prior/60GEMSDOE-main/registry"))


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = pathlib.Path(argv[1])
    g = gridmod.load_grid(ROOT / "data" / "bridge")
    idx = json.loads((REGISTRY / "registry_index.json").read_text())
    indexed = {pathlib.Path(r["file"]).name for r in idx if r.get("file")}
    records = list(idx)
    extra = 0
    for tif in sorted((REGISTRY / "rasters").glob("*.tif")):
        if tif.name in indexed:
            continue
        records.append(dict(repo="(directory-derived, not in registry_index.json)",
                            submission=tif.stem, file=str(tif.relative_to(REGISTRY.parent)),
                            sha256=None))
        extra += 1
    U.ROOT = REGISTRY.parent
    with rasterio.open(path) as src:
        mine = src.read(1).astype(np.float32)
    res = U.compare_array_to_registry(mine, records, g.footprint,
                                     file_sha256=U._sha(path))
    out = dict(
        candidate=str(path), candidate_sha256=res.get("candidate_file_sha256"),
        registry_dir=str(REGISTRY), indexed_records=len(idx),
        directory_derived_records=extra, scanned=len(records),
        registry_rasters_checked=res["registry_rasters_checked"],
        missing_or_invalid=res["missing_or_invalid"],
        max_abs_spearman_full_footprint=res["worst_spearman_full_footprint"],
        worst_spearman_submission=res["worst_rho_submission"],
        max_dot_overlap_3px=res["worst_dot_overlap"],
        worst_overlap_submission=res["worst_overlap_submission"],
        worst_jaccard_dot_sets=res["worst_jaccard_dot_sets"],
        byte_unique=res["byte_unique_among_checked"],
        pixel_unique=res["pixel_unique_among_checked"],
        duplicate_count=res["duplicate_count"],
        shared_verdict=res["verdict"],
        lane_rule="rho>0.90 or 3px dot overlap>0.70 => duplicate, stop",
        lane_passed=bool(abs(res["worst_spearman_full_footprint"] or 0) <= 0.90 and
                         (res["worst_dot_overlap"] or 0) <= 0.70 and
                         res["byte_unique_among_checked"] and
                         res["pixel_unique_among_checked"]),
        rows=[{k: r.get(k) for k in ("submission", "spearman_full_footprint",
                                     "my_dots_within_3px_of_theirs",
                                     "their_dots_within_3px_of_mine",
                                     "jaccard_dot_sets", "error")}
              for r in sorted(res["rows"], key=lambda r: -(r.get("my_dots_within_3px_of_theirs") or 0))],
    )
    dest = ROOT / "evidence" / "uniqueness_full.json"
    dest.write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=2, default=float))
    print("worst 5 rows by 3-px overlap:")
    for r in out["rows"][:5]:
        print("  ", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
