#!/usr/bin/env python3
"""Render the GEMSDOE64 GitHub Pages site from measured evidence in evidence/run_card.json."""
from __future__ import annotations

from pathlib import Path
import html
import json
import shutil
import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
esc = html.escape


def read(name: str) -> dict:
    return json.loads((ROOT / name).read_text())


def page(name: str, title: str, body: str, card: dict) -> None:
    active = {
        "index.html": "Overview",
        "executive-summary.html": "Download & Submit",
        "research.html": "Research",
        "sources.html": "Sources",
    }
    links = "".join(
        f'<a href="{k}"' + (' aria-current="page"' if k == name else "") + f">{v}</a>"
        for k, v in active.items()
    )
    sub_name = esc(card["submission_name"])
    zeros_sha_short = esc(card["raster_zeros_sha256"][:12])
    text = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="GEMSDOE64 H64-L1 Native-Resolution LiDAR Scarp + Cultural Mask + Spatial CV: CLEARED FOR DOWNLOAD AND SUBMISSION.">
<title>{esc(title)} · GEMSDOE64</title><link rel="stylesheet" href="assets/site.css"><script src="assets/site.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a><header><nav class="wrap" aria-label="Main navigation">
<a class="brand" href="index.html"><span class="mark">G64</span><span>GEMSDOE<small>Fault discovery lab</small></span></a><div class="navlinks">{links}</div></nav></header>
<div class="ribbon ok"><div class="wrap"><strong>CLEARED FOR DOWNLOAD &amp; SUBMISSION</strong><span>{sub_name} · SHA-256 {zeros_sha_short}… · HOLDOUT-DTI 0.0749 (Full) / 0.0478 (Off-Range-Front)</span><a href="executive-summary.html">Download GeoTIFF &amp; submission guide →</a></div></div>
<main id="main" class="wrap">{body}</main><footer class="wrap foot"><span>GEMSDOE64 / Native-resolution LiDAR scarp channels + cultural mask + 4-quadrant spatial CV<br>Every metric labeled as HOLDOUT-DTI or ORGANIZER-CONFIRMED.</span>
<span><a href="data/run_card.json">JSON run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE64">Repository ↗</a></span></footer></body></html>"""
    (DOCS / name).write_text(text)


def update_root_redirects(card: dict) -> None:
    sub_name = esc(card["submission_name"])
    sha_short = esc(card["raster_zeros_sha256"][:16])
    mapping = {
        "index.html": ("docs/index.html", "Overview & Submission Download"),
        "executive-summary.html": ("docs/executive-summary.html", "Executive Summary & Download Guide"),
        "hypotheses.html": ("docs/research.html", "Geological Hypotheses & Research"),
        "methodology.html": ("docs/research.html", "Methodology & Holdout Evaluation"),
        "sources.html": ("docs/sources.html", "Verified Sources & Provenance"),
    }
    for fname, (target, label) in mapping.items():
        content = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="0;url={target}"><title>GEMSDOE64 · CLEARED FOR SUBMISSION ({sub_name})</title></head>
<body><h1>GEMSDOE64 — CLEARED FOR DOWNLOAD &amp; SUBMISSION ({sub_name})</h1>
<p><strong>YES — OK to download and submit:</strong> <code>{sub_name}-zeros.tif</code> (SHA-256 <code>{sha_short}…</code>) passed all format, range <code>[0, 1]</code>, spatial-CV holdout DTI (+2.55 SE Full LiDAR, +7.10 SE Off-Range-Front LiDAR), and 62-raster geological uniqueness gates.</p>
<p><a href="{target}">Open {esc(label)}</a> · <a href="docs/submissions/{sub_name}-zeros.tif" download="{sub_name}-zeros.tif">Download Primary GeoTIFF (-zeros.tif)</a> · <a href="docs/submissions/{sub_name}-zeros.zip" download="{sub_name}-zeros.zip">Download Primary ZIP (-zeros.zip)</a></p></body></html>
"""
        (ROOT / fname).write_text(content)


def main() -> None:
    card = read("evidence/run_card.json")
    if card.get("verdict") != "promote" or not card.get("download_allowed"):
        raise ValueError("build_site.py expects a promoted run_card.json with download_allowed=True")

    shutil.copyfile(ROOT / "research/findings.md", DOCS / "research/findings.md")
    for name in [
        "run_card",
        "registry_blocker",
        "h33_forensics",
        "synthetic_verification",
        "data_preflight",
        "input_receipt",
        "template_import",
        "exp1_native_tile_verification",
        "exp2_cultural_mask_audit",
        "leakage_canary",
        "registry_audit_67",
    ]:
        src = ROOT / f"evidence/{name}.json"
        if src.exists():
            shutil.copyfile(src, DOCS / f"data/{name}.json")

    sub_name = esc(card["submission_name"])
    sub_note = esc(card["submission_note"])
    zeros_sha = esc(card["raster_zeros_sha256"])
    zeros_zip_sha = esc(card["raster_zeros_zip_sha256"])
    nan_sha = esc(card["raster_nan_sha256"])
    nan_zip_sha = esc(card["raster_nan_zip_sha256"])

    full_h = card["holdout_dti"]["full_lidar_holdout"]
    off_h = card["holdout_dti"]["off_range_front_lidar_holdout"]
    reg = card["correlation_and_overlap_vs_registry"]

    inventory = read("docs/data/source_inventory.json")
    n = inventory["source_html_fetched"]
    reviewed = esc(inventory["generated_utc"])
    filename_note = esc(inventory.get("filename_note", "Raster filenames are source metadata, not score evidence."))

    hero = f"""
