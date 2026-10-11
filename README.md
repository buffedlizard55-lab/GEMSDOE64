# GEMSDOE64 — native-resolution lidar scarp lane

> **SESSION START:** read this README and [`evidence/run_card.json`](evidence/run_card.json) before any work.
> The published site is built into [`docs/`](docs/) from measured evidence only.

## The project prompt (kept here verbatim, as instructed)

> Review this repository every session, follow the README and the run card, and
> produce a **unique** GeoTIFF submission for the DrivenData DOE GEMS competition
> — unique against everything in the sibling GEMSDOE family, never a copy of a
> previous submission (copying is allowed for education only). Make it obvious on
> the site whether the file is cleared to download and submit, and make the
> download prominent, with an executive-summary subpage that explains exactly how
> to submit it. Explain **why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`
> scored 0.2778** and whether it can be beaten. Produce 3–5 new candidate
> geological hypotheses first (layers, physical signature/transform, why the
> fault is missing from the USGS/INGENIOUS catalogue rather than already in it,
> and how each differs from anything already implemented), ranked by expected DTI
> gain against implementation cost; validate the top candidate on a
> spatially-blocked holdout **before** considering a submission slot; name a
> specific free official source for any new external data and verify it is
> obtainable first. Store knowledge gathered from official verified sources, do
> deep research, look for overlooked data, be contrarian but grounded. Work line
> by line, verify from official sources with links for manual review, complete
> everything autonomously without asking for manual input, flag irregularities,
> and never hallucinate. Run at least three passes (implement/verify,
> review-fix, re-check/improve), create a pull request, merge it into `main`, and
> list the remaining work and limitations. Follow the parallel-run protocol: stay
> in lane, reuse the shared tools rather than forking them, use at most three
> experiments or two hours, never spend a weekly submission slot, and label every
> number as HOLDOUT-DTI (with evaluator version, withheld positives and 95% CI)
> or ORGANIZER-CONFIRMED. Registry correlation above 0.90 or more than 70 % of
> dots within three pixels of a prior is a duplicate — stop. Keep **Maximize
> P(Win)** and **Own the Outcome** as the focal values.

## Current decision

| item | value |
| --- | --- |
| file | [`docs/downloads/g64-lidarscarp-strikeline-*.tif`](docs/downloads) (see [`docs/index.html`](docs/index.html)) |
| format | single band, float32, EPSG:32611, 3730 × 3292, 100 m, values in {0,1}, zero positive cells on the published catalogue |
| verdict | see [`evidence/run_card.json`](evidence/run_card.json) → `verdict`, `download_allowed`, `failed_gates` |
| slots used | 0 (this repository never spends one) |

The site's front page carries the file, the format preflight, and a two-line
verdict: the **literal protocol gate** and the **diagnostic certificate**. If the
literal gate fails, the page says so in the banner even though the file is
downloadable as an audit artefact. That distinction is kept because the sibling
projects' published reviews apply the same rule and report the same blocker.

## What the lane is

Native-resolution lidar scarp evidence, aggregated to the competition grid:

1. slope-detrended scarp **template matching** (`scarplet`-style, bidirectional
   step templates over 12 orientations) on the finest reachable topography;
2. **Steger** sub-pixel ridge/valley and **Frangi** multiscale vesselness on the
   same detrended surface, plus the 100 m stack's `det_elev` structure;
3. the lane's new **strike-line consistency** statistic: the fraction of aligned
   neighbours that carry evidence, used as a keep-fraction veto on packed dots;
4. **cultural mask**: cells within 30 m of a mapped road (TIGER road distance);
5. emission: Poisson-disk packing at 2.8 px (280 m) and 3.4 px, catalogue-flank
   pruning at 2 px — the step that the sibling lane measured as worth +0.0049;
6. instrument: whole-component hide-and-recover in four quadrants with a 3 px
   feature buffer, repeated over **three independent truth draws** (seeds
   20/21/22), scored with the shared pooled evaluator
   (`gems57-pooled-hide-v3-se`) and a paired spatial-block bootstrap.

Nothing here uploads, and no submission slot is used.

## Why `h33-h33-2-b2-…-e5eb6e7e-zeros` scored 0.2778 (owner-reported)

Full analysis: [`docs/answer.html`](docs/answer.html). The short version:

* the metric is `TP / (TP + 0.2·FP + 0.8·FN)` on a 3 px triangular kernel, so a
  **dot** on a fault line earns up to three kernel-units of credit while an
  off-target dot costs only 0.2 — dotting converts quantity into credit;
* the h33 file is the sibling group's 40,199-dot base emission minus every dot
  within 2 px (200 m) of the published catalogue → 37,654 dots: a 6.3 % mass
  reduction for 1.5 % of the off-catalogue credit, safety factor 2.08;
* the sibling's own instruments give it +0.00487 in 4/4 spatial quads and
  project 0.2747; the quoted 0.2778 is **owner-reported, with no organizer
  receipt in any repository checked** (the sibling's 2026-10-11 status file says
  exactly this: `OWNER-REPORTED / UNVERIFIED`). Both numbers are reproduced as
  claims with that label, never as a certified score;
* it can be beaten by *better dots*, not more of them: at the sibling's closure
  `DTI = a / (0.8 + 0.2·N/|G|)`, reaching 0.3195 needs ~25 k credited dots or
  +24 % credited mass. That is a ranking problem — which pixels — and is the
  hypothesis this lane tests.

## Hypotheses (ranked; details in [`docs/hypotheses.html`](docs/hypotheses.html))

1. **Strike-line veto on lidar scarp channels** — implemented and measured here.
2. **Expected-DTI gain pruning with cross-fitted probabilities** — implemented;
   refuted by the instrument in this lane (the cross-fitted probability labels
   the surrogate truth too poorly, so the arm collapsed). Kept as a negative.
3. **Cross-sensor corroboration veto** — available in the same feature block;
   not separately scored.
4. **Curvature-polarity asymmetry (footwall/hanging-wall)** — needs a 1 m DEM.
   The tile hosts are outside this sandbox's egress; see
   [`docs/irregularities.html`](docs/irregularities.html).
5. **Slip/length screening against the Qfaults attribute table** — data exists
   (mirrored), not yet tested.

## Uniqueness: two verdicts, both published

The inherited rule treats every positive pixel as a dot and stops when more than
70 % of a candidate's dots fall within 3 px of one prior's dots. One prior in the
checked registry carries positive mass at **every** footprint cell (it is a
probability surface, not an emission set), so that criterion is arithmetically
unsatisfiable for any non-empty candidate — the sibling project's own review
records the identical 1.0 overlap and the identical "NOT CLEARED" clearance.

`gems57.uniqueness.dense_prior_certificate` therefore measures, per prior:
support fraction, forward/reverse 3 px overlap, rank correlation on a 300 k-cell
subsample, byte/pixel identity, and — for dense priors — **matched random
controls** in the same emission domain. The certificate reports both the literal
verdict and a diagnostic verdict over the priors where the criterion is
informative. No exemption is taken anywhere: the run card keeps the literal
result, and the site shows both.

## Provenance and limits

* Inputs are **mirror-pinned**: every byte used is pinned by SHA-256 in
  [`evidence/input_pins.json`](evidence/input_pins.json) and re-verified on each
  run. Mirror consistency is not organizer authentication, and the run card says
  so.
* The 19-band stack reassembled here reproduces the pinned digest
  `4371c82e…` exactly (418,912,844 bytes).
* The 1 m lidar path (`src/gems64/lidar_scarp.py`, unit-tested) is implemented
  but not executed: 3DEP hosts are unreachable from this sandbox. The shipped
  candidate uses the finest reachable lidar-derived grid.
* No number in this repository is a leaderboard score. The public leaderboard is
  referenced only as rows with a verified read date.

## Site map

Front page (download + two verdicts) · [executive summary](docs/executive-summary.html) ·
[why 0.2778](docs/answer.html) · [hypotheses](docs/hypotheses.html) · [sources](docs/sources.html) ·
[irregularities](docs/irregularities.html) · [previous lane report (H64)](docs/research.html).

## Reproduction

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-lock.txt
.venv/bin/pip install --no-deps -e .
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_registry_index.py --scan /tmp/s60/registry/rasters \
    --witness /tmp/layers/witness_17_E-proba-multiscale.tif --out evidence/registry_index.json
.venv/bin/python scripts/pin_inputs.py --bridge data/bridge --features /tmp/training_features.tif \
    --lidar data/external/lidar_scarp_features_u8.tif \
    --road-distance data/external/tiger_road_distance_m.tif --out evidence/input_pins.json
.venv/bin/python scripts/run_scarp_lane.py --name g64-lidarscarp-strikeline
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py
```

