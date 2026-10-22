"""
Tests for Snapshot module (skills/financial-analyst/scripts/snapshot.py)
Covering requirements: FR-002, FR-003, FR-004, FR-006, FR-007, FR-008, FR-009
"""

import json
import os
import sys
import tempfile
import pytest

# Ensure scripts folder is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from snapshot import Snapshot, BASES, STATUSES


def _item(data, source, fetched_at="2026-10-14T10:00:00+09:00"):
    return {"source": source, "fetched_at": fetched_at, "status": "ok", "kind": "json", "data": data,
            "error": None, "note": None}


def _use_raw(monkeypatch, inputs):
    """Point the pipeline at synthetic raw inputs (spec 003: it reads nothing else)."""
    import get_financial_stats as gfs
    import raw_inputs as ri
    monkeypatch.setitem(gfs.RUN, "raw", ri.RawInputs(inputs))


def test_vocab_whitelist():
    snap = Snapshot()
    # Valid bases
    for b in BASES:
        snap.record(f"test.{b}", 100, source="test", basis=b, status="final")

    # Invalid basis
    with pytest.raises(ValueError, match="Invalid basis 'invalid_basis'"):
        snap.record("test.bad", 100, source="test", basis="invalid_basis", status="final")

    # Valid statuses
    for s in STATUSES:
        kwargs = {}
        if s == 'corrected':
            kwargs = {"ki": "KI-001", "original": 50}
        snap.record(f"test.status.{s}", 100, source="test", basis="quote", status=s, **kwargs)

    # Invalid status
    with pytest.raises(ValueError, match="Invalid status 'invalid_status'"):
        snap.record("test.bad_status", 100, source="test", basis="quote", status="invalid_status")


def test_corrected_requires_ki_and_original():
    snap = Snapshot()

    # Missing ki
    with pytest.raises(ValueError, match="Field 'ki' is required"):
        snap.record("test.val", 100, source="test", basis="quote", status="corrected", original=50)

    # Missing original
    with pytest.raises(ValueError, match="Field 'original' is required"):
        snap.record("test.val", 100, source="test", basis="quote", status="corrected", ki="KI-002")

    # original=None (original was missing/null) is allowed
    snap.record("test.val_null", 100, source="test", basis="quote", status="corrected", ki="KI-002", original=None)
    assert snap.values["test.val_null"]["original"] is None
    assert snap.values["test.val_null"]["ki"] == "KI-002"


def test_series_limit():
    snap = Snapshot()
    # 300 daily entries
    data = {f"2026-01-{i:03d}": i * 10 for i in range(1, 301)}
    snap.series("005930.KS.close", data, source="yahoo", basis="yahoo_close", limit=260)

    res = snap.series_data["005930.KS.close"]
    assert res["source"] == "yahoo"
    assert res["basis"] == "yahoo_close"
    assert len(res["data"]) == 260
    # Last entry should be preserved
    assert "2026-01-300" in res["data"]
    # First 40 entries should be pruned
    assert "2026-01-001" not in res["data"]
    assert "2026-01-041" in res["data"]


def test_warning_parsing():
    snap = Snapshot()
    snap.warning("[KI-006] 000660.KS: Yahoo 종가가 거래소 종가와 다름")
    snap.warning("[Warn] [KI-001] SK hynix: 수급 표 종가 차이")
    snap.warning("일반 경고 메시지입니다.")

    assert len(snap.warnings) == 3
    assert snap.warnings[0]["ki"] == "KI-006"
    assert snap.warnings[0]["msg"].startswith("[KI-006]")
    assert snap.warnings[1]["ki"] == "KI-001"
    assert snap.warnings[1]["msg"].startswith("[KI-001]")
    assert snap.warnings[2]["ki"] is None
    assert snap.warnings[2]["msg"] == "일반 경고 메시지입니다."


