#!/usr/bin/env python3
"""Hard format gate for a GEMS submission GeoTIFF.

Every check corresponds to a sentence in the published submission format (DrivenData
competition 306, page 967, https://www.drivendata.org/competitions/306/doe-gems/page/967/):

  "same projected coordinate reference system as the training data (EPSG 32611)"
  "same resolution as the training data (100m)"
  "same bounds as the training data, and data outside the bounds is null or nan"
  "a single layer with datatype of 32-bit float (float32) with values between 0 and 1
   indicating the confidence or probability of fault presence"

It also reproduces the two failure modes behind the DrivenData form rejection
``Predicted values must be in range [0, 1]`` as *checks*, so the gate can be shown to catch
them.  Both mechanisms were measured in this repository against the real rasters:

  mode A  NaN or Inf INSIDE the footprint.  Cause: a footprint mask derived from a single
          feature band strands exactly 3,061 scored pixels, because band 1 has 5,165,852 valid
          in-footprint cells against the template's 5,167,373.  ``((v>=0)&(v<=1)).all()`` is
          False for NaN, so the form rejects the file.
  mode B  a finite value outside [0, 1].  Cause: the ``-3.4028234663852886e+38`` feature
          sentinel surviving into the output on those same 3,061 in-footprint cells.

Run:  python scripts/validate_submission.py docs/downloads/<file>.tif
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

from gems64.grid import (  # noqa: E402
    BOUNDS, EPSG, FOOTPRINT_CELLS, HEIGHT, RESOLUTION_M, TRANSFORM, WIDTH, RAW, load_footprint,
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(path: Path, template: Path | None = None) -> tuple[bool, list[dict], dict]:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)})

    try:
        src = rasterio.open(path)
    except Exception as exc:  # noqa: BLE001
        return False, [{"check": "openable", "ok": False, "detail": str(exc)}], {}

    with src:
        arr = src.read(1)
        meta = {"driver": src.driver, "count": src.count, "dtype": src.dtypes[0],
                "shape": [src.height, src.width], "crs": str(src.crs), "res": list(src.res),
                "transform": list(tuple(src.transform)[:6]), "nodata": src.nodata,
                "bytes": path.stat().st_size, "sha256": sha256(path)}

        add("driver is GTiff", src.driver == "GTiff", src.driver)
        add("single band", src.count == 1, f"count={src.count}")
        add("dtype float32", src.dtypes[0] == "float32", src.dtypes[0])
        add("CRS EPSG:32611", str(src.crs) == f"EPSG:{EPSG}", str(src.crs))
        add("resolution 100 m", tuple(src.res) == (RESOLUTION_M, RESOLUTION_M), str(src.res))
        add(f"shape {HEIGHT}x{WIDTH}", (src.height, src.width) == (HEIGHT, WIDTH),
            f"{src.height}x{src.width}")
        add("geotransform matches the official grid",
            tuple(src.transform)[:6] == TRANSFORM, str(tuple(src.transform)[:6]))
        add("bounds match the official grid",
            tuple(round(b, 3) for b in src.bounds) == tuple(round(b, 3) for b in BOUNDS),
            str(tuple(round(b, 1) for b in src.bounds)))

        # The footprint is taken from the OFFICIAL template, never from a feature band: that
        # substitution is precisely rejection mode A.
        if template is not None and template.exists():
            with rasterio.open(template) as t:
                inside = np.isfinite(t.read(1))
            add("footprint taken from the official sample_submission",
                int(inside.sum()) == FOOTPRINT_CELLS, f"{int(inside.sum()):,} cells")
        else:
            inside = load_footprint()
            add("footprint taken from gems64.grid.load_footprint",
                int(inside.sum()) == FOOTPRINT_CELLS, f"{int(inside.sum()):,} cells")

        fin_in = np.isfinite(arr[inside])
        add("no NaN/Inf INSIDE the footprint (rejection mode A)", bool(fin_in.all()),
            f"{int((~fin_in).sum()):,} non-finite of {int(inside.sum()):,}")

        vals = arr[inside][fin_in] if fin_in.any() else np.empty(0, arr.dtype)
        if vals.size:
            vmin, vmax = float(vals.min()), float(vals.max())
        else:
            vmin = vmax = float("nan")
        add("values inside [0, 1] (rejection mode B)",
            bool(vals.size and vmin >= 0.0 and vmax <= 1.0), f"min={vmin!r} max={vmax!r}")
        add("no float32 sentinel (-3.4e38) anywhere",
            bool(np.all(np.abs(arr[np.isfinite(arr)]) < 1e30)),
            f"max |finite| = {float(np.abs(arr[np.isfinite(arr)]).max()) if np.isfinite(arr).any() else 0:.4g}")

        outside = ~inside
        add("outside the footprint is zero or NaN only",
            bool(np.all((arr[outside] == 0) | ~np.isfinite(arr[outside]))),
            f"{int(np.sum(~((arr[outside] == 0) | ~np.isfinite(arr[outside])))):,} offenders "
            f"of {int(outside.sum()):,}")
        add("nodata tag is absent (organizer reference writer sets none)",
            src.nodata is None, f"nodata={src.nodata}")

        n_pos = int((vals > 0).sum())
        summary = dict(meta=meta, n_positive_inside_footprint=n_pos,
                       positive_share_of_footprint=n_pos / max(int(inside.sum()), 1),
                       min=vmin, max=vmax, mean=float(vals.mean()) if vals.size else None)
        add("emits at least one positive pixel", n_pos > 0, f"{n_pos:,} positive pixels")

    ok = all(c["ok"] for c in checks)
    return ok, checks, summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tif", nargs="+", help="submission GeoTIFF(s) to validate")
    ap.add_argument("--template", default=str(RAW / "sample_submission.tif"))
    ap.add_argument("--json", default=None, help="also write the full report here")
    a = ap.parse_args()
    tmpl = Path(a.template)
    reports, all_ok = [], True
    for f in a.tif:
        p = Path(f)
        ok, checks, summary = validate(p, tmpl)
        all_ok &= ok
        print("=" * 92)
        print(f"{p.name}  ->  {'PASS' if ok else 'FAIL'}")
        for c in checks:
            print(f"  [{'PASS' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
        if summary:
            print(f"  sha256 {summary['meta']['sha256']}")
            print(f"  positive pixels inside footprint: "
                  f"{summary['n_positive_inside_footprint']:,} "
                  f"({100*summary['positive_share_of_footprint']:.3f}%)")
            print(f"  value range inside footprint: [{summary['min']!r}, {summary['max']!r}]")
        reports.append(dict(file=p.name, ok=ok, checks=checks, summary=summary))
    print("=" * 92)
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'} ({len(reports)} file(s))")
    if a.json:
        Path(a.json).write_text(json.dumps(reports, indent=1, default=str))
        print("wrote", a.json)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
