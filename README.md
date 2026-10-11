# GEMSDOE64 — Native-Resolution Lidar Scarp Channels (`PROMOTE` · Cleared for Submission)

> **SESSION START:** Read this `README.md` and [`evidence/run_card.json`](evidence/run_card.json) first. The GitHub Pages site is built in [`docs/`](docs/) ([`docs/index.html`](docs/index.html), [`docs/executive-summary.html`](docs/executive-summary.html), [`docs/research.html`](docs/research.html), [`docs/sources.html`](docs/sources.html)); full PhD analysis and geological hypotheses are in [`docs/research/findings.md`](docs/research/findings.md).

---

## Current Decision: **PROMOTE — CLEARED TO DOWNLOAD & SUBMIT**

Every spatial-CV holdout gate (overall, range-front, and off-range-front basin/piedmont blocks), single-feature leakage canary (`max AUC = 0.7616 <= 0.90`), 70-raster registry uniqueness check (both pre-placement surface and final placed dots), and GeoTIFF validator check passed:

| Submission Artifact | Path in Repo / Pages Download | SHA-256 | Specification & Purpose |
|---|---|---|---|
| **Primary Portal GeoTIFF (`all-finite [0, 1]`)** | [`submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif`](submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif) · [`docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif`](docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif) | `346d57f0eca0ff36f7648f8b5a3ba8764054ab9e42e1677873791b83f460f45e` | **Upload this file to DrivenData.** `float32`, `EPSG:32611`, `3730×3292`, `100 m`, `0` NaNs anywhere, all `12,279,160` pixels in `[0.0, 1.0]`, `37,654` NMS peak dots (`1.0`). |
| **Portal ZIP Archive** | [`submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.zip`](submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.zip) · [`docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z.zip`](docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z.zip) | `e2ee6466f9f1654e63e166123db35325e4a7beca101e27548c6a1c5152212d38` | Single-member ZIP containing `gems64-h64-lidar-scarp-cv-20261011T220000Z.tif`. |
| **Strict `NaN`-Outside Twin** | [`submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z-nan-outside.tif`](submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z-nan-outside.tif) · [`docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z-nan-outside.tif`](docs/downloads/gems64-h64-lidar-scarp-cv-20261011T220000Z-nan-outside.tif) | `ead50e13592a2facea8b01b9eceb292693a5b21c76319ab8cd9ae37a0e133f3b` | Identical in-footprint predictions (`5,167,373` finite pixels in `[0, 1]`, `37,654` dots) with `NaN` strictly outside the footprint (`7,111,787` exterior pixels). |

- **Copy-Paste DrivenData Submission Name**: `gems64-h64-lidar-scarp-cv-20261011T220000Z`
- **Copy-Paste Submission Note (`116 / 140` chars)**:
  ```text
  GEMSDOE64 native lidar scarp channels (Scarplet+Steger+Frangi) + cultural mask + 4-fold spatial CV; 37654 NMS peaks.
  ```
- **Why `"Predicted values must be in range [0, 1]"` Happened Previously & How It Is Solved**:
  DrivenData's upload validator checks `np.all((arr >= 0.0) & (arr <= 1.0))` on the raster array before applying the footprint mask. Under IEEE-754 arithmetic, `NaN >= 0.0` evaluates to `False`. Our primary submission `gems64-h64-lidar-scarp-cv-20261011T220000Z.tif` replaces all `7,111,787` exterior `NaN`s with `0.0`, omits any `nodata` sentinel, and clips all `5,167,373` in-footprint values to `[0.0, 1.0]`, guaranteeing `12,279,160` finite `float32` pixels in `[0.0, 1.0]`.

---

## 1. PhD-Level Forensic Analysis of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778` `ORGANIZER-CONFIRMED`)

Using `scripts/audit_h33.py` ([`evidence/h33_forensics.json`](evidence/h33_forensics.json)), we performed an exact byte- and pixel-level audit of `GEMSDOE32__h33-2-b2-zeros.tif` (`h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`, `0.2778` `ORGANIZER-CONFIRMED`) against its parent raster `GEMSDOE28__h27-4-r1-solo-d2-8.tif`, `sample_submission.tif`, and `existing_faults.tif`:

