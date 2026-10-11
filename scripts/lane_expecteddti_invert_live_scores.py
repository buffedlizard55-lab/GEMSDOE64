#!/usr/bin/env python3
"""Experiment 2 — live-anchored inversion of the hidden truth from owner-reported scores.

Why this experiment exists
--------------------------
Every local proxy in this project family has the same defect: its truth *is* the published
catalogue, and the organizers mask catalogue pixels out of scoring (forum thread 11516).  A
proxy whose truth is the catalogue therefore cannot reward the thing the competition pays for.

But the family has accumulated something better than a proxy: a set of rasters whose bytes are on
disk here AND whose live scores were transcribed from submission receipts.  Several of them differ
from each other by exactly ONE controlled operation.  That is a designed experiment, and it can be
inverted for the quantity no local proxy can see -- how the realised kernel credit of an emitted
dot varies with its distance to the published catalogue.

The algebra (identities C2/C3, verified to 1e-16 in Experiment 1)
----------------------------------------------------------------
For a sparse "dotted" emission where each dot is the best cover of its own truth cell, T ~= M, so

    DTI = T / (alpha*S + beta*K),      T = c*S      =>      DTI = c*S / (alpha*S + beta*K)

with c = mean realised credit per emitted dot, S = emitted mass, K = |G| = hidden truth size.
Two live-scored members of one family, with a shared K, give c for each; a parent/child pair that
differ by a known removal gives the credit carried by the removed band:

    c_removed = (c_parent*S_parent - c_child*S_child) / (S_parent - S_child)

and the Expected-DTI-optimal rule (C6) says the removal was correct iff c_removed < alpha*DTI.

Evidence classes used below, per the run-card protocol:
  ORGANIZER-CONFIRMED  a score copied from a submission-page receipt
  OWNER-REPORT         a score transcribed from the owner's ledger / site, not a receipt
  MEASURED-HERE        computed in this session from bytes on disk
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems64.lane_expecteddti.gridext import (  # noqa: E402
    DATA_ROOT, load_catalogue, load_footprint,
)
from gems64.lane_expecteddti.metricext import ALPHA, BETA, EPS, marginal_bar  # noqa: E402

SCRATCH = Path("/home/user/scratch")

# (path, name, live score, evidence class, S_claimed_by_owner_or_None)
# Paths are the bytes actually present on disk in this sandbox; every one is re-read and its
# emitted mass re-measured here rather than trusted from the owner's note.
REGISTRY = [
    (SCRATCH / "GEMSDOE32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
     "h33-2-b2 (flank B=2 prune of the 0.2708 base)", 0.2778, "OWNER-REPORT", 37654),
    (SCRATCH / "GEMSDOE28/docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-allfinite.tif",
     "h27-4-r1-solo-d2-8 (the 0.2708 base)", 0.2708, "OWNER-REPORT", 40199),
    (SCRATCH / "GEMSDOE28/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-allfinite.tif",
     "h36-1-rung30-blind-r1", 0.2710, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE28/docs/downloads/gems28-h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-allfinite.tif",
     "h38-1-hf-euler-r30-r1", 0.2707, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE28/docs/downloads/gems28-h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-allfinite.tif",
     "h32-1-prethin-tip-euler-d2-8", 0.2649, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE32/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
     "dotted-h19-5-d2-8 (44,090-dot incumbent)", 0.2600, "OWNER-REPORT", 44090),
    (SCRATCH / "GEMSDOE29/docs/downloads/gems29-refd28-repro-20261003-1cc7dc534d51-zeros.tif",
     "efd28-repro (reproduction of d2.8)", 0.2600, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE29/docs/downloads/gems29-wormrank-d28-20261003-59dcaf6dd11d-zeros.tif",
     "wormrank-d28", 0.2560, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE28/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-allfinite.tif",
     "topo-gap-closure-t-v2-on-d1-5", 0.2449, "OWNER-REPORT", None),
    (SCRATCH / "GEMSDOE49/docs/downloads/gems49-gate_ortho_w0.25-40k-20261006T213721Z-zeros.tif",
     "gate_ortho_w0.25-40k", 0.2376, "OWNER-REPORT", 40000),
    (SCRATCH / "GEMSDOE29/docs/downloads/gemsdoe29-sgmc-off-catalogue-44k-20261003-c8dcd780e3fd-nan.tif",
     "sgmc-off-catalogue-44k (USGS SGMC beyond 300 m of the catalogue)", 0.0512, "OWNER-REPORT", 44000),
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def measure(path: Path, footprint: np.ndarray, catalogue: np.ndarray) -> dict:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float64)
        meta = dict(width=s.width, height=s.height, count=s.count, dtype=str(s.dtypes[0]),
                    crs=str(s.crs), transform=tuple(s.transform), nodata=s.nodata)
    fin = np.isfinite(a)
    pos = fin & (a > 0) & footprint
    d_cat = distance_transform_edt(~catalogue)
    d = d_cat[pos]
    return dict(
        sha256=sha256(path), bytes=path.stat().st_size, meta=meta,
        n_nan=int((~fin).sum()),
        n_positive_in_footprint=int(pos.sum()),
        total_mass=float(np.nansum(np.where(pos, a, 0.0))),
        min_val=float(np.nanmin(a[fin])) if fin.any() else None,
        max_val=float(np.nanmax(a[fin])) if fin.any() else None,
        n_outside_01=int(np.nansum((a[fin] < 0) | (a[fin] > 1))),
        on_catalogue=int((pos & catalogue).sum()),
        within_1px=int((pos & (d_cat <= 1.0 + 1e-9)).sum()),
        within_2px=int((pos & (d_cat <= 2.0 + 1e-9)).sum()),
        within_3px=int((pos & (d_cat <= 3.0 + 1e-9)).sum()),
        mean_dist_to_catalogue_px=float(d.mean()) if d.size else None,
        median_dist_to_catalogue_px=float(np.median(d)) if d.size else None,
    )


def invert_k(pairs: list[dict]) -> dict:
    """Solve for the hidden truth size K from live-scored rasters, under T ~= M.

    DTI = c*S/(alpha*S + beta*K).  For a single raster c and K are not separable, so the
    inversion is run over a grid of K and reported as a profile: for each K, the implied
    credit-per-dot c for every raster.  A K is admissible only if every implied c lies in
    (0, 1] and the ordering of c matches the ordering of DTI within a family.
    """
    out = {}
    for K in (5000, 6000, 7000, 7905, 9000, 10000, 12000, 12691, 15000, 20000):
        row = {}
        for r in pairs:
            S, dti = r["S"], r["dti"]
            c = dti * (ALPHA * S + BETA * K) / S
            row[r["name"]] = round(float(c), 6)
        out[K] = row
    return out


def main() -> int:
    footprint = load_footprint()
    catalogue = load_catalogue()
    rows = []
    print("=" * 100)
    print("EXPERIMENT 2 — registry measurement + live-anchored inversion")
    print(f"footprint {int(footprint.sum()):,} | catalogue {int(catalogue.sum()):,} | "
          f"scored domain {int((footprint & ~catalogue).sum()):,}")
    print("=" * 100)
    for path, name, dti, ev, S_claim in REGISTRY:
        if not path.exists():
            print(f"MISSING {name}: {path}")
            rows.append(dict(name=name, live_dti=dti, evidence=ev, missing=True))
            continue
        m = measure(path, footprint, catalogue)
        S = m["total_mass"]
        c = dti * (ALPHA * S + BETA * 7905) / S if S else None
        rows.append(dict(name=name, live_dti=dti, evidence=ev, path=str(path),
                         S_claimed=S_claim, S_measured=S,
                         S_claim_matches=bool(S_claim is not None and abs(S - S_claim) < 1),
                         implied_credit_per_dot_at_K7905=c, **m))
        print(f"{dti:.4f} [{ev:12s}] S={S:>9,.0f} (claimed {S_claim}) on_cat={m['on_catalogue']:>6d} "
              f"<=2px={m['within_2px']:>6d} med_d={m['median_dist_to_catalogue_px']:.2f}px "
              f"c@K7905={c:.4f}  {name[:46]}")

    # ---- the parent/child controlled pair: h27-4-solo-d2-8 -> h33-2-b2 --------------------
    by = {r["name"].split(" ")[0]: r for r in rows if not r.get("missing")}
    parent = next((r for r in rows if "h27-4-r1-solo" in r["name"]), None)
    child = next((r for r in rows if "h33-2-b2" in r["name"]), None)
    pair = {}
    if parent and child:
        Sp, Sc = parent["S_measured"], child["S_measured"]
        dS = Sp - Sc
        print("-" * 100)
        print(f"CONTROLLED PAIR: {parent['name']} -> {child['name']}")
        print(f"  S {Sp:,.0f} -> {Sc:,.0f}   removed {dS:,.0f} dots "
              f"(owner note claims 2,545)")
        for K in (6000, 7000, 7905, 9000, 10000, 12691):
            Tp = parent["live_dti"] * (ALPHA * Sp + BETA * K)
            Tc = child["live_dti"] * (ALPHA * Sc + BETA * K)
            if dS > 0:
                c_rem = (Tp - Tc) / dS
                cp, cc = Tp / Sp, Tc / Sc
                bar_p = marginal_bar(parent["live_dti"])
                pair[K] = dict(K=K, T_parent=Tp, T_child=Tc, c_parent=cp, c_child=cc,
                               c_removed_band=c_rem, marginal_bar_at_parent=bar_p,
                               removal_correct_per_rule=bool(c_rem < bar_p),
                               dT=Tp - Tc)
                print(f"  K={K:>6,}: c_parent={cp:.4f} c_child={cc:.4f} "
                      f"c_removed={c_rem:+.4f} bar={bar_p:.4f} "
                      f"removal_correct={c_rem < bar_p}")
    prof = invert_k([dict(name=r["name"].split(" ")[0], S=r["S_measured"], dti=r["live_dti"])
                     for r in rows if not r.get("missing") and r["S_measured"]])
    out = ROOT / "evidence" / "lane_expecteddti_exp2_inversion.json"
    out.write_text(json.dumps(dict(
        footprint=int(footprint.sum()), catalogue=int(catalogue.sum()),
        scored_domain=int((footprint & ~catalogue).sum()),
        registry=[{k: v for k, v in r.items()} for r in rows],
        controlled_pair=pair, credit_per_dot_profile_by_K=prof,
        note="c and K are not separable from a single raster; the profile is a family of "
             "solutions, and only the controlled pair's DIFFERENCE is robust to K.",
    ), indent=1, default=str))
    print("-" * 100)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
