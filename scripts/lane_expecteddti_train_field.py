#!/usr/bin/env python3
"""Experiment 3b (corrected) — physical-only field, leakage canary, blocked OOF, isotonic.

WHAT WAS WRONG AND WHY IT MATTERS
---------------------------------
The first version of this instrument added four catalogue-proximity features
(``cat_prox_e5/e15/inv3``, ``cat_density_s6``) computed from the published catalogue and then
trained the model to predict the published catalogue.  That is circular: the target *is* the
feature source.  It reported pooled blocked AUC 0.9963 and per-fold 0.9940-0.9985, and the
hide-and-recover arm returned DTI = 1.0000 in all four groups with the emission exactly
reproducing the withheld positives.  Both numbers are artefacts, not skill.

The circularity is not merely a statistical sin here, it is *directionally harmful* for this
competition.  Experiment 2 measured, from a live-scored controlled pair, that dots within 2 px
(200 m) of the published catalogue realise a mean credit of 0.0161 per dot against 0.1022 for
dots beyond it - a 6.3x depletion, robust across every plausible hidden-truth size K from 6,000
to 12,691.  The organizers mask catalogue pixels out of scoring (forum thread 11516), so a
surface that peaks next to the catalogue peaks exactly where the metric pays least.  A
catalogue-proximity model would therefore be worse than useless as an emission surface.

CORRECTED DESIGN
----------------
* Features: the 48 physical / geomorphic / potential-field layers derived from the 19 official
  bands only.  No catalogue-derived feature enters the emission model.
* The catalogue is used as a CONSTRAINT on the emission domain (masked out) and as the source of
  a live-calibrated distance DISCOUNT, never as a predictor.
* Leakage canary is run on the physical set AND on the catalogue set, so the leak is documented
  rather than hidden.  Threshold 0.90 per the run protocol.
* Blocked OOF: five spatially contiguous folds of 96 px super-blocks, 30 px buffer around every
  validation positive.  Pooled OOF -> isotonic regression -> calibrated probability.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems64.lane_expecteddti.gridext import HEIGHT, WIDTH, load_catalogue, load_footprint  # noqa: E402
from lane_expecteddti_train_and_calibrate import add_catalogue_features, blocked_folds, dist_to  # noqa: E402

PROC = ROOT / "data" / "processed"
SEED = 20261011
BUFFER_PX = 30
N_FOLDS = 5
CANARY_THRESHOLD = 0.90


def fit(X, y, seed=SEED, max_iter=300):
    from sklearn.ensemble import HistGradientBoostingClassifier

    m = HistGradientBoostingClassifier(
        loss="log_loss", max_iter=max_iter, learning_rate=0.07, max_leaf_nodes=31,
        min_samples_leaf=60, l2_regularization=1.0, max_features=0.7,
        early_stopping=False, random_state=seed,
    )
    m.fit(X, y)
    return m


def canary(X, y, names, folds, label) -> dict:
    """Single-feature blocked AUC.  AUC > 0.90 => leakage until proven otherwise."""
    from sklearn.metrics import roc_auc_score

    out = {}
    for j, nm in enumerate(names):
        a = []
        for k in range(folds.max() + 1):
            m = folds == k
            if y[m].sum() == 0 or (1 - y[m]).sum() == 0:
                continue
            a.append(roc_auc_score(y[m], X[m, j]))
        if not a:
            continue
        s = float(np.mean(a))
        out[nm] = dict(signed_auc=s, blocked_auc=max(s, 1 - s),
                       leakage_flag=bool(max(s, 1 - s) > CANARY_THRESHOLD))
    flagged = sorted(k for k, v in out.items() if v["leakage_flag"])
    top = sorted(out.items(), key=lambda kv: -kv[1]["blocked_auc"])[:12]
    print(f"  CANARY[{label}] top: " + ", ".join(f"{n}={v['blocked_auc']:.3f}" for n, v in top))
    print(f"  CANARY[{label}] flagged > {CANARY_THRESHOLD}: {len(flagged)} {flagged}")
    return dict(per_feature=out, flagged=flagged,
                max_blocked_auc=max(v["blocked_auc"] for v in out.values()))


def main() -> int:
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import average_precision_score, roc_auc_score

    t0 = time.time()
    print("=" * 100)
    print("EXPERIMENT 3b (corrected) — physical-only field + leakage canary + isotonic")
    print("=" * 100)
    z = np.load(PROC / "field_cache.npz")
    X, y, flat = z["X"], z["y"], z["flat"]
    names = [str(n) for n in z["names"]]
    cat, fp = load_catalogue(), load_footprint()
    folds = blocked_folds(flat)
    print(f"  X {X.shape} positives {int(y.sum()):,} folds {np.bincount(folds).tolist()}")

    # ---- canary on the physical set (this is what the emission model may use) -------------
    can_phys = canary(X, y, names, folds, "physical-only")

    # ---- canary on the catalogue-derived set, to DOCUMENT the leak that was removed --------
    Xc, nc = add_catalogue_features(X[:, :1], names[:1], flat, cat)
    Xcat, ncat = Xc[:, 1:], nc[1:]
    selfon = cat.ravel()[flat]
    Xcat[selfon, 0] = np.exp(-1.0 / 5.0)
    Xcat[selfon, 1] = np.exp(-1.0 / 15.0)
    Xcat[selfon, 2] = 1.0 / (1.0 + 1.0 / 3.0)
    can_cat = canary(Xcat, y, ncat, folds, "catalogue-derived")

    # ---- blocked OOF on the physical set ---------------------------------------------------
    oof = np.zeros(y.size, dtype=np.float32)
    per_fold = []
    for k in range(N_FOLDS):
        va = folds == k
        tr = ~va
        vpos = np.zeros((HEIGHT, WIDTH), bool)
        vpos.ravel()[flat[va & (y == 1)]] = True
        if vpos.any():
            tr &= ~(dist_to(vpos) <= BUFFER_PX).ravel()[flat]
        m = fit(X[tr], y[tr])
        oof[va] = m.predict_proba(X[va])[:, 1]
        per_fold.append(dict(fold=k, n_train=int(tr.sum()), n_val=int(va.sum()),
                             n_val_pos=int((y[va] == 1).sum()),
                             n_buffered_out=int((~tr & ~va).sum()),
                             auc=float(roc_auc_score(y[va], oof[va])),
                             ap=float(average_precision_score(y[va], oof[va]))))
        print(f"  fold {k}: train {int(tr.sum()):,} val {int(va.sum()):,} "
              f"val_pos {int((y[va]==1).sum()):,} AUC {per_fold[-1]['auc']:.4f} "
              f"AP {per_fold[-1]['ap']:.4f} [{time.time()-t0:.0f}s]")

    pooled_auc = float(roc_auc_score(y, oof))
    pooled_ap = float(average_precision_score(y, oof))
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(oof, y)
    cal = iso.predict(oof).astype(np.float32)
    # calibration quality in deciles of the calibrated probability
    qs = np.quantile(cal, np.linspace(0, 1, 11))
    qs[0], qs[-1] = -np.inf, np.inf
    bins = []
    for i in range(10):
        m = (cal >= qs[i]) & (cal < qs[i + 1])
        if m.sum() < 50:
            continue
        bins.append(dict(bin=i, n=int(m.sum()), mean_calibrated=float(cal[m].mean()),
                         observed_rate=float(y[m].mean()),
                         gap=float(cal[m].mean() - y[m].mean())))
    print("-" * 100)
    print(f"  PHYSICAL-ONLY pooled blocked AUC {pooled_auc:.4f} | AP {pooled_ap:.4f} | "
          f"prevalence {y.mean():.4f}")
    print(f"  calibration brier {float(np.mean((oof-y)**2)):.5f} -> "
          f"{float(np.mean((cal-y)**2)):.5f} (isotonic)  |  max |mean_cal - observed| "
          f"{max(abs(b['gap']) for b in bins):.4f}")

    # ---- refit on everything for full-grid scoring (calibration comes from the OOF) ---------
    final = fit(X, y, max_iter=320)
    import pickle

    with (PROC / "field_model.pkl").open("wb") as f:
        pickle.dump(dict(model=final, names=names, iso=iso), f)
    np.savez_compressed(PROC / "oof_physical.npz", oof=oof, cal=cal, y=y, flat=flat, folds=folds)

    out = ROOT / "evidence" / "lane_expecteddti_exp3b_field.json"
    out.write_text(json.dumps(dict(
        physical_only=dict(pooled_blocked_auc=pooled_auc, pooled_ap=pooled_ap,
                           prevalence=float(y.mean()), per_fold=per_fold,
                           fold_auc_spread=float(max(f["auc"] for f in per_fold) -
                                                 min(f["auc"] for f in per_fold)),
                           brier_raw=float(np.mean((oof - y) ** 2)),
                           brier_isotonic=float(np.mean((cal - y) ** 2)),
                           calibration_bins=bins,
                           leakage_canary=can_phys,
                           passes_canary=bool(can_phys["max_blocked_auc"] <= CANARY_THRESHOLD)),
        catalogue_derived=dict(leakage_canary=can_cat,
                               verdict=("QUARANTINED: circular target. Excluded from the "
                                        "emission model; documented here as the leakage the "
                                        "canary exists to catch.")),
        removed_artefact=dict(first_version_pooled_auc=0.9963,
                              first_version_hide_and_recover_dti=1.0000,
                              diagnosis=("circular: catalogue-proximity features predicting the "
                                         "catalogue; emission reproduced the withheld positives "
                                         "exactly")),
        seconds=round(time.time() - t0, 1),
    ), indent=1, default=float))
    print("wrote", out, f"[{time.time()-t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
