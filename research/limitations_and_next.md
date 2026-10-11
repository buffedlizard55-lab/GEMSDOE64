# Limitations, blockers, and next steps

**Status: NOT CLEARED.** This is the evidence boundary for the current checkout, reviewed 2026-10-11. A missing value below is not zero and is not an implied pass.

## Workspace and execution limits

- The checkout initially contained only `README.md` (one tracked file). It did not contain competition or registry rasters, a cached feature stack, `evaluate_holdout.py`, `submission_writer.py`, a validator, training code, or `scripts/download_competition_data.sh` / `scripts/prepare_data.py`.
- A shallow search of `/home/user` found only this checkout; no shared cache or data directory was visible.
- The official DrivenData data-page fetch redirected to login. No account/session credentials were available, and no access workaround was attempted. Authorized input files are not present.
- Python 3.11.2 is available. `nvidia-smi`, `pytest`, `uv`, and `conda` were unavailable. The synthetic script needs only the standard library; geospatial/ML dependencies (`numpy`, `scipy`, `rasterio`, `scikit-learn`, `geopandas`) were not available in the checked environment. GPU availability is unknown.
- The shared reference repository was identified, but its code is not in this checkout. Do not silently replace it with a private evaluator or writer.

## What has been tested

`python scripts/verify_expected_dti_rule.py` ran successfully (exit code 0). Its deterministic output is saved in [`expected_dti_probe.json`](expected_dti_probe.json). This is a **synthetic formula/decision-rule check only**. It verifies a published worked-example arithmetic check, an isolated unit-case threshold intuition, and a sparse spatial-kernel redundancy counterexample. It did not use real competition data and is not `HOLDOUT-DTI`, `ORGANIZER-CONFIRMED`, an evaluator regression test, or a submission validation.

No competition/modeling experiment was run. No holdout score, 95% CI, withheld-positive count, feature-alone AUC, registry similarity, candidate GeoTIFF, artifact SHA-256, validator result, submission name/comment, or receipt exists.

## Geographic/data limitations

- The official USGS GeoDAWN record describes magnetic/radiometric grid GeoTIFF archives and survey outlines, but no files were downloaded or hashed; exact GEMS-polygon overlap, grid metadata and file-level usage terms remain unchecked.
- The USGS 3DEP 1-meter index was queried against the GeoDAWN record's coarse WGS84 bounding rectangle. It returned 22 project polygons, not 22 tiles. This does not establish exact competition-polygon coverage, quality or resolution; no lidar tiles were downloaded.
- The Nevada relocated-catalog Zenodo record is open under CC-BY-4.0 and lists `nvreloc_catalog_newmag.txt` plus `station_terms.txt` (about 13.8 MB combined). The files were not downloaded or schema-audited; event density, exact competition overlap and quality remain unknown.
- The USGS Great Basin heat-flow record is marked CC0 and describes gridded maps plus well data/residuals; files and exact AOI coverage were not checked. The USGS Gabbs Valley 3D map is also CC0 but geographically local; it does not cover the full GEMS footprint.
- The official Copernicus portal describes free data access, but no Sentinel-1 AOI/date acquisition query or account/processing test was performed. Do not call this candidate test-ready until a repeatable scene stack is found.
- GDR 1391 returned “No submission found”; OSTI describes INGENIOUS themes and redistribution with attribution subject to its posted terms, but usable files, file-level terms and spatial completeness were not verified.
- No new external data were downloaded, integrated or scored. These source-record/index checks do not clear any feature for a competition experiment.

## Claims intentionally not made

- No candidate is represented as downloaded, integrated, tested, unique, holdout-improved, validator-passing or available to download.
- No current leaderboard score/rank is reported. No leaderboard feed, scraper, cache or mirrored table was built, because the Terms of Use restrict monitoring/copying absent prior written consent.
- User/owner-cited sibling-project values are unverified absent receipt-to-artifact attribution and are not used as scores in this report. See [`score_review.md`](score_review.md).
- No score is projected from feature plausibility, literature, or a toy raster.

## Next actions when missing shared inputs are available

1. Mount/restore the exact shared template and data inputs, including cached features, `evaluate_holdout.py`, `submission_writer.py`, validator, and complete prior-raster registry. Keep paths and versions in the run record.
2. Obtain competition data from an authorized entrant account. Inventory each file's source/license/terms, SHA-256, CRS, grid, nodata, bounds, resolution and AOI coverage.
3. Re-run the synthetic probe. Then preregister one hypothesis, non-fault mimic, and falsification test; do the feature-alone leakage canaries before looking at promotion results.
4. Use whole fault segments with a buffer, visible-only catalogue features, and pixel-exact visible-fault masking. Report pooled `HOLDOUT-DTI`, evaluator version, withheld-positive count and spatial block-bootstrap 95% CI.
5. Compare incumbent and proposal on the same surfaces; require gain over two block-bootstrap standard errors. Compare every registry raster before placement and final dots; stop if rank correlation >0.90 or 3-pixel overlap >70%.
6. Use the shared writer and validator on a novel final raster, check exact bytes/metadata/pixel agreement and hash, and complete a machine-readable run card. The competition run budget is at most three experiments or two hours; no slot use or automatic upload.
7. Change the site from red to green only when all gates pass and the evidence is recorded. Otherwise retain the negative result and do not offer a TIFF download.
