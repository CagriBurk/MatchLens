import numpy as np
import pandas as pd
import pytest

from matchlens import bulletin
from ui import data


def record(**extra):
    base = {"event_id": "1", "home": 0.47, "draw": 0.27, "away": 0.26, "over_2.5": 0.5, "btts_yes": 0.54,
            "twin_home": 0.45, "twin_draw": 0.28, "twin_away": 0.27, "market_home": 0.40, "market_draw": 0.27, "market_away": 0.33,
            "lam_home": 1.57, "lam_away": 1.10, "rho": -0.05}
    return {**base, **extra}


def test_agreement_needs_both_sources_above_market():
    hits, near = data.agreements(pd.DataFrame([record()]), edge=0.04)
    assert [(h["key"], round(h["low"], 2)) for h in hits] == [("home", 0.05)]
    hits, near = data.agreements(pd.DataFrame([record(twin_home=0.42)]), edge=0.04)
    assert hits == [] and near["key"] == "home"


def test_agreement_skips_missing_market():
    hits, near = data.agreements(pd.DataFrame([record(market_home=np.nan, market_draw=np.nan, market_away=np.nan)]))
    assert hits == [] and near is None


def test_score_grid_folds_tail_and_sums_to_one():
    grid, tops = data.score_grid(pd.Series(record()))
    assert grid.shape == (6, 6)
    assert grid.sum() == pytest.approx(1.0)
    assert len(tops) == 5


def test_snapshots_split_by_local_day(tmp_path, monkeypatch):
    monkeypatch.setattr(bulletin, "BULLETIN_DIR", tmp_path)
    records = pd.DataFrame([
        {"event_id": "1", "kickoff_utc": "2026-11-02T20:00Z", "league": "eng.1"},
        {"event_id": "2", "kickoff_utc": "2026-11-02T21:30Z", "league": "usa.1"},
    ])
    candidates = pd.DataFrame([{"event_id": "2", "market": "1"}])
    days = bulletin.save_snapshots(records, candidates)
    assert [str(d) for d in days] == ["2026-11-02", "2026-11-03"]
    assert pd.read_csv(tmp_path / "2026-11-03_matches.csv")["event_id"].tolist() == [2]
    assert not (tmp_path / "2026-11-02_odds.csv").exists()
    assert (tmp_path / "2026-11-03_odds.csv").exists()