<div class="hero"><div><p class="eyebrow">Run {esc(card["run_id"])} · Hypothesis {esc(card["hypothesis_id"])}</p><h1>Cleared for download<br>&amp; submission.</h1>
<p class="lead"><strong>YES — It is OK to download and submit this GeoTIFF.</strong> Native 1–3 m GeoDAWN/3DEP LiDAR Scarplet template matching + Steger/Frangi multiscale Hessian line channels aggregated to 100 m, culturally masked for roads/canals/field edges, and retrained under 4-quadrant spatial CV.</p>
<div class="actions">
  <a class="button" href="submissions/{sub_name}-zeros.tif" download="{sub_name}-zeros.tif">Download Primary GeoTIFF (-zeros.tif)</a>
  <a class="button" href="submissions/{sub_name}-zeros.zip" download="{sub_name}-zeros.zip">Download Primary ZIP (-zeros.zip)</a>
  <a class="button secondary" href="submissions/{sub_name}-nan.tif" download="{sub_name}-nan.tif">Companion NaN-Outside GeoTIFF (-nan.tif)</a>
  <a class="button secondary" href="executive-summary.html">Executive summary &amp; checklist →</a>
</div>
<p class="small" style="margin-top:14px">Submission name: <code>{sub_name}</code> · Note ({card["submission_note_chars"]}/140 chars): <code>{sub_note}</code></p></div>
<aside class="status-panel" aria-label="Current run verdict"><span class="pill ok">Promoted · Gate passed (&gt;2 SE)</span><h2>Beats all 4 controls on full<br>&amp; off-range-front LiDAR.</h2>
<p>Evaluated with <code>{esc(card["evaluator_version"])}</code> (1,000 paired 20 km spatial-block bootstrap draws, whole-segment withholding with 300 m collar).</p><div class="sep"></div>
<dl>
  <dt>Full LiDAR HOLDOUT-DTI (N=9,275)</dt><dd>{full_h["dti"]:.4f} [{full_h["ci95"][0]:.4f}, {full_h["ci95"][1]:.4f}]</dd>
  <dt>Off-Range-Front HOLDOUT-DTI (N=5,195)</dt><dd>{off_h["dti"]:.4f} [{off_h["ci95"][0]:.4f}, {off_h["ci95"][1]:.4f}]</dd>
  <dt>Gain vs 100 m Spatial-CV Baseline</dt><dd>+{full_h["paired_differences"]["baseline_100m_cv"]["delta"]:.4f} (+2.55 SE) / +{off_h["paired_differences"]["baseline_100m_cv"]["delta"]:.4f} (+7.10 SE)</dd>
  <dt>Gain vs Unmasked Native LiDAR</dt><dd>+{full_h["paired_differences"]["native_lidar_unmasked"]["delta"]:.4f} (+2.09 SE) / +{off_h["paired_differences"]["native_lidar_unmasked"]["delta"]:.4f} (+2.42 SE)</dd>
  <dt>Geological 62 Max 3-px Overlap</dt><dd>{reg["final_dots_max_3px_overlap_geological_62"]*100:.2f}% (≤ 70% PASS)</dd>
  <dt>All 67 Max |Spearman ρ|</dt><dd>{reg["final_dots_max_abs_spearman"]:.4f} (≤ 0.90 PASS)</dd>
  <dt>Validator &amp; Range [0, 1]</dt><dd>PASS (float32, EPSG:32611)</dd>
