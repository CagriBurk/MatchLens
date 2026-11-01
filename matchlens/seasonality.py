import numpy as np
import pandas as pd

CALENDAR_YEAR_LEAGUES = {"usa.1", "nor.1"}
SHRINK_GOALS = 1000.0
GROUPING = "calendar"


def calendar_group(leagues):
    return np.where(pd.Series(leagues).isin(CALENDAR_YEAR_LEAGUES).to_numpy(), "calendar_year", "european")


def group_keys(preds, grouping=GROUPING):
    if grouping == "pooled":
        return np.full(len(preds), "all")
    return calendar_group(preds["league"])


def expanding_ratio(keys, times, week, goals, lam, shrink):
    ratio = np.ones(len(keys))
    for key in np.unique(keys):
        idx = np.flatnonzero(keys == key)
        idx = idx[np.argsort(times[idx], kind="stable")]
        done = ~np.isnan(goals[idx])
        cum_goals = np.concatenate([[0.0], np.cumsum(np.where(done, goals[idx], 0.0))])
        cum_lam = np.concatenate([[0.0], np.cumsum(np.where(done, lam[idx], 0.0))])
        before = np.searchsorted(times[idx], week[idx])
        ratio[idx] = (cum_goals[before] + shrink) / (cum_lam[before] + shrink)
    return ratio


def factors(preds, shrink=SHRINK_GOALS, grouping=GROUPING):
    kickoff = preds["kickoff"].dt.tz_convert(None)
    times = kickoff.to_numpy("datetime64[ns]")
    week = kickoff.dt.to_period("W-MON").dt.start_time.to_numpy("datetime64[ns]")
    goals = (preds["home_goals"] + preds["away_goals"]).to_numpy(float)
    lam = (preds["lam_home"] + preds["lam_away"]).to_numpy(float)
    groups = group_keys(preds, grouping)
    cells = np.char.add(np.char.add(groups.astype(str), ":"), kickoff.dt.month.astype(str).to_numpy().astype(str))
    cell_ratio = expanding_ratio(cells, times, week, goals, lam, shrink)
    group_ratio = expanding_ratio(groups, times, week, goals, lam, shrink)
    return cell_ratio / group_ratio


def apply(preds, factor):
    adjusted = preds.copy()
    adjusted["lam_home"] = preds["lam_home"] * factor
    adjusted["lam_away"] = preds["lam_away"] * factor
    return adjusted
