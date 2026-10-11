# Review log

Reviewed in three passes on 2026-10-11 while building the site incrementally. This log records both successes and unresolved shortfalls; it is not a claim of competition validation.

## Pass 1 — numeric method and claim provenance

**Checks:** Ran `python scripts/verify_expected_dti_rule.py` with Python 3.11.2; checked exit status 0 and inspected the emitted values. Re-ran after renaming fields that could falsely suggest the synthetic truth-frequency examples had been isotonic-calibrated. Checked machine-readable probe and run-card JSON with Python's standard JSON parser. Reviewed the score-provenance note against the recorded organizer clarifications.

**Successes:** Published worked-example arithmetic, isolated threshold intuition, and the redundancy counterexample assertions all pass. Exact toy mean DTI decreases by `0.0006522770` after adding the candidate, demonstrating why expected marginal DTI—not a raw independent-pixel threshold—is required. The output labels itself synthetic-only. The H33 score-to-file claim remains unverified and is not repeated as a competition score; pixel-exact known-fault masking and near-trace label risk are stated.

**Shortfalls:** This is not the shared competition evaluator; there are no real rasters, labels, calibrated model outputs, holdout folds, withheld-positive counts, CI, or organizer receipts. Nothing in this pass clears a submission.

## Pass 2 — documentation, site navigation and user-facing status

**Checks:** Reviewed the README brief, executive submission guide, methodology, four-hypothesis register, source register, score review, and negative run card. Ran a standard-library HTML link/fragment audit and checked Markdown local targets.

**Successes:** Five static site pages are present; all local file/fragment links resolve (101 anchors and 28 HTML IDs at this pass). The status banner, upload guide and run card agree that no TIFF exists and no download is cleared. The range-error guide covers out-of-range/logit/scale errors, non-finite values, nodata/mask semantics and exact-file validation, while warning against blind clipping. Four ranked hypotheses list source, layer, physical signature, mimic, novelty limits, cost and first falsification test. No leaderboard feed or result table was created. During review, synthetic frequency fields were named more precisely and the remote Google Fonts request was removed so the site has no required third-party font dependency.

**Shortfalls:** No visual browser/device QA has yet been claimed. External links are references, not a guarantee of current uptime, complete AOI coverage, or downloadable data. The sibling registry and shared feature stack remain unavailable, so novelty is provisional.

## Pass 3 — final release-gate and scope audit

**Checks:** Re-ran the synthetic probe; parsed both JSON files; rechecked every local HTML/Markdown target; asserted that the machine-readable run card has a negative verdict and null score/hash/validator fields; searched the checkout for `.tif`/`.tiff` files; searched site pages/CSS for TIFF download links, leaderboard mirrors, and external font requests; ran `git diff --check`.

**Successes:** All commands completed successfully. All 5 HTML pages, 101 anchors and 28 IDs passed local link/fragment checks; README/research Markdown targets resolve. The run card explicitly has `verdict=negative`, `submission_cleared=false`, `candidate_file_exists=false`, no holdout score/CI, no SHA-256 and no validator result. No GeoTIFF artifact exists. No leaderboard table/feed or TIFF download link is present. The synthetic script exits 0; its result remains correctly classified.

**Shortfalls / release blockers:** No competition data, authorized login, shared template/evaluator/writer/validator, prior-raster registry, geospatial/ML dependencies, holdout result, artifact, receipt or browser visual test. The site can therefore be published as an auditable project brief only; it cannot provide a competition download or score claim. These shortfalls are recorded in [`limitations_and_next.md`](limitations_and_next.md) and the [run card](run_card.json).

## Follow-up review — source screen and site updates (2026-10-11)

### Pass 1 — source metadata and access status

**Checks:** Rechecked the official USGS GeoDAWN ScienceBase record and its file listing; queried the USGS National Map 1-meter index layer using GeoDAWN's published bounding rectangle; checked the Zenodo API metadata/files, USGS heat-flow release, Copernicus portal, OSTI INGENIOUS record and GDR 1391, and the USGS lidar publication link.

**Successes:** The Zenodo record lists an open CC-BY-4.0 catalogue and two files, not downloaded or schema-audited. GeoDAWN's public record lists two Area GeoTIFF grid archives and outlines, not downloaded or license/overlap-verified. The coarse 3DEP query returned 22 project polygons, explicitly not a tile count or exact competition-polygon overlay. The heat-flow record is CC0; Copernicus advertises free data access but no AOI acquisition query was run; GDR 1391 returned “No submission found.” The broken long-form USGS lidar URL was replaced with a verified Publications Warehouse page. All remaining source gaps are stated rather than inferred away.

**Shortfalls:** No external file was downloaded, checksummed locally, spatially overlaid on the exact competition polygon, or tested. The index result is coarse availability evidence only.

### Pass 2 — hypotheses, claims and user-facing site

**Checks:** Reviewed the updated five-hypothesis register for layers, physical mechanism/signature, rationale, named non-fault mimic, repo-novelty caveat, qualitative benefit/cost and source gate. Checked score provenance language across the site and research notes; audited local HTML and Markdown links.

**Successes:** The fifth candidate (GeoDAWN magnetic/radiometric discontinuities) is marked conditional, not tested or proven novel. The seismic, lidar, SAR and INGENIOUS candidates retain their distinct coverage/access gates. No numeric user/owner leaderboard value is repeated as a project score. Local links pass across 5 HTML pages (109 `href` values, 28 IDs) and 4 Markdown files. The top-level page and source register describe the no-download status.

**Shortfalls:** No visual browser/device QA was performed. External link reachability can change; source records do not establish holdout benefit or shared-stack novelty.

### Pass 3 — method and release-gate consistency

**Checks:** Re-ran `scripts/verify_expected_dti_rule.py` and compared its parsed output to `research/expected_dti_probe.json`; parsed both JSON research records; asserted the negative verdict, null holdout score/CI/hash and missing-validator state; ran `git diff --check` on staged and unstaged changes; searched for candidate TIFFs and remote-font dependencies.

**Successes:** The saved synthetic probe matches the fresh run and is clearly marked synthetic-only. The run card retains the expected-DTI lane, buffered isotonic calibration protocol, 32-raster minimum, exact marginal-gain greedy/backward-prune rule, same-surface incumbent comparison and negative promotion state. Both diff whitespace checks pass. No TIFF candidate, download link or remote-font dependency exists.

**Shortfalls / final blocker:** No competition modeling, holdout, feature-alone canary, registry comparison, artifact validation, submission, or slot use occurred because required data and shared tooling are absent. Visual QA and exact competition-AOI source overlays also remain unperformed. Verdict remains `negative`; do not offer a download.
