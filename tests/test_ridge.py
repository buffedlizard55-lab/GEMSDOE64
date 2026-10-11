"""Verification of the Steger / Frangi implementations on synthetic lines.

These tests pin *behaviour*, not just API shape: a straight line placed at a
known sub-pixel offset must be recovered to better than 0.15 px by Steger, and
Frangi must prefer a line over a blob of the same contrast.
"""
import numpy as np
import pytest

from gems64.ridge import (frangi, hessian, line_orientation, principal_eigenvalues,
                          ridge_density, scales_m, steger)


def straight_line(shape=(81, 81), offset=0.3, sigma=1.0, value=-1.0, background=0.0):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    centre = shape[1] / 2.0 + offset
    prof = value * np.exp(-((xx - centre) ** 2) / (2 * sigma ** 2))
    return background + prof


def test_steger_recovers_subpixel_offset_of_a_straight_dark_line():
    offset = 0.35
    img = straight_line(offset=offset)
    sub, mag, theta = steger(img, sigma=1.2, mode="dark")
    truth = img.shape[1] / 2.0 + offset
    estimates, thetas = [], []
    for row in range(15, img.shape[0] - 15):
        cols = np.flatnonzero(np.isfinite(sub[row]))
        # exactly one line centre per cross-section of a straight, isolated line
        assert cols.size == 1, f"row {row}: {cols.size} detections"
        estimates.append(cols[0] + sub[row, cols[0]])
        thetas.append(theta[row, cols[0]])
        assert mag[row, cols[0]] > 0
    estimates = np.array(estimates)
    assert abs(estimates.mean() - truth) < 0.15
    assert estimates.std() < 0.05
    # theta is the across-line angle; for a vertical line that is ~0 or ~pi
    across = np.abs(np.median(thetas))
    assert min(across, abs(across - np.pi)) < 0.15
    # the line's own strike (theta + pi/2) is then ~pi/2, i.e. vertical
    strike = line_orientation(np.median(thetas))
    assert abs(strike - np.pi / 2) < 0.15, strike


def test_steger_detects_no_line_in_flat_or_planar_surfaces():
    flat = np.zeros((40, 40))
    sub, mag, _ = steger(flat, sigma=1.0)
    assert not np.isfinite(sub).any() and np.all(mag == 0)
    yy, xx = np.mgrid[0:40, 0:40].astype(float)
    planar = 0.05 * xx
    sub, _, _ = steger(planar, sigma=1.0)
    assert not np.isfinite(sub).any()


def test_frangi_prefers_a_line_to_a_blob_of_the_same_width_and_contrast():
    """Frangi's Rb term is the point: matched width/contrast, a line must win.

    A Gaussian ridge has one near-zero Hessian eigenvalue (along the line); an
    isotropic blob of the same sigma has |l1| = |l2|, which the Rb factor
    suppresses by exp(-Rb^2/2b^2) = exp(-2) at b = 0.5.
    """
    sigma = 1.5
    line = straight_line(sigma=sigma, value=-1.0, offset=0.0)
    yy, xx = np.mgrid[0:81, 0:81].astype(float)
    blob = -np.exp(-((yy - 40.0) ** 2 + (xx - 40.0) ** 2) / (2 * sigma ** 2))
    v_line, s_line, _ = frangi(line, sigmas=[1.0, 1.5, 2.0], mode="dark")
    v_blob, _, _ = frangi(blob, sigmas=[1.0, 1.5, 2.0], mode="dark")
    # at the structure centre the line is ~6x the blob (Rb factor exp(-2) ~ 0.135)
    assert v_line[40, 40] > 5 * v_blob[40, 40]
    # the winning scale must match the line width, not the smallest/largest offer
    assert 1.0 <= s_line.max() <= 2.0
    # response on the line centre beats the same row away from the line
    assert v_line[40, 40] > v_line[40, 20]


def test_frangi_dark_mode_fires_on_the_flanks_of_a_bright_ridge_not_its_crest():
    img = straight_line(value=+1.0, sigma=1.2)
    bright, _, _ = frangi(img, sigmas=[1.0], mode="bright")
    dark, _, _ = frangi(img, sigmas=[1.0], mode="dark")
    crest = {40, 41}                            # ridge centre is at x = 40.5
    assert np.argmax(bright[40]) in crest
    assert np.argmax(dark[40]) not in crest, "dark mode fired on the crest"
    assert dark.max() > 0 and bright.max() > 0
    assert bright[40, 40] > dark[40, 40]


def test_hessian_matches_analytic_second_derivative_of_a_quadratic():
    yy, xx = np.mgrid[0:31, 0:31].astype(float)
    a = 3.0 * xx ** 2 + 0.5 * yy ** 2
    dyy, dxy, dxx = hessian(a, sigma=0.9)
    # interior nodes: d2/dx2 = 6, d2/dy2 = 1, dxy = 0 (Gaussian smoothing of a
    # quadratic returns the same quadratic, so this is exact up to edge effects)
    assert abs(dxx[15, 15] - 6.0) < 0.6
    assert abs(dyy[15, 15] - 1.0) < 0.3
    assert abs(dxy[15, 15]) < 0.1


def test_principal_eigenvalues_orders_by_magnitude_for_a_perfect_ridge():
    # a ridge along y has Dyy = 0 and Dxx < 0; the dominant-magnitude eigenvalue
    # must be Dxx (negative), not the identically zero along-line eigenvalue
    dyy = np.zeros((3, 3))
    dxy = np.zeros((3, 3))
    dxx = np.full((3, 3), -2.0)
    big, small = principal_eigenvalues(dyy, dxy, dxx)
    assert np.all(big == -2.0) and np.all(small == 0.0)


def test_ridge_density_is_one_for_parallel_lines_and_low_for_random():
    assert ridge_density(np.full(50, 0.7)) == pytest.approx(1.0)
    rng = np.random.default_rng(7)
    random_angles = rng.uniform(0, np.pi, 400)
    assert ridge_density(random_angles) < 0.15
    orthogonal = np.concatenate([np.full(50, 0.0), np.full(50, np.pi / 2)])
    assert ridge_density(orthogonal) < 0.05


def test_scales_m_refuses_unresolvable_scales():
    assert scales_m([6.0, 9.0, 15.0], 3.0) == [2.0, 3.0, 5.0]
    with pytest.raises(ValueError):
        scales_m([2.0], 3.0)
    with pytest.raises(ValueError):
        scales_m([10.0], 100.0)


def test_steger_rejects_nan_input():
    img = np.zeros((10, 10))
    img[5, 5] = np.nan
    with pytest.raises(ValueError):
        steger(img, sigma=1.0)
