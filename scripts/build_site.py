#!/usr/bin/env python3
"""Render the evidence site from measured receipts.

Publication policy (deliberate change, 2026-10-11)
--------------------------------------------------
The previous revision of this builder could not publish a TIFF at all: it raised
on any raster under ``docs/``.  Run 64 measured a candidate that is byte- and
pixel-unique but is *not* promotion-cleared (its dot pattern is a near-duplicate
of a prior submission and its gain does not survive the interior-terrain
stratification).  The owner's standing request is an obvious, easy-to-download
artifact, so this builder now publishes **exactly one not-cleared candidate**,
under these fail-closed conditions:

* the TIFF must be named in ``evidence/e3_emission.json`` (the run's own receipt),
* its bytes must hash to the sha256 recorded there and in its adjacent receipt,
* the receipt must say ``approved_for_weekly_slot: false`` and ``promoted: false``;
  a promoted artifact remains impossible to publish from this builder,
* no other TIFF/ZIP may exist anywhere under ``docs/``,
* every page keeps the **NOT CLEARED FOR SUBMISSION** banner and the download
  links are labelled as not-cleared.

The machine-readable form of the same rule lives in ``docs/data/publication.json``
and is enforced again by ``scripts/check_site.py`` in CI.
"""
from pathlib import Path
import hashlib
import html
import json
import shutil
import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DOWNLOADS = DOCS / 'downloads'
esc = html.escape


def read(name):
    return json.loads((ROOT / name).read_text())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publication():
    """Resolve the single whitelisted, NOT-cleared candidate (or None)."""
    emission_path = ROOT / 'evidence/e3_emission.json'
    if not emission_path.exists():
        return None
    emission = json.loads(emission_path.read_text())
    if not emission.get('emitted'):
        return None
    tif = ROOT / emission['file']
    if tif.parent != DOWNLOADS or tif.suffix.lower() != '.tif':
        raise ValueError(f'candidate must live in docs/downloads: {tif}')
    receipt_path = tif.with_suffix('.json')
    receipt = json.loads(receipt_path.read_text())
    if receipt['sha256'] != emission['sha256']:
        raise ValueError('emission receipt and adjacent receipt disagree on sha256')
    if sha256_file(tif) != emission['sha256']:
        raise ValueError('candidate bytes do not match the recorded sha256')
    if receipt.get('approved_for_weekly_slot') or receipt.get('promoted'):
        raise ValueError('this builder refuses to publish a promoted artifact')
    if len(emission['registry']['rows']) == 0:
        raise ValueError('candidate has no registry comparison receipt')
    extra = [p.name for p in DOCS.rglob('*')
             if p.suffix.lower() in ('.tif', '.tiff', '.zip')
             and p.name not in (tif.name, tif.with_suffix('.zip').name)]
    if extra:
        raise ValueError(f'undeclared rasters under docs/: {extra}')
    return dict(emission=emission, receipt=receipt, tif=tif,
                zip=tif.with_suffix('.zip'), receipt_path=receipt_path)


def page(name, title, body, nav):
    active = nav
    links = ''.join(f'<a href="{k}"'+(' aria-current="page"' if k == name else '')+f'>{v}</a>'
                    for k, v in active.items())
    text = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="GEMSDOE64 lidar-scarp lane: measured negative result, one not-cleared candidate TIFF, audit evidence and submission guide.">
<title>{esc(title)} · GEMSDOE64</title><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><nav class="wrap" aria-label="Main navigation">
<a class="brand" href="index.html"><span class="mark">G64</span><span>GEMSDOE<small>Fault discovery lab</small></span></a><div class="navlinks">{links}</div></nav></header>
<div class="ribbon"><div class="wrap"><strong>NOT CLEARED FOR SUBMISSION</strong><span>Candidate TIFF published · no weekly slot used</span><a href="executive-summary.html">Read the submission decision →</a></div></div>
<main id="main" class="wrap">{body}</main><footer class="wrap foot"><span>GEMSDOE64 / Expected-DTI selection lane<br>Evidence, not leaderboard projections. Negative results are deliverables.</span>
<span><a href="data/run_card.json">JSON run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE64">Repository ↗</a></span></footer></body></html>'''
    (DOCS / name).write_text(text)


