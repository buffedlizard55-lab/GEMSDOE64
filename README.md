# GEMSDOE64 — evidence-gated GEMS Prize research

> **Session-start instruction:** read this entire README before changing the project. Then read the current [run card](research/run_card.json), [score review](research/score_review.md), [hypothesis register](hypotheses.html), and [limitations / next steps](research/limitations_and_next.md). Keep the run card and site status synchronized with the evidence.

## Current decision: **NEGATIVE — no submission is cleared**

**There is no GEMSDOE64 submission TIFF in this repository. Do not download or submit a file from this project.** No unique prediction raster was generated because the checkout has no competition rasters, cached feature stack, shared holdout evaluator, submission writer, or registry of prior rasters. The requested holdout, lane-uniqueness, exact-file validation, and hash/pixel-agreement gates therefore cannot be run honestly. The negative result is recorded in [`research/run_card.json`](research/run_card.json).

This is an evidence-gated stop, not a claim that an improved score is impossible. A synthetic mathematical probe passed; it is **not** a holdout result, organizer receipt, leaderboard score, or submission validation. There are no `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED` scores for this checkout.

## Standing project prompt (read every session)

The following is the persistent, operational brief consolidated from the user's project request. Duplicated historical score lists are not treated as verified or current data; retain them only as explicitly labelled user/owner claims and verify any score-to-file attribution against an organizer receipt before repeating it.

### Objective and values

Build an auditable, scientifically grounded project for the DOE GEMS Prize Challenge that improves the probability of identifying previously unmapped faults relevant to geothermal resources. **Maximize P(Win):** choose evidence-based actions that improve the probability of success rather than spending scarce submissions on guesses. **Own the Outcome:** record failures, correct defects, and keep claims tied to reproducible evidence. Provide an easy-to-use GitHub Pages site with a front-and-center submission-readiness status and a dedicated executive-summary/how-to-submit page.

### Competition facts to preserve

- The target is geological fault traces in the GeoDAWN region; the official competition describes faults as indicators relevant to geothermal resource exploration.
- The published metric is distance-weighted Tversky, with false-positive weight `alpha = 0.2`, false-negative weight `beta = 0.8`, and a linear triangular kernel with `R = 300 m` on the `100 m` competition grid.
- The official submission contract is a single-band float32 GeoTIFF on the competition grid: EPSG:32611, matching resolution, bounds, shape and geotransform; prediction values in `[0, 1]`; null/NaN only outside the valid footprint.
- New-fault labels can include corrections or new geometry close to already mapped faults. DrivenData staff clarified that the known-fault exclusion is pixel-exact: predictions near, but not on, known-fault pixels are not automatically excluded. Do not treat a multi-pixel buffer as free or assume flank pruning is harmless.
- The public leaderboard is time-varying and is not private-test performance. A score listed on a sibling project page is not proof that the corresponding bytes received that score. `ORGANIZER-CONFIRMED` requires a submission-page receipt; `HOLDOUT-DTI` requires evaluator/version, withheld-positive count and 95% CI.

### Required method lane — expected-DTI-optimal selection

Stay within the expected-DTI-optimal-selection lane. First verify the decision-rule intuition numerically on synthetic rasters. Calibrate out-of-fold probabilities by isotonic regression on spatially blocked, buffered folds. Treat the ensemble/TTA/MC-dropout outputs (with the specified small spatial jitter) as at least 32 plausible truth rasters. On each calibrated surface, greedily add the ridge-candidate pixel with the largest **mean exact DTI gain under the competition's kernel metric**, then prune backward while its exact marginal gain is non-positive. Adjacent picks are redundant; never threshold calibrated pixels independently as a substitute for marginal-gain selection.

Compare against the incumbent spacing/MCLP placement on the *same surface*. Promotion requires a gain greater than two block-bootstrap standard errors, the leakage canary (test each feature alone; AUC above 0.90 is presumed leakage until disproved), registry correlation/overlap checks before placement and on final dots, and an exact-file validation. A candidate whose rank-correlation exceeds 0.90 with a registry raster or whose dots overlap more than 70% within 3 pixels is a lane duplicate: record it and stop.

### Reuse, validation, and budget rules

- Reuse the template's cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do not create private replacements or forks. If a shared tool is wrong, fix it in the shared template and record the correction. **Those files are absent from this checkout, so no holdout/evaluator/writer run is claimed here.**
- Hide and recover whole fault segments with a buffer. Derive every catalogue-based feature from visible faults only, mask visible faults pixel-exactly, and score pooled DTI on withheld positives.
- End each run with one machine-readable JSON card: hypothesis, mechanism, named non-fault mimic, `HOLDOUT-DTI` and CI, registry correlation/overlap, raster SHA-256, validator outcome, submission name/note, and verdict `promote` or `negative`.
- Stop after at most three experiments or two hours. Do not use a weekly submission slot; promotion to a real slot is a separate selector decision. Never submit automatically.
- Offer a TIFF download only when every gate passes. Otherwise publish the negative result and make it obvious that no file is cleared.

### Geological research requirements

Before testing, register three to five hypotheses with the specific layers, physical signature/transform, why the signal could reveal a fault absent from the USGS/INGENIOUS catalogue, a named non-fault mimic, novelty relative to the code/registry, expected DTI potential and implementation cost. Use official/free/shareable sources; verify availability before calling an idea viable. A source listing is not the same as a successfully downloaded and spatially verified dataset. The current ranked proposals and obtainability caveats are in [`hypotheses.html`](hypotheses.html).