def test_dump_and_io_error():
    snap = Snapshot()
    snap.record("005930.KS.quote.current_price", 237500, source="yahoo", basis="quote", as_of="2026-10-14")
    snap.warning("[KI-001] Test warn")

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "test_report_data.json")
        meta = {"generated_at": "2026-10-14 11:31 KST"}
        snap.dump(json_path, meta=meta)

        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["meta"]["generated_at"] == "2026-10-14 11:31 KST"
        assert loaded["values"]["005930.KS.quote.current_price"]["value"] == 237500
        assert len(loaded["warnings"]) == 1

    # Test error when writing to invalid path
    with pytest.raises(Exception):
        snap.dump("/non_existent_drive/invalid_path/data.json", meta={})


def test_collect_meta():
    from collect import collect_meta
    meta = collect_meta({"tickers": "005930.KS", "cyclical": ""})
    assert "generated_at" in meta
    assert "args" in meta
    assert meta["args"]["tickers"] == "005930.KS"
    assert "versions" in meta
    assert "yfinance" in meta["versions"]
    assert "pandas" in meta["versions"]
    assert "python" in meta["versions"]
    assert "numpy" in meta["versions"]
    # The tests run inside the skills git repository, so the commit must be known (spec 003 R15).
    assert isinstance(meta["repo_commit"], str) and len(meta["repo_commit"]) >= 7, meta.get("repo_commit_error")
    assert meta["repo_commit_error"] is None


def test_collect_meta_records_git_failure(monkeypatch):
    import subprocess
    from collect import collect_meta

    def boom(*args, **kwargs):
        raise FileNotFoundError("git not found")
    monkeypatch.setattr(subprocess, "run", boom)
    meta = collect_meta({})
    assert meta["repo_commit"] is None
    assert "git not found" in meta["repo_commit_error"]


@pytest.mark.network
def test_snapshot_coverage():
    import get_financial_stats
    from get_financial_stats import generate_report, SNAP

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "coverage_test_data.json")
        # Run report generation with snapshot enabled for 005930.KS
        report = generate_report(
            ["005930.KS"],
            cyclical_add=set(),
            cyclical_remove=set(),
            benchmarks=None,
            snapshot_path=json_path,
            raw_args={"tickers": "005930.KS"},
        )

        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            snap_data = json.load(f)

        values = snap_data.get("values", {})
        series = snap_data.get("series", {})

        # 1. Quote & Market cap
        assert "005930.KS.quote.current_price" in values
        assert "005930.KS.quote.fifty_two_week_high" in values
        assert "005930.KS.quote.fifty_two_week_low" in values

        # 2. Key Valuation & Financial Metrics
        assert "005930.KS.metrics.trailing_pe" in values
        assert "005930.KS.metrics.forward_pe" in values
        assert "005930.KS.metrics.trailing_eps" in values
        assert "005930.KS.metrics.forward_eps" in values
        assert "005930.KS.metrics.price_to_book" in values
        assert "005930.KS.metrics.roe" in values
        assert "005930.KS.metrics.debt_to_equity" in values

        # 3. Technical indicators
        assert "005930.KS.technical.rsi_14" in values
        assert "005930.KS.technical.sma_20" in values
        assert "005930.KS.technical.bollinger_lower" in values

        # 4. Market context
        assert "005930.KS.market_context.drawdown_52w" in values

        # 4-1. Investor flows (summary row and ownership column shown in Section 4 table 1-1)
        assert "005930.KS.flows.total_5d.foreign_net_amt" in values
        assert any(k.endswith(".foreign_hold_ratio") for k in values if k.startswith("005930.KS.flows."))

        # 5. Cycle & PB band
        assert "005930.KS.cycle.opm_ttm" in values
        assert "005930.KS.pb_band.low" in values
        assert "005930.KS.pb_band.current_pb" in values

        # 6. Scenario calculations
        assert "005930.KS.scenario.multiple_a" in values
        assert "005930.KS.scenario.bear.target_price_a" in values
        assert "005930.KS.scenario.base.target_price_a" in values
        assert "005930.KS.scenario.bull.target_price_a" in values
        assert "005930.KS.scenario.expected_price_a" in values

        # 7. Price history series (260 limit)
        assert "005930.KS.close" in series
        assert len(series["005930.KS.close"]["data"]) <= 260


