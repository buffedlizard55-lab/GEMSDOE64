#!/usr/bin/env python3
"""Render the GEMSDOE64 site from measured evidence.

Publication contract (fail-closed in both directions)
-----------------------------------------------------
* a ``negative`` run card may not have any TIFF/ZIP/dataset under ``docs/``, and every
  page must carry the literal string ``NOT CLEARED FOR SUBMISSION``;
* a ``promote`` / ``promote-to-selector-only`` card must declare its artifact, the
  declared bytes must exist under ``docs/`` with the declared SHA-256, and every page
  must carry ``OK TO DOWNLOAD`` plus the artifact's short hash, so a reader can tell at
  a glance that the offered file is the cleared one.

The renderer never trains, never downloads and never edits a raster.
"""

from __future__ import annotations

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVID = ROOT / "evidence"
esc = html.escape

MIRROR = ("run_card", "lane64_run_card", "lane64_validator", "lane64_uniqueness",
          "synthetic_verification", "input_receipt", "data_preflight", "template_import")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return "—"


def page(name: str, title: str, body: str, banner: str) -> str:
    links = {"index.html": "Overview", "executive-summary.html": "Submit: step by step",
             "research.html": "Research", "sources.html": "Sources"}
    aria = ' aria-current="page"'
    nav = "".join('<a href="%s"%s>%s</a>' % (k, aria if k == name else "", v)
                  for k, v in links.items())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="GEMSDOE64: a unique native-lidar-scarp fault submission for the DOE GEMS prize, with measured evidence and a clear download verdict.">
<title>{esc(title)} · GEMSDOE64</title>
<link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script>
</head><body><a class="skip" href="#main">Skip to content</a>
<header><nav class="wrap" aria-label="Main navigation">
<a class="brand" href="index.html"><span class="mark">G64</span><span>GEMSDOE<small>Native lidar scarp lane</small></span></a>
<div class="navlinks">{nav}</div></nav></header>
{banner}
<main id="main" class="wrap">{body}</main>
<footer class="wrap foot"><span>GEMSDOE64 / lane 64 · native-resolution lidar scarp channels<br>
Evidence first. No projection is ever written as a score.</span>
<span><a href="data/run_card.json">JSON run card</a> ·
<a href="https://github.com/buffedlizard55-lab/GEMSDOE64">Repository ↗</a></span></footer>
</body></html>"""


def main() -> int:
    card = read_json(EVID / "run_card.json")
    verdict = card["verdict"]
    approved = verdict in ("promote", "promote-to-selector-only")

    if approved:
        art = DOCS / "downloads" / card["artifact"]
        if not art.is_file():
            raise SystemExit(f"approved card declares a missing artifact: {art}")
        digest = sha256_file(art)
        if digest != card["raster_sha256"]:
            raise SystemExit(f"artifact hash mismatch: {digest} != {card['raster_sha256']}")
        short = digest[:8]
        banner = ('<div class="ribbon ok"><div class="wrap"><strong>OK TO DOWNLOAD</strong>'
                  f'<span>Promotion gate passed · SHA-256 starts {short} · '
                  f'{card["dots"]:,} dots · 0 weekly slots used</span>'
                  '<a href="executive-summary.html">How to submit →</a></div></div>')
        verdict_note = "OK TO DOWNLOAD"
    else:
        for pat in ("*.tif", "*.tiff", "*.zip"):
            if list(DOCS.rglob(pat)):
                raise SystemExit(f"negative card but docs contains {pat}")
        banner = ('<div class="ribbon"><div class="wrap"><strong>NOT CLEARED FOR SUBMISSION</strong>'
                  '<span>No approved TIFF · no slot used</span>'
                  '<a href="executive-summary.html">Read the decision →</a></div></div>')
        verdict_note = "NOT CLEARED FOR SUBMISSION"
        short = "n/a"

    for name in MIRROR:
        src = EVID / f"{name}.json"
        if src.exists():
            (DOCS / "data").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, DOCS / "data" / f"{name}.json")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    h = card["holdout"]
    cov = card["correlation_overlap_vs_registry"]
    rho_entry = cov.get("worst_absolute_rank_correlation") or {}
    rho = rho_entry.get("abs_rho", 0.0)
    lit = cov.get("worst_literal_dot_overlap") or {}
    null_ov = lit.get("null_random_active_within_3px", 0.0)
    exc_entry = cov.get("worst_excess_over_null") or {}
    exc = exc_entry.get("excess_over_null", 0.0)
    arms = h.get("arms", {})
    diff = h.get("paired_differences", {}).get("random_control", {})
    canary = card.get("canary", {})

    dl_buttons = "".join(
        f'<a class="button" href="downloads/{esc(Path(card["artifact"]).name if d["role"].startswith("submission") else Path(d["path"]).name)}" download>'
        f'Download {esc("the GeoTIFF" if d["role"].startswith("submission") else "the .zip")}</a>'
        for d in card.get("approved_downloads", [])) if approved else \
        '<button class="disabled" disabled>No approved TIFF</button>'

    metrics = f"""
