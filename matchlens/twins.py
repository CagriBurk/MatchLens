import argparse
import re

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

from data_pipeline.db import connect
from data_pipeline.espn.matches import load_matches
from matchlens import selections
from matchlens.market_lambda import fair_three_way, fair_two_way

K = 200
MAX_DEPTH = 20_000
MAX_CELLS = 2_000_000
EARLY_MINUTE = 15
ASSUMED_TWO_WAY_MARGIN = 0.05
UNVERIFIED_KAGGLE = {"aut.1", "jpn.1", "pol.1", "sui.1", "swe.1"}
ESPN_ONLY_KAGGLE = {"den.1", "nor.1", "usa.1"}
MARKETS = [
    "home", "draw", "away", "over_1.5", "over_2.5", "over_3.5", "btts_yes", "goals_6plus",
    "ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "both_halves_btts",
    "htft_1/1", "htft_X/X", "htft_2/2", "htft_1/2", "htft_2/1",
    "dc_1x", "dc_12", "dc_x2", "under_1.5", "under_2.5", "under_3.5", "btts_no",
    "ht_home", "ht_draw", "ht_away", "htft_1/X", "htft_X/1", "htft_X/2", "htft_2/X",
    *selections.COMBOS, "early_goal_0_15",
]
HALF_MARKETS = {"ht_over_0.5", "ht_over_1.5", "both_halves_over_1.5", "both_halves_btts", "ht_home", "ht_draw", "ht_away", *selections.HTFT}
ODDS_COLUMNS = ["o_home", "o_draw", "o_away", "o_over25", "o_under25"]
POOL_COLUMNS = ["source", "league", "date", "event_id", "p_home", "p_draw", "p_away", "p_over25",
                "home_goals", "away_goals", "ht_home", "ht_away", "early_goal", "home_team", "away_team"] + ODDS_COLUMNS
MINUTE = re.compile(r"(\d+)")


def early_from_timings(home, away):
    minutes = []
    for text in (home, away):
        if isinstance(text, str):
            minutes += [int(MINUTE.match(part.strip()).group(1)) for part in text.split(",") if MINUTE.match(part.strip())]
    return float(any(m <= EARLY_MINUTE for m in minutes))


def with_fair_result(df, columns):
    ok = df[columns].notna().all(axis=1) & (df[columns] > 1).all(axis=1)
    df = df[ok].copy()
    fair = fair_three_way(*df[columns].to_numpy().T)
    df["p_home"], df["p_draw"], df["p_away"] = fair[:, 0], fair[:, 1], fair[:, 2]
    return df


def espn_rows(espn):
    with connect() as conn:
        odds = pd.read_sql_query("SELECT * FROM espn_odds", conn).drop_duplicates("event_id")
    df = with_fair_result(espn.merge(odds, on="event_id"), ["b365_home", "b365_draw", "b365_away"])
    line25 = df["b365_goal_line"].eq(2.5) & df[["b365_over", "b365_under"]].notna().all(axis=1)
    df["p_over25"] = np.where(line25, fair_two_way(df["b365_over"], df["b365_under"]), np.nan)
    df["o_home"], df["o_draw"], df["o_away"] = df["b365_home"], df["b365_draw"], df["b365_away"]
    df["o_over25"] = df["b365_over"].where(line25)
    df["o_under25"] = df["b365_under"].where(line25)
    df["source"] = "b365"
    return df


def kaggle_rows():
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM kaggle_matches", conn, parse_dates=["date"])
    df = df[~df["league"].isin(UNVERIFIED_KAGGLE)]
    df = df[~df["league"].isin(ESPN_ONLY_KAGGLE) | df["espn_event_id"].notna()]
    df = df[df["score_match"].ne(0)]
    df = with_fair_result(df, ["odds_home", "odds_draw", "odds_away"])
    ou = df[["odds_over25", "odds_under25"]].notna().all(axis=1)
    df["p_over25"] = np.where(ou, fair_two_way(df["odds_over25"], df["odds_under25"]), np.nan)
    df["o_home"], df["o_draw"], df["o_away"] = df["odds_home"], df["odds_draw"], df["odds_away"]
    df["o_over25"] = df["odds_over25"].where(ou)
    df["o_under25"] = df["odds_under25"].where(ou)
    df["early_goal"] = np.nan
    df["source"] = "kaggle"
    return df.rename(columns={"espn_event_id": "event_id", "home_name": "home_team", "away_name": "away_team"})


