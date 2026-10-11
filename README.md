# GEMSDOE64 — evidence-gated expected-DTI selection

> **SESSION START:** Read this README and [`evidence/run_card.json`](evidence/run_card.json) before any work. The active Pages site is built in [`docs/`](docs/); scientific hypotheses and limitations are in [`docs/research/findings.md`](docs/research/findings.md) and [`research/limitations_and_next.md`](research/limitations_and_next.md).

## Current decision: **NEGATIVE — DO NOT SUBMIT**

**No production TIFF was created, no download is approved, and no competition slot was used.** The run stopped before training or candidate placement because a pinned registry witness's three-pixel neighborhood covers every allowed off-catalogue cell. Under the inherited rule—every positive finite prediction pixel counts as a dot—every nonempty candidate would have 100% of its dots within three pixels of that prior, exceeding the 70% overlap limit. The stop certificate is [`evidence/registry_blocker.json`](evidence/registry_blocker.json); the machine-readable decision is [`evidence/run_card.json`](evidence/run_card.json).

This is a protocol/registry negative, not a failed or completed geology model. The witness comes from a public sibling-project artifact, not an organizer receipt. The full byte/pixel audit of every prior and the organizer's complete registry are **not** complete. No candidate surface or final dot set exists to compare. A different interpretation of dense priors requires an explicit protocol change; do not exempt one privately.

The official competition files, shared feature-cache bytes, buffered OOF predictions, ensemble/TTA/MC-dropout checkpoints, and their provenance are not present in this checkout. The upstream audit records include hashes/metadata for third-party bridge inputs, but those are not authenticated competition data and are not currently in `data/`. A feature-cache receipt is not the feature cache: see [`evidence/feature_cache_receipt.json`](evidence/feature_cache_receipt.json) and [`evidence/data_preflight.json`](evidence/data_preflight.json). The receipt/sample footprint difference is a **metadata warning**, not a diagnosis of the user's rejected TIFF.

There are no `HOLDOUT-DTI` results (the holdout was not run), no `ORGANIZER-CONFIRMED` score, no candidate hash, no production validator result, and no download. User/owner leaderboard numerals without an organizer receipt are deliberately not reproduced as scores; see [`research/score_review.md`](research/score_review.md).

## Round H64 (branch `arena/9c869219-gemsdoe64`, 2026-10-11) — expected-DTI selector **built, measured, NEGATIVE**; one downloadable research raster

This round did what the standing brief asks and got a measurable answer. **Verdict: negative.
Zero submission slots used.** Run card: [`evidence/run_card_h64.json`](evidence/run_card_h64.json) ·
lane page: [`docs/research/lane64.html`](docs/research/lane64.html)

**A GeoTIFF was generated** — `artifacts/gems64-h64-dtiopt-greedy-prune-calibrated-20261011T212556Z-54be1965c2f8-zeros.tif`
(52,665 dots, float32, EPSG:32611, 100 m, values in `[0,1]`, no NaN anywhere, zero mass on
mapped catalogue pixels, sha256 `a8c5fa733053c6f98bbe859ec95c429c5632f2b4ff30a955846de71196990a82`).
**OK TO SUBMIT: NO, and no download is offered.** The brief says to offer the download only if
the gate is met, else log the negative result; the gate failed, so the artifact is kept in the
repository as evidence rather than published on the site (this also keeps the repo's fail-closed
publisher policy in `tests/test_policy.py` intact). Every local format check passes
(`python scripts/check_submission.py artifacts/<file>.tif`).

| experiment | result |
|---|---|
| **E1** decision rule on synthetic rasters | bar `alpha*DTI` = 0.06 at alpha 0.2/DTI 0.30 (empirical 0.061, monotone); Lipton generalisation 8.2 % rel. error at alpha 0.5, 4.9 % at alpha 0.2; greedy+prune hit the exhaustive optimum on 3/3 rasters (gap 0.0 over 8,192 subsets); mean-field DTI within 1.6 SE of a 64-draw plausible-truth Monte Carlo |
| **E2** holdout, 11,321 withheld positives | pooled HOLDOUT-DTI `nms_2p8` **0.1333** vs `dtiopt` 0.0707; Δ = −0.0625, SE 0.0021, z −30.1 → **gate FAIL** |
| **E2b** after the exact negative-sub-sampling odds correction `w = r·p/(r·p+1−p)` | calibration fixed (mean-field 0.087–0.095 vs realised 0.042–0.091, was 0.33 vs 0.05); `nms_2p8` **0.1139** vs `dtiopt` 0.0636; Δ = −0.0504, SE 0.0030, z −16.6 → **gate FAIL** |
| **uniqueness** full 62-raster registry scan | max &#124;Spearman&#124; **0.0403**, worst Jaccard **0.025**, byte- and pixel-unique; 3-px overlap 0.9987 against `calib_r13lattice_00904` only |

