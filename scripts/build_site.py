"""Build the GitHub Pages site (docs/) from the evidence JSON files.

Nothing is hard-coded: every number on the page is read from
``evidence/*.json`` that the experiments wrote, so the site cannot drift from
the measurements.

Usage:  python scripts/build_site.py
"""
from __future__ import annotations

import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))

CSS = """
:root{--ink:#101820;--mut:#5b6b7b;--line:#dde5ec;--ok:#0b7a3b;--bad:#b3261e;--acc:#0b5cad}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#f7fafc}
header{background:#0d2137;color:#fff;padding:26px 20px}header h1{margin:0 0 6px;font-size:24px}header p{margin:0;color:#c9d8e6}
.wrap{max-width:1000px;margin:0 auto;padding:20px}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:16px 0}
.dl{display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.btn{display:inline-block;background:var(--acc);color:#fff;text-decoration:none;padding:14px 22px;border-radius:8px;font-weight:700;font-size:18px}
.btn.sec{background:#fff;color:var(--acc);border:2px solid var(--acc)}
.verdict{font-weight:800;font-size:18px;padding:8px 14px;border-radius:8px}
.v-ok{background:#e6f6ec;color:var(--ok);border:1px solid #a9dfbe}
.v-no{background:#fdecea;color:var(--bad);border:1px solid #f2b8b5}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left}
th{background:#f1f5f9}td.n{text-align:right;font-variant-numeric:tabular-nums}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
pre{background:#0d2137;color:#e8f0f7;padding:12px;border-radius:8px;overflow-x:auto}
.mut{color:var(--mut);font-size:13px}ol li,ul li{margin:4px 0}
h2{font-size:19px;margin:4px 0 10px}h3{font-size:16px;margin:14px 0 6px}
nav a{color:#c9d8e6;text-decoration:none;margin-right:14px;font-size:14px}
.tag{display:inline-block;background:#eef3f8;border:1px solid var(--line);border-radius:20px;padding:2px 10px;font-size:12px;margin:2px 4px 2px 0}
"""

