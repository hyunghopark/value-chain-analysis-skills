"""
Tests for collect.py — the only stage that reaches external sources (spec 003, data-model §2·§3).
Network tests run locally only (CI: -m "not network").
"""

import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import collect  # noqa: E402
import raw_inputs as ri  # noqa: E402

YAHOO_ITEMS = {"info", "history", *collect.YAHOO_FRAMES}
KR_ITEMS = {"naver_integration", "wisereport_eps", "pykrx_fundamental", "daum_days", "naver_trend", "daum_quote", "daum_investor_days"}


def test_failures_are_recorded_not_raised(monkeypatch):
    """A source failure becomes status 'error' with the exception text (the pipeline turns it into the warning)."""
    def boom(*args, **kwargs):
        raise ConnectionError("timed out")
    monkeypatch.setattr(collect.requests, "get", boom)
    items = collect.collect_kr("000660.KS")
    assert items["naver_integration"]["status"] == "error" and items["naver_integration"]["error"] == "timed out"
    assert items["wisereport_eps"]["status"] == "error" and items["daum_days"]["status"] == "error"
    flows = collect.collect_flows("000660.KS")
    assert flows["naver_trend"]["status"] == "error"
    assert flows["daum_quote"]["status"] == "skipped" and flows["daum_investor_days"]["status"] == "skipped"
    ri.RawInputs({"000660.KS": {**items, **flows}})  # still a valid set of items


def test_daum_intraday_only_without_todays_naver_row(monkeypatch):
    """Daum is asked only on a weekday when Naver has no row for the day the trend arrived (same rule as the table)."""
    calls = []

    class R:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def fake_get(url, **kwargs):
        calls.append(url)
        if "trend" in url:
            return R([{"bizdate": "20261019"}])
        if "quotes" in url:
            return R({"date": "2026-10-20 10:00:00"})
        return R({"data": []})
    monkeypatch.setattr(collect.requests, "get", fake_get)
    monkeypatch.setattr(collect, "now_kst", lambda: collect.datetime.datetime(2026, 10, 20, 10, 0, 0, tzinfo=collect.KST))
    items = collect.collect_flows("000660.KS")
    assert [i["status"] for i in (items["naver_trend"], items["daum_quote"], items["daum_investor_days"])] == ["ok"] * 3
    assert len(calls) == 3

    calls.clear()
    monkeypatch.setattr(collect, "now_kst", lambda: collect.datetime.datetime(2026, 10, 19, 16, 0, 0, tzinfo=collect.KST))
    items = collect.collect_flows("000660.KS")  # Naver already has today's row
    assert items["daum_quote"]["status"] == "skipped" and len(calls) == 1


@pytest.mark.network
def test_collect_us_ticker():
    items = collect.collect_ticker("MU")
    assert set(items) == YAHOO_ITEMS
    assert items["info"]["status"] == "ok" and "symbol" in items["info"]["data"]
    assert items["history"]["status"] == "ok" and items["history"]["kind"] == "frame"
    raw = ri.RawInputs({"MU": items})
    hist = raw.frame("MU", "history")
    assert {"Open", "High", "Low", "Close", "Volume"} <= set(hist.columns) and len(hist) > 1000
    assert str(hist.index.tz) == "America/New_York"


@pytest.mark.network
def test_collect_kr_ticker():
    items = {**collect.collect_ticker("000660.KS"), **collect.collect_kr("000660.KS"), **collect.collect_flows("000660.KS")}
    assert set(items) == YAHOO_ITEMS | KR_ITEMS
    for name in ("naver_integration", "wisereport_eps", "daum_days", "naver_trend"):
        assert items[name]["status"] == "ok", (name, items[name].get("error"))
    assert items["wisereport_eps"]["kind"] == "table" and items["wisereport_eps"]["data"]["headers"]
    ri.RawInputs({"000660.KS": items})
