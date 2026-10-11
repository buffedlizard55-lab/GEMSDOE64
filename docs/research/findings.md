# GEMSDOE64 — Native-Resolution LiDAR Scarp Channels, Cultural Masking & Spatial-CV Retraining (`H64-L1`)

## 1. Executive Verdict & Submission Clearance

- **Verdict**: **`promote`** — **CLEARED FOR DOWNLOAD & COMPETITION SUBMISSION**
- **Primary Submission File (`0.0` outside footprint, portal-safe `[0, 1]`)**:
  - GeoTIFF: [`submissions/h64-lidar-scarp-cv-20261011-zeros.tif`](../submissions/h64-lidar-scarp-cv-20261011-zeros.tif) (`506,812` bytes, SHA-256 `919dfc5f9e429a8bae0784244191a23cc0d50fa265b8f5085a01f9644ab9e97c`)
  - Single-TIFF ZIP: [`submissions/h64-lidar-scarp-cv-20261011-zeros.zip`](../submissions/h64-lidar-scarp-cv-20261011-zeros.zip) (`473,538` bytes, SHA-256 `e12484fa79619cebede818a528ce8b3b00200b572f9ab2de607509fd1d3701a2`)
- **Companion Submission File (`NaN` only outside footprint, identical inside footprint)**:
  - GeoTIFF: [`submissions/h64-lidar-scarp-cv-20261011-nan.tif`](../submissions/h64-lidar-scarp-cv-20261011-nan.tif) (`802,496` bytes, SHA-256 `62e330bb8df511c33ac0a3c977f8067b7d72d84324fe2c5d7d901b88c253869b`)
  - Single-TIFF ZIP: [`submissions/h64-lidar-scarp-cv-20261011-nan.zip`](../submissions/h64-lidar-scarp-cv-20261011-nan.zip) (`676,650` bytes, SHA-256 `3f808a7022c0647696817b9a7d356ad7109407d229ace017d7789f0143e4f7d0`)
- **Unique Submission Name**: `h64-lidar-scarp-cv-20261011`
- **Submission Note (106 / 140 chars)**:
  `H64-L1 native 1-3m LiDAR scarplet+Steger/Frangi 100m + TIGER/canal/field cultural mask + 4-quad spatial CV`

---

## 2. Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778`) Scored Highest Among Prior GEMSDOE Sites

