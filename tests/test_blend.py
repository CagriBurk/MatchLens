import pytest

from matchlens import blend, markets
from matchlens.market_lambda import ImpliedLambda

MODEL, MARKET = (1.8, 0.9), (1.4, 1.1)


def test_weight_zero_returns_market_and_one_returns_model():
    assert blend.blend_lambdas(MODEL, MARKET, 0.0) == pytest.approx(MARKET)
    assert blend.blend_lambdas(MODEL, MARKET, 1.0, 1.0) == pytest.approx(MODEL)


def test_total_weight_keeps_market_supremacy():
    home, away = blend.blend_lambdas(MODEL, MARKET, 0.5)
    assert home / away == pytest.approx(MARKET[0] / MARKET[1])
    assert MARKET[0] + MARKET[1] < home + away < MODEL[0] + MODEL[1]


def test_final_lambdas_fall_back_to_model():
    assert blend.final_lambdas("eng.1", MODEL, None) == (MODEL, "model")
    lams, source = blend.final_lambdas("eng.1", MODEL, MARKET)
    assert source == "b365" and lams == pytest.approx(MARKET)


def test_market_lambdas_from_bet365_row():
    probs = markets.core_probs([1.6], [1.0], -0.07)
    margin = 1.05
    row = {"b365_home": 1 / (probs["home"][0] * margin), "b365_draw": 1 / (probs["draw"][0] * margin),
           "b365_away": 1 / (probs["away"][0] * margin), "b365_goal_line": 2.5,
           "b365_over": 1 / (probs["over_2.5"][0] * margin), "b365_under": 1 / ((1 - probs["over_2.5"][0]) * margin)}
    lam_home, lam_away = blend.market_lambdas(ImpliedLambda(), row)
    assert lam_home == pytest.approx(1.6, abs=0.011)
    assert lam_away == pytest.approx(1.0, abs=0.011)
    assert blend.market_lambdas(ImpliedLambda(), {"b365_home": 2.0}) is None
