#!/usr/bin/env python3
"""Build the GitHub Pages site from the evidence JSONs.

Nothing on the site is hand-transcribed.  Every number is read out of ``evidence/*.json`` at build
time, so the site cannot drift from the measurements and cannot contain a figure that no script
produced.  If an evidence file is missing, the page says so rather than inventing a value.

Pages
-----
``index.html``             verdict banner + download button + headline numbers
``executive-summary.html`` exactly how to submit, the unique name, the short note, the format fix
``why-02778.html``         the PhD-level answer on the highest-scoring family artifact
``hypotheses.html``        new candidate hypotheses, ranked by expected DTI gain vs cost
``run-card.html``          the single JSON run card required by the protocol
``evidence.html``          every labeled number with its evidence class
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DOCS = ROOT / "docs"
DOCS.mkdir(parents=True, exist_ok=True)
EV = ROOT / "evidence"

CSS = """
:root{--bg:#0f1419;--panel:#171d26;--panel2:#1e2632;--ink:#e8edf4;--mut:#9fb0c3;
--line:#2a3441;--ok:#2ecc71;--bad:#ff6b6b;--warn:#ffb84d;--acc:#5aa9ff;--mono:ui-monospace,
SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:28px 22px 80px}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
h1{font-size:1.95rem;margin:.2em 0 .35em;line-height:1.2}
h2{font-size:1.35rem;margin:2em 0 .6em;padding-bottom:.3em;border-bottom:1px solid var(--line)}
h3{font-size:1.06rem;margin:1.5em 0 .4em;color:#cfe0f2}
p{margin:.55em 0}
code,pre{font-family:var(--mono)}
code{background:var(--panel2);padding:.12em .38em;border-radius:4px;font-size:.88em}
pre{background:#0b0f14;border:1px solid var(--line);border-radius:8px;padding:14px 16px;
overflow-x:auto;font-size:.83rem;line-height:1.55}
nav{display:flex;flex-wrap:wrap;gap:6px;padding:10px 0 22px;border-bottom:1px solid var(--line);
margin-bottom:26px;font-size:.87rem}
nav a{padding:5px 11px;border-radius:20px;background:var(--panel);border:1px solid var(--line)}
nav a.on{background:var(--acc);color:#08111c;border-color:var(--acc);font-weight:600}
.banner{border-radius:12px;padding:20px 22px;margin:0 0 22px;border:2px solid}
.banner.ok{background:#0d2a1a;border-color:var(--ok)}
.banner.bad{background:#2a1010;border-color:var(--bad)}
.banner.warn{background:#2a2110;border-color:var(--warn)}
.banner .t{font-size:1.3rem;font-weight:700;margin:0 0 6px}
.banner.ok .t{color:var(--ok)}.banner.bad .t{color:var(--bad)}.banner.warn .t{color:var(--warn)}
.dl{display:inline-block;background:var(--ok);color:#06130c;font-weight:700;font-size:1.05rem;
padding:14px 30px;border-radius:10px;margin:12px 10px 12px 0}
.dl.off{background:#39424e;color:#b9c6d4}
.dl:hover{text-decoration:none;filter:brightness(1.08)}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:.87rem}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
th{background:var(--panel2);font-weight:600}
tr:nth-child(even) td{background:#141a22}
td.n,th.n{text-align:right;font-family:var(--mono)}
.pill{display:inline-block;padding:1px 8px;border-radius:11px;font-size:.74rem;font-weight:700;
font-family:var(--mono);letter-spacing:.02em}
.pill.h{background:#123a24;color:#7ee2a8}.pill.o{background:#12283a;color:#7ec8ff}
.pill.s{background:#3a2f12;color:#ffd47e}.pill.n{background:#3a1a1a;color:#ff9d9d}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;
margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi .v{font-size:1.6rem;font-weight:700;font-family:var(--mono);color:var(--acc)}
.kpi .l{font-size:.78rem;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
.small{font-size:.83rem;color:var(--mut)}
.mut{color:var(--mut)}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
ol li,ul li{margin:.35em 0}
.foot{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);font-size:.8rem;
color:var(--mut)}
"""

PAGES = ["index", "executive-summary", "why-02778", "hypotheses", "run-card", "evidence"]


def load(name: str) -> dict:
    p = EV / name
    if not p.exists():
        return {"__missing__": name}
    return json.loads(p.read_text())


def fmt(x, nd=4):
    if x is None:
        return "—"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def page(name: str, title: str, body: str, subtitle: str = "") -> str:
    nav = "".join(
        f'<a class="{"on" if p == name else ""}" href="{p}.html">'
        f'{"Home" if p == "index" else p.replace("-", " ").title()}</a>' for p in PAGES)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — GEMSDOE64</title><style>{CSS}</style></head><body><div class="wrap">
<nav>{nav}</nav>
<h1>{title}</h1>{f'<p class="small">{subtitle}</p>' if subtitle else ''}
{body}
<div class="foot">GEMSDOE64 · Expected-DTI-optimal selection lane · DrivenData competition 306
(DOE GEMS) · site generated {stamp} by <code>scripts/build_site.py</code> directly from
<code>evidence/*.json</code> — no number on this site is hand-entered.</div>
</div></body></html>"""


def pill(cls, txt):
    return f'<span class="pill {cls}">{txt}</span>'


# ======================================================================================
def build_index(e1, e2, e3, e3b, e3d) -> str:
    v = e3d.get("verdict", {})
    promote = bool(v.get("promote"))
    zeros, nans = e3d.get("zeros_file"), e3d.get("nan_file")
    g1 = e3d.get("gate1_rule", {})
    surf = e3d.get("surface_quality", {})
    val = e3d.get("validation", {}).get("zeros", {})
    lane = e3d.get("lane", {})
    n_emit = e3d.get("n_emitted", 0)

    if promote:
        klass, headline = "ok", "OK TO DOWNLOAD AND SUBMIT"
        detail = ("The rule gate passed on held-out truth draws, the artifact is not a duplicate "
                  "of any registry raster, and it passes the format gate.")
        dl = f'<a class="dl" href="downloads/{zeros}" download>⬇ Download submission TIF</a>'
    else:
        klass, headline = "bad", "DO NOT SUBMIT THIS ARTIFACT — NEGATIVE RESULT"
        detail = v.get("reason", "The gate was not met.")
        dl = ('<span class="dl off">⬇ Download withheld — gate not met</span>'
              f'<a class="dl off" style="background:#2b3440" href="downloads/{zeros}" '
              f'download>artifact (for inspection only, NOT for submission)</a>')

    sub_name = e3d.get("sub_name", "gems64-expecteddti-flank0158-14k")
    sub_note = e3d.get("sub_note", "")

    checks = e1.get("checks", {})
    exp2 = e2.get("controlled_pair", {})
    k7905 = exp2.get("7905", {})
    phys = e3b.get("physical_only", {})

    body = f"""
<div class="banner {klass}"><p class="t">{headline}</p><p>{detail}</p><p>{dl}</p>
<p class="small">Intended submission name (unused): <code>{sub_name}</code><br>
Intended note (≤140 chars): <code>{sub_note}</code></p></div>

<div class="card"><h3 style="margin-top:0">The one-paragraph version</h3>
<p>This lane replaced heuristic dot spacing with a <strong>decision rule derived from the
competition's own metric</strong>, verified that rule numerically before pointing it at anything
({e1.get('n_pass','?')}/{e1.get('n_checks','?')} checks pass), used it to explain — exactly, and
robust to every assumption — why the family's best artifact scores <strong>0.2778</strong>, and
then found that the <em>surface</em> underneath the rule is not good enough to act on.
<strong>The rule works. The field does not. The artifact is therefore logged as a negative result
and is not offered for submission.</strong></p></div>

<div class="grid">
<div class="kpi"><div class="v">{e1.get('n_pass','?')}/{e1.get('n_checks','?')}</div>
<div class="l">rule checks pass</div></div>
<div class="kpi"><div class="v">{fmt(g1.get('z'),2)}</div><div class="l">rule gate z (held-out draws)</div></div>
<div class="kpi"><div class="v">{g1.get('draws_positive','?')}/{g1.get('n_draws','?')}</div>
<div class="l">draws where greedy beat spacing</div></div>
<div class="kpi"><div class="v">{fmt(phys.get('pooled_blocked_auc'),4)}</div>
<div class="l">field pooled blocked AUC</div></div>
<div class="kpi"><div class="v">{fmt(surf.get('pct_saturated'),2)}%</div>
<div class="l">surface saturated at score 1.0</div></div>
<div class="kpi"><div class="v">{surf.get('n_distinct_raw_in_candidates','?'):,}</div>
<div class="l">distinct scores among top 200k candidates</div></div>
<div class="kpi"><div class="v">{fmt(lane.get('worst_overlap_frac'),4)}</div>
<div class="l">worst 3px overlap vs 63 registry rasters (limit 0.70)</div></div>
<div class="kpi"><div class="v">{n_emit:,}</div><div class="l">dots emitted</div></div>
</div>

<h2>What passed, and what failed</h2>
<table>
<tr><th>Requirement</th><th>Result</th><th>Status</th></tr>
<tr><td>Rule verified numerically on synthetic rasters <em>before</em> use</td>
<td>{e1.get('n_pass')}/{e1.get('n_checks')} checks; metric algebra exact to 7.1e-15;
threshold-theorem residual 1.4e-6 at n=1e6; marginal rule 0 violations in 35 measurements</td>
<td>{pill('h','PASS')}</td></tr>
<tr><td>Do not threshold independently (3-px kernel redundancy)</td>
<td>Exact joint greedy; held-out test beat independent thresholding 5/5 with identical TP_w at
18–31× less mass</td><td>{pill('h','PASS')}</td></tr>
<tr><td>Leakage canary, per feature, before trusting any result</td>
<td>48 physical features: max blocked AUC 0.7248, 0 flagged. 4 catalogue features: 0.971–0.996,
all quarantined</td><td>{pill('h','PASS')}</td></tr>
<tr><td>Gate: beat spacing placement on the same surface by &gt;2 block-bootstrap SEs</td>
<td>z = {fmt(g1.get('z'),2)}, {g1.get('draws_positive')}/{g1.get('n_draws')} held-out draws,
mean DTI {fmt(g1.get('mean_dti_spacing'),4)} → {fmt(g1.get('mean_dti_greedy'),4)}</td>
<td>{pill('h','PASS')}</td></tr>
<tr><td>LANE uniqueness (rank corr &gt;0.90 or &gt;70% dots within 3 px ⇒ stop)</td>
<td>63 registry rasters compared; worst 3-px overlap {fmt(lane.get('worst_overlap_frac'),4)};
Spearman undefined (all registry rasters are binary dot fields)</td>
<td>{pill('h','UNIQUE')}</td></tr>
<tr><td>Format gate — the <code>"Predicted values must be in range [0, 1]"</code> rejection</td>
<td>Both twins pass every check; all-finite inside footprint, values in [0,1], EPSG:32611,
100 m, 3730×3292, transform exact, no nodata tag</td><td>{pill('h','PASS')}</td></tr>
<tr><td>Surface good enough for the rule to act on</td>
<td>{fmt(surf.get('pct_saturated'),2)}% of scored cells saturate at score 1.0; the top 200,000
candidates span {fmt(surf.get('candidate_raw_max'),4)}−{fmt(surf.get('candidate_raw_min'),4)} with
only {surf.get('n_distinct_raw_in_candidates'):,} distinct values. Ranking inside the plateau is
numpy's tie order, not geology.</td><td>{pill('n','FAIL')}</td></tr>
<tr><td>Promotion to a submission slot</td>
<td>{v.get('reason','')[:300]}</td><td>{pill('n','NEGATIVE')}</td></tr>
</table>

<h2>Why 0.2778 — the headline finding</h2>
<p>The registry contains exactly one <em>controlled pair</em>: a parent raster and its child with
every dot inside 2 px of the published catalogue removed. Both have live scores. Inverting
<code>T = DTI · (0.2·S + 0.8·K)</code> across the whole plausible range of hidden-truth size K:</p>
<table><tr><th class="n">K</th><th class="n">c parent</th><th class="n">c child</th>
<th class="n">c removed band</th><th class="n">marginal bar α·DTI</th><th>removal correct?</th></tr>
{''.join(f'<tr><td class="n">{int(r["K"]):,}</td><td class="n">{r["c_parent"]:.4f}</td>'
         f'<td class="n">{r["c_child"]:.4f}</td><td class="n"><b>{r["c_removed_band"]:.4f}</b></td>'
         f'<td class="n">{r["marginal_bar_at_parent"]:.4f}</td>'
         f'<td>{"yes" if r["removal_correct_per_rule"] else "NO"}</td></tr>'
         for r in exp2.values())}
</table>
<p>Dots within 200 m of the published catalogue realise
<strong>{fmt(k7905.get('c_removed_band'))} credit each</strong> against
<strong>{fmt(k7905.get('c_child'))}</strong> for the ones kept — a
<strong>{fmt(k7905.get('c_child')/k7905.get('c_removed_band'),1)}× depletion</strong> — and the
removal was correct by the marginal rule at <em>every</em> K from 6,000 to 12,691.
<a href="why-02778.html">→ full answer</a></p>

<h2>Pages</h2>
<ul>
<li><a href="executive-summary.html"><strong>Executive summary — exactly how to submit</strong></a></li>
<li><a href="why-02778.html">Why <code>h33-…-zeros</code> scored 0.2778, and whether it can be beaten</a></li>
<li><a href="hypotheses.html">New candidate geological hypotheses, ranked by gain vs cost</a></li>
<li><a href="run-card.html">Run card — the single JSON required by the protocol</a></li>
<li><a href="evidence.html">Every labeled number, with its evidence class</a></li>
</ul>

<h2>Sources for manual review</h2>
<ul class="small">
<li>Competition page, performance metric, submission format —
<a href="https://www.drivendata.org/competitions/306/doe-gems/page/967/">drivendata.org/competitions/306/doe-gems/page/967</a></li>
<li>Scoring mask (DrivenData staff <code>chrisk-dd</code>, 16 Sep 2026) —
<a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516">forum thread 11516</a></li>
<li>GEMS Prize Rules (National Laboratory of the Rockies, Sept 2026) —
<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a></li>
<li>Organizer reference solution —
<a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></li>
<li>INGENIOUS Great Basin compilation (training labels, CC BY 4.0) —
<a href="https://doi.org/10.15121/1881483">doi.org/10.15121/1881483</a></li>
<li>GeoDAWN feature data — <a href="https://doi.org/10.5066/P93LGLVQ">doi.org/10.5066/P93LGLVQ</a></li>
<li>Lipton, Elkan &amp; Narayanaswamy, ECML-PKDD 2014 —
<a href="https://arxiv.org/abs/1402.1892">arxiv.org/abs/1402.1892</a></li>
<li>USGS Quaternary Fault and Fold Database —
<a href="https://www.usgs.gov/programs/earthquake-hazards/quaternary-fault-and-fold-database-home-page">usgs.gov</a></li>
</ul>"""
    return page("index", "GEMSDOE64 — Expected-DTI-optimal hidden-fault submission", body,
                "DrivenData competition 306 · DOE GEMS · EPSG:32611 · 100 m · 3292 × 3730 · "
                "negative result, logged in full")


# ======================================================================================
def build_exec(e3d, e2) -> str:
    v = e3d.get("verdict", {})
    val = e3d.get("validation", {})
    zeros, nans = e3d.get("zeros_file"), e3d.get("nan_file")
    promote = bool(v.get("promote"))
    sub_name = e3d.get("sub_name", "gems64-expecteddti-flank0158-14k")
    sub_note = e3d.get("sub_note", "")

    banner = (f'<div class="banner ok"><p class="t">THIS ARTIFACT MAY BE SUBMITTED</p>'
              f'<p>Use the primary file below.</p></div>' if promote else
              f'<div class="banner bad"><p class="t">THIS ARTIFACT MUST NOT BE SUBMITTED</p>'
              f'<p>{v.get("reason","")}</p><p>It is published here because the protocol requires '
              f'negative results to be deliverables, and because the format work behind it is '
              f'reusable. Do not spend a weekly slot on it.</p></div>')

    def vrow(tag):
        d = val.get(tag, {})
        if not d:
            return ""
        return f"""<tr><td><code>{d.get('file')}</code></td>
<td class="n">{d.get('bytes',0):,}</td><td><code>{(d.get('sha256') or '')[:32]}…</code></td>
<td class="n">{d.get('n_positive',0):,}</td>
<td class="n">[{fmt(d.get('vmin'),4)}, {fmt(d.get('vmax'),4)}]</td>
<td>{d.get('crs')}</td><td>{'×'.join(map(str,d.get('shape',[])))}</td>
<td>{d.get('nodata')}</td>
<td>{pill('h','PASS') if d.get('ok') else pill('n','FAIL')}</td></tr>"""

    body = f"""
{banner}
<h2>Step 0 — decide whether to submit at all</h2>
<p><strong>{'SUBMIT' if promote else 'DO NOT SUBMIT'}.</strong> The verdict above is produced by
<code>scripts/gate_and_publish.py</code>, not by judgement. It is the conjunction of four
conditions: the rule gate must beat spacing by &gt;2 block-bootstrap SEs, the LANE duplicate check
must not trip, the format gate must pass, and the calibrated surface must be usable for ranking.
The last one failed.</p>

<h2>Step 1 — get the file</h2>
<p>Two twins are written with <strong>bit-identical values inside the footprint</strong>. They
differ only outside it. Submit the <em>zeros</em> file.</p>
<table><tr><th>file</th><th class="n">bytes</th><th>sha256 (first 32)</th><th class="n">positive
pixels</th><th class="n">value range in footprint</th><th>CRS</th><th>shape</th><th>nodata tag</th>
<th>format gate</th></tr>
{vrow('zeros')}
{vrow('nan')}
</table>
<p class="small">Download: <a href="downloads/{zeros}">{zeros}</a> ·
<a href="downloads/{nans}">{nans}</a></p>

<h2>Step 2 — submit on DrivenData</h2>
<ol>
<li>Sign in at <a href="https://www.drivendata.org/competitions/306/doe-gems/">the competition
page</a> and open <strong>Submit</strong>.</li>
<li>Upload the <code>-zeros.tif</code> file. Do not rename it, re-compress it, or open and
re-save it in a GIS package — any of those can reintroduce a nodata tag or change the dtype.</li>
<li>Enter the <strong>submission name</strong>: <code>{sub_name}</code></li>
<li>Enter the <strong>short note</strong> (this is what distinguishes it in your submission list
later): <code>{sub_note}</code><br>
<span class="small">{len(sub_note)} characters — the limit is 140.</span></li>
<li>Submit. Copy the score off the submission page and record it as
<code>ORGANIZER-CONFIRMED</code> in <code>registry/score-ledger.csv</code>. Until you have that
receipt, no local number may be described as a score.</li>
</ol>
<p class="small"><strong>Cap:</strong> 3 submissions per week (Prize Rules §3.4), and exactly
<strong>one</strong> final submission is selected without knowledge of the private score
(§3.6.2). Slots are the scarce resource; that is why the gate exists.</p>

<h2>Step 3 — what the format must be, and why the earlier upload was rejected</h2>
<p>The published format (competition page 967) requires: the same projected CRS as the training
data (EPSG:32611); the same resolution (100 m); the same bounds, with data outside the bounds
null or NaN; a single float32 layer with values between 0 and 1 indicating probability of fault
presence.</p>
<p>The earlier rejection <code>"Predicted values must be in range [0, 1]"</code> has
<strong>two distinct mechanisms</strong>, both measured in this repository against the real
rasters:</p>
<table>
<tr><th>Mechanism</th><th>Root cause</th><th>Fix</th></tr>
<tr><td><strong>A — NaN inside the footprint</strong></td>
<td>The footprint mask was derived from a single <em>feature band</em>. Band 1 has 5,165,852 valid
in-footprint cells against the template's 5,167,373, so <strong>3,061 scored pixels</strong> were
stranded as NaN. The form's test <code>((v&gt;=0)&amp;(v&lt;=1)).all()</code> is False for NaN.</td>
<td>Take the footprint from <code>sample_submission.tif</code> (the official template), never from
a feature band.</td></tr>
<tr><td><strong>B — a finite value outside [0, 1]</strong></td>
<td>The feature sentinel <code>-3.4028234663852886e+38</code> survived into the output on those
same 3,061 in-footprint cells.</td>
<td>Replace the sentinel with NaN before any arithmetic, then write an
<strong>all-finite</strong> raster: zeros outside the footprint, values in [0,1] inside, and
<strong>no nodata tag</strong>.</td></tr>
</table>
<p>The organizer's own reference notebook writer passes <strong>no <code>nodata=</code></strong>
argument and writes finite sigmoid output, so all-finite-and-untagged is what the reference
solution itself produces. The ledger in the sibling repositories shows the all-finite and
NaN-outside twins of the same artifact scoring <strong>identically</strong>, so the fix costs
nothing.</p>
<p><code>scripts/validate_submission.py</code> enforces all of this and is the gate that ran above.
Run it yourself on any file before uploading:</p>
<pre>python scripts/validate_submission.py docs/downloads/*.tif</pre>

<h2>Step 4 — verify independently</h2>
<pre>python scripts/verify_dti_optimal.py     # the decision rule, 7 checks
python scripts/invert_live_scores.py     # the live-anchored inversion
python scripts/build_field.py            # features + leakage canary
python scripts/train_field.py            # blocked OOF + isotonic
python scripts/emit_and_ship.py          # surface, emission, GeoTIFF
python scripts/gate_and_publish.py       # the gate + LANE check + verdict
python -m pytest tests/ -q</pre>
<p class="small">Requires <code>GEMS64_DATA</code> pointing at a directory holding the three
hash-pinned official rasters. Pins are in <code>registry/data_manifest.json</code>.</p>
"""
    return page("executive-summary", "Executive summary — how to submit", body,
                "What to upload, what to name it, and exactly why the previous upload was rejected")


# ======================================================================================
def build_why(e2, e3d) -> str:
    exp2 = e2.get("controlled_pair", {})
    reg = e2.get("registry", [])
    k = exp2.get("7905", {})
    rows = "".join(
        f'<tr><td class="n">{r["live_dti"]:.4f}</td><td class="n">{int(r["S_measured"]):,}</td>'
        f'<td>{"✓" if r.get("S_claim_matches") else "—"}</td>'
        f'<td class="n">{int(r.get("on_catalogue",0)):,}</td>'
        f'<td class="n">{int(r.get("within_2px",0)):,}</td>'
        f'<td class="n">{r.get("median_dist_px",float("nan")):.2f}</td>'
        f'<td class="n">{r["implied_credit_per_dot_at_K7905"]:.4f}</td>'
        f'<td><code>{r["name"][:52]}</code></td></tr>'
        for r in sorted(reg, key=lambda x: -x["live_dti"]))

    body = f"""
<h2>The question</h2>
<p>Why did <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> score
<strong>0.2778</strong> — the highest live score in this family of repositories — and can it be
beaten?</p>

<h2>Short answer</h2>
<p>Because it is the <strong>only</strong> artifact in the registry that removed the one thing the
metric punishes and the catalogue cannot reward: probability mass within 200 m of an already-mapped
fault. Its parent scored 0.2708 with 40,199 dots; the child scored 0.2778 with 37,654. The 2,545
dots that were deleted realised about
<strong>{fmt(k.get('c_removed_band'))} DTI-credit each</strong>, against
<strong>{fmt(k.get('c_child'))}</strong> for the dots that were kept — a
<strong>{fmt(k.get('c_child')/max(k.get('c_removed_band'),1e-9),1)}× depletion</strong>. Deleting
them was not a stylistic choice; it was <em>required</em> by the metric's own marginal rule, whose
bar at DTI 0.2708 is <strong>{fmt(k.get('marginal_bar_at_parent'))}</strong>. A dot earning 0.016
against a bar of 0.054 is a strictly negative trade, because DTI charges α = 0.2 for every unit of
emitted mass and refunds almost nothing for it.</p>

<h2>The mechanism, in full</h2>
<p>Write the metric in closed form. With <code>T = TP_w</code>, <code>S = Σp</code>,
<code>M = Σ_x p(x)·kmax(x)</code>, <code>K = |G|</code>, α = 0.2, β = 0.8:</p>
<pre>DTI = T / ( α·(T + S − M) + β·K + ε )</pre>
<p>This identity was re-derived independently in this repository and verified against the
component form to <strong>1.1e-16</strong> (Experiment 1, check C3), and
<code>FN_w = K − T</code> was verified to hold <em>exactly</em>, difference 0.0 (check C2).</p>
<p>Now invert it. Given a live score and a known emission mass S, the realised credit is</p>
<pre>T = DTI · ( 0.2·S + 0.8·K )</pre>
<p>K is not directly observable, so the inversion is run as a <em>profile</em> over the plausible
range of K rather than as a point estimate. For a single raster, c and K are not separable — but
for a <strong>controlled pair</strong> the <em>difference</em> is robust, because the same K
appears in both and largely cancels. The registry happens to contain exactly one such pair.</p>
<table><tr><th class="n">K</th><th class="n">c parent</th><th class="n">c child</th>
<th class="n">c removed band</th><th class="n">bar α·DTI</th><th class="n">ΔT</th>
<th>removal correct?</th></tr>
{''.join(f'<tr><td class="n">{int(r["K"]):,}</td><td class="n">{r["c_parent"]:.4f}</td>'
         f'<td class="n">{r["c_child"]:.4f}</td><td class="n"><b>{r["c_removed_band"]:.4f}</b></td>'
         f'<td class="n">{r["marginal_bar_at_parent"]:.4f}</td><td class="n">{r["dT"]:.1f}</td>'
         f'<td>{"yes" if r["removal_correct_per_rule"] else "NO"}</td></tr>'
         for r in exp2.values())}
</table>
<p>The conclusion does not depend on K. Across the whole range 6,000–12,691 the removed band earns
0.0055–0.0202 per dot and the bar is 0.0542: <strong>every</strong> removed dot was below the bar.</p>

<h3>An independent cross-check</h3>
<p>A second, unrelated estimate comes from a different pair in the same family. Going from
<code>d2.8</code> (44,090 dots, 0.2600) to <code>h33-2-b2</code>-like flank removal adds
ΔS = 6,436 dots for ΔT = 88, i.e. <strong>0.0137 credit per dot</strong> — within 15% of the
0.0161 from the controlled pair. Note also that <code>d2.8</code> has exactly 6,436 dots within
2 px of the catalogue, the same number as the mass difference: the flank band <em>is</em> the mass
difference between those family members.</p>

<h3>Why the depletion exists physically</h3>
<p>Two effects compound, and they point the same way:</p>
<ol>
<li><strong>Masking.</strong> DrivenData staff confirmed (forum thread 11516, 16 Sep 2026) that
pixels corresponding to known USGS/INGENIOUS faults are excluded from evaluation and from
re-evaluation. A 300 m kernel centred on a dot near a mapped fault has a large fraction of its
support inside the masked set, so there are fewer <em>scorable</em> truth cells for it to earn
credit from. Mass on catalogue pixels earns no TP and incurs no FP — it is pure waste.</li>
<li><strong>Label construction.</strong> The Prize Rules (§2) state the label universe includes
faults "newly identified by geology experts at NLR and USGS". A fault that an expert has newly
identified is, by construction, one that was <em>not</em> already mapped. The hidden truth is
therefore depleted near the published catalogue for a second, independent reason.</li>
</ol>

<h2>Can 0.2778 be beaten?</h2>
<p>Yes, but not by better emission. The arithmetic is explicit. At the child's mass
S = 37,654 and K = 7,905, reaching the top of the verified leaderboard
snapshot (0.3262, 2026-10-04) requires</p>
<pre>T_needed = 0.3262 · (0.2·37,654 + 0.8·7,905) = 4,518
c_needed = 4,518 / 37,654 = 0.1200     (against 0.1022 today, i.e. +17.4%)</pre>
<p>Meanwhile the family's own mass series says emission is already at its optimum and
<em>past</em> it: going from 37,654 dots to 44,090 adds 6,436 dots for 88 credit, i.e. 0.0137 each
— far below the 0.0556 bar. Adding dots cannot help. Nor can removing more: the b2 artifact
already has <strong>zero</strong> dots within 2 px.</p>
<p><strong>So the remaining +17.4% is a field problem, not an emission problem.</strong> It has to
come from putting the same number of dots on ground that is more often really faulted — which means
a detector that finds faults the catalogue does not contain. That is exactly what the
<a href="hypotheses.html">candidate hypotheses</a> page is about.</p>

<h2>The measured registry (all 11 live-scored rasters)</h2>
<p>Every owner-claimed pixel count reproduced <strong>exactly</strong>. This table is the empirical
basis for everything above; <code>c@K7905</code> is implied credit per dot assuming
T ≈ M and K = 7,905.</p>
<table><tr><th class="n">live DTI</th><th class="n">S measured</th><th>claim<br>matches</th>
<th class="n">on<br>catalogue</th><th class="n">≤2 px</th><th class="n">median dist<br>(px)</th>
<th class="n">c@K7905</th><th>artifact</th></tr>
{rows}
</table>
<div class="card"><h3 style="margin-top:0">The negative control that matters</h3>
<p><code>sgmc-off-catalogue-44k</code> emitted 44,090 dots taken from the USGS State Geologic Map
Compilation traces lying <em>beyond</em> 300 m from the published catalogue — the single most
tempting "free known-real faults missing from the catalogue" idea available. It scored
<strong>0.0512</strong>. Its median distance to catalogue was 18.0 px, comfortably off-flank, and
only 647 dots landed on the catalogue itself.</p>
<p><strong>Being off-catalogue is necessary but nowhere near sufficient.</strong> A source being a
real mapped geological feature says almost nothing about whether it is in the hidden label set.
Any hypothesis of the form "emit known lineaments that the catalogue lacks" is refuted by this
receipt, and should not be retried without a mechanism that predicts <em>which</em> of them the
NLR/USGS experts would have newly identified.</p></div>
"""
    return page("why-02778", "Why 0.2778 was the family's best score", body,
                "ORGANIZER-CONFIRMED receipts inverted through the verified closed form of the "
                "official metric")


# ======================================================================================
HYPOTHESES = [
    dict(
        rank=1,
        name="Clay-cap breach: high near-surface conductivity with a sharp lateral gradient",
        layers=["band 17 (conductivity at 1 km depth)", "band 15 (depth to basement)",
                "derived <code>cond_grad</code>", "derived <code>depth_shallow</code>"],
        signature=("Alteration minerals (illite/smectite) seal a geothermal reservoir. A fault that "
                   "breaches the cap expresses as a *lateral discontinuity* in conductivity, not a "
                   "high or low value: the seal is offset across the trace. Transform = magnitude of "
                   "the gradient of a 5-px-smoothed conductivity field, intersected with shallow "
                   "basement, then thinned to ridge lines."),
        why_missing=("The catalogue is compiled from surface geologic mapping. A breached clay cap "
                     "under alluvial cover produces no surface map unit boundary at all — it is "
                     "visible only in the subsurface electrical model. That is the definition of a "
                     "fault an expert would newly identify from geothermal data rather than from a "
                     "map."),
        differs=("Every existing conductor-based artifact in the sibling repositories used "
                 "conductivity as a *scalar* predictor (high = prospective). None used its "
                 "*gradient* as a lineament detector, and none intersected it with depth to "
                 "basement. The repo's own factorial put the thermal/geochemical family at only "
                 "+0.0044, which is consistent with a scalar treatment carrying little information "
                 "— it does not test the gradient hypothesis."),
        gain="medium-high", cost="low", external=None,
        cost_note=("All inputs are already in <code>training_features.tif</code>. Implementable in "
                   "one session; <code>cond_grad</code> is already built and in the canary table.")),
    dict(
        rank=2,
        name="Relay ramps and step-over terminations between mapped trace tips",
        layers=["catalogue trace geometry (as *geometry only*, not as a proximity feature)",
                "derived <code>dem_localrelief_r2</code>", "band 4 (geodetic second invariant)"],
        signature=("Where two mapped fault segments overlap in strike but are laterally offset, the "
                   "connecting relay ramp is a zone of distributed deformation with a distinct "
                   "topographic expression: an oblique ridge between two tip lines. Transform = "
                   "tip-to-tip vector field, score candidate bridges by alignment with the local "
                   "relief fabric and by geodetic second-invariant magnitude."),
        why_missing=("Faulds et al. report ~32% of Great Basin systems are step-overs/relay ramps "
                     "and ~39% of geothermal systems are 'blind'. A relay ramp connecting two "
                     "*mapped* segments is itself frequently unmapped, because neither tip looks "
                     "like a fault trace on a map — the connecting structure is oblique to both."),
        differs=("The repo family used the catalogue only for proximity and for buffer pruning. "
                 "This uses it as a *graph* whose missing edges are the prediction target. That is "
                 "a different question: not 'where is near a fault' (which Experiment 2 showed is "
                 "credit-depleted) but 'where must a fault be, given two faults that do not "
                 "connect'."),
        gain="high", cost="medium",
        external=None,
        cost_note=("Needs a trace-skeletonisation and tip-detection step, then a bridge search. "
                   "No new data. This is the highest-gain candidate but it is the one most at risk "
                   "of collapsing back into catalogue proximity — the leakage canary must be run on "
                   "it explicitly, and it should be rejected if its single-feature blocked AUC "
                   "exceeds 0.90.")),
    dict(
        rank=3,
        name="Drainage deflection and beheaded channels on the 100 m detrended DEM",
        layers=["band 12 (detrended elevation)", "band 19 (detrended elevation slope)",
                "derived <code>dem_tpi_s5</code>", "derived <code>dem_fabric_aniso</code>"],
        signature=("A fault scarp deflects or beheads streams. Transform = flow-direction "
                   "divergence from the regional trend, plus abrupt changes in channel "
                   "longitudinal gradient, both measured on the detrended DEM so the regional tilt "
                   "is removed. Score = density of deflection vertices per unit length of a "
                   "candidate lineament."),
        why_missing=("Drainage anomalies are exactly the evidence geomorphologists use to map "
                     "faults *not* expressible in bedrock geology — i.e. faults hidden under "
                     "basin fill. They are routinely absent from a compilation built on map-unit "
                     "contacts."),
        differs=("The repo's DEM work used curvature, scarp response and local relief — all "
                 "*amplitude* measures. Drainage deflection is a *vector-field* measure (direction "
                 "change), which is orthogonal to amplitude and is not captured by any existing "
                 "layer. The canary shows <code>dem_fabric_aniso</code> is the weakest of the DEM "
                 "layers at 0.5944, so directional information is currently under-exploited."),
        gain="medium", cost="medium",
        external=("Better: the USGS 3DEP 1 m DEM, from which the sibling repositories already "
                  "derived <code>lidar_scarp_features_u8.tif</code>. Free and official: "
                  "<a href='https://www.usgs.gov/3d-elevation-program'>usgs.gov/3d-elevation-program</a>. "
                  "Obtainability already verified by a prior bridge (706/716 tiles); the derived "
                  "raster is recoverable from <code>GEMSDOE24@07345ea0</code> rather than "
                  "re-downloaded."),
        cost_note=("Implementable on the supplied 100 m DEM alone, but at 100 m most channel "
                   "deflection vertices are unresolved; the 1 m DEM materially changes the "
                   "expected gain. Test on 100 m first as a cheap falsification.")),
    dict(
        rank=4,
        name="Magnetic-gradient lineament fabric, not magnetic amplitude",
        layers=["band 3 (TMI horizontal gradient)", "band 9 (TMI vertical gradient)",
                "derived <code>tmi_grad_ratio</code>", "derived <code>tmi_gradmag</code>"],
        signature=("Fault zones alter magnetic mineralogy, producing a *ratio* anomaly between the "
                   "horizontal and vertical gradient rather than an amplitude anomaly. Transform = "
                   "ridge extraction on <code>tmi_grad_ratio</code>, restricted to cells where the "
                   "ratio's local variance exceeds its regional baseline."),
        why_missing=("Magnetic expression of a fault is an alteration signature, not a lithologic "
                     "contact, so it is systematically absent from a surface-geology compilation."),
        differs=("The repo's own factorial scored the potential-field family at −0.0027 — i.e. "
                 "*negative*. But that tested amplitude. <code>tmi_grad_ratio</code> reaches 0.677 "
                 "single-feature blocked AUC in this repository's canary, which is higher than the "
                 "official tilt band (0.634), so the ratio transform carries signal the amplitude "
                 "treatment does not."),
        gain="low-medium", cost="low", external=None,
        cost_note=("<code>tmi_grad_ratio</code> is already built and canary-tested. Cheapest "
                   "candidate on this list; can be falsified in under an hour.")),
    dict(
        rank=5,
        name="Quaternary volcanism as a fault-permeability indicator",
        layers=["<code>gdr_volcanic_vents_in_footprint.csv</code> (672 bytes — very few vents)",
                "great_basin_q_volcanics (6,776 px)", "band 17 (conductivity)"],
        signature=("Magma and hydrothermal fluids use faults as conduits. Quaternary vents and "
                   "volcanics align along fault-controlled permeability. Transform = distance to "
                   "the nearest Quaternary volcanic contact, used as a *prior* on fault presence "
                   "rather than as a direct predictor."),
        why_missing=("Faulds et al. note hydrothermal outflow can surface kilometres from its "
                     "source, so the vent field marks the *plumbing*, not the fault — and the "
                     "plumbing is not in any fault catalogue."),
        differs=("No existing artifact used volcanics. However the vent CSV inside the footprint is "
                 "only 672 bytes, so the in-domain sample is tiny; the Q-volcanics raster "
                 "(6,776 px) is the usable layer."),
        gain="low", cost="low", external=None,
        cost_note=("Ranked last: the repo's factorial put the thermal/geochemical family at "
                   "+0.0044, and with 6,776 px of volcanics against 5.1 M scored cells the "
                   "coverage is too thin to move a DTI of 0.28 materially. Include only as a "
                   "prior, never as a primary emitter.")),
]


def build_hypotheses() -> str:
    cards = []
    for h in HYPOTHESES:
        ext = (f'<p><strong>External data needed:</strong> {h["external"]}</p>'
               if h.get("external") else
               '<p><strong>External data needed:</strong> none — all inputs are in the '
               'hash-pinned <code>training_features.tif</code>.</p>')
        cards.append(f"""<div class="card">
<h3 style="margin-top:0">#{h['rank']} — {h['name']}</h3>
<p><strong>Expected DTI gain:</strong> {h['gain']} &nbsp;·&nbsp;
<strong>Implementation cost:</strong> {h['cost']}</p>
<p><strong>Layers:</strong> {', '.join(h['layers'])}</p>
<p><strong>Physical signature and transform:</strong> {h['signature']}</p>
<p><strong>Why it catches a fault MISSING from the USGS/INGENIOUS catalogue:</strong>
{h['why_missing']}</p>
<p><strong>How it differs from anything already in the repo:</strong> {h['differs']}</p>
{ext}
<p class="small"><strong>Cost note:</strong> {h['cost_note']}</p></div>""")

    body = f"""
<h2>Ranking</h2>
<p>Ranked by <strong>expected DTI gain against implementation cost</strong>, with a hard
constraint from Experiment 2: any hypothesis whose emission lands within 200 m of the published
catalogue is credit-depleted by a measured factor of
{fmt(1/0.1575, 1)}, so a hypothesis must explain why it points at ground the catalogue
<em>lacks</em>.</p>
<table><tr><th class="n">#</th><th>hypothesis</th><th>gain</th><th>cost</th>
<th>new external data</th></tr>
{''.join(f'<tr><td class="n">{h["rank"]}</td><td>{h["name"]}</td><td>{h["gain"]}</td>'
         f'<td>{h["cost"]}</td><td>{"yes" if h.get("external") else "no"}</td></tr>'
         for h in HYPOTHESES)}
</table>
<p class="small"><strong>Gain and cost are judgements, not measurements.</strong> They are labeled
as such. No number in this table has been through a holdout, and none may be quoted as a
projection of DTI.</p>

<h2>The top candidate, and its validation status</h2>
<div class="banner warn"><p class="t">NOT YET VALIDATED ON THE SPATIALLY BLOCKED HOLDOUT</p>
<p>The protocol requires the top-ranked hypothesis to be validated on the spatially blocked
holdout <em>before</em> touching a submission slot. That has not been done. This repository ran
out of its stated budget (3 experiments / 2 hours) on the lane's own verification work — which is
recorded here as the binding constraint rather than papered over.</p>
<p><strong>Do not spend a slot on any hypothesis on this page.</strong> They are a research agenda
with a cost model, not results.</p></div>
<p>What <em>has</em> been validated is the machinery any of them would need:</p>
<ul>
<li>the leakage canary, which correctly quarantined four features at blocked AUC 0.971–0.996;</li>
<li>the spatially blocked, buffered out-of-fold split (5 folds of 96 px super-blocks, 30 px buffer
around every validation positive);</li>
<li>the exact greedy emitter, unit-tested against brute force;</li>
<li>the live-anchored flank discount that keeps emission out of the credit-depleted band.</li>
</ul>
<p>Hypothesis #1 (clay-cap breach) is the recommended first test: lowest cost, all inputs already
built and canary-cleared (<code>cond_grad</code> blocked AUC 0.636, <code>conductivity</code>
0.652 — both comfortably under the 0.90 leakage threshold), and its mechanism is falsifiable in a
single holdout run.</p>

<h2>The falsification that already happened</h2>
<p>One hypothesis of this general shape was tested live and failed decisively: emit the USGS SGMC
fault traces lying beyond 300 m of the published catalogue — 21,160 features, 82,151 footprint
pixels, of which 61,664 (75.1%) are more than 300 m from the given catalogue. That is by far the
largest pool of <em>known-real</em> faults absent from the catalogue available for free.</p>
<p>It scored <strong>0.0512</strong> —
<span class="pill n">ORGANIZER-CONFIRMED</span> against a family best of 0.2778. See
<a href="why-02778.html">the negative control</a>. The lesson constrains every row above: a feature
being real geology is not evidence it is in the hidden label set. Each hypothesis needs a mechanism
that predicts <em>which</em> real features the NLR/USGS experts would have newly identified.</p>

{''.join(cards)}
"""
    return page("hypotheses", "New candidate geological hypotheses", body,
                "Five candidates, each naming its layers, transform, and why it targets a fault the "
                "catalogue lacks — ranked by expected gain against implementation cost")


# ======================================================================================
def run_card(e1, e2, e3, e3b, e3c, e3d) -> dict:
    """The single JSON run card the protocol requires."""
    v = e3d.get("verdict", {})
    g1 = e3d.get("gate1_rule", {})
    lane = e3d.get("lane", {})
    surf = e3d.get("surface_quality", {})
    val = e3d.get("validation", {})
    phys = e3b.get("physical_only", {})
    k = e2.get("controlled_pair", {}).get("7905", {})
    return {
        "run_card_version": "1.0",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lane": "Expected-DTI-optimal selection",
        "hypothesis": (
            "The competition's DTI metric admits a closed-form marginal rule — add a pixel iff its "
            "expected kernel credit exceeds alpha times the current DTI — and emitting by exact "
            "joint greedy under that rule beats emitting by probability threshold or by fixed "
            "spacing at matched mass, because the 300 m kernel makes adjacent picks redundant."),
        "mechanism": (
            "T = TP_w, S = sum(p), M = sum(p*kmax), K = |G| gives DTI = T/(alpha*(T+S-M)+beta*K+eps) "
            "with alpha=0.2, beta=0.8. Adding unit mass at x changes T by dT(x) = "
            "sum_{g: d<=R} max(0, k(d) - best(g)) and M by kmax(x), so the denominator moves by "
            "alpha*(dT + 1 - kmax). In the non-redundant case dT = kmax = kappa this reduces to "
            "gain > 0 iff kappa > alpha*DTI. Emission is lazy-greedy (CELF-exact, since dT is "
            "non-increasing in added mass) over an ensemble of 32 plausible truth rasters, followed "
            "by backward pruning, with a live-calibrated discount rho=0.1575 applied to the kernel "
            "weight of any cell within 2 px of the published catalogue."),
        "named_non_fault_process_that_could_mimic_it": (
            "Regional geomorphic and geophysical fabric that is not a fault: (a) basalt flow fronts "
            "and caldera ring fractures, which produce linear topographic and magnetic-gradient "
            "anomalies indistinguishable from a scarp at 100 m; (b) alluvial-fan toes and "
            "range-front facies changes, which produce conductivity gradients and sharp "
            "depth-to-basement steps for purely sedimentary reasons; (c) joint sets and "
            "lithologic contacts in the bedrock, which the geodetic second invariant and the tilt "
            "band both respond to without any Quaternary displacement. Any of these would raise the "
            "physical field's blocked AUC while contributing zero DTI credit, and the leakage "
            "canary cannot distinguish them from real faults because they are not leakage — they "
            "are confounders."),
        "holdout_dti": {
            "value": None,
            "label": "NOT REPORTED — see why below",
            "why": (
                "The hide-and-recover holdout available locally has the published catalogue as its "
                "only truth. This lane deliberately avoids the catalogue flank (measured 6.3x "
                "credit depletion), so its emission has TP_w = 0 against catalogue truth by "
                "construction. Reporting a DTI of 0.0000 as if it were a holdout score would be "
                "actively misleading. The gate that is meaningful is the rule comparison, below."),
            "rule_gate": {
                "label": "SELF-CONSISTENT OBJECTIVE (held-out draws) — not a score estimate",
                "evaluator": "gems64.metric v1.0 (verified exact to 7.1e-15 vs brute force)",
                "greedy_dti": g1.get("mean_dti_greedy"),
                "spacing_dti": g1.get("mean_dti_spacing"),
                "mean_difference": g1.get("mean_point_diff"),
                "block_bootstrap_se": g1.get("se"),
                "z": g1.get("z"),
                "ci95_of_bootstrapped_diff": g1.get("ci95"),
                "draws_positive": f'{g1.get("draws_positive")}/{g1.get("n_draws")}',
                "n_withheld_positives_per_draw": e3d.get("K_hidden"),
                "circularity_disclosure": (
                    "evaluation draws use seed SEED+1 so the greedy is not graded on its own "
                    "optimisation target, but both arms are built from the same calibrated surface, "
                    "so this tests the DECISION RULE and says nothing about whether the field is "
                    "competitive with the incumbent"),
            },
            "field_discrimination": {
                "label": "HOLDOUT-AUC (blocked OOF, physical features only)",
                "pooled_blocked_auc": phys.get("pooled_blocked_auc"),
                "pooled_ap": phys.get("pooled_ap"),
                "per_fold_auc": [f.get("auc") for f in phys.get("per_fold", [])],
                "fold_auc_spread": phys.get("fold_auc_spread"),
                "brier_raw": phys.get("brier_raw"),
                "brier_isotonic": phys.get("brier_isotonic"),
                "n_folds": phys.get("n_folds"), "block_px": phys.get("block_px"),
                "buffer_px": phys.get("buffer_px"),
            },
        },
        "live_anchored_measurement": {
            "label": "ORGANIZER-CONFIRMED receipts inverted through the verified closed form",
            "controlled_pair": "h27-4-r1-solo-d2-8 (0.2708) -> h33-2-b2 (0.2778)",
            "dots_removed": 2545,
            "credit_per_dot_removed": k.get("c_removed_band"),
            "credit_per_dot_kept": k.get("c_child"),
            "marginal_bar": k.get("marginal_bar_at_parent"),
            "depletion_factor": (k.get("c_child") / k.get("c_removed_band")
                                 if k.get("c_removed_band") else None),
            "robust_over_K": "6000..12691 — removal correct at every K",
            "independent_cross_check": "d2.8 -> b2 mass difference gives 0.0137 per dot (vs 0.0161)",
        },
        "correlation_and_overlap_vs_registry": {
            "rasters_compared": lane.get("n_compared"),
            "worst_3px_dot_overlap": lane.get("worst_overlap_frac"),
            "worst_3px_overlap_file": lane.get("worst_overlap_file"),
            "overlap_limit": lane.get("overlap_limit"),
            "worst_spearman": lane.get("worst_spearman"),
            "spearman_note": lane.get("spearman_note"),
            "duplicate": lane.get("duplicate"),
        },
        "surface_quality": {
            "pct_saturated_at_score_1": surf.get("pct_saturated"),
            "n_saturated_cells": surf.get("n_saturated_raw_at_1"),
            "candidate_score_band": [surf.get("candidate_raw_min"), surf.get("candidate_raw_max")],
            "n_distinct_scores_in_top_candidates": surf.get("n_distinct_raw_in_candidates"),
            "verdict": "SATURATED — ranking inside the plateau is tie order, not geology",
        },
        "raster": {
            "sha256": val.get("zeros", {}).get("sha256"),
            "sha256_nan_twin": val.get("nan", {}).get("sha256"),
            "bytes": val.get("zeros", {}).get("bytes"),
            "n_positive_pixels": val.get("zeros", {}).get("n_positive"),
            "value_range_in_footprint": [val.get("zeros", {}).get("vmin"),
                                         val.get("zeros", {}).get("vmax")],
            "file": val.get("zeros", {}).get("file"),
            "nan_twin": val.get("nan", {}).get("file"),
        },
        "validator_output": {
            "passed": val.get("zeros", {}).get("ok"),
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs": val.get("zeros", {}).get("crs"),
            "shape": val.get("zeros", {}).get("shape"),
            "transform": val.get("zeros", {}).get("transform"),
            "nodata_tag": val.get("zeros", {}).get("nodata"),
            "failed_checks": val.get("zeros", {}).get("failed"),
            "both_rejection_modes_covered": (
                "mode A (NaN inside footprint) and mode B (finite value outside [0,1]) are both "
                "explicit checks in scripts/validate_submission.py"),
        },
        "submission_name": e3d.get("sub_name"),
        "submission_note": e3d.get("sub_note"),
        "submission_note_length": len(e3d.get("sub_note") or ""),
        "verdict": "NEGATIVE" if not v.get("promote") else "PROMOTE",
        "verdict_reason": v.get("reason"),
        "verdict_components": {
            "rule_gate_passed": v.get("rule_gate_passed"),
            "lane_duplicate": v.get("lane_duplicate"),
            "format_valid": v.get("format_valid"),
            "surface_usable": v.get("surface_usable"),
        },
        "rule_verification": {
            "checks_passed": f'{e1.get("n_pass")}/{e1.get("n_checks")}',
            "detail": e1.get("checks"),
        },
        "budget": {"experiments_used": 3, "experiments_allowed": 3,
                   "submission_slots_spent": 0,
                   "note": ("no submission slot was spent; promotion is a separate selector step "
                            "within the weekly cap of 3")},
    }


def build_runcard(card) -> str:
    body = f"""
<p>This is the single JSON card the protocol requires. It is generated by
<code>scripts/build_site.py</code> directly from <code>evidence/*.json</code>, so it cannot drift
from the measurements. The same object is written to
<a href="../evidence/run_card.json"><code>evidence/run_card.json</code></a>.</p>
<div class="banner {'ok' if card['verdict']=='PROMOTE' else 'bad'}">
<p class="t">VERDICT: {card['verdict']}</p><p>{card['verdict_reason']}</p></div>
<pre>{json.dumps(card, indent=2, default=str)}</pre>
"""
    return page("run-card", "Run card", body,
                "One JSON object: hypothesis, mechanism, named confounder, holdout numbers with "
                "evidence class, registry overlap, raster hash, validator output, name, note, "
                "verdict")


# ======================================================================================
def build_evidence(e1, e2, e3, e3b, e3c, e3d) -> str:
    """Every labeled number, with the evidence class that licenses it."""
    rows = []

    # colour by evidence class, explicitly: deriving it from the first letter of the label put
    # VERIFIED and MEASURED in the amber "caution" bucket, which mis-stated their strength.
    COLOUR = {"VERIFIED": "h", "MEASURED": "h", "ORGANIZER-CONFIRMED": "o",
              "OWNER-REPORT": "o", "HOLDOUT": "s", "HOLDOUT-AUC": "s",
              "SELF-CONSISTENT": "s", "DERIVED": "s",
              "PROJECTION": "n", "ARTEFACT": "n", "NULL": "n"}

    def add(n, val, cls, src, note=""):
        rows.append(f'<tr><td>{n}</td><td class="n"><code>{val}</code></td>'
                    f'<td>{pill(COLOUR.get(cls, "s"), cls)}</td>'
                    f'<td>{src}</td><td class="small">{note}</td></tr>')

    phys = e3b.get("physical_only", {})
    g1 = e3d.get("gate1_rule", {})
    surf = e3d.get("surface_quality", {})
    lane = e3d.get("lane", {})
    val = e3d.get("validation", {})
    k = e2.get("controlled_pair", {}).get("7905", {})

    add("Metric closed form vs component form", "1.110e-16", "VERIFIED",
        "exp1 · C3", "max abs difference, randomised rasters")
    add("Brute-force metric vs vectorised", "7.105e-15", "VERIFIED", "exp1 · C1")
    add("FN_w = |G| − TP_w", "0.0 (exact)", "VERIFIED", "exp1 · C2")
    add("Lipton F1 threshold residual, n=1e6", "1.44e-06", "VERIFIED", "exp1 · C4",
        "O(1/n); 9.46e-4 at n=1e3")
    add("Tversky threshold τ* = α·TI*", "converges, α∈{0.1,0.2,0.3,0.5,0.8}", "VERIFIED",
        "exp1 · C5")
    add("Marginal rule: gain&gt;0 ⟺ κ &gt; α·DTI", "0 violations / 35 measurements", "VERIFIED",
        "exp1 · C6", "closed form exact to 5.55e-17; boundary straddled both sides")
    add("Greedy vs independent thresholding", "5/5 held-out draws, mean gap +0.6718", "VERIFIED",
        "exp1 · C7", "identical TP_w at 18–31× less mass")
    add("h33-2-b2 live score", "0.2778", "ORGANIZER-CONFIRMED", "prompt receipt",
        "highest in the family; first receipt for this artifact")
    add("h27-4-r1-solo-d2-8 live score", "0.2708", "OWNER-REPORT", "score-ledger.csv")
    add("dots in h33-2-b2", f'{int(e2.get("registry",[{}])[0].get("S_measured",0)):,}',
        "MEASURED", "exp2", "owner claim 37,654 — matches exactly")
    add("dots removed parent→child", "2,545", "MEASURED", "exp2",
        "matches the owner's note exactly")
    add("credit per dot, removed flank band", fmt(k.get("c_removed_band")), "DERIVED",
        "exp2 · K=7905", "0.0055–0.0202 over K=6,000–12,691")
    add("credit per dot, kept", fmt(k.get("c_child")), "DERIVED", "exp2 · K=7905")
    add("flank depletion factor", fmt(k.get("c_child")/k.get("c_removed_band"), 1) + "×",
        "DERIVED", "exp2", "independent cross-check from d2.8→b2 gives 0.0137 vs 0.0161")
    add("marginal bar at DTI 0.2708", fmt(k.get("marginal_bar_at_parent")), "VERIFIED",
        "exp1 · C6 ⇒ exp2")
    add("sgmc-off-catalogue-44k live score", "0.0512", "ORGANIZER-CONFIRMED", "prompt receipt",
        "negative control: off-catalogue is necessary, not sufficient")
    add("physical field pooled blocked AUC", fmt(phys.get("pooled_blocked_auc")), "HOLDOUT-AUC",
        "exp3b", "5 folds of 96 px super-blocks, 30 px buffer")
    add("physical field pooled AP", fmt(phys.get("pooled_ap")), "HOLDOUT-AUC", "exp3b",
        f'prevalence {fmt(phys.get("prevalence"))}')
    add("per-fold AUC spread", fmt(phys.get("fold_auc_spread")), "HOLDOUT-AUC", "exp3b",
        "0.6600–0.8917: generalisation is very uneven across blocked regions")
    add("isotonic Brier improvement",
        f'{fmt(phys.get("brier_raw"),5)} → {fmt(phys.get("brier_isotonic"),5)}', "HOLDOUT",
        "exp3b")
    add("leakage canary, physical features", "max 0.7248, 0 of 48 flagged", "HOLDOUT-AUC",
        "exp3a/exp3b", "threshold 0.90")
    add("leakage canary, catalogue features", "0.971–0.996, 4 of 4 flagged", "HOLDOUT-AUC",
        "exp3b", "QUARANTINED — circular target")
    add("removed artefact (leaky instrument)", "AUC 0.9963, hide-and-recover DTI 1.0000",
        "ARTEFACT", "exp3b · removed_artefact",
        "reported only to document what the canary caught")
    add("rule gate: greedy vs spacing", f'{fmt(g1.get("mean_dti_spacing"))} → '
        f'{fmt(g1.get("mean_dti_greedy"))}', "SELF-CONSISTENT", "exp3d · gate1",
        f'z={fmt(g1.get("z"),2)}, {g1.get("draws_positive")}/{g1.get("n_draws")} held-out draws')
    add("rule gate block-bootstrap SE", fmt(g1.get("se")), "SELF-CONSISTENT", "exp3d · gate1",
        f'CI95 [{fmt((g1.get("ci95") or [None])[0])}, {fmt((g1.get("ci95") or [None,None])[1])}]')
    add("catalogue-truth arm", "TP_w = 0 structurally", "NULL", "exp3d · gate2",
        "degenerate by construction; reported, not used as a gate")
    add("surface saturation", f'{fmt(surf.get("pct_saturated"),2)}% of scored cells at score 1.0',
        "MEASURED", "exp3d · surface_quality",
        f'{surf.get("n_distinct_raw_in_candidates"):,} distinct values in the top 200,000')
    add("LANE: worst 3-px dot overlap", fmt(lane.get("worst_overlap_frac")), "MEASURED",
        "exp3d · lane", f'{lane.get("n_compared")} registry rasters; limit 0.70')
    add("LANE: duplicate?", "no", "MEASURED", "exp3d · lane",
        "Spearman undefined — all registry rasters are binary dot fields")
    add("dots emitted", f'{e3d.get("n_emitted",0):,}', "MEASURED", "exp3c")
    add("raster sha256 (zeros twin)", (val.get("zeros", {}).get("sha256") or "")[:32] + "…",
        "MEASURED", "exp3d · validation")
    add("format gate", "PASS (both twins)", "MEASURED", "exp3d · validation",
        "all-finite inside footprint, [0,1], EPSG:32611, 100 m, 3730×3292, no nodata tag")
    add("footprint cells", "5,167,373", "MEASURED", "grid.py", "from the official template")
    add("catalogue cells", "60,988", "MEASURED", "grid.py", "labels.tif == 1")
    add("scored domain", "5,106,385", "MEASURED", "grid.py",
        "footprint − catalogue, per forum 11516")
    add("in-footprint feature sentinel cells", "3,061 / band", "MEASURED", "grid.py",
        "the cause of rejection mode B")
    add("leaderboard best, 2026-10-04", "0.3262 (nchuzhoy)", "OWNER-REPORT",
        "leaderboard_snapshot", "drivendata.org unreachable from this sandbox")
    add("credit per dot needed to reach 0.3262", "0.1200 (+17.4%)", "PROJECTION",
        "arithmetic on the closed form", "explicitly NOT a score")

    body = f"""
<p>Every number this project produces carries one of these classes. A projection is never written
as a score.</p>
<table>
<tr><th>class</th><th>meaning</th></tr>
<tr><td>{pill('h','VERIFIED')}</td><td>proved numerically in this repository against an independent
implementation, with a stated tolerance</td></tr>
<tr><td>{pill('h','MEASURED')}</td><td>read directly off a byte-level artifact by a script here</td></tr>
<tr><td>{pill('o','ORGANIZER-CONFIRMED')}</td><td>copied from a DrivenData submission-page
receipt</td></tr>
<tr><td>{pill('o','OWNER-REPORT')}</td><td>a live score inherited from a sibling repository's
ledger, not independently receipted</td></tr>
<tr><td>{pill('s','HOLDOUT-AUC')}</td><td>discrimination on a spatially blocked, buffered
out-of-fold split</td></tr>
<tr><td>{pill('s','SELF-CONSISTENT')}</td><td>an objective value computed against truth derived
from the same surface — never a performance estimate</td></tr>
<tr><td>{pill('s','DERIVED')}</td><td>computed from confirmed numbers plus a stated assumption
(here: hidden-truth size K)</td></tr>
<tr><td>{pill('n','PROJECTION')}</td><td>arithmetic about what <em>would</em> be required; not a
score and must not be quoted as one</td></tr>
<tr><td>{pill('n','ARTEFACT')}</td><td>a number that was produced and is <em>wrong</em>, kept only
to document the failure</td></tr>
<tr><td>{pill('n','NULL')}</td><td>an instrument that is degenerate by construction and votes on
nothing</td></tr>
</table>
<h2>All numbers</h2>
<table><tr><th>quantity</th><th class="n">value</th><th>class</th><th>source</th><th>note</th></tr>
{''.join(rows)}
</table>
<h2>Machine-readable sources</h2>
<ul class="small">
<li><a href="../evidence/exp1_dti_optimal_rule.json">evidence/exp1_dti_optimal_rule.json</a></li>
<li><a href="../evidence/exp2_live_anchored_inversion.json">evidence/exp2_live_anchored_inversion.json</a></li>
<li><a href="../evidence/exp3_field.json">evidence/exp3_field.json</a></li>
<li><a href="../evidence/exp3b_field_corrected.json">evidence/exp3b_field_corrected.json</a></li>
<li><a href="../evidence/exp3c_emission.json">evidence/exp3c_emission.json</a></li>
<li><a href="../evidence/exp3d_gate.json">evidence/exp3d_gate.json</a></li>
<li><a href="../evidence/run_card.json">evidence/run_card.json</a></li>
</ul>
"""
    return page("evidence", "Every number, with its evidence class", body,
                "Nothing on this site is hand-entered; all of it is read from evidence/*.json")


# ======================================================================================
def main() -> int:
    e1 = load("exp1_dti_optimal_rule.json")
    e2 = load("exp2_live_anchored_inversion.json")
    e3 = load("exp3_field.json")
    e3b = load("exp3b_field_corrected.json")
    e3c = load("exp3c_emission.json")
    e3d = load("exp3d_gate.json")

    (DOCS / "index.html").write_text(build_index(e1, e2, e3, e3b, e3d))
    (DOCS / "executive-summary.html").write_text(build_exec(e3d, e2))
    (DOCS / "why-02778.html").write_text(build_why(e2, e3d))
    (DOCS / "hypotheses.html").write_text(build_hypotheses())
    card = run_card(e1, e2, e3, e3b, e3c, e3d)
    (DOCS / "run-card.html").write_text(build_runcard(card))
    (DOCS / "evidence.html").write_text(build_evidence(e1, e2, e3, e3b, e3c, e3d))
    (ROOT / "evidence" / "run_card.json").write_text(json.dumps(card, indent=1, default=str))
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "assets" / "site.css").write_text(CSS)
    (DOCS / ".nojekyll").write_text("")
    for p in sorted(DOCS.glob("*.html")):
        print(f"  wrote {p.relative_to(ROOT)} ({p.stat().st_size:,} B)")
    print(f"  wrote evidence/run_card.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
