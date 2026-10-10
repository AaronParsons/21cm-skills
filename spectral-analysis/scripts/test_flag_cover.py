"""Tests for flag_cover.py.  Run from the repo root:

    python -m pytest skills/spectral-analysis/scripts/test_flag_cover.py
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flag_cover import FilterBank, pattern_cover, separable_cover  # noqa: E402


def brute_separable(F):
    """Minimum additive cost Σ row_cost + Σ col_cost over all covers."""
    nr, nc = F.shape
    rc, cc = (~F).sum(1), (~F).sum(0)
    best = None
    for r in itertools.product([False, True], repeat=nr):
        r = np.array(r)
        cols = (F & ~r[:, None]).any(0)             # columns the rows leave uncovered
        cost = int(rc[r].sum() + cc[cols].sum())
        best = cost if best is None else min(best, cost)
    return best


@pytest.mark.parametrize("seed", range(40))
def test_separable_cover_is_optimal(seed):
    rng = np.random.default_rng(seed)
    F = rng.random((6, 7)) < rng.uniform(0.05, 0.4)
    rows, cols = separable_cover(F)
    cover = rows[:, None] | cols[None, :]
    assert cover[F].all()
    additive = int((~F).sum(1)[rows].sum() + (~F).sum(0)[cols].sum())
    assert additive == brute_separable(F)
    assert int((cover & ~F).sum()) <= additive      # union counts overlaps once


def test_separable_cover_prefers_columns_for_rfi_channels():
    F = np.zeros((50, 20), bool)
    F[:, 3] = True                                  # a channel flagged at all times
    F[::7, 11] = True                               # an intermittent channel
    F[17, :] = True                                 # one bad time
    rows, cols = separable_cover(F)
    assert cols[3] and cols[11] and rows[17]
    assert rows.sum() == 1 and cols.sum() == 2


def test_pattern_cover_contains_every_slice():
    rng = np.random.default_rng(1)
    F = rng.random((30, 4, 25)) < 0.05             # (time, baseline, channel)
    for K in (1, 2, 5):
        c = pattern_cover(F, max_patterns=K)
        assert c.n_patterns <= K
        C = c.covered()
        assert C.shape == F.shape
        assert C[F].all()


def test_pattern_cover_exact_when_unconstrained():
    F = np.zeros((10, 8), bool)
    F[:5, 2] = True
    F[5:, 6] = True
    c = pattern_cover(F)                            # no limit: no merging
    assert c.n_patterns == 2 and c.extra_fraction() == 0


def test_pattern_cover_extra_grows_as_patterns_shrink():
    rng = np.random.default_rng(2)
    F = rng.random((200, 40)) < 0.03
    extras = [pattern_cover(F, max_patterns=K).extra_fraction() for K in (50, 10, 3, 1)]
    assert all(a <= b + 1e-12 for a, b in zip(extras, extras[1:]))
    # K = 1 is the union of all row masks
    one = pattern_cover(F, max_patterns=1)
    assert np.array_equal(one.masks[0], F.any(0))


def test_pattern_cover_extra_budget_and_drop():
    rng = np.random.default_rng(3)
    F = rng.random((100, 30)) < 0.02
    F[7] = True                                     # fully flagged slice
    c = pattern_cover(F, max_extra_frac=0.01, drop_frac=0.5)
    assert c.assign[7] == -1
    assert c.extra_fraction() <= 0.01 + 1e-12
    assert c.covered()[F].all()


def test_filterbank_matches_per_slice_weighted_fit():
    rng = np.random.default_rng(4)
    nf, nm = 32, 5
    A = np.linalg.qr(rng.normal(size=(nf, nm)))[0]
    F = np.zeros((12, nf), bool)
    F[:6, 4] = True
    F[6:, [10, 20]] = True
    c = pattern_cover(F)
    X = rng.normal(size=(12, nf)) + 1j * rng.normal(size=(12, nf))
    X[F] = 1e6                                      # flagged values must not matter
    bank = FilterBank(A, c, ridge=0.0)
    co = bank.coefficients(X)
    for t in range(12):
        w = (~c.covered()[t]).astype(float)
        G = (A.T * w) @ A
        ref = np.linalg.solve(G, (A.T * w) @ X[t])
        assert np.allclose(co[t], ref)
    r = bank.residual(X)
    assert np.isnan(r[F]).all()


def test_filterbank_drops_and_shapes():
    rng = np.random.default_rng(5)
    nf = 16
    A = np.linalg.qr(rng.normal(size=(nf, 3)))[0]
    F = rng.random((5, 3, nf)) < 0.05
    F[2, 1] = True
    c = pattern_cover(F, max_patterns=2, drop_frac=0.9)
    bank = FilterBank(A, c)
    m = bank.fit(rng.normal(size=F.shape))
    assert m.shape == F.shape
    assert np.isnan(m[2, 1]).all()
