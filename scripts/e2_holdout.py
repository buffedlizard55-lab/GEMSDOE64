"""E2: holdout comparison of emission rules on ONE calibrated surface.

Design (parallel-run protocol rule 2 -- hide-and-recover)
---------------------------------------------------------
* ``gems64.holdout.buffered_component_draw`` withholds **whole** catalogue
  components inside four label-blind eroded quadrants, with a 3-px feature
  buffer.  The withheld components are the scored truth; every other catalogue
  pixel in the region is masked out of scoring (``masked_known``), matching the
  organiser's statement that a dot on a mapped trace earns nothing.
* Features are built **only** from the visible catalogue
  (``cat & ~collar & ~inner_hidden``), so a fold can never see its own truth.
* The model is trained on an *inner* component draw inside the three quadrants
  that are not being scored, and isotonic-calibrated on the third of those
  three, so the probability surface used by the selector is out-of-fold.
* Score: pooled DTI (alpha = 0.2, beta = 0.8, 300 m triangular kernel).

Rules compared on the *same* surface
------------------------------------
``nms_2p8``  incumbent heuristic spacing (rank by p, suppress within 2.8 px)
``mclp``     maximal-coverage lazy greedy, matched mass
``dtiopt``   this lane: expected-DTI greedy add + backward prune
Controls: ``distance_only`` (proximity to visible faults) and ``random``.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from gems64 import grid as gridmod, holdout as H
from gems64.features import FeatureStack
from gems64.metric import ALPHA, BETA, EPS, kernel
from gems64.select import ExpectedDtiGreedy, MaxCoverGreedy, nms_topk

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXTERNAL = pathlib.Path(os.environ.get("GEMS64_EXTERNAL",
                                       "/home/user/prior/60GEMSDOE-main/data/external"))
NEG_PER_FOLD = int(os.environ.get("E2_NEG", 250_000))
MAX_CAND = int(os.environ.get("E2_CAND", 260_000))
MAX_DOTS = int(os.environ.get("E2_DOTS", 60_000))
ONLY_FOLDS = os.environ.get("E2_FOLDS", "")


# ------------------------------------------------------------------ components
def block_components(pred: np.ndarray, truth: np.ndarray, active: np.ndarray,
                     block: int = 16):
    """Per-spatial-block (tp, fp, fn) so a paired block bootstrap can be run."""
    p = pred & active
    g = truth & active
    dp = ndi.distance_transform_edt(~p)
    dg = ndi.distance_transform_edt(~g)
    tp_pix = (kernel(dp) * g).astype(np.float32)
    fn_pix = ((1.0 - kernel(dp)) * g).astype(np.float32)
    fp_pix = ((1.0 - kernel(dg)) * p).astype(np.float32)
    Hh, Ww = pred.shape
    nb_y, nb_x = int(np.ceil(Hh / block)), int(np.ceil(Ww / block))
    tp = np.zeros((nb_y, nb_x)); fp = np.zeros((nb_y, nb_x)); fn = np.zeros((nb_y, nb_x))
    for arr, out in ((tp_pix, tp), (fp_pix, fp), (fn_pix, fn)):
        pad = np.zeros((nb_y * block, nb_x * block), np.float32)
        pad[:Hh, :Ww] = arr
        out[:] = pad.reshape(nb_y, block, nb_x, block).sum(axis=(1, 3))
    return tp, fp, fn


def pooled(tp, fp, fn) -> float:
    T, F, N = tp.sum(), fp.sum(), fn.sum()
    return float(T / (T + ALPHA * F + BETA * N + EPS))


def block_bootstrap_diff(ref, alt, blocks: int, rng, n_boot: int = 400):
    """Paired bootstrap over spatial blocks of (alt - ref) pooled DTI."""
    tpr, fpr, fnr = ref
    tpa, fpa, fna = alt
    ny, nx = tpr.shape
    flat = [(tpr[i, j], fpr[i, j], fnr[i, j], tpa[i, j], fpa[i, j], fna[i, j])
            for i in range(ny) for j in range(nx)]
    n = len(flat)
    diffs = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        tr = fr = nr = ta = fa = na = 0.0
        for k in idx:
            a, b, c, d, e, f = flat[k]
            tr += a; fr += b; nr += c; ta += d; fa += e; na += f
        pr = tr / (tr + ALPHA * fr + BETA * nr + EPS)
        pa = ta / (ta + ALPHA * fa + BETA * na + EPS)
        diffs.append(pa - pr)
    d = np.array(diffs)
    return dict(mean=float(d.mean()), se=float(d.std(ddof=1)),
                ci=[float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
                z=float(d.mean() / (d.std(ddof=1) + 1e-12)), n_boot=n_boot)


# ------------------------------------------------------------------ surface
def build_surface(g, folds, quad, rng_seed=0, verbose=True):
    """One out-of-fold, isotonic-calibrated probability field per fold."""
    cat = g.catalogue
    fp = g.footprint
    surfaces, reports = [], []
    for f in folds:
        q = f["fold"]
        others = [i for i in range(4) if i != q]
        hidden_all = f["hidden_all"]
        collar_hidden = ndi.distance_transform_edt(~hidden_all) <= 3
        # inner pseudo-truth inside the two training quadrants
        cal_q = others[2]
        train_q = others[:2]
        comp, _ = ndi.label(cat, H.STRUCT3)
        rng = np.random.default_rng(1000 + q)
        pool = np.unique(comp[cat & (quad == train_q[0])])
        pool2 = np.unique(comp[cat & (quad == train_q[1])])
        pool = np.setdiff1d(np.concatenate([pool, pool2]), [0])
        sizes = np.bincount(comp.ravel())
        inner = H._pick_segments(rng, sizes, pool, 0.25 * float((cat & np.isin(quad, train_q)).sum()))
        inner_hidden = np.isin(comp, inner) & cat
        hidden_union = hidden_all | inner_hidden
        # distance to the hidden set (template convention), not to non-catalogue
        collar = ndi.distance_transform_edt(~hidden_union) <= 3
        visible = cat & ~hidden_union & ~collar
        if verbose:
            print(f"  fold{q}: visible={int(visible.sum())} inner_hidden={int(inner_hidden.sum())} "
                  f"withheld={int((f['truth'] & f['region']).sum())}")
        t0 = time.time()
        stack = FeatureStack(g, EXTERNAL).build(visible)
        if verbose:
            print(f"    features built in {time.time()-t0:.1f}s ({len(stack.names)} bands)")
        # --- training sample
        pos_yx = np.nonzero(inner_hidden & fp)
        neg_pool = fp & ~cat & ~inner_hidden
        ny, nx = np.nonzero(neg_pool)
        sel = rng.choice(ny.size, size=min(NEG_PER_FOLD, ny.size), replace=False)
        neg_yx = (ny[sel], nx[sel])
        X = np.vstack([stack.matrix(*pos_yx), stack.matrix(*neg_yx)])
        y = np.r_[np.ones(pos_yx[0].size, np.int8), np.zeros(neg_yx[0].size, np.int8)]
        # --- spatial split: train on quadrant A, calibrate on quadrant B
        tr = np.isin(quad[pos_yx[0], pos_yx[1]], [train_q[0]])
        cn = np.isin(quad[neg_yx[0], neg_yx[1]], [train_q[0]])
        fit_mask = np.r_[tr, cn]
        clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.1,
                                             max_leaf_nodes=31, min_samples_leaf=40,
                                             l2_regularization=1.0, random_state=0,
                                             early_stopping=False)
        clf.fit(X[fit_mask], y[fit_mask])
        pc = clf.predict_proba(X[~fit_mask])[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(pc, y[~fit_mask])
        auc_all = float(roc_auc_score(y[~fit_mask], pc))
        # --- leakage canary: each feature alone, same split
        canary = {}
        for k, nm in enumerate(stack.names):
            v = X[~fit_mask, k]
            if np.ptp(v) == 0:
                canary[nm] = None
                continue
            a = float(roc_auc_score(y[~fit_mask], v))
            canary[nm] = round(max(a, 1 - a), 4)
        # --- predict the scored fold on a row-chunked sweep
        p = np.zeros(g.shape, np.float32)
        rows = np.arange(g.height)
        for y0 in range(0, g.height, 512):
            y1 = min(g.height, y0 + 512)
            yy, xx = np.mgrid[y0:y1, 0:g.width]
            inside = fp[y0:y1] & ~cat[y0:y1]
            if not inside.any():
                continue
            m = stack.matrix(yy[inside], xx[inside])
            raw = clf.predict_proba(m)[:, 1]
            p[y0:y1][inside] = iso.predict(raw).astype(np.float32)
        surfaces.append(p)
        reports.append(dict(fold=q, n_visible=int(visible.sum()),
                            n_inner_hidden=int(inner_hidden.sum()),
                            n_withheld=int((f["truth"] & f["region"]).sum()),
                            n_pos_train=int(fit_mask.sum()), n_cal=int((~fit_mask).sum()),
                            calib_auc=auc_all,
                            feature_build_s=round(time.time() - t0, 1),
                            leakage_canary_max_single_feature_auc=max(
                                (v for v in canary.values() if v), default=None),
                            leakage_canary=canary))
        stack.free()
        del stack, X, y, clf
        import gc; gc.collect()
    return surfaces, reports


# ------------------------------------------------------------------ rules
def candidates_for(p, region, active, cap=MAX_CAND):
    cand_mask = region & active & (p > 0)
    ys, xs = np.nonzero(cand_mask)
    if ys.size > cap:
        keep = np.argsort(-p[ys, xs], kind="stable")[:cap]
        ys, xs = ys[keep], xs[keep]
    return np.stack([ys, xs], axis=1).astype(np.int32)


def rule_masks(p, cand, mass):
    out = {}
    out["nms_2p8"] = nms_topk(p, cand, 2.8, mass)
    mc = MaxCoverGreedy(p.astype(np.float64), cand)
    r = mc.run(mass)
    out["mclp"] = r["mask"]
    return out


def main() -> int:
    t_start = time.time()
    g = gridmod.load_grid()
    folds, quad = H.buffered_component_draw(g, seed=20, hide_frac=0.20, buffer_px=3)
    if ONLY_FOLDS:
        keep = {int(v) for v in ONLY_FOLDS.split(",")}
        folds = [f for f in folds if f["fold"] in keep]
    print(f"folds built; withheld positives = "
          f"{int(sum((f['truth'] & f['region']).sum() for f in folds))}")
    cache = ROOT / "evidence" / "e2_surfaces.npz"
    if cache.exists() and not os.environ.get("E2_REBUILD"):
        z = np.load(cache, allow_pickle=True)
        surfaces = [z[f"fold{f['fold']}"] for f in folds]
        reports = json.loads((ROOT / "evidence" / "e2_fold_reports.json").read_text())
        print(f"loaded cached surfaces from {cache.name}")
    else:
        surfaces, reports = build_surface(g, folds, quad)
        np.savez_compressed(cache, **{f"fold{f['fold']}": p for f, p in zip(folds, surfaces)})
        (ROOT / "evidence" / "e2_fold_reports.json").write_text(
            json.dumps(reports, indent=2, default=float))

    rng = np.random.default_rng(7)
    per_fold = []
    comps_acc = {}
    for f, p in zip(folds, surfaces):
        region, truth = f["region"], f["truth"]
        active = region & g.footprint & ~f["masked_known"]
        cand = candidates_for(p, region, active)
        # this lane: expected-DTI greedy + backward prune on the calibrated surface
        w = (p.astype(np.float64)) * (region & active)   # score-domain-restricted surface
        sel = ExpectedDtiGreedy(w, cand)
        t_sel = time.time()
        res = sel.run(max_dots=MAX_DOTS, prune=True, prune_passes=3)
        print(f"    dtiopt: {res['n_dots']} dots in {time.time()-t_sel:.0f}s "
              f"(expected DTI {res['expected_dti']:.5f})")
        mass = res["n_dots"]
        masks = {"dtiopt": sel.mask()}
        t_b = time.time()
        masks.update(rule_masks(p, cand, mass))
        print(f"    baselines in {time.time()-t_b:.0f}s")
        # controls
        dcat = np.exp(-ndi.distance_transform_edt(~f["visible"]) / 3.0).astype(np.float32)
        c2 = cand[np.argsort(-dcat[cand[:, 0], cand[:, 1]], kind="stable")[:mass]]
        m = np.zeros(g.shape, bool); m[c2[:, 0], c2[:, 1]] = True
        masks["distance_only"] = m
        c3 = cand[rng.choice(cand.shape[0], size=mass, replace=False)]
        m = np.zeros(g.shape, bool); m[c3[:, 0], c3[:, 1]] = True
        masks["random"] = m

        comps = {}
        for name, mk in masks.items():
            comps[name] = block_components(mk, truth, active)
        row = dict(fold=f["fold"], mass=mass,
                   expected_dti=round(res["expected_dti"], 6),
                   mean_kappa=round(res["mean_kappa"], 4))
        for name, c in comps.items():
            row[name] = round(pooled(*c), 6)
            comps_acc.setdefault(name, []).append(c)
        per_fold.append(row)
        print(f"  fold{f['fold']} mass={mass} " +
              " ".join(f"{k}={v:.4f}" for k, v in row.items() if k != "fold"))

    # pooled + paired block bootstrap vs each baseline
    C = comps_acc
    def stack_comps(name):
        return tuple(np.sum([c[i] for c in C[name]], axis=0) for i in range(3))
    pooled_dti = {name: pooled(*stack_comps(name)) for name in C}
    boot = {}
    rbg = np.random.default_rng(99)
    for name in C:
        if name == "dtiopt":
            continue
        boot[name] = block_bootstrap_diff(stack_comps(name), stack_comps("dtiopt"),
                                          16, rbg, n_boot=300)
    best_base = max((n for n in C if n != "dtiopt"), key=lambda n: pooled_dti[n])
    gate = boot[best_base]
    out = dict(
        experiment="E2-holdout-rule-comparison",
        evaluator_version="gems64-pooled-buffered-loqo-v1",
        split="buffered-whole-components-loqo-v2 (shared template)",
        withheld_positive_pixels=int(sum((f["truth"] & f["region"]).sum() for f in folds)),
        pooled_dti={k: round(v, 6) for k, v in sorted(pooled_dti.items(), key=lambda kv: -kv[1])},
        paired_block_bootstrap_vs_dtiopt=boot,
        gate=dict(baseline=best_base, delta=round(gate["mean"], 6),
                  se=round(gate["se"], 6), z=round(gate["z"], 3),
                  ci=[round(gate["ci"][0], 6), round(gate["ci"][1], 6)],
                  threshold="delta > 2*SE", passed=bool(gate["mean"] > 2 * gate["se"])),
        per_fold=per_fold, fold_reports=reports,
        elapsed_s=round(time.time() - t_start, 1),
    )
    (ROOT / "evidence" / "e2_holdout.json").write_text(json.dumps(out, indent=2, default=float))
    np.savez_compressed(ROOT / "evidence" / "e2_surfaces.npz",
                        **{f"fold{f['fold']}": p for f, p in zip(folds, surfaces)})
    print(json.dumps({k: out[k] for k in ("withheld_positive_pixels", "pooled_dti", "gate")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
