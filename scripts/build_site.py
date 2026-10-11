#!/usr/bin/env python3
"""Render the negative-result site from measured evidence, not UI promises.

This build cannot publish a TIFF. A future approved-candidate publisher requires
an explicit implementation and complete promotion receipts; flipping JSON alone
is deliberately insufficient to unlock a download.
"""
from pathlib import Path
import html
import json
import shutil
import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
esc = html.escape


def read(name):
    return json.loads((ROOT / name).read_text())


def page(name, title, body):
    active = {'index.html':'Overview', 'executive-summary.html':'Submit safely',
              'research.html':'Research', 'sources.html':'Sources'}
    links = ''.join(f'<a href="{k}"'+(' aria-current="page"' if k == name else '')+f'>{v}</a>' for k,v in active.items())
    text = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="GEMSDOE64 expected-DTI research: a verified negative result, audit evidence and safe submission instructions.">
<title>{esc(title)} · GEMSDOE64</title><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><nav class="wrap" aria-label="Main navigation">
<a class="brand" href="index.html"><span class="mark">G64</span><span>GEMSDOE<small>Fault discovery lab</small></span></a><div class="navlinks">{links}</div></nav></header>
<div class="ribbon"><div class="wrap"><strong>NOT CLEARED FOR SUBMISSION</strong><span>No approved TIFF · no slot used</span><a href="executive-summary.html">Read the submission decision →</a></div></div>
<main id="main" class="wrap">{body}</main><footer class="wrap foot"><span>GEMSDOE64 / Expected-DTI selection lane<br>Evidence, not leaderboard projections. Negative results are deliverables.</span>
<span><a href="data/run_card.json">JSON run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE64">Repository ↗</a></span></footer></body></html>'''
    (DOCS / name).write_text(text)


