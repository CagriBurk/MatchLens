import numpy as np
import pandas as pd

from data_pipeline import linking

TEAMS = {"1": "Arsenal", "2": "Chelsea", "3": "Everton", "4": "Fulham", "5": "Leeds United", "6": "Wolverhampton"}
ALIASES = {"Arsenal": "Arsenal", "Chelsea": "Chelsea", "Everton": "Everton", "Fulham": "Fulham", "Leeds United": "Leeds", "Wolverhampton": "Wolves"}


def espn_matches(seed=3):
    rng = np.random.default_rng(seed)
    rows, event = [], 1000
    start = pd.Timestamp("2024-08-10 14:00", tz="UTC")
    ids = list(TEAMS)
    week = 0
    for home in ids:
        for away in ids:
            if home == away:
                continue
            rows.append({
                "event_id": str(event), "league": "eng.1", "kickoff": start + pd.Timedelta(days=7 * (week // 3)),
                "home_team_id": home, "away_team_id": away, "home_team": TEAMS[home], "away_team": TEAMS[away],
                "home_goals": float(rng.integers(0, 3)), "away_goals": float(rng.integers(0, 3)),
            })
            event += 1
            week += 1
    return pd.DataFrame(rows)


def external_from(espn, day_shift=1):
    return pd.DataFrame({
        "league": espn["league"],
        "date": espn["kickoff"].dt.tz_convert(None).dt.normalize() + pd.Timedelta(days=day_shift),
        "home_name": espn["home_team"].map(ALIASES), "away_name": espn["away_team"].map(ALIASES),
        "home_goals": espn["home_goals"], "away_goals": espn["away_goals"],
    })


def test_names_are_mapped_through_votes():
    espn = espn_matches()
    _, name_map = linking.link(external_from(espn), espn)
    mapping = dict(zip(name_map["source_name"], name_map["espn_team_id"]))
    assert mapping["Wolves"] == "6"
    assert mapping["Leeds"] == "5"
    assert name_map["accepted"].all()


def test_every_match_links_to_its_event():
    espn = espn_matches()
    linked, _ = linking.link(external_from(espn), espn)
    assert linked["espn_event_id"].tolist() == espn["event_id"].tolist()
    assert linked["score_match"].all()


def test_wrong_score_is_linked_but_flagged():
    espn = espn_matches()
    external = external_from(espn)
    external.loc[0, "home_goals"] = 9
    linked, _ = linking.link(external, espn)
    assert linked.loc[0, "espn_event_id"] == espn.loc[0, "event_id"]
    assert not linked.loc[0, "score_match"]


def test_far_dates_do_not_link():
    espn = espn_matches()
    linked, _ = linking.link(external_from(espn, day_shift=5), espn)
    assert linked["espn_event_id"].isna().all()
