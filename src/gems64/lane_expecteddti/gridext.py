"""Grid loaders and band metadata for the Expected-DTI-optimal lane.

SUPPLEMENTARY MODULE.  The canonical grid constants live in the shared ``gems64.grid`` and are
imported from there, so this lane keeps no private fork of them.  What this module adds is what
the shared module does not carry: the 19 official band names and categories, the ``GEMS64_DATA``
data-root resolution, and the footprint / catalogue / scored-domain loaders measured against the
hash-pinned rasters.

The shared module independently pins SHA256_EXISTING_FAULTS = 7ba308ccdc4418b3... and
SHA256_SAMPLE_SUBMISSION = 2176d08e485aa2cd..., which match the digests this lane measured from
the bytes on disk (registry/data_manifest.json) -- two independent confirmations of the same pins.

Original measured-facts header follows.

Canonical grid, footprint and catalogue definitions for the DOE GEMS Prize (DrivenData #306).

Every constant in this module was measured directly from the hash-pinned competition rasters
restored into ``data/raw/`` (see ``registry/data_receipt.json`` for the SHA-256 pins) and
cross-checked against the organizer's own reference solution notebook output
(https://github.com/drivendataorg/gems-prize-reference-solution,
``unet-mc-cv-reference-solution.ipynb``).

Verified facts (measured 2026-10-11, this repository):

===============================================  ===============  ==========================
quantity                                         value            source
===============================================  ===============  ==========================
width x height                                   3292 x 3730      all three official rasters
CRS                                              EPSG:32611       all three official rasters
resolution                                       100 m x 100 m    all three official rasters
affine transform                                 (100, 0, 243350, 0, -100, 4508550)
bounds (W, S, E, N)                              243350, 4135550, 572550, 4508550
total cells                                      12,279,160       3292 * 3730
footprint cells (finite in sample_submission)    5,167,373        ``np.isfinite`` on template
outside-footprint cells (NaN in template)        7,111,787        complement
catalogue fault cells (labels == 1)              60,988           ``labels.tif``
scored cells (footprint minus catalogue)         5,106,385        forum thread 11516 masking
feature sentinel cells inside footprint          3,061 / band     ``-3.4028234663852886e+38``
  ... band 6 (tilt / total curvature)            3,073            one extra row of sentinel
feature band-1 valid cells                       5,165,852        1,521 fewer than footprint
===============================================  ===============  ==========================

The ``labels.tif`` ``-1`` (nodata) mask is **exactly** the template's NaN mask, and its ``1``
mask is **exactly** the template's ``1`` mask, so ``sample_submission.tif`` is the label raster
re-encoded.  Only its *footprint* may be used, never its values.

Scoring mask (DrivenData staff ``chrisk-dd``, official forum thread 11516, 16 Sep 2026,
https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516):

    1. Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from
       evaluation, so they do not count towards penalty terms.
    2. Re-evaluation will also mask/exclude the existing USGS/INGENIOUS faults.

Consequence: emitted probability mass on catalogue pixels earns no TP and incurs no FP.  It is
pure waste of the emission budget, so this module exposes the scored domain directly.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

# Canonical grid constants come from the SHARED ``gems64.grid`` module -- there is exactly one
# source of truth for the grid in this repository, and this lane module only adds the loaders and
# the band metadata that the shared module does not carry.  ``TRANSFORM`` is re-exposed as a plain
# 6-tuple because this lane's writers and validators compare tuples; the shared module keeps the
# authoritative ``Affine``.
from gems64.grid import EPSG, HEIGHT, WIDTH
from gems64.grid import PIXEL_M as RESOLUTION_M
from gems64.grid import TRANSFORM as _AFFINE_TRANSFORM

TRANSFORM = tuple(_AFFINE_TRANSFORM)[:6]
N_CELLS = WIDTH * HEIGHT
BOUNDS = (TRANSFORM[2], TRANSFORM[5] - HEIGHT * abs(TRANSFORM[4]),
          TRANSFORM[2] + WIDTH * TRANSFORM[0], TRANSFORM[5])
FEATURE_NODATA = np.float32(-3.4028234663852886e38)
N_FEATURE_BANDS = 19

FOOTPRINT_CELLS = 5_167_373
OUTSIDE_CELLS = 7_111_787
CATALOGUE_CELLS = 60_988
SCORED_CELLS = FOOTPRINT_CELLS - CATALOGUE_CELLS  # 5,106,385

# Data locations.  ``GEMS64_DATA`` overrides so the tree stays relocatable.
import os

DATA_ROOT = Path(os.environ.get("GEMS64_DATA", "/home/user/scratch/data/raw"))
RAW = DATA_ROOT
EXTERNAL = DATA_ROOT / "external"
PROCESSED = DATA_ROOT / "processed"

BAND_NAMES = (
    "mag_anom",        # 1  Magnetic anomaly
    "rtp",             # 2  Reduced to pole
    "tmi_hgrad",       # 3  TMI horizontal gradient
    "geod_2nd_inv",    # 4  Geodetic second invariant
    "iso_grav_slope",  # 5  Isostatic gravity anomaly slope
    "tilt",            # 6  Tilt angle / total curvature (edge detection)
    "geod_shear",      # 7  Geodetic shear rate
    "geod_dilat",      # 8  Geodetic dilatation rate
    "tmi_vgrad",       # 9  TMI vertical gradient
    "dist_eq",         # 10 Distance to earthquake (n=100 km, a=15 deg)
    "iso_grav_vgrad",  # 11 Isostatic gravity anomaly vertical gradient
    "dem_detrend",     # 12 Detrended elevation
    "iso_grav",        # 13 Isostatic gravity anomaly
    "tmi",             # 14 Total magnetic intensity
    "depth_base",      # 15 Depth to basement surface
    "eq_density",      # 16 Earthquake intensity/density (n=100 km, a=15 deg)
    "conductivity",    # 17 Conductivity surface
    "iso_grav_hgrad",  # 18 Isostatic gravity anomaly horizontal gradient
    "dem_detrend_slope",  # 19 Detrended elevation slope
)

BAND_CATEGORY = (
    "magnetic_data", "magnetic_data", "magnetic_data", "geodetic_strain", "gravity_data",
    "magnetic_data", "geodetic_strain", "geodetic_strain", "magnetic_data", "seismic",
    "gravity_data", "topographic", "gravity_data", "magnetic_data", "subsurface", "seismic",
    "subsurface", "gravity_data", "topographic",
)


def _require(p: Path) -> Path:
    if not p.exists():
        raise FileNotFoundError(
            f"{p} is missing.  Point GEMS64_DATA at a directory holding the three hash-pinned "
            f"official rasters (see registry/data_manifest.json for the digests)."
        )
    return p


def load_footprint() -> np.ndarray:
    """Boolean footprint: the cells the template leaves finite (5,167,373)."""
    import rasterio

    with rasterio.open(_require(RAW / "sample_submission.tif")) as s:
        return np.isfinite(s.read(1))


def load_catalogue() -> np.ndarray:
    """Boolean catalogue mask: ``labels.tif > 0`` (60,988 cells)."""
    import rasterio

    with rasterio.open(_require(RAW / "labels.tif")) as s:
        return s.read(1) > 0


def load_scored_domain() -> np.ndarray:
    """Footprint minus catalogue: the cells that can earn or cost anything (5,106,385)."""
    return load_footprint() & ~load_catalogue()


def load_features(bands: tuple[int, ...] | None = None) -> np.ndarray:
    """Feature stack as ``(H, W, n)`` float64 with the sentinel replaced by NaN.

    Bands are 1-based to match the organizer's numbering.  ``None`` loads all 19.
    """
    import rasterio

    idx = tuple(range(1, N_FEATURE_BANDS + 1)) if bands is None else tuple(bands)
    out = np.empty((HEIGHT, WIDTH, len(idx)), dtype=np.float64)
    with rasterio.open(_require(RAW / "training_features.tif")) as s:
        for k, i in enumerate(idx):
            b = s.read(i).astype(np.float64)
            b[b < -1e38] = np.nan
            out[..., k] = b
    return out


def assert_grid(path: Path) -> dict:
    """Fail closed unless ``path`` matches the official CRS / shape / transform exactly."""
    import rasterio

    with rasterio.open(path) as s:
        got = dict(
            width=s.width, height=s.height, count=s.count,
            dtype=str(s.dtypes[0]), crs=str(s.crs),
            transform=tuple(s.transform), nodata=s.nodata,
        )
    errs = []
    if got["width"] != WIDTH:
        errs.append(f"width {got['width']} != {WIDTH}")
    if got["height"] != HEIGHT:
        errs.append(f"height {got['height']} != {HEIGHT}")
    if got["count"] != 1:
        errs.append(f"bands {got['count']} != 1")
    if got["dtype"] != "float32":
        errs.append(f"dtype {got['dtype']} != float32")
    if not (got["crs"] or "").upper().endswith("32611"):
        errs.append(f"crs {got['crs']} != EPSG:32611")
    if tuple(got["transform"]) != TRANSFORM:
        errs.append(f"transform {got['transform']} != {TRANSFORM}")
    if errs:
        raise ValueError("grid mismatch for " + str(path) + ": " + "; ".join(errs))
    return got
