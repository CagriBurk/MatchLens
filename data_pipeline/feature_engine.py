import pandas as pd

from data_pipeline.db import connect

ROLLING_COLUMNS = ["xg_for", "xg_against", "ppda", "deep_completions"]
ROLLING_WINDOWS = [3, 5]
DEFAULT_REST_DAYS = 7


def to_team_rows(matches: pd.DataFrame) -> pd.DataFrame:
    columns = ["date", "team", "xg_for", "xg_against", "ppda", "deep_completions"]
    home = matches[["date", "home_team", "home_xg", "away_xg", "home_ppda", "home_deep_completions"]].copy()
    home.columns = columns
    away = matches[["date", "away_team", "away_xg", "home_xg", "away_ppda", "away_deep_completions"]].copy()
    away.columns = columns
    return pd.concat([home, away]).sort_values(["team", "date"]).reset_index(drop=True)


def add_form_features(team_rows: pd.DataFrame) -> pd.DataFrame:
    df = team_rows.copy()
    grouped = df.groupby("team")
    for window in ROLLING_WINDOWS:
        for col in ROLLING_COLUMNS:
            df[f"rolling_{window}_{col}"] = grouped[col].transform(
                lambda s: s.rolling(window=window, min_periods=1).mean().shift(1)
            )
    df["rest_days"] = grouped["date"].diff().dt.days.fillna(DEFAULT_REST_DAYS)
    df["prev_xg_for"] = grouped["xg_for"].shift(1)
    df["prev_ppda"] = grouped["ppda"].shift(1)
    df["prev_deep"] = grouped["deep_completions"].shift(1)
    df["diff_xg_rolling_3"] = df["prev_xg_for"] - df["rolling_3_xg_for"]
    df["diff_ppda_rolling_3"] = df["prev_ppda"] - df["rolling_3_ppda"]
    df["diff_deep_rolling_3"] = df["prev_deep"] - df["rolling_3_deep_completions"]
    return df


def run():
    query = (
        "SELECT date, home_team, away_team, home_xg, away_xg, home_ppda, away_ppda, "
        "home_deep_completions, away_deep_completions FROM tactical_match_stats"
    )
    with connect() as conn:
        matches = pd.read_sql_query(query, conn, parse_dates=["date"])
        features = add_form_features(to_team_rows(matches))
        features.to_sql("team_tactical_form", conn, if_exists="replace", index=False)
    print(f"team_tactical_form: {len(features)} rows")


if __name__ == "__main__":
    run()
