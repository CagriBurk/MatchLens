import numpy as np
import pytest

from matchlens import odds


def test_fair_probs_remove_margin():
    probs = odds.fair_probs([1.85, 3.6, 4.75])
    assert probs.sum() == pytest.approx(1.0)
    assert odds.margin([1.85, 3.6, 4.75]) > 0


def test_expected_value():
    assert odds.expected_value(0.5, 2.2) == pytest.approx(0.1)


@pytest.mark.parametrize("goals,line,result", [
    (3, 2.5, 0.9), (2, 2.5, -1.0),
    (3, 3.0, 0.0), (4, 3.0, 0.9), (2, 3.0, -1.0),
    (3, 2.75, 0.45), (2, 2.75, -1.0), (4, 2.75, 0.9),
    (3, 3.25, -0.5), (4, 3.25, 0.9),
])
def test_settle_over_asian_lines(goals, line, result):
    assert odds.settle_over(goals, line, 1.9) == pytest.approx(result)


@pytest.mark.parametrize("goals,line,result", [
    (2, 2.5, 0.9), (3, 3.0, 0.0), (2, 2.25, 0.45), (3, 3.25, 0.45), (3, 2.75, -0.5), (4, 2.75, -1.0),
])
def test_settle_under_asian_lines(goals, line, result):
    assert odds.settle_under(goals, line, 1.9) == pytest.approx(result)


def test_asian_total_ev_matches_manual():
    totals = np.array([0.1, 0.2, 0.3, 0.25, 0.15])
    expected = -0.1 - 0.2 - 0.3 + 0.25 * 0.0 + 0.15 * 0.9
    assert odds.asian_total_ev(totals, 3.0, 1.9, "over") == pytest.approx(expected)