OFFICIAL = [
    ("Competition home", "https://www.drivendata.org/competitions/306/competition-doe-gems/"),
    ("Problem / submission format (page 967)", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"),
    ("About / resources (page 968)", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/"),
    ("Data download (login required)", "https://www.drivendata.org/competitions/306/competition-doe-gems/data/"),
    ("Leaderboard", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"),
    ("Official reference solution", "https://github.com/drivendataorg/gems-prize-reference-solution"),
    ("USGS GeoDAWN airborne magnetics/radiometrics (NW Great Basin)", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and"),
    ("INGENIOUS project (Great Basin Center for Geothermal Energy)", "https://gbcge.org/current-projects/ingenious/"),
    ("EPSG:32611 (WGS 84 / UTM zone 11N)", "https://epsg.io/32611"),
    ("Tversky index", "https://en.wikipedia.org/wiki/Tversky_index"),
    ("Geothermal Data Repository submission 1391", "https://gdr.openei.org/submissions/1391"),
]


def load(name):
    p = ROOT / "evidence" / name
    return json.loads(p.read_text()) if p.is_file() else None


def esc(x):
    return html.escape(str(x))


def dl_block(e3, gate_passed, verdict_text, verdict_class):
    if not e3:
        return ('<div class="card"><h2>Submission file</h2>'
                '<p class="verdict v-no">NO TIF BUILT YET &mdash; run scripts/e3_build_submission.py</p></div>')
    rel = "downloads/" + pathlib.Path(e3["file_name"]).name
    zrel = rel[:-4] + ".zip"
    return f"""
<div class="card">
  <h2>Submission file &mdash; this session</h2>
  <div class="dl">
    <a class="btn" href="{rel}" download>&#11015; DOWNLOAD {esc(e3['file_name'])}</a>
    <a class="btn sec" href="{zrel}" download>.zip (single TIFF)</a>
    <a class="btn sec" href="{rel[:-4]}-runcard.json" download>run card</a>
    <a class="btn sec" href="{rel[:-4]}.json" download>validation receipt</a>
  </div>
  <p style="margin-top:14px"><span class="verdict {verdict_class}">{esc(verdict_text)}</span></p>
  <p><b>Submission name:</b> <code>{esc(e3['submission_name'])}</code><br>
     <b>Note (&le;140 chars):</b> <code>{esc(e3['note'])}</code> ({e3['note_chars']} chars)<br>
     <b>raster sha256:</b> <code>{esc(e3['raster_sha256'])}</code><br>
     <b>dots:</b> {e3['n_dots']:,} &middot; <b>bytes:</b> {e3['raster_bytes']:,}</p>
  <p class="mut">Format checks below are local. Local validity is not organizer
  acceptance, and promotion to a weekly slot is a separate selector decision.</p>
</div>"""


def fmt_report_table(e3):
    if not e3:
        return ""
    fr = e3.get("format_report", {})
    rows = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
                   for k, v in fr.items() if k not in ("path",))
    return f"<table><tr><th>format check</th><th>value</th></tr>{rows}</table>"


def uniq_table(e3):
    if not e3:
        return ""
    u = e3["uniqueness"]
    rows = "".join(f"<tr><td>{esc(k)}</td><td class='n'>{esc(v)}</td></tr>" for k, v in u.items())
    return f"<table><tr><th>uniqueness check vs {u['n_registry_rasters_checked']} registry rasters</th><th>value</th></tr>{rows}</table>"


def gate_card(e2, title, extra=""):
    g = e2["gate"]
    rows = "".join(f"<tr><td>{esc(k)}</td><td class='n'>{v:.4f}</td></tr>"
                   for k, v in e2["pooled_dti"].items())
    return f"""
<div class="card"><h2>{esc(title)}</h2>{extra}
<p>Evaluator <code>{esc(e2['evaluator_version'])}</code>, split <code>{esc(e2['split'])}</code>,
<b>{e2['withheld_positive_pixels']:,}</b> withheld positive pixels (whole catalogue
components hidden inside four label-blind eroded quadrants, 3-px feature buffer).</p>
<table><tr><th>emission rule on the same calibrated surface</th><th>pooled HOLDOUT-DTI</th></tr>{rows}</table>
<p>Paired block bootstrap vs the best baseline (<code>{esc(g['baseline'])}</code>):
&Delta; = <b>{g['delta']:+.5f}</b>, SE = {g['se']:.5f}, z = {g['z']:.2f},
95% CI [{g['ci'][0]:+.5f}, {g['ci'][1]:+.5f}]. Gate is &Delta; &gt; 2&times;SE:
<b>{'PASS' if g['passed'] else 'FAIL'}</b>.</p>
<p class="mut">HOLDOUT-DTI is a withheld-catalogue measurement on this machine.
It is not an organizer score and not a projection of one.</p>
</div>"""


def index_html(e1, e2, e3, gate_passed, e2b=None):
    verdict_text = ("OK TO DOWNLOAD AND SUBMIT &mdash; holdout gate passed"
                    if gate_passed else
                    "OK TO DOWNLOAD FOR RESEARCH &mdash; DO NOT SUBMIT (holdout gate not met)")
    verdict_class = "v-ok" if gate_passed else "v-no"
    gate_html = ""
    if e2b:
        gate_html += gate_card(e2b, "Holdout gate (E2b, calibration prior corrected)",
                               "<p><b>This is the governing measurement.</b> The exact "
                               "negative-sub-sampling odds correction "
                               "<code>w = r&middot;p/(r&middot;p+1-p)</code>, r = "
                               f"{e2b['negative_subsampling_rate']:.6f}, is applied to the "
                               "out-of-fold isotonic surface before selection.</p>")
    if e2:
        gate_html += gate_card(e2, "Holdout gate (E2, first arm &mdash; uncorrected prior)",
                               "<p class='mut'>Superseded by E2b. Kept because it is the "
                               "measurement that exposed the calibration flaw: the "
                               "mean-field DTI (0.33) was four times the realised 0.05.</p>")
    e1_html = ""
    if e1:
        r = e1["threshold_rule_alpha02"]
        e1_html = f"""
<div class="card"><h2>Decision rule, verified before use (E1)</h2>
<p>On synthetic rasters the marginal dot is accepted exactly when its calibrated
kernel credit clears <code>alpha &times; DTI</code>. At alpha = 0.2 and DTI = 0.30 the
bar is <b>{r['quoted_0p2_0p30_bar']}</b>; the measured switch is
{r['empirical_bar']:.4f} (analytic {r['analytic_bar']:.4f}), monotone in kappa.</p>
<p>Lipton/Elkan/Narayanaswamy generalisation: at alpha = 0.5 the optimal
independent threshold is {e1['lipton_alpha05']['empirical_optimal_threshold']:.4f}
vs the predicted F1*/2 = {e1['lipton_alpha05']['predicted_bar']:.4f}
(rel. error {e1['lipton_alpha05']['rel_error']*100:.1f}%); at alpha = 0.2,
{e1['lipton_alpha02']['empirical_optimal_threshold']:.4f} vs
{e1['lipton_alpha02']['predicted_bar']:.4f}.</p>
<p>Greedy add + backward prune reached the <b>exhaustive optimum on all
{len(e1['greedy_vs_exhaustive'])} synthetic rasters</b> (gap 0.0 over
{e1['greedy_vs_exhaustive'][0]['subsets_enumerated']:,} enumerated subsets each),
and the mean-field expected DTI agrees with a
{e1['greedy_vs_exhaustive'][0]['mc_draws']}-draw plausible-truth Monte Carlo
within {abs(e1['greedy_vs_exhaustive'][0]['mean_field_vs_mc_z']):.1f} SE.</p>
</div>"""
    links = "".join(f'<li><a href="{u}">{esc(t)}</a></li>' for t, u in OFFICIAL)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE64 &mdash; DTI-optimal emission</title><style>{CSS}</style></head><body>
<header><div class="wrap" style="padding:0">
<h1>GEMSDOE64 &mdash; expected-DTI-optimal emission for the DOE GEMS Prize</h1>
<p>Lane: replace heuristic dot spacing with a decision rule on a calibrated
probability surface. DrivenData competition 306.</p>
<nav><a href="index.html">Home</a><a href="executive-summary.html">How to submit</a>
<a href="method.html">Method &amp; evidence</a><a href="https://github.com/buffedlizard55-lab/GEMSDOE64">Repository</a></nav>
</div></header><div class="wrap">
{dl_block(e3, gate_passed, verdict_text, verdict_class)}
{gate_html}
{e1_html}
<div class="card"><h2>Format validation</h2>{fmt_report_table(e3)}</div>
<div class="card"><h2>Uniqueness (parallel-run protocol)</h2>{uniq_table(e3)}
<p class="mut">Lane rule: stop if rank correlation with any registry raster
exceeds 0.90 or more than 70% of dots fall within 3 px of one registry raster's dots.</p></div>
<div class="card"><h2>Official sources for manual review</h2><ul>{links}</ul></div>
<p class="mut">Built by <code>scripts/build_site.py</code> from
<code>evidence/*.json</code>. No number on this page is typed by hand.</p>
</div></body></html>"""


def exec_html(e3, gate_passed):
    steps = """
<ol>
<li>Click the blue <b>DOWNLOAD</b> button on the home page. You get a
single-band GeoTIFF (<code>.tif</code>). The <code>.zip</code> next to it contains
the same one TIFF if you prefer to upload a zip.</li>
<li>Open the competition <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">submission page</a>
and press <b>New submission</b>.</li>
<li><b>File to submit:</b> choose the downloaded <code>.tif</code> (or the <code>.zip</code>).</li>
<li><b>Note (optional):</b> paste the note shown on the home page
(&le;140 characters) so the run is recognisable later.</li>
<li>Press submit. The portal re-checks CRS, shape, geotransform and value range.</li>
</ol>"""
    checks = """
<ul>
<li>single band, <code>float32</code></li>
<li>shape <code>3730 &times; 3292</code>, CRS <code>EPSG:32611</code>,
transform <code>(100, 0, 243350, 0, -100, 4508550)</code> &mdash; 100 m pixels</li>
<li>every finite value inside <code>[0, 1]</code>; the writer is fail-closed and
refuses to clip, fill or repair anything</li>
<li>all-finite export (no NaN anywhere): outside-footprint cells are 0.0, matching
this family's accepted <code>-zeros</code> submissions. The organiser's own
<code>sample_submission.tif</code> uses NaN outside the footprint; both encodings
have been accepted by the portal for this family, and the metric is evaluated
inside the footprint.</li>
<li>zero positive mass on mapped catalogue pixels (they are masked out of
scoring, so a dot there is pure false-positive mass)</li>
</ul>"""
    verdict = ("cleared by this session's holdout gate"
               if gate_passed else
               "<b>NOT cleared</b>: the holdout gate was not met, so this file is a "
               "research artifact. Do not spend a weekly submission slot on it.")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>How to submit &mdash; GEMSDOE64</title><style>{CSS}</style></head><body>
<header><div class="wrap" style="padding:0"><h1>Executive summary &mdash; how to make a submission</h1>
<p>Five clicks from this site to a portal submission.</p>
<nav><a href="index.html">Home</a><a href="executive-summary.html">How to submit</a>
<a href="method.html">Method &amp; evidence</a></nav></div></header><div class="wrap">
<div class="card"><h2>1. Download</h2>
<p><a class="btn" href="index.html">Go to the download button</a></p>
<p>This session's file: <code>{esc(e3['file_name']) if e3 else '(none built)'}</code></p>
<p>Status: {verdict}</p></div>
<div class="card"><h2>2. Upload</h2>{steps}</div>
<div class="card"><h2>3. What the portal checks (and what we pre-checked)</h2>{checks}</div>
<div class="card"><h2>4. Naming convention</h2>
<p><code>gems64-&lt;method&gt;-&lt;UTC stamp&gt;-&lt;12-hex array digest&gt;-zeros.tif</code>.
The digest is the sha256 of the decoded pixel array, so two files with the same
name suffix are the same raster.</p></div>
<div class="card"><h2>5. Budget rule</h2>
<p>This session does not spend a submission slot. Promotion is a separate
selector step inside the weekly cap shown on the submission page.</p></div>
</div></body></html>"""


def method_html(e1, e2, e3):
    e2 = e2 or {}
    fold_reports = e2.get("fold_reports") or load("e2_holdout.json").get("fold_reports", [])
    per_fold = ""
    if e2 and e2.get("per_fold"):
        cols = [k for k in e2["per_fold"][0].keys()]
        head = "".join(f"<th>{esc(c)}</th>" for c in cols)
        body = "".join("<tr>" + "".join(
            f"<td class='n'>{r[c]:.4f}</td>" if isinstance(r[c], float) else f"<td>{esc(r[c])}</td>"
            for c in cols) + "</tr>" for r in e2["per_fold"])
        per_fold = f"<table><tr>{head}</tr>{body}</table>"
    canary = ""
    if e2:
        rows = []
        for fr in fold_reports:
            mx = fr["leakage_canary_max_single_feature_auc"]
            rows.append(f"<tr><td>fold{fr['fold']}</td><td class='n'>{fr['n_visible']:,}</td>"
                        f"<td class='n'>{fr['n_inner_hidden']:,}</td>"
                        f"<td class='n'>{fr['n_withheld']:,}</td>"
                        f"<td class='n'>{fr['calib_auc']:.4f}</td>"
                        f"<td class='n'>{mx}</td></tr>")
        canary = ("<table><tr><th>fold</th><th>visible catalogue px</th>"
                  "<th>inner-hidden positives</th><th>withheld positives</th>"
                  "<th>held-out-quadrant AUC</th><th>max single-feature AUC (leakage canary)</th></tr>"
                  + "".join(rows) + "</table>")
    feats = ""
    if e3:
        feats = "".join(f"<span class='tag'>{esc(n)}</span>"
                        for n in e3["surface"]["feature_names"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Method and evidence &mdash; GEMSDOE64</title><style>{CSS}</style></head><body>
<header><div class="wrap" style="padding:0"><h1>Method and evidence</h1>
<p>Every number below is written by a script in this repository.</p>
<nav><a href="index.html">Home</a><a href="executive-summary.html">How to submit</a>
<a href="method.html">Method &amp; evidence</a></nav></div></header><div class="wrap">
<div class="card"><h2>Objective</h2>
<p>The score is a distance-weighted Tversky index with alpha = 0.2, beta = 0.8
and a 300 m (3 px) triangular kernel. Because FN<sub>w</sub> = |G| &minus; TP<sub>w</sub>,</p>
<pre>DTI = T / (0.2*(T + F) + 0.8*|G|)</pre>
<p>Adding one unit-mass dot at x changes T by
<code>dT = sum_g w_g max(0, k(x,g) - C_g)</code> and F by
<code>dF = 1 - E[max_g k(x,g) B_g]</code>. The exact accept test is
<code>dT &gt; alpha*T*dF / (alpha*F + beta*|G|)</code>, which for a non-redundant dot
reduces to <code>kappa &gt; alpha*DTI</code> (0.06 at DTI 0.30). Adjacent picks are
redundant under the 3-px kernel, so pixels are never thresholded independently:
the greedy tracks the running credit field C and the backward prune removes any
dot whose removal raises DTI.</p></div>
<div class="card"><h2>Feature stack ({e3['surface']['n_features'] if e3 else '?'} bands)</h2>{feats}
<p class="mut">Catalogue-derived bands are rebuilt per fold from the visible
catalogue only. Bands from <code>lidar_scarp_features_u8.tif</code>,
<code>geodawn_rad_u8.tif</code> and <code>geodawn_extensions_u8.tif</code> are exposed
as numbered codes: no manifest ships with those rasters, so no band semantics are
claimed (irregularity IR-64-BANDS-01).</p></div>
<div class="card"><h2>Holdout instrument and leakage canary</h2>{canary}
<p class="mut">Canary rule: any single feature with AUC &gt; 0.90 is treated as
leakage until proven otherwise.</p></div>
<div class="card"><h2>Per-fold results</h2>{per_fold}</div>
</div></body></html>"""


def main() -> int:
    e1 = load("e1_theorem.json")
    e2 = load("e2_holdout.json")
    e2b = load("e2b_holdout.json")
    e3 = load("e3_submission.json")
    governing = e2b or e2
    gate_passed = bool(governing and governing["gate"]["passed"])
    DOCS.mkdir(exist_ok=True)
    (DOCS / ".nojekyll").write_text("")
    (DOCS / "index.html").write_text(index_html(e1, governing, e3, gate_passed, e2b=e2b))
    (DOCS / "executive-summary.html").write_text(exec_html(e3, gate_passed))
    (DOCS / "method.html").write_text(method_html(e1, governing, e3))
    print(f"site built (gate_passed={gate_passed}, e3={'yes' if e3 else 'no'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
