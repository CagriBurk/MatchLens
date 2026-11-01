import pandas as pd
import pytest

from data_pipeline import db
from matchlens import markets, tracking

SHARES = {"home_1h": 0.45, "away_1h": 0.44, "early": 0.13}
NOW = pd.Timestamp("2026-11-01 12:00", tz="UTC")


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


def fixture_frames(kickoff="2026-11-01T19:00Z", event_id="1"):
    probs, _ = markets.market_probs(1.6, 1.0, -0.05, SHARES)
    record = {"event_id": event_id, "league": "eng.1", "kickoff": "22:00", "kickoff_utc": kickoff,
              "home_team": "A", "away_team": "B", "lam_home": 1.6, "lam_away": 1.0, **probs}
    base = {k: record[k] for k in ("event_id", "league", "kickoff", "kickoff_utc", "home_team", "away_team", "lam_home", "lam_away")}
    candidates = [
        {**base, "market": "1", "key": "home", "line": None, "model_p": probs["home"], "b365": 2.2, "ev": probs["home"] * 2.2 - 1},
        {**base, "market": "Over 2.75", "key": "asian_over", "line": 2.75, "model_p": None, "b365": 1.9, "ev": 0.05},
    ]
    return pd.DataFrame([record]), pd.DataFrame(candidates)


def finished_match(event_id="1", home_goals=2, away_goals=1, ht_home=1, ht_away=0, early=1, regular=True):
    return pd.DataFrame([{"event_id": event_id, "state": "post", "regular": regular, "home_goals": float(home_goals),
                          "away_goals": float(away_goals), "ht_home": ht_home, "ht_away": ht_away,
                          "early_goals": early, "events_consistent": True}])


def read_log():
    with db.connect() as conn:
        return pd.read_sql_query("SELECT * FROM prediction_log", conn).set_index("market")


def test_log_writes_all_markets_with_odds():
    records, candidates = fixture_frames()
    logged = tracking.log_predictions(records, candidates, now=NOW)
    log = read_log()
    assert logged == len(tracking.LOG_MARKETS) + 1
    assert log.loc["home", "b365"] == 2.2
    assert pd.isna(log.loc["draw", "b365"])
    assert log.loc["asian_over", "line"] == 2.75


def test_started_matches_are_not_logged():
    records, candidates = fixture_frames(kickoff="2026-11-01T11:00Z")
    assert tracking.log_predictions(records, candidates, now=NOW) == 0


def test_settle_outcomes_and_profit():
    records, candidates = fixture_frames()
    tracking.log_predictions(records, candidates, now=NOW)
    tracking.settle(finished_match(), now=NOW + pd.Timedelta(days=1))
    log = read_log()
    assert log.loc["home", "outcome"] == 1.0
    assert log.loc["home", "profit"] == pytest.approx(1.2)
    assert log.loc["draw", "outcome"] == 0.0
    assert log.loc["over_2.5", "outcome"] == 1.0
    assert log.loc["btts_yes", "outcome"] == 1.0
    assert log.loc["both_halves_btts", "outcome"] == 0.0
    assert log.loc["early_goal_0_15", "outcome"] == 1.0
    assert log.loc["htft_1/2", "outcome"] == 0.0
    assert log.loc["htft_2/1", "outcome"] == 0.0
    assert log.loc["asian_over", "profit"] == pytest.approx(0.45)


def test_reversal_outcome():
    records, candidates = fixture_frames()
    tracking.log_predictions(records, candidates, now=NOW)
    tracking.settle(finished_match(home_goals=1, away_goals=2, ht_home=1, ht_away=0), now=NOW + pd.Timedelta(days=1))
    log = read_log()
    assert log.loc["htft_1/2", "outcome"] == 1.0
    assert log.loc["away", "outcome"] == 1.0
    assert log.loc["asian_over", "profit"] == pytest.approx(0.45)


def test_relogging_updates_until_settled():
    records, candidates = fixture_frames()
    tracking.log_predictions(records, candidates, now=NOW)
    candidates.loc[0, "b365"] = 2.4
    tracking.log_predictions(records, candidates, now=NOW + pd.Timedelta(hours=1))
    assert read_log().loc["home", "b365"] == 2.4
    tracking.settle(finished_match(), now=NOW + pd.Timedelta(days=1))
    candidates.loc[0, "b365"] = 3.0
    tracking.log_predictions(records, candidates, now=NOW)
    assert read_log().loc["home", "b365"] == 2.4


def test_non_regular_finish_is_void():
    records, candidates = fixture_frames()
    tracking.log_predictions(records, candidates, now=NOW)
    tracking.settle(finished_match(regular=False), now=NOW + pd.Timedelta(days=1))
    log = read_log()
    assert log["settled_at"].notna().all()
    assert log["outcome"].isna().all()


def test_report_after_settlement():
    records, candidates = fixture_frames()
    tracking.log_predictions(records, candidates, now=NOW)
    tracking.settle(finished_match(), now=NOW + pd.Timedelta(days=1))
    accuracy, betting = tracking.report(min_ev=0.0)
    assert accuracy.loc["home", "actual"] == 1.0
    assert betting.loc["ALL", "bets"] >= 1