def test_adr_correction_recorded():
    import get_financial_stats
    from get_financial_stats import sanitize_metrics, SNAP

    test_info = {
        'currency': 'USD',
        'financialCurrency': 'TWD',
        'trailingPE': 30.0,
        'returnOnEquity': 0.40,
        'priceToBook': 91.75,  # Distorted P/B
        'profitMargins': 0.45,
        'priceToSalesTrailing12Months': 0.52,  # Distorted P/S
    }

    sanitize_metrics(test_info, "TSM_TEST")

    # Check P/B correction record
    pb_rec = SNAP.values.get("TSM_TEST.metrics.price_to_book")
    assert pb_rec is not None
    assert pb_rec["status"] == "corrected"
    assert pb_rec["ki"] == "KI-008"
    assert pb_rec["original"] == 91.75
    assert abs(pb_rec["value"] - 12.0) < 0.01

    # Check P/S correction record
    ps_rec = SNAP.values.get("TSM_TEST.metrics.price_to_sales")
    assert ps_rec is not None
    assert ps_rec["status"] == "corrected"
    assert ps_rec["ki"] == "KI-008"
    assert ps_rec["original"] == 0.52
    assert abs(ps_rec["value"] - 13.5) < 0.01


def test_history_reconciliation_recorded(monkeypatch):
    import pandas as pd
    from get_financial_stats import check_krx_history, HISTORY, SNAP

    # Setup synthetic history with 1 missing day and 1 different price
    dates = pd.date_range("2026-10-01", "2026-10-05", freq="D")
    yahoo_hist = pd.DataFrame({
        'Close': [1000.0, 1050.0, 1020.0, 1040.0],
        'Volume': [100, 100, 100, 100]
    }, index=dates[:4])

    # Reference (Daum) has 5 dates (day 5 is missing in Yahoo) and day 2 has different close (1060 vs 1050)
    ref_df = pd.DataFrame({
        'Close': [1000.0, 1060.0, 1020.0, 1040.0, 1080.0],
        'Volume': [100, 100, 100, 100, 100]
    }, index=dates)

    sym = "009999.KS"
    HISTORY[sym] = yahoo_hist
    info = {}

    # The Daum rows come from the run's raw inputs (spec 003), as stored by collect.py
    rows = [{"date": f"{d:%Y-%m-%d} 00:00:00", "tradePrice": c, "accTradeVolume": v}
            for d, c, v in zip(ref_df.index, ref_df['Close'], ref_df['Volume'])]
    _use_raw(monkeypatch, {sym: {"daum_days": _item(rows, "daum")}})
    check_krx_history(sym, info)

    # Day 2 should be replaced (KI-006)
    d2_str = f"{dates[1]:%Y-%m-%d}"
    d2_rec = SNAP.values.get(f"{sym}.history.{d2_str}.close")
    assert d2_rec is not None
    assert d2_rec["status"] == "corrected"
    assert d2_rec["ki"] == "KI-006"
    assert d2_rec["value"] == 1060.0
    assert d2_rec["original"] == 1050.0

    # Day 5 should be filled (KI-002)
    d5_str = f"{dates[4]:%Y-%m-%d}"
    d5_rec = SNAP.values.get(f"{sym}.history.{d5_str}.close")
    assert d5_rec is not None
    assert d5_rec["status"] == "corrected"
    assert d5_rec["ki"] == "KI-002"
    assert d5_rec["value"] == 1080.0
    assert d5_rec["original"] is None


@pytest.mark.network
def test_warnings_and_meta_match_report_section8():
    from get_financial_stats import generate_report
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "section8_test_data.json")
        report = generate_report(
            ["005930.KS"],
            cyclical_add=set(),
            cyclical_remove=set(),
            benchmarks=None,
            snapshot_path=json_path,
            raw_args={"tickers": "005930.KS"},
        )

        with open(json_path, "r", encoding="utf-8") as f:
            snap_data = json.load(f)

        # Meta fields check
        meta = snap_data.get("meta", {})
        assert meta.get("generated_at")
        assert "yfinance" in meta.get("versions", {})
        assert "pandas" in meta.get("versions", {})
        assert "tickers" in meta.get("args", {})

        # Warnings matching check
        warnings_in_snap = [w["msg"] for w in snap_data.get("warnings", [])]
        # Unique warning list in order of appearance (same as warnings_section)
        unique_warns_in_snap = list(dict.fromkeys(warnings_in_snap))

        # Parse Section 8 bullets from report
        lines = report.splitlines()
        section8_idx = -1
        for idx, line in enumerate(lines):
            if "### 8. ⚠️ 데이터 품질 경고" in line:
                section8_idx = idx
                break

        assert section8_idx != -1
        section8_bullets = [
            line[2:].strip() for line in lines[section8_idx:]
            if line.startswith("- ")
        ]

        # Each bullet in Section 8 must correspond to unique warnings in snapshot
        assert section8_bullets == unique_warns_in_snap


