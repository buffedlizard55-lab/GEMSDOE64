"""Re-validate any GeoTIFF on disk against the pinned grid and export policy.

    python scripts/check_submission.py docs/downloads/<file>.tif
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from gems64 import gates, grid as gridmod, validate

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = pathlib.Path(argv[1])
    g = gridmod.load_grid(ROOT / "data" / "bridge")
    rep = gates.format_report(path, ROOT / "data" / "bridge" / "sample_submission.tif",
                              footprint=g.footprint)
    val = validate.validate(path, g.footprint, g.catalogue)
    out = dict(file=str(path), template_format_report=rep, local_validation=val)
    print(json.dumps(out, indent=2, default=str))
    ok = bool(rep.get("ok"))
    try:
        validate.assert_submittable(val)
    except AssertionError as exc:
        ok = False
        print("LOCAL VALIDATION FAILED:", exc, file=sys.stderr)
    print("FORMAT-PASSED (local only; not a uniqueness clearance or organiser acceptance)"
          if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
