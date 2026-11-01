import numpy as np
import pandas as pd
import pytest

from matchlens import seasonality


def synthetic(n_weeks=300, per_week=10, seed=0):
    rng = np.random.default_rng(seed)
    kickoff = np.repeat(pd.date_range("2019-07-06", periods=n_weeks, freq="7D", tz="UTC"), per_week)
    month = kickoff.month
    lam_total = np.full(len(kickoff), 2.8)
    true_total = lam_total * np.where(np.isin(month, [4, 5]), 1.1, 1.0)
    goals = rng.poisson(true_total)
    return pd.DataFrame({"kickoff": kickoff, "league": np.where(np.arange(len(kickoff)) % 2, "eng.1", "usa.1"),
                         "lam_home": lam_total / 2, "lam_away": lam_total / 2,
                         "home_goals": goals // 2, "away_goals": goals - goals // 2})


def test_factor_learns_season_and_starts_neutral():
    preds = synthetic(per_week=200)
    factor = seasonality.factors(preds, shrink=100.0, grouping="pooled")
    first_week = preds["kickoff"] == preds["kickoff"].min()
    assert np.allclose(factor[first_week], 1.0)
    late = preds["kickoff"] >= pd.Timestamp("2024-01-01", tz="UTC")
    spring = late & preds["kickoff"].dt.month.isin([4, 5])
    assert factor[spring].mean() == pytest.approx(1.1 / 1.017, abs=0.03)
    assert factor[late & ~spring].mean() < 1.0


def test_factor_is_leakage_free():
    preds = synthetic()
    factor = seasonality.factors(preds)
    poisoned = preds.copy()
    cut = pd.Timestamp("2022-03-07", tz="UTC")
    later = poisoned["kickoff"] >= cut
    poisoned.loc[later, "home_goals"] = 9
    poisoned_factor = seasonality.factors(poisoned)
    week_start = preds["kickoff"].dt.tz_convert(None).dt.to_period("W-MON").dt.start_time
    unaffected = (week_start <= cut.tz_convert(None)).to_numpy()
    assert np.allclose(factor[unaffected], poisoned_factor[unaffected])
    assert not np.allclose(factor[~unaffected], poisoned_factor[~unaffected])


def test_apply_keeps_ratio():
    preds = synthetic(n_weeks=5)
    preds["lam_home"] = 1.8
    adjusted = seasonality.apply(preds, np.full(len(preds), 1.2))
    assert np.allclose(adjusted["lam_home"] / adjusted["lam_away"], preds["lam_home"] / preds["lam_away"])
    assert np.allclose(adjusted["lam_home"] + adjusted["lam_away"], 1.2 * (preds["lam_home"] + preds["lam_away"]))


def test_level_tracker_is_leakage_free_and_follows_shift():
    from matchlens import level
    preds = synthetic(per_week=100)
    shift = preds["kickoff"] >= pd.Timestamp("2023-01-01", tz="UTC")
    preds.loc[shift, "home_goals"] += 1
    factor = level.factors(preds, half_life=30.0, shrink=100.0)
    assert np.allclose(factor[preds["kickoff"] == preds["kickoff"].min()], 1.0)
    week_start = preds["kickoff"].dt.tz_convert(None).dt.to_period("W-MON").dt.start_time
    before = (week_start <= pd.Timestamp("2023-01-01")).to_numpy()
    assert abs(factor[before & ~shift.to_numpy()].mean() - 1.0) < 0.05
    assert factor[preds["kickoff"] >= pd.Timestamp("2023-06-01", tz="UTC")].mean() > 1.25
    poisoned = preds.copy()
    poisoned.loc[shift, "home_goals"] = 9
    assert np.allclose(factor[before], level.factors(poisoned, half_life=30.0, shrink=100.0)[before])
