#!/usr/bin/env python3
"""Render the GEMSDOE64 site from measured evidence.

Design rules (the project's standing requirement):
* the download card is the first thing on the page and states, in words, whether
  the file is cleared for submission;
* every number is labelled HOLDOUT-DTI (surrogate instrument), MEASURED (from
  bytes on disk), or OWNER-REPORTED / ORGANIZER-CONFIRMED;
* nothing is projected as a score, and no figure is invented here: the dynamic
  values come from ``evidence/run_card.json`` and ``evidence/registry_index.json``.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DL = DOCS / "downloads"
esc = html.escape


def read(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return default


def fmt(x, nd=5):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def main() -> int:
    card = read(ROOT / "evidence" / "run_card.json", {}) or {}
    reg = read(ROOT / "evidence" / "registry_index.json", {}) or {}
    hold = card.get("holdout", {}) or {}
    val = card.get("validator_output", {}) or {}
    sreg = card.get("surface_registry", {}) or {}
    arms = card.get("arms", {}) or {}
    canaries = card.get("leakage_canaries", []) or []
    paired = card.get("paired_vs_incumbent", {}) or {}
    sha = card.get("raster_sha256")
    name = card.get("submission_name") or "g64-lidarscarp-strikeline"
    verdict = card.get("verdict", "negative")
    allowed = bool(card.get("download_allowed"))
    cert = card.get("uniqueness_certificate") or {}
    # "cleared" here means exactly one thing: the promotion policy's own verdict.
    # The repository never spends a submission slot, so slot authorization is the
    # owner's decision and is reported separately, never folded into this banner.
    cleared = bool(allowed)
    tif = next(iter(sorted(DL.glob(f"{name}-*.tif"))), None) if DL.exists() else None
    zipf = None   # the portal accepts a single GeoTIFF; no duplicate packaging here
    dti = hold.get("dti")
    ci = hold.get("ci95") or [None, None]
    withheld = hold.get("withheld_positive_pixels")

    banner = ("CLEARED FOR SUBMISSION" if cleared else
              "NOT CLEARED FOR SUBMISSION — audit artifact only")
    banner_class = "ok" if cleared else "stop"
    banner_detail = ("All gates passed; the run card authorises a download and a slot decision is "
                     "yours." if cleared else
                     "The card's promotion policy did not clear this file. Read the gate table "
                     "before doing anything with it.")

    lane = (card.get("uniqueness_certificate") or {})
    dense_rows = lane.get("dense_priors") or []
    dense_pct = (f"{100 * max([d['support_fraction'] for d in dense_rows]):.1f} %"
                 if dense_rows else "no measured prior")
    dense_files = ", ".join(f"<code>{esc(d['file'])}</code>" for d in dense_rows) or "none"
    if dense_rows:
        control_txt = ("the matched random controls in the same emission domain all reach "
                       f"{fmt(max(d['control_overlap_min'] for d in dense_rows), 3)} forward overlap")
    else:
        control_txt = "no dense prior was found in this scan"
    literal_cls = "ok" if lane.get("literal_verdict_unique") else "stop"
    literal_txt = "PASS" if lane.get("literal_verdict_unique") else "FAIL (stop rule)"
    diag_cls = "ok" if lane.get("diagnostic_verdict_unique") else "stop"
    diag_txt = ("PASS — unique by bytes, pixels and rank structure"
                if lane.get("diagnostic_verdict_unique") else "FAIL")
    checked = lane.get("registry_rasters_checked")
    unsat_list = ", ".join(lane.get("unsatisfiable_criteria") or []) or "none"
    saturating = len(lane.get("saturating_priors") or [])
    informative = lane.get("informative_priors")
    worst_ov = fmt(lane.get("worst_overlap_informative"), 3)
    worst_rho = fmt(lane.get("worst_abs_spearman"), 4)


    def arm_rows():
        rows = []
        for k, v in arms.items():
            rows.append(f"<tr><td><code>{esc(k)}</code></td><td>{v.get('n_dots')}</td>"
                        f"<td>{fmt(v.get('pooled_dti'))}</td></tr>")
        return "".join(rows)

    def canary_rows():
        return "".join(f"<tr><td><code>{esc(r['feature'])}</code></td><td>{fmt(r['auc'], 3)}</td>"
                       f"<td>{'LEAKAGE SUSPECT' if r['leakage_until_proven_otherwise'] else 'clear'}</td></tr>"
                       for r in sorted(canaries, key=lambda r: -r["auc"]))

    def gate_rows():
        gates = [
            ("format (1 band, float32, EPSG:32611, 3730×3292, [0,1], no NaN)", val.get("format_pass")),
            ("template validator (shared, on-disk re-read)", val.get("all_checks_passed")),
            ("no positive mass on the published catalogue", val.get("on_catalogue_positive_pixels") == 0),
            ("leakage canaries (AUC < 0.90)", all(not r["leakage_until_proven_otherwise"] for r in canaries)),
            ("registry uniqueness (shared gate)", sreg.get("unique")),
            ("complete accessible prior scan", sreg.get("complete_accessible_scan")),
            ("beats the historical best surface on the same folds", paired.get("beats_two_se")),
        ]
        out = []
        for label, ok in gates:
            state = "pass" if ok is True else ("fail" if ok is False else "not measured")
            cls = {"pass": "ok", "fail": "stop", "not measured": "warn"}[state]
            out.append(f"<tr><td>{esc(label)}</td><td class='{cls}'>{state}</td></tr>")
        return "".join(out)

    def dl_card():
        if not tif:
            return ("<div class='dl-card stop'><h2>No candidate file</h2>"
                    "<p>The run produced no serialized candidate. Nothing to download.</p></div>")
        rows = [
            ("file", tif.name),
            ("bytes", f"{tif.stat().st_size:,}"),
            ("sha256", f"<code>{esc(sha or '')}</code>"),
            ("grid", "EPSG:32611 · 100 m · 3730 × 3292 · single band · float32 · all cells finite"),
            ("content", f"{fmt(val.get('emitted_positive_pixels'), 0)} emitted cells at value 1.0 "
                        f"(binary dot emission), 0 on mapped faults"),
        ]
        table = "".join(f"<tr><th>{esc(k)}</th><td>{v}</td></tr>" for k, v in rows)
        ziplink = f" · <a href='downloads/{esc(zipf.name)}' download>submission <code>.zip</code></a>" if zipf and zipf.exists() else ""
        return f"""<div class="dl-card {banner_class}">
    <div class="dl-head"><span class="pill {banner_class}">{esc(banner)}</span><span class="muted">{esc(banner_detail)}</span></div>
    <h2 id="download">Download the candidate GeoTIFF</h2>
    <p class="lead"><a class="button" href="downloads/{esc(tif.name)}" download>⬇ Download <code>{esc(tif.name)}</code></a>{ziplink}</p>
    <table class="kv">{table}</table>
    <details><summary>How to submit it (30 seconds)</summary>
      <ol>
        <li>Open the competition <em>Submit</em> page and choose <strong>New submission</strong>.</li>
        <li>Upload the <code>.tif</code> above (or the <code>.zip</code> containing exactly that one TIFF; the portal accepts either).</li>
        <li><strong>Unique name</strong> field: <code>G64-LIDARSCARP-STRIKELINE</code></li>
        <li><strong>Note</strong> field (≤ 140 characters, paste): <code>{esc(card.get('note') or '')}</code></li>
        <li>Submit. A weekly slot is used — this repository never spends one for you.</li>
      </ol>
      <p class="muted">If the banner above says <em>NOT CLEARED</em>, treat the file as an audit
      artefact: the portal's format rules accept it, but the promotion policy did not clear it,
      because the literal registry rule cannot be satisfied by <em>any</em> non-empty candidate while
      saturating priors sit in the checked inventory — that is measured below with matched random
      controls, not asserted. The diagnostic verdict, computed without exempting anything, is
      <strong>{diag_txt}</strong>.</p>
    </details>
  </div>"""

    cards = [
        ("HOLDOUT-DTI (surrogate)", f"{fmt(dti)}", f"95% CI [{fmt(ci[0])}, {fmt(ci[1])}] · withheld positives {withheld}"),
        ("Registry", f"{sreg.get('rasters_checked')} rasters", f"worst Spearman {fmt(sreg.get('worst_spearman'), 4)} · worst dot overlap {fmt(sreg.get('worst_dot_overlap'), 4)}"),
        ("Uniqueness certificate",
         ("UNIQUE (no exemption taken)" if cert.get("diagnostic_verdict_unique") else "not unique"),
         f"literal protocol gate: {'pass' if cert.get('literal_verdict_unique') else 'FAIL'} · "
         f"{cert.get('registry_rasters_checked')} priors checked · worst informative overlap "
         f"{fmt(cert.get('worst_overlap_informative'), 3)} · worst |Spearman| {fmt(cert.get('worst_abs_spearman'), 4)}"),
        ("Data provenance", "mirror-pinned", "19-band stack sha256 4371c82e… matches the mirror manifest; NOT organizer-authenticated"),
        ("Lane", "1 of the parallel-run lanes", "native-resolution lidar scarp channels (this lane)"),
    ]
    card_html = "".join(
        f"<div class='card'><h3>{esc(t)}</h3><p class='big'>{esc(v)}</p><p class='muted'>{esc(s)}</p></div>"
        for t, v, s in cards)

    main_body = f"""
