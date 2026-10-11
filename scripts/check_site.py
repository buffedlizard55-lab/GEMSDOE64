#!/usr/bin/env python3
"""Check static links, accessibility basics and fail-closed publication state.

Publication policy changed deliberately on 2026-10-11: the site may carry exactly
one NOT-cleared candidate TIFF (plus its single-TIFF ZIP and its receipt), and
only when ``docs/data/publication.json``, the run card and the on-disk bytes all
agree.  Promoted artifacts are still impossible to publish: any receipt with
``promoted: true`` or ``approved_for_weekly_slot: true`` is a hard failure here.
"""
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


def _sha256(path):
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check():
    problems = []
    card = json.loads((DOCS / 'data/run_card.json').read_text())
    source_card = json.loads((ROOT / 'evidence/run_card.json').read_text())
    if card != source_card: problems.append('site run card differs from measured evidence')
    if card.get('verdict') != 'negative' or card.get('download_allowed'):
        problems.append('this publisher cannot display promoted evidence')
    if card.get('approved_for_weekly_slot'):
        problems.append('site run card claims weekly-slot approval')
    manifest_path = DOCS / 'data/publication.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'candidate_published': False}
    allowed_rasters, allowed_downloads = set(), {'data/run_card.json'}
    if manifest.get('candidate_published'):
        cand = manifest['candidate']
        if cand.get('promoted') or cand.get('approved_for_weekly_slot'):
            problems.append('publication manifest claims promotion')
        for key in ('tif', 'zip', 'receipt'):
            allowed_downloads.add(cand[key])
        allowed_rasters = {cand['tif'], cand['zip']}
        if cand['sha256'] != card.get('raster_sha256'):
            problems.append('manifest sha256 differs from the run card')
        tif, zipf = DOCS / cand['tif'], DOCS / cand['zip']
        if not tif.is_file() or not zipf.is_file():
            problems.append('manifest names a missing artifact')
        elif _sha256(tif) != cand['sha256'] or _sha256(zipf) != cand['zip_sha256']:
            problems.append('published bytes do not match the recorded hashes')
        import zipfile
        if zipf.is_file():
            with zipfile.ZipFile(zipf) as z:
                if z.namelist() != [tif.name]:
                    problems.append('ZIP must contain exactly the one TIFF')
    elif card.get('raster_sha256') is not None:
        problems.append('run card names a raster but the manifest publishes none')
    rasters = [str(p.relative_to(DOCS)) for p in DOCS.rglob('*')
               if p.suffix.lower() in ('.tif', '.tiff', '.zip')]
    for rel in rasters:
        if rel not in allowed_rasters:
            problems.append(f'undeclared raster under docs/: {rel}')
    pages = {}
    for path in DOCS.glob('*.html'):
        p = Parser(); p.feed(path.read_text()); pages[path.resolve()] = p
        if p.lang != 'en' or p.h1 != 1: problems.append(f'{path}: language or heading hierarchy')
        if p.duplicates: problems.append(f'{path}: duplicate IDs {p.duplicates}')
        for x in p.downloads:
            if x not in allowed_downloads:
                problems.append(f'{path}: unauthorized download link {x}')
        if 'NOT CLEARED FOR SUBMISSION' not in path.read_text():
            problems.append(f'{path}: missing prominent verdict')
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
    if len(pages) != 5: problems.append('expected five main pages')
    return dict(ok=not problems, checked_pages=len(pages), problems=problems,
                approved_tiff_links=0,
                published_candidates=int(bool(manifest.get('candidate_published'))))


if __name__ == '__main__':
    result = check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['ok'] else 1)
