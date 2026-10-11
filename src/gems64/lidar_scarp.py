"""Native-resolution lidar scarp channels: scarp matching + ridge/valley structure.

Lane (verbatim from the task statement)
---------------------------------------
"Native-resolution lidar scarp channels. The 100 m stack discards the subtle
scarps visible in the 1 m GeoDAWN lidar, which plausibly is evidence geologists
use to add faults. On high-prior tiles first, compute two sets of features.
(i) scarplet template matching (Sare & Hilley, JOSS 2018,
doi:10.21105/joss.01066), which returns amplitude, relative age, orientation and
SNR from a GeoTIFF DEM, extended with slope-aware scarp templates (AGU 2015
poster T31A-2838, tested in Surprise Valley). (ii) Steger sub-pixel ridge/valley
lines (IEEE TPAMI 20(2):113-125, 1998) and Frangi multiscale Hessian line
measures (MICCAI 1998, LNCS 1496:130-137) at 2-20 m scales on a slope-detrended
surface. Aggregate to 100 m cells as scarp-pixel fraction, SNR-weighted
amplitude, structure-tensor orientation coherence and dominant strike."

What this module is, and is not
-------------------------------
It is a **complete, unit-tested implementation of the two feature sets and the
aggregation rule, parameterised in metres**, so that it runs unchanged on a 1 m
DEM (lane target) or on any coarser grid (fallback). It is *not* a claim that the
published run used 1 m data: the competition's `1m_DEM_links.csv` points at
external hosts that this sandbox cannot reach (recorded in
``evidence/access_blockers.json``), so the published candidate was computed on
the finest **locally reachable** lidar-derived layer (the owner-CI 100 m
aggregate of 706 USGS 3DEP 1 m tiles). Every receipt states which grid was used.

Scientific basis (each with a citable source; no invented method)
----------------------------------------------------------------
* scarplet: Sare, R. & Hilley, G. (2018), "scarplet: A Python package for
  topographic edge/object matching", JOSS 3(22), 266, doi:10.21105/joss.01066.
  A scarp is matched with a template family; the fit returns amplitude, width,
  offset, a *relative-age* proxy (offset/width style freshness) and an SNR.
* Slope-aware extension: AGU Fall Meeting 2015, abstract/poster T31A-2838
  ("testing scarp degradation models in Surprise Valley", cited by the task
  statement). Here the extension is explicit: the profile model fitted to every
  candidate scarp carries a **local-slope term** (``c * t``) in addition to the
  step and offset, i.e. the template is fitted to the *slope-detrended* surface
  and the residual regional gradient is solved for, not assumed zero.
* Steger (1998), "An unbiased detector of curvilinear structures",
  IEEE TPAMI 20(2):113-125: sub-pixel curvilinear structures from the
  eigenvalues/eigenvectors of the Hessian, with the sub-pixel offset along the
  direction of the strongest curvature.
* Frangi et al. (1998), "Multiscale vessel enhancement filtering",
  MICCAI, LNCS 1496:130-137: multi-scale Hessian line/vessel measure from the
  eigenvalue ratio and the Frobenius norm, maximised over scales.
* Structure tensor orientation coherence and dominant strike: the standard
  gradient-structure-tensor formulation (e.g. Jahne 1993; Weickert 1998). The
  strike returned by :func:`structure_tensor` is the orientation of the
  *coherent* gradient alignment, mapped into [0, 180) degrees as a
  line orientation.

Conventions
-----------
* Arrays are float64 (or float32) 2-D, **row index increases southwards** for
  the competition grid (north-up GeoTIFF), so azimuth/strike angles are reported
  in map convention: 0 deg = east-west line, 90 deg = north-south line.
* ``sigma`` and ``width`` arguments are in **pixels** at the *input grid*; helper
  :func:`scales_px` converts a metre scale to pixels so a caller can express the
  2-20 m lane scales on a 1 m DEM (``scales_px(2, 20, 1.0)`` -> 2..20 px) or on a
  100 m grid (where the same request rounds to the smallest resolvable scale).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

__all__ = [
    "scales_px",
    "slope_detrend",
    "hessian_eigen",
    "steger_ridge",
    "frangi_vesselness",
    "scarplet_step_fit",
    "structure_tensor",
    "structure_strike",
    "aggregate_to_grid",
    "line_consistency",
]

EPS = 1e-12


def scales_px(scales_m, pixel_m: float, *, minimum: float = 1.0) -> np.ndarray:
    """Metre scales -> pixel scales, floored at ``minimum`` px and rounded.

    Rounding is *disclosed*: on a 100 m grid a request for 2-20 m scales cannot
    be honoured physically and is reported as the 1-2 px that the grid can hold.
    """
    if pixel_m <= 0:
        raise ValueError("pixel_m must be positive")
    s = np.asarray(scales_m, dtype=float) / float(pixel_m)
    return np.unique(np.clip(np.round(s), minimum, None)).astype(float)


def slope_detrend(surface: np.ndarray, sigma: float = 3.0, *, finite_mask=None) -> np.ndarray:
    """Remove the smoothly varying regional surface, keeping scarp-scale relief.

    The lane specifies a *slope-detrended* surface. This is the standard
    high-pass formulation (surface minus its Gaussian-smoothed self); NaNs are
    handled by normalised convolution so that voids do not bleed into the
    result as zeros.
    """
    src = np.asarray(surface)
    work_dtype = np.float64 if src.dtype == np.float64 else np.float32
    s = src.astype(work_dtype, copy=False)
    finite = np.isfinite(s) if finite_mask is None else (np.isfinite(s) & np.asarray(finite_mask, bool))
    if not finite.any():
        raise ValueError("no finite cells in the surface")
    filled = np.where(finite, s, work_dtype(0.0))
    w = ndi.gaussian_filter(finite.astype(work_dtype), sigma, mode="nearest")
    sm = ndi.gaussian_filter(filled, sigma, mode="nearest") / np.maximum(w, work_dtype(EPS))
    out = s - sm
    return np.where(finite, out, np.nan)


def hessian_eigen(surface: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Gaussian-smoothed Hessian eigen-decomposition.

    Returns ``(l1, l2, ny, nx)`` where ``l1`` is the eigenvalue of largest
    magnitude, ``l2`` the other one, and ``(ny, nx)`` the eigenvector of ``l1``
    (the direction *across* a ridge/valley line). NaNs are propagated.
    """
    # float32 throughout: at the 12.3 M-cell competition grid a float64 Hessian
    # stack alone is ~600 MB transient per scale, which does not fit the sandbox.
    # The surface is robustly standardised first: un-normalised detrended
    # elevation carries ~1e3 amplitudes whose second derivatives overflow fp32.
    src = np.asarray(surface, dtype=np.float64)
    fin0 = np.isfinite(src)
    if fin0.any():
        med = float(np.median(src[fin0]))
        scale = float(np.percentile(np.abs(src[fin0] - med), 84.0)) or 1.0
    else:
        med, scale = 0.0, 1.0
    s = ((src - med) / scale).astype(np.float32)
    del src
    finite = np.isfinite(s)
    fill = np.where(finite, s, np.float32(0.0))
    w = ndi.gaussian_filter(finite.astype(np.float32), sigma, mode="nearest")
    # normalised-convolution (scale-space) second derivatives
    hyy = ndi.gaussian_filter(fill, sigma, order=(2, 0), mode="nearest") / np.maximum(w, EPS)
    hxx = ndi.gaussian_filter(fill, sigma, order=(0, 2), mode="nearest") / np.maximum(w, EPS)
    hxy = ndi.gaussian_filter(fill, sigma, order=(1, 1), mode="nearest") / np.maximum(w, EPS)
    trace = hyy + hxx
    det = hyy * hxx - hxy * hxy
    disc = np.sqrt(np.maximum(trace * trace / 4.0 - det, 0.0))
    l1 = trace / 2.0 + disc
    l2 = trace / 2.0 - disc
    ny = hxy
    nx = l1 - hyy
    norm = np.hypot(ny, nx)
    tiny = norm < 1e-12
    ny = np.where(tiny, 1.0, ny)
    nx = np.where(tiny, 0.0, nx)
    norm = np.where(tiny, 1.0, norm)
    ny, nx = ny / norm, nx / norm
    bad = ~finite | (w < 0.5)
    l1 = np.where(bad, np.nan, l1)
    l2 = np.where(bad, np.nan, l2)
    ny = np.where(bad, np.nan, ny)
    nx = np.where(bad, np.nan, nx)
    return l1, l2, ny, nx