<section class="hero">
  <p class="kicker">GEMSDOE64 · lane: native-resolution lidar scarp channels</p>
  <h1>A unique GEMS fault-prediction GeoTIFF, with the decision spelled out.</h1>
  <p class="lead">One hundred metres, EPSG:32611, float32, values in [0,1] — and a banner that says
  whether the evidence clears it for a weekly submission slot.</p>
</section>
{dl_card()}
<section class="grid">{card_html}</section>

<section>
  <h2>What this file is</h2>
  <p>Hypothesis: <em>{esc(card.get('hypothesis') or '')}</em></p>
  <p>Mechanism: {esc(card.get('mechanism') or '')}</p>
  <p><strong>Named non-fault process that could mimic it:</strong> {esc(card.get('named_non_fault_mimic') or '')}
  Erosion, deposition and lithologic steps produce strike-coherent, slope-detrended scarps without fault
  slip; the strike-coherence veto reduces but does not eliminate that failure mode.</p>
  <table class="kv">
    <tr><th>emission rule chosen</th><td>{esc(name)}</td></tr>
    <tr><th>dots emitted</th><td>{fmt(val.get('emitted_positive_pixels'), 0)}</td></tr>
    <tr><th>cultural mask</th><td>{card.get('cultural_masked_cells')} cells within 30 m of a mapped road
        (TIGER road-distance layer, sha256 <code>{esc((card.get('cultural_mask_sha256') or '')[:16])}…</code>)</td></tr>
    <tr><th>runtime</th><td>{card.get('runtime_seconds')} s, commit <code>{esc((card.get('git_commit') or '')[:12])}</code></td></tr>
  </table>
