"""E3: build the submission raster with the DTI-optimal selector.

Steps
-----
1. Global calibrated surface: an inner component draw withholds 20 % of the
   catalogue; features come from the remaining visible catalogue only; the
   classifier is fitted on two quadrants and isotonic-calibrated on the third;
   the calibrated probability is predicted over the whole footprint.
2. Selection: ``gems64.select.ExpectedDtiGreedy`` (greedy add under the exact
   expected-DTI gain, then backward prune while the marginal gain > 0).
3. Packaging: the shared fail-closed writer ``gems64.submission_writer``
   (single-band float32, EPSG:32611, 100 m, all-finite, values in [0, 1], zero
   mass on the mapped catalogue), then ``gates.format_report`` against
   ``data/bridge/sample_submission.tif`` and ``validate.validate``.
4. Uniqueness: ``gems64.uniqueness.compare_array_to_registry`` against the
   pinned registry of prior rasters (Spearman rho and 3-px dot overlap).

Writes ``evidence/e3_submission.json`` and the GeoTIFF under
``docs/downloads/``.
"""

from __future__ import annotations

import hashlib
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
from gems64 import gates, grid as gridmod, holdout as H, uniqueness as U
from gems64.features import FeatureStack
from gems64.select import ExpectedDtiGreedy

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXTERNAL = pathlib.Path(os.environ.get("GEMS64_EXTERNAL",
                                       "/home/user/prior/60GEMSDOE-main/data/external"))
REGISTRY = pathlib.Path(os.environ.get("GEMS64_REGISTRY",
                                       "/home/user/prior/60GEMSDOE-main/registry"))
NEG = int(os.environ.get("E3_NEG", 400_000))
MAX_CAND = int(os.environ.get("E3_CAND", 250_000))
MAX_DOTS = int(os.environ.get("E3_DOTS", 150_000))
HIDE_FRAC = 0.20
SEED = 20261011


def build_global_surface(g, verbose=True):
    cat, fp, quad = g.catalogue, g.footprint, H.quadrant_ids(g.footprint)
    comp, _ = ndi.label(cat, H.STRUCT3)
    sizes = np.bincount(comp.ravel())
    rng = np.random.default_rng(SEED)
    pool = np.setdiff1d(np.unique(comp[cat]), [0])
    hidden = np.isin(comp, H._pick_segments(rng, sizes, pool,
                                            HIDE_FRAC * float(cat.sum()))) & cat
    collar = ndi.distance_transform_edt(~hidden) <= 3
    visible = cat & ~hidden & ~collar
    stack = FeatureStack(g, EXTERNAL, cache_dir=ROOT / ".cache").build(visible)
    pos_yx = np.nonzero(hidden & fp)
    ny, nx = np.nonzero(fp & ~cat)
    sel = rng.choice(ny.size, size=min(NEG, ny.size), replace=False)
    X = np.vstack([stack.matrix(*pos_yx), stack.matrix(ny[sel], nx[sel])])
    y = np.r_[np.ones(pos_yx[0].size, np.int8), np.zeros(sel.size, np.int8)]
    # spatial split: fit on quadrants 0,1,2 ; isotonic-calibrate on quadrant 3
    qpos = quad[pos_yx[0], pos_yx[1]]
    qneg = quad[ny[sel], nx[sel]]
    fit = np.r_[qpos != 3, qneg != 3]
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08,
                                         max_leaf_nodes=31, min_samples_leaf=50,
                                         l2_regularization=1.0, random_state=0,
                                         early_stopping=False)
    clf.fit(X[fit], y[fit])
    pc = clf.predict_proba(X[~fit])[:, 1]
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(pc, y[~fit])
    auc = float(roc_auc_score(y[~fit], pc))
    if verbose:
        print(f"  surface: visible={int(visible.sum())} hidden={int(hidden.sum())} "
              f"calib_auc={auc:.4f} n_cal={int((~fit).sum())}")
    p = np.zeros(g.shape, np.float32)
    for y0 in range(0, g.height, 512):
        y1 = min(g.height, y0 + 512)
        yy, xx = np.mgrid[y0:y1, 0:g.width]
        inside = fp[y0:y1] & ~cat[y0:y1]
        if not inside.any():
            continue
        p[y0:y1][inside] = iso.predict(
            clf.predict_proba(stack.matrix(yy[inside], xx[inside]))[:, 1]
        ).astype(np.float32)
    receipt = dict(visible_px=int(visible.sum()), hidden_px=int(hidden.sum()),
                   hide_frac=HIDE_FRAC, seed=SEED, calib_auc_heldout_quadrant=auc,
                   n_features=len(stack.names), feature_names=stack.names,
                   stack_receipt=stack.receipt)
    stack.free()
    del stack, X, y, clf
    return p, receipt, visible, hidden


def prior_correct(p: np.ndarray, r: float) -> np.ndarray:
    """Exact odds correction for negative sub-sampling at rate ``r``."""
    p = np.clip(np.asarray(p, np.float64), 0.0, 1.0 - 1e-12)
    return (r * p / (r * p + 1.0 - p)).astype(np.float32)