def steger_ridge(surface: np.ndarray, sigma: float, *, polarity: str = "ridge") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Steger sub-pixel ridge/valley measure.

    ``polarity='ridge'`` selects bright-crest lines (``l1 < 0``: the surface is
    locally concave across the line -- a positive scarp/crest under an
    elevation-signed convention), ``'valley'`` selects ``l1 > 0``.

    Returns ``(strength, subpixel_offset, orientation_deg)``:
    * ``strength``  -- ``|l1|`` where the point is a line point (``|l1| >= |l2|``
      and the requested sign holds), else 0.
    * ``subpixel_offset`` -- Steger's offset to the true line centre, in pixels,
      measured along the ``(ny, nx)`` direction (positive = towards +normal).
    * ``orientation_deg`` -- line orientation in map convention, in [0, 180).
    """
    if polarity not in {"ridge", "valley"}:
        raise ValueError("polarity must be 'ridge' or 'valley'")
    s = np.asarray(surface, dtype=np.float32)
    l1, l2, ny, nx = hessian_eigen(s, sigma)
    finite = np.isfinite(s)
    fill = np.where(finite, s, np.float32(0.0))
    w = ndi.gaussian_filter(finite.astype(np.float32), sigma, mode="nearest")
    gy = ndi.gaussian_filter(fill, sigma, order=(1, 0), mode="nearest") / np.maximum(w, EPS)
    gx = ndi.gaussian_filter(fill, sigma, order=(0, 1), mode="nearest") / np.maximum(w, EPS)
    want = l1 < 0.0 if polarity == "ridge" else l1 > 0.0
    cross = np.abs(l1) >= np.abs(l2)
    # Steger: offset to the line centre along the eigenvector of l1
    denom = np.abs(l1) + EPS
    with np.errstate(invalid="ignore", divide="ignore"):
        t = -(gy * ny + gx * nx) / denom
    strength = np.where(want & cross & finite, np.abs(l1), 0.0).astype(np.float32)
    t = np.where(want & cross & finite, np.clip(t, -2.0, 2.0), 0.0).astype(np.float32)
    orientation = np.degrees(np.arctan2(ny, nx)).astype(np.float32)  # normal direction
    orientation = np.mod(orientation, 180.0)      # line orientation, undirected
    return strength, t, orientation


def frangi_vesselness(surface: np.ndarray, sigmas, *, polarity: str = "dark",
                      beta: float = 0.5, c_scale: float | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Frangi multiscale Hessian line measure, maximised over ``sigmas``.

    ``polarity='dark'`` enhances dark line-like structures on a bright
    background (the convention Frangi et al. use for vessels), ``'bright'`` the
    opposite. This is used for both fault-scarp crests and the paired troughs,
    which is why the polarity is a parameter rather than a constant.

    Returns ``(vesselness, best_sigma_index)``; ``vesselness`` is in [0, 1].
    """
    if polarity not in {"dark", "bright"}:
        raise ValueError("polarity must be 'dark' or 'bright'")
    sig = np.atleast_1d(np.asarray(sigmas, dtype=float))
    if sig.size == 0 or (sig <= 0).any():
        raise ValueError("sigmas must be positive")
    best = np.zeros(np.asarray(surface).shape, dtype=np.float32)
    best_idx = np.zeros(best.shape, dtype=np.int16)
    best_raw = np.full(best.shape, -np.inf, dtype=np.float32)
    for i, s in enumerate(sig):
        l1, l2, _ny, _nx = hessian_eigen(surface, float(s))
        if polarity == "dark":
            # dark line on bright background: l1 (largest |.|) must be > 0 and |l2| not huge
            la, lb = np.where(np.abs(l1) >= np.abs(l2), l1, l2), np.where(np.abs(l1) >= np.abs(l2), l2, l1)
        else:
            la, lb = np.where(np.abs(l1) >= np.abs(l2), l1, l2), np.where(np.abs(l1) >= np.abs(l2), l2, l1)
        lam1, lam2 = la, lb
        if polarity == "dark":
            keep = lam1 > 0.0
        else:
            keep = lam1 < 0.0
        absl1 = np.abs(lam1)
        absl2 = np.abs(lam2)
        with np.errstate(invalid="ignore", divide="ignore"):
            rb = absl2 / np.maximum(absl1, EPS)          # blob-like structures -> ratio near 1
            s_norm = np.sqrt(lam1 * lam1 + lam2 * lam2)
        s_norm = np.sqrt(lam1 * lam1 + lam2 * lam2)
        # c: half the maximum Frobenius norm over the finite domain of this scale
        finite = np.isfinite(s_norm)
        c = float(c_scale) if c_scale is not None else (np.percentile(s_norm[finite], 99.5) if finite.any() else 1.0)
        c = max(c, EPS)
        v = np.exp(-(rb * rb) / (2.0 * beta * beta)) * (1.0 - np.exp(-(s_norm * s_norm) / (2.0 * c * c)))
        v = np.where(keep & np.isfinite(v), v, 0.0)
        v = v * np.maximum(s, EPS)  # scale-normalise so larger scales are comparable
        upd = v > best_raw
        best_raw = np.where(upd, v, best_raw)
        best_idx = np.where(upd, i, best_idx)
        best = np.where(upd, v, best)
    return best, best_idx


