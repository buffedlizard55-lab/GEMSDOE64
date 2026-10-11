# GEMSDOE64 — Native-Resolution LiDAR Scarp Channels, Cultural Masking & Spatial-CV Retraining (`H64-L1`)

> **COMPETITION SUBMISSION STATUS: `promote` — YES, IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED GEOTIFF.**
>
> - **Primary Portal-Safe GeoTIFF (`0.0` outside footprint, `min = 0.0, max = 1.0, n_nan = 0`)**: [`submissions/h64-lidar-scarp-cv-20261011-zeros.tif`](submissions/h64-lidar-scarp-cv-20261011-zeros.tif) (`506,812` bytes · SHA-256 `919dfc5f9e429a8bae0784244191a23cc0d50fa265b8f5085a01f9644ab9e97c`)
> - **Primary Single-TIFF ZIP**: [`submissions/h64-lidar-scarp-cv-20261011-zeros.zip`](submissions/h64-lidar-scarp-cv-20261011-zeros.zip) (`473,538` bytes · SHA-256 `e12484fa79619cebede818a528ce8b3b00200b572f9ab2de607509fd1d3701a2`)
> - **Companion NaN-Outside-Footprint GeoTIFF (`NaN` only outside footprint, identical inside footprint)**: [`submissions/h64-lidar-scarp-cv-20261011-nan.tif`](submissions/h64-lidar-scarp-cv-20261011-nan.tif) (`802,496` bytes · SHA-256 `62e330bb8df511c33ac0a3c977f8067b7d72d84324fe2c5d7d901b88c253869b`)
> - **Companion Single-TIFF ZIP**: [`submissions/h64-lidar-scarp-cv-20261011-nan.zip`](submissions/h64-lidar-scarp-cv-20261011-nan.zip) (`676,650` bytes · SHA-256 `3f808a7022c0647696817b9a7d356ad7109407d229ace017d7789f0143e4f7d0`)
> - **Unique Submission Name**: `h64-lidar-scarp-cv-20261011`
> - **Submission Note (106 / 140 chars)**: `H64-L1 native 1-3m LiDAR scarplet+Steger/Frangi 100m + TIGER/canal/field cultural mask + 4-quad spatial CV`
> - **GitHub Pages Site & Executive Summary**: [`docs/index.html`](docs/index.html) · [`docs/executive-summary.html`](docs/executive-summary.html) · [`docs/research.html`](docs/research.html) · [`docs/sources.html`](docs/sources.html)

---

## Core Values & Mission Prompt

### Core Values
- **Maximize P(Win)**: Every decision is evaluated by one question: *does this increase our probability of winning the competition?* Prefer high-leverage geological and modeling improvements over cosmetic changes, and validate every idea against the actual competition metric (**Distance-Tolerant IoU / Extended F1**, $\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel).
- **Own the Outcome**: Do not stop at "code written" or "model trained." Verify that the predictions make geological sense, the submission file is valid (`float32`, `EPSG:32611`, `100 m`, `[0, 1]`), and the score actually improves on spatially blocked holdout (`> 2 SE`) before recommending any upload.

