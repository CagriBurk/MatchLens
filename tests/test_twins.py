import numpy as np
import pandas as pd
import pytest

from matchlens import twins


def synthetic_pool(n=3000, seed=5):
    rng = np.random.default_rng(seed)
    p_home = rng.uniform(0.2, 0.7, n)
    p_away = rng.uniform(0.1, 0.8 - p_home)
    home_goals = rng.poisson(2.5 * p_home, n)
    away_goals = rng.poisson(2.5 * p_away, n)
    return pd.DataFrame({
        "source": "kaggle", "league": "eng.1", "event_id": None,
        "date": pd.Timestamp("2015-01-01") + pd.to_timedelta(np.arange(n), unit="D"),
        "p_home": p_home, "p_draw": 1 - p_home - p_away, "p_away": p_away,
        "p_over25": np.where(np.arange(n) % 3 == 0, np.nan, rng.uniform(0.3, 0.7, n)),
        "home_goals": home_goals.astype(float), "away_goals": away_goals.astype(float),
        "ht_home": np.minimum(home_goals, 1).astype(float), "ht_away": np.zeros(n),
        "early_goal": np.nan, "o_home": 2.0, "o_draw": 3.3, "o_away": 3.8, "o_over25": 1.9, "o_under25": 1.9,
    })


@pytest.fixture(scope="module")
def finder():
    return twins.TwinFinder(synthetic_pool())


def test_neighbours_respect_date_cutoff(finder):
    before = np.datetime64("2018-01-01")
    found, _ = finder.neighbours(np.array([[0.45, 0.3]]), [before], k=50, use_over=False)
    assert (found >= 0).all()
    assert (finder.dates[found[0]] < before).all()


def test_neighbours_are_close(finder):
    found, radius = finder.neighbours(np.array([[0.45, 0.3, 0.5]]), [np.datetime64("2030-01-01")], k=40)
    picked = finder.pool.loc[found[0], ["p_home", "p_away", "p_over25"]].to_numpy()
    assert np.all(np.linalg.norm(picked - [0.45, 0.3, 0.5], axis=1) <= radius[0] + 1e-12)
    assert finder.pool.loc[found[0], "p_over25"].notna().all()


def test_too_few_history_returns_partial(finder):
    found, _ = finder.neighbours(np.array([[0.45, 0.3]]), [np.datetime64("2015-01-20")], k=50, use_over=False)
    assert (found[0] >= 0).sum() == 19


def test_frequencies_match_manual_count(finder):
    summary = finder.summarize(0.5, 0.25, None, before="2030-01-01", k=100)
    found, _ = finder.neighbours(np.array([[0.5, 0.25]]), [np.datetime64("2030-01-01")], k=100, use_over=False)
    rows = finder.pool.loc[found[0]]
    assert summary["n"] == 100
    assert summary["home"] == pytest.approx((rows["home_goals"] > rows["away_goals"]).mean())
    assert summary["home"] + summary["draw"] + summary["away"] == pytest.approx(1.0)
    assert summary["htft_1/2"] == pytest.approx(((rows["ht_home"] > rows["ht_away"]) & (rows["home_goals"] < rows["away_goals"])).mean())
    assert summary["early_goal_0_15_n"] == 0


def test_walk_forward_is_leakage_free():
    pool = synthetic_pool(800)
    finder = twins.TwinFinder(pool)
    result = twins.walk_forward(finder, start="2016-06-01", k=30)
    poisoned = pool.copy()
    late = poisoned["date"] >= pd.Timestamp("2016-09-01")
    poisoned.loc[late, "home_goals"] = 9.0
    poisoned_result = twins.walk_forward(twins.TwinFinder(poisoned), start="2016-06-01", k=30)
    early = result["date"] < pd.Timestamp("2016-09-01")
    assert np.allclose(result.loc[early, "twin_home"], poisoned_result.loc[early, "twin_home"])


def test_early_goal_from_timings():
    assert twins.early_from_timings("30,90'8", None) == 0.0
    assert twins.early_from_timings("45'1", "12") == 1.0
    assert twins.early_from_timings(None, None) == 0.0
