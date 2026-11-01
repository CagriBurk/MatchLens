import json

import numpy as np
import pandas as pd

from data_pipeline.config import DATA_DIR
from data_pipeline.db import connect
from matchlens import markets

PATH = DATA_DIR / "model" / "goal_weights.json"
MAX_TOTAL = markets.GOAL_GROUP_MAX
GROUPS = 2 * (MAX_TOTAL + 1)
SHRINK = 50.0


def observed_group(home_goals, away_goals):
    home_goals, away_goals = np.asarray(home_goals, int), np.asarray(away_goals, int)
    return np.minimum(home_goals + away_goals, MAX_TOTAL) + (MAX_TOTAL + 1) * ((home_goals > 0) & (away_goals > 0))


def fit(preds, shrink=SHRINK):
    predicted = np.zeros(GROUPS)
    index = None
    for row in preds.itertuples():
        matrix = markets.score_matrix(row.lam_home, row.lam_away, row.rho)
        index = markets.goal_groups(matrix.shape[0]) if index is None else index
        predicted += np.bincount(index.ravel(), weights=matrix.ravel(), minlength=GROUPS)
    observed = np.bincount(observed_group(preds["home_goals"], preds["away_goals"]), minlength=GROUPS).astype(float)
    return (observed + shrink) / (predicted + shrink)


def save(weights, path=PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"weights": [float(w) for w in weights], "max_total": MAX_TOTAL}), encoding="utf-8")


def load(path=PATH):
    if not path.exists():
        return None
    return np.array(json.loads(path.read_text(encoding="utf-8"))["weights"])


def refresh():
    with connect() as conn:
        preds = pd.read_sql_query("SELECT lam_home, lam_away, rho, home_goals, away_goals FROM backtest_predictions", conn)
    weights = fit(preds.dropna())
    save(weights)
    return weights, len(preds)


def main():
    weights, n = refresh()
    labels = [f"{t if t < MAX_TOTAL else str(MAX_TOTAL) + '+'}{' btts' if b else ''}" for b in (0, 1) for t in range(MAX_TOTAL + 1)]
    print(f"goal weights from {n} walk-forward predictions -> {PATH}")
    print(pd.Series(weights, index=labels).round(3).to_string())


if __name__ == "__main__":
    main()
