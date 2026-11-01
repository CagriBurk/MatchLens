import numpy as np


def implied(odds):
    odds = np.asarray(odds, dtype=float)
    return 1 / odds


def margin(odds):
    return float(implied(odds).sum() - 1)


def fair_probs(odds):
    probs = implied(odds)
    return probs / probs.sum()


def fair_odds(prob):
    return 1 / prob if prob > 0 else float("inf")


def expected_value(prob, odds):
    return prob * odds - 1


def split_line(line):
    frac = round(line % 1, 2)
    if frac in (0.25, 0.75):
        return [line - 0.25, line + 0.25]
    return [line]


def settle_over(total_goals, line, odds):
    parts = split_line(line)
    payout = 0.0
    for part in parts:
        if total_goals > part:
            payout += odds
        elif total_goals == part:
            payout += 1.0
    return payout / len(parts) - 1


def settle_under(total_goals, line, odds):
    parts = split_line(line)
    payout = 0.0
    for part in parts:
        if total_goals < part:
            payout += odds
        elif total_goals == part:
            payout += 1.0
    return payout / len(parts) - 1


def asian_total_ev(totals, line, odds, side):
    settle = settle_over if side == "over" else settle_under
    return float(sum(p * settle(k, line, odds) for k, p in enumerate(totals)))