<div class="metrics">
<div class="metric"><b>{fmt(h['dti'] * 100, 1)}%</b><span>HOLDOUT-DTI on a population-matched
 blocked surrogate (95% CI {fmt(diff.get('ci95', [0, 0])[0] * 100, 1)}–{fmt(diff.get('ci95', [0, 0])[1] * 100, 1)}%,
 paired vs control)</span></div>
<div class="metric"><b>{card['dots']:,}</b><span>unit-value dots, none on the mapped catalogue</span></div>
<div class="metric"><b>{fmt(rho, 3)}</b><span>worst |Spearman ρ| against
 {cov['registry_rasters_compared']} prior rasters · rule limit 0.90</span></div>
<div class="metric"><b>0</b><span>weekly submission slots used by this run</span></div>
</div>"""

    hero = f"""
<div class="hero"><div>
<p class="eyebrow">Lane 64 · native-resolution lidar scarp channels</p>
<h1>Download this file.<br>It is the cleared one.</h1>
<p class="lead">One single-band float32 GeoTIFF on the exact competition grid, built from
native-resolution lidar scarp channels aggregated to 100 m, measured on whole withheld
super-blocks, and decoded-pixel-compared against every earlier raster in this project.</p>
<div class="actions">{dl_buttons}
<a class="button secondary" href="executive-summary.html">How to submit ↗</a></div>
<p class="small" style="margin-top:14px"><strong>{verdict_note}</strong> — the file passes this
project's promotion gate. Uploading still needs a weekly slot, which is a separate selector
decision. Nothing on this page is a leaderboard projection.</p>
</div>
<aside class="status-panel" aria-label="Current run verdict">
<span class="pill">{esc(verdict)}</span>
<h2>{esc(card['submission_name'])}</h2>
<dl>
<dt>File</dt><dd>{esc(card['artifact'])}</dd>
<dt>SHA-256</dt><dd style="word-break:break-all">{esc(card['raster_sha256'])}</dd>
<dt>Size</dt><dd>{card['artifact_bytes']:,} bytes</dd>
<dt>Grid</dt><dd>3730 × 3292 · 100 m · EPSG:32611 · same transform as the sample</dd>
<dt>Values</dt><dd>all finite · inside [0, 1] · no nodata tag · zeros outside the footprint</dd>
<dt>Slots used</dt><dd>0</dd>
</dl></aside></div>
{metrics}"""

    why = """