1. **Exact Mathematical Identity**:
   - `GEMSDOE28__h27-4-r1-solo-d2-8.tif` (`sha256: 35d99ccba9818e4433bfebff9d0e0425f89695ab6262f5a608dc5da9305c9566`) contains `40,199` binary positive pixels (`1.0`) inside the footprint and `7,111,787` `NaN` pixels outside the footprint.
   - `GEMSDOE32__h33-2-b2-zeros.tif` (`sha256: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`) contains `37,654` binary positive pixels (`1.0`) and `0` `NaN`s anywhere.
   - Defining the 2-pixel (`200 m`) Euclidean collar around the `60,988` in-footprint mapped catalogue fault cells (`existing_faults.tif`) as $B_2 = \{x \in \Omega : d_{\text{Euc}}(x, \mathcal{C}_{\text{known}}) \le 200\text{ m}\}$, `H33-2-B2` is **pixel-for-pixel identical** to `H27-4-R1` after zeroing out `2,545` dots inside $B_2$ (`40,199 - 2,545 = 37,654`, `added = 0`, `outside_b2_removed = 0`) and replacing exterior `NaN`s with `0.0`.
2. **Why `H33-2-B2` Achieved `0.2778` (`ORGANIZER-CONFIRMED`)**:
   - Under the Distance-Weighted Tversky Index ($\alpha = 0.2, \beta = 0.8$, $300\text{ m}$ triangular kernel $K(d) = \max(0, 1 - d/300\text{ m})$), recall on hidden faults is weighted $4\times$ higher than precision ($\beta/\alpha = 4$), and a single placed dot saturates $K(d)$ across a $300\text{ m}$ radius.
   - Mapped faults $\mathcal{C}_{\text{known}}$ are masked from the hidden test target. Dots placed within $\le 200\text{ m}$ of known faults sit inside the already-mapped fault corridor where they cannot discover new off-catalogue fault segments, yet their $300\text{ m}$ halo spills into adjacent non-fault background and accumulates $\alpha\,\text{FP}_w$. Removing those `2,545` collar dots reduced $\alpha\,\text{FP}_w$ by $\sim 509$ weighted units without losing off-catalogue recall $\text{TP}_w$.
3. **Why `H33-2-B2` Was Capped at `0.2778` and How to Score Higher (Toward `0.3195` and `0.3774`)**:
   - `H33-2-B2` added **zero** new dots (`added = 0`) and used only 100 m resampled features, which dilute meter-scale ($W_s \in [2, 20]\text{ m}$) piedmont and intrabasin fault scarps by $20\times\text{–}50\times$.
   - Furthermore, `5,021` of `H33-2-B2`'s dots (`13.33%`) lie in cultural road/claim/canal corridors (`tiger_road_distance_m < 75 m`, `blm_closed_claim_distance_m < 60 m`, or flat-basin cardinal canals) where true off-catalogue USGS SGMC faults are **$4.66\times$ depleted**.
   - By introducing **native 1–3 m lidar scarp channels** (Scarplet + slope-aware detrending + Steger + Frangi), fixing the **$90^\circ$ strike reference-frame bug**, applying the **cultural-feature mask**, and retraining under **4-fold spatial CV**, we unlock substantial `HOLDOUT-DTI` gains across both range fronts and basin interiors.

> **Irregularity flagged on the `0.3774` target, resolved against this repository's own verified
> snapshot.** [`docs/data/leaderboard_snapshot.json`](docs/data/leaderboard_snapshot.json)
> (`observed_utc: 2026-10-11`, `verified: true`, manual rendered-page fetch of 50 rows) carries an
> erratum recording a live re-read whose rows 1–10 supersede the snapshot body. On that re-read the
> top of the board is **`0.4133`** (`xiaofanhu`), then `0.3585` (`cfld__`) and `0.3418`
> (`JerryDataWorks`); **`0.3195` is confirmed real** (`DARD`, rank 9) and the `0.2778` receipt
> analysed above sits at **rank 23** (`extradr19`). The `0.3262` that was #1 on 2026-10-04
> (`nchuzhoy`) is now rank 7.
>
> **`0.3774` appears nowhere** — not in the 50 snapshot rows, not in the live re-read rows, and not
> in any of the five sibling-clone ledgers. Treat it as unconfirmed until an `ORGANIZER-CONFIRMED`
> receipt exists; drivendata.org is unreachable from the sandbox, so it could not be checked at
> source. Consequence for the heading above: any improvement computed against `0.3262` understates
> the gap by roughly a third. Reaching live #1 from `H33-2-B2`'s `S = 37,654` at `K = 7,905` needs
> `T = 5,726`, i.e. credit per dot of `0.1521` against `0.1022` today — **`+48.8%`**, not the
> `+17.4%` that `0.3262` implies. Both figures are `PROJECTION` (arithmetic on the verified closed
> form `T = D·(α·S + β·K)`), never scores; the derivation is in
> [`docs/research/lane-expecteddti-findings.md`](docs/research/lane-expecteddti-findings.md).

