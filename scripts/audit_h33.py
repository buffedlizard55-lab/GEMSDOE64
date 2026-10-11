#!/usr/bin/env python3
"""Re-measure a prior for education. Never write a copied submission."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt


def audit(candidate, base, sample, catalogue):
    def read(path):
        with rasterio.open(path) as ds:
            return ds.read(1), (ds.shape, str(ds.crs), tuple(ds.transform)[:6])
    a, meta = read(candidate); b, bm = read(base)
    ref, rm = read(sample); c, cm = read(catalogue)
    if not (meta == bm == rm == cm):
        raise ValueError('prior/reference grids differ')
    foot = np.isfinite(ref)
    mapped = (c > 0) & foot
    dots = (a > 0) & np.isfinite(a) & foot
    baseline = (b > 0) & np.isfinite(b) & foot
    d = distance_transform_edt(~mapped)
    predicted = baseline & (d > 2)
    return dict(evidence_class='PRIOR-ARTIFACT-MEASUREMENT-NOT-A-SCORE',
        candidate_sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),
        base_sha256=hashlib.sha256(Path(base).read_bytes()).hexdigest(),
        grid=dict(shape=list(meta[0]), crs=meta[1], transform=list(meta[2])),
        candidate_dots=int(dots.sum()), base_dots=int(baseline.sum()),
        deleted_dots=int((baseline & ~dots).sum()), new_dots=int((dots & ~baseline).sum()),
        dots_on_catalogue=int((dots & mapped).sum()), dots_within_200m=int((dots & (d <= 2)).sum()),
        rule='base positive support AND distance_to_mapped_catalogue > 2 pixels',
        rule_pixel_disagreement=int((predicted != dots).sum()),
        candidate_matches_documented_rule=bool(np.array_equal(predicted, dots)),
        organizer_receipt=None, organizer_confirmed_score=None,
        causal_explanation='Unproven. Pruning can reduce FP/redundant coverage; hidden truth is unavailable.',
        copied_candidate_written=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--candidate', required=True)
    ap.add_argument('--base', default='data/registry/g28-base.tif')
    ap.add_argument('--sample', default='data/reference/sample_submission.tif')
    ap.add_argument('--catalogue', default='data/reference/existing_faults.tif')
    args = ap.parse_args()
    report = audit(args.candidate, args.base, args.sample, args.catalogue)
    Path('evidence/h33_forensics.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
