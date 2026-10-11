# GEMSDOE64 — expected-DTI-optimal emission (DOE GEMS Prize, DrivenData competition 306)

## Read this first — the download and its status

**[Open the site (GitHub Pages)](https://buffedlizard55-lab.github.io/GEMSDOE64/)** — the
download button and its OK / DO-NOT-SUBMIT verdict are the first thing on the home page.

<!-- STATUS:BEGIN -->
**OK TO DOWNLOAD FOR RESEARCH — DO NOT SUBMIT.** The lane gate was not met; this file is a research artifact.

* **Download:** [`docs/downloads/gems64-h64-dtiopt-greedy-prune-calibrated-20261011T212556Z-54be1965c2f8-zeros.tif`](docs/downloads/gems64-h64-dtiopt-greedy-prune-calibrated-20261011T212556Z-54be1965c2f8-zeros.tif) (sha256 `a8c5fa733053c6f98bbe859ec95c429c5632f2b4ff30a955846de71196990a82`, 52,665 dots)
* **Submission name:** `h64-dtiopt-greedy-prune-calibrated` — note: `DTI-optimal greedy+prune on isotonic-calibrated multiphysics surface`
* **HOLDOUT-DTI** (gems64-pooled-buffered-loqo-v1, 11,321 withheld positives, pooled): nms_2p8 0.1139, random 0.0820, mclp 0.0655
* **Gate** vs `nms_2p8`: Δ = -0.05039, SE = 0.00303, z = -16.64, 95% CI [-0.05616, -0.04349] — FAIL (rule: Δ > 2×SE)
* **Uniqueness** vs 62 registry rasters: max |Spearman| = 0.0403, max 3-px dot overlap = 0.9987 (lane limits 0.90 / 0.70) — FAIL
* **Run card verdict:** `negative` (holdout gate NOT MET; literal uniqueness NOT MET (dense-lattice comparator only; see literal_rule_note)); submission slots used: 0
<!-- STATUS:END -->

* **[How to submit (executive summary)](docs/executive-summary.html)**
* **[Method and evidence](docs/method.html)**
* Run card: [`evidence/run_card.json`](evidence/run_card.json)

## Standing brief (read at the start of every session)

> THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!
>
> MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
> SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF
> SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF
> SUBMISSION.
>
> There should be an easy to download submission tif file as described by the prompt. Read
> the entire prompt.
>
> **Lane — Expected-DTI-optimal selection.** Replace heuristic spacing with a decision rule
> on a calibrated surface. For a Tversky-family score with α+β=1, adding a pixel raises the
> expected score when its calibrated probability exceeds α × the optimal score. For DTI
> (α=0.2) that is about 0.06 at DTI 0.30. This extends Lipton, Elkan & Narayanaswamy
> (ECML-PKDD 2014: the F1-optimal threshold is half the optimal F1), so verify it numerically
> on synthetic rasters first. The 3-px kernel makes adjacent picks redundant, so don't
> threshold independently. Calibrate by isotonic regression on spatially blocked, buffered
> out-of-fold predictions. Treat ensemble, TTA and MC-dropout outputs (jittered 1–2 px) as
> ≥32 plausible truth rasters. Greedily add the ridge-candidate pixel with the largest mean
> DTI gain under the repo's exact kernel metric, then prune backward until marginal gain ≤ 0.
> Gate: beat the current spacing/MCLP placement on the same surface by >2 block-bootstrap
> SEs. Finish: normalize to [0,1]; write a float32 EPSG:32611 100 m GeoTIFF (NaN only outside
> the footprint); pass validate_submission.py; run a hash/pixel-agreement check against all
> prior rasters; offer the download only if the gate is met, else log the negative result.
>
> **PARALLEL-RUN PROTOCOL.** (1) LANE: stay inside the method paragraph. If the raster's
> rank-correlation with any registry raster exceeds 0.90, or more than 70% of dots fall
> within 3 px of one registry raster's dots, log it as a duplicate and stop; check on the
> surface before placement AND on the final dots. (2) REUSE, DON'T REBUILD: use the
> template's cached feature stack, `evaluate_holdout.py` and `submission_writer.py`; holdout
> = hide-and-recover (withhold whole fault segments with a buffer, derive every
> catalogue-based feature only from the visible faults, mask visible faults pixel-exactly,
> score pooled DTI, α 0.2, β 0.8, 300 m triangular kernel). If a shared tool is wrong, fix it
> once in the template and report it; never keep a private fork. (3) LABEL EVERY NUMBER as
> HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI) or
> ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written
> as a score. (4) LEAKAGE CANARY: test each feature alone on the holdout; AUC above 0.90 means
> leakage until proven otherwise. (5) RUN CARD: end with one JSON card (hypothesis;
> mechanism; the named non-fault process that could mimic it; holdout DTI + CI;
> correlation/overlap vs registry; raster sha256; validator output; submission name + note of
> at most 140 characters; verdict promote / negative). Negative results are deliverables.
> (6) BUDGET: stop after 3 experiments or 2 hours. Do not pick submissions: promotion to a
> real slot is a separate selector step, within the weekly cap shown on the submission page.
>
> Values must be in `[0, 1]` — the portal rejects anything else with
> "Predicted values must be in range [0, 1]". Give every submission a unique name and a short
> note (≤140 characters). Work line by line from official verified sources with links for
> manual review; flag irregularities; no hallucinations. Core values: **Maximize P(Win)** and
> **Own the Outcome**.

