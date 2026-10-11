# Review findings — lidar-scarp lane, run 64

## Decision

**NEGATIVE / NOT CLEARED FOR SUBMISSION.** One candidate TIFF was generated,
hashed, validated and published for download **labelled as not-cleared**. No
weekly slot was used, no promotion is claimed, and the owner-reported champion
is not beaten on the evidence that this run was able to measure where the
terrain-class mimic cannot explain the gain.

Every number below carries its evidence class:

* `PROXY-INSTRUMENT (sgmc_off)` — a state-geological-map fault population located
  more than 300 m from the mapped catalogue, evaluated on the shared evaluator
  (`gems57-pooled-hide-v3-se`). It is *not* the hidden panel and it favours
  rock-exposed terrain.
* `HOLDOUT-DTI (catalogue_hide)` — whole-component hide-and-recover on the mapped
  catalogue, shared evaluator, 4 label-blind quadrant folds, 80 px buffer.
* `REGISTRY-MEASUREMENT` — byte, pixel, rank and dot-overlap comparisons against
  the reachable registry rasters.
* `ORGANIZER-CONFIRMED` — **none exists in this repository**.

## What was actually built

A **catalogue-independent** surface: the lane never uses distance-to-catalogue,
catalogue density or any catalogue-derived feature to rank cells. The pipeline is
12 quantised 2 m lidar scarp channels and 7 quantised 3 m scarp channels, decoded
from their published manifests, reduced to named components at 100 m (amplitude,
SNR-weighted amplitude, step, crest/base curvature, vergence asymmetry,
cross-strike consistency, coherence, relief, 3 m replication, coverage), then
percentile-ranked inside an eligible domain (lidar-covered cells, at least 3 px
from the mapped catalogue, outside the cultural mask) and thinned by a greedy
1.5 px blue-noise selection.

The run also ablated every component and the pre-declared equal-weight composite
(0.45 amplitude / 0.30 coherence / 0.25 3 m replication) at 24 000 dots each
(`PROXY-INSTRUMENT (sgmc_off)`). The composite is the **worst arm measured**
(DTI 0.02372, credit 0.0540 per dot), because coherence (0.03217 / 0.0733) and the
3 m replication gate (0.02390 / 0.0544) carry almost nothing and the gate even
*anti*-correlates with the state-map population (canary AUC 0.343). The adopted
surface is therefore the strongest single component, `amp_snr = sqrt(ex_max · ex_mean)`
(0.10352 / 0.2377), with `amp_mean` (0.10291), `base` (0.10263) and `step`
(0.10252) statistically beside it; `relief` reaches 0.08366 and `vergence`,
`coh`, `replicate3m` stay at or below 0.05. That is a selection made **on the
instrument**, and every receipt says so.

## Instrument 1 — `PROXY-INSTRUMENT (sgmc_off)`

Domain: 2 967 065 eligible cells, 62 122 truth pixels (≥3 px from the catalogue),
4 label-blind quadrant folds, 200 px (20 km) block bootstrap, 1 000 draws.
The owner-reported champion `GEMSDOE32__h33-2-b2-zeros.tif` (sha256 `c55bafc4…`)
is re-measured on the same instrument as a comparator arm — never as a score.

| arm (37 654 dots unless noted) | DTI | 95 % CI | credit per dot |
|---|---|---|---|
| lane `amp_snr` 37 k | **0.13689** | 0.10660–0.16868 | 0.2110 |
| terrain-matched control (8 relief × 4 slope classes) | 0.12407 | — | 0.1939 |
| mass-matched random | 0.06373 | — | 0.0976 |
| distance-only control (farthest cells) | 0.00353 | — | 0.0054 |
| owner-reported champion `h33-2-b2` | 0.09539 | — | 0.1465 |
| lane 160 k dots | 0.23246 | — | 0.1627 |

Paired block-bootstrap differences **candidate − arm**:

| arm | Δ | SE | verdict |
|---|---|---|---|
| champion `h33-2-b2` | **+0.04150** | 0.01716 | clears 2 SE |
| terrain-matched control | +0.01282 | 0.00722 | **does not clear 2 SE** |
| random mass-matched | +0.07316 | 0.01248 | clears 2 SE |
| lane 160 k | −0.09557 | 0.00776 | larger-mass arm wins |

Two things kill the discovery claim on this instrument.

1. **The gain is concentrated at the range front.** 117 of 323 blocks (36 %) are
   classified range-front (they contain catalogue cells in the top relief decile)
   and hold 74 % of the instrument truth. Inside the 206 interior blocks the
   ordering inverts: champion 0.08767, candidate 0.01433 — a paired difference of
   **−0.07333 (SE 0.01060)**, i.e. the champion beats the candidate by roughly
   3.5 SE where range-front incision cannot earn the credit. Instrument 1 also
   rewards mass monotonically (0.23246 at 160 k dots), which is the signature of a
   terrain-class proxy rather than of a fault detector.
2. **A stricter truth changes nothing.** Using only truth cells more than 800 m
   from the mapped catalogue (51 742 px), the pooled numbers barely move
   (candidate 0.13635, champion 0.08481) and the interior ordering is identical
   (champion 0.08140, candidate 0.01541, terrain-matched control 0.02135).

The internal control comparisons are equally informative: a *fixed sibling
artifact* (the champion), which no arm of this run can influence, beats the
candidate inside the interior stratum; and the terrain-matched control is
statistically indistinguishable from the candidate. On this instrument the lane
surface is, at best, a range-front relief detector.

## Instrument 2 — `HOLDOUT-DTI (catalogue_hide)`

Whole-component hide-and-recover with per-fold placement rebuilt from the visible
catalogue only, 60 988 withheld positive pixels, 161 physical clusters.

