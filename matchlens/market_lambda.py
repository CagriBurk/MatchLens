import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import poisson

from matchlens.odds import split_line

GRID = np.arange(0.10, 4.51, 0.01)
MAX_GOALS = 10
DEFAULT_RHO = -0.07


class ImpliedLambda:
    def __init__(self, rho=DEFAULT_RHO, grid=GRID):
        lam_home, lam_away = (a.ravel() for a in np.meshgrid(grid, grid, indexing="ij"))
        goals = np.arange(MAX_GOALS + 1)
        home_pmf = poisson.pmf(goals[None, :], lam_home[:, None])
        away_pmf = poisson.pmf(goals[None, :], lam_away[:, None])
        matrix = home_pmf[:, :, None] * away_pmf[:, None, :]
        matrix[:, 0, 0] *= 1 - lam_home * lam_away * rho
        matrix[:, 0, 1] *= 1 + lam_home * rho
        matrix[:, 1, 0] *= 1 + lam_away * rho
        matrix[:, 1, 1] *= 1 - rho
        matrix /= matrix.sum(axis=(1, 2), keepdims=True)
        diff = goals[:, None] - goals[None, :]
        total = goals[:, None] + goals[None, :]
        self.lam_home, self.lam_away = lam_home, lam_away
        self.home = (matrix * (diff > 0)).sum(axis=(1, 2))
        self.away = (matrix * (diff < 0)).sum(axis=(1, 2))
        self.totals = np.stack([(matrix * (total == k)).sum(axis=(1, 2)) for k in range(2 * MAX_GOALS + 1)], axis=1)
        self.tree_result = cKDTree(np.column_stack([self.home, self.away]))
        self.line_trees = {}

    def line_probability(self, line):
        win = np.zeros(len(self.home))
        push = np.zeros(len(self.home))
        parts = split_line(line)
        for part in parts:
            win += self.totals[:, int(np.floor(part)) + 1:].sum(axis=1) / len(parts)
            if float(part).is_integer():
                push += self.totals[:, int(part)] / len(parts)
        return win / (1 - push)

    def line_tree(self, line):
        key = round(float(line), 2)
        if key not in self.line_trees:
            self.line_trees[key] = cKDTree(np.column_stack([self.home, self.away, self.line_probability(key)]))
        return self.line_trees[key]

    def solve(self, p_home, p_away, p_over=None, line=2.5):
        p_home, p_away = np.atleast_1d(p_home).astype(float), np.atleast_1d(p_away).astype(float)
        lam_home = np.full(len(p_home), np.nan)
        lam_away = np.full(len(p_home), np.nan)
        valid = np.isfinite(p_home) & np.isfinite(p_away)
        has_over = np.zeros(len(p_home), dtype=bool)
        if p_over is not None:
            p_over = np.atleast_1d(p_over).astype(float)
            has_over = valid & np.isfinite(p_over)
            if has_over.any():
                points = np.column_stack([p_home[has_over], p_away[has_over], p_over[has_over]])
                _, idx = self.line_tree(line).query(points)
                lam_home[has_over], lam_away[has_over] = self.lam_home[idx], self.lam_away[idx]
        only_result = valid & ~has_over
        if only_result.any():
            _, idx = self.tree_result.query(np.column_stack([p_home[only_result], p_away[only_result]]))
            lam_home[only_result], lam_away[only_result] = self.lam_home[idx], self.lam_away[idx]
        return lam_home, lam_away


def fair_two_way(over, under):
    over, under = np.asarray(over, dtype=float), np.asarray(under, dtype=float)
    inv_over, inv_under = 1 / over, 1 / under
    return inv_over / (inv_over + inv_under)


def fair_three_way(home, draw, away):
    inv = 1 / np.column_stack([home, draw, away]).astype(float)
    return inv / inv.sum(axis=1, keepdims=True)
