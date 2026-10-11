import numpy as np
from scipy.special import erf
from gems64.lidar_scarp import compute_native_dem_scarp_channels


def test_synthetic_scarp_scarplet_steger_frangi():
    yy, xx = np.mgrid[0:100, 0:100].astype(np.float32) * 3.0
    theta = np.deg2rad(15.0)
    u = (xx - 150.0) * np.cos(theta) + (yy - 150.0) * np.sin(theta)
    z = 1200.0 + 0.03 * xx + 0.8 * erf(u / 4.5)
    valid = np.ones_like(z, dtype=bool)
    res = compute_native_dem_scarp_channels(z, valid, res_m=3.0)
    scarp_zone = (np.abs(u) <= 3.0) & (yy > 45.0) & (yy < 255.0) & (xx > 45.0) & (xx < 255.0)
    bg_zone = (np.abs(u) >= 35.0) & (yy > 45.0) & (yy < 255.0) & (xx > 45.0) & (xx < 255.0)

    assert float(res["amplitude"][scarp_zone].mean()) > 4.0 * float(
        res["amplitude"][bg_zone].mean() + 1e-4
    )
    assert float(res["frangi_vesselness"][scarp_zone].mean()) > 0.70
    assert float(res["frangi_vesselness"][bg_zone].mean()) < 0.10
    assert float(res["steger_line"][scarp_zone].mean()) > 0.50
    strike_med = float(np.nanmedian(res["orientation_deg"][scarp_zone]))
    assert abs(strike_med - 15.0) < 5.0