| arm | DTI | 95 % CI |
|---|---|---|
| mass-matched random | 0.07548 | 0.06885–0.08142 |
| terrain-matched control | 0.06299 | 0.05355–0.07230 |
| lane candidate | 0.06183 | 0.04957–0.07344 |
| owner-reported champion | 0.00670 | 0.00597–0.00745 |

Paired against the candidate: random −0.01366 (SE 0.00615, not 2 SE),
terrain-matched −0.00116 (SE 0.00349), champion +0.05513 (SE 0.00601, clears
2 SE). **This instrument cannot promote the candidate.** It is a no-harm check and
a faint-scarp sensitivity check: the candidate is statistically tied with both
controls, which is the honest reading of "no measurable harm, no measurable
edge". The **published artifact as-is** scores 0.00000 on all four folds by
construction, because its dots sit ≥ 3 px from the entire catalogue and this
instrument's truth *is* catalogue geometry; that row is a structural diagnostic
(what the file targets is off-catalogue faulting), not a harm measurement. The champion's 0.00670 is *structurally* poor because the champion was
built to avoid the mapped catalogue, and this instrument scores exactly that
catalogue; the number is reported, never used as a comparative claim.

## Registry comparison — `REGISTRY-MEASUREMENT`

62 single-band rasters on the pinned grid were decoded and compared (bytes,
decoded pixels, rank correlation, dot overlap, dot-set Jaccard).

* `byte_unique` **true**, `pixel_unique` **true** — no prior raster shares the
  candidate's bytes or its decoded positive support.
* Two comparators saturate the footprint: `calib_r13lattice_00904.tif` and
  `r13_lattice_s5_00904.tif` (206 895 dots each) place a 3 px neighbourhood over
  **99.87 %** of the footprint, so *every* nonempty candidate exceeds the literal
  "≤ 70 % within 3 px" clause against them (IR-H71-UNIQ-01).
* With comparators of near-total halo coverage set aside, the discriminating
  reading still fails: **88.8 %** of the candidate's dots lie within 3 px of
  `gems32-bayesopt-dilation-scarp-d28-20261004-*` (45 000 dots) and **95.3 %**
  within 3 px of `r11_greedy_mp.tif` (272 853 dots), with only 6.1 % / 0.9 %
  exact-dot Jaccard. The lane's top cells are the same physical scarp cells that
  earlier submissions already mined; the candidate is a fresh dot set on a
  heavily used surface. Verdict: `negative` (logged as a near-duplicate, not
  exempted).

## Why the owner-reported champion scores highest

This run's measurements add to the sibling reconstruction (its support is
reproduced by pruning, 2 545 deletions and zero additions):

* On the honest-like population the champion is **not** a strong fault detector:
  `PROXY-INSTRUMENT (sgmc_off)` 0.09539 at 37 654 dots versus 0.13689 for the
  lane candidate; `HOLDOUT-DTI (catalogue_hide)` 0.00670.
* Where it *is* strong is the interior stratum of the state-map population
  (0.08767 with the same dot budget, 6× the candidate) and the 800 m strict
  truth (0.08140). Its geometry therefore earns credit in low-relief,
  interior terrain — exactly the population where a lidar-visible alluvial scarp
  detector *should* earn it and where this run's surface does not.
* The plausible explanation, consistent with every measurement here, is that the
  champion's advantage comes from **placement across a broad, interior, non-halo
  field** rather than from a stronger per-pixel detector: it is spread out
  (median 1.97 km from the mapped network in the sibling reconstruction, maximum
  21.9 km), it is not confined to range fronts, and it is not a duplicate of the
  scarp-feature submissions that saturate the registry's overlap clauses.
* **Is a higher-scoring submission achievable?** The evidence here says yes in
  principle and not from this lane: the field must earn credit in the interior
  stratum, must beat a terrain-matched control there by more than 2 SE, and must
  not be a near-duplicate of the scarp-feature family. No arm of this run does
  the first two, so no promotion is offered. The published candidate is a
  format-valid, hash-verifiable, byte-unique artifact with a measured pooled edge
  over the champion on one proxy instrument — and a measured 3.5 SE deficit in
  the stratum that decides the verdict.

## Artefacts

| artifact | value |
|---|---|
| candidate TIFF | `docs/downloads/gems64-lane-ampsnr-37654-20261011.tif` |
| sha256 | `534eea95cfc4798e…` (full hash in the run card and the adjacent receipt) |
| validator | float32, EPSG:32611, 100 m, 3730 × 3292, values 0.0–1.0, template report ok |
| submission name / note | 36 / 135 characters (limit 140) |
| weekly slots used | 0 |
| instrument 1 | `evidence/e1_sgmc_off.json` |
| instrument 2 | `evidence/e2_catalogue_hide.json` |
| registry | `evidence/e3_emission.json`, `evidence/registry_index.json` |
| run card | `evidence/run_card.json` (schema `gems64-run-card-v2`) |

## Next session, in order

1. Build the **interior-first** field the evidence points at: rank cells whose
   geometry is inconsistent with range-front relief (low-relief, interior
   blocks, high vergence asymmetry and cross-strike consistency) and evaluate it
   on the interior stratum of both instruments before anything else.
2. Freeze that field and budget in `PREREGISTRATION.md` **before** reading any
   instrument, then run the pooled and interior comparisons once.
3. Add the missing control arms: mass-matched random *inside* the interior
   stratum and a sparse-spread control with the champion's shape (median ~2 km
   from the network).
4. Re-run the registry comparison with the two saturated lattice comparators
   marked non-discriminating in the same receipt, and record exact-dot Jaccard
   alongside the 3 px overlap so the duplicate reading cannot be misread.
5. Do not spend a slot until the interior comparison clears 2 SE against the
   terrain-matched control *and* against the sparse-spread control.
