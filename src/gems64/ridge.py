"""Steger sub-pixel ridge/valley lines and Frangi multiscale vesselness.

Two textbook detectors, implemented here so the lane can *use* them rather than
cite them:

* **Steger (1998)**, "An unbiased detector of curvilinear structures",
  IEEE TPAMI 20(2):113-125, doi:10.1109/34.659181.  A curvilinear structure sits
  where the gradient is parallel to the eigenvector of the Hessian eigenvalue
  with the dominant magnitude.  With ``n`` that eigenvector, the sub-pixel
  offset of the line centre from a grid point is

      s = -(n . grad) / (n . H . n)

  and the grid point is a line centre when ``|s| <= 0.5`` and the polarity of
  ``n . H . n`` matches the wanted line type.

* **Frangi et al. (1998)**, "Multiscale vessel enhancement filtering", MICCAI,
  LNCS 1496:130-137, doi:10.1007/BFb0056195.  With ``|l1| <= |l2|`` the Hessian
  eigenvalues at scale sigma,

      V = exp(-Rb^2 / 2b^2) * (1 - exp(-S^2 / 2c^2)),
      Rb = |l1| / |l2|,   S = sqrt(l1^2 + l2^2),

  and the multiscale response is ``max_sigma V(sigma)``.

Both take *sigma in pixels*: at the competition's 100 m grid one pixel is 100 m,
so the lane's "2-20 m scales" are only reachable on the 1 m-derived 3 m pilot
tiles, where sigma = 0.7-6.7 px.  :func:`scales_m` converts metres to sigma for
a given cell size and refuses scales the data cannot resolve, so a caller cannot
quietly mix a 100 m-grid surface with a 2 m template.

Angle convention: ``theta`` is the orientation of the **dominant-curvature
eigenvector**, i.e. across the line.  :func:`line_orientation` rotates it to the
line's own strike in ``[0, pi)``.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi


def _gauss_kernel(sigma: float, truncate: float = 4.0) -> np.ndarray:
    radius = max(1, int(np.ceil(truncate * float(sigma))))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    k = np.exp(-(x ** 2) / (2.0 * float(sigma) ** 2))
    return k / k.sum()


def principal_eigenvalues(dyy: np.ndarray, dxy: np.ndarray, dxx: np.ndarray):
    """Order Hessian eigenvalues by **magnitude**, not by signed value.

    For a perfectly straight line the along-line eigenvalue is exactly zero, so
    ordering by signed value would rank the across-line eigenvalue second and
    silently drop every detection.  Returns ``(big, small)`` by absolute value.
    """
    tr = dyy + dxx
    disc = np.sqrt(np.maximum((dyy - dxx) ** 2 / 4.0 + dxy ** 2, 0.0))
    lo, hi = tr / 2.0 - disc, tr / 2.0 + disc
    swap = np.abs(lo) > np.abs(hi)
    return np.where(swap, lo, hi), np.where(swap, hi, lo)


def line_orientation(theta):
    """Across-line eigenvector angle -> line strike in ``[0, pi)``."""
    return (np.asarray(theta, float) + np.pi / 2.0) % np.pi


def hessian(arr: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Hessian of the sigma-smoothed image: ``(Dyy, Dxy, Dxx)`` in pixel units."""
    a = np.asarray(arr, np.float64)
    if sigma <= 0:
        raise ValueError("positive sigma required")
    k = _gauss_kernel(sigma)
    sm = ndi.convolve1d(ndi.convolve1d(a, k, axis=0, mode="nearest"), k, axis=1, mode="nearest")
    dyy = np.zeros_like(sm)
    dxx = np.zeros_like(sm)
    dxy = np.zeros_like(sm)
    dyy[1:-1, :] = sm[2:, :] - 2 * sm[1:-1, :] + sm[:-2, :]
    dxx[:, 1:-1] = sm[:, 2:] - 2 * sm[:, 1:-1] + sm[:, :-2]
    dxy[1:-1, 1:-1] = 0.25 * (sm[2:, 2:] - sm[2:, :-2] - sm[:-2, 2:] + sm[:-2, :-2])
    return dyy, dxy, dxx


