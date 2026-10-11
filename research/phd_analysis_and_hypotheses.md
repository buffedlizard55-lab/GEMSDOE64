# GEMSDOE64 PhD Analysis, Candidate Geological Hypotheses, and Native-Resolution Lidar Scarp Channels Validation

See `docs/research/findings.md` and `evidence/run_card.json` for the complete verified record.

## Summary of Key Verified Results

1. **Forensic Identity of `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778` `ORGANIZER-CONFIRMED`, `evidence/h33_forensics.json`)**:
   - Exact deterministic pruning of `GEMSDOE28__h27-4-r1-solo-d2-8.tif` (`40,199` dots, `7,111,787` exterior `NaN`s) by removing all `2,545` dots within $d_{\text{Euc}}(\cdot, \mathcal{C}_{\text{known}}) \le 200\text{ m}$ (`2 px`) of `existing_faults.tif` (`37,654` remaining dots, `0` added, `0` removed outside `200 m`) and replacing exterior `NaN`s with `0.0` (`nodata=None`).
2. **Native 3 m DEM Scarp Channels Verification (`src/gems64/lidar_scarp.py`)**:
   - Implements Sare & Hilley (*JOSS* 2018, `doi:10.21105/joss.01066`) Scarplet template matching + AGU 2015 T31A-2838 slope-aware alluvial-fan detrending + Steger (*IEEE TPAMI* 1998) sub-pixel ridge centerlines + Frangi (*MICCAI* 1998) 2–20 m multiscale Hessian vesselness.
   - Real native 3 m DEM tile `data/pilot/dem3m/x42y425_3m.tif` (`window = [2585, 1766, 101, 101]`, `385` catalogue cells): **`ROC-AUC = 0.6617`**.
3. **Spatial-CV `HOLDOUT-DTI` (`gems57-pooled-hide-v3-se`, `evidence/experiments.json`)**:
   - **Experiment `E1` (4-fold label-blind spatial CV, 8 km buffer, `48,441` withheld positive pixels)**:
     - Overall: `0.109182 -> 0.137003` (`+0.027821`, `+25.48%`, `95% CI: [+0.021244, +0.034918]`, `SE = 0.003500`, `beats_two_se = True`)
     - Range-front blocks (`64` blocks): `+0.030394` (`beats_two_se = True`)
     - Off-range-front blocks (`64` blocks): `+0.025625` (`+28.66%`, `beats_two_se = True`)
   - **Experiment `E2` (4-fold buffered whole-component spatial CV, 300 m visible-catalogue collar, `9,274` withheld positive pixels)**:
     - Overall: `0.113522 -> 0.130522` (`+0.017000`, `+14.98%`, `95% CI: [+0.009202, +0.025473]`, `SE = 0.004120`, `beats_two_se = True`)
     - Range-front blocks (`52` blocks): `0.126160 -> 0.145038` (`+0.018877`, `beats_two_se = True`)
     - Off-range-front blocks (`52` blocks): `0.106413 -> 0.121961` (`+0.015548`, `+14.61%`, `beats_two_se = True`)
4. **Promoted Unique Submission (`evidence/run_card.json`)**:
   - `submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif` (`sha256: 346d57f0eca0ff36f7648f8b5a3ba8764054ab9e42e1677873791b83f460f45e`, `37,654` dots, `0` NaNs, all values in `[0.0, 1.0]`).
   - `submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z-nan-outside.tif` (`sha256: ead50e13592a2facea8b01b9eceb292693a5b21c76319ab8cd9ae37a0e133f3b`, `NaN` only outside footprint).
