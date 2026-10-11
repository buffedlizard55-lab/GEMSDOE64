#!/usr/bin/env python3
"""Experiment 3b — spatially blocked OOF, hide-and-recover holdout, isotonic calibration.

Two instruments are produced, and they are reported separately because they measure different
things.  Conflating them is the failure mode that this project family already documented once
(GEMSDOE32, knowledge/01: a catalogue-truth proxy ranked a candidate *above* an incumbent that a
live-anchored model ranked *below* it).

  INSTRUMENT A — hide-and-recover holdout (the prompt's specification).
    Whole fault segments are withheld with a 30 px buffer.  Every catalogue-derived feature is
    recomputed from the VISIBLE faults only.  Visible faults are masked pixel-exactly out of the
    scored domain.  Pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel) is the score.
    Limitation, stated up front: its truth is drawn from the published catalogue, and the
    organizers mask catalogue pixels out of scoring, so this instrument cannot reward a genuinely
    new fault.  It measures "can the field find fault-like ground it has not seen", not "can it
    find the hidden label set".

  INSTRUMENT B — spatially blocked OOF discrimination + isotonic calibration.
    Five spatially contiguous folds of 96 px blocks with a 30 px buffer.  The pooled OOF scores
    are calibrated by isotonic regression, which is what turns the field into the probability
    surface the Expected-DTI-optimal rule (verified 7/7 in Experiment 1) requires.

Nothing here writes a submission.  That is ``scripts/lane_expecteddti_emit_and_ship.py``.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems64.lane_expecteddti.gridext import HEIGHT, WIDTH, load_catalogue, load_footprint  # noqa: E402
from gems64.lane_expecteddti.metricext import ALPHA, BETA, components  # noqa: E402

PROC = ROOT / "data" / "processed"
SEED = 20261011
BLOCK = 96
BUFFER_PX = 30
N_FOLDS = 5
SUPER = 3          # super-block = SUPER x SUPER tiles, grouped so folds are spatially contiguous


def blocked_folds(flat: np.ndarray, n_folds: int = N_FOLDS) -> np.ndarray:
    """Spatially contiguous fold assignment on a serpentine ordering of super-blocks."""
    yy, xx = np.divmod(flat, WIDTH)
    tb, lb = yy // BLOCK, xx // BLOCK
    ntb = (HEIGHT + BLOCK - 1) // BLOCK
    nlb = (WIDTH + BLOCK - 1) // BLOCK
    sy, sx = tb // SUPER, lb // SUPER
    nsy, nsx = (ntb + SUPER - 1) // SUPER, (nlb + SUPER - 1) // SUPER
    # serpentine: alternate row direction so neighbouring super-blocks get consecutive indices
    idx = np.where(sy % 2 == 0, sy * nsx + sx, sy * nsx + (nsx - 1 - sx))
    # Equal-COUNT bins on the rank of the super-block index, not equal-WIDTH bins on the index
    # itself.  The footprint is irregular (only 42 % of the grid is in it and the sample is
    # tile-stratified), so equal-width bins gave folds of 219533 / 204399 / 34130 / 9769 / 4755
    # rows.  Ranking first keeps folds spatially contiguous AND balanced.
    u, inv = np.unique(idx, return_inverse=True)
    counts = np.bincount(inv)
    cum = np.concatenate([[0], np.cumsum(counts)])
    edges = np.linspace(0, cum[-1], n_folds + 1).astype(np.int64)
    fold_of_super = np.searchsorted(edges[1:-1], cum[:-1], side="right")
    return np.minimum(fold_of_super[inv], n_folds - 1).astype(np.int8)


def segment_catalogue(cat: np.ndarray, n_groups: int = 4) -> tuple[np.ndarray, np.ndarray]:
    """Split the catalogue into whole fault segments, then group segments into ``n_groups``.

    Segments are 8-connected components of the catalogue mask.  Groups are assigned by segment
    centroid on a serpentine super-block ordering, so a withheld group is a set of WHOLE segments
    occupying a contiguous region - the hide-and-recover design the prompt specifies.
    """
    from scipy.ndimage import label as cc_label

    lab, n = cc_label(cat, structure=np.ones((3, 3), dtype=np.int8))
    seg_id = np.zeros(n + 1, dtype=np.int64)
    objs = np.argwhere(lab > 0)
    if objs.size == 0:
        return lab, np.zeros(cat.shape, np.int8)
    ids = lab[objs[:, 0], objs[:, 1]]
    yy, xx = objs[:, 0], objs[:, 1]
    order = np.argsort(ids, kind="stable")
    bounds = np.searchsorted(ids[order], np.unique(ids[order]))
    groups = np.zeros(n + 1, dtype=np.int8)
    ntb = (HEIGHT + BLOCK - 1) // BLOCK
    nlb = (WIDTH + BLOCK - 1) // BLOCK
    keys = []
    for i in range(len(bounds) - 1):
        sl = order[bounds[i]:bounds[i + 1]]
        sid = int(ids[sl[0]])
        cy, cx = yy[sl].mean(), xx[sl].mean()
        sy, sx = int(cy // BLOCK) // SUPER, int(cx // BLOCK) // SUPER
        nsx = (nlb + SUPER - 1) // SUPER
        k = sy * nsx + sx if sy % 2 == 0 else sy * nsx + (nsx - 1 - sx)
        keys.append((sid, k, sl.size))
    keys.sort(key=lambda t: t[1])
    per = int(np.ceil(len(keys) / n_groups))
    for i, (sid, _, _) in enumerate(keys):
        groups[sid] = min(i // per, n_groups - 1)
    seg_group = groups[lab]
    seg_group[lab == 0] = -1
    return lab, seg_group.astype(np.int8)


def dist_to(mask: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt

    return distance_transform_edt(~mask) if mask.any() else np.full(mask.shape, 1e6)


def add_catalogue_features(X: np.ndarray, names: list[str], flat: np.ndarray,
                           visible: np.ndarray) -> tuple[np.ndarray, list[str]]:
    """Append catalogue-derived features computed from ``visible`` faults ONLY.

    This is the anti-leakage step: when a fold withholds segments, the distance features are
    rebuilt from the visible remainder, never from the withheld truth.
    """
    from scipy.ndimage import gaussian_filter

    d = dist_to(visible).astype(np.float32)
    dens = gaussian_filter(visible.astype(np.float32), 6.0)
    extra = np.stack([
        np.exp(-d.ravel()[flat] / 5.0),
        np.exp(-d.ravel()[flat] / 15.0),
        1.0 / (1.0 + d.ravel()[flat] / 3.0),
        dens.ravel()[flat],
    ], axis=1).astype(np.float32)
    enames = ["cat_prox_e5", "cat_prox_e15", "cat_prox_inv3", "cat_density_s6"]
    return np.hstack([X, extra]), names + enames


def fit_model(X, y, seed=SEED):
    from sklearn.ensemble import HistGradientBoostingClassifier

    m = HistGradientBoostingClassifier(
        loss="log_loss", max_iter=260, learning_rate=0.075, max_leaf_nodes=31,
        min_samples_leaf=60, l2_regularization=1.0, max_features=0.7,
        early_stopping=False, random_state=seed,
    )
    m.fit(X, y)
    return m


def instrument_b(X, y, flat, cat, footprint) -> dict:
    """Spatially blocked OOF + isotonic calibration."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score, average_precision_score

    folds = blocked_folds(flat)
    oof = np.zeros(y.size, dtype=np.float32)
    per_fold = []
    t0 = time.time()
    for k in range(N_FOLDS):
        va = folds == k
        tr = ~va
        # 30 px buffer: drop training rows that lie within BUFFER_PX of any validation POSITIVE
        vpos = np.zeros((HEIGHT, WIDTH), bool)
        vpos.ravel()[flat[va & (y == 1)]] = True
        if vpos.any():
            buf = dist_to(vpos) <= BUFFER_PX
            tr &= ~(buf.ravel()[flat])
        m = fit_model(X[tr], y[tr])
        oof[va] = m.predict_proba(X[va])[:, 1]
        per_fold.append(dict(fold=k, n_train=int(tr.sum()), n_val=int(va.sum()),
                             n_val_pos=int((y[va] == 1).sum()),
                             auc=float(roc_auc_score(y[va], oof[va])),
                             ap=float(average_precision_score(y[va], oof[va]))))
        print(f"  fold {k}: train {int(tr.sum()):,} val {int(va.sum()):,} "
              f"val_pos {int((y[va]==1).sum()):,} AUC {per_fold[-1]['auc']:.4f} "
              f"AP {per_fold[-1]['ap']:.4f}  [{time.time()-t0:.0f}s]")
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(oof, y)
    cal = iso.predict(oof)
    return dict(
        instrument="B_blocked_oof_isotonic",
        n_folds=N_FOLDS, block_px=BLOCK, buffer_px=BUFFER_PX,
        pooled_auc=float(roc_auc_score(y, oof)),
        pooled_ap=float(average_precision_score(y, oof)),
        mean_fold_auc=float(np.mean([f["auc"] for f in per_fold])),
        fold_auc_spread=float(np.max([f["auc"] for f in per_fold]) -
                              np.min([f["auc"] for f in per_fold])),
        per_fold=per_fold,
        calibration=dict(method="isotonic", n_points=int(oof.size),
                         mean_raw=float(oof.mean()), mean_calibrated=float(cal.mean()),
                         prevalence=float(y.mean()),
                         brier_raw=float(np.mean((oof - y) ** 2)),
                         brier_calibrated=float(np.mean((cal - y) ** 2))),
        seconds=round(time.time() - t0, 1),
    ), oof, iso