def footystats_rows():
    with connect() as conn:
        df = pd.read_sql_query("SELECT * FROM footystats_matches WHERE status = 'complete'", conn)
    df["date"] = pd.to_datetime(df["kickoff"], utc=True).dt.tz_convert(None).dt.normalize()
    df = with_fair_result(df, ["odds_home", "odds_draw", "odds_away"])
    df["p_over25"] = np.where(df["odds_over25"] > 1, 1 / (df["odds_over25"] * (1 + ASSUMED_TWO_WAY_MARGIN)), np.nan)
    df["early_goal"] = [early_from_timings(h, a) for h, a in zip(df["home_goal_timings"], df["away_goal_timings"])]
    df["o_home"], df["o_draw"], df["o_away"] = df["odds_home"], df["odds_draw"], df["odds_away"]
    df["o_over25"] = df["odds_over25"].where(df["odds_over25"] > 1)
    df["o_under25"] = np.nan
    df["source"] = "footystats"
    return df.rename(columns={"espn_event_id": "event_id", "home_name": "home_team", "away_name": "away_team"})


def build_pool():
    espn = load_matches()
    espn = espn[espn["regular"] & espn["home_goals"].notna()].copy()
    espn["date"] = espn["kickoff"].dt.tz_convert(None).dt.normalize()
    consistent = espn["events_consistent"]
    espn["ht_home"] = espn["ht_home"].where(consistent)
    espn["ht_away"] = espn["ht_away"].where(consistent)
    espn["early_goal"] = (espn["early_goals"] > 0).astype(float).where(consistent)
    outcome_cols = ["home_goals", "away_goals", "ht_home", "ht_away", "early_goal"]
    truth = espn.set_index("event_id")[outcome_cols + ["league", "date", "home_team", "away_team"]]

    sources = [espn_rows(espn), kaggle_rows(), footystats_rows()]
    frames = []
    for df in sources:
        frames.append(df.reindex(columns=POOL_COLUMNS))
    pool = pd.concat(frames, ignore_index=True)
    pool["priority"] = pool["source"].map({"b365": 0, "kaggle": 1, "footystats": 2})
    linked = pool[pool["event_id"].notna()].sort_values("priority")
    over_fill = linked.dropna(subset=["p_over25"]).drop_duplicates("event_id").set_index("event_id")[["p_over25", "o_over25", "o_under25"]]
    half_fill = linked.dropna(subset=["ht_home"]).drop_duplicates("event_id").set_index("event_id")[["ht_home", "ht_away"]]
    early_fill = linked.dropna(subset=["early_goal"]).drop_duplicates("event_id").set_index("event_id")["early_goal"]
    linked = linked.drop_duplicates("event_id").set_index("event_id")
    missing_over = linked["p_over25"].isna()
    linked.loc[missing_over, ["p_over25", "o_over25", "o_under25"]] = over_fill.reindex(linked.index[missing_over]).to_numpy()
    known = linked.index.intersection(truth.index)
    truth_cols = ["home_goals", "away_goals", "league", "date", "home_team", "away_team"]
    linked.loc[known, truth_cols] = truth.loc[known, truth_cols].to_numpy()
    for column in ("ht_home", "ht_away", "early_goal"):
        linked.loc[known, column] = truth.loc[known, column].to_numpy()
    linked[["ht_home", "ht_away"]] = linked[["ht_home", "ht_away"]].fillna(half_fill.reindex(linked.index))
    linked["early_goal"] = linked["early_goal"].fillna(early_fill.reindex(linked.index))
    unlinked = pool[pool["event_id"].isna()]
    pool = pd.concat([linked.reset_index(), unlinked], ignore_index=True)[POOL_COLUMNS]
    pool = pool.dropna(subset=["home_goals", "away_goals", "p_home", "p_away"])
    pool["date"] = pd.to_datetime(pool["date"])
    pool = pool.sort_values("date").reset_index(drop=True)
    with connect() as conn:
        pool.to_sql("twins_pool", conn, if_exists="replace", index=False)
    return pool


