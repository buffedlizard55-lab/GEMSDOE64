"""Multi-physics + hydrothermal feature stack for the DOE GEMS grid.

Every layer is read from a file whose provenance is recorded in
``evidence/data_receipt.json``.  Band *names* are taken from the manifest that
shipped with the raster; where a raster has no manifest (``lidar_scarp``,
``geodawn_rad``, ``geodawn_extensions``) the bands are exposed as
``<layer>_b01`` ... with **no invented semantics** (irregularity IR-64-BANDS-01).

Catalogue-derived features are always computed from the *visible* catalogue mask
that the caller supplies, never from the full catalogue, so a holdout fold can
never see its own withheld segments.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from .metric import RADIUS_PX

STRUCT8 = np.ones((3, 3), bool)

# documented band order of data/external/topo_10m_derived_100m_u8.manifest.json
TOPO_BANDS = ("slope_p90", "slope_max", "steep_frac", "slope_std", "relief_local",
              "curv_prof_absmax", "aspect_coherence", "hs_lineament", "dem_mean")


def _read_u8(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read().astype(np.uint8)


DIST_CAP_PX = 100.0


def _edtf(mask: np.ndarray, dtype=np.float16) -> np.ndarray:
    """Euclidean distance (px) to the nearest True pixel, capped at 100 px.

    Capped because the cap is far beyond the 3-px metric kernel, and float16
    keeps a 5.2 Mpx stack inside the sandbox memory budget.
    """
    if not mask.any():
        return np.full(mask.shape, DIST_CAP_PX, dtype)
    return np.minimum(ndi.distance_transform_edt(~mask), DIST_CAP_PX).astype(dtype)


def tips_and_extrapolation(cat: np.ndarray, reach_px: int = 8) -> tuple[np.ndarray, np.ndarray]:
    """Trace tips (dead ends) of the visible catalogue and their along-strike rays.

    A tip is a catalogue pixel with at most one 8-connected catalogue neighbour.
    The ray direction is the tip minus the catalogue pixel ``reach`` steps back
    along the trace, obtained by a greedy walk, so the extrapolation follows the
    *local* strike rather than a straight global line.
    """
    cat = np.asarray(cat, bool)
    n_nb = ndi.convolve(cat.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - cat.astype(np.uint8)
    tips = cat & (n_nb <= 1)
    ys, xs = np.nonzero(tips)
    extrap = np.zeros(cat.shape, bool)
    for y0, x0 in zip(ys, xs):
        # walk back along the trace to estimate the incoming direction
        cy, cx, py, px_ = int(y0), int(x0), int(y0), int(x0)
        for _ in range(reach_px):
            best = None
            for j in (-1, 0, 1):
                for i in (-1, 0, 1):
                    ny, nx = cy + j, cx + i
                    if (ny, nx) == (py, px_) or not (0 <= ny < cat.shape[0] and 0 <= nx < cat.shape[1]):
                        continue
                    if cat[ny, nx]:
                        best = (ny, nx)
                        break
                if best:
                    break
            if best is None:
                break
            py, px_ = cy, cx
            cy, cx = best
        dy, dx = y0 - cy, x0 - cx
        if dy == 0 and dx == 0:
            continue
        L = float(np.hypot(dy, dx))
        uy, ux = dy / L, dx / L
        for t in range(1, reach_px + 1):
            ry = int(round(y0 + uy * t))
            rx = int(round(x0 + ux * t))
            if 0 <= ry < cat.shape[0] and 0 <= rx < cat.shape[1]:
                extrap[ry, rx] = True
    extrap &= ~cat
    return tips, extrap


@dataclass
class FeatureStack:
    """Lazy-ish multi-physics stack aligned to the competition grid."""

    grid: object
    external_dir: Path
    names: list = field(default_factory=list)
    cache_dir: Path | None = None
    _u8: dict = field(default_factory=dict)
    _f32: dict = field(default_factory=dict)
    _mm: object = None
    receipt: dict = field(default_factory=dict)

    # ------------------------------------------------------------------ build
    def build(self, visible: np.ndarray) -> "FeatureStack":
        g = self.grid
        fp, H, W = g.footprint, g.height, g.width
        d_cat = _edtf(visible)
        tips, extrap = tips_and_extrapolation(visible)
        d_tip = _edtf(tips)
        d_ext = _edtf(extrap)

        f32: dict[str, np.ndarray] = {}
        f32["d_cat"] = d_cat
        f32["k_cat_3"] = np.exp(-d_cat / 3.0).astype(np.float16)
        f32["k_cat_8"] = np.exp(-d_cat / 8.0).astype(np.float16)
        f32["d_tip"] = d_tip
        f32["k_tip_3"] = np.exp(-d_tip / 3.0).astype(np.float16)
        f32["d_strike_extrap"] = d_ext
        f32["k_strike_extrap_3"] = np.exp(-d_ext / 3.0).astype(np.float16)
        f32["cat_density_11"] = ndi.uniform_filter(
            visible.astype(np.float32), 11).astype(np.float16)

        ex = Path(self.external_dir)
        topo = _read_u8(ex / "topo_10m_derived_100m_u8.tif")
        for i, nm in enumerate(TOPO_BANDS):
            f32[f"topo_{nm}"] = topo[i]          # uint8 codes (manifest-documented)
        del topo
        for tag, fn, nb in (("lidar_scarp", "lidar_scarp_features_u8.tif", 12),
                            ("geodawn_rad", "geodawn_rad_u8.tif", 4),
                            ("geodawn_ext", "geodawn_extensions_u8.tif", 4)):
            arr = _read_u8(ex / fn)
            assert arr.shape[0] == nb, f"{fn}: expected {nb} bands, got {arr.shape[0]}"
            for i in range(nb):
                f32[f"{tag}_b{i+1:02d}"] = arr[i]     # uint8 codes (undocumented)
            del arr

        with rasterio.open(ex / ".." / "geodawn_dem_a2_100m.tif") as src:
            dem = src.read(1).astype(np.float32)
        dem[~np.isfinite(dem)] = np.nan
        dem[dem <= -999998] = np.nan
        med = float(np.nanmedian(dem[fp])) if np.isfinite(dem[fp]).any() else 0.0
        dem_filled = np.where(np.isfinite(dem), dem, med)
        gy, gx = np.gradient(dem_filled, 100.0)
        f32["dem_elev"] = dem_filled.astype(np.float16)
        f32["dem_slope"] = np.hypot(gy, gx).astype(np.float32)
        f32["dem_lap"] = ndi.laplace(dem_filled).astype(np.float32)
        f32["dem_slope_std_5"] = ndi.uniform_filter(
            np.hypot(gy, gx) ** 2, 5).astype(np.float16)
        f32["dem_rough"] = (ndi.maximum_filter(dem_filled, 5) -
                            ndi.minimum_filter(dem_filled, 5)).astype(np.float16)
        del dem, dem_filled, gy, gx

        thermal = self._thermal_mask(ex)
        d_th = _edtf(thermal)
        f32["d_thermal_point"] = d_th
        f32["k_thermal_8"] = np.exp(-d_th / 8.0).astype(np.float16)
        hot = self._thermal_mask(ex, only_hot=True)
        f32["d_thermal_hot"] = _edtf(hot)
        del d_th

        self._spill(f32)   # sets self.names from the pre-clear key order
        self.receipt = dict(
            n_features=len(self.names),
            n_visible_catalogue_px=int(visible.sum()),
            n_tips=int(tips.sum()),
            n_extrap_px=int(extrap.sum()),
            n_thermal_points=int(thermal.sum()),
            n_hot_points=int(hot.sum()),
            footprint_px=int(fp.sum()),
        )
        return self

    @staticmethod
    def _thermal_mask(ex: Path, only_hot: bool = False) -> np.ndarray:
        """Rasterise the GDR well/spring points (row,col already on this grid)."""
        path = Path(ex) / "gdr_wellspring_in_footprint.csv"
        out = np.zeros((3730, 3292), bool)
        if not path.is_file():
            return out
        with path.open(newline="") as fh:
            for row in csv.DictReader(fh):
                try:
                    r, c = int(float(row["row"])), int(float(row["col"]))
                except (TypeError, ValueError):
                    continue
                if not (0 <= r < 3730 and 0 <= c < 3292):
                    continue
                if only_hot and (row.get("thermalclass") or "").strip().lower() != "hot":
                    continue
                out[r, c] = True
        return out

    # ------------------------------------------------------------------ access
    def _spill(self, f32: dict) -> None:
        """Park the stack in a float16 memory-mapped file.

        The sandbox has ~3 GB of RAM; a 45-band float32 stack is ~1.8 GB.  Page
        cache is reclaimable, so a memmap keeps the same information resident
        without triggering the OOM killer.
        """
        import tempfile
        self.names = list(f32.keys())
        d = Path(self.cache_dir) if self.cache_dir else Path(tempfile.mkdtemp(prefix="gems64fs_"))
        d.mkdir(parents=True, exist_ok=True)
        self.cache_dir = d
        path = d / f"stack_{abs(hash(tuple(self.names))) % 10**8}.f16"
        mm = np.memmap(path, dtype=np.float16, mode="w+",
                       shape=(len(self.names),) + f32[self.names[0]].shape)
        for i, nm in enumerate(self.names):
            mm[i] = f32[nm]
        mm.flush()
        self._mm = mm
        self._f32 = {nm: mm[i] for i, nm in enumerate(self.names)}
        f32.clear()

    def matrix(self, ys: np.ndarray, xs: np.ndarray) -> np.ndarray:
        """Design matrix for the given pixel indices (bands are stored in their
        native compact dtype and widened here)."""
        out = np.empty((ys.size, len(self.names)), np.float32)
        for k, nm in enumerate(self.names):
            out[:, k] = self._f32[nm][ys, xs]
        return np.nan_to_num(out, nan=0.0, posinf=60.0, neginf=0.0)

    def bytes_held(self) -> int:
        return int(sum(a.nbytes for a in self._f32.values()))

    def free(self) -> None:
        self._f32.clear()
        mm, self._mm = self._mm, None
        if mm is not None:
            path = Path(mm.filename)
            del mm
            try:
                path.unlink()
            except OSError:
                pass