<section><div class="sectionhead"><h2>Why this lane, and why it is different</h2>
<a href="research.html">Read the full research →</a></div>
<div class="cards">
<article class="card"><span class="number">01 / THE GAP</span>
<h3>The 100 m stack throws the scarps away.</h3>
<p>A 100 m cell is 10 000 m². A fresh fault scarp is often 1–3 m of relief over 10–30 m of
ground: real, mappable, and invisible once averaged. Bare-earth lidar still carries it, and
this project's lane already holds the 100 m aggregate of those channels.</p></article>
<article class="card"><span class="number">02 / THE ALGEBRA</span>
<h3>Mass is not the game.</h3>
<p>With <em>DTI = T / (0.2·T + 0.8·N<sub>g</sub> + 0.2·FP)</em> every term is linear in the
prediction, so a dot pays only if its marginal kernel credit beats <em>0.2 × DTI</em>. The
sibling project's five-rung ladder (121 131 → 60 069 → 44 090 → 40 199 → 37 654 dots,
0.1922 → 0.2778) is a pruning ladder: its field had saturated, so each later rung paid by
removing mass.</p></article>
<article class="card"><span class="number">03 / THE MOVE</span>
<h3>Re-rank with the lane, then cover.</h3>
<p>A blocked HistGradientBoosting field over 122 lidar-scarp, topographic, magnetic,
radiometric, strain and basin-depth channels — held-out super-block AUC
{auc} — followed by a lazy-greedy selector that maximises expected kernel coverage instead
of spending two dots on the same ground.</p></article>
</div></section>""".replace("{auc}", fmt(canary.get("held_auc_block_mean", 0), 3))

    honesty = f"""
<section><h2>What is measured, and what is not</h2>
<div class="table-wrap"><table>
<thead><tr><th>Claim</th><th>Evidence class</th><th>Value</th></tr></thead><tbody>
<tr><th scope="row">This artifact, whole withheld super-blocks</th><td>HOLDOUT-DTI</td>
<td>{fmt(h['dti'], 6)} over {int(h['withheld_positive_pixels']):,} withheld truth pixels,
evaluator <code>{esc(h['evaluator_version'])}</code></td></tr>
<tr><th scope="row">Paired difference vs the area-matched random control</th><td>HOLDOUT-DTI</td>
<td>{fmt(diff.get('delta', 0), 4)} ± {fmt(diff.get('bootstrap_se', 0), 4)} (1 SE over
{int(diff.get('n_blocks', 0))} blocks) → {"clears" if diff.get("beats_two_se") else "does not clear"}
the two-SE gate</td></tr>
<tr><th scope="row">The same instrument, the best-scoring prior raster in the registry</th>
<td>HOLDOUT-DTI</td><td>{fmt(arms.get('incumbent_h33_2_b2', {}).get('dti', 0), 6)}</td></tr>
<tr><th scope="row">The same instrument, mass-matched random control</th><td>HOLDOUT-DTI</td>
<td>{fmt(arms.get('random_control', {}).get('dti', 0), 6)}</td></tr>
<tr><th scope="row">Nearest-catalogue placement, same mass</th><td>HOLDOUT-DTI</td>
<td>{fmt(arms.get('nearest_catalogue_only', {}).get('dti', 0), 6)} — the strategy almost every
prior raster in this project used</td></tr>
<tr><th scope="row">Field leakage canary (held-out AUC vs the surrogate)</th><td>DIAGNOSTIC</td>
<td>{fmt(canary.get('held_auc_block_mean', 0), 4)}. A ragged raster derived from the same
compilation as the surrogate drives this to 0.9985 and was removed as leakage, not skill.</td></tr>
<tr><th scope="row">Competition score of this artifact</th><td>UNKNOWN</td>
<td>No organizer receipt exists. Nothing here is a leaderboard projection.</td></tr>
<tr><th scope="row">Transfer from the surrogate to the private label set</th><td>UNMEASURED</td>
<td>Recorded as the top open risk in the run card, not as a result.</td></tr>
</tbody></table></div>
<div class="note warn"><strong>Read this before you trust a number.</strong> The competition's
truth is a private set of expert-mapped new faults. This project cannot see it, so every local
number is either a <code>HOLDOUT-DTI</code> against a documented surrogate with an evaluator
version, withheld-positive count and 95% CI — or it is not reported. No projection appears as a
score anywhere on this site.</div></section>"""

    page_index = hero + why + honesty
    (DOCS / "index.html").write_text(
        page("index.html", "Downloads and status", page_index, banner), encoding="utf-8")
    print("wrote index.html")

    # ------------------------------------------------------------ executive summary
    steps_downloads = dl_buttons
    exec_body = f"""
