#!/usr/bin/env python3
"""Shared on-disk validator; format PASS alone does not permit publication."""
import argparse
import json
from pathlib import Path
import sys
from pathlib import Path as _Path

import numpy as np
import rasterio

sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "src"))

from gems57.gates import format_report      # noqa: E402
from gems57.validate import validate        # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('submission', type=Path)
    root = _Path(__file__).resolve().parents[1]
    reference = root / 'data' / 'reference'
    bridge = root / 'data' / 'bridge'
    ap.add_argument('--sample', type=Path,
                    default=reference / 'sample_submission.tif' if (reference / 'sample_submission.tif').exists()
                    else bridge / 'sample_submission.tif')
    ap.add_argument('--catalogue', type=Path,
                    default=reference / 'existing_faults.tif' if (reference / 'existing_faults.tif').exists()
                    else bridge / 'existing_faults.tif')
    args = ap.parse_args()
    with rasterio.open(args.sample) as src:
        footprint = np.isfinite(src.read(1))
        grid = (src.shape, src.crs, src.transform)
    with rasterio.open(args.catalogue) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError('catalogue grid differs from sample')
        cat = (src.read(1) > 0) & footprint
    local = validate(args.submission, footprint, cat)
    report = format_report(args.submission, args.sample, footprint=footprint)
    result = dict(format_pass=bool(local['all_checks_passed'] and report['ok']),
                  local=local, template=report, submission_clearance=False)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['format_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
