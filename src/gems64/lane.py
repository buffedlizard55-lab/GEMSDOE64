"""GEMSDOE64 lane: native-resolution lidar scarp geometry aggregated to 100 m.

The lane's subject is the **cached lidar scarp stack**, not a new detector on the
100 m grid.  Two independent sibling processing chains produced 100 m aggregates
of 1 m lidar at different working resolutions:

* ``lidar_scarp_features_u8.tif`` -- 12 uint8 bands at a 2 m working resolution
  over 706 3DEP 1 m tiles (10 tiles failed and are recorded as coverage holes),
  channel definitions in ``data/inputs/lidar_scarp_features.json``;
* ``h52_scarp3m_100m.tif`` -- 7 int16 bands at a 3 m working resolution over
  697 tiles, ``gemsdoe48.scarp3m v1``.

Everything below either (a) decodes those aggregates honestly, (b) combines them
into the four quantities the lane asks for -- scarp-pixel/coverage fraction,
SNR-weighted amplitude, structure-tensor orientation coherence, dominant strike,
or (c) applies the cultural-feature mask.  Where a quantity cannot be recovered
from the cached aggregate, the function says so instead of inventing it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FOOTPRINT_SHAPE = (3730, 3292)

# Manifest-driven decode: q = 1 + round(254 * t(clip(x/xmax, 0, 1))), 0 = no lidar
LIDAR_CHANNELS = ("ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
                  "downface_max", "upface_max", "cross_max", "relief", "coh100",
                  "strike", "valid")
XMAX = {"ex_max": 1.5, "ex_mean": 0.3, "step_max": 1.0, "lapneg_max": 0.05,
        "lappos_max": 0.05, "downface_max": 1.0, "upface_max": 1.0,
        "cross_max": 1.0, "relief": 300.0, "coh100": 1.0, "strike": 180.0,
        "valid": 1.0}
TRANSFORM_KIND = {"ex_max": "sqrt", "ex_mean": "sqrt", "step_max": "sqrt",
                  "lapneg_max": "sqrt", "lappos_max": "sqrt", "downface_max": "sqrt",
                  "upface_max": "sqrt", "cross_max": "sqrt", "relief": "sqrt",
                  "coh100": "linear", "strike": "linear", "valid": "linear"}

# h52 3 m product: SCALE_* tags say the stored integers are value * scale.
H52_CHANNELS = ("h_gate07", "h_gate12", "h_all", "sigma_mean", "facing_at",
                "strike_at", "cover")
H52_SCALE = {"h_gate07": 100.0, "h_gate12": 100.0, "h_all": 100.0,
             "sigma_mean": 100.0, "facing_at": 10000.0, "strike_at": 10000.0,
             "cover": 10000.0}


def decode_lidar(q: np.ndarray, channel: str) -> np.ndarray:
    """Invert the manifest quantisation.  0 stays 0 (documented "no lidar")."""
    if channel not in XMAX:
        raise KeyError(f"unknown lidar channel {channel}")
    q = np.asarray(q)
    if q.size and (q.max() > 255 or q.min() < 0):
        raise ValueError("uint8 quantised codes must lie in [0, 255]")
    inner = np.zeros(q.shape, np.float32)
    nz = q > 0
    inner[nz] = np.clip((q[nz] - 1) / 254.0, 0.0, 1.0)
    if TRANSFORM_KIND[channel] == "sqrt":
        x = np.square(inner) * np.float32(XMAX[channel])
    else:
        x = inner * np.float32(XMAX[channel])
    return x


def decode_h52(v: np.ndarray, channel: str, nodata: float = -32768.0) -> tuple[np.ndarray, np.ndarray]:
    """Decode the 3 m product; returns ``(values, covered_mask)``."""
    if channel not in H52_SCALE:
        raise KeyError(f"unknown h52 channel {channel}")
    v = np.asarray(v)
    covered = v != nodata
    out = np.zeros(v.shape, np.float32)
    out[covered] = v[covered].astype(np.float32) / np.float32(H52_SCALE[channel])
    return out, covered


def lidar_covered(valid_q: np.ndarray, *, min_fraction: float = 0.5) -> np.ndarray:
    """Cells the 2 m chain actually saw, per the ``valid`` channel."""
    return decode_lidar(valid_q, "valid") >= float(min_fraction)


def cultural_mask(road_distance_m: np.ndarray, claim_distance_m: np.ndarray | None = None,
                  *, road_buffer_m: float = 100.0, claim_buffer_m: float = 100.0) -> dict:
    """Mask roads / disturbed ground, the cultural features this lane can see.

    Only two cultural layers are available in the cached stack (TIGER roads and
    BLM closed claims).  Canals and field edges are *not* separately masked; the
    receipt records that limitation instead of implying full coverage.
    """
    road = np.asarray(road_distance_m, np.float64)
    if road.shape != FOOTPRINT_SHAPE:
        raise ValueError(f"road distance shape {road.shape} != {FOOTPRINT_SHAPE}")
    # Unknown distance (NaN outside the scored footprint) is treated as masked;
    # those cells are outside the footprint anyway and never eligible.
    near_road = ~(road > float(road_buffer_m))
    out = {"near_road": near_road, "road_buffer_m": road_buffer_m,
           "footprint_finite": np.isfinite(road)}
    if claim_distance_m is not None:
        claim = np.asarray(claim_distance_m, np.float64)
        if claim.shape != road.shape:
            raise ValueError("claim distance grid mismatch")
        near_claim = ~(claim > float(claim_buffer_m))
        out.update(near_claim=near_claim, claim_buffer_m=claim_buffer_m)
        out["masked"] = near_road | near_claim
    else:
        out["masked"] = near_road
    out["canals_and_field_edges_masked"] = False
    out["note"] = ("TIGER roads and BLM closed claims only; canals and field edges are "
                   "not separately mapped in the cached stack")
    return out


def rank01(x: np.ndarray, domain: np.ndarray) -> np.ndarray:
    """Percentile rank of ``x`` inside ``domain`` mapped to [0,1]; 0 elsewhere.

    Ties receive the **average** rank (a flat channel ranks 0.5 everywhere).  An
    index-order tie break would silently bias dot placement toward the last rows
    of the raster, because ``poisson_disk`` consumes the highest scores first.
    """
    x = np.asarray(x)
    out = np.zeros(x.shape, np.float32)
    vals = x[domain]
    if vals.size == 0:
        return out
    uniq, inv, counts = np.unique(vals, return_inverse=True, return_counts=True)
    cum = np.cumsum(counts, dtype=np.float64)
    start = cum - counts
    avg = (start + cum - 1.0) / 2.0                     # 0-based average rank per tie group
    out[domain] = (avg[inv] / max(vals.size - 1, 1)).astype(np.float32)
    return out


def vergence_asymmetry(upface: np.ndarray, downface: np.ndarray) -> np.ndarray:
    """|up - down| / (up + down): 1 for a one-sided (antislope or downface) step.

    A fault scarp is a one-sided step; a channel bank or a terrace riser pair
    presents both faces inside the same 100 m cell and scores near 0.
    """
    up = np.asarray(upface)
    dn = np.asarray(downface)
    total = up + dn
    out = np.zeros(total.shape, np.float32)
    np.divide(np.abs(up - dn), total, out=out, where=total > 0)
    return out


def lane_components(bands: dict, h52: dict) -> dict:
    """The lane's named components, each a 100 m field.

    ``bands`` maps a ``LIDAR_CHANNELS`` name to its decoded field; ``h52`` maps a
    ``H52_CHANNELS`` name to ``(values, covered)``.  Nothing here is a fault
    detector on its own -- the receipt for each experiment says what it measured.
    """
    ex_max = bands["ex_max"]
    ex_mean = bands["ex_mean"]
    step_max = bands["step_max"]
    lapneg = bands["lapneg_max"]
    lappos = bands["lappos_max"]
    coh = np.clip(bands["coh100"], 0.0, 1.0)
    relief = bands["relief"]
    valid = bands["valid"]
    cover = h52["cover"][0]
    gate12 = h52["h_gate12"][0] if "h_gate12" in h52 else np.zeros_like(cover)
    sigma_mean = h52["sigma_mean"][0] if "sigma_mean" in h52 else np.zeros_like(cover)

    # scarp-pixel fraction proxy: mean/max ratio of the 2 m slope excess.  It is
    # 1 when the whole cell shares one steep face and small for a single pixel.
    frac = np.divide(ex_mean, ex_max, out=np.zeros_like(ex_max), where=ex_max > 1e-9)
    # SNR-weighted amplitude: amplitude times how much of the cell supports it
    amp_snr = np.sqrt(ex_max * ex_mean)
    # a young, one-sided scarp: strong step + crest curvature + base concavity
    paired = np.minimum(lapneg, lappos)
    antipaired = np.abs(lapneg - lappos)
    return {
        "amp_max": ex_max,
        "amp_mean": ex_mean,
        "amp_snr": amp_snr,
        "frac": np.clip(frac, 0.0, 1.0),
        "step": step_max,
        "crest": lapneg,
        "base": lappos,
        "paired_curv": paired,
        "antipaired_curv": antipaired,
        "vergence": vergence_asymmetry(bands["upface_max"], bands["downface_max"]),
        "cross": bands["cross_max"],
        "coh": coh,
        "relief": relief,
        "sigma3m": sigma_mean,
        "replicate3m": gate12,
        "cover3m": cover,
        "valid": valid,
    }


def composite(components: dict, domain: np.ndarray, weights: dict | None = None) -> np.ndarray:
    """Rank-combine the lane components into one score on ``domain``.

    Every term is a percentile rank inside the same eligible domain, so the
    combination cannot be dominated by a channel's units.  Terms:
    ``amp`` (SNR-weighted amplitude), ``coh`` (structure-tensor coherence), and
    ``rep`` (independent 3 m replication).  The vergence/asymmetry term is kept
    separate and reported rather than folded in, because the H52 sibling result
    showed terrain class can dominate an amplitude ranking.
    """
    w = {"amp": 0.45, "coh": 0.30, "rep": 0.25} if weights is None else dict(weights)
    total = sum(w.values())
    if not np.isclose(total, 1.0):
        raise ValueError("weights must sum to 1")
    amps = rank01(components["amp_snr"], domain)
    cohs = rank01(components["coh"], domain)
    reps = rank01(components["replicate3m"], domain)
    return (np.float32(w["amp"]) * amps + np.float32(w["coh"]) * cohs
            + np.float32(w["rep"]) * reps).astype(np.float32)


def poisson_disk(score: np.ndarray, eligible: np.ndarray, n: int, radius_px: float,
                 *, seed: int = 64) -> np.ndarray:
    """Greedy blue-noise selection: descending score with a minimum spacing.

    Ties are broken by a fixed-seed jitter so the result is deterministic but not
    biased to raster order.  If the radius cannot be honoured the caller is told
    with the achieved minimum spacing instead of silently clumping.
    """
    s = np.asarray(score, np.float64)
    ok = np.asarray(eligible, bool)
    if s.shape != ok.shape:
        raise ValueError("score/eligible shape mismatch")
    rng = np.random.default_rng(seed)
    r = float(radius_px)
    r2 = r * r
    dots = np.zeros(s.shape, bool)
    occupied = np.zeros(s.shape, bool)          # cells inside the exclusion radius
    # Only eligible cells are ranked: a 1-2 M shortlist instead of the full grid.
    flat_eligible = np.flatnonzero(ok)
    jitter = rng.random(flat_eligible.size) * 1e-6   # breaks exact rank ties only
    rank = np.argsort(-(s.ravel()[flat_eligible] + jitter), kind="stable")
    order = flat_eligible[rank]
    taken = 0
    for flat in order:
        if taken >= n:
            break
        y, x = np.unravel_index(flat, s.shape)
        if not ok[y, x] or occupied[y, x]:
            continue
        dots[y, x] = True
        taken += 1
        y0, y1 = max(0, y - int(np.ceil(r))), min(s.shape[0], y + int(np.ceil(r)) + 1)
        x0, x1 = max(0, x - int(np.ceil(r))), min(s.shape[1], x + int(np.ceil(r)) + 1)
        sub = occupied[y0:y1, x0:x1]
        yy, xx = np.mgrid[y0:y1, x0:x1]
        sub |= (yy - y) ** 2 + (xx - x) ** 2 <= r2
    return dots


def load_channel_manifest(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
