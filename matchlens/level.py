import numpy as np

HALF_LIFE_DAYS = 60.0
SHRINK_GOALS = 500.0


def factors(preds, half_life=HALF_LIFE_DAYS, shrink=SHRINK_GOALS):
    kickoff = preds["kickoff"].dt.tz_convert(None)
    times = kickoff.to_numpy("datetime64[ns]")
    week = kickoff.dt.to_period("W-MON").dt.start_time.to_numpy("datetime64[ns]")
    goals = (preds["home_goals"] + preds["away_goals"]).to_numpy(float)
    lam = (preds["lam_home"] + preds["lam_away"]).to_numpy(float)
    done = ~np.isnan(goals)
    order = np.argsort(times, kind="stable")
    sorted_times = times[order]
    sorted_goals = np.where(done, goals, 0.0)[order]
    sorted_lam = np.where(done, lam, 0.0)[order]
    out = np.ones(len(preds))
    decay = np.log(2) / half_life
    for ref in np.unique(week):
        before = np.searchsorted(sorted_times, ref)
        if before == 0:
            continue
        age = (ref - sorted_times[:before]) / np.timedelta64(1, "D")
        weight = np.exp(-decay * age)
        out[week == ref] = (np.dot(weight, sorted_goals[:before]) + shrink) / (np.dot(weight, sorted_lam[:before]) + shrink)
    return out
