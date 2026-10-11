# GEMSDOE64 — DOE GEMS Prize research and submission gate

> **Current status: NEGATIVE / NO SUBMISSION FILE. Do not download or submit a TIFF from this repository.**
> This checkout does not contain competition data, a prediction surface, the shared evaluator/writer/validator, or a validated candidate. No TIFF has been generated. A made-up or all-zero raster would not be a scientifically defensible submission and could waste a competition slot.

**Start here on every future session:** read this README, `docs/run-card.json`, and the current official sources linked below before changing code, evaluating a candidate, or claiming a score. The experiment lane is the expected-DTI decision rule described in the persistent brief; do not silently substitute another feature/model lane.

- [Project dashboard](docs/index.html) — the first screen explicitly says whether a file is safe to submit.
- [Executive summary and upload instructions](docs/executive-summary.html)
- [Research notes and threshold check](docs/research.html)
- [Ranked hypothesis register](docs/hypotheses.html)
- [Auditable source register](docs/sources.html)
- [Machine-readable run card](docs/run-card.json)

## Immediate repository review

The initial branch started from a single `README.md`. This turn has added a static research dashboard and one synthetic math-check script, but the checkout still has no `data/` rasters, model, feature cache, competition test suite, prior-raster registry, or submission pipeline. In particular, the prompt refers to `scripts/download_competition_data.sh`, `scripts/prepare_data.py`, `evaluate_holdout.py`, `submission_writer.py`, and `validate_submission.py`; **none of these shared pipeline files is present in this checkout**. The environment also lacks NumPy, SciPy, Rasterio/GDAL, scikit-learn, PyTorch, and pytest. The competition data page redirects to a DrivenData login form. No login, credential, or access-control bypass was attempted.

Therefore it is not possible here to:

- build the template's cached feature stack or a calibrated out-of-fold surface;
- withhold whole fault segments with a buffer, calculate leakage-canary AUCs, or score a spatial holdout;
- compare the proposed placement with the incumbent spacing/MCLP placement using the shared exact kernel evaluator and block-bootstrap standard errors;
- check surface correlation or final-dot overlap against a complete registry of prior rasters;
- write and independently re-read a GeoTIFF against the official sample grid, run the required validator, or hash/pixel-compare all prior files.

These are **blocking missing inputs/tools**, not results that can be inferred from links, public leaderboard rows, or synthetic data. No weekly submission slot has been used. See the negative run card for each gate's status.

## Persistent project brief — read before every future change

### Objective and values

Build an auditable, reproducible system for the DOE GEMS Prize that helps identify previously unmapped geological faults relevant to geothermal exploration and can produce a legally formatted, clearly named submission GeoTIFF. Maximize the probability of a valid, useful competition result; own failures and publish them as negative results. Do not claim a win or score projection as an observed result. A unique name and a short note belong beside every *validated* downloadable artifact.

The official challenge says that the training faults are known/public labels and that scoring targets new expert-identified faults not contained in the existing public fault database; expert review updates labels for the later prize phase. The target is faults in the GeoDAWN study region, not a direct raster of geothermal vents. The official description and current rules are linked in the source register.

**Core values.** **Maximize P(Win)**: use evidence gates, conserve scarce submission slots, and reject unsupported work. **Own the Outcome**: keep negative results visible, fix shared-tool defects in the shared template, and make provenance reproducible. The goal is to improve the odds of a strong competition result—not to promise a rank or let a projection masquerade as a score.

### Fixed experiment lane for this session

Use **expected-DTI-optimal selection on a calibrated fault-likelihood surface**, not a new private feature/model branch:

1. Reuse the shared template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py` once they exist in the project checkout. Calibrate with isotonic regression using spatially blocked, buffered out-of-fold predictions.
2. Use at least 32 plausible truth rasters from ensemble/TTA/MC-dropout uncertainty, with the required 1–2 pixel jitter represented. Do not treat neighboring candidate pixels as independent because the official 300 m triangular kernel couples them.
3. Greedily add the ridge candidate with the largest **mean marginal gain under the exact evaluator**; prune backward until no positive marginal gain remains. Compare against the incumbent spacing/MCLP placement on the same surface and proceed only if the improvement exceeds two block-bootstrap standard errors.
4. Before placement and again on final dots, test against the prior-raster registry. A rank correlation above 0.90 or more than 70% of dots within 3 pixels of a registry raster is a duplicate: log it and stop.
5. Use hide-and-recover holdout only: withhold whole fault segments plus a buffer; derive every catalogue-based feature from visible faults; mask visible faults pixel-exactly; report pooled DTI with alpha 0.2, beta 0.8, and the 300 m triangular kernel. Test every feature alone; AUC above 0.90 is a leakage alarm until explained.
6. Only after all gates pass, normalize output to [0,1], write float32 on the exact EPSG:32611 / 100 m sample grid (NaN only outside the footprint), run the shared validator, and record SHA-256 plus hash/pixel agreement against every prior raster.
7. Stop after three experiments or two hours. Do not select/submit a candidate here; selector/promotion is a separate action under the competition's current slot limits.

The requested alpha-times-optimal-score threshold is a useful **ratio-of-expected-counts** derivation, not a license to threshold spatial pixels independently. Before using it, this repository ran a dependency-free exhaustive synthetic check. The check found a finite-ensemble counterexample: the cutoff accepts a pixel while the mean of exact per-map Tversky ratios falls. Consequently the active rule must be the exact mean marginal gain under the shared kernel evaluator; the scalar cutoff is not used as an acceptance criterion. Details and the reproducible script are in [research notes](docs/research.html) and [`scripts/synthetic_expected_dti_check.py`](scripts/synthetic_expected_dti_check.py). This toy check is not a competition score or a substitute evaluator.

### Evidence and reporting rules

- Every reported competition score must be explicitly **HOLDOUT-DTI** (evaluator version, number of withheld positives, and 95% CI) or **ORGANIZER-CONFIRMED** (copied from a DrivenData submission-page receipt). Do not promote a projection, a sibling site's claim, or a leaderboard screenshot to either category.
- The run card must always record: hypothesis; mechanism; a named non-fault mimic; holdout DTI and CI; registry correlation/overlap; raster SHA-256; validator output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission name and a note of at most 140 characters; verdict `promote` or `negative`.
- Offer a TIFF for download **only after every gate passes**. Otherwise publish the negative card and make the absence of a download unmistakable.
- Use official, free/public sources for external geology. Verify availability and reuse terms before use. Do not scrape DrivenData: its published Terms of Use prohibit automated robots/spiders. Link to the live official leaderboard instead of presenting a fabricated or silently stale feed.
- Do not copy an existing submission as a deliverable. Prior artifacts may be inspected for learning and exact duplicate checks only.

### Competition file and upload requirements

The official problem page requires a single-band GeoTIFF with float32 confidence values in [0,1], the training grid's projected CRS (EPSG:32611), 100 m resolution, matching bounds/geotransform, and null/NaN outside the bounds. The actual grid shape, transform, and valid footprint must be copied from the official sample/template—not guessed. The portal error `Predicted values must be in range [0, 1]` requires checking actual in-footprint min/max and nodata/sentinel handling; this checkout contains no raster to diagnose. The [executive summary](docs/executive-summary.html) gives the safe upload sequence and explicitly says there is no current file to upload.

The official rules state that competition data is supplied to registered participants via DrivenData, scores on the public leaderboard are not the private-round scores, and a final submission must be selected for both prize rounds. They also require AI-use disclosure in the narrative when applicable. Review the current rules before entering or spending a weekly evaluation slot.

## What the previous-site evidence does—and does not—show

The site links in the prompt are owner-maintained experiment reports, not official metric receipts. A live official leaderboard check during this review showed that the supplied leaderboard snapshot is no longer current; consult the [official live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/). The linked GEMSDOE32 page describes its H33-2-B2 file as a candidate and explicitly says no organizer score exists for that artifact, while also distinguishing model projections from scores. That conflicts with the prompt's characterization of the H33 entry as an established score. Without the actual submission-page receipt and file hash, the score attribution and causal explanation cannot be verified.

A plausible, **not proven**, reason sparse/dotted submissions can do better than dense fields is that reducing redundant predicted mass may reduce false-positive cost while preserving nearby credit under the distance-weighted metric. This does not establish why any particular official score was high, and it does not show that a new candidate will outperform the live leaderboard. A stronger result requires the preregistered holdout and exact-kernel gate, followed by an organizer receipt.

## Ranked hypothesis register

The detailed register is in [`docs/hypotheses.html`](docs/hypotheses.html). The only experiment lane being executed is the calibrated-surface, exact-DTI placement rule. Other geology ideas are future candidates, not experiments or submission recommendations. This repository has no prior implementation, so “new to this checkout” is verifiable; novelty against every sibling site cannot be proven from result names alone.

## Official sources for manual review

| Source | What it verifies | Status in this review |
|---|---|---|
| [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Target, feature/label context, DTI definition, 300 m triangular kernel, submission format | Read directly |
| [DrivenData official rules (NLR PDF)](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Two prize phases, one final submission, data access, evaluation, AI-use disclosure | Relevant sections read directly; not a legal review of every appendix |
| [DrivenData data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Training files and sample template | Redirects to login; no data available in checkout |
| [DrivenData live leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) | Current public leaderboard only | Live link; not treated as a submission receipt or private score |
| [DrivenData Terms of Use](https://www.drivendata.org/termsofuse/) | Prohibits automatic robots/spiders and monitoring/copying without consent | Read directly; no scraper implemented |
| [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) | Public baseline code and environment | Read directly; not present in this checkout |
| [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) | Official survey provenance and public products | Read directly |
| [INGENIOUS project](https://gbcge.org/current-projects/ingenious/) | Project context and published datasets | Read directly |
| [USGS heat-flow data release](https://www.sciencebase.gov/catalog/item/6297d2fad34ec53d276c5b28) | Official downloadable heat-flow maps/supporting data | ScienceBase lists the data ZIP; not downloaded or integrated |
| [Lipton, Elkan & Narayanaswamy (2014)](https://doi.org/10.1007/978-3-662-44851-9_15) | F1-optimal threshold result for calibrated probabilities | Read; application to exact spatial expected DTI is tested, not assumed |

## Multi-pass review record

- **Pass 1 — inventory and source check:** confirmed the checkout at session start contained only the initial README; fetched the official challenge description, rules PDF, data-page login redirect, Terms of Use, USGS GeoDAWN page, and selected official ScienceBase records.
- **Pass 2 — assumptions and risks:** checked the requested threshold numerically and found the finite-ensemble counterexample; distinguished owner-site claims/projections from official receipts; flagged the missing cached stack, scripts, sample grid, registry, and dependencies.
- **Pass 3 — completeness and safety:** added a prominent negative-status static dashboard, submission instructions that cannot accidentally offer an unvalidated file, a ranked but explicitly unvalidated hypothesis register, a source table, and the run card. No private evaluator, private feature fork, copied raster, external dataset, or competition submission was created.

## Next actions

1. Restore or attach the actual shared template/tooling and authorized competition data in the expected local layout. Never place credentials in this repository.
2. Verify shared metric/evaluator/writer/validator versions and the sample grid; fix defects in the shared template, not in a private copy.
3. Build the requested buffered segment holdout and leakage canaries using visible faults only; record withheld-positive counts and uncertainty.
4. Produce buffered spatial OOF predictions and at least 32 uncertainty truth rasters; calibrate isotonic regression using only training folds.
5. Compare exact-kernel greedy placement against incumbent spacing/MCLP and its block-bootstrap CI; run registry duplicate checks before and after placement.
6. Only on a passing gate: write, validate, hash, pixel-compare, and expose a uniquely named GeoTIFF with a concise note. Otherwise keep the negative result and no download.
7. Keep the leaderboard linked live. Do not auto-poll DrivenData unless the organizer provides an authorized API or written permission.