def main():
    card = read('evidence/run_card.json')
    if card['verdict'] != 'negative' or card['download_allowed'] or card['raster_sha256'] is not None:
        raise ValueError('This negative-result publisher cannot publish/promote a TIFF.')
    if list(DOCS.rglob('*.tif')) or list(DOCS.rglob('*.tiff')) or list(DOCS.rglob('*.zip')):
        raise ValueError('Negative-result site contains a raster/ZIP. Refusing publication.')
    for name in ['run_card', 'registry_blocker', 'h33_forensics', 'synthetic_verification',
                 'data_preflight', 'input_receipt', 'template_import']:
        shutil.copyfile(ROOT / f'evidence/{name}.json', DOCS / f'data/{name}.json')
    inventory = read('docs/data/source_inventory.json')
    n = inventory['source_html_fetched']
    reviewed = esc(inventory['generated_utc'])
    filename_note = esc(inventory.get('filename_note', 'Raster filenames are source metadata, not score evidence.'))
    hero = f'''
<div class="hero"><div><p class="eyebrow">Research run 64 / Expected-DTI selection</p><h1>Evidence before<br>emission.</h1>
<p class="lead">A calibrated decision rule for better fault predictions. This run found a protocol blocker—not a submission-ready raster.</p>
<div class="actions"><button class="disabled" disabled aria-describedby="no-tiff">No approved TIFF</button><a class="button secondary" href="executive-summary.html">Executive summary ↗</a></div>
<p id="no-tiff" class="small" style="margin-top:14px">Do not submit any artifact from this run. No production TIFF was generated.</p></div>
<aside class="status-panel" aria-label="Current run verdict"><span class="pill">Negative result · stop gate triggered</span><h2>Every nonempty dot set fails<br>the literal overlap rule.</h2>
<p>One prior's three-pixel neighborhood covers every allowed off-catalogue cell, so every nonempty candidate would exceed the 70% dot-overlap limit. We did not exempt or repurpose it.</p><div class="sep"></div>
<dl><dt>Registry overlap bound</dt><dd>100% / limit 70%</dd><dt>Production holdout</dt><dd>Not run</dd><dt>Candidate TIFF</dt><dd>Not created</dd><dt>Submission authorization</dt><dd>Not granted</dd></dl></aside></div>
<div class="metrics"><div class="metric"><b>{n}</b><span>Sibling source pages fetched, not score-verified</span></div><div class="metric"><b>0</b><span>Weekly submission slots used</span></div><div class="metric"><b>1</b><span>Verified universal registry blocker</span></div></div>
<section><div class="sectionhead"><h2>What the evidence says</h2><a href="research.html">Read the research →</a></div>
<div class="cards"><article class="card"><span class="number">01 / PRIOR ARTIFACT AUDIT</span><h3>The reference map was a pruning rule.</h3><p>H33's documented support is reproduced exactly by removing 2,545 dots within 200 m of the catalogue. No new dots were added.</p><a href="data/h33_forensics.json">Inspect measured evidence →</a></article>
<article class="card"><span class="number">02 / MATHEMATICAL VERIFICATION</span><h3>The threshold needs a caveat.</h3><p>The probability rule holds for a ratio-of-expectations surrogate. An exhaustive counterexample shows it is not an exact finite-raster expectation rule.</p><a href="data/synthetic_verification.json">Inspect synthetic tests →</a></article>
<article class="card"><span class="number">03 / REGISTRY PREFLIGHT</span><h3>A valid negative beats an unsafe file.</h3><p>A prior's three-pixel halo covers all 5,106,385 allowed off-catalogue cells. With every positive finite pixel counted as a dot, all candidate dots would be within that halo, above the 70% limit.</p><a href="data/registry_blocker.json">Inspect the stop certificate →</a></article></div></section>
<section><h2>A gate, not a guess</h2><div class="pipeline"><div class="stage done"><b>Audit & mathematics</b><span>Measured / synthetic checks</span></div><div class="stage stop"><b>Registry preflight</b><span>Stopped: universal overlap</span></div><div class="stage"><b>OOF calibration</b><span>Not run; cache unavailable</span></div><div class="stage"><b>Holdout comparison</b><span>No DTI or CI claimed</span></div><div class="stage"><b>Validate & download</b><span>No production artifact</span></div></div>
<div class="note"><strong>What could make this lane useful?</strong> Restore the shared feature/OOF cache and resolve dense-prior semantics explicitly. Then test exact expected-gain placement against spacing and MCLP on the same surface. A real improvement must exceed two paired block-bootstrap standard errors.</div></section>
<section><div class="sectionhead"><h2>An auditable record</h2><a href="sources.html">Explore all sources →</a></div><p class="small">Source metadata refreshed: {reviewed}. This timestamp does not refresh model validation or verify the live leaderboard.</p><div class="actions"><a class="button" href="data/run_card.json" download="g64-negative-run-card.json">Download negative run card</a><a class="button secondary" href="research.html#next-session-in-order">Next-session plan</a></div></section>'''
    page('index.html', 'Submission status', hero)
    summary = '''<div class="page-head"><p class="eyebrow">Executive summary / Submission guide</p><h1>Can I download and submit?</h1><p class="lead"><strong>Not from this run.</strong> No TIFF is cleared or offered. The negative verdict is the deliverable.</p></div>
<div class="note warn"><strong>No bypass:</strong> a valid GeoTIFF format, unique filename, or different file hash does not prove a valid new submission. The performance and registry gates must also pass.</div>
<section><h2>Why this run stopped</h2><p>The shared registry rule treats every positive finite prediction as a dot and measures the fraction within three pixels of prior dots. One prior's three-pixel neighborhood covers the entire allowed off-catalogue domain, so every nonempty candidate has 100% forward overlap against a 70% limit. A different interpretation requires an explicit protocol change, not a private exception.</p><p>The exact shared feature cache and buffered out-of-fold model predictions are also unavailable. No geological holdout was run; no DTI, confidence interval or score improvement is claimed.</p></section>
<section><h2>The submission process—once a future run passes</h2><ol class="steps"><li><strong>Read the verdict before downloading.</strong><p>The page must say an artifact passed the promotion gate and identify its immutable SHA-256. A negative or incomplete run has no TIFF download. This site is a static evidence viewer, not a browser training service.</p></li><li><strong>Verify holdout and uniqueness receipts.</strong><p>Require the evaluator version, withheld positive count, 95% interval, and gains exceeding two paired block-bootstrap SEs against spacing/MCLP on the same surface, plus a comparable historical best. Surface and final-dot registry checks and full hash/pixel comparisons must pass.</p></li><li><strong>Download the new single-band GeoTIFF.</strong><p>Use only the newly generated cleared file—not a reference, sample, prior raster or synthetic fixture. It must be float32, EPSG:32611, 100 m, shape 3730 × 3292, affine (100, 0, 243350, 0, −100, 4508550). All footprint values must be finite and in [0,1]. The shared export uses zero outside, no nodata sentinel, and no hidden interior mask.</p></li><li><strong>Check the exact serialized file.</strong><p>Run <code>python scripts/validate_submission.py FILE.tif</code>. If using a ZIP, it must contain exactly that one TIFF. The writer's name and note are limited to 140 characters. Local validation is not organizer acceptance.</p></li><li><strong>Use the separate slot selector.</strong><p>Confirm the actual weekly cap on the authenticated submission page and obtain slot authorization. Neither this site nor this run spends a slot. No weekly-cap value has been observed here.</p></li><li><strong>Submit and retain the organizer receipt.</strong><p>On DrivenData's “New submission” page choose the cleared file, paste its unique name/note where supported, and submit only after authorization. Archive the file hash and submission-page receipt. Only that receipt can support an ORGANIZER-CONFIRMED result.</p></li></ol></section>
<section><h2>About the previous range error</h2><p>The rejected file was not supplied, so the root cause is unknown. The shared writer rejects values outside [0,1], NaN/infinity, sentinels, grid mismatches, empty support and hidden footprint pixels. It does not silently clip or “repair” bad model output.</p><div class="note">No current submission name or raster hash exists. The unique <em>run</em> identifier is <code>g64-edti-20261011-preflight-negative</code>; it must not be mistaken for a submission filename.</div></section>
<section><div class="actions"><a class="button" href="data/run_card.json" download="g64-negative-run-card.json">Download the run card</a><a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format specification ↗</a></div><p class="small" style="margin-top:15px">Organizer pages are provided for manual review. They were not accessible from this runtime.</p></section>'''
    page('executive-summary.html', 'Submit safely', summary)
    findings = (DOCS / 'research/findings.md').read_text()
    research = markdown.markdown(findings, extensions=['tables', 'fenced_code', 'toc'])
    research = research.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
    page('research.html', 'Research and negative result', '<article class="prose">'+research+'</article>')
    catalogue = read('docs/data/source_catalogue.json')
    official_rows = ''.join(f'<tr><td><a href="{esc(r["url"], quote=True)}">{esc(r["name"])}</a></td><td>{esc(r["use"])}</td><td>{esc(r.get("verified_claim") or "No claim verified in this review.")}</td><td><span class="tag">{esc(r["status"])}</span></td></tr>' for r in catalogue['official_and_background_sources'])
    sibling_rows = []
    for r in inventory['rows']:
        commit = r.get('commit', '')
        url = r.get('source_url', r['requested_url'])
        sibling_rows.append(f'<tr><td><a href="{esc(url, quote=True)}">{esc(r["repository"])}</a><br><a href="{esc(r["requested_url"], quote=True)}">Requested site ↗</a></td><td><span class="tag">{esc(r["status"])}</span><br><code>{esc(commit[:12])}</code></td><td>{r.get("raster_path_count", "unknown")}</td><td>Not receipt-verified; TIFF bytes not exhaustively audited</td></tr>')
    sources_body = f'''<div class="page-head"><p class="eyebrow">Knowledge base / Provenance</p><h1>Sources, with their limits.</h1><p class="lead">Accessible does not mean authoritative. A retrieved page is not a verified claim, and a file hash is not an organizer receipt.</p></div>
<div class="note">GitHub source snapshots were retrieved for {n} sibling pages. No live Pages deployment or DrivenData leaderboard was verified. Raster path counts include inputs and references—not just submissions. This is <strong>not</strong> a complete decoded registry audit. {filename_note}</div>
<section><h2>Official and background references</h2><div class="table-wrap"><table><thead><tr><th>Reference</th><th>Potential use</th><th>What was verified / limitation</th><th>Review status</th></tr></thead><tbody>{official_rows}</tbody></table></div><p class="small">The organizer's reference README supports CPU execution; GPU is recommended for speed, not mandatory. The notebook's loss is not an official spatial-DTI evaluator. A public source listing is not proof of local bytes, license scope, exact AOI coverage, or holdout benefit.</p></section>
<section><div class="sectionhead"><h2>All supplied sibling repositories</h2><a href="data/source_inventory.json">Full pinned inventory ↗</a></div><p class="small">Source check: {reviewed}. Unverified numeric leaderboard claims are intentionally omitted; this inventory records source provenance, not scores.</p>
<div class="filter"><label for="source-filter">Find a source</label><input id="source-filter" type="search" placeholder="Filter by repository or status"><span id="filter-count" class="small" role="status" aria-live="polite"></span></div>
<div class="table-wrap"><table id="source-table"><thead><tr><th>Repository</th><th>Source snapshot</th><th>Tracked TIFF paths</th><th>Evidence limit</th></tr></thead><tbody>{''.join(sibling_rows)}</tbody></table></div>
<div class="actions"><a class="button secondary" href="data/input_receipt.json">Audited-input receipts</a><a class="button secondary" href="data/run_card.json">Current negative run card</a></div></section>'''
    page('sources.html', 'Sources and provenance', sources_body)
    (DOCS / '.nojekyll').write_text('')
    print('Built four static pages. Verdict negative; no TIFF/ZIP published.')


if __name__ == '__main__':
    main()