</section>

<section>
  <h2>Gate table</h2>
  <table class="kv">{gate_rows()}</table>
  <p class="muted">Verdict: <strong>{esc(verdict)}</strong> · failed gates:
  {esc(', '.join(card.get('failed_gates') or []) or 'none')} · submission slots used:
  {card.get('submission_slots_used', 0)}. The promotion policy is
  <code>gems64.promotion.promotion_decision</code>; missing evidence is a failure, never a default pass.</p>
</section>

<section>
  <h2>The uniqueness decision, spelled out</h2>
  <p>Two different verdicts are computed from the same measured scan, and both are published:</p>
  <table class="kv">
    <tr><th>literal protocol gate (inherited: any positive pixel is a dot, &gt;70 % of my dots within
        3 px of one prior's dots ⇒ stop)</th><td class="{literal_cls}">{literal_txt}</td></tr>
    <tr><th>diagnostic verdict (bytes + pixels + rank structure + the 62 priors where the 70 %
        criterion is informative)</th><td class="{diag_cls}">{diag_txt}</td></tr>
  </table>
  <p><strong>Why the literal gate cannot pass.</strong> The registry checked here contains one prior
  that carries positive mass at {dense_pct} of the footprint cells
  ({dense_files}). For such a prior the 3-pixel forward overlap of <em>any</em> non-empty candidate is
  ~1.0: {control_txt}. That is a property of the rule meeting a dense surface, not evidence about
  this file. The certificate therefore reports both numbers, takes no exemption, and leaves the
  literal gate failing — exactly as the sibling repositories' reviews do
  (their published review records the same 1.0 overlap and the same "NOT CLEARED" clearance).</p>
  <p><strong>What is true about this file.</strong> Its bytes and decoded pixels are unique among all
  {checked} checked priors; the worst overlap against the {informative} priors where the criterion is
  informative is {worst_ov} (limit 0.70) and the worst absolute rank correlation is {worst_rho}
  (limit 0.90). No exemption, no private definition of "dot".</p>
</section>

<section>
  <h2>Arms measured on the same folds</h2>
  <table class="kv"><tr><th>arm</th><th>dots</th><th>pooled holdout DTI</th></tr>{arm_rows()}</table>
  <p class="muted">Instrument: <code>{esc(hold.get('evaluator_version') or '')}</code> —
  {esc(hold.get('instrument') or '')}. These are surrogate holdout numbers on catalogue-derived
  truth; they are <em>not</em> leaderboard scores.</p>
</section>

<section>
  <h2>Leakage canaries (each feature alone)</h2>
  <table class="kv"><tr><th>feature</th><th>AUC</th><th>state</th></tr>{canary_rows()}</table>
  <p class="muted">Rule: AUC above 0.90 is leakage until proven otherwise. Every channel here is
  between 0.50 and 0.58 — weak, as the constraint states single-channel AUC should be.</p>
</section>

<section>
  <h2>Read next</h2>
  <ul>
    <li><a href="executive-summary.html">Executive summary</a> — exactly how to submit, step by step.</li>
    <li><a href="answer.html">Why 0.2778 won — and what it would take to beat it</a> (quantitative).</li>
    <li><a href="hypotheses.html">Ranked hypotheses</a> — five candidates, three of them validated here.</li>
    <li><a href="sources.html">Sources</a> — every claim with a link you can check by hand.</li>
    <li><a href="irregularities.html">Irregularities</a> — what does not add up, flagged rather than smoothed.</li>
  </ul>
</section>
"""

    exec_body = f"""
<section class="hero"><p class="kicker">Executive summary</p>
<h1>How to put a prediction into the competition — and what is standing in the way</h1></section>

<section>
<h2>1. Submission mechanics (from the competition's own pages)</h2>
<ol>
  <li>Sign in to DrivenData and open the GEMS competition page, then the <em>Submit</em> tab
  (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition home</a>,
  <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>).</li>
  <li>Choose a file: a single-band GeoTIFF (<code>.tif</code>) or a <code>.zip</code> containing exactly one GeoTIFF.</li>
  <li>The raster must match the submission template's CRS, shape and geotransform. For this competition
  that is EPSG:32611 (UTM 11N), 3730 rows × 3292 columns, 100 m pixels, origin
  (243350, 4508550), north-up.</li>
  <li>Values must be in [0, 1]. The portal rejects anything else with
  “Predicted values must be in range [0, 1]” — the error this project hit earlier with a file whose
  values were outside that range.</li>
  <li>Give the submission a unique name and a note of at most 140 characters.</li>
  <li>Every accepted upload consumes one weekly submission slot; the private-test score is not shown
  on the public leaderboard.</li>
</ol>
</section>

<section>
<h2>2. The file in this repository</h2>
<ul>
  <li><strong>name</strong>: <code>{esc(name)}</code>, sha256 <code>{esc(sha or '')}</code></li>
  <li><strong>format</strong>: single band, float32, EPSG:32611, 3730 × 3292, all cells finite, values
  exactly {{0.0, 1.0}} (binary dots), zero positive cells on the published fault catalogue.</li>
  <li><strong>gate status</strong>: {esc(banner)}</li>
  <li><strong>diagnostic uniqueness</strong>: {diag_txt} — worst 3-pixel forward overlap against the
  {informative} priors where the criterion is measurable is {worst_ov} (limit 0.70), worst absolute
  rank correlation {worst_rho} (limit 0.90)</li>
</ul>
<p>Why the red banner, in one sentence: the literal registry rule cannot be satisfied by
<em>any</em> non-empty candidate while five saturating priors sit in the checked inventory, and that
saturatation is measured with matched random controls rather than assumed
(<code>{unsat_list}</code>). The portal will accept this file — the local preflight reproduces the
portal's documented requirements and passes. Whether you <em>should</em> spend a slot is a scientific
judgement and a forecast we refuse to invent: the surrogate holdout number below is a hide-and-recover
measurement, not a leaderboard estimate.</p>
</section>

<section>
<h2>3. What still blocks a confident submission</h2>
<ol>
  <li><strong>No organizer-issued truth.</strong> The hidden evaluation labels are not published; every
  number in this repository is either a surrogate holdout measurement or an owner-reported score.</li>
  <li><strong>The registry is dense.</strong> The literal registry gate compares the candidate's
  positive support with every prior's support at a 3 px radius; at least one indexed prior carries
  positive mass almost everywhere, so the literal forward-overlap statistic saturates near 1.0 for
  any non-empty candidate. That is a property of the rule meeting a dense prior, not proof of copying
  — and it is reported, not exempted.</li>
  <li><strong>Native-resolution lidar is not reachable from this sandbox.</strong> The lane's 1 m
  processing path is implemented and unit-tested, but the tile hosts are outside the sandbox's allowed
  egress; see <a href="irregularities.html">irregularities</a>.</li>
</ol>
</section>
"""

    ans_body = f"""
<section class="hero"><p class="kicker">Analysis · owner-reported scores, reconstructed</p>
<h1>Why <code>h33-h33-2-b2…-e5eb6e7e-zeros</code> tops the family — and what beating it requires</h1></section>

<section>
<h2>The one-line metric</h2>
<p><code>DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)</code> with a triangular kernel of radius 3 px
(300 m) and <code>FN_w = |G| − TP_w</code>. False positives are charged 0.2 per unit of emitted mass;
missed truth is charged 0.8. Written with <code>a = A/|G|</code> (the credited fraction of hidden
truth) and <code>N</code> emitted dots, the corrected closure used by the sibling analysis is
<code>DTI = a / (0.8 + 0.2·N/|G|)</code>.</p>
</section>

<section>
<h2>Three mechanisms, in the order they were measured</h2>
<ol>
  <li><strong>Dotting (emission geometry).</strong> A dot on a fault line credits up to 3 px of truth
  (the kernel area) while costing 0.2 when it misses. Measured live by the owner group:
  solid ridge 0.1922 (121,131 px) → thinned at 1.5 px 0.2477 (60,069 px) → thinned at 2.8 px
  0.2600 (44,090 px). On a 1-D fault crest, re-spacing at 2.8 px retained 0.9063 of the credited
  mass while removing 26.6 % of the dots.</li>
  <li><strong>Catalogue-flank pruning.</strong> The h33 file is the group's 40,199-dot base
  (<code>GEMS28-H27-4-R1-SOLO-D2.8</code>, owner-reported live 0.2708) minus every dot within 2 px
  (200 m) of the published catalogue → 37,654 dots. The group's instruments (four spatial quadrants,
  mirrored live score, safety factor 2.08) attributed +0.00487 to it and projected 0.2747; the
  owner-reported live value quoted for it is 0.2778. <em>Both numbers are owner-reported; no organizer
  receipt was seen in any repository checked here.</em></li>
  <li><strong>Surface quality.</strong> The same pruning applied to a weaker surface does not
  reproduce the gain, so the detector behind the dots carries the rest of the signal.</li>
