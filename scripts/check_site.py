#!/usr/bin/env python3
"""Check static links, accessibility basics and fail-closed publication state."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.duplicates, self.downloads = [], set(), [], []
        self.h1 = 0
        self.lang = None
    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag == 'html': self.lang = a.get('lang')
        if tag == 'h1': self.h1 += 1
        if a.get('id'):
            if a['id'] in self.ids: self.duplicates.append(a['id'])
            self.ids.add(a['id'])
        for key in ('href', 'src'):
            if key in a: self.links.append(a[key])
        if tag == 'a' and 'download' in a: self.downloads.append(a.get('href'))


def check():
    problems = []
    import hashlib
    card = json.loads((DOCS / 'data/run_card.json').read_text())
    source_card = json.loads((ROOT / 'evidence/run_card.json').read_text())
    if card != source_card: problems.append('site run card differs from measured evidence')
    verdict = card.get('verdict')
    approved = verdict in ('promote', 'promote-to-selector-only')
    rasters = sorted(p for p in DOCS.rglob('*') if p.suffix.lower() in ('.tif', '.tiff', '.zip'))
    banner = 'OK TO DOWNLOAD' if approved else 'NOT CLEARED FOR SUBMISSION'
    if approved:
        if not card.get('download_allowed'): problems.append('promoted card forbids its download')
        declared = {d['path'] for d in card.get('approved_downloads', [])}
        for rel in declared:
            f = DOCS / rel
            if not f.is_file(): problems.append(f'declared download missing: {rel}'); continue
            if f.suffix.lower() == '.tif':
                h = hashlib.sha256(f.read_bytes()).hexdigest()
                if h != card.get('raster_sha256'):
                    problems.append(f'{rel} sha256 {h[:12]} != card {str(card.get("raster_sha256"))[:12]}')
        for f in rasters:
            if str(f.relative_to(DOCS)) not in declared:
                problems.append(f'undeclared raster published: {f.relative_to(DOCS)}')
    else:
        if rasters: problems.append('negative site contains TIFF/ZIP files')
        if card.get('download_allowed'): problems.append('negative card allows a download')
    pages = {}
    for path in DOCS.glob('*.html'):
        p = Parser(); p.feed(path.read_text()); pages[path.resolve()] = p
        if p.lang != 'en' or p.h1 != 1: problems.append(f'{path}: language or heading hierarchy')
        if p.duplicates: problems.append(f'{path}: duplicate IDs {p.duplicates}')
        if banner not in path.read_text():
            problems.append(f'{path}: missing prominent verdict {banner!r}')
    for path, p in pages.items():
        for link in p.links:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                if parsed.scheme not in ('https',): problems.append(f'{path}: unexpected URL scheme {link}')
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_relative_to(DOCS.resolve()):
                problems.append(f'{path}: link escapes deployed site {link}')
            elif not target.exists():
                problems.append(f'{path}: missing {link}')
            elif parsed.fragment and target in pages and parsed.fragment not in pages[target].ids:
                problems.append(f'{path}: missing fragment {link}')
    if len(pages) != 4: problems.append('expected four main pages')
    if not any('data/run_card.json' in p.downloads for p in pages.values()):
        problems.append('the run card is not offered as a download anywhere')
    return dict(ok=not problems, checked_pages=len(pages), problems=problems,
                verdict=verdict, approved_tiff_links=(len(rasters) if approved else 0),
                production_tiffs=len(rasters))


if __name__ == '__main__':
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