### Assigned Lane — Native-Resolution LiDAR Scarp Channels
On native-resolution GeoDAWN / USGS 3DEP LiDAR (`1–3 m`), compute:
1. **Scarplet template matching** (Sare & Hilley, *JOSS* 2018, [`doi:10.21105/joss.01066`](https://doi.org/10.21105/joss.01066); reference code [`stgl/scarplet`](https://github.com/stgl/scarplet)) returning amplitude, relative morphologic age ($\kappa t$), orientation ($\alpha$), and signal-to-noise ratio ($\text{SNR}$), extended with **slope-aware scarp templates** (AGU 2015 Fall Meeting Poster T31A-2838; Sare, Hilley, & DeLong, *JGR Solid Earth* 2019, [`doi:10.1029/2018JB016886`](https://doi.org/10.1029/2018JB016886)).
2. **Steger sub-pixel ridge/valley lines** (Steger, *IEEE TPAMI* 20(2):113–125, 1998) and **Frangi multiscale Hessian line measures** (Frangi et al., *MICCAI* 1998, LNCS 1496:130–137) at $2\text{--}20\text{ m}$ scales on a slope-detrended surface.
3. **Aggregate to $100\text{ m}$ competition grid cells** as:
   - `scarp_pixel_fraction`
   - `snr_weighted_amplitude`
   - `structure_tensor_coherence`
   - `dominant_strike`
4. **Mask roads, canals, and field edges** with the cultural-feature mask (`tiger_road_distance_m.tif`, `blm_closed_claim_distance_m.tif`, cross-slope canal dominance, and N–S/E–W section-line field-edge filter), then **retrain under 4-quadrant Leave-One-Quadrant-Out spatial CV**.
5. **Gate**: `HOLDOUT-DTI` gain on LiDAR-covered holdout blocks that is **not confined to range fronts** (`> 2 SE` improvement on both full LiDAR-covered holdout blocks and off-range-front LiDAR-covered holdout blocks).
6. **Finish**: Normalize to `[0, 1]`; write `float32` `EPSG:32611` `100 m` GeoTIFF (`NaN` only outside the footprint in `-nan.tif`, `0.0` outside the footprint in portal-safe `-zeros.tif`); pass `src/gems64/validate.py (shared)`; run hash/pixel-agreement, rank-correlation, and 3-px overlap checks against all 67 prior registry rasters; offer download.

### Parallel-Run Protocol
1. **STAY IN YOUR LANE**: Implement only the assigned hypothesis. Check Spearman rank-correlation ($\le 0.90$) and 3-px dot overlap ($\le 0.70$) against registry rasters on the surface before placement and on the final dots.
2. **REUSE, DON'T REBUILD**: Use shared template evaluators (`src/gems57/evaluate_holdout.py`, `src/gems57/submission_writer.py`). Holdout = hide-and-recover: withhold whole fault segments with a $300\text{ m}$ buffer, derive catalogue features only from visible faults, mask visible faults pixel-exactly, score pooled DTI ($\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel).
3. **EVIDENCE CLASSES**: Every number is labeled as `HOLDOUT-DTI` (with evaluator version, number of withheld positives, and 95% CI) or `ORGANIZER-CONFIRMED`. Never write a projection as a score.
4. **LEAKAGE CANARY**: Test each feature alone on the holdout before trusting any result. Directional AUC above `0.90` means leakage until proven otherwise.
5. **ONE OUTPUT**: End with one JSON RUN CARD per lane. Two now exist and must not be confused:
   [`evidence/run_card.json`](evidence/run_card.json) is the **published** card for the promoted
   LiDAR-scarp lane (`verdict: promote`) and is mirrored byte-for-byte at
   `docs/data/run_card.json`, which `scripts/check_site.py` enforces;
   [`evidence/run_card_expecteddti.json`](evidence/run_card_expecteddti.json) is the
   Expected-DTI-optimal lane's card (`verdict: negative`). Each card is generated from its own
   receipts by its own builder — `scripts/make_run_card_expecteddti.py` for the latter — and
   neither builder may be pointed at the other's output path.
6. **BUDGET**: $\le 3$ experiments (`EXP-64-1`, `EXP-64-2`, `EXP-64-3` completed in `205.81 s`).

---

## Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778`) Scored Highest & How to Beat `0.3195` / `0.3774`

Forensic audit (`scripts/audit_h33.py`, [`evidence/h33_forensics.json`](evidence/h33_forensics.json)) of `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`ORGANIZER-CONFIRMED 0.2778`, 37,654 dots) against its parent `GEMSDOE28__h27-4-r1-solo-d2-8.tif` (40,199 dots, owner-reported `0.2708`) proves:
- **Exact $200\text{ m}$ Catalogue-Flank Pruning (`rule_pixel_disagreement = 0`)**: `h33-2-b2` is pixel-identical to deleting the **2,545 dots** at $0 < d \le 2\text{ px}$ ($200\text{ m}$) from `existing_faults.tif` while retaining all 37,654 dots at $d \ge 2.236\text{ px}$.
- **Why That Raised the Score Under DTI ($\alpha=0.2, \beta=0.8, R=300\text{ m}$)**: Because `existing_faults.tif` is masked at scoring time, dots at $100\text{--}200\text{ m}$ alongside known faults earn zero $\text{TP}_w$ from the masked strand while adding $+0.2$ per dot to $0.2\,\text{FP}_w$. At true fault tips, a single dot placed at $d = 300\text{ m}$ already covers the $100\text{--}200\text{ m}$ tip cells via the $R=300\text{ m}$ triangular kernel ($\text{TP}_w$ uses $\max$, whereas $\text{FP}_w$ sums additively).
> **Independently corroborated.** The Expected-DTI lane reached the same explanation by a different
> route — inverting `T = DTI·(0.2·S + 0.8·K)` through the verified closed form across
> K = 6,000–12,691 rather than diffing pixels — and additionally quantified the flank band as a
> **6.3× credit depletion** (≈0.016 per removed dot vs ≈0.102 per retained dot), which is why the
> removal was *required* by the marginal rule and not merely score-improving. See
> [`docs/research/lane-expecteddti-findings.md`](docs/research/lane-expecteddti-findings.md).
>
> **Irregularity flagged on the targets above, resolved against this repository's own verified
> snapshot.** [`docs/data/leaderboard_snapshot.json`](docs/data/leaderboard_snapshot.json)
> (`observed_utc: 2026-10-11`, `verified: true`, manual rendered-page fetch, 50 rows) carries an
> erratum recording a live re-read whose rows 1–10 supersede the snapshot body. On that re-read the
> top of the board is **0.4133** (`xiaofanhu`), `0.3585` (`cfld__`) and `0.3418`
> (`JerryDataWorks`); **`0.3195` is confirmed real** (`DARD`, rank 9), and the `0.2778` receipt
> discussed above sits at **rank 23** (`extradr19`). The figure that was #1 on 2026-10-04,
> `0.3262` (`nchuzhoy`), is now rank 7.
>
> **`0.3774` appears nowhere** — not in the 50 snapshot rows, not in the live re-read rows, and not
> in any of the five sibling-clone ledgers. The task prompt states it inconsistently (0.3774 in one
> place, 0.3195 in another). Treat it as unconfirmed until an `ORGANIZER-CONFIRMED` receipt exists.
>
> Consequence for the targets above: any improvement computed against `0.3262` understates the gap
> by roughly a third. Reaching live #1 from `h33-2-b2`'s S = 37,654 at K = 7,905 needs
> `T = 5,726`, i.e. credit per dot of `0.1521` against `0.1022` today — **+48.8%**, not the +17.4%
> that `0.3262` implies. Both figures are `PROJECTION` (arithmetic on the verified closed form),
> never scores; the derivation is in
> [`docs/research/lane-expecteddti-findings.md`](docs/research/lane-expecteddti-findings.md).

- **How to Beat `0.2778`, `0.3195`, and `0.3774`**: Because `h33-2-b2` concentrates 95.8% of its picks within $2\text{ km}$ of already-mapped tips, its whole-segment holdout score is only `HOLDOUT-DTI = 0.003814` (`95% CI [0.003033, 0.004641]`, `withheld_positive_pixels = 9,275`, `gems57-pooled-hide-v3-se`). Beating `0.3195` and `0.3774` requires discovering **unmapped off-catalogue fault segments** in piedmont fans and basin interiors using native 1–3 m LiDAR scarp templates, cultural-mimic deconfounding, 20 km block-calibrated spatial CV, and $R=300\text{ m}$ non-maximum suppression (`size=5`) so emitted picks never double-count $\text{FP}_w$.

---

## Five Ranked Untried Geological Hypotheses

| Rank | ID | Hypothesis & Layers | Physical Signature & Why Missing From Catalogue | Difference vs Prior Repo Implementations | Expected / Measured Holdout DTI Gain & Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **H64-U1** *(Implemented as `H64-L1`)* | **Dual-Scale (2 m + 3 m) Slope-Aware Scarplet + Steger/Frangi Hessian + TIGER/Canal/Field Cultural Deconfounding** (`lidar_scarp_features_u8.tif`, `h52_scarp3m_100m.tif`, `tiger_road_distance_m.tif`, `blm_closed_claim_distance_m.tif`, `topo_10m_derived_100m_u8.tif`, `geodawn_extensions_u8.tif`) | Diffusive Quaternary normal/strike-slip scarps ($0.3\text{--}3\text{ m}$ throw) exhibit paired crest convexity ($-\text{LoG}$) and toe concavity ($+\text{LoG}$) plus net $\pm 21\text{ m}$ far-field offset ($h_{\text{gate12}}$), whereas roads, canals, and field edges are double-edged berms lacking 10 m profile curvature (`curv_10m`) and 3 m offset. | `GEMSDOE66` used only 2 m bands and a synthetic morphology proxy that got a *positive* weight (`delta_dti = -5.1e-6`). `H64-L1` fuses 2 m + 3 m stacks with TIGER road and BLM claim distance rasters, yielding negative cultural weights across all 4 spatial folds. | **Measured (`HOLDOUT-DTI`)**: **`+0.017469` (`+2.55 SE`)** over 100 m CV on full LiDAR; **`+0.037743` (`+7.10 SE`)** on off-range-front LiDAR. **Cost**: Low (`205.8 s`). |
| **2** | **H64-U2** | **Morphologic Age ($\kappa t$) Along-Strike Gradient for Propagating Fault Tips** (`scarplet_rel_age`, `dominant_strike`, `h_gate12`) | Propagating normal/strike-slip fault tips show a monotonic decrease in scarp diffusion age $\kappa t$ toward active tips/relay ramps, whereas Pleistocene Lake Lahontan shoreline terraces maintain constant $\kappa t$ along elevation contours. | No prior repo computes along-strike $\partial(\kappa t)/\partial s_{\parallel}$ or separates contour-parallel pluvial beach ridges from cross-contour fault scarps. | **Expected**: `+0.004 to +0.008` HOLDOUT-DTI on pluvial-basin blocks. **Cost**: Low–Medium. |
| **3** | **H64-U3** | **Antithetic Graben Pair Detector (Opposing `upface_max` & `downface_max` Dipole at 100–400 m)** (`upface_max`, `downface_max`, `facing_at`, `dominant_strike`) | Hanging-wall grabens along piedmont normal faults pair a synthetic downhill scarp (`downface_max`) with an antithetic uphill scarp (`upface_max`) across $100\text{--}400\text{ m}$, a geometry impossible for erosional stream banks. | Prior repos treat `upface_max` and `downface_max` as single-cell scalars rather than cross-strike synthetic–antithetic dipoles. | **Expected**: `+0.003 to +0.007` HOLDOUT-DTI on piedmont fan blocks. **Cost**: Low. |
| **4** | **H64-U4** | **Aeromagnetic Upward-Continued Tilt-Derivative Concordance with Sub-Meter Playas** (`TMI_up150`, `ThK`, `h_gate12`, `strike_at`) | Concealed intrabasin faults cutting shallow volcanic/plutonic basement beneath $<50\text{ m}$ of playa fill align horizontal gradients in `TMI_up150` and `ThK` with subtle $<0.5\text{ m}$ playa compaction scarps. | Prior repos thresholded scalar `TMI` without enforcing angular concordance $|\cos 2(\theta_{\text{scarp}} - \theta_{\text{mag}})|$. | **Expected**: `+0.003 to +0.006` HOLDOUT-DTI on concealed basin faults. **Cost**: Medium. |
| **5** | **H64-U5** | **En-Echelon Riedel Shear Stepover Tensor in Walker Lane Transtensional Domains** (`strike2m`, `strike3m`, `coh100`, `derived_sgmc_faults_100m_u8.tif`) | Transtensional strike-slip fault zones in the Walker Lane express at 1–3 m LiDAR scale as left-stepping en-echelon $R$-shears rotated $12^\circ\text{--}18^\circ$ clockwise from the regional basement fault strike. | Existing corridor kernels enforce $0^\circ$ collinearity and penalize en-echelon Riedel stepovers. | **Expected**: `+0.002 to +0.005` HOLDOUT-DTI in Walker Lane blocks. **Cost**: Medium. |

---

## Measured Holdout DTI Results (`evaluator_version = "gems57-pooled-hide-v3-se"`)

All holdout scores below are measured by `src/gems57/evaluate_holdout.py` ($\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel, 1,000 paired 20 km physical spatial-block bootstrap draws on whole-segment buffered holdout `seed=20`):

| Evaluation Domain | Arm | Evidence Class | `HOLDOUT-DTI` | 95% Block-Bootstrap CI | Withheld Positives | $\text{TP}_w$ | $\text{FP}_w$ | Paired $\Delta\text{DTI}$ (`H64-L1` vs Control) | Paired 95% CI | Bootstrap SE | $> 2\,\text{SE}$ Gate |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Full LiDAR Holdout** (`137` clusters) | **`native_lidar_masked_cv` (`H64-L1`)** | `HOLDOUT-DTI` | **`0.074914`** | **`[0.062409, 0.089659]`** | `9,275` | `1,202.2` | `41,939.5` | — | — | — | **PROMOTED** |
| Full LiDAR Holdout | `native_lidar_unmasked` | `HOLDOUT-DTI` | `0.062661` | `[0.054226, 0.071071]` | `9,275` | `1,002.8` | `41,914.1` | **`+0.012253`** | `[+0.001475, +0.024007]` | `0.005854` | **PASS (`+2.09 SE`)** |
| Full LiDAR Holdout | `baseline_100m_cv` | `HOLDOUT-DTI` | `0.057445` | `[0.046509, 0.068822]` | `9,275` | `917.9` | `41,876.4` | **`+0.017469`** | `[+0.005043, +0.032588]` | `0.006850` | **PASS (`+2.55 SE`)** |
| Full LiDAR Holdout | `random_lidar` | `HOLDOUT-DTI` | `0.039761` | `[0.034747, 0.044418]` | `9,275` | `637.6` | `42,435.6` | **`+0.035153`** | `[+0.023126, +0.048485]` | `0.006571` | **PASS (`+5.35 SE`)** |
| Full LiDAR Holdout | `h33_2_b2` (`ORGANIZER-CONFIRMED 0.2778`) | `HOLDOUT-DTI` | `0.003814` | `[0.003033, 0.004641]` | `9,275` | `49.0` | `27,073.8` | **`+0.071099`** | `[+0.058585, +0.085563]` | `0.007025` | **PASS (`+10.12 SE`)** |
| **Off-Range-Front LiDAR** (`136` clusters) | **`native_lidar_masked_cv` (`H64-L1`)** | `HOLDOUT-DTI` | **`0.047812`** | **`[0.037585, 0.058351]`** | `5,195` | `451.7` | `26,009.8` | — | — | — | **PROMOTED** |
| Off-Range-Front LiDAR | `native_lidar_unmasked` | `HOLDOUT-DTI` | `0.034406` | `[0.027187, 0.041335]` | `5,195` | `219.1` | `10,844.1` | **`+0.013406`** | `[+0.002159, +0.024300]` | `0.005546` | **PASS (`+2.42 SE`)** |
| Off-Range-Front LiDAR | `baseline_100m_cv` | `HOLDOUT-DTI` | `0.010069` | `[0.006007, 0.014600]` | `5,195` | `46.3` | `2,143.0` | **`+0.037743`** | `[+0.027813, +0.048624]` | `0.005318` | **PASS (`+7.10 SE`)** |
| Off-Range-Front LiDAR | `random_lidar` | `HOLDOUT-DTI` | `0.028277` | `[0.023923, 0.032681]` | `5,195` | `276.0` | `27,737.8` | **`+0.019535`** | `[+0.010024, +0.030543]` | `0.005180` | **PASS (`+3.77 SE`)** |
| Off-Range-Front LiDAR | `h33_2_b2` (`ORGANIZER-CONFIRMED 0.2778`) | `HOLDOUT-DTI` | `0.001175` | `[0.000758, 0.001673]` | `5,195` | `7.5` | `11,312.8` | **`+0.046637`** | `[+0.036741, +0.057465]` | `0.005407` | **PASS (`+8.63 SE`)** |

---

## Reproducing the Data Restoration, Training, Validation & Site Build

```bash
# 1. Restore and SHA-256-verify competition reference, external LiDAR stacks, pilot 3 m DEM tiles & 67 registry rasters
bash scripts/download_competition_data.sh
.venv/bin/python scripts/prepare_data.py

# 2. Run Experiments 1, 2, and 3 (Native 3 m pilot -> Cultural Mask & Canaries -> 4-Quadrant Spatial CV & Packaging)
.venv/bin/python scripts/run_lidar_scarp_lane.py

# 3. Validate the generated GeoTIFF submission
#    (scripts/check_submission.py is the CLI over the shared src/gems64/validate.py; that module has
#     no __main__ block, so it cannot be invoked as a script directly)
.venv/bin/python scripts/check_submission.py submissions/h64-lidar-scarp-cv-20261011-zeros.tif

# 4. Rebuild and verify the GitHub Pages site and run the test suite
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q

# 5. Rebuild the Expected-DTI-optimal lane's supplementary receipts, findings page and run card
#    (these do not touch docs/*.html, docs/data/ or docs/submissions/)
.venv/bin/python scripts/build_lane_findings_expecteddti.py
.venv/bin/python scripts/make_run_card_expecteddti.py
```

> These commands assume a virtualenv at `.venv/` inside the repository root, which is the
> convention this README already used. In the sandbox where the Expected-DTI lane was run there is
> no in-repo `.venv`; the interpreter was `/home/user/.venv/bin/python` (numpy 2.4.6, scipy 1.17.1,
> scikit-learn 1.9.1, rasterio 1.4.4, pytest). Substituting that path runs every command above
> unchanged.

---

## Canonical JSON RUN CARD — published ([`evidence/run_card.json`](evidence/run_card.json))

```json
{
  "run_id": "g64-lidar-scarp-cv-20261011",
  "hypothesis_id": "H64-L1",
  "lane": "Native-resolution LiDAR scarp channels + cultural-feature mask + 4-quadrant spatial CV",
  "evidence_class": "HOLDOUT-DTI",
  "evaluator_version": "gems57-pooled-hide-v3-se",
  "holdout_dti_full_lidar": {
    "dti": 0.07491384859445377,
    "ci95": [0.06240907201919719, 0.08965916830041551],
    "withheld_positive_pixels": 9275,
    "delta_vs_baseline_100m_cv": 0.01746908144222204,
    "delta_vs_native_lidar_unmasked": 0.01225330066139027,
    "beats_two_se_all_controls": true
  },
  "holdout_dti_off_range_front_lidar": {
    "dti": 0.047812333954015844,
    "ci95": [0.037585397847664154, 0.058351496253216055],
    "withheld_positive_pixels": 5195,
    "delta_vs_baseline_100m_cv": 0.037743149740378006,
    "delta_vs_native_lidar_unmasked": 0.01340645806666517,
    "beats_two_se_all_controls": true
  },
  "leakage_canary_max_directional_auc": 0.5948510430496051,
  "pre_placement_surface_max_abs_spearman": 0.12393885129220754,
  "final_dots_max_abs_spearman_all_67": 0.039379740590634635,
  "final_dots_max_3px_overlap_geological_62": 0.4547111111111111,
  "raster_zeros_file": "submissions/h64-lidar-scarp-cv-20261011-zeros.tif",
  "raster_zeros_sha256": "919dfc5f9e429a8bae0784244191a23cc0d50fa265b8f5085a01f9644ab9e97c",
  "raster_nan_file": "submissions/h64-lidar-scarp-cv-20261011-nan.tif",
  "raster_nan_sha256": "62e330bb8df511c33ac0a3c977f8067b7d72d84324fe2c5d7d901b88c253869b",
  "validator_format_pass": true,
  "submission_name": "h64-lidar-scarp-cv-20261011",
  "submission_note": "H64-L1 native 1-3m LiDAR scarplet+Steger/Frangi 100m + TIGER/canal/field cultural mask + 4-quad spatial CV",
  "verdict": "promote"
}
```

## Supplementary evidence set (run 64b, merged unmodified)

A parallel session produced an independent, catalogue-independent lidar-scarp evidence set for the
same lane. It does **not** change the published card, the promoted candidate, or the site's single
published artifact; it is merged as supplementary evidence, and its artifact sits in `submissions/`
beside the others as an audit file with its own measured negative verdict.

* receipts — `evidence/e1_sgmc_off.json` (`PROXY-INSTRUMENT (sgmc_off)`),
  `evidence/e2_catalogue_hide.json` (`HOLDOUT-DTI (catalogue_hide)`),
  `evidence/e3_emission.json` (`REGISTRY-MEASUREMENT`, 62 comparators);
* code — `src/gems64/lane.py`, `src/gems64/instrument.py`, `src/gems64/registry_policy.py`,
  `src/gems64/ridge.py`, `scripts/run_lane.py`, `scripts/assemble_inputs.py`;
* write-up — [`docs/research/lane64-ampsnr-findings.md`](docs/research/lane64-ampsnr-findings.md);
* frozen gates — [`PREREGISTRATION.md`](PREREGISTRATION.md);
* audit artifact — `submissions/gems64-lane-ampsnr-37654-20261011.tif` (sha256 `534eea95…`).

Decision-relevant result of that set: on `PROXY-INSTRUMENT (sgmc_off)` the `amp_snr` field beats the
owner-reported champion pooled (+0.04150, SE 0.01716) but **loses the interior stratum decisively**
(champion 0.08767 vs candidate 0.01433, paired −0.07333, SE 0.01060), does not clear its
terrain-matched control, is tied with the controls on `HOLDOUT-DTI (catalogue_hide)`, and its dot
pattern is 88.8 % within 3 px of `gems32-bayesopt-dilation-scarp-d28-*` — the same
interior-versus-range-front lesson this repository records elsewhere, from a second construction.
No weekly slot was used by either set.

---

## Supplementary evidence set — the Expected-DTI-optimal lane (merged alongside run 64b)

A parallel session implemented the **Expected-DTI-optimal selection** lane: replace heuristic dot
spacing with a decision rule on a calibrated surface, greedy-add the candidate pixel with the
largest mean DTI gain under the repository's exact kernel metric over an ensemble of 32 plausible
truth rasters, then prune backward, and gate the result against spacing placement by more than two
block-bootstrap SEs.

> **Its verdict is `negative` — DO NOT DOWNLOAD AND DO NOT SUBMIT ITS GEOTIFF.** It is an audit
> artifact, not a candidate. The promoted submission remains
> `submissions/h64-lidar-scarp-cv-20261011-zeros.tif`, and `docs/submissions/` still holds exactly
> the two promoted TIFFs, as `scripts/check_site.py` and `tests/test_policy.py` require. **No weekly
> slot was spent by this lane.**

* write-up — [`docs/research/lane-expecteddti-findings.md`](docs/research/lane-expecteddti-findings.md),
  generated from the receipts by `scripts/build_lane_findings_expecteddti.py` with no hand-entered
  numbers;
* run card — [`evidence/run_card_expecteddti.json`](evidence/run_card_expecteddti.json), built by
  `scripts/make_run_card_expecteddti.py`;
* receipts — `evidence/lane_expecteddti_exp1_rule.json` (`VERIFIED`, 7/7 checks),
  `_exp2_inversion.json` (`ORGANIZER-CONFIRMED` receipts inverted through the verified closed form),
  `_exp3a_field.json` / `_exp3b_field.json` (`HOLDOUT-AUC`, spatially blocked),
  `_exp3b_leaky_audit.json` (the quarantined first instrument, kept as the audit trail),
  `_exp3c_emission.json` (`SELF-CONSISTENT OBJECTIVE`), `_exp3d_gate.json` (gate, LANE check,
  shared-validator receipts);
* code — `src/gems64/lane_expecteddti/{gridext,metricext,engine,emission}.py` and
  `scripts/lane_expecteddti_*.py`. These **keep no private fork**: grid constants come from
  `gems64.grid`, and the kernel, lattice offsets, α/β, brute-force oracle and marginal rule come from
  `gems64.metric`; the gate calls the shared `gems64.validate`. What the lane originally shipped as
  its own `grid.py`, `metric.py`, `validate_submission.py`, `emission.py` and site builder were
  de-forked into these supplementary modules at merge time;
* artifact — `submissions/gems64-expecteddti-flank0.158-14k-20261011T210000Z-af6336e0-zeros.tif`
  (sha256 `abc46d756dc437ea…`, 14,075 positive px, `PASS` 18/18 shared-validator checks) and its
  `-nan` comparison twin (`FAIL` 16/18 — must never be uploaded).

Decision-relevant result of that set: the **rule is verified** — joint greedy beat independent
thresholding on 5/5 held-out draws with identical `TP_w` at 18–31× less mass, confirming that the
3-px kernel makes adjacent picks redundant — and it beat spacing placement by
z = +15.97 on 32/32 held-out draws. But the **surface is saturated**: 1.94 % of scored cells sit at
raw score 1.0 and the top 200,000 candidates span 0.0003 of score range with only 4,907 distinct
values, so the ranking that selects every dot is decided by numpy's tie order rather than by
geology. A verified optimal rule pointed at an uninformative surface yields an arbitrary dot set
that looks excellent against truth sampled from itself.

Its most transferable finding is a **live-anchored inversion** of the registry's one controlled pair
(`h27-4-r1-solo-d2-8` at 0.2708 with 2,545 dots inside 2 px of the published catalogue, versus
`h33-2-b2` at 0.2778 with zero): dots within 200 m of the catalogue realise ≈0.016 credit each
against ≈0.102 for the dots kept, a **6.3× depletion** that holds for every plausible hidden-truth
size K = 6,000–12,691. Removing that flank band was therefore *required* by the marginal rule, and
0.2778 is explained without invoking any detection improvement. The negative control
`sgmc-off-catalogue-44k` at **0.0512** bounds every off-catalogue hypothesis: being off-catalogue is
necessary but nowhere near sufficient.

---

## The full prompt (read this every session)

<details>
<summary><b>Click to expand the verbatim task specification this repository is built against.</b></summary>

### Primary task

Generate a **unique, downloadable GeoTIFF submission** for DrivenData competition 306 "DOE GEMS"
(geothermal exploration / hidden-fault prediction, northwestern Great Basin, Nevada; EPSG:32611,
100 m grid).

**Assigned LANE (single method paragraph — stay inside it):**

> **Expected-DTI-optimal selection.** Replace heuristic spacing with a decision rule on a
> calibrated surface. For a Tversky-family score with α+β=1, adding a pixel raises expected score
> when its calibrated probability exceeds α × the optimal score; for DTI (α=0.2) that is ≈0.06 at
> DTI 0.30. Extends Lipton, Elkan & Narayanaswamy (ECML-PKDD 2014: F1-optimal threshold = half
> optimal F1) — must verify numerically on synthetic rasters first. 3-px kernel makes adjacent
> picks redundant → do NOT threshold independently. Calibrate by isotonic regression on spatially
> blocked, buffered out-of-fold predictions. Treat ensemble/TTA/MC-dropout outputs (jittered 1–2
> px) as ≥32 plausible truth rasters. Greedily add the ridge-candidate pixel with largest mean DTI
> gain under the repo's exact kernel metric, then prune backward until marginal gain ≤ 0. Gate:
> beat current spacing/MCLP placement on the same surface by >2 block-bootstrap SEs. Finish:
> normalize to [0,1]; write float32 EPSG:32611 100 m GeoTIFF (NaN only outside footprint); pass
> `validate_submission.py`; hash/pixel-agreement check against ALL prior rasters; offer download
> ONLY if gate met, else log the negative result.

### Parallel-run protocol (also mandatory)

1. **LANE discipline**: if rank-correlation with any registry raster >0.90, or >70% of dots fall
   within 3 px of one registry raster's dots → log as duplicate and STOP. Check on surface before
   placement AND on final dots.
2. **REUSE, DON'T REBUILD**: use the template's cached feature stack, `evaluate_holdout.py`,
   `submission_writer.py`. Holdout = hide-and-recover: withhold whole fault segments with buffer,
   derive every catalogue-based feature only from visible faults, mask visible faults pixel-exactly,
   score pooled DTI (α=0.2, β=0.8, 300 m triangular kernel). Fix shared tools once in the template
   and report; never keep a private fork.
3. **LABEL EVERY NUMBER** as `HOLDOUT-DTI (evaluator version, #withheld positives, 95% CI)` or
   `ORGANIZER-CONFIRMED (submission-page receipt)`. A projection is never written as a score.
4. **LEAKAGE CANARY**: test each feature alone on holdout first; AUC >0.90 = leakage until proven
   otherwise.
5. **RUN CARD**: end with one JSON card containing hypothesis; mechanism; named non-fault process
   that could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator
   output (no NaN inside footprint, values in [0,1], CRS/shape/transform match); submission name +
   note ≤140 chars; verdict promote/negative. **Negative results ARE deliverables.**
6. **BUDGET**: stop after 3 experiments or 2 hours. Do not pick submissions / spend slots —
   promotion is a separate selector step within the weekly cap.

### Also required

- Answer (PhD-level) **WHY** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored **0.2778**
  (highest on the GEMSDOE32 site) and whether we can beat it.
- Produce **3–5 NEW candidate geological hypotheses** (each naming layers, physical
  signature/transform, why it catches a fault **MISSING** from the USGS/INGENIOUS catalogue rather
  than an existing one, how it differs from anything already in the repo), ranked by expected DTI
  gain vs implementation cost, with the top one validated on the spatially-blocked holdout
  **BEFORE** touching a submission slot.
- Name the specific **free official data source** needed if a candidate requires new external data,
  and verify obtainability.
- Put the **full prompt into the repo README** and re-read it each session.
- Build a clean **GitHub Pages site** with obvious download of the submission TIF plus an
  executive-summary subpage explaining exactly how to submit; include a **unique submission name**
  and a **short note** (e.g. "clustering with k=25").
- Fix the previously-reported submission error **`"Predicted values must be in range [0, 1]"`**.
- Work autonomously, no manual input; verify line by line from official sources with links for
  manual review; flag irregularities; **NO hallucinations**.
- Run **3 passes** (implement → review for bugs/edge cases → re-check against original request).
- Finish by creating a **PR and merging it to `main`**, plus suggestions for remaining work and
  limitations.

### Core values to keep central

**"Maximize P(Win)"** and **"Own the Outcome"**.

</details>

---

## Values

**Maximize P(Win).** Every claim here is either verified numerically in this repository or labeled
with the class of evidence it actually is. A negative result recorded honestly raises P(Win) more
than a plausible-looking artifact that fails on the leaderboard, because it prevents a wasted
submission slot — and slots are capped at three per week with exactly one final selection made
without private-score knowledge.

**Own the Outcome.** The gate decides whether the artifact ships. It is not overridden by
preference, and the negative result is published with the same prominence as a positive one.
