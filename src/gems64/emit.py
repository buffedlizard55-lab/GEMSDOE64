"""Emission rules for the GEMS 100 m dot submission (expected-DTI lane).

Everything here operates on **binary dot sets** on the pinned 3730 x 3292 grid
and uses the shared metric module (``gems57.metric``) for the kernel and the
official triangular weights. No private scoring rule is introduced.

The three documented rules
--------------------------
``poisson_disk_pack``
    Priority-ordered greedy packing with a minimum Euclidean separation. This is
    the "dotted ridge" emission geometry measured live by the owner group
    (solid 0.1922 -> d=1.5 0.2477 -> d=2.8 0.2600); the same surface emitted
    densely loses to a thinned one because the denominator charges 0.2 per dot
    while truth-side credit saturates (Sare & Hilley template credit per dot
    saturates at the 3 px kernel area, not at the dot count).

``unique_credit``
    For every dot, the expected truth-side credit that is *lost* if that dot
    alone is removed, under a per-cell truth probability field ``pi``:
    ``u_x = sum_g pi_g * (c_g(S) - c_g(S \\ {x}))`` with ``c`` the shared
    kernel credit. Computed exactly from a 13x13 local window (a dot can only
    ever contribute to cells within 3 px, and only cells within 3 px of ``x``
    can lose credit).

``prune_by_gain``
    Batch-removal of every dot whose single-dot removal raises the plug-in
    expected DTI ``T / (alpha*(T + FP) + beta*K)`` with
    ``T = sum_g pi_g c_g``, ``FP = sum_dots (1 - kpi_x)``, ``K = sum_g pi_g``.
    The acceptance test is the exact two-sided comparison used by
    ``gems57.metric.marginal_accept`` (DTI recomputed before/after, never an
    algebra-only surrogate), evaluated on the plug-in (mean-field) expectations.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from gems57 import metric

__all__ = [
    "poisson_disk_pack",
    "kernel_offsets",
    "dot_side_credit",
    "unique_credit",
    "expected_dti_plugin",
    "prune_by_gain",
    "dots_to_raster",
    "raster_to_dots",
]

R = 3  # kernel radius in pixels (300 m at 100 m cells)
_OFF = None


def kernel_offsets() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Non-zero kernel offsets and weights as (dy, dx, k)."""
    global _OFF
    if _OFF is None:
        dy, dx, k = [], [], []
        for j in range(-R, R + 1):
            for i in range(-R, R + 1):
                w = float(metric.kernel(np.hypot(j, i), metric.RADIUS_PX))
                if w > 0:
                    dy.append(j); dx.append(i); k.append(w)
        _OFF = (np.array(dy, np.int64), np.array(dx, np.int64), np.array(k, np.float64))
    return _OFF


def dots_to_raster(dots: np.ndarray) -> np.ndarray:
    """Binary mask -> float32 raster in [0, 1]."""
    return np.asarray(dots, bool).astype(np.float32)


def raster_to_dots(raster: np.ndarray) -> np.ndarray:
    """Float raster -> positive-support mask."""
    a = np.asarray(raster)
    return np.isfinite(a) & (a > 0)


