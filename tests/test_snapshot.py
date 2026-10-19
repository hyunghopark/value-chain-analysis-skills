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
    from get_financial_stats import collect_meta
    meta = collect_meta({"tickers": "005930.KS", "cyclical": ""})
    assert "generated_at" in meta
    assert "args" in meta
    assert meta["args"]["tickers"] == "005930.KS"
    assert "versions" in meta
    assert "yfinance" in meta["versions"]
    assert "pandas" in meta["versions"]
    # In git repo, commit should be string
    if meta["repo_commit"] is not None:
        assert isinstance(meta["repo_commit"], str)


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


def test_history_reconciliation_recorded():
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
    info = {'_krx_daily': ref_df}

    import data_checks
    # Patch data_checks.fetch_daum_days to return ref_df
    orig_fetch = data_checks.fetch_daum_days
    data_checks.fetch_daum_days = lambda code: ref_df
    try:
        check_krx_history(sym, info)
    finally:
        data_checks.fetch_daum_days = orig_fetch

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
    import requests
    from get_financial_stats import fetch_investor_trends_table, SNAP

    days = ["20261007", "20261008", "20261009", "20261012", "20261013"]
    naver_rows = [
        {"bizdate": d, "closePrice": "100,000", "accumulatedTradingVolume": "1,000",
         "foreignerPureBuyQuant": f"-{i + 1}00,000", "organPureBuyQuant": "+50,000",
         "individualPureBuyQuant": "+10,000", "foreignerHoldRatio": f"46.{i}0%"}
        for i, d in enumerate(reversed(days))
    ]

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def json(self):
            return self.payload

    def fake_get(url, **kwargs):
        if "m.stock.naver.com" in url:
            return FakeResponse(naver_rows)
        return FakeResponse({"date": "20000101"})  # 다음 금융: 당일 거래 아님 → 장중 추정 행 없음

    monkeypatch.setattr(requests, "get", fake_get)
    sym = "009998.KS"
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