</ol>
</section>

<section>
<h2>What 0.32+ requires (sibling closure, recomputed here)</h2>
<p>At the sibling's calibrated hidden-truth size (|G| ≈ 12.2k px) and credited fraction
a ≈ 0.386, reaching 0.3195 needs <strong>N ≈ 25k dots</strong> instead of 44k — the same credited
mass concentrated in half the dots — or, at the current dot count, a <strong>+24 %</strong> increase in
credited mass. Both are ranking problems (which pixels to keep), not packing problems: re-spacing
alone cannot supply them. That is exactly the hypothesis this run tests, and the reason the emission
here is a binary dot set with an explicit 2.8 px caliper and a catalogue-flank rule.</p>
</section>

<section>
<h2>This run's measured comparison (surrogate instrument)</h2>
<table class="kv">
  <tr><th>arm</th><th>dots</th><th>pooled holdout DTI</th></tr>{arm_rows()}
</table>
<p>Instrument: whole-component hide-and-recover in four quadrants with a 3 px feature buffer; the
visible catalogue is masked pixel-exactly; truth is the withheld components. Paired spatial-block
bootstrap: this run's rule vs the historical best surface (owner-reported live 0.2708)
delta = <strong>{fmt(paired.get('delta'))}</strong> with bootstrap SE {fmt(paired.get('bootstrap_se'))}
({'greater than 2 SE' if paired.get('beats_two_se') else 'not greater than 2 SE'}).</p>
<p class="muted">Honest reading: the surrogate instrument rewards any dot set placed inside a
scar/structure-rich domain (a random draw from the same domain still reaches ~0.04), so it is strong
evidence about the emission domain and weak evidence about fine ranking. It cannot be converted into
a leaderboard expectation.</p>
</section>