def load_pool():
    with connect() as conn:
        return pd.read_sql_query("SELECT * FROM twins_pool", conn, parse_dates=["date"])


def outcome_matrix(pool):
    hg, ag = pool["home_goals"].to_numpy(float), pool["away_goals"].to_numpy(float)
    hh, ha = pool["ht_home"].to_numpy(float), pool["ht_away"].to_numpy(float)
    sh, sa = hg - hh, ag - ha
    total, ht_total = hg + ag, hh + ha
    half_known = ~np.isnan(hh) & ~np.isnan(ha)
    ht_sign, ft_sign = np.sign(hh - ha), np.sign(hg - ag)
    values = {
        "home": hg > ag, "draw": hg == ag, "away": hg < ag,
        "over_1.5": total > 1.5, "over_2.5": total > 2.5, "over_3.5": total > 3.5,
        "btts_yes": (hg > 0) & (ag > 0), "goals_6plus": total >= 6,
        "ht_over_0.5": ht_total > 0.5, "ht_over_1.5": ht_total > 1.5,
        "both_halves_over_1.5": (ht_total >= 2) & (sh + sa >= 2),
        "both_halves_btts": (hh > 0) & (ha > 0) & (sh > 0) & (sa > 0),
        "htft_1/1": (ht_sign == 1) & (ft_sign == 1), "htft_X/X": (ht_sign == 0) & (ft_sign == 0),
        "htft_2/2": (ht_sign == -1) & (ft_sign == -1), "htft_1/2": (ht_sign == 1) & (ft_sign == -1),
        "htft_2/1": (ht_sign == -1) & (ft_sign == 1),
    }
    values.update(selections.full_time(hg, ag))
    values.update(selections.half_time(hg, ag, hh, ha))
    matrix = np.column_stack([values[m].astype(float) for m in MARKETS[:-1]] + [pool["early_goal"].to_numpy(float)])
    for i, market in enumerate(MARKETS):
        if market in HALF_MARKETS:
            matrix[~half_known, i] = np.nan
    return matrix


