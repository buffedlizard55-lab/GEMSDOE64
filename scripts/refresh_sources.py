#!/usr/bin/env python3
"""Read-only GitHub source inventory. Never scrape scores into confirmed evidence.

Pages and DrivenData are outside this runtime's network allowlist. We inspect
pinned source HTML on GitHub, not the live deployed websites. Metadata-only
TIFF enumeration is NOT a decoded-pixel uniqueness audit.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def api(endpoint, raw=False):
    command = ['gh', 'api', endpoint]
    if raw:
        command += ['-H', 'Accept: application/vnd.github.raw+json']
    result = subprocess.run(command, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[:500])
    return result.stdout if raw else json.loads(result.stdout)


def inspect(item):
    repo = item['repository']
    prefix = 'repos/buffedlizard55-lab/' + repo
    try:
        commit = api(prefix + '/commits/HEAD')['sha']
        tree = api(prefix + f'/git/trees/{commit}?recursive=1')
        paths = {x['path']: x for x in tree['tree'] if x['type'] == 'blob'}
        html_path = item['source_html']
        page = paths.get(html_path)
        page_hash = None
        if page:
            body = api(prefix + '/contents/' + html_path + '?ref=' + commit, raw=True)
            page_hash = hashlib.sha256(body).hexdigest()
        raster_paths = [dict(path=p, bytes=v.get('size'), git_blob_sha=v['sha'])
                        for p, v in paths.items() if p.lower().endswith(('.tif', '.tiff'))]
        return dict(**item, status='source-fetched' if page else 'no-requested-html-in-tree',
            commit=commit, source_html_sha256=page_hash,
            source_url=f'https://github.com/buffedlizard55-lab/{repo}/blob/{commit}/{html_path}',
            tree_truncated=bool(tree.get('truncated')), tracked_file_count=len(paths),
            raster_path_count=len(raster_paths), rasters=raster_paths,
            future_named_artifacts=[r['path'] for r in raster_paths if '20261012' in r['path']],
            organizer_receipt_reviewed=False, raster_bytes_audited=False)
    except (RuntimeError, subprocess.TimeoutExpired, KeyError, ValueError) as exc:
        return dict(**item, status='error', error=str(exc))


def main():
    sources = json.loads((ROOT / 'docs/data/source_catalogue.json').read_text())
    rows = list(ThreadPoolExecutor(max_workers=6).map(inspect, sources['sibling_sites']))
    result = dict(generated_utc=datetime.now(timezone.utc).isoformat(),
        evidence_class='SOURCE-INVENTORY-NOT-SCORE-OR-UNIQUENESS-CLEARANCE',
        method='GitHub commits, recursive trees and source HTML; live Pages not fetched',
        registry_complete=False, organizer_registry_complete=False,
        repositories=len(rows), errors=sum(r['status'] == 'error' for r in rows),
        source_html_fetched=sum(r['status'] == 'source-fetched' for r in rows), rows=rows)
    output = ROOT / 'docs/data/source_inventory.json'
    output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))


if __name__ == '__main__':
    main()