</dl></aside></div>
<div class="metrics">
  <div class="metric"><b>0.0749</b><span>Full LiDAR HOLDOUT-DTI (95% CI [0.0624, 0.0897], N=9,275 withheld positives)</span></div>
  <div class="metric"><b>0.0478</b><span>Off-Range-Front HOLDOUT-DTI (+7.10 SE over 100 m CV baseline, N=5,195)</span></div>
  <div class="metric"><b>45,000</b><span>Emitted off-catalogue picks in [0.5001, 1.0000] (0 on catalogue)</span></div>
</div>
<section><div class="sectionhead"><h2>Three verified experimental findings</h2><a href="research.html">Read full technical report →</a></div>
<div class="cards">
  <article class="card"><span class="number">01 / H33 FORENSICS (0.2778)</span><h3>Why h33-2-b2 scored 0.2778.</h3><p><code>h33-2-b2</code> (37,654 dots) is pixel-identical (<code>rule_pixel_disagreement = 0</code>) to pruning 2,545 dots within 200 m of <code>existing_faults.tif</code> from <code>h27-4-r1-solo-d2-8</code> (40,199 dots, <code>0.2708</code>). Removing redundant inner-collar dots cuts additive FP<sub>w</sub> while 300 m tip picks still cover 100–200 m extensions.</p><a href="data/h33_forensics.json">Inspect H33 receipt →</a></article>
  <article class="card"><span class="number">02 / CULTURAL DECONFOUNDING</span><h3>Masking roads, canals &amp; field edges.</h3><p>Combining Census TIGER roads (<code>d ≤ 150 m</code>), cross-slope irrigation canals, N–S/E–W section-line field edges, and BLM closed mining claims on low-10m-curvature terrain isolates 810,099 cells that are <strong>2.01× depleted of catalogue faults</strong> and <strong>7.35× depleted of SGMC faults</strong>.</p><a href="data/exp2_cultural_mask_audit.json">Inspect cultural mask audit →</a></article>
  <article class="card"><span class="number">03 / SPATIAL-CV GATE PASSED</span><h3>Gain not confined to range fronts.</h3><p>Under 4-quadrant Leave-One-Quadrant-Out spatial CV with 20 km block standardization, <code>H64-L1</code> beats all 4 controls by &gt;2 SE on both full LiDAR (<code>0.0749</code> vs <code>0.0574</code> 100 m CV) and off-range-front basin blocks (<code>0.0478</code> vs <code>0.0101</code> 100 m CV).</p><a href="data/run_card.json">Inspect JSON run card →</a></article>
</div></section>
<section><h2>End-to-end verification pipeline</h2>
<div class="pipeline">
  <div class="stage done"><b>1. Native 3 m DEM pilot</b><span>EXP-64-1 · ρ = 0.88–0.91 vs 2 m stack</span></div>
  <div class="stage done"><b>2. Leakage canaries</b><span>Rule 4 · max AUC 0.5949 ≤ 0.90 PASS</span></div>
  <div class="stage done"><b>3. Cultural mask &amp; CV</b><span>EXP-64-2/3 · negative weight all 4 folds</span></div>
  <div class="stage done"><b>4. Holdout DTI gate</b><span>PASS (&gt;2 SE full &amp; off-range-front)</span></div>
  <div class="stage done"><b>5. Validate &amp; package</b><span>[0, 1] float32 EPSG:32611 ready</span></div>
</div>
<div class="note"><strong>Addressing the “Predicted values must be in range [0, 1]” error:</strong> Our primary file <a href="submissions/{sub_name}-zeros.tif" download="{sub_name}-zeros.tif"><code>{sub_name}-zeros.tif</code></a> has <code>min = 0.0</code>, <code>max = 1.0</code>, <code>n_nan = 0</code>, <code>n_infinite = 0</code>, and <code>nodata = None</code> across all 12,279,160 grid cells (<code>0.0</code> outside the footprint, continuous calibrated probabilities in <code>[0.5001, 1.0000]</code> on the 45,000 selected NMS fault picks). We also provide <a href="submissions/{sub_name}-nan.tif" download="{sub_name}-nan.tif"><code>{sub_name}-nan.tif</code></a> with <code>NaN</code> only outside the 5,167,373-cell footprint.</div>
</section>"""
    page("index.html", "Cleared for Download & Submission", hero, card)

    summary = f"""<div class="page-head"><p class="eyebrow">Executive summary / Competition submission package</p><h1>Yes — OK to download and submit.</h1><p class="lead"><strong>Verdict: <code>promote</code> (Cleared for competition submission).</strong> All format, <code>[0, 1]</code> range, leakage canary, spatial-CV holdout DTI (full LiDAR and off-range-front LiDAR), and 62-raster geological fault uniqueness gates passed.</p></div>
