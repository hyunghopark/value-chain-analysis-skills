"""
Tests for raw_inputs.py — raw input storage for reproducible Section 4 (spec 003).
Covers research R3 (exact DataFrame round trip), data-model §2·§3·§5, FR-007, FR-008.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import raw_inputs as ri  # noqa: E402

T = "2026-10-20T14:05:12+09:00"


def roundtrip(df):
    return ri.decode_frame(json.loads(json.dumps(ri.encode_frame(df), ensure_ascii=False)))


def assert_same(df, back):
    assert df.equals(back)
    assert df.index.equals(back.index) and df.columns.equals(back.columns)
    assert df.index.dtype == back.index.dtype and df.columns.dtype == back.columns.dtype
    assert df.index.name == back.index.name and df.columns.name == back.columns.name
    assert list(df.dtypes) == list(back.dtypes)


# --- Frames shaped like the Yahoo tables the pipeline reads (R3) ---

def price_history(tz, start, periods):
    idx = pd.date_range(start, periods=periods, freq="D", tz=tz, unit="s", name="Date")
    idx = pd.DatetimeIndex(list(idx), name="Date").as_unit("s")  # no freq, like yfinance
    rng = np.random.default_rng(1)
    close = 100 + rng.standard_normal(periods).cumsum()
    df = pd.DataFrame({
        "Open": close + 0.5, "High": close + 1.25, "Low": close - 1.0, "Close": close,
        "Adj Close": close * 0.98, "Volume": rng.integers(1_000, 9_000_000, periods).astype("int64"),
        "Dividends": 0.0, "Stock Splits": 0.0,
    }, index=idx)
    df.loc[df.index[3], "Close"] = np.nan
    return df


def test_history_seoul_round_trip():
    assert_same(df := price_history("Asia/Seoul", "2026-01-01", 40), roundtrip(df))


def test_history_new_york_across_dst_round_trip():
    df = price_history("America/New_York", "2026-02-20", 40)  # DST starts 2026-03-08
    back = roundtrip(df)
    assert_same(df, back)
    assert str(back.index.tz) == "America/New_York"


def test_statement_round_trip():
    cols = pd.DatetimeIndex(["2025-12-31", "2024-12-31", "2023-12-31", "2022-12-31"]).as_unit("s")
    rows = pd.Index(["Net Income", "Operating Income", "Total Revenue", "Total Unusual Items"], dtype="str")
    df = pd.DataFrame([[1.5e12, 2.0e12, np.nan, 3.1e11], [2e12, 2.5e12, 1e12, 4e11],
                       [9e12, 8e12, 7e12, 6e12], [np.nan, -1.2e10, 3.3e9, 0.0]], index=rows, columns=cols)
    assert_same(df, roundtrip(df))


def test_consensus_round_trip():
    idx = pd.Index(["0q", "+1q", "0y", "+1y"], dtype="str", name="period")
    df = pd.DataFrame({"avg": [1.1, 2.2, 8.0, 12.5], "low": [1.0, 2.0, 7.0, np.nan],
                       "numberOfAnalysts": [20, 21, 30, 29]}, index=idx)
    assert_same(df, roundtrip(df))


def test_earnings_history_and_infinity_round_trip():
    idx = pd.DatetimeIndex(["2025-12-31", "2026-03-31"], name="quarter").as_unit("ns")
    df = pd.DataFrame({"epsEstimate": [1.0, np.inf], "surprisePercent": [-np.inf, 0.05]}, index=idx)
    assert_same(df, roundtrip(df))


def test_empty_frame_round_trip():
    df = pd.DataFrame()
    back = roundtrip(df)
    assert back.empty and back.shape == df.shape


def test_encoded_frame_is_plain_json():
    text = json.dumps(ri.encode_frame(price_history("Asia/Seoul", "2026-01-01", 5)), allow_nan=False)
    assert '"tz": "Asia/Seoul"' in text and "+09:00" not in text


# --- Items and access (data-model §2, §5) ---

def item(**kw):
    base = {"source": "yahoo", "fetched_at": T, "status": "ok", "kind": "json", "data": {"symbol": "MU"},
            "error": None, "note": None}
    base.update(kw)
    return base


def snapshot(inputs, version=2):
    meta = {"collected_at": T}
    if version is not None:
        meta["format_version"] = version
    return {"meta": meta, "inputs": inputs}


def test_access_by_kind():
    hist = price_history("America/New_York", "2026-01-01", 10)
    raw = ri.RawInputs({"MU": {
        "info": item(),
        "history": item(kind="frame", data=ri.encode_frame(hist)),
        "wisereport_eps": item(source="wisereport", kind="table", data={"headers": ["a"], "rows": [["1"]]}),
    }})
    assert raw.json("MU", "info") == {"symbol": "MU"}
    assert_same(hist, raw.frame("MU", "history"))
    assert raw.table("MU", "wisereport_eps")["rows"] == [["1"]]
    assert raw.fetched_at("MU", "info").isoformat() == T
    assert raw.symbols() == ["MU"]
    # Callers may modify what they get without changing the stored input
    got = raw.frame("MU", "history")
    got.iloc[0, 0] = -1
    assert_same(hist, raw.frame("MU", "history"))


@pytest.mark.parametrize("status,extra", [("empty", {}), ("error", {"error": "timeout"}), ("skipped", {})])
def test_non_ok_items_return_none_with_item(status, extra):
    raw = ri.RawInputs({"MU": {"history": item(status=status, kind=None, data=None, **extra)}})
    assert raw.frame("MU", "history") is None
    assert raw.get("MU", "history")["status"] == status
    if status == "error":
        assert raw.get("MU", "history")["error"] == "timeout"


def test_missing_input_names_path():
    raw = ri.RawInputs({"MU": {"info": item()}})
    with pytest.raises(ri.MissingInput) as e:
        raw.frame("MU", "quarterly_balance_sheet")
    assert e.value.path == "inputs.MU.quarterly_balance_sheet" and e.value.code == "missing_input"
    with pytest.raises(ri.MissingInput):
        raw.get("TSM", "info")


@pytest.mark.parametrize("bad", [
    {"source": "google"},
    {"status": "partial"},
    {"kind": "csv"},
    {"fetched_at": "2026-10-20 14:05 KST"},
    {"fetched_at": "2026-10-20T05:05:12+00:00"},
    {"status": "error", "kind": None, "data": None, "error": None},
    {"status": "ok", "data": None},
    {"status": "empty", "kind": None, "data": {"x": 1}},
    {"kind": "frame", "data": {"index": {}}},
])
def test_invalid_items_rejected(bad):
    with pytest.raises(ri.InvalidInput) as e:
        ri.RawInputs({"MU": {"info": item(**bad)}})
    assert "inputs.MU.info" in str(e.value) and e.value.code == "invalid_input"


@pytest.mark.parametrize("snap", [
    snapshot({"MU": {"info": item()}}, version=None),
    snapshot({"MU": {"info": item()}}, version=1),
    {"meta": {"format_version": 2}, "values": {}},
    {"meta": {}, "values": {}, "series": {}, "warnings": []},
])
def test_legacy_format(snap):
    with pytest.raises(ri.LegacyFormat) as e:
        ri.check_format(snap)
    assert e.value.code == "legacy_format"


def test_dumps_loads_round_trip():
    hist = price_history("Asia/Seoul", "2026-01-01", 10)
    inputs = {"000660.KS": {"history": item(kind="frame", data=ri.encode_frame(hist)), "info": item()}}
    meta = {"format_version": 2, "collected_at": T, "args": {"tickers": "000660.KS"}}
    snap = ri.loads(ri.dumps(meta, inputs))
    assert snap["meta"] == meta
    raw = ri.RawInputs(snap["inputs"])
    assert_same(hist, raw.frame("000660.KS", "history"))


def test_make_item_validates():
    it = ri.make_item("daum", T, "ok", "json", data=[{"date": "2026-10-20"}])
    assert it["status"] == "ok" and it["error"] is None
    with pytest.raises(ri.InvalidInput):
        ri.make_item("daum", T, "error", error=None)
