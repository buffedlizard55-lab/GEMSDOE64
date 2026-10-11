> **Historical parallel-session snapshot from PR #1.** Preserved, not independently re-verified by this session. Some availability statements are superseded. See the [current README](../README.md) and [current run card](../evidence/run_card.json).

# Score and artifact provenance review

**Review date: 2026-10-11.** This is a provenance audit, not leaderboard monitoring. No current leaderboard value is mirrored here; DrivenData's [Terms of Use](https://www.drivendata.org/termsofuse/) restrict monitoring/copying absent prior written consent. Use the official challenge directly for current information, subject to those terms.

## Decision

The user-cited value **0.2778** for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is **not verified as a score for that raster** in this project. There is no organizer submission receipt connecting the cited bytes, submission, account and score. It is neither a `HOLDOUT-DTI` result produced by a spatially blocked evaluator here nor `ORGANIZER-CONFIRMED` here. Do not use it as a baseline, achievement, expected score, or reason to clear a new TIFF.

The GEMSDOE32 page describes a raster variant involving a dotted-H19-5 basis and catalogue-flank pruning, and projects a score for it; that projection is not an organizer score. A GEMSDOE54 project page reports that 0.2778 appeared at rank 13 in its manual **2026-10-09** read while also marking the file unscored / its attribution as unverified. The rank is a dated secondary report, not a receipt and not a current rank. GEMSDOE32 separately describes an owner-claimed best of 0.2600; that is likewise not confirmation for the named raster.

## What can and cannot be inferred

| Item | What is supportable | What remains unverified |
|---|---|---|
| Claimed value `0.2778` | A value is cited in project/sibling-page history. | That the organizer evaluated this exact file and returned this value; submission ID, receipt, account, phase and final artifact hash. |
| Raster name `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` | User-supplied identifier. | The exact bytes, projection, metadata, pixel values, whether it was uploaded or scored, or whether it is the artifact described by a page. |
| Candidate mechanism | Removing redundant predictions can improve a spatial Tversky score when it removes false-positive mass without losing comparable true-positive coverage. | Whether that mechanism explains the named file, and whether its reported score or any delta came from pruning. No before/after receipt or controlled evaluation is available. |
| Rank context | Earlier notes contain a one-time official-page read of 0.4133 at rank 1 and 0.3195 at rank 9; the sibling page has a dated 2026-10-09 report. | Any of these values or ranks being current now; a stable relationship between leaderboard rank and a local raster. No fresh leaderboard check was made. |
| Owner-declared `0.2600` | GEMSDOE32 labels it an owner-claimed best. | Organizer confirmation, exact scored bytes and comparability to another file or competition phase. |

## Why pruning could help—conditional explanation only

The published metric is a distance-weighted Tversky index with a 300 m triangular kernel and heavier false-negative than false-positive coefficient (`β = 0.8`, `α = 0.2`). An added prediction near already-covered truth can contribute little new true-positive coverage because kernel coverage uses a local maximum, while still adding false-positive mass. Removing that dot can therefore raise DTI **if** it reduces the denominator more than it sacrifices truth coverage. That is a plausible generic mechanism, not a retrospective diagnosis of `0.2778`.

There is an important competing risk. DrivenData staff clarified that the known-fault mask is pixel-exact and that unmasked neighboring pixels remain scoreable; new labels can include extensions/corrections near known traces. A multi-pixel catalogue buffer is not automatically free. Pruning may remove useful newly labeled flank geometry. It must be tested against buffered whole-segment holdouts with a pixel-exact visible-fault mask, then compared on the same plausible truth surfaces as the incumbent.

The synthetic check in this repository reinforces the same caution: raw candidate frequency can exceed `α × mean baseline DTI` while adding the candidate **decreases** exact mean DTI because of spatial overlap. See [`expected_dti_probe.json`](expected_dti_probe.json) and [`../methodology.html`](../methodology.html). It is not a competition score.

## Evidence required to upgrade a claim

1. Preserve the exact uploaded GeoTIFF bytes and compute SHA-256.
2. Provide the official submission receipt/page showing submission ID, timestamp, filename or hash, competition phase and score.
3. Confirm the receipt refers to this exact raster, not another run with a similar name.
4. Keep a separate `HOLDOUT-DTI` report with evaluator version, blocked-fold definition, withheld-positive count, pooled DTI, and 95% confidence interval. Never substitute one score class for the other.
5. Do not scrape, poll, cache or republish the leaderboard to fill a missing receipt; obtain prior written consent for any monitoring/copying workflow.

## References

- [Official GEMS problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Organizer clarification: pixel-exact known-fault mask](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)
- [Organizer clarification: pooled leaderboard aggregation](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550)
- [Organizer discussion: test-label provenance / new faults](https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/10) · [near-trace “new fault” discussion](https://community.drivendata.org/t/where-do-you-draw-the-line/11536)
- [GEMSDOE32 project index](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) · [dated score page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/leaderboard.html)
- [GEMSDOE54 docs](https://buffedlizard55-lab.github.io/GEMSDOE54/docs/)