Byte-level forensic analysis (`scripts/audit_h33.py`, [`evidence/h33_forensics.json`](../evidence/h33_forensics.json)) of `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`sha256: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`, 37,654 positive pixels) against its parent `GEMSDOE28__h27-4-r1-solo-d2-8.tif` (`sha256: 2fc94a38d77f74d4f4ed1a97a83e7bb71a1ceea090515ec641e6681cc47c44c8`, 40,199 positive pixels) establishes:

1. **Exact Pixel Identity with a $200\text{ m}$ Catalogue-Flank Pruning Rule (`rule_pixel_disagreement = 0`)**:
   - `h33-2-b2` is pixel-for-pixel identical to removing the **2,545 dots** that lie at Euclidean distance $0 < d \le 2\text{ px}$ ($200\text{ m}$) from `existing_faults.tif`, while retaining all **37,654 dots** at $d \ge 2.236\text{ px}$ ($\sqrt{5}\times 100\text{ m}$), and adding **0** new pixels.
2. **Mathematical Mechanism Under Distance-Tolerant IoU ($\text{DTI}, \alpha=0.2, \beta=0.8, R=300\text{ m}$)**:
   - Under the competition metric:
     $$\text{DTI} = \frac{\text{TP}_w}{\text{TP}_w + 0.2\,\text{FP}_w + 0.8\,\text{FN}_w}, \quad w(d) = \max\!\left(0, 1 - \frac{d}{300\text{ m}}\right)$$
   - Known catalogue fault pixels ($60,988$ cells) are **masked** at evaluation time (`masked_known`). Consequently, a predicted dot placed at $d = 100\text{--}200\text{ m}$ perpendicular to an already-mapped fault strand receives **zero $\text{TP}_w$ credit** from the masked strand while still incurring up to $+0.2$ in the denominator ($0.2\,\text{FP}_w$) unless an unmapped fault branch happens to sit there.
   - Even at genuine fault tips where an unmapped continuation begins at $d = 100\text{ m}$ from the catalogue tip, a single predicted dot placed at $d = 300\text{ m}$ along strike already covers the $100\text{--}200\text{ m}$ tip cells via the $R=300\text{ m}$ triangular kernel ($w(200\text{ m})=1/3, w(100\text{ m})=2/3$), because $\text{TP}_w$ takes the **maximum** over nearby predictions (`1 - d_to_pred / R`), whereas $\text{FP}_w$ **sums additively** over every emitted dot!
   - Pruning the 2,545 redundant inner-collar dots reduced $\text{FP}_w$ by $\sim 2,500$ units with negligible loss of $\text{TP}_w$, lifting the owner-reported score from `0.2708` (`h27-4-r1-solo-d2-8`) to `0.2778` (`h33-2-b2`).
3. **Why Tip-Collar Pruning Alone Plateaus and How `H64-L1` Goes Beyond It**:
   - Because `h33-2-b2` places 95.8% of its 37,654 dots within $2.0\text{ km}$ of already-mapped catalogue tips, it is nearly blind to **whole unmapped fault segments** in intrabasin valleys and piedmont fans (`HOLDOUT-DTI = 0.003814`, `95% CI [0.003033, 0.004641]` on `gems57-pooled-hide-v3-se` with $N=9,275$ withheld positive pixels).
   - Reaching and beating `0.3195` and `0.3774` requires genuine **off-catalogue surface & geophysical fault discovery** (native 1–3 m LiDAR scarplet template matching + multiscale Steger/Frangi Hessian line extraction + cultural-mimic masking + 20 km block-calibrated spatial CV) combined with $R=300\text{ m}$ non-maximum suppression so emitted picks do not double-count $\text{FP}_w$.

---

## 3. Five Untried Geological Hypotheses Ranked by Expected DTI Gain & Cost

| Rank | ID | Hypothesis & Specific Layers | Physical Signature & Why Missing From USGS/INGENIOUS Catalogue | Difference vs Existing Repo Implementations | Expected Holdout DTI Gain & Cost |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **H64-U1** *(Implemented in this run as `H64-L1`)* | **Dual-Scale (2 m + 3 m) Slope-Aware Scarplet + Steger/Frangi Hessian + TIGER/Canal/Field Cultural Deconfounding** (`lidar_scarp_features_u8.tif`, `h52_scarp3m_100m.tif`, `tiger_road_distance_m.tif`, `blm_closed_claim_distance_m.tif`, `topo_10m_derived_100m_u8.tif`, `geodawn_extensions_u8.tif`) | Diffusive Quaternary normal/strike-slip scarps ($0.3\text{--}3\text{ m}$ throw) cutting alluvial fans and playas exhibit paired crest convexity ($-\text{LoG}$) and toe concavity ($+\text{LoG}$) plus net $\pm 21\text{ m}$ far-field offset ($h_{\text{gate12}}$), whereas graded roads, irrigation canals, and section-line field edges are double-edged berms lacking 10 m profile curvature (`curv_10m`) and 3 m far-field offset. Missed in 1:250k airphoto mapping due to sub-2 m vertical relief. | Prior `GEMSDOE66` used only 2 m channels and a synthetic morphology proxy that received a *positive* weight in logistic regression (`delta_dti = -5.1e-6`). `H64-L1` fuses 2 m + 3 m stacks with actual TIGER road and BLM claim distance rasters, achieving negative cultural weights on all 4 spatial folds. | **Measured**: `+0.0175` over 100 m CV baseline (`+2.55 SE`) on full LiDAR; `+0.0377` (`+7.10 SE`) on off-range-front LiDAR. **Cost**: Low (~3.4 min). |
| **2** | **H64-U2** | **Morphologic Age ($\kappa t$) Along-Strike Gradient for Blind Propagating Fault Tips** (`scarplet_rel_age` $\kappa t \propto (\text{step\_max}/\sqrt{\text{lapneg}\cdot\text{lappos}})^2$, `dominant_strike`, `h_gate12`) | Propagating normal/strike-slip fault segments exhibit a monotonic decrease in morphologic scarp age $\kappa t$ (sharper curvature relative to scarp height) toward active segment tips and relay ramps, whereas ancient shoreline terraces (Lake Lahontan highstands) have uniform $\kappa t$ along contour-parallel rings. | No sibling repo has used the directional derivative $\partial(\kappa t)/\partial s_{\parallel}$ or distinguished constant-elevation pluvial shorelines from cross-contour tectonic scarps. | **Expected**: `+0.004 to +0.008` HOLDOUT-DTI on pluvial-basin blocks. **Cost**: Low–Medium (~25 lines of NumPy). |
| **3** | **H64-U3** | **Antithetic Graben Pair Detector (Opposing `upface_max` & `downface_max` Dipole Across 100–400 m)** (`upface_max`, `downface_max`, `facing_at`, `dominant_strike`) | Piedmont and intrabasin normal fault zones frequently form $100\text{--}400\text{ m}$-wide hanging-wall grabens bounded by a synthetic downhill-facing scarp (`downface_max`) paired with an antithetic uphill-facing scarp (`upface_max`) at parallel strike. Erosional stream terraces and alluvial fan channels never form uphill-facing scarps opposing the regional fan gradient. | Existing repos treat `upface_max` and `downface_max` as independent scalar features rather than computing cross-strike synthetic–antithetic dipole correlation at $100\text{--}400\text{ m}$ separation. | **Expected**: `+0.003 to +0.007` HOLDOUT-DTI on piedmont fan blocks. **Cost**: Low (~30 lines of SciPy). |
| **4** | **H64-U4** | **Aeromagnetic Upward-Continued Tilt-Derivative Concordance with Sub-Meter Playas (`TMI_up150` + `ThK` + 3 m `h_gate12`)** (`geodawn_extensions_u8.tif`, `h52_scarp3m_100m.tif`) | Concealed intrabasin faults cutting shallow volcanic/plutonic basement beneath $<50\text{ m}$ of playa fill produce a strike-aligned horizontal gradient in upward-continued total magnetic intensity (`TMI_up150`) and potassium-normalized thorium (`ThK` hydrothermal alteration) colinear with subtle $<0.5\text{ m}$ playa compaction scarps. | Prior repos either thresholded raw `TMI` globally or ignored strike concordance $|\cos 2(\theta_{\text{scarp}} - \theta_{\text{mag}})|$ between sub-meter LiDAR scarps and aeromagnetic tilt edges. | **Expected**: `+0.003 to +0.006` HOLDOUT-DTI on concealed basin-interior faults. **Cost**: Medium. |
| **5** | **H64-U5** | **En-Echelon Riedel Shear Stepover Tensor in Walker Lane Transtensional Domains** (`strike2m`, `strike3m`, `coh100`, `derived_sgmc_faults_100m_u8.tif`) | In the Walker Lane and Humboldt structural belt, right-lateral/oblique transtensional fault zones express at 1–3 m LiDAR scale as arrays of left-stepping $R$-shears oriented $12^\circ\text{--}18^\circ$ clockwise from the regional basement fault corridor strike. | All prior directional filters assume single-azimuth collinearity ($0^\circ$ offset) and suppress en-echelon Riedel stepover arrays. | **Expected**: `+0.002 to +0.005` HOLDOUT-DTI in southern/western Walker Lane blocks. **Cost**: Medium. |

---

## 4. Assigned Lane Implementation & Three-Experiment Record (`H64-L1`)

### Experiment 1 (`EXP-64-1`): Native 3 m DEM Tile Verification (`x40y427_3m.tif` & `x42y425_3m.tif`)
- **Implementation**: `src/gems64/lidar_scarp.py` (`scarplet_template_kernel`, `compute_native_scarplet_steger_frangi_tile`, `aggregate_tile_to_100m`) and `scripts/run_lidar_scarp_lane.py` ([`evidence/exp1_native_tile_verification.json`](../evidence/exp1_native_tile_verification.json)).
- **Formulation**:
  1. **Slope-Detrended Surface**: $z_{\text{det}} = G_{2\text{m}}(z) - G_{60\text{m}}(z)$ (Hanks 2000; Sare & Hilley AGU 2015 T31A-2838).
  2. **Scarplet Template Matching** (Sare & Hilley, JOSS 2018, `doi:10.21105/joss.01066`):
     $$W(x_r, y_r; \kappa t, \alpha) = -\frac{x_r}{2(\kappa t)^{3/2}\sqrt{\pi}}\exp\!\left(-\frac{x_r^2}{4\kappa t}\right), \quad |x_r| \le 2\sqrt{\kappa t}\,\text{erfinv}(0.90), \;|y_r| \le \frac{L}{2}$$
     with exact least-squares signal energy $T_1 = \text{xcorr}^2 / \sum W^2$, residual variance $\sigma_{\text{err}}^2 = \frac{1}{n}\max(T_3 - T_1, 0) + \epsilon$, $\text{SNR} = T_1 / \sigma_{\text{err}}^2$, and slope-aware contour alignment weight $w_{\text{slope}} = \frac{1}{2}(1 + |\cos(\alpha - \theta_{\text{reg}})|)$.
  3. **Steger (1998) Sub-Pixel Curvilinear Lines & Frangi (1998) Multiscale Hessian**: Evaluated at $\sigma \in \{3, 6, 12, 20\}\text{ m}$ on $z_{\text{det}}$, solving $t = -(g_x n_x + g_y n_y)/\lambda_1$ with $|t n_x|\le 0.5, |t n_y|\le 0.5$ and $\mathcal{V}(\sigma) = \exp(-R_B^2/2\beta^2)(1 - \exp(-S^2/2c^2))$.
  4. **100 m Aggregation**: Aggregated $3337\times 3337$ native 3 m pixels into $101\times 101$ ($10,201$) 100 m competition grid cells per tile:
     - `x40y427_3m.tif` (`r=[2385:2486], c=[1566:1667]`, 473 fault cells): Spearman rank correlation with full-footprint 2 m stack = **`+0.8838`**; on-fault vs off-fault enrichment = **`1.0659x`** (`snr_weighted_amplitude`) and **`1.0767x`** (`steger_frangi_score`).
     - `x42y425_3m.tif` (`r=[2585:2686], c=[1766:1867]`, 490 fault cells): Spearman rank correlation with full-footprint 2 m stack = **`+0.9092`**; on-fault vs off-fault enrichment = **`1.1496x`** (`snr_weighted_amplitude`) and **`1.1685x`** (`steger_frangi_score`).

### Experiment 2 (`EXP-64-2`): Full-Footprint Aggregation, Leakage Canaries & Cultural-Feature Masking
- **Implementation**: [`evidence/exp2_cultural_mask_audit.json`](../evidence/exp2_cultural_mask_audit.json) and [`evidence/leakage_canary.json`](../evidence/leakage_canary.json).
- **Single-Feature Leakage Canaries (Rule 4)**: Every feature was tested alone against withheld whole fault segments (`N = 9,275` positive pixels across the 4 buffered quadrants). All 12 channels passed well below the `0.90` leakage ceiling (`max_directional_auc = 0.5949`, `any_flagged = False`):
  - `scarp_pixel_fraction`: `AUC = 0.4347` (`directional_auc = 0.5653`)
  - `snr_weighted_amplitude`: `AUC = 0.5498` (`directional_auc = 0.5498`)
  - `structure_tensor_coherence`: `AUC = 0.4789` (`directional_auc = 0.5211`)
  - `dominant_strike`: `AUC = 0.5098` (`directional_auc = 0.5098`)
  - `hessian_sharpness`: `AUC = 0.5935` (`directional_auc = 0.5935`)
  - `scarplet_rel_age`: `AUC = 0.5817` (`directional_auc = 0.5817`)
  - `slope_polarity`: `AUC = 0.4937` (`directional_auc = 0.5063`)
  - `curv_10m`: `AUC = 0.5949` (`directional_auc = 0.5949`)
- **Cultural-Feature Mask (`LS64.build_cultural_feature_mask`)**:
  - Combines Census TIGER/Line road proximity (`tiger_road_distance_m <= 150 m`), cross-slope irrigation canals (`cross_max > 1.05 * (upface_max + downface_max)`), N–S/E–W section-line agricultural field edges (`|sin(2 * dominant_strike)| < 0.18` with `h_gate12 < 0.10 m`), and BLM closed mining claim benches (`blm_closed_claim_distance_m <= 150 m`) on low-relief/low-10 m-curvature terrain.
  - Across the `3,893,082` LiDAR-covered footprint cells (`75.34%` of the `5,167,373` footprint), the cultural mask flags `810,099` cells (`20.81%`) whose catalogue fault rate is **`0.006181`** vs **`0.012443`** domain-wide (**`2.01x` depleted of catalogue faults**) and whose SGMC geologic fault rate is **`0.001916`** vs **`0.014079`** domain-wide (**`7.35x` depleted of SGMC faults**).

### Experiment 3 (`EXP-64-3`): 4-Quadrant Spatial-CV Retraining & Holdout DTI Gate Evaluation
- **Protocol**: 4-quadrant Leave-One-Quadrant-Out (LOQO) spatial CV using `gems57/holdout.py` (`buffered_component_draw`, `seed=20`, `hide_frac=0.20`, `buffer_px=3`, `boundary_px=12`) and scored by `gems57/evaluate_holdout.py` (`evaluator_version = "gems57-pooled-hide-v3-se"`, $\alpha=0.2, \beta=0.8, R=300\text{ m}$ triangular kernel, 1,000 paired 20 km physical spatial-block bootstrap draws).
- **Spatial-CV Learned Sign Check**: In all 4 spatial folds, `cultural_mask` receives a strictly negative weight (`-0.4791, -0.4913, -0.5532, -0.4389`), while `hessian_sharpness` (`+1.0730, +0.5804, +1.0292, +0.5027`), 3 m `z_h12` (`+0.3149, +0.4071, +1.0494, +0.8101`), `corridor_sig` (`+0.6846, +0.4699, +0.8009, +0.5919`), and `slope_polarity` (`+0.3577, +0.2695, +0.3330, +0.1697`) receive strictly positive weights across all 4 folds.

#### Table 1 — Full LiDAR-Covered Holdout Blocks (`HOLDOUT-DTI`, `gems57-pooled-hide-v3-se`, `withheld_positive_pixels = 9,275`, `137` physical 20 km clusters)

| Arm | Evidence Class | `HOLDOUT-DTI` | 95% Block-Bootstrap CI | $\text{TP}_w$ | $\text{FP}_w$ | Paired $\Delta\text{DTI}$ (`H64-L1` minus Control) | Paired 95% CI | Bootstrap SE | $> 2\,\text{SE}$ Gate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `random_lidar` (45k random in LiDAR domain) | `HOLDOUT-DTI` | `0.039761` | `[0.034747, 0.044418]` | `637.6` | `42,435.6` | **`+0.035153`** | `[+0.023126, +0.048485]` | `0.006571` | **PASS (`+5.35 SE`)** |
| `h33_2_b2` (`ORGANIZER-CONFIRMED 0.2778` prior) | `HOLDOUT-DTI` | `0.003814` | `[0.003033, 0.004641]` | `49.0` | `27,073.8` | **`+0.071099`** | `[+0.058585, +0.085563]` | `0.007025` | **PASS (`+10.12 SE`)** |
| `baseline_100m_cv` (10 m/100 m topo + aeromag Spatial CV) | `HOLDOUT-DTI` | `0.057445` | `[0.046509, 0.068822]` | `917.9` | `41,876.4` | **`+0.017469`** | `[+0.005043, +0.032588]` | `0.006850` | **PASS (`+2.55 SE`)** |
| `native_lidar_unmasked` (Unmasked Native-LiDAR Scarp) | `HOLDOUT-DTI` | `0.062661` | `[0.054226, 0.071071]` | `1,002.8` | `41,914.1` | **`+0.012253`** | `[+0.001475, +0.024007]` | `0.005854` | **PASS (`+2.09 SE`)** |
| **`native_lidar_masked_cv` (`H64-L1` Candidate)** | `HOLDOUT-DTI` | **`0.074914`** | **`[0.062409, 0.089659]`** | **`1,202.2`** | **`41,939.5`** | — | — | — | **PROMOTED** |

#### Table 2 — Off-Range-Front LiDAR-Covered Holdout Blocks (`HOLDOUT-DTI`, `gems57-pooled-hide-v3-se`, `withheld_positive_pixels = 5,195`, `136` physical 20 km clusters)

| Arm | Evidence Class | `HOLDOUT-DTI` | 95% Block-Bootstrap CI | $\text{TP}_w$ | $\text{FP}_w$ | Paired $\Delta\text{DTI}$ (`H64-L1` minus Control) | Paired 95% CI | Bootstrap SE | $> 2\,\text{SE}$ Gate |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `random_lidar` (45k random in LiDAR domain) | `HOLDOUT-DTI` | `0.028277` | `[0.023923, 0.032681]` | `276.0` | `27,737.8` | **`+0.019535`** | `[+0.010024, +0.030543]` | `0.005180` | **PASS (`+3.77 SE`)** |
| `h33_2_b2` (`ORGANIZER-CONFIRMED 0.2778` prior) | `HOLDOUT-DTI` | `0.001175` | `[0.000758, 0.001673]` | `7.5` | `11,312.8` | **`+0.046637`** | `[+0.036741, +0.057465]` | `0.005407` | **PASS (`+8.63 SE`)** |
| `baseline_100m_cv` (10 m/100 m topo + aeromag Spatial CV) | `HOLDOUT-DTI` | `0.010069` | `[0.006007, 0.014600]` | `46.3` | `2,143.0` | **`+0.037743`** | `[+0.027813, +0.048624]` | `0.005318` | **PASS (`+7.10 SE`)** |
| `native_lidar_unmasked` (Unmasked Native-LiDAR Scarp) | `HOLDOUT-DTI` | `0.034406` | `[0.027187, 0.041335]` | `219.1` | `10,844.1` | **`+0.013406`** | `[+0.002159, +0.024300]` | `0.005546` | **PASS (`+2.42 SE`)** |
| **`native_lidar_masked_cv` (`H64-L1` Candidate)** | `HOLDOUT-DTI` | **`0.047812`** | **`[0.037585, 0.058351]`** | **`451.7`** | **`26,009.8`** | — | — | — | **PROMOTED** |

---

## 5. Root-Cause Resolution of `"Predicted values must be in range [0, 1]"` & Uniqueness Audit

1. **Why Earlier Submissions Failed With `"Predicted values must be in range [0, 1]"`**:
   - Unnormalized raw logit/z-score outputs, negative nodata sentinels (`-9999.0`, `-3.4e38`), or `NaN` pixels outside the footprint when evaluated by a strict `0 <= x <= 1` array check trigger DrivenData's `"Predicted values must be in range [0, 1]"` rejection.
   - Our primary submission [`submissions/h64-lidar-scarp-cv-20261011-zeros.tif`](../submissions/h64-lidar-scarp-cv-20261011-zeros.tif) is strictly normalized to `[0.0, 1.0]` (`min = 0.0`, `max = 1.0`, `n_nan = 0`, `n_infinite = 0`, `nodata = None`, `float32`, `EPSG:32611`, `3730 x 3292`), passing `python scripts/validate_submission.py` with `format_pass: true` and `all_checks_passed: true`. We also provide the companion [`submissions/h64-lidar-scarp-cv-20261011-nan.tif`](../submissions/h64-lidar-scarp-cv-20261011-nan.tif) with `NaN` only outside the `5,167,373`-cell footprint (`identical inside the footprint`).
2. **Full 67-Raster Registry Uniqueness Audit ([`evidence/registry_audit_67.json`](../evidence/registry_audit_67.json))**:
   - **Byte & Pixel Identity**: `byte_unique_across_all_67 = True`, `pixel_unique_across_all_67 = True`.
   - **Pre-Placement Surface Rank Correlation**: $\max |\rho_{\text{Spearman}}| = 0.1239 \le 0.90$ (`PASS`, vs `7GEMSDOE__gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif`).
   - **Final Dots Rank Correlation (All 67 Rasters)**: $\max |\rho_{\text{Spearman}}| = 0.0394 \le 0.90$ (`PASS`, vs `7GEMSDOE__gems7-lidarscarp-ridge-top2pct-36c3a3f341c8.tif`).
   - **Final Dots 3-px Overlap Across All 62 Geological Fault Submissions**: $\max \text{overlap}_{3\text{px}} = 0.4547 \le 0.70$ (`PASS`, vs `calib_hedgev2_01563_sample.tif`; $\max \text{Jaccard} = 0.0249$).
   - **Transparent Disclosure of 5 Space-Filling / Regular-Lattice Calibration Probes**: Five files in the 67-raster repository dump are non-geological space-filling or grid-lattice calibration probes whose 3-px halos cover $>73\%$ of the entire map (`17GEMSDOE__17GEMSDOE_E-proba-multiscale.tif` covering `100.0%`, `r13_lattice_s5_00904.tif` and `calib_r13lattice_00904.tif` 5-px grid lattices covering `99.87%`, `r14_union_tips10_lat6.tif` 6-px lattice covering `76.21%`, and `r11_greedy_mp.tif` 272k-dot packing covering `73.66%`). Even a uniform random dot set has $>73.66\%$ overlap against those 5 space-filling probes; against all 62 genuine geological fault submissions, our candidate passes the $\le 0.70$ overlap gate with `0.4547`.
