import numpy as np
import pandas as pd
import pytest

from data_pipeline import db, nesine
from matchlens import coupons, markets, selections


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")


def test_combo_probabilities_are_consistent():
    matrix = markets.score_matrix(1.6, 1.1, -0.05)
    probs = selections.matrix_probs(matrix, keys=["home", "home&btts_yes", "home&btts_no", "btts_yes&over_2.5", "btts_yes&under_2.5", "btts_yes"])
    assert probs["home&btts_yes"] + probs["home&btts_no"] == pytest.approx(probs["home"])
    assert probs["btts_yes&over_2.5"] + probs["btts_yes&under_2.5"] == pytest.approx(probs["btts_yes"])


def test_settlement_outcomes():
    match = {"home_goals": 2.0, "away_goals": 1.0, "ht_home": 0.0, "ht_away": 1.0, "events_consistent": True}
    assert coupons.leg_outcome("home&btts_yes", match) == 1.0
    assert coupons.leg_outcome("home&over_2.5", match) == 1.0
    assert coupons.leg_outcome("btts_no&under_2.5", match) == 0.0
    assert coupons.leg_outcome("htft_2/1", match) == 1.0
    assert coupons.leg_outcome("htft_2/1", {**match, "events_consistent": False}) is None


def cands(rows):
    df = pd.DataFrame(rows, columns=["event_id", "key", "odds", "p_safe", "mbs"])
    return df.assign(ratio=df["odds"] * df["p_safe"], p_ref=1 / (df["odds"] * 1.15))


def test_build_stops_at_target_and_uses_one_leg_per_match():
    df = cands([(str(i), "home", 1.40, 0.75, 1) for i in range(10)] + [("0", "over_1.5", 1.40, 0.80, 1)])
    legs = coupons.build(df, (1.35, 1.65), target=0.20, min_legs=2, max_legs=8)
    assert len({leg["event_id"] for leg in legs}) == len(legs)
    assert np.prod([leg["p_safe"] for leg in legs]) >= 0.20
    assert len(legs) == 5


def test_build_prefers_value_and_respects_tolerance():
    df = cands([("1", "home", 1.50, 0.70, 1), ("2", "home", 1.50, 0.62, 1), ("3", "home", 1.50, 0.55, 1)])
    legs = coupons.build(df, (1.35, 1.65), target=0.0, min_legs=1, max_legs=6)
    assert [leg["event_id"] for leg in legs] == ["1", "2"]


def test_build_drops_legs_violating_mbs():
    df = cands([("1", "home", 1.50, 0.80, 1), ("2", "home", 1.50, 0.79, 1), ("3", "home", 1.50, 0.78, 4)])
    legs = coupons.build(df, (1.35, 1.65), target=0.0, min_legs=2, max_legs=6)
    assert sorted(leg["event_id"] for leg in legs) == ["1", "2"]


def test_generate_and_settle_roundtrip():
    records = pd.DataFrame([{"event_id": str(i), "league": "eng.1", "kickoff_utc": "2030-01-01T19:00Z", "home_team": f"H{i}",
                             "away_team": f"A{i}", "home": 0.75, "twin_home": 0.78, "ref_home": 0.66, "ref_src": "b365"} for i in range(4)])
    offers = pd.DataFrame([{"event_id": str(i), "key": "home", "odds": 1.42, "mbs": 1} for i in range(4)])
    written = coupons.generate("2030-01-01", records, offers, now=pd.Timestamp("2029-12-31", tz="UTC"))
    assert written > 0 and coupons.exists("2030-01-01")
    stored = coupons.load("2030-01-01")
    assert {"model_blue", "twin_blue"} <= set(stored["coupon"])
    assert stored.loc[stored["coupon"].eq("model_blue"), "p_safe"].eq(0.75).all()
    assert stored.loc[stored["coupon"].eq("twin_blue"), "p_safe"].eq(0.78).all()
    assert stored["ref_src"].eq("b365").all()
    assert coupons.generate("2030-01-01", records, offers, now=pd.Timestamp("2029-12-31", tz="UTC")) == 0
    matches = pd.DataFrame([{"event_id": str(i), "state": "post", "regular": True, "home_goals": 1.0, "away_goals": 0.0,
                             "ht_home": 0.0, "ht_away": 0.0, "events_consistent": True} for i in range(4)])
    assert coupons.settle(matches) == written
    assert (coupons.load("2030-01-01")["outcome"] == 1.0).all()


