#!/usr/bin/env python
"""Stage 1: build the candidate lattice, the lane feature stack and a blocked-CV field.

Design notes
------------
* The competition metric rewards *coverage* of ground-truth pixels with a triangular
  kernel of radius 3 px, so what matters is a well-ranked surface plus a placement
  rule, not a dense probability map.  We therefore predict on a stride-2 candidate
  lattice inside the scored footprint (1.29 M of 5.17 M cells): a dot that lands one
  cell away from the optimum loses only 1/3 of its kernel weight, and the lattice
  keeps the memory ceiling at a few hundred MB on a 4 GB box.
* Every feature is computed at the native 100 m cell and, for the lane's scarp
  channels, also averaged over the 3 x 3 neighbourhood, because a fault scarp that
  falls one cell off-centre must not vanish from the candidate's own feature vector.
* Labels for the field: the given fault catalogue (positives).  Ground truth for the
  competition is a *different* compilation, so the field is additionally regulated by
  a population-matched surrogate (independent-compilation faults more than 300 m from
  the catalogue) in stage 2.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
STRIDE = 2
SEED = 640064


def log(msg: str) -> None:
    print(msg, flush=True)


def read_band(path: Path, band: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def sanitize(a: np.ndarray, nodata) -> np.ndarray:
    """Return float32 with nodata/NaN/inf replaced by 0 and the extremes clipped."""
    b = a.astype(np.float32, copy=True)
    if nodata is not None and np.isfinite(nodata):
        b[b == nodata] = 0.0
    bad = ~np.isfinite(b)
    if bad.any():
        b[bad] = 0.0
    lo, hi = np.percentile(b, [0.01, 99.99])
    if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
        np.clip(b, lo, hi, out=b)
    return b


def main() -> int:
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- grid
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as s:
        sample = s.read(1)
        profile = dict(shape=s.shape, crs=s.crs, transform=s.transform)
    fp = np.isfinite(sample)
    del sample
    with rasterio.open(ROOT / "data/official/labels.tif") as s:
        cat = s.read(1) > 0
    active = fp & ~cat
    dcat = ndi.distance_transform_edt(~cat).astype(np.float32)
    log(f"[grid] shape={profile['shape']} footprint={int(fp.sum())} catalogue={int(cat.sum())}")

    # ------------------------------------------------------- candidate lattice
    yy, xx = np.mgrid[0:profile["shape"][0], 0:profile["shape"][1]]
    lat = fp & (yy % STRIDE == 0) & (xx % STRIDE == 0)
    del yy, xx
    cand = np.flatnonzero(lat.ravel())
    lat_pos = np.zeros(lat.size, np.int32)
    lat_pos[cand] = np.arange(cand.size, dtype=np.int32)
    log(f"[lattice] candidates={cand.size} ({100*cand.size/int(fp.sum()):.1f}% of footprint)")

    feats, names = [], []

    def add(name: str, arr: np.ndarray, scale: int = 0) -> None:
        """scale 0 = native value at the candidate, >0 = uniform mean over that window."""
        if scale:
            arr = ndi.uniform_filter(arr, size=scale, mode="nearest")
        feats.append(arr.ravel()[cand].astype(np.float32))
        names.append(name if not scale else f"{name}_m{scale}")

    # ---- 1. official GeoDAWN numerical feature stack (19 bands, the organizer's own)
    tpath = ROOT / "data/official/training_features.tif"
    with rasterio.open(tpath) as tf:
        tdesc = [d.split(" - ")[0].strip().replace(" ", "_") for d in tf.descriptions]
        nodata = tf.nodata
        for i in range(tf.count):
            raw = tf.read(i + 1)
            b = sanitize(raw, nodata)
            del raw
            add(f"of_{tdesc[i]}", b)
            add(f"of_{tdesc[i]}", b, 3)
            del b
            gc.collect()
    log(f"[feat] official stack done ({len(names)} features) t={time.time()-t0:.0f}s")

    # ---- 2. lane core: 1 m lidar scarp aggregates (12 bands)
    with rasterio.open(ROOT / "data/bridge/lidar_scarp_features_u8.tif") as s:
        ldesc = list(s.descriptions)
        lid = s.read()
    for i, d in enumerate(ldesc):
        b = lid[i].astype(np.float32)
        add(f"li_{d}", b)
        if d not in ("valid", "strike"):
            add(f"li_{d}", b, 3)
            add(f"li_{d}", b, 7)
    del lid
    gc.collect()
    log(f"[feat] lidar scarp done ({len(names)} features) t={time.time()-t0:.0f}s")

    # ---- 3. 10 m topography derivatives (9 bands)
    with rasterio.open(ROOT / "data/bridge/topo_10m_derived_100m_u8.tif") as s:
        pdesc = list(s.descriptions)
        topo = s.read()
    for i, d in enumerate(pdesc):
        b = topo[i].astype(np.float32)
        add(f"tp_{d}", b)
        add(f"tp_{d}", b, 3)
    del topo
    gc.collect()

    # ---- 4. chi / knickpoint products (u8 flags + i16 magnitudes)
    with rasterio.open(ROOT / "data/bridge/dem10_chi_100m_u8.tif") as s:
        cdesc = list(s.descriptions)
        chi8 = s.read()
    for i, d in enumerate(cdesc):
        b = chi8[i].astype(np.float32)
        add(f"ch_{d}", b)
        add(f"ch_{d}", b, 3)
    del chi8
    gc.collect()
    with rasterio.open(ROOT / "data/bridge/dem10_chi_100m_i16.tif") as s:
        idesc = list(s.descriptions)
        chi16 = s.read()
    for i, d in enumerate(idesc):
        raw = chi16[i].astype(np.float32)
        raw[raw <= -32768] = 0.0
        np.clip(raw, -1e4, 1e4, out=raw)
        add(f"ci_{d}", raw)
        add(f"ci_{d}", raw, 3)
    del chi16
    gc.collect()

    # ---- 5. geothermal / structural context layers
    # NOTE: derived_sgmc_faults_* is deliberately NOT a feature.  It is derived from the
    # same compilation that supplies the stage-2 surrogate label, so including it makes a
    # held-out AUC of 0.9985 - a textbook leakage canary (see evidence/lane64_canary.json).
    for path, tag in (("data/bridge/geodawn_rad_u8.tif", "rad"),
                      ("data/bridge/geodawn_extensions_u8.tif", "ext")):
        p = ROOT / path
        if not p.exists():
            continue
        with rasterio.open(p) as s:
            desc = list(s.descriptions)
            arr = s.read()
        for i, d in enumerate(desc):
            b = arr[i].astype(np.float32)
            add(f"{tag}_{d}", b)
            add(f"{tag}_{d}", b, 3)
        del arr
        gc.collect()

    X = np.stack(feats, axis=1)
    del feats
    gc.collect()
    log(f"[feat] matrix {X.shape} {X.nbytes/1e6:.0f} MB t={time.time()-t0:.0f}s")

    # ---- distance-to-catalogue is a *placement* feature, never a field input:
    #      truth for the competition is by construction absent on the catalogue, so
    #      "distance to the visible map" would be a leakage-shaped shortcut.
    payload = dict(X=X, cand=cand, lat=lat, fp=fp, cat=cat, active=active,
                   dcat=dcat, names=np.array(names), shape=np.array(profile["shape"]))
    np.savez_compressed(WORK / "stage1_features.npz", **payload)
    (WORK / "stage1_names.json").write_text(json.dumps(names, indent=1))
    log(f"[stage1] saved {WORK/'stage1_features.npz'} t={time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