def _profile_sample(surface: np.ndarray, cy, cx, theta_rad: np.ndarray, half_len: int) -> np.ndarray:
    """Bilinear samples of ``surface`` along the normal direction at ``(cy, cx)``.

    Shape ``(2*half_len+1, len(cy))``: rows are offsets along the normal
    ``(-sin t, cos t)`` in (row, col) order, i.e. cross-strike profiles.
    """
    s = np.asarray(surface, dtype=np.float64)
    h, w = s.shape
    offs = np.arange(-half_len, half_len + 1, dtype=np.float64)[:, None]
    ny = -np.sin(theta_rad)[None, :]
    nx = np.cos(theta_rad)[None, :]
    yy = cy[None, :] + offs * ny
    xx = cx[None, :] + offs * nx
    y0 = np.floor(yy).astype(np.int64)
    x0 = np.floor(xx).astype(np.int64)
    fy = yy - y0
    fx = xx - x0
    y0c = np.clip(y0, 0, h - 2)
    x0c = np.clip(x0, 0, w - 2)
    v00 = s[y0c, x0c]
    v01 = s[y0c, x0c + 1]
    v10 = s[y0c + 1, x0c]
    v11 = s[y0c + 1, x0c + 1]
    out = (v00 * (1 - fy) * (1 - fx) + v01 * (1 - fy) * fx + v10 * fy * (1 - fx) + v11 * fy * fx)
    inside = (yy >= 0) & (yy <= h - 1) & (xx >= 0) & (xx <= w - 1)
    return np.where(inside, out, np.nan)


