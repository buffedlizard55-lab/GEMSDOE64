# Limitations and remaining work

Written at the end of the session that produced the current run card. Every item
is a real gap, not a hedge.

## Limitations of what was produced

1. **No organizer-issued truth exists in this environment.** Every performance
   number is either a surrogate hide-and-recover measurement (`HOLDOUT-DTI`, with
   evaluator version, withheld positives and 95 % CI), a mirror measurement
   (`MEASURED`), a public-leaderboard row, or an owner-reported claim. There is no
   `ORGANIZER-CONFIRMED` score anywhere in the repository.
2. **The literal uniqueness gate is unsatisfiable, not passed.** Five checked
   priors (two lattice builds, `r11_greedy_mp`, `r14_union_tips10_lat6`, and a
   whole-footprint probability surface) have matched random controls that already
   exceed the 70 % forward-overlap limit, so the criterion cannot separate a copy
   from an original for them. The literal verdict is therefore **fail**; the
   diagnostic verdict over the 58 priors where the criterion is measurable is
   **unique** (worst forward overlap 0.633, worst |ρ| 0.044, byte and pixel
   unique). Both numbers are published side by side; no exemption was taken.
3. **The registry is not the organizer's registry.** 63 hash-pinned priors were
   scanned. The sibling project's own 2026-10-11 review reports 651 of 655
   accessible rasters checked, with the same 1.0-overlap blocker. Files that are
   private, unlinked or written after this session are invisible here.
4. **The 1 m lidar path was not executed.** It is implemented and unit-tested,
   but USGS tile hosts are unreachable from this sandbox
   (`evidence/access_blockers.json`). The shipped candidate uses the finest
   reachable lidar-derived grid, and the run card's `scale_audit` says so.
5. **The instrument is a domain detector, not a ranker.** A random dot set drawn
   from the same emission domain scores 0.0375 against 0.0504 for the winner on
   the same folds. The paired margin over that control is real (+0.0129, > 2 SE)
   but the absolute level shows how much of the surrogate signal comes from
   *where the dots are allowed to be* rather than from *which* dots are kept.
   Fine-ranking claims are accordingly weak.
6. **One truth family.** The hide-and-recover truth is catalogue-derived; no
   independent truth (field mapping, relocated seismicity) was integrated, so a
   candidate that is good at predicting the catalogue is rewarded.
7. **Budget.** The parallel-run protocol allows three experiments or two hours.
   This session ran one lane experiment (the arms table), reused the shared
   tools, and used zero submission slots. The three-arm budget also explains why
   H3 (cross-sensor corroboration) was implemented inside the arm set but not
   studied as its own experiment.

## Remaining work, in priority order

1. **Obtain organizer-authenticated data.** The competition data page is
   login-walled; nothing here is authenticated competition data. Any real
   submission decision should re-run the lane against the official bytes.
2. **Settle the dense-prior protocol question with the owner.** Options: (a)
   exclude non-emission surfaces from the dot-overlap rule in the shared protocol
   (with the matched-control certificate as the evidence), or (b) keep the
   literal rule and accept that no candidate can ever clear while saturating
   priors are indexed. This repository implements the certificate and keeps the
   literal gate; it does not choose for the owner.
3. **Push the spacing finding through the family's instruments.** The winner here
   is 3.4 px packing + 2 px catalogue-flank pruning on the *same* surface as the
   sibling's 2.8 px family best. Since the sibling measured 1.5 → 2.8 as a large
   gain, 3.4 (and 4.0) deserve a proper spacing sweep on their live-mirror
   instruments before anyone spends a slot.
4. **Test H5 (Qfaults slip/length screening)** with the same instrument; the
   attribute table is already mirrored.
5. **Try H4 when a 1 m DEM is reachable**, and compare native versus aggregated
   processing — that comparison is the lane's actual claim and it is untested.
6. **Replace the surrogate instrument with a real detector benchmark**: train the
   official reference U-Net on the 19-band stack, then ask whether the lane's
   dots add anything on top of its probability surface.