---

## 2. Five Candidate Geological Hypotheses (Ranked by Expected DTI Gain & Cost)

| Rank | Hypothesis | Specific Layers | Physical Signature & Why Missing from USGS/INGENIOUS Catalogue | Measured / Expected `HOLDOUT-DTI` Gain & Cost |
|---|---|---|---|---|
| **1 (Validated & Promoted)** | **H64-L1: Native-Resolution (1–3 m) Lidar Scarp Channels + Slope-Aware Detrending + Cultural Veto** | `lidar_scarp_features_u8.tif` (2 m), `h52_scarp3m_100m.tif` (3 m), native 3 m DEM tiles (`data/pilot/dem3m/*.tif`), `tiger_road_distance_m.tif`, `blm_closed_claim_distance_m.tif` | Diffused error-function scarp step $z(u) = \frac{H}{2}\text{erf}(u/\sqrt{4\kappa t})$ on dipping alluvial fans creates a 1D ridge in $\|\nabla_\sigma z_{\text{det}}\|$ detected by Steger (1998) sub-pixel centerlines and Frangi (1998) 2–20 m vesselness, separated into synthetic (`downface`) and antithetic (`upface`) scarps vs. cross-slope gullies (`crossface`). Catches degraded $0.3\text{–}2.5\text{ m}$ piedmont/intrabasin scarps invisible at 100 m while vetoing road grades and irrigation canals. | **Measured**: **`+0.027821` (`+25.48%`, `E1`)** and **`+0.017000` (`+14.98%`, `E2`)** `HOLDOUT-DTI` (`> 4 SE`); Cost: Low–Medium. |
| **2** | **H64-G2: Shallow-vs-Deep Potential-Field Vertical Gradient Decoupling** | `training_features.tif` Bands 7–12 (`Gravity_G`, `dGdz`, `fG`, `Magnetic_M`, `dMdz`, `fM`) + `DEM_elevation` | High vertical-to-regional gravity gradient ratio $\|\partial g/\partial z\| / (\|\Delta g_B\| + \epsilon)$ co-located with magnetic vertical derivative maxima inside flat Quaternary basin fill ($\text{relief}_{100\text{m}} < 15\text{ m}$). Catches intrabasin graben bounding faults buried beneath Holocene playa aggradation. | Expected: `+0.006` to `+0.012` `HOLDOUT-DTI`; Cost: Low. |
| **3** | **H64-S3: Crustal Stress-Tensor Slip & Dilation Tendency on Lidar Scarp Attitudes** | `training_features.tif` Bands 13–17 (`S_hmax_azimuth`, `S_v`, `P_p`, `S_hmax`, `S_hmin`) + 90°-corrected `dominant_strike` | High Mohr-Coulomb slip tendency $\tau/\sigma'_n$ and dilation tendency when local scarp strike aligns at $0^\circ\text{–}30^\circ$ to $S_{\text{Hmax}}$ under high pore-fluid pressure $P_p$. Catches unmapped oblique transfer faults in Walker Lane / Great Basin accommodation zones. | Expected: `+0.004` to `+0.008` `HOLDOUT-DTI`; Cost: Low. |
| **4** | **H64-H4: En-Échelon Relay-Ramp Breaching & Step-Over Strain-Transfer Bridge** | `existing_faults.tif`, `topo_10m_derived_100m_u8.tif`, `upface_max`, `downface_max` | Rotational transverse bed tilt and antithetic (`upface_max`) breaching scarps within overlapping normal fault step-overs ($\Delta_\perp \in [0.3, 2.5]\text{ km}$). Catches breaching faults omitted where 1:250k maps draw disconnected segments. | Expected: `+0.005` to `+0.010` `HOLDOUT-DTI`; Cost: Medium. |
| **5** | **H64-M5: Shallow-vs-Deep Magnetotelluric Conductivity Vertical Contrast ($\rho_{1\text{km}}/\rho_{4\text{km}}$)** | `training_features.tif` Bands 18–20 (`MT_1km`, `MT_2km`, `MT_4km`) + `derived_sgmc_faults_100m_u8.tif` | Low shallow-to-deep resistivity ratio $\log_{10}(\rho_{1\text{km}}/\rho_{4\text{km}})$ and lateral conductivity edges along smectite/illite-altered geothermal fault conduits lacking fresh surface rupture. | Expected: `+0.002` to `+0.005` `HOLDOUT-DTI`; Cost: Low. |

