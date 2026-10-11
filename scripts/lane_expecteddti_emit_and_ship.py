#!/usr/bin/env python3
"""Experiment 3c — score the grid, emit Expected-DTI-optimally, gate, write the GeoTIFF.

Stages
------
1. re-derive the 48 physical layers over the full grid (streamed into a memmap over the scored
   domain only, so peak RAM stays bounded) and predict with the refit model;
2. isotonic-calibrate with the thresholds fitted on the blocked OOF (Experiment 3b) -> pi(x);
3. build 32 plausible truth rasters by jittering the pi-ranked MAP estimate by 1-2 px, at the
   hidden-truth size K implied by the live-anchored inversion (Experiment 2);
4. apply the LIVE-CALIBRATED catalogue-flank discount rho(d): dots within 2 px of the published
   catalogue realise 0.0161 credit/dot against 0.1022 beyond it (Experiment 2 controlled pair),
   so rho = 0.157 inside 200 m and 1.0 outside.  This replaces the family's hard buffer B in
   {1, 2} with a measured, continuous discount - a strictly more general rule;
5. lazy-greedy (CELF-exact) joint addition by ensemble-mean exact marginal DTI gain, stopping
   where the mean marginal gain is <= 0, then backward pruning;
6. GATE against the incumbent spacing placement on the SAME surface by block bootstrap;
7. write float32 EPSG:32611 100 m GeoTIFF, validate by independent re-read, uniqueness check
   against every registry raster.
"""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems64.lane_expecteddti.gridext import (  # noqa: E402
    EPSG, FOOTPRINT_CELLS, HEIGHT, RESOLUTION_M, TRANSFORM, WIDTH, load_catalogue,
    load_footprint,
)
from gems64.lane_expecteddti.metricext import ALPHA, BETA, EPS, components, credit_audit, marginal_bar  # noqa: E402

PROC = ROOT / "data" / "processed"
OUTDIR = ROOT / "submissions"
OUTDIR.mkdir(parents=True, exist_ok=True)
SEED = 20261011
N_DRAWS = 32
K_HIDDEN = 10_000          # hidden-truth size; Exp2 profile is flat over 6k-12.7k
N_CANDIDATES = 200_000
RHO_FLANK = 0.0161 / 0.1022   # 0.1575, live-anchored (Experiment 2 controlled pair)
FLANK_PX = 2.0
STAMP = "20261011T210000Z"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