class TwinFinder:
    def __init__(self, pool):
        self.pool = pool.reset_index(drop=True)
        self.dates = self.pool["date"].to_numpy(dtype="datetime64[ns]")
        self.outcomes = outcome_matrix(self.pool)
        self.scores = (self.pool["home_goals"].astype(int).astype(str) + "-" + self.pool["away_goals"].astype(int).astype(str)).to_numpy()
        has_over = self.pool["p_over25"].notna().to_numpy()
        self.full_index = np.flatnonzero(has_over)
        self.full_tree = cKDTree(self.pool.loc[has_over, ["p_home", "p_away", "p_over25"]].to_numpy())
        self.result_tree = cKDTree(self.pool[["p_home", "p_away"]].to_numpy())

    def neighbours(self, points, before, k=K, use_over=True):
        points = np.atleast_2d(points)
        before = np.asarray(before, dtype="datetime64[ns]").reshape(-1)
        tree, mapping = (self.full_tree, self.full_index) if use_over else (self.result_tree, None)
        found = np.full((len(points), k), -1)
        radius = np.full(len(points), np.nan)
        pending = np.arange(len(points))
        depth = k * 3
        max_depth = min(tree.n, MAX_DEPTH)
        while len(pending):
            depth = min(depth, max_depth)
            batch = max(1, MAX_CELLS // depth)
            remaining = []
            for start_at in range(0, len(pending), batch):
                rows = pending[start_at:start_at + batch]
                dist, idx = tree.query(points[rows], k=depth)
                dist, idx = dist.reshape(len(rows), -1), idx.reshape(len(rows), -1)
                idx = idx if mapping is None else mapping[idx]
                valid = self.dates[idx] < before[rows, None]
                final = (valid.sum(axis=1) >= k) | (depth >= max_depth)
                for j in np.flatnonzero(final):
                    chosen = np.flatnonzero(valid[j])[:k]
                    found[rows[j], :len(chosen)] = idx[j, chosen]
                    if len(chosen):
                        radius[rows[j]] = dist[j, chosen[-1]]
                remaining.append(rows[~final])
            pending = np.concatenate(remaining)
            depth *= 4
        return found, radius

    def frequencies(self, found):
        mask = found >= 0
        values = self.outcomes[np.where(mask, found, 0)]
        values[~mask] = np.nan
        counts = np.sum(~np.isnan(values), axis=1)
        hits = np.nansum(values, axis=1)
        return hits, counts

    def search(self, p_home, p_away, p_over=None, before=None, k=K):
        use_over = p_over is not None and np.isfinite(p_over)
        point = [p_home, p_away, p_over] if use_over else [p_home, p_away]
        before = np.datetime64("now") if before is None else np.datetime64(pd.Timestamp(before).tz_localize(None) if pd.Timestamp(before).tzinfo else pd.Timestamp(before))
        found, radius = self.neighbours(np.array([point]), [before], k=k, use_over=use_over)
        return point, use_over, found, radius

    def twin_table(self, p_home, p_away, p_over=None, before=None, k=K):
        point, _, found, _ = self.search(p_home, p_away, p_over, before, k)
        table = self.pool.loc[found[0][found[0] >= 0]].copy()
        axes = ["p_home", "p_away", "p_over25"][:len(point)]
        table["distance"] = np.linalg.norm(table[axes].to_numpy() - np.array(point), axis=1)
        return table.reset_index(drop=True)

    def summarize(self, p_home, p_away, p_over=None, before=None, k=K):
        _, use_over, found, radius = self.search(p_home, p_away, p_over, before, k)
        row = found[0][found[0] >= 0]
        hits, counts = self.frequencies(found)
        summary = {"n": len(row), "radius": float(radius[0]), "used_over": use_over}
        for i, market in enumerate(MARKETS):
            summary[market] = hits[0, i] / counts[0, i] if counts[0, i] else np.nan
            summary[f"{market}_n"] = int(counts[0, i])
        top = pd.Series(self.scores[row]).value_counts(normalize=True).head(5)
        summary["top_scores"] = " ".join(f"{score}({100 * share:.0f}%)" for score, share in top.items())
        summary["leagues"] = self.pool.loc[row, "league"].value_counts().head(3).to_dict()
        return summary


TEST_START = "2019-07-01"
EDGE_THRESHOLDS = (0.02, 0.04, 0.06, 0.08)
MAX_ODDS = 6.0
EPS = 1e-12


def walk_forward(finder, start=TEST_START, k=K, chunk=5000):
    pool = finder.pool
    targets = np.flatnonzero((pool["date"] >= pd.Timestamp(start)).to_numpy())
    has_over = pool["p_over25"].notna().to_numpy()
    hits = np.full((len(pool), len(MARKETS)), np.nan)
    counts = np.zeros((len(pool), len(MARKETS)))
    for use_over in (True, False):
        group = targets[has_over[targets] == use_over]
        columns = ["p_home", "p_away", "p_over25"] if use_over else ["p_home", "p_away"]
        for start_at in range(0, len(group), chunk):
            rows = group[start_at:start_at + chunk]
            found, _ = finder.neighbours(pool.loc[rows, columns].to_numpy(), finder.dates[rows], k=k, use_over=use_over)
            h, c = finder.frequencies(found)
            hits[rows], counts[rows] = h, c
    columns = {}
    for i, market in enumerate(MARKETS):
        columns[f"twin_{market}"] = hits[targets, i]
        columns[f"twin_{market}_n"] = counts[targets, i]
    result = pool.loc[targets].reset_index(drop=True)
    return pd.concat([result, pd.DataFrame(columns)], axis=1).set_axis(targets, axis=0)


def smoothed(result, market, classes=2):
    return (result[f"twin_{market}"] + 1) / (result[f"twin_{market}_n"] + classes)


def log_loss_binary(p, y):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def accuracy(result):
    hg, ag = result["home_goals"].to_numpy(), result["away_goals"].to_numpy()
    outcome = np.select([hg > ag, hg == ag], [0, 1], 2)
    rows = np.arange(len(result))
    market = result[["p_home", "p_draw", "p_away"]].to_numpy()
    twins = np.column_stack([smoothed(result, m, 3) for m in ("home", "draw", "away")])
    twins = twins / twins.sum(axis=1, keepdims=True)
    report = {
        "matches": len(result),
        "ll_1x2_market": float(-np.mean(np.log(np.clip(market[rows, outcome], EPS, 1)))),
        "ll_1x2_twins": float(-np.mean(np.log(np.clip(twins[rows, outcome], EPS, 1)))),
    }
    ou = result["p_over25"].notna().to_numpy()
    over = (hg + ag > 2.5).astype(float)
    report["ou_matches"] = int(ou.sum())
    report["ll_o25_market"] = log_loss_binary(result.loc[ou, "p_over25"], over[ou])
    report["ll_o25_twins"] = log_loss_binary(smoothed(result[ou], "over_2.5"), over[ou])
    return report


def bets(result):
    hg, ag = result["home_goals"].to_numpy(), result["away_goals"].to_numpy()
    wins = {"home": hg > ag, "draw": hg == ag, "away": hg < ag, "over": hg + ag > 2.5, "under": hg + ag < 2.5}
    twin_over = result["twin_over_2.5"] / result["twin_over_2.5_n"]
    sides = [
        ("home", result["twin_home"] / result["twin_home_n"], result["p_home"], "o_home"),
        ("draw", result["twin_draw"] / result["twin_draw_n"], result["p_draw"], "o_draw"),
        ("away", result["twin_away"] / result["twin_away_n"], result["p_away"], "o_away"),
        ("over", twin_over, result["p_over25"], "o_over25"),
        ("under", 1 - twin_over, 1 - result["p_over25"], "o_under25"),
    ]
    frames = []
    for side, twin_p, market_p, odds_col in sides:
        price = result[odds_col].to_numpy()
        frames.append(pd.DataFrame({
            "side": side, "league": result["league"].to_numpy(), "season": result["date"].dt.year.to_numpy(),
            "source": result["source"].to_numpy(), "edge": (twin_p - market_p).to_numpy(), "odds": price,
            "profit": np.where(wins[side], price - 1, -1.0),
        }))
    out = pd.concat(frames, ignore_index=True).dropna(subset=["edge", "odds"])
    return out[(out["odds"] > 1) & (out["odds"] <= MAX_ODDS)]


def roi_table(all_bets, by="side"):
    rows = []
    for threshold in EDGE_THRESHOLDS:
        picked = all_bets[all_bets["edge"] > threshold]
        for key, group in picked.groupby(by):
            rows.append({by: key, "min_edge": threshold, "bets": len(group), "roi": group["profit"].mean()})
    return pd.DataFrame(rows).pivot_table(index=by, columns="min_edge", values=["bets", "roi"])


def save_backtest(result):
    linked = result[result["event_id"].notna()]
    columns = ["event_id", "source", "p_home", "p_draw", "p_away", "p_over25"] + [c for c in result.columns if c.startswith("twin_")]
    with connect() as conn:
        linked[columns].assign(event_id=linked["event_id"].astype(str)).to_sql("twins_backtest", conn, if_exists="replace", index=False)


def run_backtest():
    finder = TwinFinder(load_pool())
    result = walk_forward(finder)
    save_backtest(result)
    all_bets = bets(result)
    with pd.option_context("display.width", 220, "display.max_rows", 200):
        print({k: round(v, 4) if isinstance(v, float) else v for k, v in accuracy(result).items()})
        print("\nROI by side (bet when twin frequency exceeds market probability by min_edge)")
        print(roi_table(all_bets).round(3).to_string())
        print("\nROI by season, all sides")
        print(roi_table(all_bets.assign(all="all"), by="season").round(3).to_string())
        print("\nROI by odds source")
        print(roi_table(all_bets, by="source").round(3).to_string())
    return result, all_bets


def main():
    parser = argparse.ArgumentParser(description="Odds twins: historical matches with similar opening odds")
    parser.add_argument("action", choices=["build", "backtest"])
    args = parser.parse_args()
    if args.action == "build":
        pool = build_pool()
        print(f"twins_pool: {len(pool)} matches, {pool['p_over25'].notna().sum()} with over/under, "
              f"{pool['ht_home'].notna().sum()} with half-time, {pool['early_goal'].notna().sum()} with early-goal data")
        print(pool["source"].value_counts().to_string())
    if args.action == "backtest":
        run_backtest()


if __name__ == "__main__":
    main()