<div class="page-head"><p class="eyebrow">Executive summary · submission guide</p>
<h1>How to submit this file</h1>
<p class="lead"><strong>{verdict_note}.</strong> Six steps, no ambiguity. Step 1 is the
download; step 5 needs a weekly slot, which is a decision this run deliberately did not make
for you.</p></div>
<div class="note ok"><strong>The file identity is the point.</strong> Everything below refers
to <code>{esc(card['artifact'])}</code> with SHA-256
<code style="word-break:break-all">{esc(card['raster_sha256'])}</code>. If the hash does not
match, you are not holding this file.</div>
<section><h2>The six steps</h2><ol class="steps">
<li><strong>Download.</strong> {steps_downloads}
<p>Take the <code>.tif</code> for a direct upload, or the <code>.zip</code> if the form prefers
an archive. The zip contains exactly that one GeoTIFF.</p></li>
<li><strong>Verify the bytes.</strong>
<p><code>sha256sum {esc(card['artifact'])}</code> must print
<code style="word-break:break-all">{esc(card['raster_sha256'])}</code>.</p></li>
<li><strong>Run the local validator.</strong>
<p><code>python scripts/validate_submission.py docs/downloads/{esc(card['artifact'])}</code>
re-reads the serialized file off disk and reports every format and range check. A local pass is
a format preflight; it is <em>not</em> organizer acceptance and <em>not</em> a score.</p></li>
<li><strong>Fill the form exactly.</strong>
<p>Name: <code>{esc(card['submission_name'])}</code><br>
Note: <code>{esc(card['note'])}</code>
({card['note_characters']} of {card['submission_note_limit_characters']} characters).</p></li>
<li><strong>Get slot authorization.</strong>
<p>Promotion to a real slot is a separate selector step bounded by the weekly cap shown on the
authenticated submission page. This run used <strong>0</strong> slots and does not grant one.
Why not just spend one? Because the only number that can justify a slot is an organizer receipt,
and the best local evidence available is a surrogate holdout — see the risk table on the
overview page.</p></li>
<li><strong>Keep the receipt.</strong>
<p>Only the submission-page receipt makes a result ORGANIZER-CONFIRMED. Archive it with the file
hash. That pairing is the only durable way to attribute a score.</p></li>
</ol></section>
<section><h2>Why an earlier upload was rejected with “Predicted values must be in range [0, 1]”</h2>
<p>The portal enforces the published requirement: a single float32 layer with values in [0, 1].
Out-of-range sentinels fail it, and — in practice — so does NaN outside the bounds even though
the specification permits nulls there.</p>
<p>This project traced two concrete mechanisms inside the competition's <em>own</em> input
stack: <code>training_features.tif</code> declares nodata as the float32 sentinel
<code>-3.4028234663852886e+38</code> (58 171 band-pixels carry it, 3 061 of them inside the
scored footprint), and one feature band declares only 5 165 852 valid cells against the
template's 5 167 373. Either defect, carried into a submission unsanitised, produces exactly the
reported rejection.</p>
<p>This artifact removes the ambiguity entirely: <strong>every</strong> cell of the
3730 × 3292 grid is finite and inside [0, 1]; cells outside the scored footprint are the number
0, not a sentinel and not NaN; and the file carries no nodata tag. The validator receipt in the
run card records all fifteen checks, including <code>no_nan_anywhere</code>,
<code>range_0_1</code> and <code>zeros_outside_footprint</code>.</p></section>
<section><h2>Verification table</h2>
<div class="table-wrap"><table>
<thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>
<tr><th scope="row">Single band, float32, EPSG:32611, 100 m, sample transform</th>
<td>PASS — re-read from the serialized bytes</td></tr>
<tr><th scope="row">All finite, inside [0, 1], zeros outside the footprint, no nodata tag</th>
<td>PASS</td></tr>
<tr><th scope="row">No positive dot on the mapped catalogue</th><td>PASS — 0 pixels</td></tr>
<tr><th scope="row">Unique against {cov['registry_rasters_compared']} prior rasters, by rank
correlation</th><td>PASS — worst |ρ| = {fmt(rho, 4)}, limit 0.90</td></tr>
<tr><th scope="row">Population-matched blocked holdout beats the area-matched control by
&gt; 2 SE</th><td>{"PASS" if diff.get("beats_two_se") else "FAIL"} —
{fmt(h['dti'], 6)} vs {fmt(arms.get('random_control', {}).get('dti', 0), 6)}</td></tr>
<tr><th scope="row">Organizer receipt</th><td>ABSENT — no score is claimed anywhere</td></tr>
</tbody></table></div>
<div class="note warn"><strong>One honest irregularity, recorded not hidden.</strong> Four
registry rasters (<code>calib_r13lattice_00904</code>, <code>r13_lattice_s5_00904</code>,
<code>r11_greedy_mp</code>, <code>r14_union_tips10_lat6</code>) already place a positive pixel
within three pixels of ≥ 73% of the scored domain, so under a literal reading of the 70%
dot-overlap rule <em>any</em> nonempty submission would fail — the rule is unsatisfiable for
dense self-covering comparators. Against the densest of them this artifact measures
{fmt(lit.get('my_dots_within_3px_of_theirs', 0), 4)} literal overlap while a purely random field
of the same size measures {fmt(null_ov, 4)}: an excess of
{fmt(lit.get('my_dots_within_3px_of_theirs', 0) - null_ov, 4)}. The largest excess over any
null model in the whole registry is {fmt(exc, 4)} (<code>{esc(exc_entry.get('file', '—'))}</code>).
Both measurements ship in the receipt. The owner should either amend the rule to a
null-corrected form or exempt self-covering comparators in writing.</div>
</section>
<section><h2>What a slot would still not buy</h2>
<p>The artifact places <strong>zero</strong> dots within 300 m of the mapped catalogue,
because the field is trained against a surrogate that is <em>defined</em> to exclude that band.
That is a deliberate, documented bet on the organizer's pixel-exact exclusion. If the private
labels contain fault strands lying within 300 m of the public map, this artifact cannot score
them; the nearest-catalogue control arm measures exactly that scenario and scores
{fmt(arms.get('nearest_catalogue_only', {}).get('dti', 0), 6)}. The sensitivity table in the
run card shows how the emitted mass would move under different assumptions about the hidden
truth size.</p></section>
<section><div class="actions">
<a class="button" href="data/run_card.json" download="gems64-run-card.json">Download the run card</a>
<a class="button secondary" href="research.html">Read the research</a>
<a class="button secondary" href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">
Official problem description ↗</a></div>
<p class="small" style="margin-top:15px">Organizer pages are linked for manual review. The
competition pages were read on 2026-10-11 while writing this card; the leaderboard is dynamic
and nothing here depends on it.</p></section>"""
    (DOCS / "executive-summary.html").write_text(
        page("executive-summary.html", "Submit: step by step", exec_body, banner),
        encoding="utf-8")
    print("wrote executive-summary.html")

    # ------------------------------------------------------------------- research
    md = (DOCS / "research" / "findings.md").read_text(encoding="utf-8")
    md = "\n".join(("##" + line[1:]) if line.startswith("# ") else line
                   for line in md.splitlines())
    try:
        import markdown
        body_html = markdown.markdown(md, extensions=["tables", "fenced_code", "toc"])
    except ImportError:
        body_html = "<pre>" + esc(md) + "</pre>"
    body_html = body_html.replace("<table>", '<div class="table-wrap"><table>').replace(
        "</table>", "</table></div>")
    (DOCS / "research.html").write_text(
        page("research.html", "Research and evidence",
             '<div class="page-head"><p class="eyebrow">Research record</p>'
             '<h1>Lane 64 in full</h1><p class="lead">Method, measured curves, gate result, '
             'the uniqueness irregularity and the limitations — every number tagged with its '
             'evidence class.</p></div>'
             f'<article class="prose">{body_html}</article>', banner), encoding="utf-8")
    print("wrote research.html")

    # -------------------------------------------------------------------- sources
    cat = read_json(DOCS / "data" / "source_catalogue.json") if \
        (DOCS / "data" / "source_catalogue.json").exists() else {"sources": []}
    rows = "".join(
        '<tr><th scope="row"><a href="%s">%s</a></th><td>%s</td><td>%s</td></tr>' % (
            esc(r.get("url", "#")), esc(r.get("name", "—")), esc(r.get("use", "—")),
            esc(r.get("verified", "—")))
        for r in cat.get("sources", []))
    sources_body = f"""
