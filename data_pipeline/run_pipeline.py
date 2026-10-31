import argparse

from data_pipeline import feature_engine, ingest_elo, ingest_understat, merge_features

STEPS = {
    "understat": ingest_understat.run,
    "elo": ingest_elo.run,
    "features": feature_engine.run,
    "merge": merge_features.run,
}


def main():
    parser = argparse.ArgumentParser(description="MatchLens data pipeline")
    parser.add_argument("steps", nargs="*", choices=list(STEPS), default=["features", "merge"])
    args = parser.parse_args()
    for step in args.steps:
        print(f"Running step: {step}")
        STEPS[step]()


if __name__ == "__main__":
    main()
