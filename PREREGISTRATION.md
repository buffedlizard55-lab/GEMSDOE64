# Pre-registration — GEMSDOE64 lidar-scarp lane (frozen 2026-10-11)

This file freezes the decision rule *before* any further promotion attempt, so that a
later session cannot move the goalposts. Everything here was written after the
exploratory E1/E2/E3 runs of 2026-10-11; those runs are therefore **selection-exposed**
and cannot be used as confirmatory evidence for the surface they selected. The frozen
rule applies to the *next* run and to the interpretation of the existing receipts.

## 1. Estimand

The competition metric is a distance-weighted Tversky index (DTI). Every local number in
this repository is an **instrument** value, never the hidden-panel score:

| label | meaning | required receipt fields |
|---|---|---|
| `HOLDOUT-DTI` | shared evaluator (`gems57.evaluate_holdout`), whole-component hide-and-recover, alpha 0.2 / beta 0.8, 300 m triangular kernel | evaluator version, withheld positive pixels, 95 % CI, implementation sha256 |
| `PROXY-INSTRUMENT (<name>)` | truth population other than the hidden panel (`sgmc_off`, `catalogue_hide`) | instrument name, truth definition, withheld positive pixels, 95 % CI |
| `REGISTRY-MEASUREMENT` | byte, pixel, rank or dot-overlap comparison against registry rasters | comparator list, radius, coverage of each comparator |
| `ORGANIZER-CONFIRMED` | copied from a submission-page receipt | receipt reference (none exists in this repository) |

A projection is never written as a score. Missing evidence is `null`, never 0.

## 2. Frozen promotion gates (all must pass)

1. **Population.** Candidate beats its 8-relief × 4-slope **terrain-matched control** by more
   than 2 paired block-bootstrap SEs (200 px = 20 km blocks, 1 000 draws).
2. **Stratum.** The same comparison holds inside the **interior** stratum (20 km blocks that
   contain no catalogue cell in the top decile of relief). A gain that lives only in
   range-front blocks is a terrain-class artifact and is logged as such.
3. **No-harm.** On `catalogue_hide`, the candidate is not worse than the mass-matched random
   control by more than 2 SE, and is not worse than the terrain-matched control at all.
4. **Uniqueness.** `byte_unique` and `pixel_unique` versus every reachable registry raster;
   the discriminating dot-overlap reading (`>70 %` of candidate dots within 3 px of a
   *non-saturated* comparator) is reported, and a violation is logged as a duplicate even
   though two comparators saturate the footprint (99.87 %) and make the literal clause
   unsatisfiable.
5. **Leakage canary.** No single feature may reach AUC > 0.90 against the instrument truth;
   if one does, the run stops until the leakage is explained.
6. **Format.** Single-band float32 GeoTIFF, EPSG:32611, 100 m, transform
   `(100, 0, 243350, 0, −100, 4508550)`, every footprint value finite in `[0,1]`, no NaN
   inside the footprint, zero positive mass on the mapped catalogue; shared writer +
   validator pass on the *serialized* file.

Failing any gate ⇒ verdict `negative`, the artifact is published only with the
**NOT CLEARED FOR SUBMISSION** banner, and the failed gates are named in the run card.

## 3. Frozen negative-result template

A negative result is a deliverable and must ship as a run card with these fields:

```json
{
  "schema": "gems64-run-card-v2",
  "hypothesis": "...", "mechanism": "...", "non_fault_mimic": "named mimic, measured how",
  "holdout": {"instrument_1": {"evidence_class": "PROXY-INSTRUMENT", "instrument": "sgmc_off",
                "dti": null, "ci95": null, "evaluator_version": "...",
                "withheld_positive_pixels": null, "paired_vs_control": null},
              "instrument_2": {"evidence_class": "HOLDOUT-DTI", "instrument": "catalogue_hide",
                "dti": null, "ci95": null, "withheld_positive_pixels": null},
              "gate_outcome": "..."},
  "correlation_overlap_vs_registry": {"byte_unique": null, "pixel_unique": null,
    "worst_dot_overlap": null, "duplicate_flags": [], "verdict": "negative"},
  "raster_sha256": null,
  "validator_output": null,
  "submission_name": "...", "note": "...",
  "submission_note_character_count": null,
  "promoted": false, "approved_for_weekly_slot": false, "submission_slots_used": 0,
  "verdict": "negative", "failed_gates": ["..."], "limitation": "..."
}
```

## 4. What the next (confirmatory) run must do differently

* Regenerate the surface and the dot set **from the frozen rule alone** — no advisory
  re-look at instrument 1 before the gates are computed, because the surface
  (`amp_snr`) and the size sweep were both chosen on that instrument.
* Add the missing comparator arm the exploration exposed: **mass-matched random inside the
  interior stratum** and a **sparse-spread control of the same budget** (the sibling
  champion's shape), so "concentration" and "spread" are compared directly rather than
  through a single pooled number.
* Pre-declare the dot budget in the run card *before* placement (a size sweep is
  exploratory once the instrument has been read).
* Re-run the registry comparison **after** deleting the two saturated lattice comparators
  from the discriminating set, and record both readings side by side.
* Carry the `min_px = 8.0` (800 m) strict-truth variant of instrument 1 as a mandatory
  second readout; the 3 px halo variant rewards tracing the mapped pattern.