**Why the lane lost.** The greedy concentrates dots on the highest-probability pixels, which
cluster along the visible catalogue, while the withheld truth is spatially displaced from it.
A spread-out covering (fixed 2.8-px spacing) recovers more distinct truth pixels per dot.
Probability-optimal placement only beats spacing when the surface is unbiased — and this one
is not. That is a mechanism, not a tuning miss, and it is consistent with every 0.26–0.28
submission in this family being a *spaced* emission rather than a thresholded one.

**IR-64-LATTICE-01** (corroborates this repo's existing registry blocker): the literal 70 %
3-px overlap rule fails only against the dense lattice comparator, whose 3-px halo covers the
whole off-catalogue footprint, so it traps *every* sparse candidate — while Spearman (0.0005),
Jaccard (0.0084) and reverse overlap (0.157) show the placement is unrelated to it. Owner
decision needed; not waived here.

**IR-64-BANDS-01:** `lidar_scarp_features_u8.tif`, `geodawn_rad_u8.tif` and
`geodawn_extensions_u8.tif` ship no manifest, so their bands are used as numbered codes and no
physical meaning is claimed.

Reproduce this round:

```bash
export GEMS64_EXTERNAL=/path/to/60GEMSDOE/data/external
export GEMS64_REGISTRY=/path/to/60GEMSDOE/registry
python3 scripts/e1_theorem.py && python3 scripts/e2_holdout.py \
  && python3 scripts/e2b_prior_correction.py && python3 scripts/e3_build_submission.py \
  && python3 scripts/check_uniqueness.py artifacts/<file>.tif \
  && python3 scripts/make_run_card.py && python3 scripts/build_site_lane64.py
```

## Objective and core values

Build an auditable research project to improve the chance of identifying previously unmapped faults relevant to geothermal resources. **Maximize P(Win)**: preserve scarce submissions and make choices from properly blocked evidence. **Own the Outcome:** record blockers and failures, correct defects, and never turn an owner claim, projection, or synthetic result into a competition score.

The competition maps faults in the GeoDAWN region. It uses a distance-weighted Tversky metric with a triangular spatial kernel. The exact shared implementation is authoritative for local evaluation. Organizer clarifications say the known-fault exclusion is pixel-exact; nearby unmasked pixels remain scoreable, and new geometry can occur near known traces. A broad catalogue buffer is not automatically free.

## Required method lane — expected-DTI-optimal selection

Stay in the assigned expected-DTI-optimal-selection lane; do not implement an outside-lane feature or private evaluator.

1. First verify the threshold intuition on synthetic rasters. The independent-pixel threshold is valid for a ratio-of-expected-counts surrogate or a nonredundant special case; it is **not** a general rule for the expectation of a finite spatial DTI ratio. The exhaustive synthetic evidence is in [`evidence/synthetic_verification.json`](evidence/synthetic_verification.json); the earlier compact probe is [`research/expected_dti_probe.json`](research/expected_dti_probe.json). Neither is a holdout result.
2. Calibrate probabilities with isotonic regression on spatially blocked, buffered out-of-fold predictions. Preserve genuine ensemble/TTA/MC-dropout variation, including non-wrapping one-to-two-pixel jitter, as at least 32 plausible binary truth rasters. Duplicated jitter alone is not epistemic uncertainty.
3. Greedily add ridge candidates by their **mean exact DTI marginal gain** over the plausible truth rasters, then backward-prune while marginal gain is nonpositive. Re-evaluate gains; do not assume finite-ratio DTI is submodular or substitute independent thresholding.
4. Compare the result with the incumbent spacing/MCLP selection on the same surface and folds. Promote only if the gain is greater than two paired spatial block-bootstrap standard errors and a comparable prior best is beaten.
5. Test every feature alone as a leakage canary; holdout AUC above 0.90 is leakage until explained. Hide whole fault components with a buffer, derive catalogue features from visible faults only, and mask visible faults pixel-exactly.
6. Compare against every declared registry raster before placement and on final dots. Rank correlation above 0.90 or more than 70% of candidate dots within three pixels of a prior is a duplicate/lane-drift stop. Require a complete byte/hash and decoded-pixel check before any promotion.

The shared metric/holdout/writer/validator implementation is in [`src/gems57/`](src/gems57/), imported from a pinned 60GEMSDOE commit; original hashes and corrections are recorded in [`evidence/template_import.json`](evidence/template_import.json) and [`docs/research/template-corrections.md`](docs/research/template-corrections.md). Lane-specific selection/calibration helpers are in [`src/gems64/`](src/gems64/). These tools are present; the real cached stack and model outputs are not. Do not fork the shared evaluator or writer.

## Current evidence and limits

- A single pinned registry witness's three-pixel neighborhood covers the entire allowed off-catalogue domain under the current literal positive-pixel/dot definition. That is enough to stop this run, but it is **not** a complete registry audit or a candidate correlation measurement.
- The shared 35-channel feature-cache receipt points to an ephemeral path and its bytes are unavailable. Its declared footprint differs from the sample's measured finite footprint. Never use the narrower receipt mask to introduce NaNs inside a valid submission footprint.
- The sample/catalogue/prior hashes in the input receipts came through public third-party GitHub bridges; they do not authenticate official DrivenData inputs. The DrivenData data page previously redirected to login; no gated files or credentials were obtained.
- An H33 predecessor comparison reconstructed an owner's pruning rule from public raster artifacts. It is an artifact audit only; no organizer receipt links that raster to a score, and no score causality is inferred. See [`evidence/h33_forensics.json`](evidence/h33_forensics.json).
- The active ranked hypotheses are the four **in-lane** cached-feature ideas in [`docs/research/findings.md`](docs/research/findings.md). They are not tested or globally novel. Source reconnaissance is kept separate from the active method lane.
- No production model, feature-alone canary, buffered holdout, `HOLDOUT-DTI`, 95% CI, candidate TIFF, submission receipt, or `ORGANIZER-CONFIRMED` score exists for this run.

## Source reconnaissance (checked 2026-10-11; no data downloaded)

These checks establish catalog/portal metadata only—not local file integrity, exact competition-polygon coverage, permission for a particular use, or holdout benefit.

- The Trugman/Zenodo relocated-earthquake record is open under CC-BY-4.0 and lists `nvreloc_catalog_newmag.txt` and `station_terms.txt`; neither file nor its schema was inspected locally. Exact competition-area event coverage remains unknown.
- The USGS GeoDAWN ScienceBase record describes airborne magnetic/radiometric surveys and lists Area 1/Area 2 GeoTIFF grid archives and survey outlines. The files were not downloaded or hashed; exact competition-polygon overlap, raster metadata, and file-level usage terms remain unchecked.
- The USGS 3DEP 1-meter index query using GeoDAWN's coarse bounding rectangle returned 22 project polygons. That is **not** a tile count or exact AOI overlay; complete lidar coverage is not established.
- The USGS Great Basin heat-flow record is marked CC0, but its files and exact AOI coverage were not checked. Copernicus describes free Sentinel-data access, but no AOI acquisition query was performed. GDR 1391 returned “No submission found”; do not treat the linked INGENIOUS data as obtainable from that record.
- The full source register and query/record links are in the active [`docs/sources.html`](docs/sources.html) and [`docs/data/source_catalogue.json`](docs/data/source_catalogue.json). The data checks above are not active model hypotheses and were not integrated.

## Run budget and artifact policy

Stop after at most three competition experiments or two hours. No experiment may spend a weekly submission slot. Promotion to a real slot is a separate authorized selector decision. The run card must record a named non-fault mimic, holdout DTI and 95% CI, evaluator version and withheld-positive count, registry correlation/overlap, raster SHA-256, validator output, a unique submission name and note (at most 140 characters), and a `promote` or `negative` verdict. Missing evidence is null, not zero or inferred.

Only create/offer a TIFF if every holdout, uniqueness, provenance, and exact-file gate passes: single-band float32; values in [0,1]; EPSG:32611; 100 m; exact template grid/bounds/shape/transform; NaN only outside the footprint; shared validator passes; and file hash plus decoded pixels agree with the submitted registry comparison. The site must keep the negative status and offer **no TIFF** while any gate is unresolved.

## Reproduction and site

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-lock.txt
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_synthetic.py
.venv/bin/python scripts/run_preflight.py
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

`run_preflight.py` is expected to stop before training/placement while cache and OOF artifacts are missing. `scripts/download_competition_data.sh` restores only public audit inputs and then fails closed; it does not bypass authentication or fetch gated competition data. `scripts/validate_submission.py FILE.tif` is a local format preflight only; a local pass never authorizes upload.

The active site is published from `docs/` through the existing Pages workflow. Its top page is the submission-readiness summary, with the executive upload guide, research findings, and source register one click away. The scheduled source refresh reads the public GitHub sibling inventory; it does not scrape/cache the DrivenData leaderboard, train a model, change a verdict, or submit a file.

## Next session — blockers first

1. Resolve dense-prior semantics explicitly in the shared protocol; until then retain the universal-overlap negative gate. No private exemption.
2. Restore/authenticate the exact shared feature-cache bytes, buffered OOF predictions, checkpoints, and provenance; verify sample/feature footprints and preserve the official submission mask.
3. Run the feature-alone leakage canaries, then one preregistered nested buffered component holdout using the shared evaluator. Keep at least 32 genuine plausible truth rasters.
4. Compare exact-gain placement with spacing/MCLP on the same calibrated surfaces and folds; require the specified paired-bootstrap margin and complete registry/hash/pixel checks.
5. Only after every gate passes may a unique TIFF be written and offered. Retain the negative site state otherwise.

## Core values

- **Maximize P(Win)**: prioritize measured lift on the right holdout and preserve scarce submission opportunities.
- **Own the Outcome:** preserve negative results, correct misleading provenance, and never promote a projection as a score.

---

## Standing brief (verbatim, read at the start of every session)

> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
> UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST
> BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION. There should
> be an easy to download submission tif file as described by the prompt. Read the entire prompt.
>
> **Lane — Expected-DTI-optimal selection.** Replace heuristic spacing with a decision rule on a
> calibrated surface. For a Tversky-family score with α+β=1, adding a pixel raises the expected
> score when its calibrated probability exceeds α × the optimal score. For DTI (α=0.2) that is
> about 0.06 at DTI 0.30. This extends Lipton, Elkan & Narayanaswamy (ECML-PKDD 2014: the
> F1-optimal threshold is half the optimal F1), so verify it numerically on synthetic rasters
> first. The 3-px kernel makes adjacent picks redundant, so don't threshold independently.
> Calibrate by isotonic regression on spatially blocked, buffered out-of-fold predictions. Treat
> ensemble, TTA and MC-dropout outputs (jittered 1–2 px) as ≥32 plausible truth rasters.
> Greedily add the ridge-candidate pixel with the largest mean DTI gain under the repo's exact
> kernel metric, then prune backward until marginal gain ≤ 0. Gate: beat the current
> spacing/MCLP placement on the same surface by >2 block-bootstrap SEs. Finish: normalize to
> [0,1]; write a float32 EPSG:32611 100 m GeoTIFF (NaN only outside the footprint); pass
> validate_submission.py; run a hash/pixel-agreement check against all prior rasters; offer the
> download only if the gate is met, else log the negative result.
>
> **PARALLEL-RUN PROTOCOL.** (1) LANE: stay inside the method paragraph. If the raster's
> rank-correlation with any registry raster exceeds 0.90, or more than 70% of dots fall within
> 3 px of one registry raster's dots, log it as a duplicate and stop; check on the surface
> before placement AND on the final dots. (2) REUSE, DON'T REBUILD: use the template's cached
> feature stack, `evaluate_holdout.py` and `submission_writer.py`; holdout = hide-and-recover
> (withhold whole fault segments with a buffer, derive every catalogue-based feature only from
> the visible faults, mask visible faults pixel-exactly, score pooled DTI, α 0.2, β 0.8, 300 m
> triangular kernel). If a shared tool is wrong, fix it once in the template and report it;
> never keep a private fork. (3) LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of
> withheld positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A
> projection is never written as a score. (4) LEAKAGE CANARY: test each feature alone on the
> holdout; AUC above 0.90 means leakage until proven otherwise. (5) RUN CARD: end with one JSON
> card (hypothesis; mechanism; the named non-fault process that could mimic it; holdout DTI +
> CI; correlation/overlap vs registry; raster sha256; validator output; submission name + note of
> at most 140 characters; verdict promote / negative). Negative results are deliverables.
> (6) BUDGET: stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a real
> slot is a separate selector step, within the weekly cap shown on the submission page.
>
> Values must be in `[0, 1]` — the portal rejects anything else with "Predicted values must be in
> range [0, 1]". Give every submission a unique name and a short note (≤140 characters). Create
> an executive-summary subpage that explains exactly how to make a submission. Work line by line
> from official verified sources with links for manual review; flag irregularities; no
> hallucinations. Core values: **Maximize P(Win)** and **Own the Outcome**.