def main() -> int:
    t0 = time.time()
    g = gridmod.load_grid()
    cached = ROOT / ".cache" / "e3_surface.npy"
    rcpt_json = ROOT / ".cache" / "e3_surface_receipt.json"
    if cached.exists() and rcpt_json.exists() and os.environ.get("E3_REUSE"):
        print(f"reusing cached surface {cached}")
        p = np.load(cached)
        receipt = json.loads(rcpt_json.read_text())
    else:
        print("building global surface ...")
        p_raw, receipt, visible, hidden = build_global_surface(g)
        # exact odds correction for the negative sub-sampling used in training
        n_bg = int((g.footprint & ~g.catalogue).sum())
        r = NEG / n_bg
        p = prior_correct(p_raw, r)
        receipt.update(negative_subsampling_rate=r, negatives_kept=NEG,
                       background_pixels=n_bg,
                       prior_correction="w = r*p/(r*p+1-p)")
        (ROOT / ".cache").mkdir(exist_ok=True)
        np.save(ROOT / ".cache" / "e3_surface.npy", p)
        rcpt_json.write_text(json.dumps(receipt, indent=2, default=float))
        print(f"  prior correction r={r:.6f}: "
              f"sum_w {float(p_raw.sum()):.0f} -> {float(p.sum()):.0f}")

    cand_mask = g.footprint & ~g.catalogue & (p > 0)
    ys, xs = np.nonzero(cand_mask)
    if ys.size > MAX_CAND:
        keep = np.argsort(-p[ys, xs], kind="stable")[:MAX_CAND]
        ys, xs = ys[keep], xs[keep]
    cand = np.stack([ys, xs], axis=1).astype(np.int32)
    print(f"  candidates={cand.shape[0]}  sum_p={float(p.sum()):.1f}")

    sel = ExpectedDtiGreedy(p.astype(np.float64), cand)
    res = sel.run(max_dots=MAX_DOTS, prune=True, prune_passes=4, verbose=True)
    mask = sel.mask()
    print(f"  selected {res['n_dots']} dots, expected DTI={res['expected_dti']:.5f}, "
          f"mean kappa={res['mean_kappa']:.4f}")

    pred = np.where(mask, np.float32(1.0), np.float32(0.0))
    name = "h64-dtiopt-greedy-prune-calibrated"
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    sha = hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest()[:12]
    fname = f"gems64-{name}-{stamp}-{sha}-zeros.tif"
    out = ROOT / "docs" / "downloads" / fname
    note = "DTI-optimal greedy+prune on isotonic-calibrated multiphysics surface"
    rcpt = None
    from gems64 import submission_writer
    rcpt = submission_writer.write_submission(
        out, pred, ROOT / "data" / "bridge" / "sample_submission.tif", g.footprint,
        note=note, name=name, catalogue=g.catalogue,
        metadata=dict(experiment="E3", selector="expected-dti-greedy+backward-prune",
                      selector_result={k: v for k, v in res.items()},
                      surface={k: receipt[k] for k in
                               ("negative_subsampling_rate", "calib_auc_heldout_quadrant",
                                "n_features") if k in receipt}))

    report = gates.format_report(out, ROOT / "data" / "bridge" / "sample_submission.tif",
                                 footprint=g.footprint)
    print("  format_report ok:", report["ok"], report.get("problems"))

    # ---- uniqueness against the pinned registry
    idx = json.loads((REGISTRY / "registry_index.json").read_text())
    U.ROOT = REGISTRY.parent
    uniq = U.compare_array_to_registry(pred, idx, g.footprint, file_sha256=rcpt["sha256"])
    rows = uniq["rows"]
    max_rho = uniq["worst_spearman_full_footprint"]
    max_ov = uniq["worst_dot_overlap"]
    worst_rho = None
    worst_ov = None
    out_json = dict(
        experiment="E3-submission-build",
        file=str(out.relative_to(ROOT)), file_name=fname,
        submission_name=name, note=note, note_chars=len(note),
        raster_sha256=rcpt["sha256"], raster_bytes=rcpt["bytes"],
        array_sha256=hashlib.sha256(np.ascontiguousarray(pred).tobytes()).hexdigest(),
        n_dots=int(res["n_dots"]), selector=res,
        surface=receipt,
        format_report=report,
        uniqueness=dict(n_registry_rasters_checked=uniq["registry_rasters_checked"],
                        n_registry_rasters_expected=uniq["registry_rasters_expected"],
                        missing_or_invalid=uniq["missing_or_invalid"],
                        max_abs_spearman_full_footprint=max_rho,
                        worst_spearman_submission=uniq["worst_rho_submission"],
                        max_dot_overlap_3px=max_ov,
                        worst_overlap_submission=uniq["worst_overlap_submission"],
                        worst_jaccard_dot_sets=uniq["worst_jaccard_dot_sets"],
                        byte_unique=uniq["byte_unique_among_checked"],
                        pixel_unique=uniq["pixel_unique_among_checked"],
                        lane_rule="fail if rho>0.90 or 3px dot overlap>0.70",
                        shared_verdict=uniq["verdict"],
                        passed=bool(max_rho is not None and abs(max_rho) <= 0.90 and
                                    max_ov is not None and max_ov <= 0.70 and
                                    uniq["byte_unique_among_checked"] and
                                    uniq["pixel_unique_among_checked"])),
        elapsed_s=round(time.time() - t0, 1),
    )
    (ROOT / "evidence" / "e3_submission.json").write_text(json.dumps(out_json, indent=2, default=float))
    print(json.dumps({k: out_json[k] for k in ("file_name", "raster_sha256", "n_dots",
                                               "uniqueness")}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
