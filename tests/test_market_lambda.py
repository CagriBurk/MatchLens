import numpy as np
import pytest

from matchlens import markets
from matchlens.market_lambda import ImpliedLambda, fair_three_way, fair_two_way


@pytest.fixture(scope="module")
def solver():
    return ImpliedLambda(rho=-0.07)


@pytest.mark.parametrize("lam_home,lam_away", [(1.6, 1.1), (0.8, 2.3), (2.5, 0.6), (1.2, 1.2)])
def test_recovers_lambdas_from_probabilities(solver, lam_home, lam_away):
    probs = markets.core_probs(np.array([lam_home]), np.array([lam_away]), -0.07)
    full = solver.solve(probs["home"], probs["away"], probs["over_2.5"])
    result_only = solver.solve(probs["home"], probs["away"])
    for lh, la in (full, result_only):
        assert lh[0] == pytest.approx(lam_home, abs=0.011)
        assert la[0] == pytest.approx(lam_away, abs=0.011)


def test_missing_inputs_give_nan(solver):
    lam_home, _ = solver.solve(np.array([np.nan, 0.45]), np.array([0.3, 0.3]), np.array([0.5, np.nan]))
    assert np.isnan(lam_home[0]) and np.isfinite(lam_home[1])


def test_fair_probabilities_sum_to_one():
    assert fair_three_way([2.0], [3.4], [3.8]).sum() == pytest.approx(1.0)
    assert fair_two_way(1.9, 1.95) + fair_two_way(1.95, 1.9) == pytest.approx(1.0)


@pytest.mark.parametrize("line", [2.25, 2.75, 3.0])
def test_recovers_lambdas_from_asian_line(solver, line):
    from matchlens import odds
    probs = markets.core_probs(np.array([1.7]), np.array([1.2]), -0.07)
    totals = markets.total_distribution(markets.score_matrix(1.7, 1.2, -0.07))
    parts = odds.split_line(line)
    win = sum(totals[int(np.floor(p)) + 1:].sum() for p in parts) / len(parts)
    push = sum(totals[int(p)] for p in parts if float(p).is_integer()) / len(parts)
    lam_home, lam_away = solver.solve(probs["home"], probs["away"], np.array([win / (1 - push)]), line=line)
    assert lam_home[0] == pytest.approx(1.7, abs=0.011)
    assert lam_away[0] == pytest.approx(1.2, abs=0.011)
