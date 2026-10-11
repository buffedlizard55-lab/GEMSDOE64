#!/usr/bin/env python3
"""Check cached input availability; never rebuild or substitute a feature stack."""
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio


def main():
    requirements = ['data/reference/sample_submission.tif', 'data/reference/existing_faults.tif',
                    'data/cache/feature_stack.npy', 'data/cache/feature_stack.manifest.json',
                    'data/oof/predictions.npz', 'data/oof/provenance.json']
    missing = [p for p in requirements if not Path(p).is_file()]
    result = dict(ready=False, missing=missing, rebuilt_features=False,
                  official_origin_authenticated=False)
    if not missing:
        # Availability is not provenance: require independently reviewed OOF and
        # feature manifests before a future training runner can claim readiness.
        result['reason'] = 'Manifests present but not yet reviewed; readiness cannot be inferred from file existence.'
    for name in requirements[:2]:
        if Path(name).exists():
            with rasterio.open(name) as src:
                a = src.read(1)
                result[name] = dict(sha256=hashlib.sha256(Path(name).read_bytes()).hexdigest(),
                    shape=list(src.shape), crs=str(src.crs), transform=list(src.transform)[:6],
                    count=src.count, finite_cells=int(np.isfinite(a).sum()))
    Path('evidence/data_preflight.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
