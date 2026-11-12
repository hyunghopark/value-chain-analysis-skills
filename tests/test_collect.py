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

BASE_YAHOO_ITEMS = {"info", "history", *collect.YAHOO_FRAMES}
US_ITEMS = BASE_YAHOO_ITEMS | {"edgar_financials", "edgar_shares"}
KR_ITEMS = {
    "krx_stock",
    "dart_financials",
    "naver_integration",
    "wisereport_eps",
    "daum_days",
    "naver_trend",
    "toss_stock_flows",
    "toss_market_flows",
}


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
    ri.RawInputs({"000660.KS": {**items, **flows}})  # still a valid set of items


def test_toss_flows_recorded_gracefully(monkeypatch):
    """Toss MCP flows are captured without raising exceptions."""
    monkeypatch.setattr(collect.mcp_client, "get_toss_stock_flows", lambda code: {"test": "stock_flow"})
    monkeypatch.setattr(collect.mcp_client, "get_toss_market_flows", lambda market: {"test": "market_flow"})
    monkeypatch.setattr(collect.requests, "get", lambda url, **kwargs: type("R", (), {"json": lambda self: [{"bizdate": "20261019"}]})())
    items = collect.collect_flows("000660.KS")
    assert items["toss_stock_flows"]["status"] == "ok"
    assert items["toss_market_flows"]["status"] == "ok"
    assert items["naver_trend"]["status"] == "ok"


@pytest.mark.network
def test_collect_us_ticker():
    items = collect.collect_ticker("MU")
    assert set(items) == US_ITEMS
    assert items["info"]["status"] == "ok" and "symbol" in items["info"]["data"]
    assert items["history"]["status"] == "ok" and items["history"]["kind"] == "frame"
    raw = ri.RawInputs({"MU": items})
    hist = raw.frame("MU", "history")
    assert {"Open", "High", "Low", "Close", "Volume"} <= set(hist.columns) and len(hist) > 1000
    assert str(hist.index.tz) == "America/New_York"


@pytest.mark.network
def test_collect_kr_ticker():
    items = {**collect.collect_ticker("000660.KS"), **collect.collect_kr("000660.KS"), **collect.collect_flows("000660.KS")}
    assert set(items) == BASE_YAHOO_ITEMS | KR_ITEMS
    for name in ("naver_integration", "wisereport_eps", "daum_days", "naver_trend"):
        assert items[name]["status"] == "ok", (name, items[name].get("error"))
    assert items["wisereport_eps"]["kind"] == "table" and items["wisereport_eps"]["data"]["headers"]
    ri.RawInputs({"000660.KS": items})