def test_flow_table_totals_and_ratio_recorded(monkeypatch):
    """수급 표의 '최근 5일 누적(추정)' 행과 외국인 지분율 칸도 스냅샷에 있어야 한다 (SC-002)."""
    from get_financial_stats import fetch_investor_trends_table, SNAP

    days = ["20261007", "20261008", "20261009", "20261012", "20261013"]
    naver_rows = [
        {"bizdate": d, "closePrice": "100,000", "accumulatedTradingVolume": "1,000",
         "foreignerPureBuyQuant": f"-{i + 1}00,000", "organPureBuyQuant": "+50,000",
         "individualPureBuyQuant": "+10,000", "foreignerHoldRatio": f"46.{i}0%"}
        for i, d in enumerate(reversed(days))
    ]

    sym = "009998.KS"
    # Received on a weekday without its own Naver row, so the Daum quote is read: not today's trade → no intraday row
    _use_raw(monkeypatch, {sym: {
        "naver_trend": _item(naver_rows, "naver", "2026-10-14T10:00:00+09:00"),
        "daum_quote": _item({"date": "20000101"}, "daum", "2026-10-14T10:00:01+09:00"),
        "daum_investor_days": {"source": "daum", "fetched_at": "2026-10-14T10:00:01+09:00", "status": "skipped",
                               "kind": None, "data": None, "error": None, "note": None},
    }})
    table = fetch_investor_trends_table("009998", "테스트", {"symbol": sym})

    # 표에 보인 누적 금액(억 원)과 스냅샷 값이 같아야 한다
    frgn = SNAP.values[f"{sym}.flows.total_5d.foreign_net_amt"]
    organ = SNAP.values[f"{sym}.flows.total_5d.organ_net_amt"]
    indiv = SNAP.values[f"{sym}.flows.total_5d.individual_net_amt"]
    assert frgn["value"] == pytest.approx(-(1 + 2 + 3 + 4 + 5) * 1e5 * 1e5 / 1e8)
    assert organ["value"] == pytest.approx(5 * 5e4 * 1e5 / 1e8)
    assert indiv["value"] == pytest.approx(5 * 1e4 * 1e5 / 1e8)
    assert f"**{frgn['value']:+,.0f}억 원**" in table
    for rec in (frgn, organ, indiv):
        assert rec["basis"] == "derived"
        assert rec["status"] == "estimated"
        assert len(rec["inputs"]) == 5
    assert frgn["inputs"][0].startswith(f"{sym}.flows.")

    # 외국인 지분율 칸: 비율은 다른 비율 값처럼 소수로 저장
    ratio = SNAP.values[f"{sym}.flows.2026-10-13.foreign_hold_ratio"]
    assert ratio["value"] == pytest.approx(0.46)
    assert ratio["source"] == "naver"
    assert "46.00%" in table


