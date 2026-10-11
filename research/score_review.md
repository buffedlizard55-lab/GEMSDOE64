# Score and artifact provenance review

**Review date: 2026-10-11.** Canonical status: [`../evidence/run_card.json`](../evidence/run_card.json).
Read the [project brief](../README.md) and [`../PREREGISTRATION.md`](../PREREGISTRATION.md) first.

## Decision

There is **no `ORGANIZER-CONFIRMED` number anywhere in this repository**, and the owner-reported
0.2778 for `h33-h33-2-b2-…-zeros` is **not** a verified score for those bytes: no submission-page
receipt, submission identifier, account, phase or hash linkage exists here. It is quoted only as an
*owner-reported* figure, never as a baseline or an achievement.

What this run *did* do is measure the artifact itself, locally, on two labelled instruments — and
those measurements are the only numbers this repository produces:

| measurement | class | value |
|---|---|---|
| champion vs candidate, pooled | `PROXY-INSTRUMENT (sgmc_off)` | 0.09539 vs 0.13689 (Δ +0.04150, SE 0.01716) |
| champion vs candidate, interior stratum | `PROXY-INSTRUMENT (sgmc_off)` | 0.08767 vs 0.01433 (Δ −0.07333, SE 0.01060) |
| champion vs candidate, ≥ 800 m strict truth, interior | `PROXY-INSTRUMENT (sgmc_off)` | 0.08140 vs 0.01541 |
| champion vs candidate, catalogue recovery | `HOLDOUT-DTI (catalogue_hide)` | 0.00670 vs 0.06183 (protocol construction) |
| published artifact as-is on catalogue recovery | `HOLDOUT-DTI (catalogue_hide)` | 0.00000 on all four folds, by construction |
| owner-reported champion score | owner-reported, **not** receipt-verified | 0.2778 |
| leaderboard numerals cited by the user (e.g. 0.3774, 0.3195, 0.4133) | owner/user-cited snapshots, **not** re-verified here | not reproduced as results |

DrivenData's terms restrict leaderboard monitoring and copying; this review therefore records the
provenance of numbers rather than refreshing or mirroring any leaderboard.

## Why the champion artifact may lead, on the evidence available

The sibling reconstruction shows its support is reproduced by pruning (2 545 deletions, zero
additions), i.e. it is a placement rule, not a new detector. This run adds: it is beaten pooled by a
lidar-scarp surface at equal dot budget, it is nearly useless on the catalogue-recovery instrument
(it was built to avoid the catalogue), and it **wins by ≈ 3.5 SE inside the interior stratum** where
range-front terrain cannot earn credit. The consistent reading is that its advantage is a broad,
interior, non-halo field — and that any submission meant to beat it must earn credit there.

## What remains unverified

* Whether the organizer evaluated the exact named raster and returned 0.2778; receipt, submission ID,
  account, phase, final artifact hash.
* Whether any of the family's published rasters was ever submitted at all, and with which account.
* The current public leaderboard, the private-round score of any artifact, and the weekly cap.
* Whether the sibling artifacts were built from organizer data or from public GeoDAWN/lidar sources
  re-derived locally (this repository's lane uses the latter).

## Rules this review keeps

1. A projection is never written as a score; a missing value is `null`.
2. Numbers carry their instrument and class, with evaluator version, withheld-positive count and a
   95 % CI where the shared evaluator produced them.
3. No receipt, no promotion: `approved_for_weekly_slot` and `promoted` stay `false` until an
   organizer submission-page receipt exists in `evidence/organizer_receipt.json`.
