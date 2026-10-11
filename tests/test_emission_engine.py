#!/usr/bin/env python3
"""Unit tests for the emission engine: commit / uncommit exactness against components().

Run: ``python -m pytest tests/test_emission_engine.py -q`` or directly with python.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import emit_and_ship as E          # noqa: E402
from gems64.metric import components   # noqa: E402


def _draws(H, W, R, ncell, rng):
    out = []
    for _ in range(R):
        d = np.zeros((H, W), bool)
        d[rng.integers(3, H - 3, ncell), rng.integers(3, W - 3, ncell)] = True
        out.append(d)
    return out


def _check(H, W, R, nc, ncell, seed, n_flank):
    rng = np.random.default_rng(seed)
    draws = _draws(H, W, R, ncell, rng)
    rho = np.ones(H * W)
    if n_flank:
        rho[rng.choice(H * W, size=n_flank, replace=False)] = E.RHO_FLANK
    cells = list(map(int, rng.choice(H * W, size=nc, replace=False)))

    # --- commit reproduces components() exactly when rho == 1 everywhere ------------------
    e = E.Ensemble(draws, rho)
    for c in cells:
        e.commit(c)
    p = np.zeros(H * W)
    p[cells] = 1.0
    p = p.reshape(H, W)
    if n_flank == 0:
        for r, d in enumerate(draws):
            cc = components(p, d)
            assert abs(e.T[r] - cc["TP_w"]) < 1e-9, (r, e.T[r], cc["TP_w"])
            assert abs(e.S - cc["S"]) < 1e-12

    # --- single drop: uncommit == fresh ensemble without those cells ----------------------
    drop = [cells[5], cells[11], cells[-1]]
    for c in drop:
        e.uncommit(c)
    ref = E.Ensemble(draws, rho)
    for c in cells:
        if c not in drop:
            ref.commit(c)
    assert np.allclose(e.T, ref.T, atol=1e-9), (e.T, ref.T)
    assert np.allclose(e.M, ref.M, atol=1e-9), (e.M, ref.M)
    assert e.S == ref.S
    assert abs(e.dti_mean() - ref.dti_mean()) < 1e-9

    # --- recommit round-trips exactly (this is what the incremental version failed) -------
    for c in drop:
        e.commit(c)
    full = E.Ensemble(draws, rho)
    for c in cells:
        full.commit(c)
    assert np.allclose(e.T, full.T, atol=1e-9), (e.T, full.T)
    assert np.allclose(e.M, full.M, atol=1e-9), (e.M, full.M)
    assert e.S == full.S

    # --- interleaved stress ---------------------------------------------------------------
    for _ in range(8):
        order = list(cells)
        rng.shuffle(order)
        a, b, c_, d_ = min(20, nc), min(7, nc), min(26, nc), min(11, nc)
        e2 = E.Ensemble(draws, rho)
        for x in order[:a]:
            e2.commit(x)
        for x in order[:b]:
            e2.uncommit(x)
        for x in order[a:c_]:
            e2.commit(x)
        for x in order[b:d_]:
            e2.uncommit(x)
        final = (set(order[b:a]) | set(order[a:c_])) - set(order[b:d_])
        r3 = E.Ensemble(draws, rho)
        for x in sorted(final):
            r3.commit(x)
        assert np.allclose(e2.T, r3.T, atol=1e-9), (e2.T, r3.T)
        assert np.allclose(e2.M, r3.M, atol=1e-9), (e2.M, r3.M)
        assert e2.S == r3.S
        assert abs(e2.dti_mean() - r3.dti_mean()) < 1e-9
    return True


def test_commit_uncommit_exact():
    cases = [(60, 60, 4, 30, 45, 3, 0), (60, 60, 8, 40, 45, 11, 5),
             (40, 50, 3, 20, 30, 7, 0), (80, 80, 32, 120, 60, 5, 12)]
    for H, W, R, nc, ncell, seed, nf in cases:
        assert _check(H, W, R, nc, ncell, seed, nf), (H, W, R, nc, seed)


if __name__ == "__main__":
    import time

    t0 = time.time()
    for H, W, R, nc, ncell, seed, nf in [(60, 60, 4, 30, 45, 3, 0), (60, 60, 8, 40, 45, 11, 5),
                                         (40, 50, 3, 20, 30, 7, 0), (80, 80, 32, 120, 60, 5, 12)]:
        _check(H, W, R, nc, ncell, seed, nf)
        print(f"  PASS H={H} W={W} R={R} n={nc} n_flank={nf}")
    print(f"ALL EMISSION-ENGINE TESTS PASS [{time.time()-t0:.1f}s]")


def test_delta_T_and_kmax_exact_vs_brute_force():
    """The vectorised lazy-greedy fields must equal commit()-and-measure, cell by cell."""
    rng = np.random.default_rng(17)
    H = W = 40
    R = 5
    draws = _draws(H, W, R, 30, rng)
    rho = np.ones(H * W)
    rho[rng.choice(H * W, 4, replace=False)] = E.RHO_FLANK
    ens = E.Ensemble(draws, rho)
    cells = list(map(int, rng.choice(H * W, 12, replace=False)))
    for c in cells[:5]:
        ens.commit(c)
    test = np.array(sorted(rng.choice(H * W, 40, replace=False)), dtype=np.int64)
    dT = ens.delta_T(test)
    km = ens.kmax(test)
    for i, c in enumerate(test):
        e2 = E.Ensemble(draws, rho)
        for x in cells[:5]:
            e2.commit(x)
        T0, M0 = e2.T.copy(), e2.M.copy()
        e2.commit(int(c))
        assert np.allclose(e2.T - T0, dT[i], atol=1e-9), (c, e2.T - T0, dT[i])
        assert np.allclose(e2.M - M0, km[i], atol=1e-9), (c, e2.M - M0, km[i])


def test_kernel_lattice_is_the_euclidean_disk():
    """k(d) = max(1 - d/R, 0) with R = 3 px admits exactly 25 lattice offsets and 6 weights."""
    from gems64.metric import lattice_kernel_values

    v = lattice_kernel_values()
    dy = np.array([a[0] for a in v])
    dx = np.array([a[1] for a in v])
    k = np.array([a[2] for a in v])
    assert len(v) == 25
    assert (dy ** 2 + dx ** 2 < 9).all()
    assert abs(dy).max() == 2 and abs(dx).max() == 2
    assert sorted(np.round(np.unique(k), 6).tolist()) == [
        0.057191, 0.254644, 0.333333, 0.528595, 0.666667, 1.0]
    assert abs(float(k.sum()) - 9.380298) < 1e-5


if __name__ == "__main__":
    test_delta_T_and_kmax_exact_vs_brute_force()
    print("  PASS delta_T/kmax exact vs brute force")
    test_kernel_lattice_is_the_euclidean_disk()
    print("  PASS kernel lattice = euclidean disk, 25 offsets, 6 weights")