### Submission UX and quality bar

When and only when a candidate is cleared, the first screen of the site must show the direct `.tif` download, a unique non-reused submission name, a short note of at most 140 characters, SHA-256, and the exact validator result. The executive-summary page must explain the DrivenData upload steps and format contract. Do not offer a synthetic, all-zero, copied, or otherwise unvalidated raster as a competition prediction. The previous portal message `Predicted values must be in range [0, 1]` does not, by itself, establish whether the cause was an out-of-range value, a nodata sentinel, or another serialization issue; inspect the actual rejected file before diagnosing it.

### Current-feed constraint

The official DrivenData Terms of Use state that robots/spiders/automatic access for monitoring or copying are prohibited, and also restrict manual monitoring/copying without prior written consent. Therefore this project does **not** scrape, cache, or automatically refresh leaderboard rows. The site links directly to the official page and records no mirrored score table. An authorized feed/API or written permission would be needed before adding automation.

## Answer to the score question (evidence status)

The user-supplied `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is an **unverified user/owner claim**, not a `HOLDOUT-DTI` result or an `ORGANIZER-CONFIRMED` score in this repo. The GEMSDOE32 page describes a dotted-H19-5 / catalogue-flank-pruned raster and a *modelled projection*, but also says no organizer score exists for its artifacts; another sibling page explicitly flags the score-to-file link as unverified. A plausible mechanism is that a fixed-budget thinning or prune can improve DTI if it removes prediction mass with negligible marginal true-positive coverage. That mechanism is not proof that this specific file earned the quoted result.

A critical correction from the organizer's forum: the known-fault mask is pixel-exact; adjacent predictions remain subject to the normal new-fault metric, and new-fault truth can itself lie near a known trace. Thus a 2-pixel catalogue buffer is not automatically free and may delete useful corrections. Read [`research/score_review.md`](research/score_review.md) before interpreting the claim. The user's `0.3195` value is a historical snapshot, not a stable current leaderboard value; an earlier one-time official read also recorded a higher leader at `0.4133`. Neither is current ranking data. Use the official page directly, without mirroring it here.

The expected-DTI rule `q > alpha × S` is correct in the isolated, nonredundant unit-count case. The synthetic probe also constructs an exact-kernel counterexample where a pixel's marginal truth frequency exceeds `alpha × mean DTI` but adding it reduces mean DTI due to local redundancy. Therefore the competition decision must use exact marginal gain averaged over plausible truth rasters, not the local threshold alone. See [`methodology.html`](methodology.html) and [`research/expected_dti_probe.json`](research/expected_dti_probe.json).

## What is actually present in this checkout

- At session start, the tracked repository contained only this 11-byte README.
- No `data/` directory, competition TIFFs, cached features, prior rasters, registry, training/holdout scripts, shared evaluator, submission writer, validator, or dependencies (`numpy`, `scipy`, `rasterio`, `scikit-learn`, `pytest`) were present.
- The DrivenData data URL redirected to login during review. No credentials were available or requested, and no authentication bypass was attempted.
- The suggested `scripts/download_competition_data.sh` and `scripts/prepare_data.py` do not exist in this checkout. The earlier prompt's statement that those commands are ready is not true of this branch.
- A standard-library-only **synthetic formula probe** is provided at `scripts/verify_expected_dti_rule.py`. It is not an evaluator and must not be used to report holdout numbers.

## Next steps (in order)

1. Restore the shared template/tooling into the intended shared location or this branch: cached feature stack, exact `evaluate_holdout.py`, `submission_writer.py`, `validate_submission.py`, and the prior-raster registry. Do not fork the tools privately.
2. Make the authorized competition files available in `data/` from an enrolled account, then record their filenames, hashes, CRS/grid metadata, and license/provenance. The agent cannot sign in or retrieve gated files from an unauthenticated redirect.
3. Re-run the synthetic probe, then run feature-alone leakage canaries and the preregistered spatially blocked hide-and-recover test for the top-ranked hypothesis. Report only properly labelled `HOLDOUT-DTI` with evaluator version, withheld positives, and 95% CI.
4. If the same-surface >2-SE and lane-uniqueness gates pass, build a new raster from the sample template, validate it with the shared writer/validator, hash it, and compare pixels/hashes against the complete registry.
5. Only then enable a green “OK to download and submit” banner with the unique TIFF, ≤140-character note, and receipt/evidence links. Otherwise keep the current red “NOT CLEARED” status.

## Core values in practice

- **Maximize P(Win):** prioritize measured lift on the right holdout and preserve scarce competition submissions.
- **Own the Outcome:** preserve negative results, correct misleading provenance, and never promote a projection as a score.

## Project map

- [GitHub Pages landing page](index.html)
- [Executive summary / how to submit](executive-summary.html)
- [Ranked research hypotheses](hypotheses.html)
- [Expected-DTI methodology](methodology.html)
- [Verified source register](sources.html)
- [Score/provenance review](research/score_review.md)
- [Limitations and next steps](research/limitations_and_next.md)
- [Multi-pass review log](research/review_log.md)
- [Run card (machine-readable)](research/run_card.json)
- [Synthetic decision-rule probe](scripts/verify_expected_dti_rule.py)
