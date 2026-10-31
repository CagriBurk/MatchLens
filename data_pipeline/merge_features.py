import pandas as pd

from data_pipeline.db import connect


def run():
    with connect() as conn:
        tactics = pd.read_sql_query("SELECT * FROM team_tactical_form", conn)
        elo = pd.read_sql_query('SELECT original_team_name, "from", "to", elo FROM historical_club_elo', conn)

        tactics["date"] = pd.to_datetime(tactics["date"]).dt.normalize()
        elo["from"] = pd.to_datetime(elo["from"])
        elo["to"] = pd.to_datetime(elo["to"])

        merged = tactics.merge(elo, how="left", left_on="team", right_on="original_team_name")
        in_range = (merged["date"] >= merged["from"]) & (merged["date"] <= merged["to"])
        dataset = merged[in_range].drop(columns=["original_team_name", "from", "to"])

        missing = len(tactics) - len(dataset)
        if missing:
            print(f"Warning: {missing} team-match rows have no Elo rating")

        dataset.to_sql("ml_master_dataset", conn, if_exists="replace", index=False)
    print(f"ml_master_dataset: {len(dataset)} rows")


if __name__ == "__main__":
    run()