def poisson_disk_pack(priority: np.ndarray, allowed: np.ndarray, *, min_dist_px: float = 2.8,
                      max_dots: int | None = None) -> np.ndarray:
    """Greedy priority packing with a hard minimum separation (Poisson-disk style).

    ``priority`` is a float field (higher = better); ``allowed`` a bool mask of
    eligible cells. Ties break by row-major order, so the result is
    deterministic. ``min_dist_px`` is a Euclidean distance in cells, matching the
    owner group's measured ``dot_thin`` family.
    """
    p = np.asarray(priority, dtype=np.float64)
    a = np.asarray(allowed, bool)
    if p.shape != a.shape:
        raise ValueError("priority and allowed must share a shape")
    if min_dist_px <= 0:
        raise ValueError("min_dist_px must be positive")
    h, w = p.shape
    order = np.lexsort((np.tile(np.arange(w), h), np.repeat(np.arange(h), w), -p.ravel()))
    flat_ok = a.ravel()[order] & np.isfinite(p.ravel()[order])
    order = order[flat_ok]
    if order.size == 0:
        return np.zeros_like(a)
    dots = np.zeros_like(a)
    # blocked[i, j] = True when a kept dot is within min_dist_px of (i, j)
    blocked = np.zeros_like(a)
    r = int(np.ceil(min_dist_px))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (yy * yy + xx * xx) <= (min_dist_px * min_dist_px)
    n_kept = 0
    for index in order:
        i, j = divmod(int(index), w)
        if blocked[i, j]:
            continue
        dots[i, j] = True
        n_kept += 1
        y0, y1 = max(0, i - r), min(h, i + r + 1)
        x0, x1 = max(0, j - r), min(w, j + r + 1)
        sub = disk[(y0 - (i - r)):(y0 - (i - r)) + (y1 - y0), (x0 - (j - r)):(x0 - (j - r)) + (x1 - x0)]
        blocked[y0:y1, x0:x1] |= sub
        if max_dots is not None and n_kept >= max_dots:
            break
    return dots


def _max_over_offsets(field: np.ndarray, *, allow_zero: bool = True):
    """Per-cell max of ``field`` sampled at the 49 kernel offsets."""
    dy, dx, k = kernel_offsets()
    out = np.zeros(field.shape, dtype=np.float64)
    arg = np.full(field.shape, -1, dtype=np.int16)
    for idx, (j, i, w) in enumerate(zip(dy, dx, k)):
        shifted = np.zeros(field.shape, dtype=np.float64)
        ys0, ys1 = max(0, -j), field.shape[0] - max(0, j)
        xs0, xs1 = max(0, -i), field.shape[1] - max(0, i)
        shifted[ys0:ys1, xs0:xs1] = field[ys0 + j:ys1 + j, xs0 + i:xs1 + i] * w
        upd = shifted > out
        out = np.where(upd, shifted, out)
        arg = np.where(upd, idx, arg)
    if not allow_zero:
        out = np.where(arg >= 0, out, 0.0)
    return out, arg


def dot_side_credit(dots: np.ndarray, pi: np.ndarray) -> np.ndarray:
    """Expected dot-side kernel credit ``kpi_x`` at every dot (0 elsewhere)."""
    d = np.asarray(dots, bool)
    p = np.asarray(pi, dtype=np.float64)
    if d.shape != p.shape:
        raise ValueError("dots and pi must share a shape")
    kpi = np.zeros(d.shape, dtype=np.float64)
    dy, dx, k = kernel_offsets()
    for j, i, w in zip(dy, dx, k):
        shifted = np.zeros(p.shape, dtype=np.float64)
        ys0, ys1 = max(0, j), p.shape[0] + min(0, j)
        xs0, xs1 = max(0, i), p.shape[1] + min(0, i)
        shifted[ys0:ys1, xs0:xs1] = p[ys0 - j:ys1 - j, xs0 - i:xs1 - i] * w
        kpi = np.maximum(kpi, np.where(d, shifted, 0.0))
    return kpi