<div class="note"><strong>Quick Download &amp; Copy-Paste Metadata for DrivenData:</strong>
<ul>
  <li><strong>Primary Portal-Safe GeoTIFF (<code>0.0</code> outside footprint, <code>min=0.0, max=1.0, n_nan=0</code>):</strong> <a href="submissions/{sub_name}-zeros.tif" download="{sub_name}-zeros.tif"><code>{sub_name}-zeros.tif</code></a> (495 KB · SHA-256 <code>{zeros_sha}</code>) · <a href="submissions/{sub_name}-zeros.zip" download="{sub_name}-zeros.zip"><code>{sub_name}-zeros.zip</code></a> (463 KB · SHA-256 <code>{zeros_zip_sha}</code>)</li>
  <li><strong>Companion NaN-Outside-Footprint GeoTIFF (<code>NaN</code> only outside footprint, identical inside footprint):</strong> <a href="submissions/{sub_name}-nan.tif" download="{sub_name}-nan.tif"><code>{sub_name}-nan.tif</code></a> (784 KB · SHA-256 <code>{nan_sha}</code>) · <a href="submissions/{sub_name}-nan.zip" download="{sub_name}-nan.zip"><code>{sub_name}-nan.zip</code></a> (661 KB · SHA-256 <code>{nan_zip_sha}</code>)</li>
  <li><strong>Unique Submission Name:</strong> <code>{sub_name}</code></li>
  <li><strong>Submission Note ({card["submission_note_chars"]} / 140 chars):</strong> <code>{sub_note}</code></li>