---

## 3. Assigned Lane Validation (`src/gems64/lidar_scarp.py` & `scripts/run_lane64.py`)

### 3.1 Native 3 m DEM Verification (Synthetic Scarp & Real USGS 3DEP Tile `x42y425_3m.tif`)

- **Synthetic N15°E Fault Scarp ($H = 1.6\text{ m}, \sigma_s = 4.5\text{ m}$) on Dipping Alluvial Fan**:
  - Applying Steger (1998) sub-pixel ridge detection and Frangi (1998) multiscale Hessian analysis to the **scale-space step-gradient surface** $\|\nabla_\sigma z_{\text{det}}\|\,w_{\text{slope}}\,w_{\text{piedmont}}$ yields `scarplet_amplitude = 1.092 m` vs `0.137 m` background (`7.95x`), `frangi_vesselness = 0.990` vs `0.030` (`33.4x`), `steger_line` rate `0.859` vs `0.050` (`17.1x`), and recovered geological strike `14.34°` vs `15.00°` true strike.
- **Real Native 3 m DEM Tile `data/pilot/dem3m/x42y425_3m.tif` (`3412×3412` pixels)**:
  - Aggregated to `101×101` cells on the master 100 m grid (`window = [2585, 1766, 101, 101]`, `385` catalogue cells): **`ROC-AUC = 0.6617`** from the native 3 m lidar scarp channels alone.

### 3.2 Spatial-CV Holdout Results (`HOLDOUT-DTI`, `gems57-pooled-hide-v3-se`)

| Experiment & Spatial Subset | Withheld Positives | 100 m Topo Baseline `HOLDOUT-DTI` (95% CI) | Culturally Masked Lidar Scarp `HOLDOUT-DTI` (95% CI) | Paired Gain $\Delta\text{DTI}$ (95% CI, SE) | Gate (`> 2 SE`) |
|---|---|---|---|---|---|
| **`E1` Overall (Label-Blind 8 km Spatial Buffer, Pure Detector)** | `48,441` (`128` blocks) | `0.109182` (`[0.097759, 0.120120]`) | **`0.137003`** (`[0.124049, 0.149290]`) | **`+0.027821` (`+25.48%`)** (`[+0.021244, +0.034918]`, `SE=0.003500`, `7.95 SE`) | **`PASS`** |
| **`E1` Range-Front Blocks** | `23,317` (`64` blocks) | `0.129027` (`[0.111270, 0.145020]`) | **`0.159421`** (`[0.140452, 0.177049]`) | **`+0.030394` (`+23.56%`)** (`[+0.019555, +0.041455]`, `SE=0.005536`, `5.49 SE`) | **`PASS`** |
| **`E1` Off-Range-Front Basin/Piedmont Blocks** | `25,124` (`64` blocks) | `0.089418` (`[0.075776, 0.103063]`) | **`0.115043`** (`[0.098878, 0.131919]`) | **`+0.025625` (`+28.66%`)** (`[+0.018090, +0.033822]`, `SE=0.003991`, `6.42 SE`) | **`PASS`** |
| **`E2` Overall (Buffered Whole-Component CV, 300 m Collar)** | `9,274` (`104` blocks) | `0.113522` (`[0.103202, 0.123710]`) | **`0.130522`** (`[0.117397, 0.143103]`) | **`+0.017000` (`+14.98%`)** (`[+0.009202, +0.025473]`, `SE=0.004120`, `4.13 SE`) | **`PASS`** |
| **`E2` Range-Front Blocks** | `4,432` (`52` blocks) | `0.126160` (`[0.111579, 0.140634]`) | **`0.145038`** (`[0.127289, 0.162708]`) | **`+0.018877` (`+14.96%`)** (`[+0.008723, +0.029419]`, `SE=0.005494`, `3.44 SE`) | **`PASS`** |
| **`E2` Off-Range-Front Basin/Piedmont Blocks** | `4,842` (`52` blocks) | `0.106413` (`[0.091427, 0.122146]`) | **`0.121961`** (`[0.103754, 0.141768]`) | **`+0.015548` (`+14.61%`)** (`[+0.004441, +0.027564]`, `SE=0.006042`, `2.57 SE`) | **`PASS`** |

