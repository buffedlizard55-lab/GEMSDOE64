# GEMSDOE64 — native-resolution lidar scarp channels

> **SESSION START:** read this file, then [`evidence/run_card.json`](evidence/run_card.json)
> and [`docs/research/findings.md`](docs/research/findings.md) before any work.

## Current decision: **OK TO DOWNLOAD**

The lane produced one artifact and it passes this project's promotion gate:

| | |
| --- | --- |
| **Submission name** | `GEMSDOE64-NATIVE-LIDAR-SCARP-COVER` |
| **File** | [`docs/downloads/gems64-scarpcover-60000-98d317b7-zeros.tif`](docs/downloads/gems64-scarpcover-60000-98d317b7-zeros.tif) |
| **Also** | [`…-zeros.zip`](docs/downloads/gems64-scarpcover-60000-98d317b7-zeros.zip) — that one TIFF, nothing else |
| **SHA-256** | `1551f1b545a08fdb8ac49059c83ca2b1843f026c3f3fdbbe92195c7d668ef1a7` |
| **Bytes** | 822 200 |
| **Grid** | 3730 × 3292 · 100 m · EPSG:32611 · `(100, 0, 243350, 0, −100, 4508550)` |
| **Values** | all finite, inside [0, 1], no nodata tag, zeros outside the footprint, 60 000 unit dots |
| **Note (134/140)** | `Native 100 m lidar scarp channels, blocked-CV field, kernel-greedy coverage; dots off the mapped catalogue; unique vs 62 prior rasters` |
| **HOLDOUT-DTI** | 0.3408 over 61 664 withheld truth pixels, evaluator `gems64-dti-exact-v1` |
| **Gate** | +0.2217 ± 0.0549 versus the area-matched random control → clears two SE |
| **Organizer score** | none. No submission has been made. |

**Downloading is cleared. Spending a weekly slot is not** — that is a separate selector
decision bounded by the cap on the authenticated submission page. This run used **0** slots.
The static site in [`docs/`](docs/) says the same thing in [`index.html`](docs/index.html) and
gives the six-step upload procedure in [`executive-summary.html`](docs/executive-summary.html).

### What would make you distrust that table

Read these before submitting anything:

* The 0.3408 is a **HOLDOUT-DTI against a surrogate**, not a competition score. The surrogate is
  the USGS SGMC compilation, and the metric is computed on whole 32 km super-blocks that the
  field never saw. Transfer to the private expert labels is **unmeasured** and is the top open
  risk in the run card.
* The artifact places **zero dots within 300 m of the mapped catalogue**, because the surrogate
  is defined to exclude that band. If the private labels contain strands adjacent to the public
  map, this file cannot score them. That is the single largest downside and it is deliberate.
* There is **no cultural-feature mask** in this checkout, so roads, canals and field edges are
  unmasked mimics.
* The literal 70 % dot-overlap rule is **unsatisfiable** against four self-covering registry
  rasters. Both the literal and the null-corrected measurements ship; see §"Open irregularities".

## The lane