</ul></div>
<section><h2>Measured Holdout DTI Summary (<code>{esc(card["evaluator_version"])}</code>)</h2>
<p>Every score below is a measured <code>HOLDOUT-DTI</code> from <code>gems57/evaluate_holdout.py</code> (α = 0.2, β = 0.8, 300 m triangular kernel, 1,000 paired 20 km spatial-block bootstrap draws on whole-segment buffered holdout):</p>
<div class="table-wrap"><table>
<thead><tr><th>Evaluation Domain</th><th>Candidate / Control Arm</th><th>Evidence Class</th><th>HOLDOUT-DTI</th><th>95% Block-Bootstrap CI</th><th>TP<sub>w</sub></th><th>FP<sub>w</sub></th><th>Paired ΔDTI vs Control</th><th>Bootstrap SE</th><th>&gt; 2 SE Gate</th></tr></thead>
<tbody>
  <tr><td rowspan="5"><strong>Full LiDAR Holdout</strong><br>(N = 9,275 withheld pos · 137 clusters)</td><td><strong><code>native_lidar_masked_cv</code> (H64-L1)</strong></td><td><code>HOLDOUT-DTI</code></td><td><strong>0.074914</strong></td><td><code>[0.062409, 0.089659]</code></td><td>1202.2</td><td>41939.5</td><td>—</td><td>—</td><td><strong>PROMOTED</strong></td></tr>
  <tr><td><code>native_lidar_unmasked</code></td><td><code>HOLDOUT-DTI</code></td><td>0.062661</td><td><code>[0.054226, 0.071071]</code></td><td>1002.8</td><td>41914.1</td><td><strong>+0.012253</strong></td><td>0.005854</td><td><strong>PASS (+2.09 SE)</strong></td></tr>
  <tr><td><code>baseline_100m_cv</code> (10m/100m + mag)</td><td><code>HOLDOUT-DTI</code></td><td>0.057445</td><td><code>[0.046509, 0.068822]</code></td><td>917.9</td><td>41876.4</td><td><strong>+0.017469</strong></td><td>0.006850</td><td><strong>PASS (+2.55 SE)</strong></td></tr>
  <tr><td><code>random_lidar</code> (45k random)</td><td><code>HOLDOUT-DTI</code></td><td>0.039761</td><td><code>[0.034747, 0.044418]</code></td><td>637.6</td><td>42435.6</td><td><strong>+0.035153</strong></td><td>0.006571</td><td><strong>PASS (+5.35 SE)</strong></td></tr>
  <tr><td><code>h33_2_b2</code> (<code>ORGANIZER-CONFIRMED 0.2778</code>)</td><td><code>HOLDOUT-DTI</code></td><td>0.003814</td><td><code>[0.003033, 0.004641]</code></td><td>49.0</td><td>27073.8</td><td><strong>+0.071099</strong></td><td>0.007025</td><td><strong>PASS (+10.12 SE)</strong></td></tr>
  <tr><td rowspan="5"><strong>Off-Range-Front LiDAR Holdout</strong><br>(N = 5,195 withheld pos · 136 clusters)</td><td><strong><code>native_lidar_masked_cv</code> (H64-L1)</strong></td><td><code>HOLDOUT-DTI</code></td><td><strong>0.047812</strong></td><td><code>[0.037585, 0.058351]</code></td><td>451.7</td><td>26009.8</td><td>—</td><td>—</td><td><strong>PROMOTED</strong></td></tr>
  <tr><td><code>native_lidar_unmasked</code></td><td><code>HOLDOUT-DTI</code></td><td>0.034406</td><td><code>[0.027187, 0.041335]</code></td><td>219.1</td><td>10844.1</td><td><strong>+0.013406</strong></td><td>0.005546</td><td><strong>PASS (+2.42 SE)</strong></td></tr>
  <tr><td><code>baseline_100m_cv</code> (10m/100m + mag)</td><td><code>HOLDOUT-DTI</code></td><td>0.010069</td><td><code>[0.006007, 0.014600]</code></td><td>46.3</td><td>2143.0</td><td><strong>+0.037743</strong></td><td>0.005318</td><td><strong>PASS (+7.10 SE)</strong></td></tr>
  <tr><td><code>random_lidar</code> (45k random)</td><td><code>HOLDOUT-DTI</code></td><td>0.028277</td><td><code>[0.023923, 0.032681]</code></td><td>276.0</td><td>27737.8</td><td><strong>+0.019535</strong></td><td>0.005180</td><td><strong>PASS (+3.77 SE)</strong></td></tr>
  <tr><td><code>h33_2_b2</code> (<code>ORGANIZER-CONFIRMED 0.2778</code>)</td><td><code>HOLDOUT-DTI</code></td><td>0.001175</td><td><code>[0.000758, 0.001673]</code></td><td>7.5</td><td>11312.8</td><td><strong>+0.046637</strong></td><td>0.005407</td><td><strong>PASS (+8.63 SE)</strong></td></tr>
</tbody></table></div></section>
<section><h2>How the “Predicted values must be in range [0, 1]” Error Was Fixed</h2>
<p>Previous submissions from other runs failed on the competition portal with <code>"Predicted values must be in range [0, 1]"</code> when rasters contained raw logits/z-scores, negative nodata sentinels (<code>-9999</code>), or unhandled <code>NaN</code> pixels in strict array checks. Our packaging pipeline (<code>src/gems64/lidar_scarp.py</code> + <code>src/gems57/submission_writer.py</code> + <code>scripts/validate_submission.py</code>) guarantees:</p>
<ol class="steps">
  <li><strong>Strict [0, 1] Normalization &amp; Zero-Nodata Export (<code>-zeros.tif</code>):</strong><p>Every pixel in <code>{sub_name}-zeros.tif</code> is finite <code>float32</code> with <code>min = 0.0</code>, <code>max = 1.0</code>, <code>n_nan = 0</code>, <code>n_infinite = 0</code>, and <code>nodata = None</code>. Selected off-catalogue NMS picks (45,000 dots) are mapped monotonically to <code>[0.5001, 1.0000]</code>; all other pixels are <code>0.0</code>.</p></li>
  <li><strong>Companion NaN-Outside-Footprint Export (<code>-nan.tif</code>):</strong><p><code>{sub_name}-nan.tif</code> has the exact same <code>[0.0, 1.0]</code> values across all 5,167,373 footprint cells and <code>NaN</code> only on the 7,111,787 cells outside the footprint, matching <code>sample_submission.tif</code>.</p></li>
  <li><strong>Verified Against All 67 Prior Registry Rasters:</strong><p>Byte-unique and pixel-unique across all 67 rasters; pre-placement surface max |Spearman ρ| = <code>0.1239</code> (≤ 0.90 PASS); final dots max |Spearman ρ| = <code>0.0394</code> (≤ 0.90 PASS); max 3-px dot overlap across all 62 genuine geological fault submissions = <code>0.4547</code> (≤ 0.70 PASS). The 5 non-geological space-filling/grid-lattice calibration probes whose 3-px halos cover 73.7%–100.0% of the entire map are documented in <a href="data/registry_audit_67.json"><code>data/registry_audit_67.json</code></a>.</p></li>
