# Lane 64 — native-resolution lidar scarp channels

**Run `g64-scarp-native-lidar-20261011`.** Every number below is tagged with its evidence
class. Nothing here is a competition score, a leaderboard projection, or organizer-confirmed.

## 1. What changed in this run

The session began from a **negative** state: no TIFF existed, the site said
*NOT CLEARED FOR SUBMISSION*, and the recorded blocker was a registry witness whose 3-pixel
neighbourhood covers the entire allowed domain, making the literal 70 % dot-overlap rule
unsatisfiable for any nonempty candidate.

Three things unblocked the lane, all of them measured rather than asserted:

1. **The competition's own feature stack was restored.** `training_features.tif`
   (19 bands, 418 912 844 B) was fetched from a public owner mirror as five parts and
   reassembled; the assembled file hashes to
   `4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5`, byte-identical to the
   hash pinned in `data/prepared_manifest.json`. The grid template, mapped-fault catalogue and
   100 m DEM were restored alongside it and hash-checked. These remain **owner-mirrored, not
   organizer-authenticated** (IR-30-001 stands).
2. **The emission rule was re-derived from the published metric**, not from a threshold
   heuristic (section 2). The previous lane's blocker is shown below to be a property of the
   *rule*, not of this lane's output (section 6).
3. **A leakage canary fired and was honoured.** The first feature list included
   `derived_sgmc_faults_100m_u8.tif`. Held-out super-block AUC against the surrogate came back
   at **0.9985** — above the shared > 0.90 canary. The raster is derived from the same
   compilation that supplies the surrogate label, so it was removed from the feature list and
   re-run. The honest value is **0.7917** mean held-out AUC across the six scored blocks.

## 2. The metric, and the only free knob

Page 967 of the competition defines, verbatim:

```
TP_w = Σ_{g∈G} max_{x: d(x,g) ≤ R} p(x)·k(d(x,g))
FP_w = Σ_{x: p(x) > 0} p(x)·[1 − max_{g∈G} k(d(x,g))]
FN_w = Σ_{g∈G} [1 − max_{x: d(x,g) ≤ R} p(x)·k(d(x,g))]
k(d)  = max(1 − d/R, 0),  R = 300 m = 3 px at 100 m
DTI   = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)
```

`scripts/build_scarp_stage2.py::metric_terms` implements exactly this. Because every term is
linear in `p`, the argmax over `p` is at `p ∈ {0, 1}`: the entire optimisation problem is
**which cells to light up**, and the only other knob is **how many**.

With `T = TP_w`, `S = Σ p` and `A = Σ_x p(x)·k_g(x)` (mass already rewarded for proximity),

```
DTI = T / (0.2·T + 0.8·N_g + 0.2·(S − A))
```

so an added dot of value `v` pays iff

```
v · (0.8·N_g + 0.2·(S − A))  >  T · (0.2·v + 0.2)
```

i.e. a dot pays while its marginal kernel credit beats `0.2 × DTI` (scaled). That is why the
sibling project's five-rung ladder — 121 131 dots → 0.1922, 60 069 → 0.2477, 44 090 → 0.2600,
40 199 → 0.2708, 37 654 → 0.2778 (all owner-reported) — is a **pruning** ladder: their field
had saturated, so the ladder was buying score by removing mass. Our field does not saturate
until ≈120 000 dots on the surrogate, because held-out AUC 0.79 keeps the marginal credit
above the bar far longer.

## 3. Field

* **Positives** — independent-compilation (USGS SGMC) faults more than 300 m from the mapped
  catalogue: 61 664 px, 15 369 of them on the stride-2 candidate lattice.
* **Negatives** — 240 000 active lattice cells more than 300 m from *any* known fault in either
  compilation, sampled from a pool of 1 074 962.
* **Labels never include the catalogue**, because the competition's truth is by construction
  absent from it; the field's `distance-to-catalogue` term is used for placement diagnostics
  only and is **not** a feature.
* **Model** — `HistGradientBoostingClassifier`, 300 iterations, lr 0.06, 31 leaves, L2 = 1.0.
* **Features** — 122 columns: 19 organizer numerical bands, 12 lane lidar-scarp bands (each also
  averaged over 3 × 3 and, for scarps, 7 × 7 windows), 9 topography derivatives, 9 χ/knickpoint
  products, 4 radiometric, 4 magnetic-extension, every one at native scale and as a 3 × 3 mean.
