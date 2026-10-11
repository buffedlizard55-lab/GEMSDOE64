# GEMSDOE64 — lidar-scarp lane, expected-DTI selection (run 64)

> **SESSION START:** read this README, then [`evidence/run_card.json`](evidence/run_card.json) and
> [`PREREGISTRATION.md`](PREREGISTRATION.md) before doing anything. The published site is built from
> [`docs/`](docs/); the research write-up is [`docs/research/findings.md`](docs/research/findings.md).

## Project brief (the standing prompt)

1. Work the **assigned lane** (expected-DTI-optimal selection) inside the GEMS/GeoDAWN fault-mapping
   competition: improve the *expected* DTI of a submission rather than fit one leaderboard.
2. Answer **why the owner-reported champion** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`
   scored highest on the family's site (owner-reported **0.2778**; user-cited leaderboard high
   **0.3774**, other **0.3195**) and **whether a higher-scoring submission is achievable**.
3. Produce **one unique TIF submission** — never a copy of a prior submission — with an **obvious,
   easy-to-download** artifact, a unique name, and a ≤ 140-character note, free of the
   “Predicted values must be in range [0,1]” rejection.
4. Keep the site current: an executive summary at the top stating plainly how to submit, a
   submission-guide subpage, a research page, and verified-source links for manual review.
5. Label **every** number `HOLDOUT-DTI` (evaluator version, withheld positives, 95 % CI) or
   `ORGANIZER-CONFIRMED` (submission-page receipt); a **proxy instrument** number must carry its
   instrument name and be marked `PROXY-INSTRUMENT`; a projection is never written as a score.
6. Run in at least **three passes** (implement+verify, review and fix, re-check against the brief);
   keep negative results as deliverables; list remaining work and limitations; commit, PR, merge.
7. Budget: at most **three experiments** or two hours per run. Never spend a weekly slot from the lane.

## Current decision: NEGATIVE — candidate published, not cleared

One candidate TIFF exists and is downloadable from the site and from
[`docs/downloads/`](docs/downloads/) — **labelled not-cleared**:

| field | value |
|---|---|
| file | `docs/downloads/gems64-lane-ampsnr-37654-20261011.tif` (132 751 bytes) |
| sha256 | `534eea95cfc4798e…` — full hash in the run card and adjacent receipt |
| format | single-band float32, EPSG:32611, 100 m, 3730 × 3292, values 0.0–1.0, zeros outside the footprint |
| name / note | `gems64-lane-ampsnr-37654-20261011.tif` / 135-character note (limit 140) |
| validator | shared `submission_writer` + `validate` + `gates.format_report`: ok, `approved_for_weekly_slot: false` |
| slots used | 0 |

**Do not treat it as promoted.** The lane's own gate is not met: on the deciding stratum the
owner-reported champion is *better*, and the candidate is statistically tied with its controls.
The site carries the same verdict on every page.

## What was measured (no number here is a leaderboard projection)

### Instrument 1 — `PROXY-INSTRUMENT (sgmc_off)`

State-geological-map faults ≥ 300 m from the mapped catalogue; shared evaluator
`gems57-pooled-hide-v3-se`; 2 967 065 eligible cells; **62 122** truth pixels; 4 label-blind quadrant
folds; 200 px (20 km) block bootstrap, 1 000 draws. The champion raster is re-measured as a
comparator arm, never as a score.

| arm (37 654 dots) | DTI | 95 % CI | credit/dot |
|---|---|---|---|
| lane `amp_snr` | **0.13689** | 0.10660–0.16868 | 0.2110 |
| terrain-matched control (8 relief × 4 slope) | 0.12407 | — | 0.1939 |
| mass-matched random | 0.06373 | — | 0.0976 |
| owner-reported champion `h33-2-b2` | 0.09539 | — | 0.1465 |
| lane, 160 000 dots | 0.23246 | — | 0.1627 |

Paired differences (candidate − arm): champion **+0.04150 (SE 0.01716, clears 2 SE)**;
terrain-matched control **+0.01282 (SE 0.00722, does not clear 2 SE)**; lane 160 k −0.09557.

**Interior stratum** (206 of 323 blocks, the ones that contain no catalogue cell in the top relief
decile): champion **0.08767** vs candidate **0.01433**, paired **−0.07333 (SE 0.01060)** — the
champion wins by ≈ 3.5 SE exactly where range-front incision cannot earn the credit. With a stricter
truth (≥ 800 m from the catalogue, 51 742 px) the ordering is unchanged (champion 0.08140, candidate
0.01541, terrain control 0.02135).

### Instrument 2 — `HOLDOUT-DTI (catalogue_hide)`

Whole-component hide-and-recover on the mapped catalogue, 60 988 withheld positives, 161 clusters:
mass-matched random 0.07548 (0.06885–0.08142), terrain-matched control 0.06299, **candidate 0.06183
(0.04957–0.07344)**, champion 0.00670. Paired against the candidate: random −0.01366, terrain-matched
−0.00116. **No-harm check passed; no promotion possible from this instrument**, and its champion
number is structurally unfair (the champion was built to avoid the catalogue) so it is reported, not used.
The candidate row is the protocol construction (placement rebuilt per fold from the visible catalogue);
the published artifact scored **as-is** returns 0.00000 on all four folds *by construction* — its dots
are ≥ 3 px from the entire catalogue while the instrument's truth is catalogue geometry. That is a
structural diagnostic of what the file targets, not a harm measurement, and it is in the receipt.

### Surface ablation and the hypotheses it settled (instrument 1, 24 000 dots each)

| ranked surface | DTI | credit/dot | status |
|---|---|---|---|
| `amp_snr` = √(2 m excess max × mean) | **0.10352** | 0.2377 | **adopted** |
| `amp_mean` | 0.10291 | 0.2363 | close second |
| `base` (base concavity) | 0.10263 | 0.2356 | — |
| `step_max` | 0.10252 | 0.2354 | — |
| `cross_max` | 0.10029 | 0.2301 | — |
| `amp_max` | 0.09982 | 0.2290 | — |
| `crest` (crest convexity) | 0.09455 | 0.2168 | — |
| `relief` | 0.08366 | 0.1915 | terrain-class-like |
| `frac` (scarp-pixel fraction) | 0.07607 | 0.1743 | — |
| `vergence` (|up−down| asymmetry) | 0.05092 | 0.1163 | weak |
| `coh` (2 m orientation coherence) | 0.03217 | 0.0733 | weak |
| `replicate3m` (3 m chain gate) | 0.02390 | 0.0544 | weak |
| **declared composite 0.45 amp / 0.30 coh / 0.25 rep** | **0.02372** | 0.0540 | **rejected — worst arm measured** |

Five hypotheses were on the table at the start of the run; the measured outcome of each is above:

1. *Native-resolution scarp amplitude on its own carries the signal* — **ADOPTED** (`amp_snr` wins every
   ablation and beats the owner-reported champion on instrument 1 by +0.04150 at the same 37 654-dot budget).
2. *Orientation coherence and strike consistency add information* — **REJECTED** (`cross` 0.10029,
   `coh` 0.03217; the composite with coherence is the worst arm).
3. *Independent 3 m replication (h52 `h_gate12`) is a useful filter* — **REJECTED** (0.02390, and it
   anti-correlates with the state-map population, AUC 0.343).
4. *Crest/base curvature pairing isolates one-sided scarps* — **PARTLY REJECTED** (`crest` 0.09455,
   `base` 0.10263, `paired_curv` weak; no improvement over amplitude).
5. *Vergence asymmetry separates fault scarps from channel banks* — **NOT SUPPORTED** on this
   instrument (`vergence` 0.05092); it stays in the lane's component set for the next, interior-first run.

### Registry — `REGISTRY-MEASUREMENT`

62 single-band registry rasters compared by bytes, decoded pixels, rank correlation and dot overlap:
`byte_unique` **true**, `pixel_unique` **true**; two comparators (`calib_r13lattice_00904.tif`,
`r13_lattice_s5_00904.tif`) place a 3 px halo over **99.87 %** of the footprint, which makes the
literal “≤ 70 % within 3 px” clause unsatisfiable for any nonempty candidate; on the discriminating
reading **88.8 %** of the candidate's dots still sit within 3 px of
`gems32-bayesopt-dilation-scarp-d28-*` and 95.3 % within 3 px of `r11_greedy_mp.tif`. Logged as a
**near-duplicate pattern** — the reason the verdict is `negative` even though the bytes are new.

### Why the owner-reported champion leads, and whether more is achievable

The champion is a **broad, interior, non-halo field**, not a stronger pixel detector. It is beaten on
the pooled proxy population by this lane's candidate (+0.04150, 2 SE) and is near-useless on the
catalogue-recovery instrument (0.00670), yet it wins the interior stratum by 3.5 SE and wins the
strict-truth interior by 5 SE. A higher-scoring submission is therefore achievable in principle by
whatever earns credit *in the interior* — and this lane's surface does not. Full reasoning:
[`docs/research/findings.md`](docs/research/findings.md).

## How to submit (plainly)

1. Open the site (`docs/index.html`) → **Download candidate TIFF (NOT cleared)** or use
   `docs/downloads/gems64-lane-ampsnr-37654-20261011.tif` (ZIP with the single TIFF alongside).
2. Verify `sha256sum` against the receipt `…20261011.json`.
3. `.venv/bin/python scripts/validate_submission.py FILE.tif` — local format check only.
4. As an authorized operator, upload on the competition’s “New submission” page, paste the recorded
   135-character note if asked, confirm the weekly cap yourself, and **keep the submission-page
   receipt**; that receipt is the only thing that can create an `ORGANIZER-CONFIRMED` number here.
5. If the portal rejects the file, stop and record the error verbatim — the writer never clips or
   silently repairs values.

## Layout

* `src/gems57/` — shared template (metric, spatial folds, `evaluate_holdout`, writer, validator, gates).
  Same code as the pinned sibling import; nothing is forked privately.
* `src/gems64/` — lane code: `lane.py` (decode, components, rank, blue-noise placement, cultural mask),
  `instrument.py` (Proxy/Pooled instruments, controls, strata, block bootstrap),
  `registry_policy.py` (registry index, saturating comparators, literal + discriminating readings),
  `ridge.py` (standalone reference detectors for the ridge geometry used by the lane).
* `scripts/run_lane.py` — E1/E2/E3 runner; `scripts/assemble_inputs.py` — input assembly;
  `scripts/make_run_card.py` — derives the run card from receipts; `scripts/build_site.py` +
  `scripts/check_site.py` — the site and its publication guard.
* `evidence/` — receipts (`e1_sgmc_off.json`, `e2_catalogue_hide.json`, `e3_emission.json`,
  `registry_index.json`, `run_card.json`, `input_assembly.json`, …).
* `data/inputs/` — 14 assembled inputs + 62 registry comparators; every file hashed in
  `evidence/input_assembly.json`; raw data is git-ignored.
* `PREREGISTRATION.md` — frozen gates, the negative-result template, and what the next run must do.

## Reproduction

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-lock.txt && .venv/bin/pip install --no-deps -e .
.venv/bin/python scripts/assemble_inputs.py          # idempotent; needs network for the pinned sources
.venv/bin/python scripts/run_lane.py --experiments e1,e2,e3 \
    --emit --submit-name gems64-lane-ampsnr-37654-20261011.tif --submit-note "<135-char note>"
.venv/bin/python scripts/make_run_card.py
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

## Limitations (carry into the next session)

* No `ORGANIZER-CONFIRMED` number exists in this repository; the owner-reported 0.2778 and the
  leaderboard numerals (0.3774 / 0.3195 / 0.4133) are quoted as **owner/site claims**, not receipts.
* Instrument 1 is a different fault population and favours rock-exposed terrain; instrument 2 is
  blind to off-catalogue placement. Neither can rank these submissions against the hidden panel.
* The cultural mask covers TIGER roads and BLM closed claims only; canals and field edges are **not**
  masked (recorded in every receipt).
* `amp_snr` and the 37 654-dot budget were selected after looking at instrument 1, so that run is
  selection-exposed; the gates in `PREREGISTRATION.md` exist to stop that from being treated as
  confirmation.
* The lane never verified a weekly cap, never logged into DrivenData, and never submitted anything.

## Next session — in order

1. Build the interior-first field the evidence points at, evaluate it on the interior stratum of
   both instruments, and beat the terrain-matched *and* sparse-spread controls by > 2 SE there.
2. Freeze that field and its budget in `PREREGISTRATION.md` **before** reading any instrument.
3. Re-run the registry comparison with the two saturated lattice comparators marked
   non-discriminating in the same receipt, and report exact-dot Jaccard next to the 3 px overlap.
4. Only then spend a slot, as a separate authorized selector decision, and archive the
   submission-page receipt as `evidence/organizer_receipt.json`.