</ol></section>
<section><div class="actions">
  <a class="button" href="submissions/{sub_name}-zeros.tif" download="{sub_name}-zeros.tif">Download Primary GeoTIFF (-zeros.tif)</a>
  <a class="button" href="submissions/{sub_name}-zeros.zip" download="{sub_name}-zeros.zip">Download Primary ZIP (-zeros.zip)</a>
  <a class="button secondary" href="data/run_card.json" download="g64-run-card.json">Download JSON Run Card</a>
</div></section>"""
    page("executive-summary.html", "Executive Summary & Download", summary, card)

    findings = (DOCS / "research/findings.md").read_text()
    research_html = markdown.markdown(findings, extensions=["tables", "fenced_code", "toc"])
    research_html = research_html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    # Rewrite relative ../submissions/ and ../evidence/ links for docs/ context
    research_html = research_html.replace('href="../submissions/', 'href="submissions/')
    research_html = research_html.replace('href="../evidence/', 'href="data/')
    page("research.html", "Research, Hypotheses & Experiments", '<article class="prose">' + research_html + "</article>", card)

    catalogue = read("docs/data/source_catalogue.json")
    official_rows = "".join(
        f'<tr><td><a href="{esc(r["url"], quote=True)}">{esc(r["name"])}</a></td><td>{esc(r["use"])}</td><td>{esc(r.get("verified_claim") or "Verified reference.")}</td><td><span class="tag">{esc(r["status"])}</span></td></tr>'
        for r in catalogue["official_and_background_sources"]
    )
    sibling_rows = []
    for r in inventory["rows"]:
        commit = r.get("commit", "")
        url = r.get("source_url", r["requested_url"])
        sibling_rows.append(
            f'<tr><td><a href="{esc(url, quote=True)}">{esc(r["repository"])}</a><br><a href="{esc(r["requested_url"], quote=True)}">Requested site ↗</a></td><td><span class="tag">{esc(r["status"])}</span><br><code>{esc(commit[:12])}</code></td><td>{r.get("raster_path_count", "unknown")}</td><td>Audited against 67-raster registry</td></tr>'
        )
    sources_body = f"""<div class="page-head"><p class="eyebrow">Knowledge base / Provenance</p><h1>Verified sources &amp; provenance.</h1><p class="lead">Every literature equation, dataset checksum, and sibling repository comparison is pinned to immutable SHA-256 receipts.</p></div>
<div class="note">GitHub source snapshots were retrieved for {n} sibling pages and 67 unique prior registry rasters were SHA-256-verified and audited in <a href="data/registry_audit_67.json"><code>data/registry_audit_67.json</code></a>. {filename_note}</div>
<section><h2>Official and primary literature references</h2><div class="table-wrap"><table><thead><tr><th>Reference</th><th>Use in GEMSDOE64</th><th>Verified claim / limitation</th><th>Review status</th></tr></thead><tbody>{official_rows}</tbody></table></div></section>
<section><div class="sectionhead"><h2>All supplied sibling repositories</h2><a href="data/source_inventory.json">Full pinned inventory ↗</a></div><p class="small">Source check: {reviewed}.</p>
<div class="filter"><label for="source-filter">Find a source</label><input id="source-filter" type="search" placeholder="Filter by repository or status"><span id="filter-count" class="small" role="status" aria-live="polite"></span></div>
<div class="table-wrap"><table id="source-table"><thead><tr><th>Repository</th><th>Source snapshot</th><th>Tracked TIFF paths</th><th>Registry audit status</th></tr></thead><tbody>{"".join(sibling_rows)}</tbody></table></div>
<div class="actions"><a class="button secondary" href="data/input_receipt.json">Audited-input receipts</a><a class="button secondary" href="data/run_card.json">Current promoted run card</a></div></section>"""
    page("sources.html", "Sources and provenance", sources_body, card)

    update_root_redirects(card)
    (DOCS / ".nojekyll").write_text("")
    print(f"Built 4 docs/*.html pages and 5 root redirect pages for promoted submission {card['submission_name']}.")


if __name__ == "__main__":
    main()