def scarplet_step_fit(surface: np.ndarray, theta_deg, *, half_len: int = 4,
                      width_px: float = 1.0, mask: np.ndarray | None = None,
                      chunk: int = 150_000) -> dict:
    """Slope-aware scarp template matching on a slope-detrended surface.

    Model fitted to each cross-strike profile ``p(t)`` of half-length
    ``half_len`` pixels::

        p(t) = a * tanh(t / width) + b + c * t

    ``a`` is the scarp amplitude, ``b`` the local offset and ``c`` the residual
    profile slope (the AGU-2015 slope-aware term). ``a`` is solved directly by a
    linear least-squares fit against the fixed basis ``[tanh(t/w), 1, t]``, so
    the estimate is the matched-filter/GLRT amplitude for this template family.

    Returns a dict of arrays with keys ``amplitude``, ``slope`` (the ``c`` term),
    ``snr`` (``|a|`` divided by the profile residual standard deviation -- the
    scarplet SNR convention), ``orientation`` (deg, [0,180), orientation of the
    fitted scarp line = ``theta + 90`` mod 180) and ``freshness`` (``|a|/width``,
    the standard relative-age proxy: a young scarp keeps a steep, high-amplitude
    profile; an old, degraded scarp has a small amplitude spread over a wide
    rounded profile).

    ``mask`` (bool, same shape) restricts the fit to a cell subset -- the lane's
    "high-prior tiles first" ordering -- and returns zeros elsewhere. Cells
    outside the mask are never sampled, which also bounds peak memory: the
    profile matrix is ``(2*half_len+1) x n_selected``.
    """
    s = np.asarray(surface, dtype=np.float64)
    theta = np.atleast_1d(np.deg2rad(np.asarray(theta_deg, dtype=float)))
    h, w = s.shape
    flat_index = np.arange(h * w, dtype=np.int64)
    if mask is None:
        sel = np.ones(h * w, dtype=bool)
    else:
        sel = np.asarray(mask, bool).ravel().copy()
    sel = sel & np.isfinite(s).ravel()
    n_all = h * w
    sel_idx = flat_index[sel]
    sel_idx = sel_idx.reshape(-1, 1).astype(np.float64)
    cy = (sel_idx // w).astype(np.float64).ravel()
    cx = (sel_idx % w).astype(np.float64).ravel()
    del sel_idx, flat_index
    n = cy.size
    best = {k: np.zeros(n, dtype=np.float64) for k in ("amplitude", "slope", "snr", "freshness")}
    best["snr"] = np.zeros(n)
    keep_amp = np.zeros(n)
    best_theta = np.zeros(n)
    rng = np.arange(-half_len, half_len + 1, dtype=np.float64)
    basis_step = np.tanh(rng / float(width_px))
    design = np.column_stack([basis_step, np.ones_like(rng), rng])
    pinv = np.linalg.pinv(design)
    dof = max(2 * half_len + 1 - 3, 1)
    # Chunked over selected cells to bound peak memory on large grids.
    for start in range(0, n, int(chunk)):
        stop = min(n, start + int(chunk))
        cyc, cxc = cy[start:stop], cx[start:stop]
        for t_deg in theta_deg:
            t_rad = np.deg2rad(float(t_deg))
            prof = _profile_sample(s, cyc, cxc, np.full(stop - start, t_rad), half_len)
            valid = np.isfinite(prof).all(axis=0)
            coef = pinv @ np.where(valid, prof, 0.0)
            amp, off, c = coef[0], coef[1], coef[2]
            resid = np.where(valid, prof, 0.0) - (design @ coef)
            sd = np.sqrt((resid * resid).sum(axis=0) / dof)
            snr = np.abs(amp) / np.maximum(sd, EPS)
            strength = np.where(valid, np.abs(amp) * (snr / (1.0 + snr)), 0.0)
            upd = strength > keep_amp[start:stop]
            keep_amp[start:stop] = np.where(upd, strength, keep_amp[start:stop])
            for key, val in (("amplitude", amp), ("slope", c), ("snr", snr),
                             ("freshness", np.abs(amp) / max(float(width_px), EPS))):
                sub = best[key][start:stop]
                best[key][start:stop] = np.where(upd, np.where(valid, val, 0.0), sub)
            best_theta[start:stop] = np.where(upd, (float(t_deg) + 90.0) % 180.0, best_theta[start:stop])
            del prof, valid, coef, amp, off, c, resid, sd, snr, strength, upd
    shape = (h, w)
    out = {}
    for k, v in best.items():
        full = np.zeros(n_all, dtype=np.float64)
        full[sel] = v
        out[k] = full.reshape(shape)
        del full
    theta_full = np.zeros(n_all, dtype=np.float64)
    theta_full[sel] = best_theta
    out["orientation"] = theta_full.reshape(shape)
    return out


def structure_tensor(surface: np.ndarray, sigma: float = 1.5, rho: float = 3.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Second-moment (structure) tensor fields of the local gradient.

    Returns ``(coherence, orientation_deg, energy)`` where ``coherence`` is
    ``(l1 - l2) / (l1 + l2)`` in [0, 1] (0 = isotropic texture, 1 = a single
    coherent line direction), ``orientation_deg`` is the line orientation in map
    convention [0, 180), and ``energy`` is the smoothed gradient energy.
    """
    s = np.asarray(surface, dtype=np.float32)
    finite = np.isfinite(s)
    fill = np.where(finite, s, np.float32(0.0))
    w = ndi.gaussian_filter(finite.astype(np.float32), sigma, mode="nearest")
    gy = ndi.gaussian_filter(fill, sigma, order=(1, 0), mode="nearest") / np.maximum(w, EPS)
    gx = ndi.gaussian_filter(fill, sigma, order=(0, 1), mode="nearest") / np.maximum(w, EPS)
    j11 = ndi.gaussian_filter(gy * gy, rho, mode="nearest")
    j12 = ndi.gaussian_filter(gy * gx, rho, mode="nearest")
    j22 = ndi.gaussian_filter(gx * gx, rho, mode="nearest")
    trace = j11 + j22
    disc = np.sqrt(np.maximum((j11 - j22) ** 2 / 4.0 + j12 * j12, 0.0))
    l1 = trace / 2.0 + disc
    l2 = trace / 2.0 - disc
    coherence = np.where(trace > EPS, (l1 - l2) / np.maximum(l1 + l2, EPS), 0.0)
    # dominant gradient direction of the major eigenvector -> line orientation
    orient = 0.5 * np.arctan2(2.0 * j12, (j11 - j22))
    line_orient = np.mod(np.degrees(orient) + 90.0, 180.0)
    energy = trace
    bad = ~finite | (w < 0.5)
    return (np.where(bad, np.nan, coherence), np.where(bad, np.nan, line_orient), np.where(bad, np.nan, energy))


def structure_strike(coherence: np.ndarray, orientation_deg: np.ndarray, *,
                     min_coherence: float = 0.0) -> np.ndarray:
    """Dominant-strike channel: orientation where coherent, NaN elsewhere."""
    c = np.asarray(coherence, dtype=np.float64)
    o = np.asarray(orientation_deg, dtype=np.float64)
    out = np.where(np.isfinite(c) & np.isfinite(o) & (c >= min_coherence), o, np.nan)
    return out


def aggregate_to_grid(*, factor: int, layers: dict[str, np.ndarray], weights: dict[str, np.ndarray] | None = None,
                      orientation_layer: str | None = None, min_valid_frac: float = 0.25) -> dict:
    """Aggregate native-resolution layers to a coarser cell grid ("100 m cells").

    ``factor`` is the integer block size (native pixels per target cell). All
    layers must share a shape divisible by ``factor``. Output keys, exactly the
    four aggregate statistics named by the lane:

    ``scarp_fraction``
        fraction of valid native pixels whose (weighted) evidence exceeds zero.
    ``snr_weighted_amplitude``
        sum(w * amplitude) / sum(w) over the block; ``weights`` defaults to the
        scarp amplitude itself when a ``snr`` layer is present.
    ``orientation_coherence``
        magnitude of the circular mean resultant vector of the block's
        orientations, i.e. ``|mean(exp(2i*theta))|`` in [0, 1]: 1 when every
        native pixel shares one strike, 0 when strikes cancel.
    ``dominant_strike``
        orientation of that mean resultant vector, in [0, 180) degrees.

    Blocks whose valid fraction is below ``min_valid_frac`` return NaN.
    """
    if factor < 1:
        raise ValueError("factor must be >= 1")
    out: dict[str, np.ndarray] = {}
    shapes = {v.shape for v in layers.values()}
    if len(shapes) != 1:
        raise ValueError(f"all layers must share a shape, got {sorted(shapes)}")
    h, w = next(iter(shapes))
    if h % factor or w % factor:
        raise ValueError(f"shape {h}x{w} is not divisible by factor {factor}")
    hb, wb = h // factor, w // factor
    valid_any = np.zeros((hb, wb), dtype=np.float64)

    def blocks(a):
        a = np.asarray(a, dtype=np.float64)
        return a.reshape(hb, factor, wb, factor).transpose(0, 2, 1, 3).reshape(hb, wb, factor * factor)

    amp_key = next((k for k in layers if "amplitude" in k), None)
    snr_key = next((k for k in layers if "snr" in k), None)
    if amp_key is not None:
        amp = layers[amp_key]
        wgt = (weights or {}).get(amp_key, layers.get(snr_key, np.abs(amp)))
        wgt = np.where(np.isfinite(wgt), wgt, 0.0)
        ab = blocks(amp)
        wb_ = blocks(wgt)
        num = np.nansum(np.where(np.isfinite(ab), ab * wb_, 0.0), axis=2)
        den = np.nansum(np.where(np.isfinite(ab), wb_, 0.0), axis=2)
        out["snr_weighted_amplitude"] = np.where(den > EPS, num / np.maximum(den, EPS), np.nan)
        ev = np.isfinite(ab) & (ab != 0.0)
        out["scarp_fraction"] = np.where(
            (np.isfinite(ab).sum(axis=2) > 0),
            ev.sum(axis=2) / np.maximum(np.isfinite(ab).sum(axis=2), 1), np.nan)
        valid_any = np.maximum(valid_any, (np.isfinite(ab).sum(axis=2) > 0).astype(np.float64))
    else:
        fills = []
        for name, arr in layers.items():
            b = blocks(arr)
            n_valid = np.isfinite(b).sum(axis=2)
            vals = np.nansum(np.where(np.isfinite(b), b, 0.0), axis=2)
            out[name] = np.where(n_valid > 0, vals / np.maximum(n_valid, 1), np.nan)
            fills.append(n_valid > 0)
        if fills:
            valid_any = np.maximum(valid_any, np.logical_or.reduce(fills).astype(np.float64))
    if orientation_layer is not None and orientation_layer in layers:
        ob = blocks(layers[orientation_layer])
        th = np.deg2rad(ob)
        with np.errstate(invalid="ignore"):
            cs = np.nanmean(np.cos(2 * th), axis=2)
            sn = np.nanmean(np.sin(2 * th), axis=2)
        coh = np.hypot(np.nan_to_num(cs), np.nan_to_num(sn))
        out["orientation_coherence"] = np.where(np.isfinite(cs) & np.isfinite(sn), coh, np.nan)
        out["dominant_strike"] = np.mod(np.degrees(0.5 * np.arctan2(np.nan_to_num(sn), np.nan_to_num(cs))), 180.0)
        out["dominant_strike"] = np.where(out["orientation_coherence"] > 0, out["dominant_strike"], np.nan)
    if "orientation_coherence" in out and "dominant_strike" in out:
        for k in ("orientation_coherence", "dominant_strike"):
            out[k] = np.where(valid_any > 0.5 * min_valid_frac, out[k], np.nan)
    return out


def line_consistency(strike_deg: np.ndarray, evidence: np.ndarray, *, half_len: int = 2,
                     max_strike_dev_deg: float = 30.0, min_hits: int = 3) -> np.ndarray:
    """Fraction of neighbours that continue the local strike with evidence.

    For every cell, sample the ``half_len`` nearest cells on **both** sides along
    the local strike (nearest-neighbour lattice ray, bidirectional) and compute a
    strike-deviation-weighted hit fraction. A line-like fault scarp scores near
    1; an isolated blob (a single cell with evidence but no aligned neighbours)
    scores near 0. Isolated blobs are the dominant false-positive mode of
    per-cell max-aggregated scarp channels, which is what this statistic targets.

    Cells with NaN strike or NaN evidence return NaN.
    """
    st = np.asarray(strike_deg, dtype=np.float64)
    ev = np.asarray(evidence, dtype=np.float64)
    if st.shape != ev.shape:
        raise ValueError("strike and evidence must share a shape")
    h, w = st.shape
    th = np.deg2rad(st)
    # unit direction along the strike line, in (row, col) = (-sin, cos)
    dy = -np.sin(th)
    dx = np.cos(th)
    have = np.isfinite(st) & np.isfinite(ev)
    hits = np.zeros((h, w), np.float64)
    counted = np.zeros((h, w), np.float64)
    tot_hits = np.zeros((h, w), np.float64)
    yy, xx = np.mgrid[0:h, 0:w]
    for sgn in (+1.0, -1.0):
        for step in range(1, half_len + 1):
            ny = np.rint(yy + sgn * step * dy).astype(np.int64)
            nx = np.rint(xx + sgn * step * dx).astype(np.int64)
            inb = (ny >= 0) & (ny < h) & (nx >= 0) & (nx < w)
            nyc, nxc = np.clip(ny, 0, h - 1), np.clip(nx, 0, w - 1)
            nb_st = st[nyc, nxc]
            nb_ev = ev[nyc, nxc]
            dev = np.abs(((nb_st - st + 90.0) % 180.0) - 90.0)
            ok = inb & have & np.isfinite(nb_st) & np.isfinite(nb_ev) & (nb_ev > 0) & (dev <= max_strike_dev_deg)
            hits += np.where(ok, 1.0, 0.0)
            tot_hits += np.where(ok, 1.0 - dev / max(max_strike_dev_deg, EPS), 0.0)
            counted += np.where(inb & have, 1.0, 0.0)
    n_needed = float(min_hits)
    frac = tot_hits / np.maximum(n_needed, EPS)
    out = np.where(counted > 0, np.minimum(frac, 1.0), np.nan)
    out = np.where(tot_hits >= n_needed, out, np.where(np.isfinite(out), out, np.nan))
    return out