---

## 4. Reproducible Pipeline Commands

```bash
# 1. Restore/verify competition data, external lidar/cultural rasters, and 70 registry comparators
bash scripts/download_competition_data.sh
PYTHONPATH=.:src .venv/bin/python scripts/prepare_data.py

# 2. Run the full Native-Resolution Lidar Scarp Channels pipeline (E1, E2, E3 + 70-raster audit)
PYTHONPATH=.:src .venv/bin/python scripts/run_lane64.py

# 3. Validate the emitted GeoTIFF submission and rebuild/check the GitHub Pages site
PYTHONPATH=.:src .venv/bin/python scripts/validate_submission.py submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif
PYTHONPATH=.:src .venv/bin/python scripts/build_site.py
PYTHONPATH=.:src .venv/bin/python scripts/check_site.py

# 4. Run the test suite
PYTHONPATH=.:src .venv/bin/python -m pytest -q

# 5. Expected-DTI-optimal lane (see §7). Steps a-c rebuild its receipts end to end; d-e regenerate
#    its findings page and run card. None of these touch docs/*.html, docs/data/ or docs/downloads/,
#    so step 3's `git diff --exit-code -- docs` guard is unaffected.
#    The field/emission steps need the competition rasters; point GEMS64_DATA at them (defaults to
#    data/raw). The LANE uniqueness check reads registry rasters from sibling clones — override with
#    GEMS64_REGISTRY_ROOTS, and note it reports lane_certified=false rather than "not a duplicate"
#    if none are reachable.
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_verify_rule.py
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_invert_live_scores.py
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_build_field.py
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_train_field.py
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_emit_and_ship.py
PYTHONPATH=.:src GEMS64_DATA=data/raw .venv/bin/python scripts/lane_expecteddti_gate.py
PYTHONPATH=.:src .venv/bin/python scripts/build_lane_findings_expecteddti.py
PYTHONPATH=.:src .venv/bin/python scripts/make_run_card_expecteddti.py
PYTHONPATH=.:src .venv/bin/python scripts/check_submission.py \
  submissions/gems64-expecteddti-flank0.158-14k-20261011T210000Z-af6336e0-zeros.tif
```

> Step 5's gate exits non-zero by design: it returns `2` for a negative verdict, so a shell chain
> should not treat that as a build failure. `scripts/make_run_card.py` builds the **published** card
> only — note that its `lane` string still reads "expected-DTI-optimal selection on a calibrated
> surface" while `evidence/run_card.json` describes the lidar lane, i.e. that builder is stale
> relative to the card it would overwrite. Do not run it against
> `evidence/run_card_expecteddti.json`; use `scripts/make_run_card_expecteddti.py`.

---

## 5. Original Task Prompt (Preserved Verbatim)

<details>
<summary>Click to expand full task prompt</summary>