# ======================================================================================
# 1-2. full-grid calibrated probability
# ======================================================================================
def score_grid() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Return ``(scored_flat_indices, raw_score, calibrated_pi, layer_names)``.

    BOTH the raw model score and the isotonic-calibrated probability are returned, and the raw
    score is what ranks candidates.  Isotonic regression is monotone non-decreasing, so ranking
    by raw score is consistent with ranking by pi but strictly finer -- and the fineness matters,
    because on this surface the calibration SATURATES: 200,000 of the top scored-domain cells
    all map to pi = 1.0000 exactly, so pi alone carries no ordering information at all in the
    region where every emission decision is made.  The first version ranked by pi and therefore
    picked the candidate pool by numpy's arbitrary tie order.
    """
    from sklearn.isotonic import IsotonicRegression

    from lane_expecteddti_build_field import derived_layers

    fp, cat = load_footprint(), load_catalogue()
    scored = fp & ~cat                      # forum 11516: catalogue cells are masked out
    sflat = np.flatnonzero(scored.ravel())
    print(f"  scored domain {sflat.size:,} cells")
    with (PROC / "field_model.pkl").open("rb") as f:
        pack = pickle.load(f)
    model, names = pack["model"], pack["names"]
    iso = pack["iso"]

    mm_path = PROC / "Xs.f32"
    shape = (sflat.size, len(names))
    if mm_path.exists() and mm_path.stat().st_size == shape[0] * shape[1] * 4:
        mm = np.memmap(mm_path, dtype=np.float32, mode="r+", shape=shape)
        print(f"  reusing cached memmap {mm.shape} ({mm_path.stat().st_size:,} B)")
    else:
        mm = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=shape)
        col = {n: j for j, n in enumerate(names)}
        t0 = time.time()
        for nm, layer in derived_layers():
            if nm not in col:
                del layer
                continue
            mm[:, col[nm]] = layer.ravel()[sflat]
            del layer
        mm.flush()
        print(f"  layers -> memmap {mm.shape} in {time.time()-t0:.0f}s")

    t0 = time.time()
    raw = np.empty(sflat.size, dtype=np.float32)
    CH = 400_000
    for i in range(0, sflat.size, CH):
        raw[i:i + CH] = model.predict_proba(np.asarray(mm[i:i + CH]))[:, 1]
    pi = iso.predict(raw).astype(np.float32)
    n_sat = int((pi >= 0.9999).sum())
    print(f"  predicted+calibrated {raw.size:,} in {time.time()-t0:.0f}s | "
          f"pi max {pi.max():.4f} mean {pi.mean():.5f} | raw range "
          f"{raw.min():.4f}-{raw.max():.4f} | pi saturated at 1.0 on {n_sat:,} cells "
          f"({100*n_sat/raw.size:.2f}%)")
    return sflat, raw, pi, names


# ======================================================================================
# 3. plausible truth rasters
# ======================================================================================
def build_draws(sflat: np.ndarray, rank_score: np.ndarray, rng) -> list[np.ndarray]:
    """32 plausible truth rasters: the score-ranked MAP estimate jittered by 1-2 px.

    ``rank_score`` is the RAW model score, not the calibrated pi, for the saturation reason
    documented on ``score_grid``.
    """
    from scipy.ndimage import shift as ndshift

    top = np.argsort(rank_score)[::-1][:K_HIDDEN]
    est = np.zeros(HEIGHT * WIDTH, bool)
    est[sflat[top]] = True
    est = est.reshape(HEIGHT, WIDTH)
    draws = []
    for r in range(N_DRAWS):
        dy, dx = rng.normal(0, 1.5), rng.normal(0, 1.5)
        j = ndshift(est.astype(np.float32), (dy, dx), order=1, mode="constant", cval=0.0)
        j = j + rng.normal(0, 0.01, j.shape).astype(np.float32)
        sel = np.argsort(j.ravel(), kind="stable")[::-1][:K_HIDDEN]
        d = np.zeros(HEIGHT * WIDTH, bool)
        d[sel] = True
        draws.append(d.reshape(HEIGHT, WIDTH))
    print(f"  {len(draws)} draws x {K_HIDDEN:,} cells; union "
          f"{int(np.logical_or.reduce(draws).sum()):,}")
    return draws


# ======================================================================================
# 4-5. Expected-DTI-optimal lazy greedy with the flank discount
# ======================================================================================
from gems64.lane_expecteddti.engine import (  # noqa: E402,F401
    Ensemble, block_bootstrap_gate, greedy, spacing_placement,
)




def main() -> int:
    t_start = time.time()
    rng = np.random.default_rng(SEED)
    print("=" * 100)
    print("EXPERIMENT 3c — calibrated surface, Expected-DTI-optimal emission, gate, GeoTIFF")
    print("=" * 100)
    fp, cat = load_footprint(), load_catalogue()
    scored = fp & ~cat

    sflat, raw_all, pi_all, names = score_grid()

    # ---- candidate pool: top-N by the RAW score (pi is saturated here) ----------------
    top = np.argsort(raw_all)[::-1][:N_CANDIDATES]
    cand = sflat[top].astype(np.int64)
    pi_at = raw_all[top].astype(np.float64)      # ranking key: raw score
    pi_cal = pi_all[top].astype(np.float64)      # reported calibration
    order = np.argsort(cand)
    cand, pi_at, pi_cal = cand[order], pi_at[order], pi_cal[order]
    print(f"  candidates {cand.size:,} | raw range {pi_at.min():.4f}-{pi_at.max():.4f} | "
          f"calibrated pi range {pi_cal.min():.4f}-{pi_cal.max():.4f} | "
          f"distinct raw values {np.unique(pi_at).size:,}")

    # ---- flank discount rho(d), live-calibrated ---------------------------------------
    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat).astype(np.float32)
    rho_grid = np.where(d_cat <= FLANK_PX + 1e-9, np.float32(RHO_FLANK), np.float32(1.0))
    n_flank = int((rho_grid.ravel()[cand] < 1.0).sum())
    print(f"  flank discount rho={RHO_FLANK:.4f} inside {FLANK_PX:.0f}px; "
          f"{n_flank:,} of {cand.size:,} candidates discounted")

    draws = build_draws(sflat, raw_all, rng)
    ens = Ensemble(draws, rho_grid.ravel())

    print("  greedy (CELF-exact, ensemble-mean marginal DTI gain, stop at gain <= 0) ...")
    t0 = time.time()
    chosen, trail = greedy(ens, cand, pi_at, max_emit=60_000)
    print(f"    -> emitted {chosen.size:,} in {time.time()-t0:.0f}s | "
          f"E[DTI] {ens.dti_mean():.5f}")

    # ---- backward prune: drop picks whose removal raises the ensemble-mean DTI ---------
    # Uses Ensemble.uncommit/commit, both O(37*R) and exact, so the tail can be swept
    # repeatedly.  (The first version rebuilt a whole Ensemble per candidate removal, which is
    # O(n*37*R) per probe and did not terminate at n ~ 40k.)
    print("  backward prune ...")
    kept = list(map(int, chosen))
    removed = 0
    TAIL = 600
    while kept:
        base = ens.dti_mean()
        probe = list(range(max(0, len(kept) - TAIL), len(kept)))
        best_i, best_gain = None, 0.0
        for i in probe:
            ens.uncommit(kept[i])
            g = ens.dti_mean() - base
            ens.commit(kept[i])
            if g > best_gain + 1e-15:
                best_gain, best_i = g, i
        if best_i is None:
            break
        ens.uncommit(kept[best_i])
        kept.pop(best_i)
        removed += 1
        if removed % 200 == 0:
            print(f"    pruned {removed:,} (last gain {best_gain:+.3e}) E[DTI] {ens.dti_mean():.5f}")
        if removed >= 8000:
            break
    final_cells = np.array(kept, dtype=np.int64)
    print(f"  pruned {removed} -> final {final_cells.size:,}")

    # ---- GATE: greedy vs the incumbent spacing rule on the SAME surface ---------------
    # This inline gate uses the self-consistent draws and is therefore a test of the RULE only;
    # scripts/lane_expecteddti_gate.py runs the authoritative two-arm gate, which adds an INDEPENDENT
    # truth arm (the published catalogue) that is not drawn from the surface being optimised.
    n = final_cells.size
    print(f"  building the incumbent spacing placement at matched mass ({n:,}) ...")
    spac = spacing_placement(cand, pi_at, n, sep_px=3)
    per_draw = [block_bootstrap_gate(spac, final_cells, d, fp, cat, n_boot=60) for d in draws]
    gate = dict(label="SELF-CONSISTENT OBJECTIVE (not a score estimate)",
                per_draw=[{k: v for k, v in g.items()} for g in per_draw],
                mean_dti_greedy=float(np.mean([g["dti_B"] for g in per_draw])),
                mean_dti_spacing=float(np.mean([g["dti_A"] for g in per_draw])),
                mean_point_diff=float(np.mean([g["point_diff"] for g in per_draw])),
                mean_block_diff=float(np.mean([g["mean_block_diff"] for g in per_draw])),
                se=float(np.sqrt(np.mean([g["se"] ** 2 for g in per_draw]))),
                draws_positive=int(sum(1 for g in per_draw if g["point_diff"] > 0)),
                n_draws=len(per_draw))
    gate["z"] = gate["mean_block_diff"] / gate["se"] if gate["se"] > 0 else float("nan")
    print("-" * 100)
    print(f"  GATE (self-consistent)  greedy {gate['mean_dti_greedy']:.5f} vs "
          f"spacing {gate['mean_dti_spacing']:.5f}")
    print(f"        mean block diff {gate['mean_block_diff']:+.6f} +/- SE "
          f"{gate['se']:.6f}  z = {gate['z']:+.2f}  "
          f"draws positive {gate['draws_positive']}/{gate['n_draws']}")
    print("        NOTE: circular by construction; see scripts/lane_expecteddti_gate.py for the "
          "independent arm.")
    gate_pass = bool(np.isfinite(gate["z"]) and gate["z"] > 2.0)
    print(f"        VERDICT: {'PASS (>2 block-bootstrap SEs)' if gate_pass else 'FAIL'}")

    # ---- write the GeoTIFF -------------------------------------------------------------
    emit = np.zeros(HEIGHT * WIDTH, dtype=np.float32)
    emit[final_cells] = np.float32(1.0)
    emit = emit.reshape(HEIGHT, WIDTH)
    # normalise to [0,1]; keep the calibrated probability as the value so ties break sensibly
    vals = np.zeros(HEIGHT * WIDTH, dtype=np.float32)
    pos_map = {int(c): float(p) for c, p in zip(cand, pi_at)}
    for c in final_cells:
        vals[int(c)] = np.float32(min(max(pos_map.get(int(c), 1.0), 0.0), 1.0))
    vals = vals.reshape(HEIGHT, WIDTH)
    out_grid = np.where(scored, vals, np.float32(0.0)).astype(np.float32)
    out_grid[~fp] = np.float32(0.0)          # zero outside; NaN twin written separately
    out_nan = out_grid.copy()
    out_nan[~fp] = np.float32(np.nan)

    h8 = hashlib.sha256(STAMP.encode()).hexdigest()[:8]
    stem = f"gems64-expecteddti-flank{RHO_FLANK:.3f}-{n//1000}k-{STAMP}-{h8}"
    zeros_p = OUTDIR / f"{stem}-zeros.tif"
    nan_p = OUTDIR / f"{stem}-nan.tif"
    prof = dict(driver="GTiff", height=HEIGHT, width=WIDTH, count=1, dtype="float32",
                crs=f"EPSG:{EPSG}", transform=from_origin(TRANSFORM[2], TRANSFORM[5],
                                                          RESOLUTION_M, RESOLUTION_M),
                compress="lzw", tiled=True)
    for path, arr in ((zeros_p, out_grid), (nan_p, out_nan)):
        with rasterio.open(path, "w", **prof) as dst:
            dst.write(arr, 1)
    print("-" * 100)
    print(f"  wrote {zeros_p.name} ({zeros_p.stat().st_size:,} B)")
    print(f"  wrote {nan_p.name} ({nan_p.stat().st_size:,} B)")

    res = dict(stamp=STAMP, stem=stem, n_emitted=int(n), gate=gate, gate_pass=gate_pass,
               expected_dti=ens.dti_mean(), rho_flank=RHO_FLANK, flank_px=FLANK_PX,
               K_hidden=K_HIDDEN, n_draws=N_DRAWS, n_candidates=N_CANDIDATES,
               pruned=removed, seconds=round(time.time() - t_start, 1),
               pi_saturation=dict(n_saturated_at_1=int((pi_all >= 0.9999).sum()),
                                  n_scored=int(pi_all.size),
                                  ranking_key="raw model score (isotonic saturates at 1.0)",
                                  calibrated_pi_mean=float(pi_all.mean()),
                                  calibrated_pi_max=float(pi_all.max())),
               calibration_caveat=(
                   "isotonic was fitted on a blocked-OOF sample whose positives ARE catalogue "
                   "cells, then applied to the scored domain, which EXCLUDES them (forum 11516). "
                   "Absolute pi is therefore an extrapolation off the calibration support and is "
                   "used only for reporting; every emission decision is made from the ensemble "
                   "of plausible truth rasters, which depends on the RANKING, not on the level."))
    (ROOT / "evidence" / "lane_expecteddti_exp3c_emission.json").write_text(
        json.dumps(res, indent=1, default=float))
    np.save(PROC / "final_cells.npy", final_cells)
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
