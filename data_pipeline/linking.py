import pandas as pd

MAX_VOTE_DAY_GAP = 1
MAX_LINK_DAY_GAP = 2
MIN_VOTES = 3
MIN_RATIO = 3.0
ESPN_COLUMNS = ["event_id", "league", "kickoff", "home_team_id", "away_team_id", "home_team", "away_team", "home_goals", "away_goals"]


def espn_frame(espn):
    df = espn[espn["home_goals"].notna()][ESPN_COLUMNS].copy()
    df["date"] = df["kickoff"].dt.tz_convert(None).dt.normalize()
    return df


def candidate_pairs(external, espn):
    pairs = []
    keys = ["league", "date", "home_goals", "away_goals"]
    for offset in range(-MAX_VOTE_DAY_GAP, MAX_VOTE_DAY_GAP + 1):
        shifted = espn.assign(date=espn["date"] + pd.Timedelta(days=offset))
        pairs.append(external.merge(shifted, on=keys, suffixes=("", "_espn")))
    return pd.concat(pairs, ignore_index=True)


def vote_names(pairs):
    votes = pd.concat([
        pairs[["league", "home_name", "home_team_id", "home_team"]].set_axis(["league", "source_name", "espn_team_id", "espn_name"], axis=1),
        pairs[["league", "away_name", "away_team_id", "away_team"]].set_axis(["league", "source_name", "espn_team_id", "espn_name"], axis=1),
    ])
    counts = votes.groupby(["league", "source_name", "espn_team_id"]).agg(votes=("espn_name", "size"), espn_name=("espn_name", "last")).reset_index()
    counts["share"] = counts["votes"] / counts.groupby(["league", "source_name"])["votes"].transform("sum")
    ranked = counts.sort_values("votes", ascending=False)
    runner_up = ranked.groupby(["league", "source_name"])["votes"].nth(1).rename("runner_up")
    best = ranked.drop_duplicates(["league", "source_name"]).merge(
        ranked.loc[runner_up.index, ["league", "source_name"]].assign(runner_up=runner_up.to_numpy()),
        on=["league", "source_name"], how="left",
    )
    best["runner_up"] = best["runner_up"].fillna(0)
    best["accepted"] = (best["votes"] >= MIN_VOTES) & (best["votes"] >= MIN_RATIO * best["runner_up"])
    return best.sort_values(["league", "source_name"]).reset_index(drop=True)


def link_matches(external, espn, name_map):
    accepted = name_map[name_map["accepted"]][["league", "source_name", "espn_team_id"]]
    ext = external.merge(accepted.rename(columns={"source_name": "home_name", "espn_team_id": "home_id"}), on=["league", "home_name"], how="left")
    ext = ext.merge(accepted.rename(columns={"source_name": "away_name", "espn_team_id": "away_id"}), on=["league", "away_name"], how="left")
    joined = ext.dropna(subset=["home_id", "away_id"]).merge(
        espn[["event_id", "league", "home_team_id", "away_team_id", "date", "home_goals", "away_goals"]],
        left_on=["league", "home_id", "away_id"], right_on=["league", "home_team_id", "away_team_id"],
        suffixes=("", "_espn"),
    )
    joined["day_gap"] = (joined["date"] - joined["date_espn"]).dt.days.abs()
    joined = joined[joined["day_gap"] <= MAX_LINK_DAY_GAP].sort_values("day_gap")
    joined = joined.drop_duplicates("row_id").drop_duplicates("event_id")
    joined["score_match"] = (joined["home_goals"] == joined["home_goals_espn"]) & (joined["away_goals"] == joined["away_goals_espn"])
    links = joined[["row_id", "event_id", "score_match"]].rename(columns={"event_id": "espn_event_id"})
    return external.merge(links, on="row_id", how="left")


def link(external, espn_matches):
    espn = espn_frame(espn_matches)
    external = external.copy()
    external["row_id"] = range(len(external))
    in_range = external["date"] >= espn["date"].min() - pd.Timedelta(days=MAX_VOTE_DAY_GAP)
    name_map = vote_names(candidate_pairs(external[in_range & external["league"].isin(espn["league"].unique())], espn))
    linked = link_matches(external, espn, name_map)
    return linked.drop(columns=["row_id"]), name_map


def link_report(linked, espn_matches):
    espn = espn_frame(espn_matches)
    start = espn.groupby("league")["date"].min()
    df = linked[linked["league"].isin(start.index)].copy()
    df = df[df["date"] >= df["league"].map(start)]
    df["linked"] = df["espn_event_id"].notna()
    report = df.groupby("league").agg(rows=("linked", "size"), linked=("linked", "sum"), score_match=("score_match", "mean"))
    report["link_rate"] = report["linked"] / report["rows"]
    return report


def save_name_map(conn, source, name_map):
    table = name_map.assign(source=source)
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='team_name_map'").fetchone()
    if exists:
        others = pd.read_sql_query("SELECT * FROM team_name_map WHERE source != ?", conn, params=(source,))
        table = pd.concat([others, table], ignore_index=True)
    table.to_sql("team_name_map", conn, if_exists="replace", index=False)