def truth_side_credit(dots: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Credit per cell from a binary dot set: ``(credit, argmax_offset, second_max)``."""
    kfield = dots.astype(np.float64)
    credit, arg = _max_over_offsets(kfield)
    # second best: redo with the winning offset suppressed
    dy, dx, k = kernel_offsets()
    second = np.zeros(credit.shape)
    for idx, (j, i, w) in enumerate(zip(dy, dx, k)):
        shifted = np.zeros(credit.shape)
        ys0, ys1 = max(0, -j), credit.shape[0] - max(0, j)
        xs0, xs1 = max(0, -i), credit.shape[1] - max(0, i)
        shifted[ys0:ys1, xs0:xs1] = kfield[ys0 + j:ys1 + j, xs0 + i:xs1 + i] * w
        val = np.where(arg == idx, 0.0, shifted)
        second = np.maximum(second, val)
    return credit, arg, second


def unique_credit(dots: np.ndarray, pi: np.ndarray, *, chunk: int = 4096) -> np.ndarray:
    """Expected truth-side credit lost by removing each dot alone (0 if none).

    Pure-local and exact: a dot at ``x`` can only be the unique contributor for
    cells within 3 px of ``x``; the value there is ``k(d) - second_max``.
    """
    d = np.asarray(dots, bool)
    p = np.asarray(pi, dtype=np.float64)
    if d.shape != p.shape:
        raise ValueError("dots and pi must share a shape")
    credit, arg, second = truth_side_credit(d)
    dy, dx, k = kernel_offsets()
    coords = np.argwhere(d)
    out = np.zeros(len(coords), dtype=np.float64)
    h, w = d.shape
    for start in range(0, len(coords), chunk):
        block = coords[start:start + chunk]
        y = block[:, 0][:, None]
        x = block[:, 1][:, None]
        # cells that would lose credit: x + o for each offset o
        gy = y + dy[None, :]
        gx = x + dx[None, :]
        ok = (gy >= 0) & (gy < h) & (gx >= 0) & (gx < w)
        gy_c = np.clip(gy, 0, h - 1)
        gx_c = np.clip(gx, 0, w - 1)
        wgt = k[None, :]
        is_sole = ok & (arg[gy_c, gx_c] == np.arange(len(k))[None, :])
        lo = np.maximum(wgt - second[gy_c, gx_c], 0.0)
        out[start:start + chunk] = (np.where(is_sole, lo * p[gy_c, gx_c], 0.0)).sum(axis=1)
    return out


def expected_dti_plugin(dots: np.ndarray, pi: np.ndarray, *, alpha: float = metric.ALPHA,
                        beta: float = metric.BETA, kpi: np.ndarray | None = None) -> dict:
    """Plug-in expected DTI of a binary dot set under a truth-probability field.

    ``T = sum_g pi_g * credit_g``, ``FP = sum_dots (1 - kpi_x)``,
    ``K = sum_g pi_g``, ``DTI = T / (alpha*(T + FP) + beta*K)``. This is the
    ratio-of-expectations surrogate; the exact finite-sample score is what the
    holdout instrument reports, and the two are never conflated.
    """
    d = np.asarray(dots, bool)
    p = np.asarray(pi, dtype=np.float64)
    if d.shape != p.shape:
        raise ValueError("dots and pi must share a shape")
    credit, _arg, _second = truth_side_credit(d)
    t = float((p * credit).sum())
    if kpi is None:
        kpi = dot_side_credit(d, p)
    fp = float((1.0 - kpi[d]).sum()) if d.any() else 0.0
    kk = float(p.sum())
    den = alpha * (t + fp) + beta * kk
    return dict(T=t, FP=fp, K=kk, n_dots=int(d.sum()), den=den,
                dti=float(t / den) if den > 0 else 0.0)


def prune_by_gain(dots: np.ndarray, pi: np.ndarray, *, alpha: float = metric.ALPHA,
                  beta: float = metric.BETA, max_passes: int = 6,
                  require_positive_truth: bool = True) -> tuple[np.ndarray, list[dict]]:
    """Remove dots whose single removal raises the plug-in expected DTI.

    Each pass evaluates the exact single-removal test for every current dot
    (local credit loss + exact two-sided DTI comparison) and then applies *all*
    improving removals simultaneously, which is why more than one pass can be
    needed. The pass log records the plug-in DTI before/after and the number
    removed, so a non-improving pass is visible rather than silently kept.
    """
    d = np.asarray(dots, bool).copy()
    p = np.asarray(pi, dtype=np.float64)
    log: list[dict] = []
    for _ in range(max_passes):
        state = expected_dti_plugin(d, p, alpha=alpha, beta=beta)
        if not d.any():
            break
        kpi = dot_side_credit(d, p)
        u = unique_credit(d, p)
        t0, den0 = state["T"], state["den"]
        kk = state["K"]
        coords = np.argwhere(d)
        n_emit = d.sum()
        remove = np.zeros(len(coords), dtype=bool)
        for i, (y, x) in enumerate(coords):
            ux = u[i]
            kx = kpi[y, x]
            t1 = t0 + ux
            fp1 = state["FP"] - (1.0 - kx)
            den1 = alpha * (t1 + fp1) + beta * kk
            if den1 <= 0:
                continue
            # exact comparison: does removing this dot raise the plug-in DTI?
            if (t0 / den0) < (t1 / den1):
                if (not require_positive_truth) or ux > 0.0:
                    remove[i] = True
        if not remove.any():
            log.append(dict(pass_index=len(log), dti_before=state["dti"], dti_after=state["dti"],
                            removed=0, n_dots=int(n_emit)))
            break
        keep = ~remove
        new = np.zeros_like(d)
        new[coords[keep, 0], coords[keep, 1]] = True
        after = expected_dti_plugin(new, p, alpha=alpha, beta=beta)
        log.append(dict(pass_index=len(log), dti_before=state["dti"], dti_after=after["dti"],
                        removed=int(remove.sum()), n_dots=int(new.sum())))
        d = new
    else:
        state = expected_dti_plugin(d, p, alpha=alpha, beta=beta)
        log.append(dict(pass_index=len(log), dti_before=state["dti"], dti_after=state["dti"],
                        removed=0, n_dots=int(d.sum()), stopped="max_passes"))
    return d, log


def greedy_surface_coverage(priority: np.ndarray, allowed: np.ndarray, *, max_dots: int,
                            cover_quantile: float = 90.0, radius_px: int = 3,
                            iteration_cap: int = 600_000) -> tuple[np.ndarray, dict]:
    """Greedy maximum-coverage baseline over the *priority surface*, not the truth.

    This is the MCLP-style comparator: targets are the highest-priority cells
    (``cover_quantile``), a dot covers every target within ``radius_px``, and
    candidates are accepted in descending priority order while they add at least
    one uncovered target. It knows nothing about kernel credit, so it is a fair
    "spread the same budget over the strongest cells" baseline.

    The scan is capped at ``iteration_cap`` candidates and the cap is reported,
    so a truncated baseline is visible rather than silently different.
    """
    p = np.asarray(priority, dtype=np.float64)
    a = np.asarray(allowed, bool)
    if p.shape != a.shape:
        raise ValueError("priority and allowed must share a shape")
    if max_dots <= 0:
        raise ValueError("max_dots must be positive")
    finite = a & np.isfinite(p)
    if not finite.any():
        return np.zeros_like(a), dict(candidates=0, accepted=0, iteration_cap_hit=False)
    targets = finite & (p >= np.percentile(p[finite], cover_quantile))
    r = int(radius_px)
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (yy * yy + xx * xx) <= (r * r)
    useful = ndi.binary_dilation(targets, structure=disk) & finite
    order = np.flatnonzero(useful.ravel())
    order = order[np.argsort(-p.ravel()[order], kind="stable")]
    h, w = p.shape
    covered = np.zeros_like(targets)
    dots = np.zeros_like(a)
    accepted = 0
    cap_hit = False
    for n, index in enumerate(order):
        if n >= iteration_cap:
            cap_hit = True
            break
        i, j = divmod(int(index), w)
        y0, y1 = max(0, i - r), min(h, i + r + 1)
        x0, x1 = max(0, j - r), min(w, j + r + 1)
        window_targets = targets[y0:y1, x0:x1]
        if window_targets.any() and not (window_targets & ~covered[y0:y1, x0:x1]).any():
            continue
        dots[i, j] = True
        accepted += 1
        disk_window = disk[(y0 - (i - r)):(y0 - (i - r)) + (y1 - y0),
                           (x0 - (j - r)):(x0 - (j - r)) + (x1 - x0)]
        covered[y0:y1, x0:x1] |= window_targets & disk_window
        if accepted >= max_dots:
            break
    return dots, dict(candidates=int(len(order)), accepted=int(accepted),
                      iteration_cap_hit=bool(cap_hit),
                      targets=int(targets.sum()), covered=int(covered.sum()))
