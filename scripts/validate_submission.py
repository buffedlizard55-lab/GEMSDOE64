#!/usr/bin/env python3
"""Shared on-disk validator; format PASS alone does not permit publication."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import rasterio
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from gems57.gates import format_report
from gems57.validate import validate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('submission', type=Path)
    ap.add_argument('--sample', type=Path, default=Path('data/official/sample_submission.tif'))
    ap.add_argument('--catalogue', type=Path, default=Path('data/official/labels.tif'))
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
