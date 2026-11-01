import sys
import time

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from matchlens import markets, selections, twins
from matchlens.market_lambda import DEFAULT_RHO, ImpliedLambda
from matchlens.dixon_coles import DEFAULT_SHARES

OUT = sys.argv[1]
START = pd.Timestamp("2019-07-01")
KS = (50, 100, 200, 500, 1000, 2000)
KMAX = 2000
LEAGUE_K = (50, 200)
LEAGUE_YEARS = 3
FT = ["home", "draw", "away", "dc_1x", "dc_x2", "over_1.5", "over_2.5", "under_2.5", "over_3.5", "under_3.5", "btts_yes", "btts_no",
      "goals_6plus", "home&btts_yes", "away&btts_yes", "draw&btts_yes", "home&over_2.5", "away&over_2.5", "home&under_2.5",
      "btts_yes&over_2.5", "btts_no&under_2.5", "btts_yes&under_2.5", "btts_no&over_2.5", "draw&under_2.5"]
HT = ["ht_home", "ht_draw", "ht_away", "ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "both_halves_btts",
      "htft_1/1", "htft_2/2", "htft_1/2", "htft_2/1", "htft_X/1", "htft_X/2"]
KEYS = FT + HT
t0 = time.time()

pool = twins.load_pool()
pool = pool[pool["p_over25"].notna()].sort_values("date").reset_index(drop=True)
hg, ag = pool["home_goals"].to_numpy(float), pool["away_goals"].to_numpy(float)
hh, ha = pool["ht_home"].to_numpy(float), pool["ht_away"].to_numpy(float)
full = selections.full_time(hg, ag)
half = selections.half_time(hg, ag, hh, ha)
ht_ok = ~np.isnan(hh) & ~np.isnan(ha)
Y = np.column_stack([np.asarray(full[k], float) for k in FT] + [np.where(ht_ok, np.asarray(half[k], float), np.nan) for k in HT]).astype(np.float32)
X = pool[["p_home", "p_away", "p_over25"]].to_numpy(float)
dates = pool["date"].to_numpy("datetime64[D]")
leagues = pool["league"].to_numpy()
print(f"pool {len(pool)}  {time.time() - t0:.0f}s", flush=True)

targets = np.flatnonzero(pool["date"].to_numpy() >= np.datetime64(START))
solver = ImpliedLambda()
lam_h, lam_a = solver.solve(X[targets, 0], X[targets, 1], X[targets, 2], line=2.5)
P0 = np.full((len(targets), len(KEYS)), np.nan, np.float32)
for i, (lh, la) in enumerate(zip(lam_h, lam_a)):
    probs, _ = markets.market_probs(lh, la, DEFAULT_RHO, DEFAULT_SHARES)
    P0[i] = [probs[k] for k in KEYS]
P0[:, KEYS.index("home")] = X[targets, 0]
P0[:, KEYS.index("away")] = X[targets, 1]
P0[:, KEYS.index("draw")] = 1 - X[targets, 0] - X[targets, 1]
P0[:, KEYS.index("over_2.5")] = X[targets, 2]
P0[:, KEYS.index("under_2.5")] = 1 - X[targets, 2]
print(f"baseline done {time.time() - t0:.0f}s", flush=True)

n_t, n_k = len(targets), len(KEYS)
est = {f"g{k}": np.full((n_t, n_k), np.nan, np.float32) for k in KS}
est.update({f"lg{k}": np.full((n_t, n_k), np.nan, np.float32) for k in LEAGUE_K})
est["wtd"] = np.full((n_t, n_k), np.nan, np.float32)
neff = {name: np.zeros(n_t, np.float32) for name in est}
months = pd.Series(pool["date"].to_numpy()[targets]).dt.to_period("M").to_numpy()
for month in pd.unique(months):
    sel = np.flatnonzero(months == month)
    cut = np.datetime64(month.start_time.date())
    hist = np.flatnonzero(dates < cut)
    tree = cKDTree(X[hist])
    rows = targets[sel]
    for part in np.array_split(np.arange(len(sel)), max(1, len(sel) // 250)):
        psel, prow = sel[part], rows[part]
        dist, idx = tree.query(X[prow], k=KMAX)
        nb = hist[idx]
        vals = Y[nb]
        seen = ~np.isnan(vals)
        csum = np.cumsum(np.where(seen, vals, 0), axis=1)
        ccnt = np.cumsum(seen, axis=1)
        for k in KS:
            est[f"g{k}"][psel] = csum[:, k - 1] / np.maximum(ccnt[:, k - 1], 1)
            neff[f"g{k}"][psel] = k
        del csum, ccnt
        h = np.maximum(dist[:, 199:200], 1e-4)
        age = (cut - dates[nb]).astype(float) / 365.25
        w = (np.exp(-0.5 * (dist / h) ** 2) * 0.5 ** (age / 3) * np.where(leagues[nb] == leagues[prow][:, None], 2.0, 1.0)).astype(np.float32)
        ws = np.where(seen, w[:, :, None], np.float32(0))
        est["wtd"][psel] = (ws * np.nan_to_num(vals)).sum(axis=1) / np.maximum(ws.sum(axis=1), 1e-12)
        neff["wtd"][psel] = w.sum(axis=1) ** 2 / (w ** 2).sum(axis=1)
        del vals, seen, ws
    for lg in np.unique(leagues[rows]):
        sub = sel[leagues[rows] == lg]
        pool_lg = hist[(leagues[hist] == lg) & (dates[hist] >= cut - np.timedelta64(int(365.25 * LEAGUE_YEARS), "D"))]
        if len(pool_lg) < 50:
            continue
        ltree = cKDTree(X[pool_lg])
        for k in LEAGUE_K:
            kk = min(k, len(pool_lg))
            _, lidx = ltree.query(X[targets[sub]], k=kk)
            lidx = lidx.reshape(len(sub), kk)
            v = Y[pool_lg[lidx]]
            est[f"lg{k}"][sub] = np.nanmean(v, axis=1)
            neff[f"lg{k}"][sub] = kk
print(f"neighbours done {time.time() - t0:.0f}s", flush=True)

meta = pool.loc[targets, ["date", "league", "source"]].reset_index(drop=True)
Yt = Y[targets]
np.savez_compressed(OUT, keys=np.array(KEYS), P0=P0, Y=Yt, dates=meta["date"].to_numpy("datetime64[D]"),
                    leagues=meta["league"].to_numpy().astype(str), sources=meta["source"].to_numpy().astype(str),
                    **{f"est_{k}": v for k, v in est.items()}, **{f"neff_{k}": v for k, v in neff.items()})
print(f"saved {n_t} targets {time.time() - t0:.0f}s", flush=True)