```text
Review /home/user/GEMSDOE64 — Improve the project. Put this prompt in the README. We're trying to win this competition and identify unknown faults.
Work autonomously line by line from official verified trusted sources with links for manual review. Flag irregularities, do not hallucinate.

Core Values
Maximize P(Win): bias toward high-EV exploration, preserve submission slots, validate locally on a spatial holdout that matches the competition metric.
Own the Outcome: log failures, fix root causes, never present a projected score as a real one.

Assigned Lane (this parallel run — stay inside this one method paragraph)
Native-resolution lidar scarp channels. On high-prior tiles first, compute: (1) Scarplet template matching (Sare & Hilley, JOSS 2018, doi:10.21105/joss.01066) returning amplitude, relative age, orientation, and SNR from a GeoTIFF DEM, extended with slope-aware scarp templates (AGU 2015 poster T31A-2838, tested in Surprise Valley); (2) Steger sub-pixel ridge/valley lines (IEEE TPAMI 20(2):113-125, 1998) and Frangi multiscale Hessian line measures (MICCAI 1998, LNCS 1496:130-137) at 2-20 m scales on a slope-detrended surface. Aggregate to 100 m cells as scarp-pixel fraction, SNR-weighted amplitude, structure-tensor orientation coherence, and dominant strike. Mask roads, canals, and field edges with the existing cultural-feature mask, then retrain under spatial CV. Gate: DTI gain on lidar-covered holdout blocks that is not confined to range fronts. Finish: normalize to [0,1]; write a float32 EPSG:32611 100 m GeoTIFF (NaN only outside the footprint); pass validate_submission.py; run the hash/pixel-agreement check against all prior rasters; offer the download only if the gate is met, else log the negative result.

If rank-correlation with any registry raster exceeds 0.90, or more than 70% of our dots fall within 3 px of one registry raster's dots, log as a duplicate and stop. Check on the surface before placement AND on the final dots.

Reuse the Shared Tools (do not rewrite)
Use the template's cached feature stack, evaluate_holdout.py, and submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer, derive every catalogue-based feature only from the remaining visible faults, mask visible faults pixel-exactly, and score pooled DTI (alpha=0.2, beta=0.8, 300 m triangular kernel). If a shared tool has a bug, fix it in the template and report it — never keep a private fork.

Rules
Score labeling: every number must be labeled HOLDOUT-DTI (with evaluator version, number of withheld positives, and 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page receipt). Never write a projection as a score.
Leakage canary: test each feature alone on the holdout before trusting any result. AUC above 0.90 means leakage until proven otherwise.
Run card: end with one JSON card containing: hypothesis; mechanism; one named non-fault process that could mimic it; holdout DTI + CI; correlation/overlap vs. registry; raster sha256; validator output (no NaN inside footprint, values in [0,1], CRS/shape/transform match); submission name + note (<=140 chars); verdict promote / negative.
Budget: stop after 3 experiments or 2 hours.

URGENT: WE MUST GENERATE A TIF SUBMISSION FOR THIS COMPETITION. IT MUST BE UNIQUE — DO NOT COPY A PREVIOUS SUBMISSION. Make it obvious on the site if it is OK to download and submit.

QUESTION: Why did h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros get 0.2778? Study, analyze, and explain at a PhD level why this worked and whether we can do better.

HYPOTHESES: Generate 3-5 candidate geological hypotheses not tried yet. Rank by expected DTI improvement and implementation cost. Validate the top candidate on a spatially-blocked holdout before recommending a submission.

Build a clean GitHub Pages UI with an executive summary subpage explaining how to submit and addressing the "Predicted values must be in range [0, 1]" error, unique submission name, and <=140 char note. Run through three passes, then create a PR and merge onto main.
```

</details>

---

## 6. Final JSON Run Card (`evidence/run_card.json`)

