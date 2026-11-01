import numpy as np
from scipy.stats import poisson

MAX_GOALS = 10
MAX_HALF_GOALS = 8
TOTAL_LINES = (1.5, 2.5, 3.5, 4.5)


def poisson_vector(lam, size):
    probs = poisson.pmf(np.arange(size + 1), lam)
    probs[-1] += max(0.0, 1 - probs.sum())
    return probs


def score_matrix(lam_home, lam_away, rho=0.0, max_goals=MAX_GOALS):
    matrix = np.outer(poisson_vector(lam_home, max_goals), poisson_vector(lam_away, max_goals))
    matrix[0, 0] *= 1 - lam_home * lam_away * rho
    matrix[0, 1] *= 1 + lam_home * rho
    matrix[1, 0] *= 1 + lam_away * rho
    matrix[1, 1] *= 1 - rho
    return matrix / matrix.sum()


def result_probs(matrix):
    return float(np.tril(matrix, -1).sum()), float(np.trace(matrix)), float(np.triu(matrix, 1).sum())


def total_distribution(matrix):
    size = matrix.shape[0] + matrix.shape[1] - 1
    totals = np.zeros(size)
    for i in range(matrix.shape[0]):
        totals[i:i + matrix.shape[1]] += matrix[i]
    return totals


def over_prob(totals, line):
    return float(totals[int(np.floor(line)) + 1:].sum())


def btts_prob(matrix):
    return float(matrix[1:, 1:].sum())


def half_matrices(lam_home, lam_away, shares):
    first = score_matrix(lam_home * shares["home_1h"], lam_away * shares["away_1h"], max_goals=MAX_HALF_GOALS)
    second = score_matrix(lam_home * (1 - shares["home_1h"]), lam_away * (1 - shares["away_1h"]), max_goals=MAX_HALF_GOALS)
    return first, second


def ht_ft_probs(first, second):
    size = first.shape[0]
    goals = np.arange(size)
    ht_sign = np.sign(goals[:, None] - goals[None, :])
    combined = np.einsum("ab,cd->abcd", first, second)
    ft_home = goals[:, None, None, None] + goals[None, None, :, None]
    ft_away = goals[None, :, None, None] + goals[None, None, None, :]
    ft_sign = np.sign(ft_home - ft_away)
    labels = {1: "1", 0: "X", -1: "2"}
    probs = {}
    for ht in (1, 0, -1):
        for ft in (1, 0, -1):
            mask = (ht_sign[:, :, None, None] == ht) & (ft_sign == ft)
            probs[f"htft_{labels[ht]}/{labels[ft]}"] = float(combined[mask].sum())
    return probs


def market_probs(lam_home, lam_away, rho, shares):
    matrix = score_matrix(lam_home, lam_away, rho)
    totals = total_distribution(matrix)
    home, draw, away = result_probs(matrix)
    first, second = half_matrices(lam_home, lam_away, shares)
    first_totals, second_totals = total_distribution(first), total_distribution(second)
    ht_home, ht_draw, ht_away = result_probs(first)

    probs = {
        "home": home, "draw": draw, "away": away,
        "dc_1x": home + draw, "dc_12": home + away, "dc_x2": draw + away,
        "btts_yes": btts_prob(matrix), "btts_no": 1 - btts_prob(matrix),
        "ht_home": ht_home, "ht_draw": ht_draw, "ht_away": ht_away,
        "ht_over_0.5": over_prob(first_totals, 0.5), "ht_over_1.5": over_prob(first_totals, 1.5),
        "2h_over_0.5": over_prob(second_totals, 0.5), "2h_over_1.5": over_prob(second_totals, 1.5),
        "both_halves_over_1.5": over_prob(first_totals, 1.5) * over_prob(second_totals, 1.5),
        "both_halves_btts": btts_prob(first) * btts_prob(second),
        "goals_6plus": over_prob(totals, 5.5),
        "early_goal_0_15": 1 - float(np.exp(-(lam_home + lam_away) * shares["early"])),
    }
    for line in TOTAL_LINES:
        probs[f"over_{line}"] = over_prob(totals, line)
        probs[f"under_{line}"] = 1 - probs[f"over_{line}"]
    probs.update(ht_ft_probs(first, second))
    return probs, matrix


def top_scores(matrix, k=3):
    flat = np.argsort(matrix, axis=None)[::-1][:k]
    return [(int(i), int(j), float(matrix[i, j])) for i, j in zip(*np.unravel_index(flat, matrix.shape))]