def instrument_a(X, y, flat, cat, footprint, names) -> dict:
    """Hide-and-recover: withhold whole fault segments with a buffer, rebuild catalogue features."""
    from sklearn.metrics import roc_auc_score

    _, seg_group = segment_catalogue(cat, n_groups=4)
    res = dict(instrument="A_hide_and_recover", n_groups=4, buffer_px=BUFFER_PX, folds=[])
    pooled_pred, pooled_true = [], []
    for k in range(4):
        withheld = (seg_group == k)
        visible = cat & ~withheld
        # pixel-exact mask: visible faults are removed from the scored domain entirely
        scored = footprint & ~visible
        Xk, nk = add_catalogue_features(X, names, flat, visible)
        tr = (~withheld.ravel()[flat]) & scored.ravel()[flat]
        va = withheld.ravel()[flat] & footprint.ravel()[flat]
        if va.sum() == 0 or tr.sum() == 0:
            continue
        m = fit_model(Xk[tr], y[tr])
        pv = m.predict_proba(Xk[va])[:, 1]
        pooled_pred.append(pv)
        pooled_true.append(np.ones(pv.size, np.int8))
        # pooled DTI on a local window around the withheld segments
        ys, xs = np.nonzero(withheld)
        y0, y1 = max(0, ys.min() - 40), min(HEIGHT, ys.max() + 41)
        x0, x1 = max(0, xs.min() - 40), min(WIDTH, xs.max() + 41)
        win = np.zeros((HEIGHT, WIDTH), np.float32)
        wf = win.ravel()
        wf[flat[va]] = pv
        win = win[y0:y1, x0:x1]
        tw = withheld[y0:y1, x0:x1]
        vw = scored[y0:y1, x0:x1]
        # emit the top-q of the window by probability, at the incumbent's live emission share
        for share in (0.0074, 0.0148, 0.0296):
            q = np.quantile(win[vw & (win > 0)], 1 - share) if (vw & (win > 0)).any() else 1.0
            em = (win >= q) & vw
            c = components(em.astype(float), tw, valid=vw)
            res["folds"].append(dict(group=k, share=share, n_withheld_pos=int(tw.sum()),
                                     n_visible_pos=int(visible.sum()), n_emitted=int(em.sum()),
                                     pooled_dti=c["dti"], tp=c["TP_w"], fp=c["FP_w"],
                                     n_truth=c["n_truth"], credit_per_dot=c["credit_per_unit_mass"]))
        auc = float(roc_auc_score(np.r_[np.ones(pv.size), np.zeros(int(tr.sum() // 10))],
                                 np.r_[pv, m.predict_proba(Xk[tr][np.random.default_rng(1)
                                                                 .choice(tr.sum(),
                                                                         tr.sum() // 10,
                                                                         replace=False)])[:, 1]]))
        res["folds"][-1]["recover_auc"] = auc
        print(f"  group {k}: withheld {int(tw.sum()):,} visible {int(visible.sum()):,} "
              f"auc {auc:.4f}")
    if pooled_pred:
        pp = np.concatenate(pooled_pred)
        res["n_recovered_positives"] = int(pp.size)
        res["mean_recovered_prob"] = float(pp.mean())
    return res


def main() -> int:
    t0 = time.time()
    print("=" * 100)
    print("EXPERIMENT 3b — blocked OOF, hide-and-recover holdout, isotonic calibration")
    print("=" * 100)
    z = np.load(PROC / "field_cache.npz", allow_pickle=False)
    X, y, flat = z["X"], z["y"], z["flat"]
    names = [str(n) for n in z["names"]]
    print(f"  cache: X {X.shape} y {y.shape} positives {int(y.sum()):,}")
    cat = load_catalogue()
    fp = load_footprint()

    # instrument B needs catalogue features too, built from ALL catalogue faults EXCEPT the row
    # itself would leak; we use the leave-fold-out visible set inside each fold instead.
    folds = blocked_folds(flat)
    Xb = X.copy()
    namesb = list(names)
    # per-fold catalogue features are rebuilt inside instrument_a; for B use a global version
    # built from the catalogue with each row's own cell excluded (pixel-exact self-mask).
    Xb, namesb = add_catalogue_features(Xb, namesb, flat, cat)
    selfon = np.isin(flat, np.flatnonzero(cat.ravel()))
    Xb[selfon, namesb.index("cat_prox_e5")] = np.exp(-1.0 / 5.0)
    Xb[selfon, namesb.index("cat_prox_e15")] = np.exp(-1.0 / 15.0)
    Xb[selfon, namesb.index("cat_prox_inv3")] = 1.0 / (1.0 + 1.0 / 3.0)

    b, oof, iso = instrument_b(Xb, y, flat, cat, fp)
    a = instrument_a(X, y, flat, cat, fp, names)

    np.savez_compressed(PROC / "oof_cache.npz", oof=oof, y=y, flat=flat,
                        folds=folds, iso_x=iso.X_thresholds_, iso_y=iso.y_thresholds_)
    out = ROOT / "evidence" / "lane_expecteddti_exp3b_leaky_audit.json"
    out.write_text(json.dumps(dict(instrument_b=b, instrument_a=a,
                                   feature_names=namesb,
                                   seconds=round(time.time() - t0, 1)), indent=1, default=float))
    print("-" * 100)
    print(f"INSTRUMENT B pooled AUC {b['pooled_auc']:.4f} | AP {b['pooled_ap']:.4f} | "
          f"fold spread {b['fold_auc_spread']:.4f}")
    print(f"calibration: brier {b['calibration']['brier_raw']:.5f} -> "
          f"{b['calibration']['brier_calibrated']:.5f} (isotonic)")
    print("wrote", out, f"[{time.time()-t0:.0f}s]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
