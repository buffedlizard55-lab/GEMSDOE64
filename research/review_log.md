# Review log

Reviewed in three passes on 2026-10-11 while building the site incrementally. This log records both successes and unresolved shortfalls; it is not a claim of competition validation.

## Pass 1 — numeric method and claim provenance

**Checks:** Ran `python scripts/verify_expected_dti_rule.py` with Python 3.11.2; checked exit status 0 and inspected the emitted values. Re-ran after renaming fields that could falsely suggest the synthetic truth-frequency examples had been isotonic-calibrated. Checked machine-readable probe and run-card JSON with Python's standard JSON parser. Reviewed the score-provenance note against the recorded organizer clarifications.

**Successes:** Published worked-example arithmetic, isolated threshold intuition, and the redundancy counterexample assertions all pass. Exact toy mean DTI decreases by `0.0006522770` after adding the candidate, demonstrating why expected marginal DTI—not a raw independent-pixel threshold—is required. The output labels itself synthetic-only. The `0.2778` claim remains unverified; pixel-exact known-fault masking and near-trace label risk are stated.

**Shortfalls:** This is not the shared competition evaluator; there are no real rasters, labels, calibrated model outputs, holdout folds, withheld-positive counts, CI, or organizer receipts. Nothing in this pass clears a submission.

## Pass 2 — documentation, site navigation and user-facing status

**Checks:** Reviewed the README brief, executive submission guide, methodology, four-hypothesis register, source register, score review, and negative run card. Ran a standard-library HTML link/fragment audit and checked Markdown local targets.

**Successes:** Five static site pages are present; all local file/fragment links resolve (101 anchors and 28 HTML IDs at this pass). The status banner, upload guide and run card agree that no TIFF exists and no download is cleared. The range-error guide covers out-of-range/logit/scale errors, non-finite values, nodata/mask semantics and exact-file validation, while warning against blind clipping. Four ranked hypotheses list source, layer, physical signature, mimic, novelty limits, cost and first falsification test. No leaderboard feed or result table was created. During review, synthetic frequency fields were named more precisely and the remote Google Fonts request was removed so the site has no required third-party font dependency.

**Shortfalls:** No visual browser/device QA has yet been claimed. External links are references, not a guarantee of current uptime, complete AOI coverage, or downloadable data. The sibling registry and shared feature stack remain unavailable, so novelty is provisional.

## Pass 3 — final release-gate and scope audit

**Checks:** Re-ran the synthetic probe; parsed both JSON files; rechecked every local HTML/Markdown target; asserted that the machine-readable run card has a negative verdict and null score/hash/validator fields; searched the checkout for `.tif`/`.tiff` files; searched site pages/CSS for TIFF download links, leaderboard mirrors, and external font requests; ran `git diff --check`.

**Successes:** All commands completed successfully. All 5 HTML pages, 101 anchors and 28 IDs passed local link/fragment checks; README/research Markdown targets resolve. The run card explicitly has `verdict=negative`, `submission_cleared=false`, `candidate_file_exists=false`, no holdout score/CI, no SHA-256 and no validator result. No GeoTIFF artifact exists. No leaderboard table/feed or TIFF download link is present. The synthetic script exits 0; its result remains correctly classified.

**Shortfalls / release blockers:** No competition data, authorized login, shared template/evaluator/writer/validator, prior-raster registry, geospatial/ML dependencies, holdout result, artifact, receipt or browser visual test. The site can therefore be published as an auditable project brief only; it cannot provide a competition download or score claim. These shortfalls are recorded in [`limitations_and_next.md`](limitations_and_next.md) and the [run card](run_card.json).
