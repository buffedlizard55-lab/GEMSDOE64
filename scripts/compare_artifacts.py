"""Side-by-side scoring of shipped dot rasters on the two local proxy instruments.

The private expert labels are not available, so no number here is a competition
score.  What *is* available are two fault populations that can stand in for
"faults the organiser will score":

* ``cat``       -- the mapped public catalogue (``data/official/existing_faults.tif``).
                   Organizer-grade provenance, but the organizer removes exactly these
                   pixels from scoring, so a high value here means "near the known
                   network", not "discovered a new fault".
* ``sgmc_off``  -- USGS SGMC compilation minus a 300 m collar around the catalogue: an
                   independent compilation restricted to the *off-catalogue* band,
                   which is the population the private labels are drawn from.
* ``sgmc``      -- the whole SGMC compilation, as an upper-bound sensitivity.

Every artifact is compared against an area-matched random control drawn from the same
active lattice, so the reported ``delta`` is a per-mass skill measure.  Blocks are the
same eight ~20 x 20 km super-blocks used by the promotion gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57.grid import SHAPE  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from build_scarp_stage2 import block_ids, lazy_greedy, metric_terms, ALPHA, BETA  # noqa: E402

WORK = ROOT / "work"
OUT = ROOT / "evidence" / "artifact_comparison.json"

ARTIFACTS = {
    "scarpcover60k": ROOT / "docs/downloads/gems64-scarpcover-60000-98d317b7-zeros.tif",
    "h64-lidar-scarp-cv": ROOT / "submissions/gems64-h64-lidar-scarp-cv-20261011T220000Z.tif",
    "h64-lane-ampsnr": ROOT / "submissions/gems64-lane-ampsnr-37654-20261011.tif",
    "champion-h33-2-b2": ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif",
    "dotted-d2.8-44090": ROOT / "data/registry/GEMSDOE25__dotted-h19-5-d2-8.tif",
    "h19-5-121k": ROOT / "data/registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif",
}


def read_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(1)
    return np.nan_to_num(a) >= 1.0


def main() -> int:
    fp = np.load(WORK / "fp.npy")
    cat = np.load(WORK / "cat.npy")
    sgmc = np.load(WORK / "sgmc.npy")
    sgmc_off = np.load(WORK / "sgmc_off.npy")
    truths = {"cat": cat, "sgmc": sgmc, "sgmc_off": sgmc_off}

    field = np.load(WORK / "field_oof.npy").astype(np.float32)
    # candidate lattice: the same stride-2 lattice the lane selects on
    lat = np.zeros(fp.shape, bool)
    lat[::2, ::2] = True
    lat &= fp
    active = lat & ~cat
    cand = np.flatnonzero(active.ravel())
    rng = np.random.default_rng(20261011)

    blk = block_ids(fp.shape)
    blocks = [b for b in np.unique(blk) if (fp & (blk == b)).any()]

    masks = {k: read_mask(v) for k, v in ARTIFACTS.items()}
    for k, m in masks.items():
        assert m.shape == fp.shape, (k, m.shape)

    rows = []
    for name, dots in masks.items():
        n = int(dots.sum())
        entry = {"artifact": name, "dots": n, "path": str(ARTIFACTS[name].relative_to(ROOT))}
        dcat = np.load(WORK / "dcat.npy")
        entry["median_distance_to_catalogue_px"] = round(float(np.median(dcat[dots])), 2)
        entry["frac_within_3px_of_catalogue"] = round(float(dots[dcat <= 3.0].sum()) / max(n, 1), 4)
        for tname, truth in truths.items():
            pooled = metric_terms(dots, truth, (0, 0, *fp.shape), fp.shape)
            entry[f"dti_{tname}"] = round(pooled["dti"], 4)
        # area-matched random control, same lattice, same count
        pick = rng.choice(cand.size, size=min(n, cand.size), replace=False)
        ctrl = np.zeros(fp.shape, bool)
        ctrl.ravel()[cand[pick]] = True
        for tname in ("cat", "sgmc_off"):
            truth = truths[tname]
            per_a, per_c, per_t = [], [], []
            for b in blocks:
                y0, x0, y1, x1 = (
                    int((blk == b).nonzero()[0].min()), int((blk == b).nonzero()[1].min()),
                    int((blk == b).nonzero()[0].max()) + 1, int((blk == b).nonzero()[1].max()) + 1)
                reg = (y0, x0, y1, x1)
                shared = dict(region=reg, shape=fp.shape)
                ra = metric_terms(dots, truth, **shared)
                rc = metric_terms(ctrl, truth, **shared)
                per_a.append(ra["dti"]); per_c.append(rc["dti"])
                if ra["n_truth"]:
                    per_t.append(ra["n_truth"])
            per_a = np.array(per_a); per_c = np.array(per_c)
            d = per_a - per_c
            bs = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(1000)])
            entry[f"delta_vs_random_{tname}"] = {
                "delta": round(float(d.mean()), 4),
                "se": round(float(bs.std(ddof=1)), 4),
                "ci95": [round(float(np.quantile(bs, 0.025)), 4),
                         round(float(np.quantile(bs, 0.975)), 4)],
                "beats_two_se": bool(abs(d.mean()) > 2 * bs.std(ddof=1)),
                "pooled_artifact": round(float(np.mean(per_a)), 4),
                "pooled_random": round(float(np.mean(per_c)), 4),
                "n_blocks": len(blocks),
            }
        rows.append(entry)
        print(f"[cmp] {name:22s} n={n:6d} " + " ".join(
            f"{k}={entry['dti_' + k]:.4f}" for k in truths) + " " + " ".join(
            f"d[{k}]={entry['delta_vs_random_' + k]['delta']:+.4f}"
            for k in ("cat", "sgmc_off")), flush=True)

    payload = {
        "evidence_class": "REGISTRY-MEASUREMENT",
        "not_a_score": True,
        "statement": ("Local proxy instruments only. 'cat' is the organizer's mapped catalogue, which the "
                      "organizer removes from scoring, so it measures proximity to the known network rather "
                      "than discovery. 'sgmc_off' is an independent compilation >300 m off the catalogue and "
                      "is the closer analogue of the private 'new fault' population. No organizer score is "
                      "claimed for any artifact."),
        "alpha": ALPHA, "beta": BETA, "radius_px": 3.0,
        "blocks": len(blocks),
        "truth_sizes": {k: int(v.sum()) for k, v in truths.items()},
        "artifact_comparison": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"[cmp] wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