def main():
    card = read('evidence/run_card.json')
    pub = publication()
    if card['verdict'] != 'negative' or card.get('download_allowed'):
        raise ValueError('loud failure: this publisher only renders a not-cleared negative verdict')
    if card.get('approved_for_weekly_slot'):
        raise ValueError('run card must not claim slot approval')
    for name in ['run_card', 'e1_sgmc_off', 'e2_catalogue_hide', 'e3_emission', 'registry_index',
                 'registry_blocker', 'h33_forensics', 'synthetic_verification', 'data_preflight',
                 'input_receipt', 'input_assembly', 'template_import']:
        src = ROOT / f'evidence/{name}.json'
        if src.exists():
            shutil.copyfile(src, DOCS / f'data/{name}.json')
    inventory = read('docs/data/source_inventory.json')
    n = inventory['source_html_fetched']
    reviewed = esc(inventory['generated_utc'])
    filename_note = esc(inventory.get('filename_note', 'Raster filenames are source metadata, not score evidence.'))

    i1 = card['holdout']['instrument_1']
    disc = [r for r in pub['emission']['registry']['rows'] if r.get('discriminating')]
    worst_disc = max(disc, key=lambda r: r['my_dots_within_3px_of_theirs']) if disc else None
    i2 = card['holdout']['instrument_2']
    reg = card['correlation_overlap_vs_registry']
    if pub is None:
        download_block = ('<div class="note warn"><strong>No candidate TIFF in this checkout.</strong> '
                          'Re-run <code>scripts/run_lane.py --experiments e3 --emit …</code> to publish one.</div>')
        stale = True
    else:
        rec = pub['receipt']
        download_block = f'''<div class="actions">
<a class="button" href="downloads/{esc(rec['file'])}" download>Download candidate TIFF (NOT cleared)</a>
<a class="button secondary" href="downloads/{esc(rec['zip_file'])}" download>Download ZIP (single TIFF)</a>
<a class="button secondary" href="downloads/{pub['receipt_path'].name}">Read its receipt ↗</a></div>
<p class="small">sha256 <code>{esc(rec['sha256'])}</code> · {rec['bytes']:,} bytes · float32 · EPSG:32611 · 100 m · values 0–1 ·
{rec['validator']['meta']['shape'][1]}×{rec['validator']['meta']['shape'][0]} px · all {len(rec['validator']['checks'])} local checks passed (range 0–1 guaranteed, no NaN, zero dots on the mapped catalogue) · template validator ok: {str(rec['template_report']['ok']).lower()}.
Local format validation is <em>not</em> organizer acceptance and <em>not</em> promotion.</p>'''
        stale = False
    hero = f'''
<div class="hero"><div><p class="eyebrow">Run 64 / lidar-scarp lane / expected-DTI selection</p><h1>One candidate,<br>two honest controls.</h1>
<p class="lead">A native-resolution lidar scarp surface, its two instrument measurements, its terrain-matched control
and the measured reason it is <strong>not</strong> promoted.</p>
<div class="actions"><a class="button secondary" href="executive-summary.html">Executive summary ↗</a>
<a class="button secondary" href="submission-guide.html">Submission guide ↗</a></div></div>
<aside class="status-panel" aria-label="Current run verdict"><span class="pill">Negative result · gate not cleared</span>
<h2>The gain is range-front<br>terrain, not new faults.</h2>
<p>Inside interior blocks the owner-reported champion scores {i1['interior_stratum']['champion_h33_2_b2']:.5f}
while the candidate scores {i1['interior_stratum']['candidate']:.5f}
(paired {i1['interior_stratum']['paired_vs_champion']['delta']:+.5f}, SE {i1['interior_stratum']['paired_vs_champion']['se']:.5f}).
The pooled edge over the champion on instrument&nbsp;1 ({i1['paired_vs_champion']['delta']:+.5f}, 2&nbsp;SE) does not
survive the stratification the lane's own protocol requires.</p><div class="sep"></div>
<dl><dt>Candidate dots</dt><dd>{card['submission_name_check']['characters'] and pub['emission']['candidate']['dots'] if pub else 0}</dd>
<dt>Instrument 1 (sgmc_off)</dt><dd>{i1['candidate']['dti']:.5f} vs champion {i1['champion_h33_2_b2']['dti']:.5f}</dd>
<dt>Instrument 2 (catalogue_hide)</dt><dd>{i2['candidate']['dti']:.5f} vs champion {i2['champion_h33_2_b2']['dti']:.5f}</dd>
<dt>Registry dot overlap</dt><dd>{worst_disc['my_dots_within_3px_of_theirs']*100:.1f}% within 3 px of {esc(worst_disc['submission'].split('/')[-1])}</dd>
<dt>Weekly slots used</dt><dd>0</dd></dl></aside></div>
<div class="metrics"><div class="metric"><b>{pub['emission']['candidate']['dots'] if pub else 0}</b><span>Blue-noise candidate dots, ≥3 px off the mapped catalogue</span></div>
<div class="metric"><b>{reg['comparators_compared']}</b><span>Registry rasters compared by bytes, pixels and dots</span></div>
<div class="metric"><b>{i1['interior_stratum']['champion_h33_2_b2']:.4f}</b><span>Champion interior-stratum DTI vs the candidate's {i1['interior_stratum']['candidate']:.4f}</span></div>
<div class="metric"><b>0</b><span>Weekly submission slots used</span></div></div>
{download_block}
<section><div class="sectionhead"><h2>What the evidence says</h2><a href="research.html">Read the research →</a></div>
<div class="cards"><article class="card"><span class="number">01 / CONTROLS</span><h3>Concentration beats the champion, not the terrain.</h3>
<p>Terrain-matched control {i1['terrain_matched_control']['dti']:.5f} vs candidate {i1['candidate']['dti']:.5f} on instrument 1:
{i1['paired_vs_terrain_matched_control']['delta']:+.5f} (SE {i1['paired_vs_terrain_matched_control']['se']:.5f}) — under two standard errors.
In the interior stratum the control is also {abs(i1['interior_stratum']['paired_vs_terrain_matched_control']['delta']):.5f} *ahead*.</p>
<a href="data/e1_sgmc_off.json">Inspect instrument 1 →</a></article>
<article class="card"><span class="number">02 / STRATIFIED</span><h3>The champion wins where terrain cannot explain it.</h3>
<p>In interior blocks the champion reaches {i1['interior_stratum']['champion_h33_2_b2']:.5f} and the candidate
{i1['interior_stratum']['candidate']:.5f}: a paired delta of {i1['interior_stratum']['paired_vs_champion']['delta']:+.5f}
(SE {i1['interior_stratum']['paired_vs_champion']['se']:.5f}) against the candidate. That single measurement drives the negative verdict.</p>
<a href="data/e1_sgmc_off.json">Inspect the strata →</a></article>
<article class="card"><span class="number">03 / UNIQUENESS</span><h3>Byte-unique, pattern-redundant.</h3>
<p>No prior raster shares its bytes or pixels, yet {worst_disc['my_dots_within_3px_of_theirs']*100:.1f}% of its dots sit within
3 px of <code>{esc(worst_disc['submission'].split('/')[-1])}</code> — the family has already mined this surface.</p>
<a href="data/e3_emission.json">Inspect the registry comparison →</a></article></div></section>
<section><h2>A gate, not a guess</h2><div class="pipeline">
<div class="stage done"><b>Surface &amp; placement</b><span>amp/SNR percentile, 1.5 px blue noise</span></div>
<div class="stage done"><b>Instrument 1 + controls</b><span>Ran; terrain control not cleared</span></div>
<div class="stage stop"><b>Interior stratum</b><span>Stopped: champion wins by 5 SE</span></div>
<div class="stage done"><b>Instrument 2 (no-harm)</b><span>Ran: tied with controls</span></div>
<div class="stage warn"><b>Registry &amp; emission</b><span>Byte-unique; 88.8% dot overlap</span></div></div>
<div class="note"><strong>What could make this lane useful?</strong> {esc(card['limitation'])}</div></section>
<section><div class="sectionhead"><h2>An auditable record</h2><a href="sources.html">Explore all sources →</a></div>
<p class="small">Source metadata refreshed: {reviewed}. This timestamp does not refresh model validation or verify the live leaderboard.</p>
<div class="actions"><a class="button" href="data/run_card.json" download="g64-run-card.json">Download run card</a>
<a class="button secondary" href="research.html#next-session-in-order">Next-session plan</a></div></section>'''
    nav = {'index.html': 'Overview', 'executive-summary.html': 'Submit safely',
           'submission-guide.html': 'Submission guide', 'research.html': 'Research',
           'sources.html': 'Sources'}
    page('index.html', 'Submission status', hero, nav)

    if pub is not None:
        rec = pub['receipt']
        rec_facts = f'''<dl class="kv"><dt>File</dt><dd><code>{esc(rec['file'])}</code></dd>
<dt>sha256</dt><dd><code>{esc(rec['sha256'])}</code></dd>
<dt>ZIP</dt><dd><code>{esc(rec['zip_file'])}</code></dd>
<dt>Submission name</dt><dd>{esc(rec['submission_name'])} ({len(rec['submission_name'])}/140 characters)</dd>
<dt>Submission note</dt><dd>{esc(rec['note'])} ({rec['note_chars']}/140 characters)</dd>
<dt>Validator</dt><dd>{rec['validator']['meta']['dtype']}, {rec['validator']['meta']['crs']}, 100 m, values {rec['validator']['min']}–{rec['validator']['max']},
all {len(rec['validator']['checks'])} checks passed (“range [0,1] guaranteed”: {str(rec['validator']['checks']['range_0_1_guaranteed']).lower()};
dots on the mapped catalogue: {rec['validator']['on_catalogue_positive_pixels']})</dd>
<dt>Status</dt><dd>NOT cleared · {esc(rec['status'])}</dd></dl>'''
    else:
        rec_facts = '<p>No candidate was emitted in this checkout.</p>'
    summary = f'''<div class="page-head"><p class="eyebrow">Executive summary / submission decision</p><h1>Should I submit this file?</h1>
<p class="lead"><strong>Only if you accept a measured redundancy.</strong> The candidate is format-clean and byte-unique, but the lane's own
promotion gate is <strong>not</strong> met, so the file is published as a labelled candidate and not as a promoted submission.</p></div>
<div class="note warn"><strong>The short version:</strong> downloading and submitting is safe for the format (it cannot trigger the
“Predicted values must be in range [0,1]” rejection: min 0.0, max 1.0, no NaN inside the footprint), but the evidence says it is unlikely
to beat the owner-reported champion, and 88.8% of its dots coincide with an earlier submission's dot pattern.</div>
<section><h2>Facts about the file</h2>{rec_facts}</section>
<section><h2>Why the verdict is negative</h2><ol class="steps">
<li><strong>Pooled instrument 1 favours the candidate, the stratum does not.</strong><p>Against the owner-reported champion the candidate gains
{i1['paired_vs_champion']['delta']:+.5f} (SE {i1['paired_vs_champion']['se']:.5f}) on the population of state-map faults that lie off the mapped catalogue.
Inside interior 20 km blocks, where range-front terrain cannot explain credit, the champion scores
{i1['interior_stratum']['champion_h33_2_b2']:.5f} against the candidate's {i1['interior_stratum']['candidate']:.5f}
(paired {i1['interior_stratum']['paired_vs_champion']['delta']:+.5f}, SE {i1['interior_stratum']['paired_vs_champion']['se']:.5f}).</p></li>
<li><strong>The terrain-matched control is not beaten.</strong><p>Dots drawn from the same relief × slope classes score
{i1['terrain_matched_control']['dti']:.5f} against the candidate's {i1['candidate']['dti']:.5f}
(candidate minus control: {i1['paired_vs_terrain_matched_control']['delta']:+.5f}, SE {i1['paired_vs_terrain_matched_control']['se']:.5f}).</p></li>
<li><strong>Instrument 2 shows no harm, and no edge.</strong><p>The published artifact scored as-is returns {i2['published_artifact_as_is']['pooled_dti']:.5f} on
all four folds <em>by construction</em> (its dots are ≥ 3 px from the whole catalogue while this instrument's truth is catalogue geometry) — a structural
diagnostic, not a harm measurement. The protocol construction (per-fold placement from the visible catalogue) scores
{i2['candidate']['dti']:.5f} ({i2['candidate']['ci95'][0]:.5f}–{i2['candidate']['ci95'][1]:.5f}) against the mass-matched random control
{i2['random_mass_matched']['dti']:.5f} and the terrain-matched control {i2['terrain_matched_control']['dti']:.5f}: statistically tied.</p></li>
<li><strong>Uniqueness is byte-deep, not pattern-deep.</strong><p>{esc(reg['note'])}</p></li></ol></section>
<section><h2>The submission path, if you decide to use it</h2><p>Step-by-step instructions, including what to check before spending a slot,
are on the <a href="submission-guide.html">submission guide</a>.</p>
<ol class="steps"><li><strong>Read the verdict.</strong><p>No artifact here is approved for an automatic weekly slot; this is a labelled candidate.</p></li>
<li><strong>Verify the hash.</strong><p>Download the TIFF (or the single-TIFF ZIP) and compare sha256 with the receipt.</p></li>
<li><strong>Validate locally.</strong><p><code>python scripts/validate_submission.py FILE.tif</code> — local format checks only.</p></li>
<li><strong>Submit only as an authorized operator.</strong><p>The lane never spends a slot itself. Retention of the submission-page receipt is the only
path to an ORGANIZER-CONFIRMED number.</p></li></ol></section>
<section><div class="actions"><a class="button" href="data/run_card.json" download="g64-run-card.json">Download the run card</a>
<a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official format specification ↗</a></div>
<p class="small">Organizer pages are provided for manual review; they were fetched through a public mirror and are not re-verified here.</p></section>'''
    page('executive-summary.html', 'Submit safely', summary, nav)

    guide = '''<div class="page-head"><p class="eyebrow">Submission guide</p><h1>Download, validate, submit — in that order.</h1>
<p class="lead">This page exists so that nobody has to guess which file is which, or whether a file is cleared.</p></div>
<section><h2>1. What you can download here</h2>
<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>What it is</th><th>What it is not</th></tr></thead><tbody>
<tr><td><code>downloads/gems64-lane-ampsnr-37654-20261011.tif</code></td><td>Single-band float32 GeoTIFF on the pinned competition grid, 37,654 dots at value 1.0, zeros elsewhere.</td><td>Not organizer-accepted, not promotion-cleared.</td></tr>
<tr><td><code>downloads/gems64-lane-ampsnr-37654-20261011.zip</code></td><td>The same TIFF alone in a ZIP, for portals that want an archive.</td><td>Contains no extra files, no evidence, no sample.</td></tr>
<tr><td><code>downloads/gems64-lane-ampsnr-37654-20261011.json</code></td><td>The writer's receipt: hash, byte count, validator output, name and note.</td><td>Not a submission-page receipt; it proves nothing about the leaderboard.</td></tr>
</tbody></table></div></section>
<section><h2>2. Verify before you submit</h2><ol class="steps">
<li><strong>Hash the file.</strong><p><code>sha256sum gems64-lane-ampsnr-37654-20261011.tif</code> must match the receipt.</p></li>
<li><strong>Check the grid and the range.</strong><p>EPSG:32611, 100 m, 3730×3292, transform (100, 0, 243350, 0, −100, 4508550). Every value inside the
footprint finite and in [0,1]; the writer refuses to emit anything else and never clips silently.</p></li>
<li><strong>Run the local validator.</strong><p><code>.venv/bin/python scripts/validate_submission.py FILE.tif</code>. A local pass is necessary, never sufficient.</p></li>
<li><strong>Check the catalogue distance.</strong><p>Every dot must be at least 3 px (300 m) from the mapped catalogue; the emitted file satisfies this by construction
and the receipt records the minimum.</p></li></ol></section>
<section><h2>3. Submit as an authorized operator</h2><ol class="steps">
<li><strong>Confirm the weekly cap yourself</strong> on the authenticated DrivenData page. This repository has never observed a cap value and never spends a slot.</li>
<li><strong>Upload the TIFF</strong> (or the ZIP) on the competition's “New submission” page and paste the recorded name and note if the portal asks for them.</li>
<li><strong>Keep the receipt.</strong><p>Only the submission-page receipt can support an <code>ORGANIZER-CONFIRMED</code> number. Copy it into
<code>evidence/organizer_receipt.json</code> if it exists; until then every score in this repository is a labelled instrument.</p></li>
<li><strong>If the portal rejects the file</strong>, stop and record the full error text verbatim. Do not “fix” it by guessing at nodata handling.</li></ol></section>
<section><h2>4. What would make a future candidate worth a slot</h2><p>The lane's frozen gates are in <code>PREREGISTRATION.md</code>:
beat the terrain-matched control by more than 2 paired SEs <em>inside the interior stratum</em>, keep instrument 2 within noise of its controls,
clear the byte/pixel uniqueness check, and record the dot-pattern overlap honestly even when the literal clause is unsatisfiable.</p></section>
<section><div class="actions"><a class="button" href="data/run_card.json" download="g64-run-card.json">Download run card</a>
<a class="button secondary" href="executive-summary.html">Back to the decision ↗</a></div></section>'''
    page('submission-guide.html', 'Submission guide', guide, nav)

    findings = (DOCS / 'research/findings.md').read_text()
    research = markdown.markdown(findings, extensions=['tables', 'fenced_code', 'toc'])
    research = research.replace('<table>', '<div class="table-wrap"><table>').replace('</table>', '</table></div>')
    page('research.html', 'Research and negative result', '<article class="prose">'+research+'</article>', nav)

    catalogue = read('docs/data/source_catalogue.json')
    official_rows = ''.join(f'<tr><td><a href="{esc(r["url"], quote=True)}">{esc(r["name"])}</a></td><td>{esc(r["use"])}</td><td>{esc(r.get("verified_claim") or "No claim verified in this review.")}</td><td><span class="tag">{esc(r["status"])}</span></td></tr>' for r in catalogue['official_and_background_sources'])
    sibling_rows = []
    for r in inventory['rows']:
        commit = r.get('commit', '')
        url = r.get('source_url', r['requested_url'])
        sibling_rows.append(f'<tr><td><a href="{esc(url, quote=True)}">{esc(r["repository"])}</a><br><a href="{esc(r["requested_url"], quote=True)}">Requested site ↗</a></td><td><span class="tag">{esc(r["status"])}</span><br><code>{esc(commit[:12])}</code></td><td>{r.get("raster_path_count", "unknown")}</td><td>Not receipt-verified; TIFF bytes not exhaustively audited</td></tr>')
    sources_body = f'''<div class="page-head"><p class="eyebrow">Knowledge base / Provenance</p><h1>Sources, with their limits.</h1><p class="lead">Accessible does not mean authoritative. A retrieved page is not a verified claim, and a file hash is not an organizer receipt.</p></div>
<div class="note">GitHub source snapshots were retrieved for {n} sibling pages. No live Pages deployment or DrivenData leaderboard was verified. Raster path counts include inputs and references—not just submissions. This is <strong>not</strong> a complete decoded registry audit. {filename_note}</div>
<section><h2>Official and background references</h2><div class="table-wrap"><table><thead><tr><th>Reference</th><th>Potential use</th><th>What was verified / limitation</th><th>Review status</th></tr></thead><tbody>{official_rows}</tbody></table></div>
<p class="small">The organizer's reference README supports CPU execution. The notebook's loss is not an official spatial-DTI evaluator. A public source listing is not proof of local bytes, license scope, exact AOI coverage, or holdout benefit.</p></section>
<section><h2>The competition-format specification</h2><p>The submission page requires a single-layer float32 GeoTIFF on EPSG:32611 with 100 m cells,
values in [0,1] and null/NaN only outside the footprint. The local writer pins the sample submission's grid exactly and refuses every repair.
That page is the reference for the format fields quoted across this site.</p>
<p class="small"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">competition-doe-gems/page/967 ↗</a> (fetched through a public mirror; treat as manual-review reference).</p></section>
<section><div class="sectionhead"><h2>All supplied sibling repositories</h2><a href="data/source_inventory.json">Full pinned inventory ↗</a></div><p class="small">Source check: {reviewed}. Unverified numeric leaderboard claims are intentionally omitted; this inventory records source provenance, not scores.</p>
<div class="filter"><label for="source-filter">Find a source</label><input id="source-filter" type="search" placeholder="Filter by repository or status"><span id="filter-count" class="small" role="status" aria-live="polite"></span></div>
<div class="table-wrap"><table id="source-table"><thead><tr><th>Repository</th><th>Source snapshot</th><th>Tracked TIFF paths</th><th>Evidence limit</th></tr></thead><tbody>{''.join(sibling_rows)}</tbody></table></div>
<div class="actions"><a class="button secondary" href="data/input_receipt.json">Audited-input receipts</a><a class="button secondary" href="data/run_card.json">Current run card</a></div></section>'''
    page('sources.html', 'Sources and provenance', sources_body, nav)

    (DOCS / '.nojekyll').write_text('')
    manifest = dict(schema='gems64-publication-v1', generated_utc=card['reviewed_utc'],
                    policy=('exactly one NOT-cleared candidate may be published; promoted artifacts cannot be '
                            'rendered by this builder; no other raster may exist under docs/'),
                    candidate_published=pub is not None,
                    candidate=None if pub is None else dict(
                        tif=f"downloads/{pub['tif'].name}",
                        zip=f"downloads/{pub['zip'].name}",
                        receipt=f"downloads/{pub['receipt_path'].name}",
                        sha256=pub['receipt']['sha256'],
                        zip_sha256=pub['receipt']['zip_sha256'],
                        submission_name=pub['receipt']['submission_name'],
                        note=pub['receipt']['note'],
                        approved_for_weekly_slot=False,
                        promoted=False,
                        registry_verdict=pub['emission']['registry']['verdict'],
                        duplicate_flags=pub['receipt']['metadata']['duplicate_flags']))
    (DOCS / 'data/publication.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Built five static pages. Verdict negative; '
          + ('one NOT-CLEARED candidate published.' if pub else 'no candidate published.'))


if __name__ == '__main__':
    main()
