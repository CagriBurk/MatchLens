import pandas as pd
import pytest

from data_pipeline import db
from data_pipeline.espn import parse
from matchlens import bulletin, markets, tracking

SHARES = {"home_1h": 0.45, "away_1h": 0.44, "early": 0.13}


def draftkings_summary(home="-350", draw="+475", away="+850", line="o2.5", over="-165", under="+120"):
    def side(odds, line_value=None):
        close = {"odds": odds}
        if line_value:
            close["line"] = line_value
        return {"close": close, "open": {"odds": odds}}
    return {"odds": [
        {"provider": {"name": "DraftKings"}, "overUnder": 2.5,
         "moneyline": {"home": side(home), "draw": side(draw), "away": side(away)},
         "total": {"over": side(over, line), "under": side(under, "u" + line[1:])}},
    ]}


def test_american_to_decimal():
    assert parse.american_to_decimal("-350") == pytest.approx(1.2857, abs=1e-4)
    assert parse.american_to_decimal("+475") == pytest.approx(5.75)
    assert parse.american_to_decimal(None) is None


def test_parse_draftkings_odds():
    row = parse.parse_draftkings_odds(draftkings_summary(), "9")
    assert row["dk_home"] == pytest.approx(1.2857, abs=1e-4)
    assert row["dk_away"] == pytest.approx(9.5)
    assert row["dk_goal_line"] == 2.5
    assert row["dk_over"] == pytest.approx(1.6061, abs=1e-4)
    assert parse.parse_draftkings_odds({"odds": [{"provider": {"name": "Bet 365"}}]}, "9") is None


B365 = {"b365_home": 2.35, "b365_draw": 3.5, "b365_away": 2.9, "b365_goal_line": 2.75, "b365_over": 1.9, "b365_under": 1.95}
DK = {"dk_home": 2.4, "dk_draw": 3.4, "dk_away": 2.95, "dk_goal_line": 2.5, "dk_over": 1.95, "dk_under": 1.87}


def test_bet365_first_for_result_and_dk_line_for_over():
    view = bulletin.market_view({**B365, **DK})
    assert view["market_src"] == "b365"
    assert view["market_odds_home"] == 2.35
    assert view["market_ou_src"] == "dk"
    assert view["market_line"] == 2.5
    assert view["market_over_2.5"] == pytest.approx((1 / 1.95) / (1 / 1.95 + 1 / 1.87))


def test_draftkings_fallback():
    view = bulletin.market_view(DK)
    assert view["market_src"] == "dk"
    assert sum(view[f"market_{s}"] for s in ("home", "draw", "away")) == pytest.approx(1.0)


def test_asian_line_converted_to_over_25():
    view = bulletin.market_view(B365)
    assert view["market_ou_src"] == "b365~"
    p_line = (1 / 1.9) / (1 / 1.9 + 1 / 1.95)
    assert abs(view["market_over_2.5"] - p_line) < 0.06


def test_no_prices_gives_empty_view():
    assert bulletin.market_view({"b365_home": None}) == {}


def test_market_source_is_logged(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    probs, _ = markets.market_probs(1.5, 1.1, -0.05, SHARES)
    record = {"event_id": "1", "league": "eng.1", "kickoff": "22:00", "kickoff_utc": "2030-01-01T19:00Z", "home_team": "A",
              "away_team": "B", "lam_home": 1.5, "lam_away": 1.1, **probs, **bulletin.market_view({**B365, **DK})}
    tracking.log_predictions(pd.DataFrame([record]), pd.DataFrame(), now=pd.Timestamp("2029-12-31", tz="UTC"))
    with db.connect() as conn:
        log = pd.read_sql_query("SELECT market, market_src FROM prediction_log", conn).set_index("market")["market_src"]
    assert log["home"] == "b365" and log["over_2.5"] == "dk" and pd.isna(log["btts_yes"])