* **Blocking** — 8 whole super-blocks of ~20 × 20 km. A block's field comes only from a model
  that never saw that block. Two blocks (SW and SE corners) contain no scored footprint at all,
  so the six fitted blocks cover the whole domain.

Held-out AUC by block: 0.7014, 0.8460, 0.8208, 0.8243, 0.7557, 0.8022 — mean **0.7917**.

## 4. Selection and emission size

Dots are chosen by **lazy-greedy maximisation of `Σ_t F(t) · max_dot k(|t − dot|)`** over the
candidate lattice, where `F` is the out-of-fold field. When `F` is the posterior fault
probability this objective *is* `E[TP_w]`, so the selector is the expected-DTI-optimal greedy
under a linear-in-`p` objective. The truth never enters the selector.

Measured surrogate curve (whole-domain, not blocked; evidence class **surrogate-CV**):

| dots | 20 000 | 40 000 | 60 000 | 80 000 | 100 000 | 120 000 | 160 000 | 200 000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| surrogate DTI | 0.1878 | 0.2824 | 0.3409 | 0.3753 | 0.3950 | **0.4007** | 0.3824 | 0.3551 |
| credit / dot | 0.5126 | 0.4185 | 0.3626 | 0.3199 | 0.2864 | 0.2561 | 0.2027 | 0.1649 |

(These supersede earlier values 0.0757 / 0.1219 / 0.1525 / 0.1722 / 0.1851 / 0.1909 / 0.1838 /
0.1707, which were produced by a `metric_terms` that took the `max` over the kernel alone in
`TP_w` and so credited no dot-less truth cell. Fixed and re-verified cell-by-cell against
`gems57.metric.dti_bruteforce`; see section 5.)

Emission size is then chosen by maximising the **exact** DTI expression for each assumed hidden
truth size `N_g` and transfer factor `τ` on the measured `T(K)`, `FP(K)`:

| N_g | τ | best K | implied DTI |
| --- | --- | --- | --- |
| 8 000 | 1.0 | 60 000 | 0.1651 |
| 8 000 | 0.5 | 60 000 | 0.0839 |
| 12 000 | 1.0 | 60 000 | 0.2057 |
| 12 000 | 0.5 | 60 000 | 0.1050 |
| 20 000 | 1.0 | 80 000 | 0.2643 |
| 20 000 | 0.5 | 80 000 | 0.1357 |
| 30 000 | 0.5 | 100 000 | 0.1627 |
| 61 664 | 1.0 | 120 000 | 0.4007 |

The shipped mass is the **median** of the per-assumption optima (70 000, which snaps to the
nearest measured support — 60 000, the tie against 80 000 broken downward): **60 000 dots**.
The surface is flat between 60 000 and 120 000, which is why the median rather than a single
assumption sets the number. Both the curve and the size table move at the metric fix (the
certified-credit definition changed), so the selected mass moved from 80 000 to 60 000 dots; the
shape of the argument is unchanged.

## 5. Gate result — population-matched blocked hide-and-recover

Eight whole super-blocks; the field is out-of-fold everywhere; each block receives a dot budget
proportional to its active area so that the pooled mass matches the artifact. Evidence class
**HOLDOUT-DTI**, evaluator `gems64-dti-exact-v1`.

