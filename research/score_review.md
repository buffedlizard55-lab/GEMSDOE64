# Score and artifact provenance review

**Current evidence status: no verified competition score for this run.** Read the [project brief](../README.md) and [active run card](../evidence/run_card.json) first.

**Review date: 2026-10-11.** This is a provenance audit, not leaderboard monitoring. No leaderboard values are copied into this report. DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) restrict monitoring/copying absent prior written consent. Use the official challenge directly for current information, subject to those terms.

## Decision

The H33 value cited by the user is **not verified as a score for the named raster** in this project. There is no organizer submission receipt connecting the exact bytes, submission identifier, account, phase, and value. It is neither a `HOLDOUT-DTI` result produced by a spatially blocked evaluator here nor `ORGANIZER-CONFIRMED` here. Do not use it as a baseline, achievement, expected score, or reason to clear a new TIFF.

The GEMSDOE32 owner page describes an H33 variant derived by pruning a prior dotted map around known catalogue traces. It also distinguishes a candidate and modelled projection from organizer scores, and says no organizer score exists for its artifact. A second owner-maintained page also marks the score-to-file attribution as unverified. These project pages are useful hypotheses about method history, not submission receipts. The available pages do not establish that the named bytes were scored or that pruning caused the cited value.

## What can and cannot be inferred

| Item | What is supportable | What remains unverified |
|---|---|---|
| User-cited H33 value | A value is mentioned in the prompt and sibling-project history. | Whether the organizer evaluated the exact named raster and returned that value; receipt, submission ID, account, phase, and final artifact hash. |
| Raster identifier | The user supplied a unique-looking filename. | The exact bytes, projection, metadata, pixel values, whether it was uploaded, or whether it is the artifact described by an owner page. |
| Candidate mechanism | Removing redundant predictions can improve a spatial Tversky score if it removes false-positive mass without losing comparable true-positive coverage. | Whether this mechanism explains the named file or any reported delta. No before/after receipt or controlled evaluation is available. |
| Leaderboard context | The prompt includes user/owner leaderboard snapshots, which are not copied here. | Current score/rank, private-round performance, or any stable mapping from a sibling filename to a leaderboard value. This report does not query or mirror the page. |
| Owner-reported baselines | Sibling pages contain owner-reported candidate/benchmark claims. | Organizer confirmation, exact scored bytes, and comparability across versions or phases. |

## Why pruning could help—conditional explanation only

The published metric is a distance-weighted Tversky index with a 300 m triangular kernel and a higher false-negative than false-positive coefficient (`beta = 0.8`, `alpha = 0.2`). An added prediction near already-covered truth can contribute little new true-positive coverage because coverage uses a local maximum, while still adding false-positive mass. Removing that dot can therefore raise DTI **if** it reduces the denominator more than it sacrifices truth coverage. This is a plausible generic mechanism, not a retrospective diagnosis of the H33 claim.

There is an important competing risk. DrivenData staff clarified that the known-fault mask is pixel-exact and that unmasked neighboring pixels remain scoreable; new labels can include extensions/corrections near known traces. A multi-pixel catalogue buffer is not automatically free. Pruning may remove useful newly labeled flank geometry. It must be tested against buffered whole-segment holdouts with a pixel-exact visible-fault mask, then compared on the same plausible truth surfaces as the incumbent.

The synthetic check in this repository reinforces the same caution: a candidate's marginal truth frequency can exceed `alpha × mean baseline DTI` while adding it **decreases** exact mean DTI because of spatial overlap. See [`expected_dti_probe.json`](expected_dti_probe.json) and the active [research findings](../docs/research/findings.md). This is a synthetic result, not a competition score.

## Evidence required to upgrade a claim

1. Preserve the exact uploaded GeoTIFF bytes and compute SHA-256.
2. Provide the official submission receipt/page showing submission ID, timestamp, filename or hash, competition phase, and returned value.
3. Confirm the receipt refers to those exact bytes, not another run with a similar name.
4. Keep a separate `HOLDOUT-DTI` report with evaluator version, blocked-fold definition, withheld-positive count, pooled DTI, and 95% confidence interval. Never substitute one evidence class for another.
5. Do not scrape, poll, cache, or republish the leaderboard to fill a missing receipt; obtain prior written consent for any monitoring/copying workflow.

## References

- [Official GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Organizer clarification: pixel-exact known-fault mask](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)
- [Organizer clarification: pooled leaderboard aggregation](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550)
- [Organizer discussion: test-label provenance / new faults](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/10) · [near-trace “new fault” discussion](https://community.drivendata.org/t/where-do-you-draw-the-line/11536)
- [GEMSDOE32 project index](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) · [owner-maintained report](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/leaderboard.html)
- [GEMSDOE54 docs](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)