def test_nesine_parsing_and_matching():
    payload = {"sg": {"LA": [{"LID": 7, "N": "İngiltere Premier Lig"}], "EA": [
        {"C": 11, "TYPE": 1, "HN": "Man. Utd", "AN": "Tottenham", "LC": 7, "ESD": 1893524400000, "MA": [
            {"MTID": 1, "SOV": 0.0, "MBS": 1, "OCA": [{"N": 1, "O": 1.9}, {"N": 2, "O": 3.4}, {"N": 3, "O": 3.6}]},
            {"MTID": 414, "SOV": 0.0, "MBS": 1, "OCA": [{"N": 2, "O": 5.1}, {"N": 4, "O": 11.0}]},
            {"MTID": 12, "SOV": 3.5, "MBS": 1, "OCA": [{"N": 2, "O": 2.0}]}]},
        {"C": 12, "TYPE": 1, "HN": "Arsenal", "AN": "Chelsea", "LC": 7, "ESD": 1893524400000, "MA": []}]}}
    events, offers = nesine.events_and_offers(payload)
    assert set(offers["key"]) == {"home", "draw", "away", "home&btts_no", "draw&btts_no"}
    fixtures = pd.DataFrame([{"event_id": "99", "home_team": "Manchester United", "away_team": "Tottenham Hotspur",
                              "kickoff_utc": "2030-01-01T19:00Z"}])
    matched = nesine.match_events(fixtures, events)
    assert matched["code"].tolist() == [11]


def test_nesine_fair_probability_handles_double_chance():
    payload = {"sg": {"LA": [], "EA": [{"C": 1, "TYPE": 1, "HN": "A", "AN": "B", "LC": 0, "ESD": 1893524400000, "MA": [
        {"MTID": 3, "SOV": 0.0, "MBS": 1, "OCA": [{"N": 1, "O": 1.25}, {"N": 2, "O": 1.30}, {"N": 3, "O": 1.60}]},
        {"MTID": 1, "SOV": 0.0, "MBS": 1, "OCA": [{"N": 1, "O": 2.0}, {"N": 2, "O": 3.2}, {"N": 3, "O": 3.5}]}]}]}}
    _, offers = nesine.events_and_offers(payload)
    fair = offers.set_index("key")["fair"]
    assert fair[["dc_1x", "dc_12", "dc_x2"]].sum() == pytest.approx(2.0)
    assert fair[["home", "draw", "away"]].sum() == pytest.approx(1.0)


def test_sides_use_their_own_probability_against_reference():
    records = pd.DataFrame([{"event_id": "1", "league": "eng.1", "kickoff_utc": "2030-01-01T19:00Z", "home_team": "H", "away_team": "A",
                             "home": 0.70, "twin_home": 0.60, "ref_home": 0.65, "under_3.5": 0.70, "twin_under_3.5": 0.72,
                             "ref_under_3.5": 0.68, "ref_src": "b365", "ref_ou_src": "dk"}])
    offers = pd.DataFrame([{"event_id": "1", "key": "home", "odds": 1.45, "mbs": 1, "fair": 0.62},
                           {"event_id": "1", "key": "under_3.5", "odds": 1.40, "mbs": 1, "fair": 0.66},
                           {"event_id": "1", "key": "draw", "odds": 4.0, "mbs": 1, "fair": 0.24}])
    cands = coupons.candidates(records, offers).set_index("key")
    assert "draw" not in cands.index
    assert cands.loc["home", "ref_src"] == "b365" and cands.loc["under_3.5", "ref_src"] == "b365~"
    model = coupons.side_pool(coupons.candidates(records, offers), "model")
    twin = coupons.side_pool(coupons.candidates(records, offers), "twin")
    model_ok = model[model["p_safe"] >= model["p_ref"]]["key"].tolist()
    twin_ok = twin[twin["p_safe"] >= twin["p_ref"]]["key"].tolist()
    assert sorted(model_ok) == ["home", "under_3.5"] and twin_ok == ["under_3.5"]


def test_reference_view_keeps_direct_market_and_derives_the_rest():
    from matchlens import bulletin, dixon_coles
    market = {"market_home": 0.5, "market_draw": 0.27, "market_away": 0.23, "market_src": "b365",
              "market_over_2.5": 0.55, "market_ou_src": "b365"}
    view = bulletin.reference_view(market, dict(dixon_coles.DEFAULT_SHARES))
    assert view["ref_home"] == 0.5 and view["ref_dc_1x"] == pytest.approx(0.77) and view["ref_under_2.5"] == pytest.approx(0.45)
    assert view["ref_over_1.5"] > view["ref_over_2.5"] > view["ref_over_3.5"]
    assert view["ref_btts_yes"] + view["ref_btts_no"] == pytest.approx(1.0)
    assert 0 < view["ref_htft_1/2"] < 0.1
    assert bulletin.reference_view({**market, "market_over_2.5": None}, dixon_coles.DEFAULT_SHARES) == {}
