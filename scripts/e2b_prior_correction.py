"""E2b: the same rule comparison after correcting the calibration prior.

E2 (``evidence/e2_holdout.json``) came back NEGATIVE for this lane: at matched
mass the DTI-optimal selector scored far below the incumbent 2.8-px spacing.
The diagnosis is in the run card: the isotonic surface was fitted on a
*sub-sampled* negative pool (``E2_NEG`` background pixels out of ~5.1 M), so
every calibrated probability is inflated by the sampling odds.  The selector
then believes the truth mass ``K = sum_g w_g`` is an order of magnitude larger
than it is, over-emits low-credit dots, and its mean-field DTI (0.33) is
nowhere near the realised 0.05.

For negative sub-sampling at rate ``r`` the odds correction is exact:

    odds_true = r * odds_sampled
    w         = r*p / (r*p + 1 - p)

which is strictly increasing in ``p``, so it re-uses the cached out-of-fold
surfaces without refitting anything.

Writes ``evidence/e2b_holdout.json``.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import numpy as np
from scipy import ndimage as ndi

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from e2_holdout import (block_bootstrap_diff, block_components, candidates_for,  # noqa: E402
                        pooled, rule_masks)
from gems64 import grid as gridmod, holdout as H  # noqa: E402
from gems64.select import ExpectedDtiGreedy  # noqa: E402

MAX_DOTS = int(os.environ.get("E2_DOTS", 60_000))
MAX_CAND = int(os.environ.get("E2_CAND", 100_000))


def prior_correct(p: np.ndarray, r: float) -> np.ndarray:
    """Exact odds correction for negative sub-sampling at rate ``r``."""
    p = np.clip(np.asarray(p, np.float64), 0.0, 1.0 - 1e-12)
    return (r * p / (r * p + 1.0 - p)).astype(np.float32)


def main() -> int:
    t0 = time.time()
    g = gridmod.load_grid()
    folds, quad = H.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    z = np.load(ROOT / "evidence" / "e2_surfaces.npz")
    n_bg = int((g.footprint & ~g.catalogue).sum())
    neg_kept = int(os.environ.get("E2_NEG", 150_000))
    r = neg_kept / n_bg
    print(f"negative sub-sampling rate r = {neg_kept}/{n_bg} = {r:.6f}")

    rng = np.random.default_rng(7)
    comps_acc, per_fold = {}, []
    for f in folds:
        p_raw = z[f"fold{f['fold']}"]
        p = prior_correct(p_raw, r)
        region, truth = f["region"], f["truth"]
        active = region & g.footprint & ~f["masked_known"]
        cand = candidates_for(p, region, active, cap=MAX_CAND)
        w = p.astype(np.float64) * (region & active)
        sel = ExpectedDtiGreedy(w, cand)
        res = sel.run(max_dots=MAX_DOTS, prune=True, prune_passes=3)
        mass = res["n_dots"]
        print(f"  fold{f['fold']}: sum_w={float(w.sum()):.0f} mass={mass} "
              f"mean-field DTI={res['expected_dti']:.4f}")
        masks = {"dtiopt": sel.mask()}
        masks.update(rule_masks(p, cand, mass))
        dcat = np.exp(-ndi.distance_transform_edt(~f["visible"]) / 3.0).astype(np.float32)
        c2 = cand[np.argsort(-dcat[cand[:, 0], cand[:, 1]], kind="stable")[:mass]]
        m = np.zeros(g.shape, bool); m[c2[:, 0], c2[:, 1]] = True
        masks["distance_only"] = m
        c3 = cand[rng.choice(cand.shape[0], size=mass, replace=False)]
        m = np.zeros(g.shape, bool); m[c3[:, 0], c3[:, 1]] = True
        masks["random"] = m
        comps = {k: block_components(v, truth, active) for k, v in masks.items()}
        row = dict(fold=f["fold"], mass=mass, sum_w=round(float(w.sum()), 1),
                   expected_dti=round(res["expected_dti"], 6),
                   mean_kappa=round(res["mean_kappa"], 4))
        for name, c in comps.items():
            row[name] = round(pooled(*c), 6)
            comps_acc.setdefault(name, []).append(c)
        per_fold.append(row)
        print("    " + " ".join(f"{k}={v:.4f}" for k, v in row.items() if k != "fold"))

    def stack_comps(name):
        return tuple(np.sum([c[i] for c in comps_acc[name]], axis=0) for i in range(3))

    pooled_dti = {k: pooled(*stack_comps(k)) for k in comps_acc}
    rbg = np.random.default_rng(99)
    boot = {k: block_bootstrap_diff(stack_comps(k), stack_comps("dtiopt"), 16, rbg, 300)
            for k in comps_acc if k != "dtiopt"}
    best = max((k for k in comps_acc if k != "dtiopt"), key=lambda k: pooled_dti[k])
    gate = boot[best]
    out = dict(
        experiment="E2b-holdout-rule-comparison-prior-corrected",
        evaluator_version="gems64-pooled-buffered-loqo-v1",
        split="buffered-whole-components-loqo-v2 (shared template)",
        fix="exact odds correction w = r*p/(r*p+1-p) for negative sub-sampling",
        negative_subsampling_rate=r, negatives_kept=neg_kept, background_pixels=n_bg,
        withheld_positive_pixels=int(sum((f["truth"] & f["region"]).sum() for f in folds)),
        pooled_dti={k: round(v, 6) for k, v in sorted(pooled_dti.items(), key=lambda kv: -kv[1])},
        paired_block_bootstrap_vs_dtiopt=boot,
        gate=dict(baseline=best, delta=round(gate["mean"], 6), se=round(gate["se"], 6),
                  z=round(gate["z"], 3), ci=[round(gate["ci"][0], 6), round(gate["ci"][1], 6)],
                  threshold="delta > 2*SE", passed=bool(gate["mean"] > 2 * gate["se"])),
        per_fold=per_fold, elapsed_s=round(time.time() - t0, 1),
    )
    (ROOT / "evidence" / "e2b_holdout.json").write_text(json.dumps(out, indent=2, default=float))
    print(json.dumps({k: out[k] for k in ("pooled_dti", "gate")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
