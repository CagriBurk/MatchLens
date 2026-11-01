import numpy as np
import pandas as pd
import pytest

from matchlens import backtest, markets

SHARES = {"home_1h": 0.45, "away_1h": 0.44, "early": 0.13}


def prediction_frame(scores, odds_row=None):
    rows = []
    for home_goals, away_goals in scores:
        probs, matrix = markets.market_probs(1.5, 1.0, -0.05, SHARES)
        probs["totals"] = markets.total_distribution(matrix)
        rows.append({"league": "eng.1", "home_goals": home_goals, "away_goals": away_goals, **probs, **(odds_row or {})})
    return pd.DataFrame(rows)


def test_accuracy_report_without_odds():
    report = backtest.accuracy_report(prediction_frame([(1, 0), (0, 0), (2, 3)]))
    assert report["matches"] == 3
    assert "ll_1x2_market" not in report


def test_outcome_index():
    df = pd.DataFrame({"home_goals": [2, 1, 0], "away_goals": [1, 1, 3]})
    assert list(backtest.outcome_index(df)) == [0, 1, 2]


def test_betting_report_flat_stake_profit():
    odds_row = {"b365_home": 3.0, "b365_draw": 3.4, "b365_away": 5.5,
                "b365_over": 1.9, "b365_under": 1.9, "b365_goal_line": 2.5}
    df = prediction_frame([(1, 0), (0, 2)], odds_row)
    _, bets = backtest.betting_report(df, thresholds=(0.0,))
    home_bets = bets[(bets["market"] == "1x2") & (bets["odds"] == 3.0)]
    assert list(home_bets["profit"]) == pytest.approx([2.0, -1.0])
    over_bets = bets[(bets["market"] == "total")].iloc[:2]
    assert list(over_bets["profit"]) == pytest.approx([-1.0, -1.0])
    assert np.isfinite(bets["ev"]).all()
