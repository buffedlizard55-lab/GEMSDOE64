#!/usr/bin/env python3
"""Restore pinned audit inputs over allowed GitHub endpoints, NOT submissions.

Bridge checksums prove identity to sibling files, not official authenticity.
No prior TIFF is ever staged under docs/ or renamed into a new submission.
"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ('buffedlizard55-lab/60GEMSDOE', '6444fa6552335190f0bc89661acf725ed73e7fcb',
     'data/bridge/sample_submission.tif', 'data/reference/sample_submission.tif',
     '2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc'),
    ('buffedlizard55-lab/60GEMSDOE', '6444fa6552335190f0bc89661acf725ed73e7fcb',
     'data/bridge/existing_faults.tif', 'data/reference/existing_faults.tif',
     '7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093'),
    ('buffedlizard55-lab/17GEMSDOE', '6fc71d19d49dca4960d5434bd81b6dd06fcc030a',
     'docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif',
     'data/registry/17GEMSDOE_E-proba-multiscale.tif',
     'ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be'),
    ('buffedlizard55-lab/60GEMSDOE', '6444fa6552335190f0bc89661acf725ed73e7fcb',
     'registry/rasters/GEMSDOE28__h27-4-r1-solo-d2-8.tif', 'data/registry/g28-base.tif',
     '2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8'),
    ('buffedlizard55-lab/GEMSDOE32', 'b39e16ee85f83e3291951f56b615d657a071bb2b',
     'docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif',
     'data/registry/g32-h33.tif',
     'c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9'),
]


def main():
    rows = []
    for repo, commit, source, destination, digest in SOURCES:
        target = ROOT / destination
        if not target.exists():
            result = subprocess.run(['gh', 'api', f'repos/{repo}/contents/{source}?ref={commit}',
                '-H', 'Accept: application/vnd.github.raw+json'], capture_output=True, timeout=120, check=True)
            data = result.stdout
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f'download checksum mismatch: {destination}')
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_suffix('.partial')
            temporary.write_bytes(data)
            temporary.replace(target)
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f'local checksum mismatch: {destination}')
        rows.append(dict(path=destination, sha256=actual, bytes=target.stat().st_size,
            url=f'https://github.com/{repo}/blob/{commit}/{source}',
            provenance='third-party bridge / prior artifact; official identity not authenticated'))
    receipt = dict(inputs=rows, complete_training_data=False, purpose='audit only',
        missing=['shared 35-channel cached feature stack', 'buffered OOF model predictions',
                 'ensemble/TTA/MC-dropout checkpoints and provenance'],
        no_prior_copied_as_new_submission=True)
    (ROOT / 'evidence/input_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('Pinned audit inputs restored. Training inputs remain incomplete; no TIFF authorized.')


if __name__ == '__main__':
    main()
