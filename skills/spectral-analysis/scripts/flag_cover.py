"""Cover a flag mask with a few shapes, so a few DPSS filters serve all slices.

A per-slice weighted fit with a mask that changes from slice to slice has a
different bias in every slice, which scatters bright power along the other
axis (see ../SKILL.md, "Broadcasting flags").  Flagging more data so that
slices share masks removes that, and lets one filter be built per mask and
reused.  This module finds covers that do so at little cost in data.

Flags are boolean arrays whose LAST axis is the filter axis (e.g. frequency for
a delay filter); every other axis indexes slices (time, baseline, ...).

    separable_cover(flags2d)        exact: which whole rows and columns to flag
                                    so their union covers every flagged cell,
                                    at minimum cost (one filter per axis).
    pattern_cover(flags, ...)       greedy: K filter-axis masks; each slice is
                                    assigned one that contains its own flags
                                    (or dropped).  Union of K outer products.
    FilterBank(A, cover)            one weighted DPSS projector per mask,
                                    applied to every slice assigned to it.

Only numpy and scipy are needed.  Example:

    cover = pattern_cover(flags, max_patterns=4, drop_frac=0.5)
    print(cover.summary())
    bank = FilterBank(A, cover)               # A: (nf, nmodes) DPSS basis
    model = bank.fit(data)                    # same shape as data
"""

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_flow

__all__ = ["separable_cover", "pattern_cover", "PatternCover", "FilterBank"]


# ----------------------------------------------------------------------
# Separable cover: minimum-weight bipartite vertex cover (König), exact
# ----------------------------------------------------------------------

def separable_cover(flags, row_cost=None, col_cost=None):
    """Rows and columns to flag so that every flagged cell lies in one of them.

    flags : (nrow, ncol) bool.
    row_cost, col_cost : nonnegative integer cost of flagging each row / column.
        Default: the number of currently unflagged cells it would remove, so the
        total cost is the number of extra cells flagged.

    Returns (rows, cols), boolean arrays.  Each flagged cell is an edge
    (row, col) of a bipartite graph; a minimum-weight vertex cover is a minimum
    cut (source -> row: row cost; row -> col: infinite; col -> sink: col cost),
    so the cover is exactly optimal for the ADDITIVE cost Σ row_cost + Σ col_cost.
    With the default costs that counts an unflagged cell where a chosen row
    meets a chosen column twice, so it is an upper bound on the number of extra
    cells flagged.  Minimising the union exactly adds a row-column interaction a
    cut cannot represent; the bound is tight when the chosen rows and columns
    rarely intersect, as with a few bad channels and a few bad times.
    """
    F = np.asarray(flags, dtype=bool)
    if F.ndim != 2:
        raise ValueError("separable_cover needs a 2-D mask")
    nr, nc = F.shape
    rc = (~F).sum(1) if row_cost is None else np.asarray(row_cost)
    cc = (~F).sum(0) if col_cost is None else np.asarray(col_cost)
    rc, cc = np.asarray(rc, dtype=np.int64), np.asarray(cc, dtype=np.int64)
    if (rc < 0).any() or (cc < 0).any():
        raise ValueError("costs must be nonnegative")
    rows = np.zeros(nr, bool)
    cols = np.zeros(nc, bool)
    if not F.any():
        return rows, cols
    # Free vertices (zero cost) that touch a flag go in the cover directly.
    rows |= (rc == 0) & F.any(1)
    cols |= (cc == 0) & F.any(0)
    R = F & ~rows[:, None] & ~cols[None, :]
    if not R.any():
        return rows, cols
    big = int(rc.sum() + cc.sum() + 1)
    src, snk = nr + nc, nr + nc + 1
    ri, ci = np.nonzero(R)
    u = np.concatenate([np.full(nr, src), ri, nr + np.arange(nc)])
    v = np.concatenate([np.arange(nr), nr + ci, np.full(nc, snk)])
    cap = np.concatenate([rc, np.full(ri.size, big), cc]).astype(np.int32 if big < 2**31 else np.int64)
    G = csr_matrix((cap, (u, v)), shape=(nr + nc + 2, nr + nc + 2))
    flow = maximum_flow(G, src, snk).flow
    resid = (G - flow).tocsr()
    resid.eliminate_zeros()
    # Vertices reachable from the source in the residual graph (positive capacity).
    seen = np.zeros(nr + nc + 2, bool)
    seen[src] = True
    stack = [src]
    indptr, indices, data = resid.indptr, resid.indices, resid.data
    while stack:
        x = stack.pop()
        for k in range(indptr[x], indptr[x + 1]):
            y = indices[k]
            if data[k] > 0 and not seen[y]:
                seen[y] = True
                stack.append(y)
    # Reverse edges of saturated flow also count (flow on y->x lets x->y).
    # csgraph's flow matrix is antisymmetric, so G - flow already includes them.
    rows |= ~seen[:nr] & R.any(1)
    cols |= seen[nr:nr + nc] & R.any(0)
    covered = rows[:, None] | cols[None, :]
    if not covered[F].all():                      # guard: should never trigger
        raise RuntimeError("separable_cover failed to cover all flags")
    return rows, cols