| arm | pooled DTI | withheld truth px |
| --- | --- | --- |
| **this artifact (60 000 dots)** | **0.3408** | 61 664 |
| block-local greedy, same budgets | 0.3322 | 61 664 |
| area-matched random control | 0.1016 | 61 664 |
| incumbent `h33-2-b2` (the project's best public score, 37 654 dots) | 0.0939 | 61 664 |
| nearest-catalogue placement, same mass | 0.0092 | 61 664 |

Paired block bootstrap over the six fitted blocks (1000 draws):
this artifact − random = **+0.2217**, 1 SE = 0.0549, 95 % CI [+0.1836, +0.2586];
this artifact − incumbent = **+0.2247**; both clear the two-SE gate. **Verdict: promote.**

The incumbent scoring 0.0939 is not a defect in the incumbent. Under this instrument the truth
is *defined* to sit more than 300 m off the catalogue, and the incumbent is a pruned dilation of
the catalogue. That is precisely the point of the instrument: it measures the lane's own
objective, and the project's best public score is uninformative about it.

**Metric correction (this run).** An earlier revision of `metric_terms` maximised `k(d)` over
the kernel alone when accumulating `TP_w`, which credited a dot-less truth cell with zero
instead of the kernel weight of its nearest dot; on random fields its DTI read 0.0052 against
the reference evaluator's 0.0496. It is now `shifted_max(pad3, OFF, KW)` applied to `p(x)·k(d)`
for `TP_w` and to `k(d)` for `FP_w`, matching `gems57.metric.dti_bruteforce` to < 2 × 10⁻⁶ per
component on 8 random fields and to `dti_binary` on a 60-dot binary field, region-additive, and
`k(1 px) = 2/3` for a single off dot. Every `tp_w`/`dti` figure above is from the corrected
evaluator; the numbers published before the fix (0.1722 gate, 0.1909 curve peak, the 80 000-dot
size table) were invalid and have been replaced throughout.

## 6. Registry uniqueness, and one honest irregularity

Decoded-pixel comparison against all 62 rasters in the local registry:

* **Rank correlation** — worst |Spearman ρ| = **0.0700** (`h60_officialstack_50k.tif`), against a
  rule limit of 0.90. No prior surface resembles this one.
* **Dot overlap** — largest excess over a same-size random field placed on the same lattice
  is **+0.2504** (`h60_officialstack_50k.tif`). Against the nearest-catalogue family the excess
  is ≈ 0.
* **The irregularity.** Four rasters (`calib_r13lattice_00904`, `r13_lattice_s5_00904`,
  `r11_greedy_mp`, `r14_union_tips10_lat6`) already place a positive pixel within 3 px of
  ≥ 73 % of every allowed cell. Under the literal 70 % rule, *any* nonempty submission fails
  against them: this artifact measures 0.9992 literal overlap on the densest comparator, while a
  same-size random field measures 0.9984. The rule as written is unsatisfiable for dense
  self-covering comparators and therefore carries no information about lane drift here.

  **This is recorded, not waived.** Both measurements ship in
  `evidence/lane64_uniqueness.json`; the site and the run card state the ambiguity in plain
  language. The correct fix is a written protocol amendment (count overlap relative to the
  comparator's own null, or exempt explicitly self-covering comparators), decided by the owner,
  not a private exemption taken by this run.

## 7. Limitations

1. **No organizer receipt.** No submission has been made; no score is claimed.
2. **Surrogate ≠ private labels.** The field and the gate are measured against an independent
   compilation. Transfer to the private expert labels is unmeasured and is the top open risk.
   The instrument is also *internally* favourable: the field is trained on the same population
   it is scored against, only on other blocks.
3. **No cultural-feature mask.** The lane paragraph names one; it does not exist in this
   checkout. Roads, canals, field edges and cut banks share scarp morphology and are not masked.
   The confusion is recorded as the leading uncontrolled mimic rather than claimed as handled.
4. **Zero dots within 300 m of the mapped catalogue.** The surrogate excludes that band by
   construction, so the field is blind there. If the private labels include strands adjacent to
   the public map, this artifact cannot score them — the nearest-catalogue control arm measures
   that scenario at 0.0000. This is a deliberate, documented bet on the pixel-exact exclusion,
   and it is the single largest source of downside.
5. **1 m tiles were not re-derived.** The lane's scarplet/Steger/Frangi products were reused from
   the project's 100 m aggregate; the underlying 1 m tiles are gated.
6. **Two of eight blocks contain no footprint**, so the field has six folds, not eight.

## 8. Next session, in order

1. **Amend the uniqueness protocol in writing** (null-corrected overlap, or an explicit
   self-covering exemption). Until then the literal rule cannot distinguish any candidate.
2. **Test the near-catalogue hypothesis directly.** The one design choice that could cost
   everything is the hard 300 m exclusion. Build a two-arm artifact (field arm + annulus arm
   ranked by the lane's scarp channels) and measure the marginal credit of the annulus arm on a
   surrogate that does *not* exclude the annulus.
3. **Spend a slot only with the owner's authorization** and record filename + SHA-256 + returned
   score as one triple, which is the only durable attribution.
4. **Re-derive the lane at 1 m** if and when the gated DEM tiles become available.
