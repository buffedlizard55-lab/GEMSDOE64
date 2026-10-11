# Shared-template changes in GEMSDOE64

Original import: 60GEMSDOE commit `6444fa6552335190f0bc89661acf725ed73e7fcb`.
Per-file original hashes: `evidence/template_import.json`. These are corrections
in the **single shared copy** used here, not alternate/private implementations.
They have not been pushed to a sibling repository from this branch-fixed session.

1. `evaluate_holdout.py`: v3-se adds the paired block-bootstrap standard error
   and strict `delta > 2*SE` result. A positive percentile interval is not the
   same stated rule. Existing aligned physical-block pooling is retained.
2. `holdout.py`: adds `blocked_component_folds`, withholding whole 8-connected
   components, excluding cross-boundary components from touched training folds,
   and buffering both spatial training boundaries and hidden catalogue context.
   The legacy 12-pixel-chunk instrument is retained for provenance but **not used
   or certified for this lane**. New caller uses the strict entry point.
3. `metric.py`: corrects prose that incorrectly bounded marginal truth credit
   by a dot's single nearest-truth credit. One dot can cover multiple truths.
   No metric formula was changed. Binary/soft arithmetic is tested against the
   independent literal brute-force implementation.
4. `uniqueness.py`: removes a late-added density-classified “like-for-like”
   alternative to prevent unauthorized exemptions. The literal shared policy
   and its universal saturation-certificate helper remain the only policy.
5. `validate.py`: requires nonempty positive support, an absent nodata tag under
   the conservative all-finite policy, and no internal mask hiding footprint
   pixels. Serializes nonfinite metadata tags as strings for strict JSON output.
   Writer input stays normalized and all-finite; zero outside complies with
   “NaN only outside” without requiring NaNs anywhere.

The TIFF writer itself remains the shared imported implementation. Its on-disk
checks now call the corrected validator. Local format validity is not evidence
of organizer upload acceptance. Synthetic serialization fixtures are confined
to pytest temporary directories and never published.

Pass 2 added these shared safeguards after review:
- Pooled terms must satisfy `TP + FN == truth_count` per block before bootstrap.
- A same-basename TIFF in a different registry directory is no longer exempted
  from discovery; only the exact candidate path is excluded.
- Registry comparisons require a SHA-256 pin, reject invalid interior values,
  and validate the candidate file's actual CRS/affine before pixel comparison.
- Lane policy requires an actual finite holdout point estimate, not just a CI;
  null/missing holdout evidence fails closed. An empty feature set cannot pass a
  leakage-canary helper by doing no checks.
