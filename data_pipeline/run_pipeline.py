import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__line__))))

from data_pipeline import ingest_historical
from data_pipeline import ingest_api
from data_pipeline import team_mapper
from data_pipeline import feature_engine

def main():
    print("Initializing MatchLens Data Pipeline")

    print("[1/4] Data Ingestion")
    # ingest_historical.run()
    # ingest_api.run()
    print("Ingestion completed")

    print("[2/4] Team Mapping")
    # team_mapper.run()
    print("Mapping completed")

    print("[3/4] Feature Engineering")
    feature_engine.run()
    print("Feature Engineering completed")

    print("MatchLens Pipeline execution finished successfully")

if __name__ == "__main__":
    main()