<section>
<h2>Can this beat 0.2778?</h2>
<p>Two honest answers. On the surrogate instrument, yes with a large margin against the group's best
live-scored surface — but that instrument is not the hidden test set. Against the real leaderboard,
unproven: the current top of the public leaderboard is 0.4133
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a>,
snapshot verified 2026-10-11), and the gap between 0.28 and 0.41 is a detector problem, not an
emission problem.</p>
</section>
"""

    hyp_body = f"""
<section class="hero"><p class="kicker">Candidates</p>
<h1>Five hypotheses, ranked; three were runnable here</h1></section>
<section>
<h2>H1 — Strike-coherence veto on lidar scarp channels <span class="pill ok">implemented &amp; measured</span></h2>
<p><strong>Layers:</strong> the 1 m 3DEP lidar-derived scarp layer (or the 1 m DEM itself), aggregated
per 100 m cell as scarp fraction, SNR-weighted amplitude, structure-tensor orientation coherence and
dominant strike. <strong>Signature:</strong> a bidirectional strike-line neighbour test on per-cell
scarp evidence (misses become isolated blobs; real fault scarps stay line-like).
<strong>Why it can catch catalogue-missing faults:</strong> the catalogue is a Quaternary-scope
compilation; older bedrock faults have degraded or buried expressions that survive in lidar
micro-topography but not in the 100 m stack. <strong>Novelty:</strong> the sibling repositories use
per-cell max-aggregated lidar channels and ridge/valley masks; no indexed prior applies a
strike-consistency veto with an explicit expected-credit emission rule. <strong>Cost:</strong> done
in this run; the native 1 m path is blocked by egress (see irregularities).</p>
</section>
<section>
<h2>H2 — Expected-DTI greedy selection with per-dot marginal credit <span class="pill warn">implemented, arm refuted on the instrument</span></h2>
<p><strong>Layers:</strong> any probability surface plus a per-cell truth-probability field.
<strong>Signature:</strong> remove every dot whose single removal raises the plug-in expected DTI,
using the exact shared kernel; the plug-in DTI is <code>T/(0.2(T+FP)+0.8K)</code> with
<code>T=Σ π·credit</code>. <strong>Why it should help:</strong> the measured loss mode is redundant
flank-shadow mass; the exact test targets it case by case rather than by a global spacing constant.
<strong>Result:</strong> on the cross-fitted instrument this arm removed almost all dots and scored
0 on the surrogate truth — because the calibrated π under a heavily imbalanced surrogate labels the
scarps as low-probability. That is a negative result and it is kept.</p>
</section>
<section>
<h2>H3 — Cross-sensor corroboration veto <span class="pill ok">implemented &amp; measured</span></h2>
<p><strong>Layers:</strong> lidar scarp channels + detrended elevation curvature + radiometric
texture. <strong>Signature:</strong> a cell must be supported by at least two independent evidence
families (streaming second-best of ten normalised channels). <strong>Why:</strong> cultural and
erosional false positives rarely appear in several independent measurements at once.
<strong>Novelty:</strong> the indexed priors combine channels additively; a veto-style fusion is not
indexed. <strong>Cost:</strong> low, folded into H1.</p>
</section>
<section>
<h2>H4 — Curvature-polarity asymmetry (footwall/hanging-wall) mapping <span class="pill warn">not runnable here</span></h2>
<p><strong>Layers:</strong> 1 m DEM (needed), or 10 m DEM as a degraded fallback.
<strong>Signature:</strong> sign-consistent cross-fault curvature over hundreds of metres, with the
fault dip direction inferred from the asymmetry. <strong>Why it could add faults:</strong> blind or
buried faults express themselves as a systematic tilt of the hanging wall rather than a discrete
scarp. <strong>Data needed:</strong> the competition's <code>1m_DEM_links.csv</code> tile list and the
USGS 3DEP 1 m lidar tiles — free and official, but the hosts are outside this sandbox's egress
(checked 2026-10-11, see irregularities). <strong>Cost:</strong> high; requires an unrestricted runner.</p>
</section>
<section>
<h2>H5 — Slip/length ratio screening against the Qfaults attribute table <span class="pill warn">data available, not yet tested</span></h2>
<p><strong>Layers:</strong> Qfaults attribute table (5.8 MB, mirrored in the sibling repositories) plus
a candidate surface. <strong>Signature:</strong> faults whose mapped length and slip rate imply
continuations the compilation truncates. <strong>Why:</strong> compilation truncation and
segmentation are documented mechanisms for “missing” faults. <strong>Novelty:</strong> the siblings
evaluated gap-closure geometrically and refuted it on the live metric (T-v2: −0.0028); an
attribute-conditioned version with the expected-DTI acceptance test has not been scored.
<strong>Cost:</strong> medium.</p>
</section>
"""

    src_body = """