def frangi(arr: np.ndarray, sigmas, *, beta: float = 0.5, c: float = 0.5,
           mode: str = "dark") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Multiscale Frangi vesselness ``(response, sigma_star, theta)``.

    ``mode='dark'`` scores dark lines on a bright background (channels, valleys);
    ``mode='bright'`` scores ridges.  ``theta`` is the across-line angle at the
    winning scale; ``sigma_star`` is 0 where the response is 0.
    """
    a = np.asarray(arr, np.float64)
    if a.ndim != 2:
        raise ValueError("frangi expects a 2-D array")
    if not np.isfinite(a).all():
        raise ValueError("frangi expects a finite array")
    sigmas = [float(s) for s in np.atleast_1d(sigmas)]
    if not sigmas or min(sigmas) <= 0:
        raise ValueError("positive sigmas required")
    best = np.zeros_like(a)
    best_sigma = np.zeros_like(a)
    best_theta = np.zeros_like(a)
    for sigma in sigmas:
        dyy, dxy, dxx = hessian(a, sigma)
        big, small = principal_eigenvalues(dyy, dxy, dxx)
        sel = (big > 0) if mode == "dark" else (big < 0)
        rb = np.abs(small) / (np.abs(big) + 1e-12)
        s_norm = np.sqrt(big ** 2 + small ** 2)
        scale = max(float(np.percentile(s_norm, 99.0)), 1e-12)
        v = (np.exp(-(rb ** 2) / (2 * beta ** 2))
             * (1.0 - np.exp(-(s_norm ** 2) / (2 * (c * scale) ** 2))))
        v = np.where(sel, v, 0.0)
        better = v > best
        best = np.where(better, v, best)
        best_sigma = np.where(better, sigma, best_sigma)
        best_theta = np.where(better, np.arctan2(dxy, big - dyy), best_theta)
    return best, best_sigma, best_theta


def steger(arr: np.ndarray, sigma: float, *, mode: str = "dark",
           min_contrast: float = 0.0):
    """Steger sub-pixel line detection at one scale.

    Returns ``(subpixel, magnitude, theta)``: ``subpixel`` holds the offset of
    the estimated line centre relative to each grid point (NaN where the point is
    not a line centre), ``magnitude`` is ``|n . grad|`` there, and ``theta`` is
    the across-line angle.
    """
    a = np.asarray(arr, np.float64)
    if a.ndim != 2:
        raise ValueError("steger expects a 2-D array")
    if not np.isfinite(a).all():
        raise ValueError("steger expects a finite array")
    if sigma <= 0:
        raise ValueError("positive sigma required")
    k = _gauss_kernel(sigma)
    sm = ndi.convolve1d(ndi.convolve1d(a, k, axis=0, mode="nearest"), k, axis=1, mode="nearest")
    gy = np.zeros_like(sm)
    gx = np.zeros_like(sm)
    gy[1:-1, :] = (sm[2:, :] - sm[:-2, :]) / 2.0
    gx[:, 1:-1] = (sm[:, 2:] - sm[:, :-2]) / 2.0
    dyy, dxy, dxx = hessian(a, sigma)
    big, _ = principal_eigenvalues(dyy, dxy, dxx)
    norm = np.hypot(dxy, big - dyy)
    safe = norm > 1e-12
    ny = np.divide(dxy, norm, out=np.ones_like(norm), where=safe)
    nx = np.divide(big - dyy, norm, out=np.zeros_like(norm), where=safe)
    n_dot_g = ny * gy + nx * gx
    n_dot_h_n = ny * ny * dyy + 2 * ny * nx * dxy + nx * nx * dxx
    with np.errstate(divide="ignore", invalid="ignore"):
        offset = -n_dot_g / n_dot_h_n
    polarity = (big > 0) if mode == "dark" else (big < 0)
    valid = (polarity & np.isfinite(offset) & (np.abs(offset) <= 0.5)
             & (np.abs(n_dot_g) > min_contrast))
    return (np.where(valid, offset, np.nan),
            np.where(valid, np.abs(n_dot_g), 0.0),
            np.arctan2(ny, nx))


def scales_m(scales_in_metres, cell_size_m: float):
    """Convert physical scales to sigma in pixels; refuse sub-cell scales."""
    cell = float(cell_size_m)
    if cell <= 0:
        raise ValueError("cell size must be positive")
    out = []
    for m in np.atleast_1d(scales_in_metres).astype(float):
        if m < 2.0 * cell:
            raise ValueError(f"scale {m} m is not resolvable at {cell} m cells")
        out.append(m / cell)
    return out


def ridge_density(angles, *, weights=None) -> float:
    """Circular concentration of line orientations in ``[0, pi)``.

    Resultant length of the doubled-angle vector: 1 = all lines parallel,
    0 = uniform.  This is the structure-tensor coherence of a set of detected
    line pixels, computed without assuming a dominant direction.
    """
    a = np.asarray(angles, float)
    w = np.ones_like(a) if weights is None else np.asarray(weights, float)
    if a.shape != w.shape:
        raise ValueError("angles and weights must have the same shape")
    good = np.isfinite(a) & np.isfinite(w) & (w > 0)
    a, w = a[good], w[good]
    if a.size == 0 or w.sum() <= 0:
        return 0.0
    z = np.exp(2j * a)
    return float(np.abs((w * z).sum()) / w.sum())
