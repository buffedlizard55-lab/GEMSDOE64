# Limitations, blockers, and next steps

**Current decision: NEGATIVE — no download or slot.** Reviewed 2026-10-11. These are current limits of the checkout and active run; a missing value is not zero or an implied pass. The canonical machine-readable status is [`../evidence/run_card.json`](../evidence/run_card.json).

## Decisive blocker

A pinned public sibling-project prior has a three-pixel neighborhood covering every allowed off-catalogue cell. Under the protocol's rule that every positive finite prediction pixel is a dot, every nonempty candidate would have 100% of its dots within three pixels of that prior, above the 70% forward-overlap limit. The run stopped before model fitting or candidate placement. See [`../evidence/registry_blocker.json`](../evidence/registry_blocker.json).

This is a single-witness universal stop under the current rule—not a candidate correlation, proof of scientific copying, or complete byte/pixel audit of all priors. The witness is a public owner artifact, not an organizer-issued registry receipt. No candidate surface or final dot set exists. Changing how dense probability rasters count requires an explicit shared-protocol decision; do not create a private exemption.

## Workspace and execution limits

- The shared `src/gems57/` metric, holdout, writer, validator and registry utilities are present, imported from a pinned 60GEMSDOE commit. Local corrections and source hashes are recorded in [`../evidence/template_import.json`](../evidence/template_import.json) and [`../docs/research/template-corrections.md`](../docs/research/template-corrections.md); no private evaluator or TIFF-writer fork is used.
- Lane helpers are in `src/gems64/`. The expected-DTI reference selector is bounded and is not a trained model or production-scale optimizer.
- The current `data/` directory contains only its README. Official competition rasters, shared feature-cache bytes, buffered OOF predictions, model checkpoints/provenance and complete local registry inputs are absent. Upstream evidence records describe third-party GitHub bridge artifacts; they do not authenticate organizer-origin data and are not present as local TIFFs now.
- The feature-cache receipt points to an ephemeral path. Its declared footprint differs from the sample receipt's recorded finite footprint; since feature bytes are unavailable, this is only a receipt-level discrepancy, not a measured raster-mask comparison or diagnosis of the user's rejected upload. Do not use the narrower declared footprint as a nodata mask.
- The DrivenData data page previously redirected to login. No account credentials were requested or supplied and no authentication bypass was attempted.

## Tests and evidence classes

The repository includes synthetic exact-kernel checks, metric-vs-brute-force tests, calibration-isolation and holdout/gate tests, writer/validator tests using fixtures, and static-site checks. Synthetic results are mathematical checks only; fixture TIFFs are not a competition prediction. This session did not run a real geological feature canary, buffered holdout, or candidate placement.

No competition `HOLDOUT-DTI` result, 95% CI, withheld-positive count, candidate SHA-256, production validator result, unique submission name, upload, slot use or `ORGANIZER-CONFIRMED` score exists for the active run. The complete registry byte/pixel audit is not complete. The user/owner score-to-file claims remain unverified; numeric leaderboard claims are deliberately not reproduced.

## External source reconnaissance — metadata only

No external geological source file was downloaded, locally hashed, integrated or evaluated. See the detailed active register at [`../docs/sources.html`](../docs/sources.html), machine-readable metadata at [`../docs/data/source_catalogue.json`](../docs/data/source_catalogue.json), and source checks in [`../evidence/run_card.json`](../evidence/run_card.json).

- Zenodo record 11167510 is open under CC-BY-4.0 and lists a Nevada/nearby relocated catalogue and station-terms file. The files/schema and exact target-area event coverage were not checked.
- The USGS GeoDAWN record lists Area 1/Area 2 magnetic/radiometric grid archives and survey outlines. Files, terms and exact competition-polygon overlap were not checked.
- A 3DEP 1-meter index query against the GeoDAWN bounding rectangle returned project polygons; it is not a tile count or exact target-polygon coverage result.
- The USGS heat-flow record is CC0, but files and exact coverage were not checked. The Copernicus portal describes free access, but no Sentinel-1 target-scene query was made. GDR 1391 returned “No submission found.”

These public-source checks do not make an outside-lane feature viable. The four active hypotheses in [`../docs/research/findings.md`](../docs/research/findings.md) are all within the expected-DTI lane and use named cache channels; none is tested or globally novel.

## Next steps, in order

1. Resolve dense-prior semantics explicitly in the shared protocol; retain the negative gate until authorized. No private exception.
2. Restore and authenticate the exact shared feature cache, buffered OOF outputs, checkpoints and manifests. Verify file hashes, channel schema, valid footprint and exact submission grid; do not rebuild a private substitute.
3. Run every feature-alone leakage canary before one preregistered, nested buffered whole-component holdout. Derive catalogue features from visible faults only and apply the visible-fault mask pixel-exactly.
4. Fit isotonic calibration on spatially blocked/buffered OOF predictions; preserve at least 32 provenance-checked ensemble/TTA/MC-dropout truth draws, including the specified small jitter.
5. Run the exact mean-DTI greedy-add/backward-prune selector and compare against spacing/MCLP on the same surfaces/folds. Require improvement greater than two paired block-bootstrap SEs and a comparable prior best.
6. Check the complete registry before placement and on final dots; verify all raster hashes and decoded pixels. Stop on correlation/overlap gates or incomplete source access.
7. Only after every gate passes, write with the shared template writer, run the shared validator, complete one JSON run card and obtain separate slot authorization. Until then keep the site negative and offer no TIFF.

The experiment budget is at most three competition experiments or two hours. The current run used no competition experiment budget for geological modeling and no submission slot.