# Run 64b — the `amp_snr` lane evidence set (second, independent of the published card)

This page records a **second evidence set** for the same competition lane, produced by a parallel
session on 2026-10-11 and merged here unmodified. It does not replace or re-score anything on the
published card: the site's published candidate and its run card remain the strikeline artifact and
`evidence/run_card.json`. Everything below is either `PROXY-INSTRUMENT (sgmc_off)`,
`HOLDOUT-DTI (catalogue_hide)` or `REGISTRY-MEASUREMENT`, and there is still **no
`ORGANIZER-CONFIRMED`** number anywhere in the repository.

## What was built

A catalogue-independent surface: the lane never uses distance-to-catalogue for ranking. Twelve
quantised 2 m lidar scarp channels and seven quantised 3 m scarp channels are decoded from their
published manifests, reduced to named 100 m components (amplitude, SNR-weighted amplitude, step,
crest/base curvature, vergence asymmetry, cross-strike consistency, coherence, relief, 3 m
replication, coverage), percentile-ranked inside the eligible domain and thinned with a greedy
1.5 px blue-noise selection. Code: `src/gems64/lane.py`, `src/gems64/instrument.py`,
`src/gems64/registry_policy.py`, `scripts/run_lane.py`. Receipts:
`evidence/e1_sgmc_off.json`, `evidence/e2_catalogue_hide.json`, `evidence/e3_emission.json`.

## Surface ablation (instrument 1, 24 000 dots per surface)

| surface | DTI | credit/dot |
|---|---|---|
| `amp_snr` = √(2 m excess max × mean) | **0.10352** | 0.2377 |
| `amp_mean` | 0.10291 | 0.2363 |
| `base` | 0.10263 | 0.2356 |
| `step` | 0.10252 | 0.2354 |
| `cross` | 0.10029 | 0.2301 |
| `amp_max` | 0.09982 | 0.2290 |
| `crest` | 0.09455 | 0.2168 |
| `relief` | 0.08366 | 0.1915 |
| `frac` | 0.07607 | 0.1743 |
| `vergence` | 0.05092 | 0.1163 |
| `coh` | 0.03217 | 0.0733 |
| `replicate3m` (3 m chain gate) | 0.02390 | 0.0544 |
| declared composite 0.45 amp / 0.30 coh / 0.25 rep | **0.02372** | 0.0540 |

The pre-declared composite is the **worst arm measured**; coherence and the 3 m replication gate
carry almost nothing on this instrument, and the gate anti-correlates with the state-map population
(canary AUC 0.343). `amp_snr` was adopted and the selection is disclosed in every receipt.

## Instrument 1 — `PROXY-INSTRUMENT (sgmc_off)`

2 967 065 eligible cells, 62 122 truth pixels (≥ 300 m from the mapped catalogue), 4 label-blind
quadrant folds, 200 px block bootstrap, 1 000 draws. The owner-reported champion raster is
re-measured as a comparator arm, never as a score.

| arm (37 654 dots) | DTI | 95 % CI | credit/dot |
|---|---|---|---|
| `amp_snr` candidate | **0.13689** | 0.10660–0.16868 | 0.2110 |
| terrain-matched control (8 relief × 4 slope) | 0.12407 | — | 0.1939 |
| mass-matched random | 0.06373 | — | 0.0976 |
| owner-reported champion `h33-2-b2` | 0.09539 | — | 0.1465 |
| `amp_snr`, 160 000 dots | 0.23246 | — | 0.1627 |

Paired differences (candidate − arm): champion **+0.04150 (SE 0.01716)**, terrain-matched control
**+0.01282 (SE 0.00722)** — under two standard errors.

**The stratum decides it.** Inside the 206 interior blocks (those without a catalogue cell in the top
relief decile) the ordering inverts: champion **0.08767** vs candidate **0.01433**, paired
**−0.07333 (SE 0.01060)**. With a stricter truth (≥ 800 m, 51 742 px) it is 0.08140 vs 0.01541. The
pooled advantage is range-front relief credit, not fault discovery — the same mimic this repository
tracks everywhere else.

## Instrument 2 — `HOLDOUT-DTI (catalogue_hide)`

60 988 withheld positives, 161 clusters, per-fold placement rebuilt from the visible catalogue:
random 0.07548 (0.06885–0.08142), terrain-matched 0.06299, candidate 0.06183 (0.04957–0.07344),
champion 0.00670. Paired against the candidate: random −0.01366, terrain-matched −0.00116. No harm,
no edge. The published artifact scored **as-is** returns 0.00000 on all four folds *by construction*
(its dots are ≥ 3 px from the entire catalogue while this instrument's truth is catalogue geometry) —
a structural diagnostic, not a harm measurement.

## Registry — `REGISTRY-MEASUREMENT`

62 comparators; `byte_unique` and `pixel_unique` both true. Two comparators
(`calib_r13lattice_00904.tif`, `r13_lattice_s5_00904.tif`) put a 3 px halo over **99.87 %** of the
footprint, so the literal "≤ 70 % within 3 px" clause cannot be satisfied by any nonempty candidate;
on the discriminating reading 88.8 % of this candidate's dots still sit within 3 px of
`gems32-bayesopt-dilation-scarp-d28-*` and 95.3 % within 3 px of `r11_greedy_mp.tif`. Logged as a
**near-duplicate pattern** — the family has already mined this surface — which is one more reason the
published card's candidate is a different construction.

## The artifact that came out of this set

`artifacts/gems64-lane-ampsnr-37654-20261011.tif`, sha256
`534eea95cfc4798e035698e447050b709cf63bbd7ea52c79cb6fae523b599b38`, 132 751 bytes, float32,
EPSG:32611, 100 m, 3730 × 3292, values 0.0–1.0, 18/18 local checks including
`range_0_1_guaranteed` and `zero_dots_on_mapped_catalogue`, with its single-TIFF ZIP and its writer
receipt alongside. It is kept **outside `docs/`** so that the deployed site keeps exactly one
published candidate (the card's) and the publication guard stays meaningful; the file is an audit
artifact with a measured negative verdict, not a promotion.

## Frozen gates for the next run

[`PREREGISTRATION.md`](../../PREREGISTRATION.md) freezes the decision rule: beat the terrain-matched
control by more than two paired block-bootstrap SEs **inside the interior stratum**, stay within noise
of the controls on the catalogue-recovery instrument, clear the byte/pixel uniqueness check, and keep
the leakage canary below AUC 0.90. The next field must earn its credit in the interior; nothing in
this set does.
