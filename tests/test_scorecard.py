import numpy as np
import pandas as pd
import pytest

from matchlens import scorecard


def log_frame():
    rows = []
    for i, (m, t, p, y, src) in enumerate([(0.6, 0.55, 0.5, 1, "b365"), (0.3, 0.35, 0.4, 0, "dk"), (0.7, np.nan, 0.6, 1, "dk"), (0.2, 0.25, np.nan, 0, None)]):
        rows.append({"event_id": str(i), "market": "home", "model_p": m, "twin_p": t, "market_p": p, "outcome": float(y), "market_src": src})
    return pd.DataFrame(rows)


def test_source_table_uses_common_rows_only():
    table = scorecard.source_table(log_frame())
    assert (table["n"] == 2).all()
    assert table.loc["model", "brier"] == pytest.approx(((0.6 - 1) ** 2 + 0.3 ** 2) / 2)


def test_market_table_counts_each_source():
    table = scorecard.market_table(log_frame())
    assert table.loc["home", "model_n"] == 4 and table.loc["home", "twin_n"] == 3 and table.loc["home", "market_n"] == 3


def test_calibration_buckets():
    table = scorecard.calibration(log_frame(), "model_p")
    assert table["n"].sum() == 4
    assert set(table["low"].round(1)) == {0.2, 0.3, 0.6, 0.7}


def test_market_source_table():
    table = scorecard.market_source_table(log_frame()).set_index("source")
    assert table.loc["dk", "n"] == 2 and table.loc["b365", "n"] == 1


def coupon_legs():
    base = {"day": "2030-01-01", "settled_at": "x", "p_book": 0.5}
    return pd.DataFrame([
        {**base, "coupon": "blue", "leg": 1, "odds": 1.5, "p_safe": 0.7, "outcome": 1.0},
        {**base, "coupon": "blue", "leg": 2, "odds": 1.4, "p_safe": 0.75, "outcome": 1.0},
        {**base, "coupon": "blue", "leg": 3, "odds": 1.6, "p_safe": 0.7, "outcome": None},
        {**base, "coupon": "red", "leg": 1, "odds": 3.0, "p_safe": 0.3, "outcome": 0.0},
        {**base, "coupon": "red", "leg": 2, "odds": 3.2, "p_safe": 0.3, "outcome": None, "settled_at": None},
        {**base, "coupon": "yellow", "leg": 1, "odds": 2.0, "p_safe": 0.5, "outcome": None, "settled_at": None},
    ])


def test_coupon_results_handle_void_and_pending():
    results = scorecard.coupon_results(coupon_legs()).set_index("coupon")
    assert results.loc["blue", "status"] == "won" and results.loc["blue", "legs"] == 2
    assert results.loc["blue", "odds"] == pytest.approx(2.1)
    assert results.loc["red", "status"] == "lost"
    assert results.loc["yellow", "status"] == "pending"


def test_coupon_summary_roi():
    summary = scorecard.coupon_summary(scorecard.coupon_results(coupon_legs()))
    assert summary.loc["blue", "roi"] == pytest.approx(1.1)
    assert summary.loc["red", "roi"] == pytest.approx(-1.0)
    assert np.isnan(summary.loc["yellow", "hit_rate"])


def test_scorecard_views_render():
    from ui import scorecard_views as sv
    log = log_frame()
    html = "".join([
        sv.source_section(scorecard.source_table(log)),
        sv.market_section(scorecard.market_table(log)),
        sv.calibration_section(scorecard.calibration(log, "twin_p"), "twin"),
        sv.market_source_section(scorecard.market_source_table(log)),
        sv.coupon_summary_section(scorecard.coupon_summary(scorecard.coupon_results(coupon_legs())), scorecard.leg_summary(coupon_legs())),
        sv.coupon_history_section(scorecard.coupon_results(coupon_legs())),
    ])
    assert "EN İYİ" in html and "tuttu" in html and "yattı" in html
