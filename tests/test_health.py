import numpy as np
import pandas as pd
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


def test_slope_standard_error_matches_spread():
    rng = np.random.default_rng(3)
    p = 1 / (1 + np.exp(-rng.normal(0, 0.8, 10000)))
    slopes = []
    for _ in range(40):
        y = (rng.random(len(p)) < p).astype(float)
        _, slope, se = health.calibration_fit_se(p, y)
        slopes.append(slope)
    assert np.std(slopes) == pytest.approx(se, rel=0.35)


def test_status_needs_practical_and_statistical_miss():
    base = {"n": 5000, "bias": 0.0, "z_bias": 0.0, "slope": 1.0, "z_slope": 0.0, "skill": 0.01}
    assert health.status(base) == "PASS"
    assert health.status({**base, "slope": 0.75, "z_slope": -1.5}) == "WARN"
    assert health.status({**base, "slope": 0.75, "z_slope": -3.0}) == "FAIL"
    assert health.status({**base, "bias": 0.003, "z_bias": 3.0}) == "WARN"
    assert health.status({**base, "bias": -0.02, "z_bias": -4.0}) == "FAIL"
    assert health.status({**base, "skill": -0.01}) == "FAIL"
    assert health.status({**base, "slope": 0.5, "z_slope": -9.0}, "htft_1/2") == "info"


def test_perfect_model_rarely_fails():
    rng = np.random.default_rng(5)
    p = 1 / (1 + np.exp(-rng.normal(0, 0.6, 5000)))
    assert health.perfect_ok_rate(p, n_sims=50) >= 0.94


def test_block_bootstrap_and_paired_verdict():
    rng = np.random.default_rng(11)
    n = 6000
    weeks = np.repeat(pd.date_range("2024-07-01", periods=60, freq="W-MON").to_numpy(), n // 60)
    frame = lambda ll1, llg: pd.DataFrame({"event_id": np.arange(n).astype(str), "week": weeks, "final": True,
                                           "ll_1x2": ll1, "ll_goal": llg})
    base_1x2, base_goal = rng.uniform(0.5, 1.5, n), rng.uniform(2.0, 3.0, n)
    mean, lo, hi = health.block_bootstrap(np.full(n, -0.001) + rng.normal(0, 0.01, n), weeks)
    assert lo < mean < hi < 0
    _, verdict = health.paired_comparison(frame(base_1x2 - 0.002, base_goal), frame(base_1x2, base_goal))
    assert verdict == "ACCEPT"
    _, verdict = health.paired_comparison(frame(base_1x2 - 0.002, base_goal + 0.01), frame(base_1x2, base_goal))
    assert verdict == "REJECT"
    _, verdict = health.paired_comparison(frame(base_1x2, base_goal), frame(base_1x2, base_goal))
    assert verdict == "REJECT"