Native-resolution lidar scarp channels. Bare-earth 1 m lidar resolves fault scarps whose 100 m
expression is below the resolution of the shared stack; scarp-pixel fraction, SNR-weighted
amplitude, ridge/valley (Laplace) and cross-scarp (Hessian) responses, structure-tensor
coherence and dominant strike are the lane's channels. `scarplet` (Sare & Hilley, JOSS 2018,
[doi:10.21105/joss.01066](https://doi.org/10.21105/joss.01066)), Steger
(IEEE TPAMI 20(2):113–125, 1998) and Frangi (MICCAI 1998, LNCS 1496:130–137) are the named
methods behind those channels. The 1 m tiles behind the aggregate are gated in this sandbox, so
the lane reuses the project's 100 m lidar-scarp aggregate rather than re-running them; that is
recorded as a limitation, not hidden.

## How the artifact is built

```bash
python -m venv .venv && .venv/bin/pip install numpy scipy scikit-learn rasterio pytest
python scripts/restore_competition_data.py     # hash-verified owner mirrors, ~26 s
python scripts/build_scarp_field.py            # 122-feature candidate lattice, ~110 s
python scripts/build_scarp_stage2.py           # blocked field, greedy, gates, artifact, receipts, ~5 min
python scripts/assemble_run_card.py            # derived run card, never hand-written
python scripts/build_site.py && python scripts/check_site.py
python scripts/validate_submission.py docs/downloads/gems64-scarpcover-60000-98d317b7-zeros.tif
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

`build_scarp_stage2.py` refuses to mark the artifact promoted unless the population-matched
blocked instrument beats the area-matched control by more than two paired block-bootstrap
standard errors **and** every on-disk format check passes. `build_site.py` refuses to publish a
promoted card whose bytes do not hash to the card's SHA-256, and refuses to publish *any* raster
under a negative card. `check_site.py` re-verifies both directions from the built HTML.

## What is measured, and what is asserted

Every number in this repository is one of:

* **HOLDOUT-DTI** — the published metric, computed on whole withheld super-blocks, with the
  evaluator version, the withheld-positive count and a 95 % paired block-bootstrap interval.
* **surrogate-CV** — the same metric on the population-matched surrogate under blocked folds.
  Used only to shape the emitted mass.
* **DIAGNOSTIC** — a leakage canary, a control arm, or a sensitivity. Never a score.
* **REGISTRY-MEASUREMENT** — decoded-pixel comparison against the 62 prior rasters kept in
  `data/registry/`.

There is no leaderboard projection anywhere, no synthetic result presented as a holdout, and no
organizer-confirmed score, because **no submission has been made**.

## Open irregularities (recorded, not waived)

1. **IR-64-UNIQ-01 — the literal overlap rule is unsatisfiable.** `calib_r13lattice_00904`,
   `r13_lattice_s5_00904`, `r11_greedy_mp` and `r14_union_tips10_lat6` already place a positive
   pixel within 3 px of ≥ 73 % of every allowed cell. Any nonempty submission therefore exceeds
   the 70 % rule against them. This artifact measures 0.9992 literal overlap on the densest
   comparator while a same-size random field measures 0.9984. Both numbers ship in
   `evidence/lane64_uniqueness.json`. **Fix it in the shared protocol in writing** — a
   null-corrected overlap, or an explicit self-covering exemption. Do not take a private
   exemption; this run does not.
2. **IR-64-CANARY-01 — a leakage canary fired and was honoured.** Including
   `derived_sgmc_faults_100m_u8.tif` as a feature drove held-out AUC to 0.9985, above the shared
   0.90 canary. It was removed; the honest value is 0.7917. The exclusion is recorded in
   `evidence/lane64_run_card.json → field.leakage_canary`.
3. **IR-30-001 — provenance.** Every competition raster here is an owner-mirrored copy,
   SHA-256-pinned, **not organizer-authenticated**. The pins are re-checked on every run by
   `scripts/restore_competition_data.py --check`.
4. **IR-64-DATA-01 — the 1 m lane inputs are gated.** The lane's native-resolution products are
   reused from the project's 100 m aggregate; scarplet/Steger/Frangi were not re-run.

## Next session, in order

1. Amend the uniqueness protocol in writing (IR-64-UNIQ-01). Until then the literal rule cannot
   distinguish any candidate from any other.
2. Build the two-arm near-catalogue artifact and measure the annulus arm's marginal credit on a
   surrogate that does *not* exclude the 300 m band.
3. Spend a slot only with the owner's authorization, and record filename + SHA-256 + returned
   score as a single triple.
4. Re-derive the lane at 1 m if the gated DEM tiles become available.

## Core values

* **Maximize P(Win)** — measured lift on the right holdout, and scarce submission opportunities
  preserved.
* **Own the Outcome** — negative results are deliverables; blockers are recorded, not routed
  around; no projection is ever written as a score.
