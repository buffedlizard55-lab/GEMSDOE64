# GEMSDOE64 · Expected-DTI selection

> **SUBMISSION STATUS: NEGATIVE — DO NOT SUBMIT. No approved TIFF download.**
> A pinned registry prior is positive across the footprint, making the literal
> 70% dot-overlap gate impossible for any nonempty candidate. No production TIFF
> was created and no competition slot was used. This is a measured negative
> result, not a completed training run or a promised leaderboard improvement.

[Project site](https://buffedlizard55-lab.github.io/GEMSDOE64/) ·
[Executive summary](docs/executive-summary.html) ·
[Research findings](docs/research/findings.md) ·
[JSON run card](evidence/run_card.json) ·
[Input receipts](evidence/input_receipt.json)

**Every session starts by reading this README and the run card.**
The starting checkout contained only an 11-byte README; the inherited statement
that a complete training pipeline was ready was not true for this repository.

## What this session delivered

- Pinned audit of source HTML / Git trees for all 62 named sibling repositories;
  no automatic conversion of historical reports into verified competition scores.
- Exact reconstruction of GEMSDOE32 H33's support for education: 2,545 deletions
  from 40,199 predecessor dots, leaving 37,654; zero rule/pixel disagreement.
  No previous raster was copied into a new submission.
- A verified universal literal-overlap blocker and an explicit negative run card.
- Exhaustive synthetic verification of the probability threshold **surrogate**
  and a counterexample to its unrestricted finite-raster expectation claim.
- A bounded exact-mean-DTI forward/backward reference selector, blocked isotonic
  calibration helpers, a whole-component buffered holdout entry point, paired
  bootstrap SEs, a strict publication decision helper, and shared TIFF tools.
- Tests for metric arithmetic, masking, OOF calibration isolation, registry
  saturation, gate failures, invalid numeric output, and serialized TIFF/ZIPs.
- A static GitHub Pages site, submission instructions, auditable source feed,
  and explicit no-download state. Synthetic TIFF fixtures never enter the site.

**Not delivered:** a fitted geological model, real feature canaries, real
HOLDOUT-DTI improvement, a complete decoded registry comparison, a production
submission TIFF, organizer acceptance, or a live leaderboard score. The reference
selector is intentionally bounded; production-scale training/optimization is
future work, not a hidden ready-to-run pipeline.

## Reproduce locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/python scripts/restore_inputs.py
.venv/bin/python scripts/prepare_data.py   # expected exit 2: cache/OOF missing
.venv/bin/python scripts/audit_h33.py --candidate data/registry/g32-h33.tif
.venv/bin/python scripts/verify_synthetic.py
.venv/bin/python scripts/run_preflight.py # stops before training/placement
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

`gh` authentication is used only for allowed GitHub requests; no credentials are
stored. `bash scripts/download_competition_data.sh` restores audit inputs and
then deliberately exits 2 rather than falsely claiming training data readiness.
`python scripts/validate_submission.py FILE.tif` is the shared on-disk preflight;
a local PASS alone never authorizes a download or slot.

Refresh source metadata with `.venv/bin/python scripts/refresh_sources.py`.
Pages automation refreshes the source inventory on its scheduled deployment;
scientific evidence retains its own timestamp. No scheduled job submits files,
trains a new model, or changes a negative run card into a promotion.

## Parallel-session integration

While this PR was running, PR #1 merged another research site into main. Its
research notes, proposed hypotheses and standard-library synthetic probe are
preserved under `research/` and the original root-level pages, labeled as
**historical parallel-session snapshots**. Its original README is saved as
`research/parallel-session-README.md`. Those notes are not independently verified
sources for this session's scientific claims. The active site is `docs/` and
the single current run card is `evidence/run_card.json`; the root entry redirects
to that site. Both runs are negative and neither supplies a submission TIFF.

The prior next steps called for restoration of shared tools and inputs. This
session restored the tools and pinned audit inputs, but not the cached feature
stack or trained OOF artifacts. The measured registry obstruction comes first.
No outside-lane hypothesis from the parallel register was implemented.

## Shared template policy

`src/gems57/` is the single shared metric/evaluator/writer implementation imported
from a pinned 60GEMSDOE commit. See [original hashes](evidence/template_import.json)
and [correction log](docs/research/template-corrections.md). Local corrections
are made there, not in a private lane fork. No changes were pushed to another
repository/branch. Any cross-repository synchronization remains a follow-up.
`src/gems64/` adds only this lane's experimental selection/calibration/policy.
Large data, model outputs and audit-only prior rasters are ignored under `data/`.

## Next session: blockers first

1. Resolve the dense-prior semantics in the shared protocol; no exemption was
   granted here, and a negative result must remain negative until it is.
2. Restore/authenticate the exact shared feature cache and genuine buffered OOF
   model artifacts; do not confuse cache receipts with available bytes.
3. Run feature-only canaries and a single preregistered nested blocked experiment.
4. Check ≥32 plausible model truth draws, calibration and provenance; compare
   exact-gain placement with spacing/MCLP on the same surface and folds, then
   require >2 paired block-bootstrap SEs and a comparable historical-best win.
5. Only after complete registry, format, and integrity checks may a unique TIFF
   be offered. Slot selection is separate, within the actual portal cap.

---

# Project prompt / standing requirements

The original request is preserved here as a **consolidated operating charter**:
repeated “review / no hallucinations / verify line by line” sentences and repeated
URLs are consolidated, not represented as new evidence. The reported-results
list below preserves the supplied artifact names and values. Read this section
every time work resumes.

## Highest urgency

> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A
> PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST
> GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO
> DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There must be an easy-to-download submission TIFF, **only when the stated
promotion gate is met**. Its eligibility belongs at the very beginning of the
site and executive summary. Never present a prior TIFF or a synthetic fixture
as a new submission. If gates fail, log the negative result and offer no TIFF.

## Assigned lane (original method paragraph)

Expected-DTI-optimal selection. Replace heuristic spacing with a decision rule
on a calibrated surface. For a Tversky-family score with α+β=1, adding a pixel
raises the expected score when its calibrated probability exceeds α × the optimal
score. For DTI (α=0.2) that is about 0.06 at DTI 0.30. This extends Lipton, Elkan &
Narayanaswamy (ECML-PKDD 2014: the F1-optimal threshold is half the optimal F1), so
verify it numerically on synthetic rasters first. The 3-px kernel makes adjacent
picks redundant, so don’t threshold independently. Calibrate by isotonic regression
on spatially blocked, buffered out-of-fold predictions. Treat ensemble, TTA and
MC-dropout outputs (jittered 1–2 px) as ≥32 plausible truth rasters. Greedily add
the ridge-candidate pixel with the largest mean DTI gain under the repo’s exact
kernel metric, then prune backward until marginal gain ≤ 0. Gate: beat the current
spacing/MCLP placement on the same surface by >2 block-bootstrap SEs. Finish:
normalize to [0,1]; write a float32 EPSG:32611 100 m GeoTIFF (NaN only outside the
footprint); pass validate_submission.py; run a hash/pixel-agreement check against
all prior rasters; offer the download only if the gate is met, else log the
negative result.

**Scientific correction from this session:** the simple probability rule is exact
for the ratio-of-expected-counts surrogate, not generally for the expectation of
a finite random ratio. The synthetic counterexample and exact-draw selector are
linked above; the prompt's conjecture is not silently treated as a theorem.

## Parallel-run protocol — read first

1. **LANE:** Stay in the single assigned method. If surface rank-correlation with
   any registry raster exceeds 0.90, or >70% of dots lie within 3 px of one prior's
   dots, log a duplicate and stop. Check before placement and on final dots.
2. **REUSE, DON'T REBUILD:** Use the shared cached feature stack,
   evaluate_holdout.py and submission_writer.py. Withhold whole fault segments
   with a buffer. Derive catalogue features only from visible faults, mask
   visible faults pixel-exactly, pool DTI at α=.2, β=.8 with the 300 m triangular
   kernel. Fix shared tools once, report corrections, never maintain a private fork.
3. **EVIDENCE LABELS:** Scientific performance numbers must be HOLDOUT-DTI
   (evaluator version, withheld positive count, 95% CI) or ORGANIZER-CONFIRMED
   (copied from a submission-page receipt). A projection is never a score.
   Historical prompt quotations and synthetic arithmetic are not eligible scores.
4. **LEAKAGE CANARY:** Test each feature alone before trusting results; AUC >.90
   means leakage until proven otherwise.
5. **RUN CARD:** End with one JSON card containing hypothesis, mechanism, a named
   non-fault mimic, holdout DTI/CI, registry correlation/overlap, raster SHA256,
   validator output, submission name and ≤140-character note, verdict promote or
   negative. Missing evidence is null, not fabricated. Negative results matter.
6. **BUDGET:** Stop after 3 experiments or 2 hours. Do not choose or spend a real
   submission slot. Promotion to a slot is a separate selector step, within the
   weekly cap shown on the submission page.

## Research and competition objective

- Review the repository, previous-session next steps, prior results and the
  complete linked competition prompt before implementing. Understand why the
  GEMSDOE32 H33 result reported in the prompt was stronger and whether a new,
  unique strategy can do better. No forecast may be written as a measured score.
- Generate 3–5 ranked geological hypotheses before implementation. For each name
  the exact layers, physical transform/signature, why it might catch an unmapped
  fault rather than repeat a catalogue feature, how it differs from existing
  work, its non-fault mimic, expected opportunity and implementation cost.
- Validate the leading candidate on a spatially blocked holdout before a weekly
  slot; do not submit something that has not beaten a comparable holdout best.
- If an idea needs new data, identify a free official source and actually check
  availability before calling it viable. Store auditable knowledge and links for
  future geothermal research. Ground contrarian ideas in physics and evidence;
  distinguish fault detection from geothermal vent/reservoir confirmation.
- Work autonomously with no required manual inputs in this run. State limitations,
  blocked accesses, unverifiable claims and irregularities instead of inventing
  answers. No credentials should be requested or stored in chat.
- Follow the competition overview, problem description, about/resources, data,
  reference solution, leaderboard and supplied PDF. Use official verified
  sources for claims, with links for manual review. Read the actual data before
  relying on inherited claims about what the pipeline or GPU requires.

## Submission format and user-visible workflow

The user reported an earlier portal rejection: **“Predicted values must be in
range [0, 1]”.** The rejected TIFF was not attached, so its cause must not be
invented. The submission-page text supplied by the user says a single-band
GeoTIFF (.tif), or a ZIP containing one GeoTIFF, must match the template CRS,
shape and geotransform. Give a unique submission name and a short distinguishing
comment. Make it obvious whether download/submission is allowed. Provide an
executive-summary subpage explaining the exact steps; do not expose old or
quarantined artifacts as recommended downloads.

## Data acquisition requests and inherited assertions

The prompt asked to execute `bash scripts/download_competition_data.sh` and
`python scripts/prepare_data.py` autonomously, place data under `data/`, then
train → infer → validate. It asserted data placement was the single remaining
blocker and a GPU was needed. Those assertions must be verified for the current
checkout, not copied into a success report. It reported a prior DrivenData
login redirect; this runtime did not recheck that redirect. The original
DropBox/GDR/PDF links are retained below, but were not directly fetched under
this runtime's network policy.

## Website, automation and project completion

Create a clean, simple, user-friendly GitHub Pages site with submission status
at the top, executive instructions, audit table, source links, and an up-to-date
source feed that does not imply refreshed scientific validation. Verify working
code and published claims, flag irregularities, and do not hallucinate.

Do three passes: (1) implement and verify; (2) find/fix bugs, missing requirements,
incorrect assumptions and edge cases; (3) recheck against the original request,
improving accuracy, reliability, completeness and code quality. Explain remaining
limitations instead of claiming unmet requirements are complete. Create a pull
request, merge it to main, and leave concrete next-session work.

## Core values from the prompt

**Maximize P(Win)** — weigh tradeoffs and evidence, assess risk, set aside emotion,
and choose the path most likely to succeed. In this project, spending scarce
slots on unverified or duplicate rasters undermines that objective.

**Own the Outcome** — own results end to end. Act when problems can be fixed;
treat success and failure as evidence. A documented negative is preferable to
an unsafe download or a fictitious high score.

## All user-reported prior results (unverified historical transcription)

These entries are **not HOLDOUT-DTI and not ORGANIZER-CONFIRMED**. They are
retained solely as prompt history until receipts exist. Missing entries remain
missing. The prompt alternately calls 0.3195 and 0.3774 the current leader;
neither has been verified here. See `docs/data/reported_results.json`.

| Repository | Supplied submission name | User-reported value |
|---|---|---|
| [GEMSDOE](https://buffedlizard55-lab.github.io/GEMSDOE/docs/index.html) | `gems-submission-20260925T001403Z-7f00890a` | 0.1563 |
| [6GEMSDOE](https://buffedlizard55-lab.github.io/6GEMSDOE/) | `gems6_hgb88-topk03_33cec71ff0` | 0.0286 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | `pindrop-v4-nodes-20260925T152420Z-f347b70daa` | 0.1193 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | `pindrop-v4-discovery-20260925T152423Z-37f9d5b855` | 0.0830 |
| [GEMSDOE3](https://buffedlizard55-lab.github.io/GEMSDOE3/docs/index.html) | `pindrop-v4-ridge-20260925T152422Z-4e03fc9705` | 0.1152 |
| [GEMSDOE2](https://buffedlizard55-lab.github.io/GEMSDOE2/docs/index.html) | `gemsdoe2-dual-family-union-20260925T160406Z-f68e590f` | 0.1560 |
| [GEMSDOE4](https://buffedlizard55-lab.github.io/GEMSDOE4/) | `gems-submission-20260926T163915Z-237f0063` | 0.0343 |
| [5GEMSDOE](https://buffedlizard55-lab.github.io/5GEMSDOE/docs/index.html) | `gems-submission-20260926T175114Z-7f00890a` | 0.1563 |
| [7GEMSDOE](https://buffedlizard55-lab.github.io/7GEMSDOE/) | `lidarscarp-ridge-top2pct-36c3a3f341c8` | 0.1461 |
| [8GEMSDOE](https://buffedlizard55-lab.github.io/8GEMSDOE/) | `Hedge-v2_submission` | 0.1563 |
| [GEMSDOE9](https://buffedlizard55-lab.github.io/GEMSDOE9/docs/index.html) | `2314b599` | 0.0107 |
| [11GEMSDOE](https://buffedlizard55-lab.github.io/11GEMSDOE/docs/index.html) | `gems-structural-area06-v1` | 0.0202 |
| [12GEMSDOE](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html) | `r7-nms3-dem10-scarp_0c9199f14e62` | 0.1294 |
| [12GEMSDOE](https://buffedlizard55-lab.github.io/12GEMSDOE/docs/index.html) | `r7-nms3-dem10-scarp_0c9199f14e62_allfinite` | 0.1294 |
| [15GEMSDOE](https://buffedlizard55-lab.github.io/15GEMSDOE/docs/index.html) | `gems-tso1-20260929T005627Z-conj_alteration_mag` | 0.0782 |
| [14GEMSDOE](https://buffedlizard55-lab.github.io/14GEMSDOE/docs/index.html) | `GEMS_r5-geom-horse-ensemble_20260929T154852Z_ccbe1de0_site_e96e942f` | 0.0020 |
| [17GEMSDOE](https://buffedlizard55-lab.github.io/17GEMSDOE/) | `17GEMSDOE_F-ensemble-2pct_20260930T050626Z` | 0.0187 |
| [18GEMSDOE](https://buffedlizard55-lab.github.io/18GEMSDOE/) | `H19-C_20260930T212401Z_c11e495e` | 0.0297 |
| [19GEMSDOE](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html) | `h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan` | 0.1894 |
| [19GEMSDOE](https://buffedlizard55-lab.github.io/19GEMSDOE/docs/index.html) | `h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan` | 0.1922 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | `h16-continuation-20260927T065521077735Z-3431b83c7c` | 0.0461 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | `h20-dem10-scarp-thin-20260927T155223039488Z-ffc91a1686` | 0.0921 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | `H25-ctx-ridge-20260927T232947704150Z-6452ae1d00` | 0.1280 |
| [GEMSDOE10](https://buffedlizard55-lab.github.io/GEMSDOE10/) | `h28-dotted-ridge-20260928T020256236880Z-6452ae1d00` | 0.1839 |
| [13GEMSDOE](https://buffedlizard55-lab.github.io/13GEMSDOE/) | `20261001_r13-lattice-s5_v2_nan-outside` | 0.0904 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | `h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan` | 0.1855 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | `h18-3a-topo-geophys-x-complexity-prior-20260930-c502dfab-nan` | 0.0976 |
| [16GEMSDOE](https://buffedlizard55-lab.github.io/16GEMSDOE/docs/index.html) | `h18-4-usgs-geologic-map-faults-gap-20260930-aef8f42c-nan` | 0.0360 |
| [GEMSDOE21](https://buffedlizard55-lab.github.io/GEMSDOE21/) | `h19-4-reference-20260930-691e4dfa` | 0.1894 |
| [20GEMSDOE](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html) | `h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan` | 0.1890 |
| [20GEMSDOE](https://buffedlizard55-lab.github.io/20GEMSDOE/docs/index.html) | `h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan` | 0.1859 |
| [GEMSDOE22](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html) | `h23-a-dti-optimal-emission-6pct-20261002-e2ec4b49-nan` | 0.1002 |
| [GEMSDOE22](https://buffedlizard55-lab.github.io/GEMSDOE22/docs/index.html) | `h23-b-dti-optimal-emission-10pct-20261002-86176698-nan` | 0.0748 |
| [GEMSDOE23](https://buffedlizard55-lab.github.io/GEMSDOE23/) | `h30-arrangement-matched-habitat-20261002-0d4e02e8-nan` | 0.1352 |
| [GEMSDOE24](https://buffedlizard55-lab.github.io/GEMSDOE24/) | `h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan` | 0.2477 |
| [GEMSDOE25](https://buffedlizard55-lab.github.io/GEMSDOE25/) | `dotted-h19-5-d2-8-20261002-e56ea318af89-nan` | 0.2600 |
| [GEMSDOE26](https://buffedlizard55-lab.github.io/GEMSDOE26/) | `dilcond-oof-v1-20261003-47629f496133-nan` | 0.1223 |
| [GEMSDOE27](https://buffedlizard55-lab.github.io/GEMSDOE27/) | `topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan` | 0.2449 |
| [GEMSDOE30](https://buffedlizard55-lab.github.io/GEMSDOE30/) | `d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca` | 0.2600 |
| [GEMSDOE31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/index.html) | `h27-4-solo-d28-20261004-8acb75e1-nan` | 0.2708 |
| [GEMSDOE33](https://buffedlizard55-lab.github.io/GEMSDOE33/) | `h33d-analog-tip-stepover-r30-20261004-cb490425926e` | 0.2632 |
| [GEMSDOE34](https://buffedlizard55-lab.github.io/GEMSDOE34/docs/index.html) | `h34-scatter-q50-arr-matched-20261004T223317Z` | 0.0778 |
| [GEMSDOE35](https://buffedlizard55-lab.github.io/GEMSDOE35/docs/index.html) | `h35-06-aaa86efb25-20261004T225420098147Z-candidate` | 0.0418 |
| [GEMSDOE36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/index.html) | `anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros` | 0.2750 |
| [GEMSDOE37](https://buffedlizard55-lab.github.io/GEMSDOE37/) | `h6-physics-dotted-80k-20261005T055000Z-0bef9211631c` | 0.1193 |
| [GEMSDOE38](https://buffedlizard55-lab.github.io/GEMSDOE38/docs/index.html) | `D-step-3p0-07pct-tipProt-20261005-ecfbf59e2b48-zero` | 0.0763 |
| [GEMSDOE42](https://buffedlizard55-lab.github.io/GEMSDOE42/docs/index.html) | `xscale-worm-persistence-20261006T000541Z-nan` | 0.0581 |
| [GEMSDOE43](https://buffedlizard55-lab.github.io/GEMSDOE43/docs/index.html) | `sup01-hgb21-sep40-n40000-20261006-bc2e4e9a8d6f-nan` | 0.0424 |
| [GEMSDOE45](https://buffedlizard55-lab.github.io/GEMSDOE45/) | `h51-km-faultzone-20261006-zeros` | 0.0106 |
| [GEMSDOE49](https://buffedlizard55-lab.github.io/GEMSDOE49/) | `gate_ortho_w0.25-40k-20261006T213721Z-nan` | 0.2376 |
| [GEMSDOE32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) | `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | 0.2778 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan` | 0.2708 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan` | 0.2649 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan` | 0.2710 |
| [GEMSDOE28](https://buffedlizard55-lab.github.io/GEMSDOE28/) | `h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan` | 0.2707 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `efd28-repro-20261003-1cc7dc534d51-nan` | 0.2600 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `repo-c0-habitat-emission-20261003-a4d439b07426-nan` | 0.0041 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan` | 0.0512 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `wormrank-d28-20261003-59dcaf6dd11d-zeros` | 0.2560 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `wormsurv-filter-20261003-921f10960d6e-zeros` | 0.0532 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `xfit-c0-habitat-20261003-ca879db0089a-zeros` | 0.0439 |
| [GEMSDOE29](https://buffedlizard55-lab.github.io/GEMSDOE29/docs/index.html) | `xfit-h41-union-qfaults-20261003-9edb34b99e3a-zeros` | 0.0356 |
| [GEMSDOE46](https://buffedlizard55-lab.github.io/GEMSDOE46/) | `r11f-scarp-radiometric-fusion-00e049b51218-zeros` | 0.1589 |
| [GEMSDOE46](https://buffedlizard55-lab.github.io/GEMSDOE46/) | `r12-scarp-rad-concordance-23e807e2de9f-zeros` | 0.0843 |
| [GEMSDOE39](https://buffedlizard55-lab.github.io/GEMSDOE39/) | `h40-e-disc-h40e-30k-zeros` | 0.0339 |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | `h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1` | 0.0355 |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | `h8-euler-lineament-depthcluster-20261006-785c4f5d5ce1-hard` | 0.0397 |
| [GEMSDOE40](https://buffedlizard55-lab.github.io/GEMSDOE40/docs/index.html) | `h45-eulerdepthreadcluster-20261006-f28e5cff6826-zeros` | 0.0984 |
| [GEMSDOE41](https://buffedlizard55-lab.github.io/GEMSDOE41/) | `h42-submission-primary` | 0.0245 |
| [GEMSDOE44](https://buffedlizard55-lab.github.io/GEMSDOE44/docs/index.html) | `h46-twostageAB_20261006T160000Z_b0cfe956-zeros` | 0.0715 |
| [GEMSDOE47](https://buffedlizard55-lab.github.io/GEMSDOE47/) | `h60-lidarscarp-s2p0-20261007-nanoutside` | 0.0430 |
| [GEMSDOE48](https://buffedlizard55-lab.github.io/GEMSDOE48/docs/index.html) | `h59-cover-ds-belief-b2xh33d-20261008T184547Z-b79c4c61d8d8` | 0.2296 |
| [GEMSDOE50](https://buffedlizard55-lab.github.io/GEMSDOE50/) | `h59-sharpened-scarp-scatter-90k-20261007T171954Z-allfinite` | 0.0764 |
| [GEMSDOE51](https://buffedlizard55-lab.github.io/GEMSDOE51/docs/index.html) | `h53-twostage-20261008T040951Z-9a0b32c871` | 0.1047 |
| [GEMSDOE52](https://buffedlizard55-lab.github.io/GEMSDOE52/) | `h97b-candidate` | not supplied |
| [GEMSDOE53](https://buffedlizard55-lab.github.io/GEMSDOE53/docs/index.html) | `h8-tiprelay-ridgeconcord-pr2-n80000-20261009-49bec522-zeros` | 0.0159 |
| [GEMSDOE54](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/index.html) | `h54c-manifest-edge-20261009T025732Z-73454bc5` | 0.0449 |
| [55GEMSDOE](https://buffedlizard55-lab.github.io/55GEMSDOE/docs/index.html) | `tensor_full-n16000-sep3-20261009T211747Z-nan` | 0.0290 |
| [56GEMSDOE](https://buffedlizard55-lab.github.io/56GEMSDOE/docs/index.html) | `h56-final-dotted-ridge-d2p8-20261009T190421Z` | 0.0658 |
| [57GEMSDOE](https://buffedlizard55-lab.github.io/57GEMSDOE/docs/index.html) | `h57r-joint-strata-38000-20261010T214547Z-00cf5b2066f1-zeros` | not supplied |
| [58GEMSDOE](https://buffedlizard55-lab.github.io/58GEMSDOE/docs/index.html) | `ml-binary-ridge-20261012T000000Z` | not supplied |
| [59GEMSDOE](https://buffedlizard55-lab.github.io/59GEMSDOE/docs/index.html) | `h59j-coherence-consensus-dotted-20261011T043000Z` | not supplied |
| [60GEMSDOE](https://buffedlizard55-lab.github.io/60GEMSDOE/docs/index.html) | `not supplied` | not supplied |
| [61GEMSDOE](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html) | `h61a-basement-step-20000dots-20261011T012029Z-eb2ae4bb024b-zeros` | not supplied |
| [61GEMSDOE](https://buffedlizard55-lab.github.io/61GEMSDOE/docs/index.html) | `h61o-vardepth-none-40000dots-20261011T160711Z-28d4fac611ea-zeros-zeros` | not supplied |
| [62GEMSDOE](https://buffedlizard55-lab.github.io/62GEMSDOE/docs/index.html) | `not supplied` | not supplied |

## Original research/manual-review links

- [Competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/) — not-fetched-network-policy.
- [Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — not-fetched-network-policy.
- [About and resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/) — not-fetched-network-policy.
- [Data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — not-fetched-network-policy.
- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — not-fetched-network-policy.
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — primary-source-read.
- [GeoDAWN magnetic/radiometric survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — not-fetched-network-policy.
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) — not-fetched-network-policy.
- [GDR INGENIOUS data](https://gdr.openei.org/submissions/1391) — not-fetched-network-policy.
- [Competition PDF supplied by user](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — not-fetched-network-policy.
- [CRS reference](https://epsg.io/32611) — not-fetched-network-policy.
- [Tversky background](https://en.wikipedia.org/wiki/Tversky_index) — not-fetched-network-policy.
- [Lipton et al. F1 thresholding](https://arxiv.org/abs/1402.1892) — not-fetched-network-policy.

### User-provided data links (not downloaded directly in this run)

- [GEMS_96647.pdf on Dropbox](https://www.dropbox.com/scl/fi/aemhtutjgcp6tr3tint94/GEMS_96647.pdf?rlkey=rek210cj2smnmzb8n0sla1vmd&st=wz4kofki&dl=0)
- [example_submission.tif](https://www.dropbox.com/scl/fi/6rgvnuady818ol8yqgis4/example_submission.tif?rlkey=kbykilvau066xuogoosbf4cq8&st=8junzdyw&dl=0)
- [existing_faults.tif](https://www.dropbox.com/scl/fi/t7fyt03qdh9egyme0itwo/existing_faults.tif?rlkey=yiao96uluqdkipf0h5vju71jf&st=rnino7ya&dl=0)
- [gems-geodawn-numerical-features.tif](https://www.dropbox.com/scl/fi/3vz9o0wwavi26xaeoxlwr/gems-geodawn-numerical-features.tif?rlkey=je8d8fepqfbst9lnwsq9rkplu&st=zj1lag1r&dl=0)
- [Digital-elevation-model-links-JSON.pdf](https://www.dropbox.com/scl/fi/ig0mban712ns1atphgphe/Digital-elevation-model-links-JSON.pdf?rlkey=zm77f1vbtt2if8hlruymptnu3&st=srhhir10&dl=0)

No organizer credentials, private data entitlement, official data identity, live
weekly cap, full organizer registry, or organizer submission receipt was verified.
This repository stores uncertainty explicitly instead of silently filling it.
