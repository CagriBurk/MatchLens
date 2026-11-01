import argparse
from datetime import datetime, timedelta

import pandas as pd

from data_pipeline.espn.leagues import LEAGUES
from data_pipeline.ingest_espn import build_tables, current_year, fetch_summaries, summary_targets
from matchlens import bulletin, tracking, twins
from matchlens.data import load_matches

LOG_DAYS = 3


def run(leagues, days, workers):
    bulletin.refresh_scoreboards(leagues)
    years = bulletin.refresh_years()
    targets = summary_targets(leagues, years)
    fetch_summaries(targets, workers=workers)
    build_tables(leagues, years, incremental=True)
    pool = twins.build_pool()
    print(f"twins_pool: {len(pool)} matches")

    matches = load_matches(leagues, from_year=current_year() - 1)
    settled = tracking.settle(matches)
    today = datetime.now(bulletin.LOCAL_TZ).date()
    dates = [today + timedelta(days=i) for i in range(days)]
    records, candidates = bulletin.build(dates, leagues, refresh=False)
    logged = tracking.log_predictions(records, candidates)
    bulletin.save_snapshots(records, candidates)
    print(f"settled {settled} predictions, logged {logged} predictions for {len(records)} fixtures")

    accuracy, betting = tracking.report()
    if accuracy is None:
        return
    with pd.option_context("display.width", 200):
        print(accuracy.round(3).to_string())
        if len(betting):
            print(f"Bets with EV > {tracking.MIN_EV:.0%}")
            print(betting.round(3).to_string())


def main():
    parser = argparse.ArgumentParser(description="Daily update: ESPN data, prediction log and settlement")
    parser.add_argument("--leagues", nargs="*", default=list(LEAGUES))
    parser.add_argument("--days", type=int, default=LOG_DAYS)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    run(args.leagues, args.days, args.workers)


if __name__ == "__main__":
    main()
