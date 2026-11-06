from datetime import date

import pandas as pd

from matchlens import coupons, update


def fixtures():
    return pd.DataFrame({"event_id": ["afternoon", "midnight", "early", "morning"],
                         "kickoff_utc": ["2026-11-07T10:00Z", "2026-11-07T21:00Z", "2026-11-08T04:00Z", "2026-11-08T05:00Z"]})


def test_day_fixtures_include_night_matches_until_next_morning_run():
    assert update.day_fixtures(fixtures(), date(2026, 11, 7))["event_id"].tolist() == ["afternoon", "midnight", "early"]


def fail_if_called(*args, **kwargs):
    raise AssertionError("must not write")


def test_failed_nesine_fetch_writes_nothing_and_reports_failure(monkeypatch):
    def unavailable(records):
        raise ConnectionError("down")

    monkeypatch.setattr(update.nesine, "odds_for", unavailable)
    monkeypatch.setattr(update.nesine, "save", fail_if_called)
    monkeypatch.setattr(coupons, "generate", fail_if_called)
    monkeypatch.setattr(coupons, "log_selections", fail_if_called)
    assert update.run_coupons(fixtures(), date(2026, 11, 7), (0, 0)) is False


def test_successful_fetch_writes_day_fixtures(monkeypatch):
    seen = {}
    offers = pd.DataFrame({"event_id": ["afternoon"]})
    monkeypatch.setattr(update.nesine, "odds_for", lambda records: (offers, offers))
    monkeypatch.setattr(update.nesine, "save", lambda table: len(table))

    def record(day, records, table, force=False):
        seen[len(seen)] = records["event_id"].tolist()
        return 1

    monkeypatch.setattr(coupons, "generate", record)
    monkeypatch.setattr(coupons, "log_selections", record)
    assert update.run_coupons(fixtures(), date(2026, 11, 7), (0, 0)) is True
    assert seen == {0: ["afternoon", "midnight", "early"], 1: ["afternoon", "midnight", "early"]}


def test_no_fixtures_is_not_a_failure():
    assert update.run_coupons(pd.DataFrame(), date(2026, 11, 7), (0, 0)) is True
