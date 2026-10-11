# Review findings — expected-DTI selection lane

## Decision

**NEGATIVE / NOT CLEARED FOR SUBMISSION.** No new competition TIFF was created.
There is no approved download and no slot was used. This is an explicit failure
to meet the request for a new deliverable TIFF, not a claim that a placeholder
satisfies that request. The user's own mandatory stop/promotion rules take
precedence over publishing an unvalidated file.

## What was actually available

The starting GEMSDOE64 commit `c45c7fa9816d15f3bffdada2be9297b6f87e39ee`
contained only an 11-byte README. No previous pipeline, cache, trainable model,
holdout best, or next-session task list existed in this checkout. Those claims
in the prompt describe other sessions, not this repository.

The shared evaluator, metric, holdout, writer and validator were imported from
[60GEMSDOE at a fixed commit](https://github.com/buffedlizard55-lab/60GEMSDOE/tree/6444fa6552335190f0bc89661acf725ed73e7fcb/src/gems57).
Original file hashes and local corrections are recorded. One implementation is
used; there is no private scoring or TIFF-writing fork in the lane package.
The advertised 35-channel cache receipt points to `/tmp/gems32/work/feature_stack.npy`;
its bytes were not present in the checkout or in the inspected Git trees.
A receipt is not a cache. No substitute feature stack was rebuilt.
The [pinned feature receipt](https://github.com/buffedlizard55-lab/60GEMSDOE/blob/6444fa6552335190f0bc89661acf725ed73e7fcb/registry/feature_receipt.json)
reports 5,165,852 footprint cells, while the downloaded sample has 5,167,373 finite
cells: a **receipt-level difference of 1,521 cells**. Feature bytes were unavailable,
so this is not a measured feature-mask comparison. It is a format/provenance
warning: do not use a narrower feature-validity mask to put NaNs inside the
sample footprint. This does not establish the cause of the user's rejected file.


Pinned sample/catalogue TIFFs were recovered through GitHub bridges. They have
the expected grid, but a matching third-party hash is not independent proof of
official origin. `labels.tif` in the inspected sibling is the same catalogue,
not independent hidden-fault truth. Public source metadata were subsequently
checked through official catalog pages; no external data bytes were acquired.
No authenticated DrivenData login, leaderboard query, or weekly-cap observation
was made.

## Why the GEMSDOE32 artifact could be effective

This is a measured algorithm reconstruction, not a causal leaderboard analysis.
The published H33-2-B2 TIFF has **37,654 positive cells**. Its predecessor has
**40,199**. Removing predecessor dots at Euclidean catalogue distance **≤2 pixels**
produces the H33 support exactly: **2,545 deletions, zero additions, zero pixel
disagreements**. Both arrays were read and compared on the pinned grid. The H33
file SHA-256 is `c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9`.
These are ARTIFACT MEASUREMENTS, not scores.

Sources:
- [Published H33 artifact audit](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/b39e16ee85f83e3291951f56b615d657a071bb2b/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-audit.json)
- [H33 source page](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/b39e16ee85f83e3291951f56b615d657a071bb2b/docs/index.html)
- `evidence/h33_forensics.json` and `scripts/audit_h33.py` in this repository.

With T = TP, F = FP and K = truth count, the shared kernel metric gives
D = α(T+F)+βK when α+β=1. Deleting a dot with lost true credit t and saved false
credit f improves the realized ratio exactly when

    (1 − α S) t < α S f,  where S = T / D.

Thus deletion helps if it saves penalty with little loss of unique coverage.
Known-fault-adjacent predictions may spend mass on already explained structures;
a sparse layout may reduce kernel redundancy. But distance to a known fault is
not proof that an unseen splay is absent. The 200 m pruning rule can also delete
real hidden continuations. We cannot attribute an organizer score to any of
these mechanisms without hidden truth or a defensible independent experiment.

The H33 score-to-file claim and the prompt's leaderboard snapshots are **unverified**: no organizer receipt connects a value to the exact artifact, account, and competition phase. The pinned owner page also distinguishes a projection from an organizer score. No numerical user/owner leaderboard claim is reproduced here, treated as a baseline, or presented as a result. No improvement over an organizer-confirmed score is established or promised.

## The threshold claim: a necessary correction

For independent binary decisions without spatial credit, define the **ratio of
expected counts**

    S(A) = sum(i in A) p_i / [α |A| + β sum(i) p_i].

Adding a cell improves this surrogate iff `p_i > α S(A)`. At an optimum, the
threshold is `α S*`; for F1, α=β=1/2. At a hypothetical surrogate value 0.30,
α=0.2 gives the arithmetic threshold 0.06. Those are hypothetical mathematical
values, not a measured HOLDOUT-DTI or competition score.

We checked 204,800 additions across 200 probability vectors and all their
256 subsets: no surrogate-rule contradictions. **But expectation of a ratio
is not generally the ratio of expectations.** Exhaustive enumeration of four
Bernoulli truths found a counterexample: the proposed pixel probability exceeds
α times the exact expected score, while the exact expected score decreases.
The probabilities and all calculations are in `evidence/synthetic_verification.json`.
This falsifies the unrestricted finite-raster claim; it does not falsify the
population/surrogate F1 result attributed to Lipton, Elkan and Narayanaswamy.
[Primary-author preprint link, not fetched here](https://arxiv.org/abs/1402.1892).

For the shared spatial metric, truth coverage is a maximum over predictions,
whereas the FP term sums prediction costs. A new dot may cover many truth cells;
its ΔTP can exceed its nearest-truth credit and even one. The correct realized
inclusion test is

    ΔTP > α S [ΔTP + 1 − nearest_truth_kernel_credit].

A scalar calibrated probability cannot encode redundancy or the joint spatial
truth distribution. The reference selector therefore averages **each draw's
actual ratio**, re-evaluates all additions, and then removes dots while removal
increases the mean. It does not assume submodularity for lazy updates. Thirty-two
synthetic jittered line rasters verified exact agreement with the literal
brute-force metric oracle. They are not trained ensemble/TTA/MC-dropout outputs,
not calibration evidence, and never a holdout score. The reference implementation
has explicit size/time limits and is not a production-scale optimizer.

## Decisive registry stop

[17GEMSDOE's E-proba-multiscale artifact](https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif)
has positive finite values at **all 5,167,373 footprint cells**. Its 3-pixel halo
covers **all 5,106,385 off-catalogue allowed cells**. The downloaded witness hash
is `ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be`.
The sample, catalogue, and witness grids were checked before the calculation.

Under the template's literal rule that every positive prediction pixel is a dot,
any nonempty candidate has forward overlap 1.0 with this prior, whatever its
geology or rank correlation. This is a universal obstruction, not a measured
candidate correlation or evidence of scientific copying. Excluding dense priors
could make a sensible *revised* protocol, but that change is not authorized by
this prompt. This session retains the literal rule and stops before production
fitting/placement. No surface or final dots exist to compare. Full byte/pixel
comparison against every prior is **not complete**; it is unnecessary to prove
this single-witness failure, and would remain mandatory for a promotion.

## Four ranked in-lane geological hypotheses — not tested claims

There was no implementation to differ from in the starting repository. We do not
claim global novelty across every sibling's source code. In fact scarp, magnetic,
radiometric, and basement-edge families have already appeared in the supplied
history. The proposed novel intervention here is the **calibration/expected-DTI
placement rule**, not rediscovery of those layers. Rankings below are qualitative
engineering priorities, not predicted DTI values. Only H64-A would be eligible
for a first experiment after blockers are resolved.

| Priority | Hypothesis and specific cached layers | Physical signature and reason for off-catalogue recovery | Non-fault mimic | Distinction / expected opportunity / cost |
|---|---|---|---|---|
| 1 · H64-A | Weak cross-sensor ridge consensus: cached det_elev_slope, curv_s1/s2, tmi_edge/rtp_edge, grav_edge | Modest aligned scarp curvature and potential-field edges may jointly support subtle or partly buried extensions too weak for a single-layer threshold | Differential erosion at lithologic contacts | Preserve cache features; calibrate OOF uncertainty, then replace spacing with exact expected-gain placement. Highest relative opportunity, medium cost; cache/OOF absent |
| 2 · H64-B | Along-strike continuity with localized uncertainty: cached ridge_s1/s2/s3, coherence_s2, strike_cos/sin | Multiscale ridge agreement could maintain degraded fault expression under patchy surface cover without catalogue continuation features | Drainage incision or terrace margins | Same selection lane, not a new line detector; retain plausible shifted truths rather than an arbitrary exclusion radius. Medium opportunity, medium cost |
| 3 · H64-C | Buried shallow-edge corroboration: cached depth_grad, grav_edge, tmi_edge | Coincident independent gradients might locate buried steps where catalogue surface expression is missing | Intrusive or depositional lithologic boundaries | Existing edge transforms only; posterior positional spread penalizes unresolved locations. Lower localization confidence at 300 m, medium cost; earlier basement lanes already tested broader family |
| 4 · H64-D | Conductivity-boundary/topographic disagreement: cached cond_edge, ridge_s2, relief5 | Localized electrical transition near a subtle ridge could indicate fluid-altered structure omitted from a surface-fault catalogue | Saline playa sediments or non-fault clay layers | No new MT inversion or new data acquisition; exact marginal utility can reject broad uncertain anomalies. Lowest confidence, medium cost; conductivity-claycap family not globally new |

All four active hypotheses depend on *existing named cache channels*, not newly
proposed external layers. None is viable until the cache bytes/provenance and
registry semantics are resolved. Separate source reconnaissance checked the
[USGS GeoDAWN ScienceBase record](https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7): it lists Area 1/Area 2 GeoTIFF grid archives, but no files were downloaded, file-level terms audited, or exact competition polygon overlaid. The linked [GDR 1391 page](https://gdr.openei.org/submissions/1391) returned “No submission found.” These are metadata checks only, not active off-lane feature proposals. No feature-only canary was run on real data because no feature stack was used. Cross-sensor correlation is not causal proof of a permeable fault, and fault detection is not direct geothermal-vent or reservoir confirmation.

## Next session, in order

1. Resolve the registry semantics explicitly upstream: keep this negative verdict
   unless the owner changes how dense continuous rasters participate in dot overlap.
2. Restore the exact shared feature-cache bytes with hashes, band descriptions,
   official provenance and model/OOF manifests. Do not reconstruct an untracked substitute.
3. Rebuild a single shared, nested buffered blocked experiment from whole components;
   fit each catalogue-derived feature on visible faults only. Run every feature's
   canary before modeling; investigate AUC >0.90 (also its inverse).
4. Train/calibrate without evaluation-label access; preserve spatially correlated
   ensemble, TTA and genuine MC-dropout variation, with non-wrapping 1–2 pixel
   positional perturbations. Thirty-two copies or independent jitter alone do not
   substitute for epistemic uncertainty. Check calibration on unbalanced population
   prevalence; catalogue probability is not automatically unmapped-fault probability.
5. Scale the exact-gain reference algorithm using sparse/local coverage updates,
   retaining a full oracle test. Compare with frozen spacing and MCLP on the **same
   surface**, same fold masks, and the same truth; compare to a comparable historical
   best. Pool terms before resampling 20 km blocks; require gain >2 paired SEs.
6. Only if all gates pass: write using the shared writer; run the on-disk validator;
   do SHA and decoded-pixel checks against the full declared registry; publish one
   unique TIFF with a ≤140-character note. Promotion to a weekly slot is a separate
   authorized selector operation after checking the actual submission-page cap.

## Range-error response and limitations

The user's earlier file was not supplied, so its rejection cause is unknown.
Possibilities include nodata sentinels, unnormalized output, infinity, or NaN
inside the footprint. This writer never silently clips/repairs model output.
Binary dots are already in [0,1]; all-finite zero-outside export is stricter than
“NaN only outside,” so no NaN can leak inside. It checks float32, EPSG:32611,
100 m pixels, exact shape/affine, footprint, catalogue masking, nonempty support,
and the serialized TIFF and ZIP. Tests deliberately reject bad range/sentinels
and verify a synthetic round-trip fixture, but **no production validator pass**
is claimed. A local format pass is not organizer acceptance.

The official [reference README](https://github.com/drivendataorg/gems-prize-reference-solution/blob/aebe92f7c8a990f0e3443451b7a825d9afd6336b/README.md)
explicitly supports CPU-only execution. “GPU needed” and “only blocker is data
placement” are not accurate descriptions of this checkout. The notebook's
Tversky training loss is not an official spatial-DTI test oracle. We verified
internal metric arithmetic against a separate literal implementation, not a
live organizer test endpoint.