Large inputs live outside Git (`/data/*` is ignored, and the 419 MB stack stays in
`/tmp`): the restore recipe is in [`docs/research/reproduce.md`](docs/research/reproduce.md).

## Previous round in this repository (H64, merged PR #7)

The expected-DTI selector lane ran first and is preserved here rather than overwritten. Its verdict
was **negative**, zero slots used, and it deliberately did not publish its raster
(`artifacts/gems64-h64-dtiopt-greedy-prune-calibrated-...-zeros.tif`, 52,665 dots) even though every
format check passed. Its measured findings, kept because they agree with this lane's:

* greedy probability-optimal placement **lost** to fixed 2.8 px spacing on its own instrument
  (pooled HOLDOUT-DTI 0.0707 vs 0.1333; after an exact odds correction, 0.0636 vs 0.1139); the
  greedy concentrates dots along the visible catalogue while the withheld truth is displaced from it;
* its full 62-raster registry scan found max |Spearman| 0.0403, worst Jaccard 0.025, byte- and
  pixel-unique, **and** a 3-pixel overlap of 0.9987 against `calib_r13lattice_00904` — the same
  saturating-prior effect this round's certificate later quantified with matched random controls;
* its report and submission walkthrough: [`docs/research/lane64.html`](docs/research/lane64.html),
  [`evidence/run_card_h64.json`](evidence/run_card_h64.json).

