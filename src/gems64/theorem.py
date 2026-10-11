"""Numerical verification of the DTI-optimal decision rule on synthetic rasters.

Three independent checks (``scripts/e1_theorem.py`` runs them all):

``check_threshold_rule``
    For a *non-redundant* dot the accept bar is ``kappa > alpha * DTI``.  Sweep
    ``kappa`` and confirm the sign change sits exactly at ``alpha * DTI``, and
    that at ``alpha = 0.2`` with ``DTI = 0.30`` the bar is ``0.06`` (the number
    quoted in the lane brief).

``check_lipton_generalisation``
    Lipton, Elkan & Narayanaswamy (ECML-PKDD 2014) proved the F1-optimal
    independent threshold is half the optimal F1.  With a Tversky family
    ``alpha + beta = 1`` the same argument gives ``alpha * DTI*``.  Verified
    here by brute-force threshold search on synthetic Bernoulli rasters at
    ``alpha = 0.5`` (reproduces ``F1*/2``) and ``alpha = 0.2``.

``check_greedy_vs_exhaustive``
    On a small synthetic candidate set, enumerate *every* subset, compute the
    exact expected DTI, and confirm greedy-add + backward-prune lands on the
    global optimum.  The same function validates the mean-field expected-DTI
    formula against a Monte-Carlo over ``>= 32`` plausible Bernoulli truth
    rasters, which is what the full-grid selector actually assumes.
"""

from __future__ import annotations

import itertools

import numpy as np

from .metric import ALPHA, BETA, RADIUS_PX, kernel
from .select import ExpectedDtiGreedy, expected_dti, kappa_field


# --------------------------------------------------------------------- helpers
def _exact_expected_dti(w: np.ndarray, mask: np.ndarray,
                        alpha: float = ALPHA, beta: float = BETA) -> float:
    """Expected DTI of a binary dot set under independent Bernoulli truth ``w``.

    ``T = sum_g w_g * max_x k(x,g)`` (linearity of expectation over the truth
    indicator), ``F = sum_x (1 - kappa(x))``, ``K = sum_g w_g``.
    """
    kap = kappa_field(w, RADIUS_PX)
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return 0.0
    cred = np.zeros(w.shape, np.float64)
    for y, x in zip(ys, xs):
        y0, y1 = max(0, y - 3), min(w.shape[0], y + 4)
        x0, x1 = max(0, x - 3), min(w.shape[1], x + 4)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        cred[y0:y1, x0:x1] = np.maximum(cred[y0:y1, x0:x1], kernel(np.hypot(yy - y, xx - x)))
    T = float((w * cred).sum())
    F = float((1.0 - kap[ys, xs]).sum())
    K = float(w.sum())
    return expected_dti(T, F, K, alpha, beta)


