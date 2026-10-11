# Expected-DTI-optimal lane — a second, independent evidence set

Generated 2026-10-11 23:20 UTC by `scripts/build_lane_findings_expecteddti.py` directly from
`evidence/lane_expecteddti_*.json`. **No number on this page is hand-entered.**

This page records a **second evidence set** for the Expected-DTI-optimal selection lane, produced by
a parallel session on 2026-10-11 and merged alongside the published card. It does not replace or
re-score anything on that card: the site's published candidate and its run card remain
`evidence/run_card.json` and the promoted pair in `docs/submissions/`. This lane's own artifact is a
**negative result** and sits in the top-level `submissions/` directory, not in the deployed download
slot — `scripts/check_site.py` and `tests/test_policy.py` require `docs/submissions/` to hold
exactly the two promoted TIFFs, and a negative lane has no business there.

Everything below is `VERIFIED`, `MEASURED`, `HOLDOUT-AUC`, `SELF-CONSISTENT`, `DERIVED`,
`OWNER-REPORT` or `ORGANIZER-CONFIRMED`, labeled per occurrence. **No projection is written as a
score.**

---

## VERDICT: NEGATIVE RESULT — DO NOT PROMOTE / DO NOT SUBMIT

NEGATIVE RESULT — DO NOT PROMOTE. the decision rule is verified and beats spacing on held-out draws (z = 15.97, 32/32 draws); the artifact is unique (worst 3-px overlap 0.0120 over 63 registry rasters); the submittable twin passes the shared validator 18/18; but the calibrated surface is saturated (1.94% of cells at raw score 1.0, 4,907 distinct values across the top 200,000 candidates), so the ranking that selects the dots is decided by numpy's tie order, not by geology. Shipping this would spend a slot on a tie-break, not on a field. Failed arms: surface usability.

| gate condition | value | passed |
|---|---|---|
| rule gate > 2 block-bootstrap SEs | z = 15.97 | True |
| LANE not a duplicate | worst 3-px dot overlap 0.0120 vs limit 0.7 | True |
| format gate (shared `gems64.validate`) | EPSG:32611, no nodata tag | True |
| surface usable for ranking | 1.94% saturated at score 1.0 | False |

**Submission slots spent by this lane: 0.**

---

## What was built

`src/gems64/lane_expecteddti/` — supplementary modules that keep **no private fork** of the shared
tools. The grid constants come from `gems64.grid`, and the kernel, lattice offsets, α/β, the
brute-force oracle and the marginal rule come from `gems64.metric`; `metricext` adds only the
whole-grid field helpers and thin key-renaming adapters, and `engine` adds the sparse multi-draw
emitter state the shared modules do not carry.

| module | adds | consumes from shared |
|---|---|---|
| `gridext` | footprint / catalogue / scored-domain loaders, 19 band names, `GEMS64_DATA` root | `WIDTH`, `HEIGHT`, `EPSG`, `PIXEL_M`, `TRANSFORM` |
| `metricext` | `best_cover`, `kmax_field`, `components` (carries S/M/K), `dti_algebra`, `credit_audit` | `kernel`, `offsets`, `ALPHA`, `BETA`, `EPS`, `dti_from_components`, `marginal_inclusion_threshold`, `dti_binary`, `dti_bruteforce` |
| `engine` | `Ensemble` (commit/uncommit/delta_T/kmax), CELF lazy greedy, spacing arm, block bootstrap | `HEIGHT`, `WIDTH`, plus `metricext` |
| `emission` | synthetic-scale verification helpers | `metricext` |

The shared `gems64.grid` independently pins `SHA256_EXISTING_FAULTS = 7ba308ccdc4418b3…` and
`SHA256_SAMPLE_SUBMISSION = 2176d08e485aa2cd…`, which match the digests this lane measured from the
bytes on disk (`registry/data_manifest.json`) — two independent confirmations of the same pins.

Scripts: `scripts/lane_expecteddti_verify_rule.py`, `_invert_live_scores.py`, `_build_field.py`,
`_train_field.py`, `_train_and_calibrate.py` (the leaky first instrument, kept for the audit trail),
`_emit_and_ship.py`, `_gate.py`. Tests: `tests/test_lane_expecteddti_engine.py`.