This round extends that result in one direction only: on the *same* instrument, 3.4 px spacing with a
2 px catalogue-flank prune beats 2.8 px spacing (+0.00526, > 2 paired SE), so the family's spacing
constant was under-tuned in the coarser direction as well as the direction H64 already measured.

## Next session

1. Re-check the certificate against the sibling registry's full inventory
   (655 expected rasters, 651 checked in their 2026-10-11 review) rather than the
   63 materialised here.
2. Test hypothesis 5 (Qfaults attribute screening) with the same instrument.
3. If a 1 m DEM becomes reachable, run the native path and compare it against
   this aggregate baseline — that is the lane's actual claim.
4. Push the strike-line keep-fraction study further (0.35/0.60 kept here) once
   the pooled evaluator has more truth draws.

## Second evidence set (run 64b, merged unmodified)

A parallel session produced an independent, catalogue-independent lidar-scarp evidence set for the
same lane and merged it here without changing the published card or the site's single candidate:

* receipts — `evidence/e1_sgmc_off.json` (`PROXY-INSTRUMENT (sgmc_off)`), `evidence/e2_catalogue_hide.json`
  (`HOLDOUT-DTI (catalogue_hide)`), `evidence/e3_emission.json` (`REGISTRY-MEASUREMENT`, 62 comparators);
* code — `src/gems64/lane.py`, `src/gems64/instrument.py`, `src/gems64/registry_policy.py`,
  `src/gems64/ridge.py`, `scripts/run_lane.py`, `scripts/assemble_inputs.py`;
* write-up — [`docs/research/lane64-ampsnr-findings.md`](docs/research/lane64-ampsnr-findings.md);
* frozen gates — [`PREREGISTRATION.md`](PREREGISTRATION.md);
* audit artifact — `artifacts/gems64-lane-ampsnr-37654-20261011.tif` (sha256 `534eea95…`, negative
  verdict, kept outside `docs/` so the deployed site still carries exactly one published candidate).

Decision-relevant result of that set: on `PROXY-INSTRUMENT (sgmc_off)` the `amp_snr` field beats the
owner-reported champion pooled (+0.04150, SE 0.01716) but **loses the interior stratum decisively**
(champion 0.08767 vs candidate 0.01433, paired −0.07333, SE 0.01060) and does not clear its
terrain-matched control — the same interior-versus-range-front lesson the main run's certificate
records, from a second construction, plus a measured near-duplicate dot pattern (88.8 % within 3 px of
`gems32-bayesopt-dilation-scarp-d28-*`). No weekly slot was used by either set.

