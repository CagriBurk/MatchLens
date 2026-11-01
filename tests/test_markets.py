import numpy as np
import pytest
from scipy.stats import poisson

from matchlens import markets

SHARES = {"home_1h": 0.45, "away_1h": 0.44, "early": 0.13}


def test_score_matrix_sums_to_one():
    matrix = markets.score_matrix(1.6, 1.1, rho=-0.08)
    assert matrix.sum() == pytest.approx(1.0)
    assert (matrix >= 0).all()


def test_rho_zero_is_independent_poisson():
    matrix = markets.score_matrix(1.4, 0.9, rho=0.0)
    assert matrix[2, 1] == pytest.approx(poisson.pmf(2, 1.4) * poisson.pmf(1, 0.9), rel=1e-6)


def test_negative_rho_raises_draw_probability():
    _, draw_plain, _ = markets.result_probs(markets.score_matrix(1.3, 1.1, 0.0))
    _, draw_dc, _ = markets.result_probs(markets.score_matrix(1.3, 1.1, -0.1))
    assert draw_dc > draw_plain


def test_total_goals_poisson_sum():
    matrix = markets.score_matrix(1.5, 1.2, rho=0.0)
    totals = markets.total_distribution(matrix)
    assert markets.over_prob(totals, 2.5) == pytest.approx(1 - poisson.cdf(2, 2.7), abs=1e-6)


def test_market_probs_consistency():
    probs, _ = markets.market_probs(1.7, 1.0, -0.07, SHARES)
    assert probs["home"] + probs["draw"] + probs["away"] == pytest.approx(1.0)
    assert probs["dc_1x"] == pytest.approx(probs["home"] + probs["draw"])
    assert probs["over_2.5"] + probs["under_2.5"] == pytest.approx(1.0)
    assert probs["over_1.5"] > probs["over_2.5"] > probs["over_3.5"] > probs["over_4.5"] > probs["goals_6plus"]
    htft = sum(v for k, v in probs.items() if k.startswith("htft_"))
    assert htft == pytest.approx(1.0, abs=1e-6)
    assert probs["both_halves_over_1.5"] < min(probs["ht_over_1.5"], probs["2h_over_1.5"])
    assert probs["both_halves_btts"] < probs["btts_yes"]
    assert probs["ht_home"] + probs["ht_draw"] + probs["ht_away"] == pytest.approx(1.0)


def test_htft_marginals_match_half_results():
    probs, _ = markets.market_probs(1.5, 1.2, 0.0, SHARES, markets.NO_STATE_EFFECT)
    ht_home = sum(v for k, v in probs.items() if k.startswith("htft_1/"))
    assert ht_home == pytest.approx(probs["ht_home"], abs=1e-6)
    ft_draw = sum(v for k, v in probs.items() if k.startswith("htft_") and k.endswith("/X"))
    assert ft_draw == pytest.approx(probs["draw"], abs=1e-3)


def test_early_goal_formula():
    probs, _ = markets.market_probs(1.5, 1.0, 0.0, SHARES)
    assert probs["early_goal_0_15"] == pytest.approx(1 - np.exp(-2.5 * 0.13))


def test_top_scores_ordered():
    matrix = markets.score_matrix(1.5, 1.0, -0.05)
    top = markets.top_scores(matrix, 3)
    assert top[0][2] >= top[1][2] >= top[2][2]


def test_core_probs_match_scalar_version():
    lam_h, lam_a = np.array([1.6, 0.7]), np.array([1.1, 2.0])
    vector = markets.core_probs(lam_h, lam_a, -0.06)
    for i in range(2):
        scalar, _ = markets.market_probs(lam_h[i], lam_a[i], -0.06, SHARES)
        for key in ("home", "draw", "away", "btts_yes", "over_1.5", "over_2.5", "over_3.5"):
            assert vector[key][i] == pytest.approx(scalar[key], abs=1e-9)


def test_state_effect_raises_reversals_and_keeps_htft_normalised():
    plain, _ = markets.market_probs(1.5, 1.2, -0.05, SHARES, markets.NO_STATE_EFFECT)
    state, _ = markets.market_probs(1.5, 1.2, -0.05, SHARES)
    assert state["htft_1/2"] > plain["htft_1/2"]
    assert state["htft_2/1"] > plain["htft_2/1"]
    assert sum(v for k, v in state.items() if k.startswith("htft_")) == pytest.approx(1.0, abs=1e-6)
    assert state["ht_home"] == pytest.approx(plain["ht_home"])


def test_both_halves_markets_without_state_effect_are_products():
    probs, _ = markets.market_probs(1.5, 1.2, 0.0, SHARES, markets.NO_STATE_EFFECT)
    assert probs["both_halves_over_1.5"] == pytest.approx(probs["ht_over_1.5"] * probs["2h_over_1.5"], rel=1e-6)