# ----------------------------------------------------------------------
# Pattern cover: K masks on the filter axis, each slice assigned one
# ----------------------------------------------------------------------

@dataclass
class PatternCover:
    """masks[k] (nf,) bool; assign (nslice,) int in [0, K) or -1 (slice dropped);
    shape: the leading (slice) shape of the original flags."""
    masks: np.ndarray
    assign: np.ndarray
    shape: tuple
    flags: np.ndarray            # original flags, (nslice, nf)

    @property
    def n_patterns(self):
        return len(self.masks)

    def covered(self):
        """The cover as a flag array of the original shape (True = flagged)."""
        out = np.ones_like(self.flags)
        ok = self.assign >= 0
        out[ok] = self.masks[self.assign[ok]]
        return out.reshape(self.shape + (self.flags.shape[-1],))

    def extra_fraction(self):
        """Extra flagged cells as a fraction of all cells."""
        C = self.covered().reshape(self.flags.shape)
        return float((C & ~self.flags).sum() / self.flags.size)

    def summary(self):
        C = self.covered().reshape(self.flags.shape)
        n_drop = int((self.assign < 0).sum())
        return (f"{self.n_patterns} masks for {self.flags.shape[0]} slices "
                f"({n_drop} dropped); flagged {100 * self.flags.mean():.2f}% -> "
                f"{100 * C.mean():.2f}% (extra {100 * self.extra_fraction():.2f}%)")