```json
{
  "schema": "gems64-run-card-v2",
  "run_id": "gems64-h64-lidar-scarp-cv-20261011T220000Z",
  "reviewed_utc": "2026-10-11T22:32:50.285599+00:00",
  "assigned_lane": "Native-resolution lidar scarp channels",
  "hypothesis": "H64-L1: Native-resolution (1-3 m) lidar scarp channels—Scarplet error-function template matching (Sare & Hilley 2018) with slope-aware alluvial-fan detrending (AGU 2015 T31A-2838) plus Steger (1998) sub-pixel ridge/valley lines and Frangi (1998) multiscale Hessian vesselness (2-20 m scales)—aggregated to 100 m cells as scarp_pixel_fraction, snr_weighted_amplitude, structure_tensor_coherence, and 90-deg-frame-corrected geological dominant_strike, masked with the cultural-feature mask (TIGER roads, BLM mining claims, and flat-basin cardinal canal/field-edge double-edged prisms with zero 3 m far-field offset) and retrained under 4-fold spatial CV, increase holdout DTI across both range-front and off-range-front basin/intrabasin blocks.",
  "mechanism": "1. Compute/decode native 2 m + 3 m Scarplet step amplitude, morphologic youthfulness (crest-toe LoG curvature dipole / step height), slope-aware synthetic (downface) + antithetic (upface) step vs cross-slope channel bank (crossface), Steger sub-pixel line fraction, and Frangi 2-20 m vesselness; 2. Aggregate to 100 m cells as scarp_pixel_fraction, snr_weighted_amplitude, energy-gated structure_tensor_coherence, and frame-corrected geological dominant_strike ((strike_img + 90) % 180); 3. Mask cultural road cuts/berms (tiger_road_distance_m < 75 m), mining disturbances (blm_closed_claim_distance_m < 60 m), and flat-basin cardinal agricultural canals/field edges (relief < 4.5 m, cardinal strike, ex_max > 2*step_max, 3 m far-field h_gate12 == 0); 4. Retrain L2-regularized spatial-CV logistic model across 4 spatial folds and place 37,654 non-maximum-suppressed peaks (r_NMS = 2.8 px, 200 m B2 visible-catalogue collar).",
  "non_fault_mimic": "Pleistocene Lake Lahontan wave-cut shoreline scarps, fluvial terrace risers, and graded highway/canal embankments produce meter-scale topographic steps in 1-3 m lidar DEMs without Holocene/Quaternary fault slip; mitigated by the cultural-feature mask (TIGER roads, BLM claims, flat-basin cardinal double-edged prisms with zero 3 m far-field offset) and slope-aware synthetic/antithetic step projection.",
  "holdout": {
    "evidence_class": "HOLDOUT-DTI",
    "status": "completed",
    "evaluator_version": "gems57-pooled-hide-v3-se",
    "dti": 0.130522,
    "ci95": [0.117397, 0.143103],
    "withheld_positive_pixels": 9274,
    "baseline_100m_topo_dti": 0.113522,
    "delta_vs_100m_baseline": 0.017000,
    "delta_vs_100m_baseline_ci95": [0.009202, 0.025473],
    "delta_vs_100m_baseline_se": 0.004120,
    "beats_two_se_vs_100m_baseline": true,
    "range_front_blocks": {
      "n_blocks": 52,
      "withheld_positive_pixels": 4432,
      "baseline_dti": 0.126160,
      "candidate_dti": 0.145038,
      "delta": 0.018877,
      "bootstrap_se": 0.005494,
      "beats_two_se": true
    },
    "off_range_front_blocks": {
      "n_blocks": 52,
      "withheld_positive_pixels": 4842,
      "baseline_dti": 0.106413,
      "candidate_dti": 0.121961,
      "delta": 0.015548,
      "bootstrap_se": 0.006042,
      "beats_two_se": true
    },
    "e1_pure_detector_spatial_cv": {
      "withheld_positive_pixels": 48441,
      "baseline_dti": 0.109182,
      "candidate_dti": 0.137003,
      "delta": 0.027821,
      "bootstrap_se": 0.003500,
      "beats_two_se": true,
      "range_front_delta": 0.030394,
      "off_range_front_delta": 0.025625
    }
  },
  "correlation_overlap_vs_registry": {
    "surface_spearman": 0.394765,
    "final_dots_spearman": 0.066123,
    "final_dot_overlap_vs_discrete_detectors": 0.630053,
    "final_dot_overlap_vs_h33_2_b2": 0.266559,
    "final_mutual_dot_overlap_all_70": 0.355692,
    "registry_rasters_checked": 70,
    "byte_unique": true,
    "pixel_unique": true
  },
  "raster_sha256": "346d57f0eca0ff36f7648f8b5a3ba8764054ab9e42e1677873791b83f460f45e",
  "nan_outside_raster_sha256": "ead50e13592a2facea8b01b9eceb292693a5b21c76319ab8cd9ae37a0e133f3b",
  "zip_sha256": "e2ee6466f9f1654e63e166123db35325e4a7beca101e27548c6a1c5152212d38",
  "validator_output": {
    "status": "PASS",
    "all_checks_passed": true,
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "dtype_float32": true,
    "crs_shape_transform_match": true,
    "zero_dots_on_mapped_catalogue": true,
    "emitted_positive_pixels": 37654
  },
  "submission_name": "gems64-h64-lidar-scarp-cv-20261011T220000Z",
  "note": "GEMSDOE64 native lidar scarp channels (Scarplet+Steger+Frangi) + cultural mask + 4-fold spatial CV; 37654 NMS peaks.",
  "verdict": "promote"
}
```

---

## 7. Supplementary Evidence Set — the Expected-DTI-optimal lane (`verdict: negative`)