def _mc_dti(w: np.ndarray, mask: np.ndarray, draws: int = 200, seed: int = 0,
            alpha: float = ALPHA, beta: float = BETA) -> tuple[float, float]:
    """Monte-Carlo DTI over Bernoulli truth draws (the 'plausible truth rasters'
    the selector is supposed to average over)."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    out = []
    for _ in range(draws):
        g = rng.random(w.shape) < w
        if not g.any() or ys.size == 0:
            out.append(0.0)
            continue
        gy, gx = np.nonzero(g)
        cred = np.zeros(w.shape, np.float64)
        for y, x in zip(ys, xs):
            y0, y1 = max(0, y - 3), min(w.shape[0], y + 4)
            x0, x1 = max(0, x - 3), min(w.shape[1], x + 4)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            cred[y0:y1, x0:x1] = np.maximum(cred[y0:y1, x0:x1], kernel(np.hypot(yy - y, xx - x)))
        T = float(cred[gy, gx].sum())
        F = 0.0   # realised self-credit of each dot under this draw
        for y, x in zip(ys, xs):
            y0, y1 = max(0, y - 3), min(w.shape[0], y + 4)
            x0, x1 = max(0, x - 3), min(w.shape[1], x + 4)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            kk = kernel(np.hypot(yy - y, xx - x))
            F += 1.0 - float((kk * g[y0:y1, x0:x1]).max())
        out.append(expected_dti(T, F, float(g.sum()), alpha, beta))
    return float(np.mean(out)), float(np.std(out) / np.sqrt(len(out)))


# ------------------------------------------------------------------- check 1
def check_threshold_rule(dti: float = 0.30, alpha: float = ALPHA) -> dict:
    """Non-redundant dot: accept iff kappa > alpha*DTI.  Verified by direct
    evaluation of the exact two-sided accept test on synthetic components."""
    T, K = 3000.0, 10_000.0
    # choose F so that DTI(T,F,K) == dti
    # dti = T/(alpha*(T+F)+beta*K) -> F = T/dti - beta*K - alpha*T   (alpha+beta=1)
    beta = 1.0 - alpha
    # dti = T / (alpha*(T+F) + beta*K)  ->  F = (T/dti - beta*K)/alpha - T
    F = float((T / dti - beta * K) / alpha - T)
    rows = []
    for kappa in np.linspace(0.001, 0.20, 200):
        dT = kappa            # non-redundant dot: marginal credit == self credit
        dF = 1.0 - kappa
        D0 = alpha * (T + F) + beta * K
        improves = (T + dT) / (D0 + alpha * (dT + dF)) > T / D0
        rows.append((float(kappa), bool(improves), float(alpha * dti)))
    bar = float(alpha * dti)
    accept = np.array([r[1] for r in rows])
    ks = np.array([r[0] for r in rows])
    idx = int(np.argmax(accept))
    empirical_bar = float(ks[idx])
    monotone = bool(np.all(~accept[:idx]) and np.all(accept[idx:]))
    return dict(alpha=alpha, dti=dti, analytic_bar=bar, empirical_bar=empirical_bar,
                abs_error=abs(empirical_bar - bar), monotone_in_kappa=monotone,
                quoted_0p2_0p30_bar=float(0.2 * 0.30),
                ok=bool(abs(empirical_bar - bar) < 0.002 and monotone))


# ------------------------------------------------------------------- check 2
def check_lipton_generalisation(alpha: float = 0.5, n: int = 400, seed: int = 7,
                                draws: int = 400) -> dict:
    """Optimal independent threshold on a synthetic Bernoulli raster equals
    ``alpha * DTI*`` (Lipton et al. give ``F1*/2`` for ``alpha = 0.5``)."""
    rng = np.random.default_rng(seed)
    p = rng.beta(0.5, 20.0, size=n)
    thr_grid = np.linspace(0.001, 0.5, 400)
    best = (-1.0, None)
    for t in thr_grid:
        pred = p >= t
        vals = []
        for _ in range(draws):
            y = rng.random(n) < p
            k = float((pred & y).sum())          # hard-prediction Tversky
            f = float((pred & ~y).sum())
            fn = float((~pred & y).sum())
            vals.append(k / (k + alpha * f + (1 - alpha) * fn + 1e-12))
        m = float(np.mean(vals))
        if m > best[0]:
            best = (m, float(t))
    dti_star, thr_star = best
    predicted = alpha * dti_star
    return dict(alpha=alpha, dti_star=dti_star, empirical_optimal_threshold=thr_star,
                predicted_bar=predicted, abs_error=abs(thr_star - predicted),
                rel_error=abs(thr_star - predicted) / max(thr_star, 1e-9),
                ok=bool(abs(thr_star - predicted) / max(thr_star, 1e-9) < 0.25))


# ------------------------------------------------------------------- check 3
def check_greedy_vs_exhaustive(seed: int = 3, n_cand: int = 13, size: int = 12,
                               mc_draws: int = 64) -> dict:
    rng = np.random.default_rng(seed)
    w = np.zeros((size, size), np.float64)
    # two short synthetic 'faults' plus scattered noise truth
    w[3, 2:9] = 0.55
    w[7, 4:10] = 0.35
    w[rng.integers(0, size, 8), rng.integers(0, size, 8)] = 0.20
    cand = np.array([[int(a), int(b)] for a in range(1, size - 1)
                     for b in range(1, size - 1)], np.int32)
    order = rng.permutation(cand.shape[0])[:n_cand]
    cand = cand[order]

    # exhaustive optimum over all subsets of the candidate set
    best_val, best_mask = -1.0, None
    for bits in range(1 << n_cand):
        m = np.zeros((size, size), bool)
        for q in range(n_cand):
            if bits >> q & 1:
                m[cand[q, 0], cand[q, 1]] = True
        v = _exact_expected_dti(w, m)
        if v > best_val:
            best_val, best_mask = v, m
    g = ExpectedDtiGreedy(w, cand)
    res = g.run(max_dots=n_cand, prune=True)
    greedy_val = _exact_expected_dti(w, g.mask())
    mc_mean, mc_se = _mc_dti(w, g.mask(), draws=mc_draws, seed=11)
    return dict(n_candidates=int(n_cand), subsets_enumerated=int(1 << n_cand),
                exhaustive_optimum=float(best_val), greedy_after_prune=float(greedy_val),
                greedy_optimality_gap=float(best_val - greedy_val),
                mean_field_expected_dti=float(res["expected_dti"]),
                mc_mean_dti=mc_mean, mc_se=mc_se,
                mc_draws=int(mc_draws),
                n_dots=int(res["n_dots"]), n_dots_optimal=int(best_mask.sum()),
                mean_field_vs_mc_z=float((res["expected_dti"] - mc_mean) / mc_se) if mc_se else 0.0,
                ok=bool(best_val - greedy_val < 1e-9))
