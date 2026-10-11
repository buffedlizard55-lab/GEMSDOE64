# Ranked hypotheses (GEMSDOE64 lane)

Written before the run, ranked by *expected DTI gain against implementation cost*.
Each entry names the layers, the physical signature and transform, why the target
fault is missing from the published USGS/INGENIOUS catalogue rather than already
in it, and how it differs from everything already implemented in this lane or in
the sibling repositories.

**Ranking key.** Sibling measurements (owner-reported, see `evidence/claim_ledger.json`
C6) put the current family top at 0.2778 and the metric closure at
`DTI = a / (0.8 + 0.2·N/|G|)`. A hypothesis therefore helps only if it either
(a) increases credited mass `a`, or (b) removes dots without losing credit.

---

## H1 — Strike-line consistency veto on lidar scarp channels *(implemented, measured here)*

* **Layers.** `lidar_scarp_features_u8.tif` (12 channels: `ex_max/ex_mean`,
  `step_max`, `lapneg_max/lappos_max`, `downface_max/upface_max`, `cross_max`,
  `relief`, `coh100`, `strike`, `valid`) and the 100 m stack's `det_elev`.
* **Signature / transform.** Slope-detrended step templates (12 orientations),
  Steger sub-pixel ridge/valley, Frangi multiscale vesselness; then the lane's
  **strike-line consistency** statistic: for each cell, the strike-deviation
  weighted fraction of aligned neighbours that carry evidence. Used as a
  keep-fraction veto on packed dots rather than as another additive channel.
* **Why the target fault is missing from the catalogue.** The published
  catalogue is a Quaternary-scope compilation; faults whose expression is a
  degraded scarp in the micro-topography (or a lithology-bounded step) can be
  invisible in the 100 m potential-field stack but still be a mapped-fault
  candidate. The veto is not about *finding* more scarps — the channels already
  contain them — it is about keeping only the ones whose evidence is line-like.
* **Novelty vs siblings.** The sibling repositories aggregate lidar channels
  per-cell with max/logistic fusion and thin by *distance* (d1.5/d2.8 Poisson).
  No indexed prior uses a strike-line continuity criterion to select which dots
  survive; the emitted file has no twin in the checked registry.
* **Cost.** Zero extra data; runs inside the existing lane in minutes.
* **Expected gain.** Modest positive if the line statistic separates real trace
  from blob noise, zero if not — the honest outcome is whatever the instrument
  says (see the arms table in `evidence/run_card.json`).

## H2 — Expected-DTI gain pruning with cross-fitted probabilities *(implemented, refuted here)*

* **Layers.** Any surface plus a per-cell truth probability.
* **Signature / transform.** Exact single-removal test of the plug-in expected
  DTI `T/(0.2(T+FP)+0.8K)` with `T = Σ π·credit`, `K = Σ π`.
* **Why it should work.** The measurable loss mode is redundant flank mass; the
  exact test targets it case by case instead of with a global spacing constant.
* **Novelty.** The sibling arm `h32d-submodular-multipysics` used a different
  budget rule; an expected-credit removal test with cross-fitted π is not
  indexed.
* **Result in this lane: refuted.** With π fitted on the hide-and-recover
  instrument's own labels, the arm removed almost every dot and scored 0.00000
  on the surrogate. Cause: the calibrated π ranks the scarp evidence as
  low-probability because the surrogate truth is *catalogue* pixels, not the
  physical scarps the lane detects. Kept as a documented negative — it is
  evidence about the instrument, not about the geology.

## H3 — Cross-sensor corroboration veto *(available, not separately scored)*

* **Layers.** lidar scarp channels + `det_elev` structure + radiometric texture.
* **Signature / transform.** A cell must be supported by at least two
  independent evidence families (streaming second-best over ten normalised
  channels) before a dot may sit there.
* **Why it could add faults.** Cultural and erosional false positives rarely
  appear in several independent measurements at once, so corroboration raises
  the credited share of the same dot budget.
* **Novelty.** Indexed priors fuse channels additively; a veto-style fusion is
  absent (the closest sibling idea, anomaly "coincidence" maps, is an additive
  score).
* **Cost.** Low — the channels are already loaded. Deferred because H1's veto
  and H3's veto act on the same dot budget and the run budget is three
  experiments.

## H4 — Curvature-polarity asymmetry (footwall / hanging-wall) *(not runnable in this sandbox)*

* **Layers.** A 1 m DEM would be required (`1m_DEM_links.csv` tile list; USGS
  3DEP). The 10 m fallback exists (`dem10_chi_100m_*`) but is too coarse for a
  metre-scale asymmetry test.
* **Signature / transform.** Sign-consistent cross-fault curvature over
  hundreds of metres, with dip direction inferred from the asymmetry; blind
  faults tilt the hanging wall instead of cutting a discrete scarp.
* **Why the target fault is missing.** A buried or blind fault has no surface
  trace for a scarp template to find; the catalogue requires a mapped trace.
* **Data check.** 3DEP tiles are free and official, but
  `prd-tnm.s3.amazonaws.com`, `index.nationalmap.gov` and
  `portal.opentopography.org` are unreachable from this sandbox
  (`evidence/access_blockers.json`). Not obtainable here — recorded, not faked.
* **Cost.** High (needs an unrestricted runner and tile management).

## H5 — Slip/length screening against the Qfaults attribute table *(data present, not yet tested)*

* **Layers.** `gdr_qfaults_traces.csv` and `qfault_attributes.csv` (mirrored,
  5.8 MB) plus any candidate surface.
* **Signature / transform.** Faults whose mapped length and slip rate imply
  continuations the compilation truncates; attribute-conditioned continuation
  rather than purely geometric gap closing.
* **Why the target fault is missing.** Compilation truncation and segmentation
  are documented mechanisms for a fault being absent from a catalogue even
  though it is in the landscape.
* **Novelty.** The sibling T-v2 gap-closure experiment was purely geometric and
  was refuted on the live metric (it bought +2.65 px of credit for 1,259 dots).
  Conditioning the *decision* on slip/length attributes with an expected-DTI
  acceptance test has not been scored anywhere in the family.
* **Cost.** Medium — attribute joins plus the existing emission path.

---

### Why these and not others

The sibling corpus already falsified: bare geometric gap closure (T-v2),
tip/Euler de-jitter additions (H33-1/H33-5 arms), submodular multi-physics
budgeting (H32-D, co-kriging 0.2716 ± 0.0069), and dense-additive fusion. The
five hypotheses above are the ones that change *which pixels earn credit* rather
than how many dots are spent, which is what the closure formula says is left.
