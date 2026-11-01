import numpy as np
import pytest

from matchlens import health


def test_calibration_fit_recovers_slope():
    rng = np.random.default_rng(1)
    logit = rng.normal(0, 1.2, 20000)
    true_p = 1 / (1 + np.exp(-logit))
    y = (rng.random(20000) < true_p).astype(float)
    overconfident = 1 / (1 + np.exp(-1.5 * logit))
    _, slope = health.calibration_fit(overconfident, y)
    assert slope == pytest.approx(1 / 1.5, abs=0.05)
    _, slope = health.calibration_fit(true_p, y)
    assert slope == pytest.approx(1.0, abs=0.05)


def test_metrics_and_status():
    p = np.full(1000, 0.6)
    y = np.r_[np.ones(550), np.zeros(450)]
    row = health.metrics(p, y, np.full(1000, 0.5))
    assert row["bias"] == pytest.approx(0.05)
    assert health.status({**row, "slope": 1.0}) == "FAIL"
    assert health.status({"n": 10}) == "n/a"