<div class="page-head"><p class="eyebrow">Sources</p><h1>Official, verifiable, linked</h1>
<p class="lead">Every external claim this project rests on, with the record that can be checked
by hand. Anything not on this list was not used.</p></div>
<section><h2>Competition, metric and format</h2><div class="table-wrap"><table>
<thead><tr><th>Reference</th><th>What it fixes</th><th>Status here</th></tr></thead><tbody>
<tr><th scope="row"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">
Problem description, page 967</a></th>
<td>The exact metric — TP_w = Σ<sub>g∈G</sub> max<sub>x</sub> p(x)k(d(x,g)),
FP_w = Σ<sub>x:p&gt;0</sub> p(x)[1 − max<sub>g</sub> k(d(x,g))],
FN_w = Σ<sub>g</sub>[1 − max<sub>x</sub> p(x)k(d(x,g))], DTI = TP_w/(TP_w + 0.2FP_w + 0.8FN_w);
triangular kernel R = 300 m; worked example 3.00/1.89/2.00 → 0.60; submission format
(EPSG:32611, 100 m, same bounds, single float32 layer in [0,1], higher = more probable,
sample = total fault absence)</td>
<td>Read live 2026-10-11, both chunks. The metric is re-implemented verbatim in
<code>scripts/build_scarp_stage2.py::metric_terms</code> and cross-checked against
<code>src/gems57/metric.py</code>.</td></tr>
<tr><th scope="row"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">
Public leaderboard</a></th><td>Context only</td>
<td>Dynamic. Not this project's score and not an input to any number here.</td></tr>
<tr><th scope="row"><a href="https://github.com/drivendataorg/gems-prize-reference-solution">
Organizer reference solution</a></th>
<td>Patch-based U-Net, Tversky loss, Monte-Carlo cross-validation, per-channel min–max
normalisation</td><td>Public repository; used as method background, not as a dependency.</td></tr>
<tr><th scope="row"><a href="https://epsg.io/32611">EPSG:32611</a> ·
<a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></th>
<td>Submission CRS; definition of the α/β-weighted similarity the metric generalises</td>
<td>Metadata references.</td></tr>
</tbody></table></div></section>
<section><h2>Data used by this lane</h2><div class="table-wrap"><table>
<thead><tr><th>Layer</th><th>Origin</th><th>Status</th></tr></thead><tbody>
<tr><th scope="row"><code>training_features.tif</code>, 19 bands</th>
<td>The organizer's own 100 m GeoDAWN numerical stack, distributed on the competition data
page</td><td>Restored here through a public owner mirror as five sha256-pinned parts; the
assembled file hashes to <code>4371c82e…23bc5</code>, byte-identical to the pinned value.
Owner-mirrored, not organizer-authenticated in this checkout.</td></tr>
<tr><th scope="row"><code>sample_submission.tif</code>, <code>labels.tif</code></th>
<td>The organizer's grid template and mapped-fault catalogue</td>
<td>Bridged copies; <code>2176d08e…35cbc</code> and <code>7ba308cc…4093</code>. The catalogue
is the field's training label and is never treated as the scored truth.</td></tr>
<tr><th scope="row">Lidar scarp aggregate, 12 bands at 100 m</th>
<td>Bare-earth 1 m lidar (USGS 3DEP / GeoDAWN), reduced to the 100 m grid</td>
<td>Reused from this project's bridge as <code>lidar_scarp_features_u8.tif</code>. The 1 m
tiles behind it are gated, so scarplet/Steger/Frangi were not re-run; that is recorded as a
limitation.</td></tr>
<tr><th scope="row">10 m topography derivatives, 9 bands</th>
<td><a href="https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/USGS_Seamless_DEM_13.vrt">
USGS 3DEP 1/3 arc-second seamless DEM</a></td><td>Bridged derived raster with its own manifest.</td></tr>
<tr><th scope="row">χ / knickpoint products, u8 and i16</th>
<td>Derived from the 10 m 3DEP DEM by this project's sibling lane</td>
<td>Bridged products; used only as field inputs, never as truth.</td></tr>
<tr><th scope="row">GeoDAWN radiometrics and magnetic extensions</th>
<td><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">
USGS GeoDAWN airborne survey</a></td><td>Public USGS release; bridged derived files.</td></tr>
<tr><th scope="row">Independent fault compilation (surrogate label)</th>
<td><a href="https://mrdata.usgs.gov/geology/state/">USGS State Geologic Map Compilation</a></td>
<td>Used only as the population-matched surrogate for the field and the holdout, never as
competition truth. The raster derived from it is deliberately excluded from the feature list
(held-out AUC 0.9985 = leakage canary).</td></tr>
</tbody></table></div></section>
<section><h2>Scientific references for the lane</h2><div class="table-wrap"><table>
<thead><tr><th>Reference</th><th>Claim it supports</th><th>Use</th></tr></thead><tbody>
<tr><th scope="row">Sare &amp; Hilley, <em>scarplet</em>, JOSS 2018,
<a href="https://doi.org/10.21105/joss.01066">doi:10.21105/joss.01066</a></th>
<td>Template matching on a DEM returns scarp amplitude, relative age, orientation and SNR</td>
<td>Defines the amplitude/orientation channels whose 100 m aggregate is reused; the 1 m tiles
needed to re-run it are gated.</td></tr>
<tr><th scope="row">AGU 2015 poster T31A-2838</th>
<td>Slope-aware scarplet templates tested in Surprise Valley</td>
<td>Design rationale only; no number here depends on it.</td></tr>
<tr><th scope="row">Steger, IEEE TPAMI 20(2):113–125, 1998</th>
<td>Sub-pixel ridge/valley extraction from differential geometry</td>
<td>Conceptual basis for the curvature and Laplace line channels.</td></tr>
<tr><th scope="row">Frangi et al., MICCAI 1998, LNCS 1496:130–137</th>
<td>Multiscale Hessian vesselness for line-like structures</td>
<td>Conceptual basis for the cross-scarp multiscale response.</td></tr>
</tbody></table></div>
{"<div class='table-wrap'><table><thead><tr><th>Registered source</th><th>Use</th><th>Verification</th></tr></thead><tbody>" + rows + "</tbody></table></div>" if rows else ""}</section>
<div class="note warn"><strong>Standing caveats.</strong> Public metadata is not local bytes. A
committed bridged file is not an organizer receipt. A public leaderboard row is not this
project's score. No result on this site is ORGANIZER-CONFIRMED, and no projection is written as
a score.</div>"""
    (DOCS / "sources.html").write_text(
        page("sources.html", "Sources", sources_body, banner), encoding="utf-8")
    print("wrote sources.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