def pattern_cover(flags, max_patterns=None, max_extra_frac=None, drop_frac=None):
    """Assign every slice a filter-axis mask that contains its flags.

    flags : bool array (..., nf); every leading index is a slice.
    max_patterns : stop merging once at most this many masks remain.
    max_extra_frac : stop before a merge would push the extra flagged fraction
        (of all cells) above this.  With both given, max_patterns wins: merging
        continues past max_extra_frac until the count is reached.
    drop_frac : slices with more than this fraction flagged are dropped (all
        flagged, no filter needed) rather than given masks of their own.

    Greedy agglomerative merging of the distinct masks: at each step the pair
    whose union adds the fewest flagged cells (weighted by how many slices use
    each) is merged.  The result is a union of outer products
    (slices assigned to k) x masks[k].  Not guaranteed optimal; exact when no
    merging is needed.
    """
    F = np.asarray(flags, dtype=bool)
    shape = F.shape[:-1]
    nf = F.shape[-1]
    F2 = F.reshape(-1, nf)
    assign = np.full(F2.shape[0], -1, dtype=int)
    keep = np.ones(F2.shape[0], bool)
    if drop_frac is not None:
        keep = F2.mean(1) <= drop_frac
    uniq, inv = np.unique(F2[keep], axis=0, return_inverse=True)
    inv = np.ravel(inv)
    if uniq.shape[0] == 0:
        return PatternCover(np.zeros((0, nf), bool), assign, shape, F2)
    counts = np.bincount(inv, minlength=uniq.shape[0]).astype(float)
    masks = uniq.astype(bool).copy()
    members = [[i] for i in range(len(masks))]         # unique patterns in each mask
    total = F2.size
    extra_now = 0.0

    alive = list(range(len(masks)))
    # Merging groups i and j gives every slice of i the extra flags M_j \ M_i and
    # every slice of j the flags M_i \ M_j, so the added cost is exactly
    # n_i |M_j \ M_i| + n_j |M_i \ M_j|, with n the number of slices per group.
    weight = counts.copy()                             # slices per group
    def pair_costs():
        M = masks[alive].astype(float)
        sz = M.sum(1)
        inter = M @ M.T
        w = weight[alive]
        c = w[:, None] * (sz[None, :] - inter) + w[None, :] * (sz[:, None] - inter)
        np.fill_diagonal(c, np.inf)
        return c

    while len(alive) > 1:
        need = max_patterns is not None and len(alive) > max_patterns
        c = pair_costs()
        a, b = np.unravel_index(np.argmin(c), c.shape)
        add = c[a, b]
        if not need:
            if max_extra_frac is None or (extra_now + add) / total > max_extra_frac:
                break
        i, j = alive[a], alive[b]
        masks[i] = masks[i] | masks[j]
        members[i] += members[j]
        weight[i] += weight[j]
        extra_now += add
        alive.remove(j)
    out_masks = masks[alive]
    group_of = np.empty(len(uniq), int)
    for k, g in enumerate(alive):
        for m in members[g]:
            group_of[m] = k
    assign[np.nonzero(keep)[0]] = group_of[inv]
    return PatternCover(out_masks, assign, shape, F2)


# ----------------------------------------------------------------------
# One weighted projector per mask
# ----------------------------------------------------------------------

class FilterBank:
    """Weighted least-squares fits to a basis A (nf, nmodes), one per mask.

    For mask k (True = flagged) the fit is c = (A^H W_k A + ridge)^-1 A^H W_k x,
    with W_k = diag(weights * ~mask_k).  `weights` (nf,) must be the same for
    every slice that shares a mask; that is what makes the filter reusable.
    Dropped slices (assign -1) return NaN.
    """

    def __init__(self, A, cover, weights=None, ridge=1e-9):
        A = np.asarray(A)
        nf = A.shape[0]
        if cover.masks.shape[1:] != (nf,):
            raise ValueError("basis and masks disagree on the filter-axis length")
        w0 = np.ones(nf) if weights is None else np.asarray(weights, float)
        self.A, self.cover = A, cover
        self.ops = []
        for m in cover.masks:
            w = w0 * ~m
            G = (A.conj().T * w) @ A
            G = G + ridge * np.trace(G).real / max(G.shape[0], 1) * np.eye(G.shape[0])
            self.ops.append(np.linalg.solve(G, A.conj().T * w))      # (nmodes, nf)

    def coefficients(self, data):
        """data: (..., nf) matching the cover's slice shape -> (..., nmodes)."""
        X = np.asarray(data).reshape(-1, self.A.shape[0])
        if X.shape[0] != self.cover.assign.size:
            raise ValueError("data do not match the cover's slices")
        out = np.full((X.shape[0], self.A.shape[1]), np.nan, dtype=np.result_type(X, self.A))
        for k, op in enumerate(self.ops):
            sel = self.cover.assign == k
            if sel.any():
                Xk = np.where(self.cover.masks[k][None, :], 0, X[sel])  # flagged values unused
                out[sel] = Xk @ op.T
        return out.reshape(self.cover.shape + (self.A.shape[1],))

    def fit(self, data):
        """The fitted model, same shape as data."""
        c = self.coefficients(data)
        return c @ self.A.T

    def residual(self, data):
        """data − fit, with every cell the cover flags set to NaN."""
        r = np.asarray(data) - self.fit(data)
        return np.where(self.cover.covered(), np.nan, r)
