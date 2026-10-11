# Why `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` scored 0.2778 — and what beating it takes

Every number below carries its evidence class. Nothing here is a leaderboard
score unless the class says so; the file-by-file ledger is
[`evidence/claim_ledger.json`](../../evidence/claim_ledger.json).

## 1. The arithmetic of the metric

ORGANIZER-DOCUMENTED (competition problem description):
`DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)`, where the weight of a pixel pair is
`max(0, 1 − d/3)` with `d` in pixels (3 px = 300 m at the competition grid), and
`FN_w = |G| − TP_w` for the hidden truth set `G`.

Two consequences drive everything the family has measured:

* a **dot** placed on a fault trace earns up to three kernel-units of credit
  (it covers the trace for 3 px) while an off-target dot costs only `0.2`;
* therefore thinning a solid ridge into dots at ~2.8 px spacing keeps most of the
  credit and removes most of the mass. OWNER-REPORTED live scores follow exactly
  that pattern: solid ridge 0.1922 (121,131 px) → 1.5 px dots 0.2477 (60,069 px)
  → 2.8 px dots 0.2600 (44,090 px).

Written with `a = A/|G|` (credited fraction of hidden truth) and `N` emitted
dots, the sibling closure is `DTI = a / (0.8 + 0.2·N/|G|)`. At the sibling's
calibration (`a ≈ 0.386`, `|G| ≈ 12.2 k px`), **0.3195 needs `N ≈ 25 k`** — the
same credit in half the dots — or **+24 % credited mass** at the current count.

## 2. What h33-2-b2 actually is

OWNER-REPORTED / MEASURED (bytes): the file is
`docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`,
219,065 bytes, sha256 `c55bafc470054e82…`, float32 EPSG:32611 3730×3292, values
in {0,1}, 37,654 positive cells, none within 200 m of the published catalogue.

OWNER-REPORTED (rule): it is the group's 40,199-dot base emission
(`GEMS28-H27-4-R1-SOLO-D2.8`) minus every dot within 2 px of the catalogue. The
group's own accounting: 2,545 dots removed = 6.3 % of mass, at a cost of 58.6
units of off-catalogue weighted credit (1.5 %) against a budget of 125.1 →
safety factor 2.08; win in 4/4 spatial quads; **projected live 0.2747**.

OWNER-REPORTED / UNVERIFIED (score): the figure quoted for that file is 0.2778.
The sibling project's own 2026-10-11 status file classifies it as
`OWNER-REPORTED / UNVERIFIED`, notes the archived same-name claim of 0.2708, and
states that no organizer receipt links either number to those TIFF bytes. This
repository reproduces the claim with that label and draws no causal conclusion
from it.

## 3. Why the mechanism is nonetheless believable

Three independent, internally consistent measurements point the same way:

1. the spacing experiment (dots beat mass at equal credit) is monotone in the
   direction the metric implies;
2. the flank prune removes dots close to already-mapped faults, where new
   geography is least likely and the FP weight is paid in full;
3. the sibling's tip/Euler addition arms were **falsified** on their own
   instrument (+0.0026 and +0.0005 at 2/4 quads), which is what a *removal*-only
   rule passing while *addition* rules fail looks like when the dots are already
   in the right places.

## 4. Can it be beaten — and by what

* By post-processing the existing surface: the sibling analysis judges this
  unlikely at the level needed for 0.3195 (<10 % probability by their own
  closure), because the remaining error is *dotted_emission vs 1-D truth
  geometry*, not mass.
* By better dot **ranking**: that is the open problem. This lane attacks it with
  a strike-line consistency veto (H1) and cross-sensor corroboration (H3) and
  measures both on a three-draw pooled instrument.
* By a different detector: the reference solution is a U-Net with the same
  α/β asymmetry; a 2D seismic-style segmentation model (FaultSEG / siUNET
  family) trained on the official 19-band stack is the shape of the thing that
  would move the ceiling, and it is outside this lane's scope.

## 5. What this repository measured instead of assuming

See `evidence/run_card.json`:

* `holdout` — pooled hide-and-recover DTI with 95 % CI over withheld whole
  components (three independent draws), labelled HOLDOUT-DTI;
* `arms` — every arm on the same folds, including a random dot control drawn
  from the same emission domain and the historical base file as a comparison;
* `oof_selection` — arm selection cross-fitted over the folds, so the selection
  procedure itself is scored out-of-fold;
* `ensemble` — whether the winner beats every baseline in every truth draw.

The random control is the honest caveat: any dot set placed inside a
scar/structure-rich domain reaches a similar order of magnitude, so the
instrument is strong evidence about the **emission domain** and weak evidence
about **fine ranking**. It is reported that way, and no leaderboard number is
projected from it.