---

## Experiment 1 — the decision rule, verified before use (7/7 PASS)

`VERIFIED` — `evidence/lane_expecteddti_exp1_rule.json`, reproduced by
`scripts/lane_expecteddti_verify_rule.py`.

| check | result | detail |
|---|---|---|
| `C1_bruteforce_agrees_with_vectorised` | PASS | max_abs_diff=7.105427357601002e-15 |
| `C2_FNw_equals_nG_minus_TPw` | PASS | max_abs_diff=0.0 |
| `C3_closed_form_equals_component_form` | PASS | max_abs_diff=1.1102230246251565e-16 |
| `C4_lipton_f1_threshold_is_half_optimal_f1` | PASS | residual_by_n={'1000': 0.0009461190686481935, '10000': 0.0001272217160317446, '100000': 5. |
| `C5_tversky_threshold_is_alpha_times_optimal_score` | PASS | by_alpha={'alpha=0.1': {'residual_at_1e4': 9.68401084373155e-05, 'residual_at_1e6': 3.1340 |
| `C6_spatial_marginal_rule_k_gt_alpha_dti` | PASS | violations=0, n_measurements=35, closed_form_dti_max_error=5.551115123125783e-17, sign_pai |
| `C7_joint_greedy_beats_independent_thresholding` | PASS | joint_wins_heldout=5/5, joint_wins_expected=5/5, mean_dti_gap_heldout=0.6717670614339275,  |

The closed form, with `T = TP_w`, `S = Σp`, `M = Σ_x p(x)·kmax(x)`, `K = |G|`, α = 0.2, β = 0.8:

```
DTI = T / ( α·(T + S − M) + β·K + ε )
```

and the marginal rule for one more unit of mass at `x`:

```
dT(x) = Σ_{g : d ≤ R} max(0, k(d) − best(g))     dS = 1     dM(x) = kmax(x)
dD    = α·(dT + 1 − kmax)
non-redundant case dT = dM = κ   ⟹   gain > 0  ⟺  κ > α·DTI
DTI_new = (T + κ) / (D + α)   exactly
```

Only **6** lattice weights are reachable at 100 m inside R = 3 px — `1.0, 0.6667, 0.5286, 0.3333,
0.2546, 0.057191` — and since DTI ≤ 1 caps the bar at α = 0.2, only the smallest (2,2)-diagonal
weight, at d = 2√2 px = 283 m, can ever be rejected, and only above DTI **0.2860**. Check C6
straddles that boundary from both sides with 0 violations in 35 deterministic measurements.

C7 is the substantive one: joint greedy beat independent thresholding on **5/5 held-out draws** with
**identical TP_w at 18–31× less mass**. Thresholding `E[kmax]` buys no extra credit and pays
α = 0.2 per unit of it — the prompt's warning against independent thresholding is quantitatively
correct, not merely prudent.

The shared module documents the same historical bar bug this lane hit independently (its
`IR-57-BAR-01` warning): both converge on `α·DTI` and both reject the `α·DTI/(1 − α·DTI)` form.

---

## Experiment 2 — live-anchored inversion: why 0.2778

`ORGANIZER-CONFIRMED` receipts inverted through the verified closed form —
`evidence/lane_expecteddti_exp2_inversion.json`, reproduced by
`scripts/lane_expecteddti_invert_live_scores.py`.

The registry contains exactly one **controlled pair**: a parent raster, and its child with every dot
inside 2 px of the published catalogue removed. Both have live scores.

```
h27-4-r1-solo-d2-8   0.2708   S = 40,199   ≤2 px from catalogue = 2,545
h33-2-b2             0.2778   S = 37,654   ≤2 px from catalogue =     0
```

Every owner-claimed pixel count reproduced **exactly** (37,654 / 40,199 / 44,090 / 40,000), and the
removed-dot count came out **2,545** — the number the owner's note claimed. Inverting
`T = DTI·(0.2·S + 0.8·K)` across the plausible range of hidden-truth size K:

| K | c parent | c child | c removed band | bar α·DTI | removal correct? |
|---|---|---|---|---|---|
| 6,000 | 0.0865 | 0.0910 | **0.0202** | 0.0542 | yes |
| 7,000 | 0.0919 | 0.0969 | **0.0180** | 0.0542 | yes |
| 7,905 | 0.0968 | 0.1022 | **0.0161** | 0.0542 | yes |
| 9,000 | 0.1027 | 0.1087 | **0.0136** | 0.0542 | yes |
| 10,000 | 0.1081 | 0.1146 | **0.0114** | 0.0542 | yes |
| 12,691 | 0.1226 | 0.1305 | **0.0055** | 0.0542 | yes |

**Finding.** Dots within 200 m of the published catalogue realise ≈0.0161
credit each against ≈0.1022 for the dots kept — a
**6.4× depletion** — and the removal was
correct by the marginal rule at *every* K. The conclusion does not depend on K, because the same K
appears in both arms and largely cancels in the difference.

`DERIVED` cross-check: going from `d2.8` (44,090 dots, 0.2600) to a flank-free set adds
ΔS = 6,436 dots for ΔT = 88, i.e. **0.0137 per dot**, within 15% of the controlled pair's 0.0161.
Note that `d2.8` has exactly 6,436 dots within 2 px — the flank band *is* the mass difference
between those family members.

### Why the depletion exists

1. **Masking.** DrivenData staff confirmed ([forum thread 11516](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516),
   16 Sep 2026) that pixels corresponding to known USGS/INGENIOUS faults are excluded from evaluation
   and from re-evaluation. A 300 m kernel centred near a mapped fault has much of its support inside
   the masked set, so there are fewer *scorable* truth cells to earn credit from. Mass on catalogue
   pixels earns no TP and incurs no FP — pure waste.
2. **Label construction.** The Prize Rules (§2) state the label universe includes faults "newly
   identified by geology experts at NLR and USGS". A newly identified fault is by construction one
   that was *not* already mapped, so the hidden truth is depleted near the published catalogue for a
   second, independent reason.

### Can 0.2778 be beaten?

`PROJECTION` — arithmetic on the closed form, explicitly **not** a score. The target is taken from
this repository's own verified leaderboard snapshot (`docs/data/leaderboard_snapshot.json`,
observed 2026-10-11, `verified: True`), whose erratum records a live re-read on 2026-10-11:
**#1 xiaofanhu 0.4133**, and the 0.2778 receipt under study sits at rank 23.
That supersedes the 2026-10-04 sibling-clone snapshot (whose top, 0.3262, is now rank 7 live).

At S = 37,654 and K = 7,905, `T = D·(α·S + β·K) = D·13,854.8`, so `c = T/S`:

| target D | who | required T | required c | vs 0.1022 today |
|---|---|---|---|---|
| 0.4133 | xiaofanhu (live #1) | 5,726 | 0.1521 | **+48.8%** |
| 0.3262 | nchuzhoy (live #7, was #1 on 2026-10-04) | 4,519 | 0.1200 | +17.4% |
| 0.2778 | extradr19 (live #23) — the receipt being explained | 3,849 | 0.1022 | +0.0% |

The family's own mass series says emission is already past its optimum — 37,654 → 44,090 dots adds
88 credit, 0.0137 each, against a 0.0556 bar. And `h33-2-b2` already has **zero** dots within 2 px,
so there is nothing left to prune. **The remaining +48.8% to live #1 (+17.4% to
the 2026-10-04 leader) is a field problem, not an emission problem.**

### The negative control that constrains every hypothesis

`ORGANIZER-CONFIRMED`: `sgmc-off-catalogue-44k` emitted 44,090 dots from USGS SGMC traces lying
beyond 300 m of the published catalogue — 21,160 features, 82,151 footprint px, 61,664 (75.1%) more
than 300 m from the given catalogue, by far the largest free pool of *known-real* faults absent from
the catalogue. It scored **0.0512**, with median distance 18.0 px and only 647 dots on the catalogue.

**Being off-catalogue is necessary but nowhere near sufficient.** A feature being real geology is not
evidence it is in the hidden label set. Any hypothesis of the form "emit known lineaments the
catalogue lacks" is refuted by this receipt unless it also supplies a mechanism predicting *which*
of them the experts would have newly identified.

### The measured registry (11 live-scored rasters)

| live DTI | S measured | claim matches | on catalogue | ≤2 px | median dist (px) | c@K7905 | artifact |
|---|---|---|---|---|---|---|---|
| 0.2778 | 37,654 | ✓ | 0 | 0 | 19.65 | 0.1022 | `h33-2-b2 (flank B=2 prune of the 0.2708 base)` |
| 0.2710 | 37,660 | — | 0 | 2,353 | 17.72 | 0.0997 | `h36-1-rung30-blind-r1` |
| 0.2708 | 40,199 | ✓ | 0 | 2,545 | 17.69 | 0.0968 | `h27-4-r1-solo-d2-8 (the 0.2708 base)` |
| 0.2707 | 37,860 | — | 0 | 2,353 | 17.69 | 0.0994 | `h38-1-hf-euler-r30-r1` |
| 0.2649 | 42,294 | — | 0 | 4,637 | 16.12 | 0.0926 | `h32-1-prethin-tip-euler-d2-8` |
| 0.2600 | 44,090 | ✓ | 0 | 6,436 | 15.00 | 0.0893 | `dotted-h19-5-d2-8 (44,090-dot incumbent)` |
| 0.2600 | 44,090 | — | 0 | 6,436 | 15.00 | 0.0893 | `efd28-repro (reproduction of d2.8)` |
| 0.2560 | 41,338 | — | 0 | 5,974 | 15.13 | 0.0904 | `wormrank-d28` |
| 0.2449 | 61,328 | — | 0 | 8,875 | 14.14 | 0.0742 | `topo-gap-closure-t-v2-on-d1-5` |
| 0.2376 | 40,000 | ✓ | 0 | 0 | 19.21 | 0.0851 | `gate_ortho_w0.25-40k` |
| 0.0512 | 44,090 | — | 647 | 3,259 | 18.03 | 0.0176 | `sgmc-off-catalogue-44k (USGS SGMC beyond 300 m o` |

---

## Experiment 3 — field, canary, emission, gate

### 3a/3b: the leakage canary did its job

`HOLDOUT-AUC` — `evidence/lane_expecteddti_exp3a_field.json`,
`evidence/lane_expecteddti_exp3b_field.json`.

The first instrument added four catalogue-proximity features and trained on them to predict the
catalogue. It reported pooled blocked AUC **0.9963** and hide-and-recover DTI **1.0000** in all four
groups, with the emission reproducing the withheld positives exactly. Both numbers are `ARTEFACT`:
the target *was* the feature source. The canary flags all four, and they are quarantined:

| feature | blocked AUC | verdict |
|---|---|---|
| `cat_prox_e5` | 0.9964 | **QUARANTINED** |
| `cat_prox_e15` | 0.9964 | **QUARANTINED** |
| `cat_prox_inv3` | 0.9890 | **QUARANTINED** |
| `cat_density_s6` | 0.9713 | **QUARANTINED** |

The circularity is not merely a statistical sin here — it is **directionally harmful**, because
Experiment 2 showed the metric pays *least* exactly where catalogue proximity is highest. A
catalogue-proximity model peaks where the credit is.

The honest field uses the 48 physical layers only. Single-feature blocked AUC maxes at
**0.7252** with **0 of 48 flagged** at the 0.90
threshold.

```
pooled blocked AUC  0.7301      AP  0.2189
prevalence          0.1291
isotonic Brier      0.12321 -> 0.10363
```

| fold | n train | n val | n val pos | AUC | AP |
|---|---|---|---|---|---|
| 0 | 367,615 | 101,264 | 8,548 | 0.7095 | 0.2053 |
| 1 | 372,642 | 95,220 | 8,597 | 0.6955 | 0.1574 |
| 2 | 377,090 | 92,553 | 5,100 | 0.8829 | 0.2888 |
| 3 | 373,535 | 94,797 | 12,002 | 0.6600 | 0.1820 |
| 4 | 381,225 | 88,752 | 26,741 | 0.8917 | 0.6838 |

The 0.2316 fold spread is the honest picture: fault detection generalises
very unevenly across blocked regions of the Great Basin. That spread is what spatial blocking is for
— random CV would have hidden it.

### 3c: emission

`SELF-CONSISTENT OBJECTIVE` — `evidence/lane_expecteddti_exp3c_emission.json`.

48 layers are streamed one at a time into a memmap over the scored domain (peak RAM one layer, not
45 — the first version materialised all of them and was OOM-killed in a 3 GB sandbox), scored in
chunks, and isotonic-calibrated on the blocked-OOF thresholds. Emission is CELF lazy-greedy over
**32 plausible truth rasters** (the score-ranked MAP estimate jittered by 1–2 px),
with a **live-calibrated catalogue-flank discount ρ = 0.1575** inside
2.0 px — replacing the family's hard buffer B ∈ {1, 2} with a measured continuous
one, so the strongest flank cells can still be emitted if they clear the bar.

Greedy stopped on its own at **14,075 dots** when the ensemble-mean marginal
gain reached zero; backward pruning then removed **0**, confirming the forward pass
had already reached the local optimum.

### 3d: the gate

`evidence/lane_expecteddti_exp3d_gate.json`, reproduced by `scripts/lane_expecteddti_gate.py`.

**Rule gate — `SELF-CONSISTENT OBJECTIVE` on held-out draws.** The greedy optimised against 32 draws
built with seed S; it is graded against 32 draws built with seed **S+1**, so it is not scored on its
own optimisation target — the same held-out-draw design that made C7 meaningful.

```
greedy  0.91883   vs   spacing  0.51394
mean difference 0.40489   block-bootstrap SE 0.02566   z = 15.97
positive on 32/32 draws, 400 block-bootstrap replicates each
mean truth coverage: spacing 0.5972 -> greedy 0.9517
```

What remains shared, and is disclosed, is the **surface**: both arms come from this model, so this
arm tests the *decision rule* and says nothing about whether the field is competitive.

**Catalogue-truth arm — `NULL` instrument, reported not used.** Its first version returned
DTI 0.00000 with z = nan because it computed `truth & footprint & ~catalogue` with `truth = catalogue`,
i.e. `truth & ~truth` — vacuous by construction. The masking belongs on the *emission* (which is
already confined to the scored domain), not on the truth. Once fixed, TP_w is still structurally ≈0:
13,871 of
14,075 dots lie beyond 3 px, median
31.8 px. A
placement scoring 0 against catalogue truth is exactly what Experiment 2 says it *should* do, so
using this arm as a gate would invert the sign of the measured effect. It is reported as null.

**LANE uniqueness — `MEASURED`, not a duplicate.** 63 registry rasters
compared. Worst 3-px dot overlap **0.0120** against a 0.70 limit;
worst Jaccard is likewise tiny. The rank-correlation arm is reported as **undefined**: every
compared registry raster is a binary dot field, so all shared values are equal and Spearman is
meaningless. The first version of this check scored that as 1.000 and declared a duplicate against a
raster with 0.012 overlap — a false positive that would have stopped the lane for no reason.

**Format gate — `MEASURED`, PASS via the shared validator.** This lane originally shipped its own
`scripts/validate_submission.py`; `main` already has `gems64.validate`, so the fork was dropped and
the shared tool is called with the footprint and catalogue so its in-footprint and
zero-dots-on-catalogue checks are exercised too.

| twin | shared validator | sha256 | positive px | range in footprint | nodata |
|---|---|---|---|---|---|
| `gems64-expecteddti-flank0.158-14k-20261011T210000Z-af6336e0-zeros.tif` | **PASS** 18/18 | `abc46d756dc437ea5a0bf8fe3160bfc8…` | 14,075 | [0.0, 0.999988] | None |
| `gems64-expecteddti-flank0.158-14k-20261011T210000Z-af6336e0-nan.tif` | FAIL 16/18 — `no_nan_anywhere`, `outside_footprint_zero` | `491fb1a9751034604ba8ce1937eb3a04…` | 14,075 | — | NaN outside footprint |

Both twins are bit-identical inside the footprint (same 14,075 positive px, same range) and differ
only outside it: `-zeros` writes 0.0, `-nan` writes NaN. The shared validator settles which one may
be submitted, and it does so asymmetrically — `-zeros` passes **18/18** and clears
`assert_submittable(rec)`, while `-nan` **fails 16/18** on `no_nan_anywhere` and
`outside_footprint_zero`. So `-zeros` is the submittable artifact and `-nan` is a comparison copy
that must never be uploaded.

This asymmetry is exactly the repository's adopted policy, and it is the direct fix for the
previously-reported `"Predicted values must be in range [0, 1]"` rejection. That error has two
independent mechanisms, both measured here: an unmasked `-3.4e38` sentinel on 3,061 in-footprint
cells, and a footprint mask derived from a *feature band* — which strands exactly those 3,061 scored
pixels as NaN, and NaN fails `((v >= 0) & (v <= 1)).all()`. The fix is to take the footprint from the
official template, convert sentinel to NaN before any arithmetic, then write all-finite values with
zeros outside the footprint and **no `nodata` tag** (matching the official reference writer, which
passes none). The shared validator's `range_0_1_guaranteed`, `no_sentinel_values` and
`in_footprint_all_finite` checks now pin all three.

The earlier receipt for this gate was written by this lane's private 15-check validator and recorded
`-nan` as `ok: true`. The gate was re-run end to end against the shared validator so the receipt is
produced by the code that is actually shipped; that re-run reproduced every other number in this
section identically (greedy 0.91883, spacing 0.51394, z = +15.97, 32/32 draws, worst overlap 0.0120).

### Why the verdict is negative

`MEASURED` — the binding constraint is the **surface**, not the rule:

```
1.94% of scored cells (99,016) saturate at raw score 1.0
the top 200,000 candidates span 0.9997 - 1.0000
with only 4,907 distinct values
```

Ranking inside that plateau is decided by numpy's tie order, not by geology. The first version of
the emitter ranked candidates by the *calibrated* π and found all 200,000 of them at exactly
π = 1.0000, so it selected the pool by tie order; it now ranks by the raw score, which is strictly
finer because isotonic is monotone. But 4,907 distinct values across 200,000 candidates is still
~40 cells per distinct value, so the ranking remains coarse exactly where every emission decision is
made.

A verified optimal decision rule pointed at an uninformative surface produces an arbitrary dot set
that looks excellent against truth sampled from itself. Shipping that would spend a weekly slot on a
tie-break. Per protocol, the negative result is the deliverable.

---

## Bugs found and fixed, each now unit-tested

Every one of these produced a *plausible number* rather than an exception, which is why the lane
tests the engine cell-by-cell against brute force instead of trusting a smoke test.

| # | bug | symptom | fix |
|---|---|---|---|
| 1 | `commit` **assigned** `best[]` instead of taking a max | a farther cell overwrote credit a nearer cell had earned; order-dependent T | `np.maximum`; exposed only once `refresh_TM` recomputed T from state |
| 2 | `uncommit` **zeroed T and M** when the removed cell had no truth within R | destroyed credit earned by every other emitted cell; T went negative | early return — such a cell contributed nothing |
| 3 | two membership broadcasts mis-aligned `(nt,)` vs `(1,R)` and `(R,nt)` vs `(nt,R)` | silently wrong when shapes happened to agree, raised otherwise | explicit `[:, None]` / `.T`, with the failure mode documented inline |
| 4 | `delta_T` omitted the flank discount `commit` applied | the CELF upper bound was not a bound for discounted cells | apply ρ to the kernel weight in both |
| 5 | `best`/`m_of`/`memT` in float32 | drifted ~1e-7 per commit/uncommit cycle; interleaved stress 6/8 → 2/8 as R grew | float64 (51 MB at \|U\|≈200k, R=32) |
| 6 | `block_bootstrap_gate` bootstrapped a ratio of per-block sums and called it a DTI difference | printed `+446.25 ± 193.12` for a quantity bounded by 1 | paired resampling that recomputes both DTIs per replicate |
| 7 | catalogue-truth gate arm computed `truth & ~truth` | DTI 0.00000, z = nan | mask the emission, not the truth; then report the arm as NULL |
| 8 | LANE Spearman on constant-valued binary rasters | scored 1.000, declared a duplicate at 0.012 overlap | require ≥3 distinct shared values; overlap is the operative statistic |
| 9 | 45 full-grid float32 layers materialised at once | OOM-killed in a 3 GB sandbox, empty output | stream: reduce each layer to the sample, then free it |
| 10 | `_z()` handed a boolean array | `numpy boolean subtract` TypeError | cast before standardising |
| 11 | blocked CV used equal-**width** bins on a serpentine index | folds of 219533 / 204399 / 34130 / 9769 / 4755 rows | equal-**count** bins on the rank, keeping folds contiguous |
| 12 | candidates ranked by calibrated π | all 200,000 at π = 1.0000 — pool chosen by tie order | rank by raw score (isotonic is monotone, raw is strictly finer) |
| 13 | `registry/data_manifest.json` full digests transcribed from truncated notes | reported `pin_pass=False` against real, correct files | measure digests from bytes; cross-check only the recorded 16-char prefix |
| 14 | verdict AND-ed both twins into `format_valid` | receipt read `format_valid: false` while its own reason string asserted "the artifact is unique and format-valid" | `format_valid` covers the *submittable* twin; `-nan` failing `no_nan_anywhere` + `outside_footprint_zero` is recorded as expected, and the reason is composed from the flags so it cannot contradict them |
| 15 | LANE check with zero reachable registry rasters | `worst_overlap` stayed at its −1.0 sentinel, so `duplicate=False` — uniqueness certified from an empty comparison | `duplicate = None` plus `lane_certified = False`, reported as UNVERIFIED; the registry roots are now env-overridable and the receipt records which were present |

Bug 13 is worth calling out separately: an earlier draft of this lane wrote out full 64-character
SHA-256 digests reconstructed from 16-character prefixes in session notes. That is fabrication, and
it produced a manifest that falsely reported three correctly-restored files as failing their pins.
The shipped manifest measures every digest from the bytes on disk and states explicitly which part
was cross-checked against a recorded prefix.

---

## Remaining work

1. **Fix the surface, not the rule.** Replace the saturating gradient-boosted classifier with a
   rank-preserving scorer — calibrated logistic on monotone feature transforms, or a shallow GBM
   with early stopping on the blocked OOF. Target: <0.1% of scored cells at the top of the range and
   ≥100k distinct values among the top 200k candidates. The shared `gems64.calibration` and
   `gems64.select` modules are the place to do it, not a lane-private trainer.
2. **Get a non-degenerate independent truth arm.** Train per withheld segment group (rebuild every
   catalogue-derived feature from the visible remainder) so the withheld segments are both unseen
   *and* unmasked, giving a non-zero denominator. Cost: 4 retrains plus 4 grid scorings.
3. **Validate the top hypothesis before any slot.** `cond_grad` is already built and canary-cleared
   at 0.636. One blocked-holdout run either promotes or kills it cheaply.
4. **Re-run the gate on the improved surface.** The emitter, block bootstrap, LANE check and shared
   validator are all tested and reusable; only the surface changes.

## Candidate hypotheses (ranked by expected gain vs cost — judgements, not measurements)

| # | hypothesis | gain | cost | new external data |
|---|---|---|---|---|
| 1 | **Clay-cap breach** — lateral *gradient* of near-surface conductivity, intersected with shallow basement, thinned to ridges | medium-high | low | none |
| 2 | **Relay ramps / step-over terminations** — the catalogue as a *graph* whose missing edges are the target | high | medium | none |
| 3 | **Drainage deflection and beheaded channels** — a vector-field measure, orthogonal to the amplitude measures already used | medium | medium | USGS 3DEP 1 m DEM (free, official; obtainability already verified by a prior bridge) |
| 4 | **Magnetic-gradient fabric** — ridge extraction on the horizontal/vertical gradient *ratio*, not amplitude | low-medium | low | none |
| 5 | **Quaternary volcanism as a permeability prior** — use as a prior, never as a primary emitter | low | low | none |

Each names a mechanism for why the target fault would be **missing** from the USGS/INGENIOUS
catalogue rather than merely near it: #1 and #4 are alteration signatures invisible to surface
mapping; #2 targets connecting structures oblique to both mapped tips; #3 targets faults hidden
under basin fill; #5 marks plumbing, not trace.

**None of these has been through a holdout.** The protocol requires the top-ranked one to be
validated on the spatially blocked holdout before a slot is touched, and this lane ran out of budget
on its own verification work. Do not spend a slot on any row above.

`cond_grad` (0.636) and `conductivity` (0.652) are both already built and comfortably under the 0.90
leakage threshold, so #1 is falsifiable in a single run.

---

## Limitations

- **No local instrument can estimate live DTI.** The best available in the sibling repositories
  correlates with owner live scores at ρ = +0.54 on n = 12, not significant at p ≈ 0.09. Everything
  here is a rule comparison plus a receipt inversion, never a score forecast.
- **The 32 truth draws come from this lane's own surface.** They are independent of the greedy's
  optimisation target (seed + 1) but not of the field, so the rule gate tests the rule.
- **Catalogue truth is structurally null for this lane** and is reported as null rather than as a
  zero score.
- **K is unknown.** All credit-per-dot figures are a profile over K = 6,000–12,691; only differences
  within a controlled pair are robust to K. A naive constant-c assumption across family members
  yields K = −3,005, which is impossible — c is not constant across the family, so only the pair
  difference is trustworthy.
- **Live scores were not receipted by this lane; drivendata.org is unreachable from this sandbox.**
  The leaderboard target comes from this repository's own verified snapshot
  (`docs/data/leaderboard_snapshot.json`, `observed_utc` 2026-10-11, `verified: True`), which
  is a *manual rendered-page fetch*, not an automated request to the competition host. Its erratum
  states plainly that snapshot rows 2–10 do **not** match the live board re-read on 2026-10-11, and
  that rows beyond rank 24 were not re-verified — so the top of the board (0.4133) is live-read
  while the tail is snapshot-only, and the two must not be mixed. Family scores come from
  sibling-repository ledgers. Only 0.2778 and 0.0512 are treated here as `ORGANIZER-CONFIRMED`
  receipts, and the projection target is labeled `PROJECTION`, never as a score.
- **Budget exceeded.** The protocol allowed 3 experiments or 2 hours. The three experiments ran, but
  debugging the emitter to exactness — fifteen bugs, each producing a plausible number rather than
  an exception — pushed wall-clock well past 2 hours. Recorded rather than hidden.
- **External geoscience layers were not used.** USGS SGMC, 3DEP 1 m DEM and GeoDAWN products exist in
  sibling repositories with verified digests, but integrating them was out of budget, and the SGMC
  negative control (0.0512) argues that adding them without a mechanism is not obviously helpful.

## Irregularities flagged

1. Contradictory "current high score" in the task prompt (0.3774 vs 0.3195), resolved against this
   repository's own verified snapshot: **`0.3195` is real** (DARD, live rank 9 on the 2026-10-11
   re-read) and **`0.3774` appears nowhere** — not in the 50 snapshot rows, not in the live re-read
   rows, and not in any of the five sibling-clone ledgers (confirmed absent). The bar to beat is
   **0.4133** (xiaofanhu, live #1), materially higher than the 0.3262 that was #1 on
   2026-10-04, so any improvement target computed from the older snapshot understates the gap by
   roughly a third.
2. This repository **shipped empty** at branch time despite the instruction to reuse
   `evaluate_holdout.py`, `submission_writer.py` and a cached feature stack — those live in sibling
   repositories, and `main` has since grown its own. Rebuilt, then de-forked into the shared tools
   at merge time.
3. `labels.tif` is **int8** with nodata −1, not int32 as the reference notebook states.
4. **Deadline conflict**: Prize Rules Appendix A.1 (5 p.m. ET) vs the homepage (2026-12-03 11:59
   p.m. UTC).
5. `sample_submission.tif` is the **label raster re-encoded** — its `−1` mask is exactly the template
   NaN mask and its `1` mask exactly the template `1` mask. Only its footprint may be used, never its
   values.
6. **Isotonic saturation** — see the verdict section. This is the finding that stopped the lane.