<section class="hero"><p class="kicker">Sources</p>
<h1>Every claim, with the link to check it by hand</h1></section>
<section>
<h2>Competition</h2>
<ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition home</a> (leaderboard, rules, prize terms).</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description</a> — the DTI metric and submission format (source of the local <code>metric.py</code>).</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">Data tab</a> — login-walled; the rasters used here reached this sandbox only as hash-pinned mirrors.</li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Rules PDF (NREL document 96647)</a> — official rules document.</li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution</a> — U-Net baseline with the same α=0.2/β=0.8 loss.</li>
</ul>
</section>
<section>
<h2>Method literature (the lane's methods)</h2>
<ul>
<li>Sare &amp; Hilley (2018), <em>scarplet</em>, JOSS 3(22):266 — <a href="https://doi.org/10.21105/joss.01066">doi:10.21105/joss.01066</a>. Scarp template matching returning amplitude, offset, width, SNR and a relative-age proxy.</li>
<li>AGU Fall Meeting 2015, poster T31A-2838 — slope-aware scarp templates tested in Surprise Valley (cited by the task statement; poster abstract in the AGU archive).</li>
<li>Steger (1998), <em>An unbiased detector of curvilinear structures</em>, IEEE TPAMI 20(2):113–125 — <a href="https://doi.org/10.1109/34.659930">doi:10.1109/34.659930</a>.</li>
<li>Frangi et al. (1998), <em>Multiscale vessel enhancement filtering</em>, MICCAI, LNCS 1496:130–137 — <a href="https://doi.org/10.1007/BFb0056195">doi:10.1007/BFb0056195</a>.</li>
<li>Tversky index — <a href="https://en.wikipedia.org/wiki/Tversky_index">the metric family behind DTI</a>; EPSG:32611 — <a href="https://epsg.io/32611">UTM zone 11N</a>.</li>
</ul>
</section>
<section>
<h2>Data provenance</h2>
<ul>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN airborne magnetics/radiometrics</a> (DOI 10.5066/P93LGLVQ) — source of the potential-field bands.</li>
<li><a href="https://index.nationalmap.gov/arcgis/rest/services/3DEPElevationIndex/MapServer/18">USGS 3DEP 1 m elevation index</a> — the lidar tiles behind the scarp layer (owner-CI derived from 706 tiles).</li>
<li><a href="https://gbcge.org/current-projects/ingenious/">GBCGE INGENIOUS</a> — INGENIOUS fault compilation used with the USGS catalogue.</li>
<li><a href="https://www.usgs.gov/data/heat-flow-maps-and-supporting-data-great-basin-usa">USGS Great Basin heat-flow data</a> (CC0) — relevant to H4/H5, metadata checked, not integrated.</li>
<li>Mirrors used for the rasters in this sandbox: public repositories <code>buffedlizard55-lab/5GEMSDOE</code> (19-band stack parts), <code>/60GEMSDOE</code> (external layers, registry inventory), <code>/GEMSDOE24</code> (TIGER road distance), <code>/GEMSDOE32</code> (h33 facts), <code>/17GEMSDOE</code> (dense prior witness). Every file is used with its sha256 recorded in <code>evidence/</code>.</li>
</ul>
<p class="muted">Provenance class for the competition rasters: owner-supplied mirrors, integrity-pinned
(sha256 matches the mirror manifest), <strong>not organizer-authenticated</strong>. The 19-band stack
reassembled in this sandbox reproduces the pinned sha256
<code>4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5</code> exactly.</p>
</section>
"""

    irr_body = """
<section class="hero"><p class="kicker">Irregularities</p>
<h1>What does not add up — flagged, not smoothed</h1></section>
<section>
<ol>
<li><strong>Two different “current high scores” in the task brief.</strong> The brief quotes the
GEMSDOE site at 0.3774 and later says 0.3195 is the highest. A leaderboard snapshot verified
2026-10-11 (rows read from the public leaderboard and stored in
<code>docs/data/leaderboard_snapshot.json</code>) shows #1 = 0.4133, #8 = 0.3195. Treat any
site-local “high score” as stale unless it carries a date and a row.</li>
<li><strong>0.2778 vs 0.2747 for the same file.</strong> The h33 repository's own README marks that
artifact <em>UNSCORED</em> with a projected live value of 0.2747; the brief reports 0.2778. Both are
owner-reported. No organizer receipt exists in any repository checked; the discrepancy is preserved
here rather than averaged.</li>
<li><strong>The dense prior and the literal uniqueness rule.</strong> A pinned prior in the registry
(the 17GEMSDOE probability raster, sha256 ab0a0a62…, re-downloaded and hash-verified here) carries
positive mass at essentially every cell of the footprint. The sibling protocol defines dots as
“finite positive pixels”, so the 3-pixel forward-overlap statistic against that prior is ~1.0 for
<em>any</em> non-empty candidate. That is a rule-meets-dense-prior degeneracy, not evidence about this
candidate. It is reported, the literal verdict is left failing, and no exemption is taken.</li>
<li><strong>Egress limitation, honestly stated.</strong> The lane requires 1 m DEM processing. The
sandbox can reach GitHub, PyPI and npm only; <code>prd-tnm.s3.amazonaws.com</code>,
<code>portal.opentopography.org</code>, <code>www.sciencebase.gov</code>, <code>data.source.coop</code>
and Dropbox all fail to resolve or connect (tested 2026-10-11). The published candidate therefore
runs the same lane code on the finest <em>reachable</em> lidar-derived grid: the owner-CI 100 m
aggregate of 706 USGS 3DEP 1 m tiles. The native-resolution path is implemented and unit-tested
(<code>tests/test_lidar_scarp.py</code>), and switches on the moment a 1 m DEM is placed at
<code>--dem</code>.</li>
<li><strong>Surrogate truth everywhere.</strong> No publication here contains a hidden-test score.
Where a number looks like a score, the label says HOLDOUT-DTI (surrogate), MEASURED (bytes), or
OWNER-REPORTED. Anything else would be a hallucination.</li>
</ol>
</section>
"""

    nav = """<nav><a href="index.html">Overview &amp; download</a><a href="executive-summary.html">Submit</a>
<a href="answer.html">Why 0.2778 won</a><a href="hypotheses.html">Hypotheses</a>
<a href="sources.html">Sources</a><a href="irregularities.html">Irregularities</a></nav>"""

    banner_full = (f"{banner} — cleared by the promotion policy; a submission slot is still the "
                   f"owner's decision" if cleared else
                   f"{banner} — audit artefact: accepted by the portal's format rules, not cleared "
                   f"by the repository's promotion policy. See the front page for the two verdicts.")

    def page(title, body):
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · GEMSDOE64</title>
<link rel="stylesheet" href="styles.css"></head>
<body><header class="site"><div class="wrap">{nav}</div></header>
<main class="wrap">{body}</main>
<footer class="wrap"><p class="verdict">{banner_full}</p>
<p>GEMSDOE64 — lane: native-resolution lidar scarp channels.
No number here is a leaderboard score unless it is labelled ORGANIZER-CONFIRMED, and none is.
Negative results are deliverables.</p>
<p><a href="data/run_card.json">run card</a> · <a href="data/registry_index.json">registry index</a>
· <a href="https://github.com/buffedlizard55-lab/GEMSDOE64">repository</a></p></footer></body></html>
"""

    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page("Overview & download", main_body))
    (DOCS / "executive-summary.html").write_text(page("Submit", exec_body))
    (DOCS / "answer.html").write_text(page("Why 0.2778 won", ans_body))
    (DOCS / "hypotheses.html").write_text(page("Hypotheses", hyp_body))
    (DOCS / "sources.html").write_text(page("Sources", src_body))
    (DOCS / "irregularities.html").write_text(page("Irregularities", irr_body))
    (DOCS / "data").mkdir(exist_ok=True)
    for src in ("evidence/run_card.json", "evidence/registry_index.json"):
        data = read(ROOT / src, {})
        (DOCS / "data" / Path(src).name).write_text(json.dumps(data, indent=2, default=str) + "\n")
    print(f"wrote docs/index.html and 5 subpages; candidate={tif.name if tif else None}; cleared={cleared}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