def test_attach_section4(tmp_path):
    """002 T014/T015: the Section 4 baseline is stored in the snapshot after the report is assembled."""
    import hashlib
    from snapshot import attach_section4

    path = tmp_path / "r_data.json"
    path.write_text(json.dumps({"meta": {}, "values": {"a": {"value": 1}}, "series": {}, "warnings": []}), encoding="utf-8")
    text = "### 1. 주요 주가\n\n| A | ₩237,500 |"
    attach_section4(str(path), text)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["section4"]["text"] == text
    assert data["section4"]["sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert data["section4"]["attached_at"].endswith("KST")
    assert data["values"]["a"]["value"] == 1                       # the rest of the snapshot is untouched

    with pytest.raises(Exception):
        attach_section4(str(tmp_path / "missing_data.json"), text)


def test_dump_format2_with_inputs(tmp_path):
    """Spec 003: a snapshot carrying raw inputs is format 2; values/series/warnings keep their shape."""
    snap = Snapshot()
    snap.record("MU.quote.current_price", 100.0, source="yahoo", basis="quote")
    inputs = {"MU": {"info": {"source": "yahoo", "fetched_at": "2026-10-20T14:05:12+09:00", "status": "ok",
                              "kind": "json", "data": {"symbol": "MU"}, "error": None, "note": None}}}
    path = tmp_path / "x_data.json"
    snap.dump(str(path), meta={"collected_at": "2026-10-20T14:05:12+09:00"}, inputs=inputs)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert list(loaded) == ["meta", "inputs", "values", "series", "warnings"]
    assert loaded["meta"]["format_version"] == 2
    assert loaded["inputs"] == inputs
    assert loaded["values"]["MU.quote.current_price"]["value"] == 100.0
    # Without inputs the shape stays format 1 (callers that only record values)
    assert "inputs" not in snap.to_dict(meta={}) and "format_version" not in snap.to_dict(meta={})["meta"]


def test_section4_body_matches_report_generator():
    from snapshot import section4_body, FINANCIAL_HEADER
    out = f"\n{FINANCIAL_HEADER}\n\n> 🕒 기준\n| a |\n\n"
    assert section4_body(out) == "> 🕒 기준\n| a |"
    assert section4_body("  > 머리 없음\n") == "> 머리 없음"


# --- KI-009: KRX closed, NXT after-market trading until 20:00 ---

def _nxt_flow_inputs(sym, fetched_at, daum_status, trade_time="190100", trade_price=1199000.0, krx_close=1223000.0):
    """Naver has no row for the run day yet, so the Daum quote estimates it (as in tests/fixtures/003)."""
    naver_rows = [{"bizdate": d, "closePrice": "1,000,000", "accumulatedTradingVolume": "1,000",
                   "foreignerPureBuyQuant": "-1,000", "organPureBuyQuant": "+500", "individualPureBuyQuant": "+500",
                   "foreignerHoldRatio": "48.81%"} for d in ("20261019", "20261016", "20261015", "20261014", "20261013")]
    quote = {"date": "2026-10-20", "tradeDate": "20261020", "tradeTime": trade_time, "tradePrice": trade_price,
             "regularTradePrice": krx_close, "foreignOwnShares": 356585226, "foreignRatio": 0.4881436728}
    if daum_status is not None:
        quote["marketStatus"] = daum_status
    days = {"data": [{"date": "2026-10-19 00:00:00", "foreignOwnShares": 356621525, "tradePrice": 1304000.0}]}
    return {sym: {"naver_trend": _item(naver_rows, "naver", fetched_at),
                  "daum_quote": _item(quote, "daum", fetched_at),
                  "daum_investor_days": _item(days, "daum", fetched_at)}}


def _flow_table(monkeypatch, inputs, sym, info=None):
    import get_financial_stats as gfs
    _use_raw(monkeypatch, inputs)
    monkeypatch.setattr(gfs, "WARNINGS", [])
    monkeypatch.setattr(gfs, "SNAP", Snapshot())
    table = gfs.fetch_investor_trends_table(sym.split(".")[0], "테스트", info or {"symbol": sym})
    return table, gfs.WARNINGS, gfs.SNAP


def test_flow_row_after_krx_close_uses_nxt_label(monkeypatch):
    """19:01 Daum quote in AFTER_MARKET: the price is the NXT trade, not the KRX close — label and warn (KI-009)."""
    sym = "009991.KS"
    table, warns, snap = _flow_table(monkeypatch, _nxt_flow_inputs(sym, "2026-10-20T19:02:29+09:00", "AFTER_MARKET"), sym)
    assert "| **2026-10-20 (NXT 시간외 잠정)** | ₩1,199,000 |" in table
    assert "장중 잠정" not in table
    assert "NXT 시간외 체결가(19:01 현재)이며 KRX 정규장 종가는 ₩1,223,000입니다(KI-009)" in table
    ki009 = [w for w in warns if w.startswith("[KI-009]")]
    assert len(ki009) == 1 and "₩1,199,000" in ki009[0] and "₩1,223,000" in ki009[0]
    price = snap.values[f"{sym}.flows.2026-10-20.price"]
    assert price["status"] == "provisional" and price["basis"] == "flow_feed_price"
    assert price["note"] == "NXT 시간외 체결가(19:01 현재)"
    krx = snap.values[f"{sym}.flows.2026-10-20.krx_close"]
    assert krx["value"] == 1223000.0 and krx["basis"] == "krx_regular_close" and krx["ki"] == "KI-009"
    # The amount is unchanged by the label: ownership change x the quote price
    amt = snap.values[f"{sym}.flows.2026-10-20.foreign_net_amt"]["value"]
    assert amt == pytest.approx((356585226 - 356621525) * 1199000.0 / 1e8)


def test_flow_row_after_nxt_close_is_closing(monkeypatch):
    """After 20:00 Daum reports CLOSING with the NXT last trade (19:59) while Naver still has no row."""
    sym = "009992.KS"
    inputs = _nxt_flow_inputs(sym, "2026-10-20T20:03:36+09:00", "CLOSING", trade_time="195900", trade_price=1190000.0)
    table, warns, _ = _flow_table(monkeypatch, inputs, sym)
    assert "| **2026-10-20 (마감 후 잠정)** | ₩1,190,000 |" in table
    assert "NXT 시간외 최종 체결가(19:59)" in table
    assert any(w.startswith("[KI-009]") and "마감 후 잠정치" in w for w in warns)


@pytest.mark.parametrize("status", [None, "REGULAR_HOURS"])
def test_flow_row_during_session_stays_intraday(monkeypatch, status):
    """Without an after-market status the existing intraday label stays and no KI-009 warning is raised."""
    sym = "009993.KS"
    inputs = _nxt_flow_inputs(sym, "2026-10-20T11:00:00+09:00", status, trade_time="105900", trade_price=1210000.0)
    table, warns, snap = _flow_table(monkeypatch, inputs, sym)
    assert "| **2026-10-20 (장중 잠정)** | ₩1,210,000 |" in table
    assert not [w for w in warns if "KI-009" in w]
    assert f"{sym}.flows.2026-10-20.krx_close" not in snap.values
    assert snap.values[f"{sym}.flows.2026-10-20.price"].get("note") is None


def _naver_today_inputs(sym, fetched_at, close="1,223,000", volume="3,639,928"):
    rows = [{"bizdate": d, "closePrice": close if d == "20261020" else "1,000,000",
             "accumulatedTradingVolume": volume if d == "20261020" else "1,000",
             "foreignerPureBuyQuant": "-1,000", "organPureBuyQuant": "+500", "individualPureBuyQuant": "+500",
             "foreignerHoldRatio": "48.81%"} for d in ("20261020", "20261019", "20261016", "20261015", "20261014")]
    skipped = {"source": "daum", "fetched_at": fetched_at, "status": "skipped", "kind": None, "data": None, "error": None, "note": None}
    return {sym: {"naver_trend": _item(rows, "naver", fetched_at), "daum_quote": skipped, "daum_investor_days": skipped}}


@pytest.mark.parametrize("fetched_at, expect", [
    ("2026-10-20T15:35:00+09:00", "장 마감(15:30) 전 실행"),
    ("2026-10-20T17:00:00+09:00", "NXT 시간외 거래(20:00 마감) 중 실행(KI-009)"),
    ("2026-10-20T20:05:00+09:00", "NXT 시간외 거래(20:00 마감) 중 실행(KI-009)"),
    ("2026-10-20T20:10:00+09:00", None),
])
def test_naver_same_day_row_final_only_after_nxt_close(monkeypatch, fetched_at, expect):
    """A Naver row for the run day read before 20:10 (NXT close + 10 min) is provisional (KI-009); the clock is fetched_at."""
    sym = "009994.KS"
    info = {"symbol": sym, "regularMarketPrice": 1223000.0, "regularMarketVolume": 3639928}
    table, warns, snap = _flow_table(monkeypatch, _naver_today_inputs(sym, fetched_at), sym, info)
    status = snap.values[f"{sym}.flows.2026-10-20.foreign_net_shares"]["status"]
    if expect is None:
        assert "**2026-10-20 (마감 후 집계)**" in table and status == "final" and not warns
    else:
        assert "**2026-10-20 (잠정)**" in table and expect in table and status == "provisional"
        assert len(warns) == 1 and (warns[0].startswith("[KI-009]") == ("KI-009" in expect))
    if expect and "KI-009" in expect:
        assert "잠정치(NXT 시간외 거래 중 스냅샷)" in table


def test_data_basis_line_marks_nxt_window(monkeypatch):
    """Data-basis line: KR tickers read between 15:30 and 20:00 on a KRX trading day say KRX close + NXT until 20:00."""
    import datetime as dt
    import get_financial_stats as gfs
    kst = dt.timezone(dt.timedelta(hours=9))
    krx_close_ts = dt.datetime(2026, 10, 20, 15, 30, 13, tzinfo=kst).timestamp()

    def info(fetched, ts=krx_close_ts, state="POSTPOST"):
        return {"marketState": state, "regularMarketTime": ts, "exchangeDataDelayedBy": 20,
                "_fetched_at": dt.datetime.fromisoformat(fetched)}

    monkeypatch.setitem(gfs.RUN, "collected_at", dt.datetime(2026, 10, 20, 19, 2, 37, tzinfo=kst))
    line = gfs.data_basis_block({"000660.KS": info("2026-10-20T19:02:27+09:00"),
                                 "MU": info("2026-10-20T19:02:30+09:00", ts=dt.datetime(2026, 10, 20, 5, 0, tzinfo=kst).timestamp(),
                                            state="PRE")})
    assert "000660.KS KRX 장 마감(최종 체결 10-20 15:30 KST, 20분 지연, NXT 시간외 거래는 20:00까지)" in line
    assert "MU 프리마켓(최종 체결 10-20 05:00 KST, 20분 지연)" in line
    assert "수급 당일 행은 잠정치입니다(KI-009)" in line

    after = gfs.data_basis_block({"000660.KS": info("2026-10-20T20:03:36+09:00")})
    holiday = gfs.data_basis_block({"000660.KS": info("2026-10-21T17:00:00+09:00")})   # no KRX trade that day
    for text in (after, holiday):
        assert "000660.KS 장 마감(최종 체결 10-20 15:30 KST, 20분 지연)" in text and "KI-009" not in text


def test_naver_row_after_nxt_close_is_final_despite_krx_basis(monkeypatch):
    """20:20 on 2026-10-20: Naver's row carries the NXT last trade (₩1,190,000), Yahoo the KRX close (₩1,223,000).

    The gap is the price basis (KI-001 cause), not an unfinished row, so the row is final after 20:10 (KI-009).
    Before 20:10 the same gap is listed as one more provisional reason.
    """
    sym = "009995.KS"
    info = {"symbol": sym, "regularMarketPrice": 1223000.0, "regularMarketVolume": 3639928}
    inputs = _naver_today_inputs(sym, "2026-10-20T20:20:41+09:00", close="1,190,000", volume="3,464,412")
    table, warns, snap = _flow_table(monkeypatch, inputs, sym, info)
    assert "| **2026-10-20 (마감 후 집계)** | ₩1,190,000 |" in table
    assert "NXT 시간외 거래(20:00 마감)까지 포함한 마감 후 집계" in table
    assert snap.values[f"{sym}.flows.2026-10-20.foreign_net_shares"]["status"] == "final" and not warns

    inputs = _naver_today_inputs(sym, "2026-10-20T19:30:00+09:00", close="1,190,000", volume="3,464,412")
    table, warns, _ = _flow_table(monkeypatch, inputs, sym, info)
    assert "**2026-10-20 (잠정)**" in table
    assert "행 종가 ₩1,190,000 ≠ KRX 종가 ₩1,223,000(NXT 체결 포함 기준 차이일 수 있음, KI-001)" in table
    assert "행 거래량 3,464,412주 ≠ 실제 3,639,928주" in table
    assert len(warns) == 1 and warns[0].startswith("[KI-009]")
