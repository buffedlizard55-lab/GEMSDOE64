# Archived review log

The former multi-session review narrative was tied to earlier site drafts and source claims; it is not current verification. It has been retired here to prevent stale pass counts, tool-availability claims, and hypothesis lists from being mistaken for this checkout's status.

For the current three-pass review, use [`../evidence/review_passes.json`](../evidence/review_passes.json). Start a future session at [`../README.md`](../README.md), then inspect the canonical [`../evidence/run_card.json`](../evidence/run_card.json), [active findings](../docs/research/findings.md), and [current limitations](limitations_and_next.md).

## Run 64 (2026-10-11) — append

Three passes were executed in-session: (1) build the lane (decode, components, instruments, runner) and
run E1/E2/E3; (2) review and repair — subject-footprint cultural-mask statistic, `rank01` tie handling
(index-order ties had biased placement to the raster's last rows; ties now get the average rank), the
stale `~held_all` fold-eligibility design that made instrument 2 structurally unreachable, the
publication guard and its tests, and a fail-closed check that the published bytes match the receipt;
(3) re-check against the brief — every number labelled, negative result shipped, download labelled
not-cleared, submission guide and executive summary re-written from the receipts.

The former root-level site (`index.html`, `executive-summary.html`, `hypotheses.html`,
`methodology.html`, `sources.html`, `styles.css`, `research/run_card.json`) was retired in this run: it
was a pre-`docs/` draft that contradicted the measured verdict, and Pages deploys `docs/` only.
