import numpy as np
import pandas as pd
import pytest

from matchlens import goal_calibration, markets

SHARES = {"home_1h": 0.45, "away_1h": 0.44, "early": 0.13}


def test_reweight_keeps_distribution_and_shifts_mass():
    matrix = markets.score_matrix(1.4, 1.1, -0.05)
    weights = np.ones(goal_calibration.GROUPS)
    weights[goal_calibration.MAX_TOTAL + 1 + 3] = 1.2
    adjusted = markets.reweight(matrix, weights)
    assert adjusted.sum() == pytest.approx(1.0)
    assert adjusted[2, 1] > matrix[2, 1] and adjusted[3, 0] < matrix[3, 0]
    assert markets.reweight(matrix, None) is matrix


def test_fit_recovers_neutral_weights_on_model_generated_data():
    rng = np.random.default_rng(3)
    lam_h, lam_a = rng.uniform(0.8, 2.0, 4000), rng.uniform(0.6, 1.6, 4000)
    preds = pd.DataFrame({"lam_home": lam_h, "lam_away": lam_a, "rho": 0.0,
                          "home_goals": rng.poisson(lam_h), "away_goals": rng.poisson(lam_a)})
    weights = goal_calibration.fit(preds)
    assert np.abs(weights - 1).max() < 0.15


def test_market_probs_use_goal_weights():
    weights = np.ones(goal_calibration.GROUPS)
    weights[goal_calibration.MAX_TOTAL + 1:] = 1.3
    base, _ = markets.market_probs(1.4, 1.1, -0.05, SHARES)
    tuned, _ = markets.market_probs(1.4, 1.1, -0.05, SHARES, goal_weights=weights)
    assert tuned["btts_yes"] > base["btts_yes"]
    assert tuned["home"] + tuned["draw"] + tuned["away"] == pytest.approx(1.0)
