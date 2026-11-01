import numpy as np

from matchlens.market_lambda import fair_three_way, fair_two_way

TOTAL_WEIGHTS = {"usa.1": 0.2, "nor.1": 0.2, "den.1": 0.2, "bel.1": 0.1}
SUPREMACY_WEIGHT = 0.0


def blend_lambdas(model, market, w_total, w_supremacy=SUPREMACY_WEIGHT):
    (model_home, model_away), (market_home, market_away) = model, market
    log_total = w_total * np.log(model_home + model_away) + (1 - w_total) * np.log(market_home + market_away)
    log_ratio = w_supremacy * np.log(model_home / model_away) + (1 - w_supremacy) * np.log(market_home / market_away)
    total, ratio = np.exp(log_total), np.exp(log_ratio)
    return float(total * ratio / (1 + ratio)), float(total / (1 + ratio))


def market_lambdas(solver, odds_row):
    prices = [odds_row.get(key) for key in ("b365_home", "b365_draw", "b365_away")]
    if not odds_row or not all(prices):
        return None
    fair = fair_three_way([prices[0]], [prices[1]], [prices[2]])[0]
    line, over, under = odds_row.get("b365_goal_line"), odds_row.get("b365_over"), odds_row.get("b365_under")
    if line and over and under:
        lam_home, lam_away = solver.solve(fair[0], fair[2], fair_two_way(over, under), line=line)
    else:
        lam_home, lam_away = solver.solve(fair[0], fair[2])
    return float(lam_home[0]), float(lam_away[0])


def final_lambdas(league, model, market):
    if market is None:
        return model, "model"
    return blend_lambdas(model, market, TOTAL_WEIGHTS.get(league, 0.0)), "b365"