## What is in this repository

```
src/gems64/
  grid.py metric.py network.py holdout.py validate.py gates.py
  uniqueness.py submission_writer.py   # shared template tools, vendored verbatim
                                       # from GEMSDOE32/57/59/60 (attribution in each file)
  features.py     # multi-physics + hydrothermal feature stack (45 bands)
  select.py       # THIS LANE: expected-DTI greedy add + backward prune, NMS/MCLP baselines
  theorem.py      # synthetic verification of the decision rule
scripts/
  e1_theorem.py            # gating check on synthetic rasters
  e2_holdout.py            # hide-and-recover holdout, rule comparison, block-bootstrap gate
  e3_build_submission.py   # surface -> selection -> fail-closed GeoTIFF -> uniqueness
  check_submission.py      # re-validate any TIFF on disk
  build_site.py            # regenerate docs/ from evidence/*.json
  fetch_external.sh        # restore the cached external layers + registry rasters
evidence/                  # machine-written results; the site is generated from these
docs/                      # GitHub Pages site (index / executive-summary / method)
data/bridge/               # the two small official bridge rasters (hashes pinned in grid.py)
tests/                     # pytest suite that executes the changed code paths
```

## Reproduce

```bash
python3 -m pip install --break-system-packages numpy scipy scikit-learn pandas rasterio shapely pyproj pytest
export GEMS64_EXTERNAL=/path/to/60GEMSDOE/data/external      # cached external layers
export GEMS64_REGISTRY=/path/to/60GEMSDOE/registry           # prior rasters for the uniqueness check
python3 scripts/e1_theorem.py          # synthetic verification of the decision rule
python3 scripts/e2_holdout.py          # holdout gate (>2 block-bootstrap SEs)
python3 scripts/e3_build_submission.py # build + validate + uniqueness-check the GeoTIFF
python3 -m pytest tests -q
python3 scripts/build_site.py
```

`data/bridge/existing_faults.tif` (sha256 `7ba308cc…4093`) and
`data/bridge/sample_submission.tif` (sha256 `2176d08e…5cbc`) are the pinned grid references;
`grid.py` re-verifies them on every load. `training_features.tif` (418 MB, the organiser's
magnetic/RTP/DEM bands) is **not** in this repository or in any sibling repository — GitHub
rejects files above 100 MB — so it must be placed by
`scripts/download_competition_data.sh` on a machine with DrivenData credentials.

## Known limitations (carried forward, not hidden)

1. **No organiser feature bands.** The model runs on the cached external layers
   (LiDAR scarp, radiometric, 10 m-derived topography, χ/ksn, GeoDAWN DEM) plus the GDR
   well/spring layer. The 0.41-level leaderboard entries are consistent with a model trained
   on the organiser bands; that comparison cannot be run here.
2. **Holdout ≠ live target.** The holdout hides *mapped* catalogue components. The scored
   truth is *unmapped* faults. Upstream sessions measured a signal that was present on
   mapped-but-uncatalogued structures and absent on catalogue-withheld crossings, so the
   instrument may not represent the live target.
3. **Scores quoted in the brief are owner reports, not organiser receipts.** No submission
   receipt ties exact bytes to a leaderboard number.
4. **Band semantics** of `lidar_scarp_features_u8.tif`, `geodawn_rad_u8.tif` and
   `geodawn_extensions_u8.tif` are undocumented in the source receipts
   (IR-64-BANDS-01); they are used as numbered codes and no physical meaning is claimed.
5. **The literal 70 % 3-px overlap rule** is unmeetable for any sparse emission over this
   footprint if dense "universal support" registry comparators are included — an upstream
   open question for the owner, recorded rather than waived.
