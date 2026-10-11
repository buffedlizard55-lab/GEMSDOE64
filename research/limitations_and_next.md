# Limitations and next steps — run 64 (lidar-scarp lane)

**Current decision: NEGATIVE — one candidate TIFF published, not cleared for a slot.**
Reviewed 2026-10-11. The canonical machine-readable status is
[`../evidence/run_card.json`](../evidence/run_card.json); the frozen decision rule for the next
run is [`../PREREGISTRATION.md`](../PREREGISTRATION.md). A missing value is `null`, never 0 or an
implied pass.

## What was actually run

| experiment | what it measured | receipt |
|---|---|---|
| E1 | `PROXY-INSTRUMENT (sgmc_off)`: 13-surface ablation at 24 000 dots, size sweep 24 k–160 k, terrain-matched and random controls, distance-only control, owner-reported champion, interior/range-front strata, ≥ 800 m strict-truth variant | `evidence/e1_sgmc_off.json` |
| E2 | `HOLDOUT-DTI (catalogue_hide)`: whole-component hide-and-recover, 4 label-blind quadrant folds, per-fold placement rebuilt from the visible catalogue, plus the published artifact scored as-is | `evidence/e2_catalogue_hide.json` |
| E3 | emission through the shared writer + validator + template gate, 62-comparator registry comparison (bytes, pixels, rank, dot overlap, Jaccard) | `evidence/e3_emission.json`, `evidence/registry_index.json` |

Three experiments is the whole budget for this run; no further experiment was run after the gates
were read.

## Decisive gate failures

1. **Interior-stratum inversion.** Inside the 206 interior 20 km blocks the owner-reported champion
   scores 0.08767 against the candidate's 0.01433 (paired delta −0.07333, SE 0.01060) on
   `PROXY-INSTRUMENT (sgmc_off)`; with the ≥ 800 m strict truth it is 0.08140 vs 0.01541. The
   candidate's pooled advantage over the champion (+0.04150, SE 0.01716) is therefore
   range-front-relief credit, not fault discovery.
2. **Terrain-matched control not beaten.** 0.12407 vs 0.13689 pooled (+0.01282, SE 0.00722, under
   2 SE) and the control is ahead inside the interior stratum.
3. **Dot-pattern uniqueness.** Bytes and decoded pixels are unique, but 88.8 % of the candidate's
   dots sit within 3 px of `gems32-bayesopt-dilation-scarp-d28-*` and 95.3 % within 3 px of
   `r11_greedy_mp.tif`; two comparators additionally saturate the footprint (99.87 % halo coverage),
   making the literal clause unsatisfiable. Logged as a near-duplicate; not exempted.

## Honest limits of the measurements

* The hidden panel is not observable here. `PROXY-INSTRUMENT (sgmc_off)` is a different fault
  population (state-geological-map compilation) and demonstrably favours rock-exposed, range-front
  terrain; `HOLDOUT-DTI (catalogue_hide)` scores catalogue geometry only, which structurally
  penalises any candidate placed away from the catalogue (the published artifact returns 0.00000 on
  it *by construction*). Neither instrument can rank a submission against the leaderboard.
* The surface (`amp_snr`) and the 37 654-dot budget were chosen after reading instrument 1, so that
  instrument's numbers are selection-exposed. Only instrument 2 and the control families are
  independent of that choice — and they do not show an edge.
* `amp_snr`, `amp_mean`, `base`, `step` are statistically beside one another in the ablation; the
  choice between them is not resolved by this run.
* The cultural mask covers TIGER roads and BLM closed claims only. Canals and field edges are **not**
  masked; the lane's own text asks for them, and no local layer exists for them.
* Instrument 1 truth is 62 122 px (≥ 300 m from the catalogue); the sibling's model-estimated hidden
  mass is ~12 226 px, so instrument 1's coverage behaviour does not transfer to the hidden panel.
* `orienteering`-style artefacts from sibling repositories were used as *comparator arms* and as
  registry comparators. They are not organizer data and their owner-reported scores are not
  receipts.

## Environment and access limits

* Official DrivenData competition rasters are not in this checkout; `data/inputs/` holds 14 inputs
  assembled through public GitHub bridges, each hashed in `evidence/input_assembly.json`. Those
  hashes do not authenticate organizer origin.
* `raw.githubusercontent.com`, `prd-tnm.s3.amazonaws.com` and `gdr.openei.org` were unreachable from
  this runtime; the fetch pattern that works is `codeload` tarballs or the GitHub contents API.
* No DrivenData login, weekly-cap observation or submission was performed. No credentials exist in
  this repository.

## Next session — in order

1. Build the **interior-first** field: cells whose geometry is inconsistent with range-front relief
   (interior blocks, low relief, high vergence asymmetry, cross-strike consistency), and evaluate it
   on the interior stratum of both instruments before anything else.
2. Freeze that field and its dot budget in `PREREGISTRATION.md` **before** reading any instrument,
   then run the pooled and interior comparisons once.
3. Add the two missing controls: mass-matched random *inside* the interior stratum and a
   sparse-spread control with the owner-reported champion's shape (median ≈ 2 km from the network).
4. Re-run the registry comparison with the two saturated lattice comparators marked
   non-discriminating in the same receipt, and print exact-dot Jaccard beside the 3 px overlap.
5. Spend a slot only after the interior comparison clears 2 SE against the terrain-matched *and*
   sparse-spread controls, then archive the submission-page receipt as
   `evidence/organizer_receipt.json`.