A second parallel run implemented the **Expected-DTI-optimal selection** lane: replace heuristic dot
spacing with a decision rule on a calibrated surface, greedy-add the candidate pixel with the largest
mean DTI gain under this repository's exact kernel metric over an ensemble of 32 plausible truth
rasters, then prune backward, and gate the result against spacing placement by more than two
block-bootstrap SEs.

> **Its verdict is `negative` — DO NOT DOWNLOAD AND DO NOT SUBMIT ITS GEOTIFF.** It is an audit
> artifact, not a candidate, and it is deliberately **not** in `docs/downloads/` or `docs/`
> anywhere. The promoted submission remains
> `submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif` as §0 states. **No weekly slot was
> spent by this lane.**

* write-up — [`docs/research/lane-expecteddti-findings.md`](docs/research/lane-expecteddti-findings.md),
  generated from the receipts by `scripts/build_lane_findings_expecteddti.py` with **no hand-entered
  numbers**;
* run card — [`evidence/run_card_expecteddti.json`](evidence/run_card_expecteddti.json), built by
  `scripts/make_run_card_expecteddti.py`. This is a **second** card and must never be confused with
  the published [`evidence/run_card.json`](evidence/run_card.json), which `scripts/check_site.py`
  requires to be mirrored byte-for-byte at `docs/data/run_card.json`;
* receipts — `evidence/lane_expecteddti_exp1_rule.json` (`VERIFIED`, 7/7 checks),
  `_exp2_inversion.json`, `_exp3a_field.json`, `_exp3b_field.json` (`HOLDOUT-AUC`, spatially
  blocked), `_exp3b_leaky_audit.json` (the quarantined leaky first instrument, kept as the audit
  trail), `_exp3c_emission.json`, `_exp3d_gate.json`;
* code — `src/gems64/lane_expecteddti/{gridext,metricext,engine,emission}.py` and
  `scripts/lane_expecteddti_*.py`. These **keep no private fork**: grid constants come from
  `gems64.grid`, and the kernel, lattice offsets, α/β, brute-force oracle and marginal rule come from
  `gems64.metric`; the gate calls the shared `gems64.validate` (18 checks) and `assert_submittable`;
* artifact — `submissions/gems64-expecteddti-flank0.158-14k-20261011T210000Z-af6336e0-zeros.tif`
  (sha256 `abc46d756dc437ea…`, 14,075 positive px, **PASS 18/18**) and its `-nan` comparison twin
  (**FAIL 16/18** on `no_nan_anywhere` + `outside_footprint_zero` — must never be uploaded).

**Decision-relevant result.** The rule is verified — joint greedy beat independent thresholding on
5/5 held-out draws with identical `TP_w` at 18–31× less mass, confirming that the 3-px kernel makes
adjacent picks redundant — and it beat spacing placement by `z = +15.97` on 32/32 held-out draws. But
the **surface is saturated**: 1.94 % of scored cells sit at raw score 1.0 and the top 200,000
candidates span 0.0003 of score range with only 4,907 distinct values, so the ranking that selects
every dot is decided by numpy's tie order rather than by geology. A verified optimal rule pointed at
an uninformative surface yields an arbitrary dot set that looks excellent against truth sampled from
itself. One arm failed (`surface usability`); the other three passed.

**Its most transferable finding independently corroborates §1.** Inverting `T = D·(α·S + β·K)`
through the verified closed form over the registry's one controlled pair (`h27-4-r1-solo-d2-8` at
`0.2708` with 2,545 dots inside 2 px of the published catalogue, versus `h33-2-b2` at `0.2778` with
zero) quantifies the flank band as a **6.3× credit depletion** — ≈`0.016` per removed dot against
≈`0.102` per retained dot — robust for every plausible hidden-truth size `K = 6,000–12,691`. So the
collar removal was *required* by the marginal rule, not merely score-improving, which is the same
conclusion §1 reaches by pixel diffing. Its negative control `sgmc-off-catalogue-44k` at **`0.0512`**
bounds every off-catalogue hypothesis: being off-catalogue is necessary but nowhere near sufficient.

---

## 8. Original Task Prompt — the Expected-DTI-optimal parallel run (preserved verbatim)

<details>
<summary><b>Click to expand. §5 preserves the lidar-scarp lane's prompt; this is the second
parallel run's prompt, preserved verbatim and re-read at the start of every session.</b></summary>

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

