"""
Comprehensive test suite for market-analyst skill:
Verifies metric calculations, crisis support evaluations, sector rotation,
macro risk indicators, Market Regime decision matrix, Socratic cognitive bias auditor,
invalidation ladder, snapshot serialization, and report number verification.
All tests run locally with 0 external network dependencies.
"""

import hashlib
import json
import os
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure scripts directory is in sys.path
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(TESTS_DIR), "skills", "market-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import market_metrics as mm
import market_regime as mr
import socratic_auditor as sa
import target_resolver as tr
from market_snapshot import MarketSnapshot, attach_section4, section4_body
import check_market_report_numbers as cmn


def make_sample_df(start_date="2024-01-01", periods=600, base_price=5000.0, trend=0.5):
    """Generate deterministic daily OHLCV series for testing."""
    dates = pd.date_range(start=start_date, periods=periods, freq="B")
    prices = [base_price + i * trend for i in range(periods)]
    df = pd.DataFrame(
        {
            "Open": [p - 5.0 for p in prices],
            "High": [p + 10.0 for p in prices],
            "Low": [p - 10.0 for p in prices],
            "Close": prices,
            "Volume": [1000000 + i * 100 for i in range(periods)],
        },
        index=dates,
    )
    return df


def test_index_metrics_calculation():
    """Test 1D, 5D, 1M, 52W High/Low, MDD, 20 EMA, 50 SMA, 200 SMA and distance."""
    df = make_sample_df(periods=300, base_price=5000.0, trend=2.0)
    met = mm.compute_index_metrics(df, ticker="^GSPC")

    assert met["status"] == "ok"
    assert met["ticker"] == "^GSPC"
    assert met["name"] == "S&P 500"
    assert met["current_close"] == round(float(df["Close"].iloc[-1]), 2)
    assert met["ret_1d"] is not None
    assert met["ret_5d"] is not None
    assert met["ret_1m"] is not None
    assert met["52w_high"] is not None
    assert met["52w_low"] is not None
    assert met["drawdown_52w"] is not None
    assert met["sma_50"] is not None
    assert met["sma_200"] is not None
    assert met["dist_200"] is not None
    # With positive trend, current close > 200 SMA
    assert met["dist_200"] > 0


def test_crisis_benchmarks_breached_and_held():
    """Test crisis support level detection for breached vs holding states."""
    df = make_sample_df(start_date="2024-01-01", periods=600, base_price=5000.0, trend=1.0)

    # Set specific crisis dates in the dataframe
    yen_dt = pd.to_datetime("2024-08-05")
    iran_dt = pd.to_datetime("2024-04-19")

    if yen_dt in df.index:
        df.loc[yen_dt, "Low"] = 5100.0
    if iran_dt in df.index:
        df.loc[iran_dt, "Low"] = 4900.0

    # Case 1: Current price is well above crisis lows (Holding)
    evals_high = mm.evaluate_crisis_benchmarks(df, current_close=5500.0)
    assert len(evals_high) >= 2
    yen_eval = next((e for e in evals_high if "yen" in e["id"]), None)
    assert yen_eval is not None
    assert yen_eval["breached"] is False
    assert yen_eval["buffer_pct"] > 0

    # Case 2: Current price crashes below crisis lows (Breached)
    evals_low = mm.evaluate_crisis_benchmarks(df, current_close=4500.0)
    yen_breached = next((e for e in evals_low if "yen" in e["id"]), None)
    assert yen_breached is not None
    assert yen_breached["breached"] is True
    assert yen_breached["buffer_pct"] < 0


def test_sector_rotation_and_relative_strength():
    """Test 11 sector RS vs SPY and Cyclical vs Defensive spread."""
    spy_df = make_sample_df(periods=50, base_price=500.0, trend=1.0)

    # Build sectors with varying trends
    sector_dfs = {}
    # Cyclicals strongly outperform SPY
    for sym in mm.CYCLICAL_SECTORS:
        sector_dfs[sym] = make_sample_df(periods=50, base_price=100.0, trend=1.5)
    # Defensives underperform SPY
    for sym in mm.DEFENSIVE_SECTORS:
        sector_dfs[sym] = make_sample_df(periods=50, base_price=100.0, trend=0.2)
    # Commodities
    for sym in mm.COMMODITY_SECTORS:
        sector_dfs[sym] = make_sample_df(periods=50, base_price=100.0, trend=0.5)

    rot = mm.compute_sector_rotation(sector_dfs, spy_df=spy_df)
    assert "sectors" in rot
    assert len(rot["sectors"]) == 11
    assert rot["spread_5d"] > 0
    assert "Risk-On" in rot["regime_desc"] or "순환매" in rot["regime_desc"]


def test_macro_risk_indicators():
    """Test VIX thresholds, 10Y Yield changes, yield curve, and HYG/LQD credit ratio."""
    # VIX: test levels
    vix_df = make_sample_df(periods=10, base_price=28.0, trend=0.5)
    tnx_df = make_sample_df(periods=10, base_price=4.5, trend=0.05)
    irx_df = make_sample_df(periods=10, base_price=4.0, trend=0.01)
    hyg_df = make_sample_df(periods=10, base_price=75.0, trend=0.1)
    lqd_df = make_sample_df(periods=10, base_price=105.0, trend=0.1)

    macro_dfs = {
        "^VIX": vix_df,
        "^TNX": tnx_df,
        "^IRX": irx_df,
        "HYG": hyg_df,
        "LQD": lqd_df,
    }
    risk = mm.compute_macro_risk(macro_dfs)

    assert risk["vix"]["level"] > 25.0
    assert risk["vix"]["signal"] == "🔴"
    assert risk["rate_10y"]["yield"] is not None
    assert risk["yield_curve"]["spread_10y_13w"] is not None
    assert risk["credit"]["hyg_lqd_ratio"] is not None
    assert risk["credit"]["signal"] in ("🟢", "🟡", "🔴")


def test_market_regime_matrix_all_regimes():
    """Verify evaluation of all 6 institutional market regimes."""
    # 1. Structural Bear Market: trend 🔴, credit 🔴
    r_bear = mr.evaluate_market_regime(
        trend_eval={"signal": "🔴", "dist_200": -6.0},
        macro_risk={"vix": {"signal": "🟡", "level": 23.0}, "credit": {"signal": "🔴"}},
        sector_rotation={"signal": "🔴", "spread_5d": -3.0},
    )
    assert r_bear["code"] == "structural_bear"
    assert r_bear["cash_pct"] >= 60

    # 2. Liquidity Shock / Panic Dip: VIX 🔴 (>= 28) and trend 🔴
    r_panic = mr.evaluate_market_regime(
        trend_eval={"signal": "🔴", "dist_200": -2.0},
        macro_risk={"vix": {"signal": "🔴", "level": 32.0}, "credit": {"signal": "🟡"}},
        sector_rotation={"signal": "🔴", "spread_5d": -2.5},
    )
    assert r_panic["code"] == "liquidity_shock"
    assert r_panic["cash_pct"] == 45

    # 3. Stagflation / Supply Shock: rate 🔴, oil spike > 4%, trend 🟡
    r_stag = mr.evaluate_market_regime(
        trend_eval={"signal": "🟡", "dist_200": 1.0},
        macro_risk={
            "rate_10y": {"signal": "🔴", "chg_5d_bps": 20.0},
            "crude_oil": {"chg_5d_pct": 6.5},
            "vix": {"signal": "🟡", "level": 22.0},
            "credit": {"signal": "🟡"},
        },
        sector_rotation={"signal": "🟡", "spread_5d": -1.0},
    )
    assert r_stag["code"] == "stagflation"
    assert r_stag["cash_pct"] >= 40

    # 4. Healthy Correction: trend 🟡, vix 🟡, credit 🟢
    r_corr = mr.evaluate_market_regime(
        trend_eval={"signal": "🟡", "dist_200": 3.0},
        macro_risk={"vix": {"signal": "🟡", "level": 21.0}, "credit": {"signal": "🟢"}},
        sector_rotation={"signal": "🟡", "spread_5d": -0.5},
    )
    assert r_corr["code"] == "correction"
    assert r_corr["cash_pct"] == 25

    # 5. Overheating: trend 🟢, breadth 🔴
    r_over = mr.evaluate_market_regime(
        trend_eval={"signal": "🟢", "dist_200": 8.0},
        macro_risk={"vix": {"signal": "🟢", "level": 14.0}, "credit": {"signal": "🟢"}},
        sector_rotation={"signal": "🔴", "spread_5d": -2.5},
    )
    assert r_over["code"] == "overheating"
    assert r_over["cash_pct"] == 30

    # 6. Bull Expansion: trend 🟢, vix 🟢, credit 🟢
    r_bull = mr.evaluate_market_regime(
        trend_eval={"signal": "🟢", "dist_200": 7.0},
        macro_risk={"vix": {"signal": "🟢", "level": 15.0}, "credit": {"signal": "🟢"}},
        sector_rotation={"signal": "🟢", "spread_5d": 1.5},
    )
    assert r_bull["code"] == "bull_expansion"
    assert r_bull["cash_pct"] == 10


def test_socratic_cognitive_biases_audit():
    """Verify detection of the 5 cognitive biases under triggered vs calm conditions."""
    # Condition: Severe drop, high VIX, rates spiked, 200 SMA broken
    sp500_bad = {"ret_5d": -4.5, "drawdown_52w": -12.0, "dist_200": -2.5}
    macro_bad = {
        "vix": {"level": 29.5},
        "rate_10y": {"chg_5d_bps": 18.0},
        "credit": {"credit_rs_5d": -1.8},
    }
    trend_bad = {"any_crisis_breached": True}

    biases = sa.audit_cognitive_biases(sp500_bad, macro_bad, trend_bad)
    assert len(biases) == 5

    # Recency, Anchoring, Confirmation, Loss Aversion, Action Bias should all trigger
    for b in biases:
        assert b["triggered"] is True
        assert b["evidence"] != ""
        assert b["prescription"] != ""

    # Condition: Calm bull market
    sp500_good = {"ret_5d": 1.2, "drawdown_52w": -1.0, "dist_200": 6.0}
    macro_good = {
        "vix": {"level": 14.0},
        "rate_10y": {"chg_5d_bps": 2.0},
        "credit": {"credit_rs_5d": 0.5},
    }
    trend_good = {"any_crisis_breached": False}

    calm_biases = sa.audit_cognitive_biases(sp500_good, macro_good, trend_good)
    for b in calm_biases:
        assert b["triggered"] is False


def test_socratic_invalidation_ladder_construction():
    """Test construction of Bull and Bear Invalidation Ladders with numeric targets."""
    sp500_m = {"current_close": 5500.0, "sma_200": 5200.0, "sma_50": 5600.0}
    macro_r = {"vix": {"level": 22.0}}
    crisis_e = [{"id": "iran_war_20240419", "name": "이란 저점", "crisis_low": 4950.0}]

    ladder = sa.build_thesis_invalidation_ladder(sp500_m, macro_r, crisis_e)
    assert "bull_invalidation_triggers" in ladder
    assert "bear_invalidation_triggers" in ladder
    assert len(ladder["bull_invalidation_triggers"]) >= 4
    assert len(ladder["bear_invalidation_triggers"]) >= 4

    # Verify numbers are rendered inside string
    bull_text = " ".join(ladder["bull_invalidation_triggers"])
    assert "5,200.0" in bull_text
    assert "4,950.0" in bull_text


def test_snapshot_lifecycle_and_section4_attach(tmp_path):
    """Test MarketSnapshot recording, saving, section4 extraction, and baseline hashing."""
    snap = MarketSnapshot()
    snap.record("^GSPC.quote.close", 5750.25, source="yahoo", basis="index_close")
    snap.record("macro.regime.verdict", "건전한 조정 국면", source="derived", basis="regime_matrix")
    snap.add_warning("TEST_WARN", "Test warning message")

    snap_file = tmp_path / "test_snapshot_data.json"
    snap.save(str(snap_file))

    with open(snap_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["meta"]["format_version"] == 2
    assert "^GSPC.quote.close" in data["values"]
    assert len(data["warnings"]) == 1

    # Test Section 4 attachment
    report_text = """# Header
## 1. Summary
Some content
## 4. 📊 정량 지표 데이터 분석 결과 (스크립트 자동 산출)
Table 1 content
Table 2 content
## 5. Sector Rotation
More content
"""
    sec_body = section4_body(report_text)
    assert "Table 1 content" in sec_body

    attached = attach_section4(report_text, str(snap_file))
    assert attached is True

    with open(snap_file, "r", encoding="utf-8") as f:
        data_after = json.load(f)

    assert "section4" in data_after
    assert "sha256" in data_after["section4"]
    expected_sha = hashlib.sha256(sec_body.encode("utf-8")).hexdigest()
    assert data_after["section4"]["sha256"] == expected_sha


def test_check_market_report_numbers(tmp_path):
    """Test report number checker for clean pass vs modified section 4 vs leftover TODO."""
    snap = MarketSnapshot()
    snap.record("^GSPC.quote.close", 5800.0, source="yahoo", basis="index_close")

    report_content = """# Title
## 1. Summary
현재 주가 5800.0 [1]
## 4. 📊 정량 지표 데이터 분석 결과 (스크립트 자동 산출)
| Index | Price |
|---|---|
| ^GSPC | 5800.0 |
## 5. End
"""
    report_file = tmp_path / "test_report.md"
    snap_file = tmp_path / "test_report_data.json"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    snap.save(str(snap_file))
    attach_section4(report_content, str(snap_file))

    # Should pass (exit code 0)
    code = cmn.verify_report(str(report_file))
    assert code == cmn.EXIT_OK

    # Tamper with Section 4 -> should fail (exit code 1)
    tampered_content = report_content.replace("| ^GSPC | 5800.0 |", "| ^GSPC | 5900.0 |")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(tampered_content)
    code_tampered = cmn.verify_report(str(report_file))
    assert code_tampered == cmn.EXIT_ISSUES

    # Introduce leftover AI_TODO -> should fail (exit code 1)
    todo_content = report_content + "\n[AI_TODO: uncompleted]"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(todo_content)
    code_todo = cmn.verify_report(str(report_file))
    assert code_todo == cmn.EXIT_ISSUES

    # Introduce leftover [수치] -> should fail (exit code 1)
    su_content = report_content + "\n* **금:** $[수치]"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(su_content)
    code_su = cmn.verify_report(str(report_file))
    assert code_su == cmn.EXIT_ISSUES


def test_crisis_benchmarks_tz_aware_and_multiindex_edge_cases():
    """Verify that evaluate_crisis_benchmarks handles tz-aware indexes, MultiIndex columns, and out-of-range dates."""
    # 1. Timezone-aware index
    tz_dates = pd.date_range("2024-01-01", periods=300, freq="B", tz="America/New_York")
    df_tz = pd.DataFrame(
        {"Close": [5000.0 + i for i in range(300)], "Low": [4990.0 + i for i in range(300)]},
        index=tz_dates,
    )
    # Should not raise TypeError: Cannot compare tz-naive and tz-aware
    evals_tz = mm.evaluate_crisis_benchmarks(df_tz, current_close=5500.0)
    assert len(evals_tz) >= 2

    # 2. DataFrame column (simulating yfinance MultiIndex without squeeze)
    cols = pd.MultiIndex.from_tuples([("Close", "^GSPC"), ("Low", "^GSPC")])
    df_multi = pd.DataFrame(
        [[5000.0, 4990.0], [5010.0, 4995.0]],
        columns=cols,
        index=pd.date_range("2024-04-18", periods=2, freq="B"),
    )
    evals_multi = mm.evaluate_crisis_benchmarks(df_multi, current_close=5200.0)
    iran_m = next((e for e in evals_multi if "iran_war_20240419" in e["id"]), None)
    assert iran_m is not None
    assert iran_m["crisis_low"] == 4990.0

    # 3. Out-of-range historical benchmark (df starts in 2025)
    df_future = pd.DataFrame(
        {"Close": [6000.0, 6010.0], "Low": [5990.0, 5995.0]},
        index=pd.date_range("2025-06-01", periods=2, freq="B"),
    )
    evals_future = mm.evaluate_crisis_benchmarks(df_future, current_close=6100.0)
    for e in evals_future:
        # Benchmark dates are in 2024; since df starts in 2025, they MUST be None (no bogus clamping)
        assert e["crisis_low"] is None
        assert e["breached"] is False
        assert e["buffer_pct"] is None


def test_rebuild_market_section4_offline(tmp_path):
    """Test rebuilding Section 4 completely offline from snapshot inputs alone."""
    import get_market_stats as gms
    import rebuild_market_section4 as rms
    import market_raw_inputs as ri

    # Create dummy raw items for target tickers
    raw_items = {}
    stamp_str = "2026-11-05T16:00:00"
    for sym in ["^GSPC", "^NDX", "^DJI", "^RUT", "^SOX", "SPY", "^VIX", "^TNX", "^IRX", "HYG", "LQD"]:
        df = make_sample_df(start_date="2024-01-01", periods=500, base_price=5000.0 if "^" in sym else 100.0)
        raw_items[sym] = ri.make_item("yahoo", stamp_str, "ok", kind="frame", data=df)

    for sym in mm.CYCLICAL_SECTORS + mm.DEFENSIVE_SECTORS + mm.COMMODITY_SECTORS:
        df = make_sample_df(start_date="2024-01-01", periods=500, base_price=100.0)
        raw_items[sym] = ri.make_item("yahoo", stamp_str, "ok", kind="frame", data=df)

    snap_file = tmp_path / "test_offline_market_data.json"

    # Run analysis using raw_inputs directly
    sec4_text, snap = gms.run_market_analysis(
        raw_inputs=raw_items,
        as_of_str="2026-11-05 16:00 KST",
        snapshot_path=str(snap_file),
    )

    attach_section4(sec4_text, str(snap_file), attached_at="2026-11-05 16:00 KST")

    # Rebuild from snapshot with zero network
    code, msg = rms.rebuild_from_snapshot(str(snap_file))
    assert code == rms.EXIT_SAME
    assert "Section 4 rebuild match verified" in msg

    # Tamper with snapshot value and verify detection
    with open(snap_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["values"]["^GSPC.quote.close"]["value"] = 999999.0
    with open(snap_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    code_tampered, msg_tampered = rms.rebuild_from_snapshot(str(snap_file))
    assert code_tampered == rms.EXIT_DIFF
    assert "Value mismatch at ^GSPC.quote.close" in msg_tampered


def test_target_resolver_all_8_profiles():
    """Verify target resolver properly classifies and configures all 8 user query examples."""
    # 1. 코스피
    p1 = tr.resolve_target("코스피")
    assert p1["profile"] == "KR_INDEX"
    assert p1["primary_ticker"] == "^KS11"
    assert p1["parent_index"] == "^KS11"
    assert p1["indices"] == ["^KS11", "^KQ11", "^GSPC", "^SOX"]
    assert "USDKRW=X" in p1["macro"]

    # 2. 한국증시
    p2 = tr.resolve_target("한국증시")
    assert p2["profile"] == "KR_MARKET"
    assert p2["primary_ticker"] == "^KS11"
    assert p2["parent_index"] == "^KS11"
    assert p2["indices"] == ["^KS11", "^KQ11", "^GSPC", "^SOX"]

    # 3. 반도체
    p3 = tr.resolve_target("반도체")
    assert p3["profile"] == "SECTOR_SEMI"
    assert p3["primary_ticker"] == "^SOX"
    assert p3["parent_index"] == "^GSPC"
    assert p3["indices"] == ["^SOX", "SMH", "^NDX", "^GSPC", "005930.KS", "000660.KS", "NVDA"]

    # 4. 삼성전자
    p4 = tr.resolve_target("삼성전자")
    assert p4["profile"] == "SINGLE_STOCK"
    assert p4["primary_ticker"] == "005930.KS"
    assert p4["parent_index"] == "^KS11"
    assert p4["indices"] == ["005930.KS", "^KS11", "^KQ11", "^SOX", "^GSPC"]
    assert "USDKRW=X" in p4["macro"]

    # 5. LG전자
    p5 = tr.resolve_target("LG전자")
    assert p5["profile"] == "SINGLE_STOCK"
    assert p5["primary_ticker"] == "066570.KS"
    assert p5["parent_index"] == "^KS11"
    assert p5["indices"] == ["066570.KS", "^KS11", "^KQ11", "^SOX", "^GSPC"]

    # 6. 테슬라
    p6 = tr.resolve_target("테슬라")
    assert p6["profile"] == "SINGLE_STOCK"
    assert p6["primary_ticker"] == "TSLA"
    assert p6["parent_index"] == "^NDX"
    assert p6["indices"] == ["TSLA", "^NDX", "^GSPC", "^SOX"]

    # 7. 미국증시
    p7 = tr.resolve_target("미국증시")
    assert p7["profile"] == "US_MARKET"
    assert p7["primary_ticker"] == "^GSPC"
    assert p7["parent_index"] == "^GSPC"
    assert p7["indices"] == ["^GSPC", "^NDX", "^DJI", "^RUT", "^SOX"]

    # 8. 기술주식
    p8 = tr.resolve_target("기술주식")
    assert p8["profile"] == "SECTOR_TECH"
    assert p8["primary_ticker"] == "^NDX"
    assert p8["parent_index"] == "^NDX"
    assert p8["indices"] == ["^NDX", "XLK", "^SOX", "^GSPC"]


def test_usdkrw_macro_risk_calculation():
    """Verify USD/KRW exchange rate risk indicator thresholds (<1350 🟢, 1350-1420 🟡, >1420 🔴)."""
    # 1. Stable rate: 1320 (< 1350) -> 🟢
    df_stable = make_sample_df(periods=10, base_price=1320.0, trend=0.1)
    risk_stable = mm.compute_macro_risk({"USDKRW=X": df_stable})
    assert risk_stable["usdkrw"]["signal"] == "🟢"
    assert risk_stable["usdkrw"]["rate"] == 1320.9
    assert "환율 안정" in risk_stable["usdkrw"]["status"]

    # 2. Caution rate: 1380 (1350-1420) -> 🟡
    df_caution = make_sample_df(periods=10, base_price=1380.0, trend=0.1)
    risk_caution = mm.compute_macro_risk({"USDKRW=X": df_caution})
    assert risk_caution["usdkrw"]["signal"] == "🟡"
    assert "환율 경계" in risk_caution["usdkrw"]["status"]

    # 3. High risk rate: 1450 (> 1420) -> 🔴
    df_high = make_sample_df(periods=10, base_price=1450.0, trend=0.1)
    risk_high = mm.compute_macro_risk({"USDKRW=X": df_high})
    assert risk_high["usdkrw"]["signal"] == "🔴"
    assert "고환율 경보" in risk_high["usdkrw"]["status"]


def test_martial_law_crisis_benchmark():
    """Verify 12.3 martial law crisis benchmark evaluation."""
    df = make_sample_df(start_date="2024-01-01", periods=600, base_price=2500.0, trend=0.5)
    ml_dt = pd.to_datetime("2024-12-03")
    if ml_dt in df.index:
        df.loc[ml_dt, "Low"] = 2450.0

    evals = mm.evaluate_crisis_benchmarks(df, current_close=2600.0)
    ml_eval = next((e for e in evals if "martial_law" in e["id"]), None)
    assert ml_eval is not None
    assert "12.3 비상계엄" in ml_eval["name"]
    assert ml_eval["breached"] is False
    assert ml_eval["buffer_pct"] > 0


def test_single_stock_beta_calculation():
    """Verify stock beta calculation relative to benchmark."""
    np.random.seed(42)
    periods = 100
    dates = pd.date_range("2024-01-01", periods=periods, freq="B")

    bench_ret = np.random.normal(0.001, 0.01, periods)
    bench_price = 100.0 * np.exp(np.cumsum(bench_ret))
    bench_df = pd.DataFrame({"Close": bench_price}, index=dates)

    noise = np.random.normal(0, 0.002, periods)
    stock_ret = 1.6 * bench_ret + noise
    stock_price = 50.0 * np.exp(np.cumsum(stock_ret))
    stock_df = pd.DataFrame({"Close": stock_price}, index=dates)

    beta = mm.compute_stock_beta(stock_df, bench_df, window=60)
    assert beta is not None
    assert round(beta, 1) == 1.6

    empty_df = pd.DataFrame()
    assert mm.compute_stock_beta(empty_df, bench_df) is None
    assert mm.compute_stock_beta(stock_df, empty_df) is None


def test_korean_and_single_stock_offline_snapshot_rebuild(tmp_path):
    """Verify offline Section 4 rebuild and snapshot determinism for Korean stocks with USD/KRW."""
    import get_market_stats as gms
    import rebuild_market_section4 as rms
    import market_raw_inputs as ri

    raw_items = {}
    stamp_str = "2026-11-05T16:00:00"
    for sym in ["005930.KS", "^KS11", "^SOX", "^GSPC", "^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD", "USDKRW=X"]:
        base = 55000.0 if sym == "005930.KS" else (2500.0 if "^KS11" in sym else (1350.0 if sym == "USDKRW=X" else 100.0))
        df = make_sample_df(start_date="2024-01-01", periods=500, base_price=base)
        raw_items[sym] = ri.make_item("yahoo", stamp_str, "ok", kind="frame", data=df)

    snap_file = tmp_path / "test_samsung_snap.json"

    sec4_text, snap = gms.run_market_analysis(
        raw_inputs=raw_items,
        indices=["005930.KS", "^KS11", "^SOX", "^GSPC"],
        primary_ticker="005930.KS",
        parent_index="^KS11",
        macro=["^VIX", "^TNX", "^IRX", "DX-Y.NYB", "CL=F", "GC=F", "HYG", "LQD", "USDKRW=X"],
        as_of_str="2026-11-05 16:00 KST",
        snapshot_path=str(snap_file),
    )

    attach_section4(sec4_text, str(snap_file), attached_at="2026-11-05 16:00 KST")

    code, msg = rms.rebuild_from_snapshot(str(snap_file))
    assert code == rms.EXIT_SAME
    assert "Section 4 rebuild match verified" in msg

    with open(snap_file, "r", encoding="utf-8") as f:
        snap_data = json.load(f)

    assert "005930.KS.quote.close" in snap_data["values"]
    assert "005930.KS.beta_parent" in snap_data["values"]
    assert "macro.usdkrw.rate" in snap_data["values"]


def test_crisis_benchmarks_scoped_to_korea():
    """Verify that Korean martial law benchmark is scoped to Korean assets only."""
    df = make_sample_df(start_date="2024-01-01", periods=300, base_price=200.0)
    ml_dt = pd.to_datetime("2024-12-03")
    if ml_dt in df.index:
        df.loc[ml_dt, "Low"] = 300.0  # Would be a breach if evaluated

    # US asset (is_korean=False)
    evals_us = mm.evaluate_crisis_benchmarks(df, current_close=200.0, is_korean=False)
    ml_eval_us = next((e for e in evals_us if "martial_law" in e["id"]), None)
    assert ml_eval_us is not None
    assert ml_eval_us.get("status") == "not_applicable"
    assert ml_eval_us["crisis_low"] is None
    assert ml_eval_us["breached"] is False

    # Korean asset (is_korean=True)
    evals_kr = mm.evaluate_crisis_benchmarks(df, current_close=200.0, is_korean=True)
    ml_eval_kr = next((e for e in evals_kr if "martial_law" in e["id"]), None)
    assert ml_eval_kr is not None
    assert "12.3 비상계엄" in ml_eval_kr["name"]
    assert ml_eval_kr.get("status") != "not_applicable"


def test_target_resolver_generic_us_and_kr_tickers():
    """Verify generic US tickers and newly added Korean stocks resolve correctly."""
    import target_resolver as tr

    # Generic US tickers
    p_intc = tr.resolve_target("INTC")
    assert p_intc["profile"] == tr.PROFILE_SINGLE_STOCK
    assert p_intc["primary_ticker"] == "INTC"
    assert p_intc["parent_index"] == "^NDX"

    p_pltr = tr.resolve_target("PLTR")
    assert p_pltr["profile"] == tr.PROFILE_SINGLE_STOCK
    assert p_pltr["primary_ticker"] == "PLTR"

    # Known Korean and US stocks
    p_msft = tr.resolve_target("MSFT")
    assert p_msft["profile"] == tr.PROFILE_SINGLE_STOCK
    assert p_msft["primary_ticker"] == "MSFT"

    p_hyundai = tr.resolve_target("현대차")
    assert p_hyundai["profile"] == tr.PROFILE_SINGLE_STOCK
    assert p_hyundai["primary_ticker"] == "005380.KS"
    assert p_hyundai["parent_index"] == "^KS11"


def test_socratic_invalidation_ladder_uses_target_name():
    """Verify thesis invalidation ladder reflects the evaluated target's actual name."""
    import socratic_auditor as sa

    primary_metrics = {
        "symbol": "005930.KS",
        "name": "삼성전자 (Samsung Electronics)",
        "current_close": 55000.0,
        "sma_200": 58000.0,
        "sma_50": 56000.0,
        "crisis_benchmarks": [
            {
                "id": "martial_law_20241203",
                "name": "12.3 비상계엄 선포 쇼크",
                "target_date": "2024-12-03",
                "crisis_low": 53000.0,
                "breached": False,
                "buffer_pct": 3.77,
            }
        ],
    }
    ladder = sa.build_thesis_invalidation_ladder(
        primary_metrics=primary_metrics,
        macro_risk={"vix": {"signal": "🟡"}},
        crisis_evals=primary_metrics["crisis_benchmarks"],
    )
    assert len(ladder["bull_invalidation_triggers"]) >= 2
    assert "삼성전자" in ladder["bull_invalidation_triggers"][0]
    assert "S&P 500" not in ladder["bull_invalidation_triggers"][0]


def test_check_market_report_numbers_detects_unpopulated_comments(tmp_path):
    """Verify check_market_report_numbers catches unpopulated script comments."""
    import check_market_report_numbers as cmn

    bad_report = tmp_path / "bad_report.md"
    bad_snap = tmp_path / "bad_report_data.json"

    # Make minimal valid snapshot
    with open(bad_snap, "w", encoding="utf-8") as f:
        json.dump({"section4": {"sha256": "dummy"}, "values": {}}, f)

    bad_report_content = (
        "## 4. 데이터 스냅샷 및 기술적 지표 베이스라인\n"
        "| 지표 | 값 |\n|---|---|\n"
        "<!-- section4-sha256: dummy -->\n\n"
        "## 9. 결론 및 모니터링 체크리스트\n"
        "<!-- 스크립트 8번 경고 항목이 이 자리에 삽입됩니다. -->\n"
    )
    with open(bad_report, "w", encoding="utf-8") as f:
        f.write(bad_report_content)

    res = cmn.verify_report(str(bad_report))
    assert res == cmn.EXIT_ISSUES


def test_tier1_tactical_support_metrics():
    """Verify Tier 1 tactical support: dist_50, dist_200, 52w_low, dist_52w_low, tier1_support."""
    df = make_sample_df(periods=300, base_price=5000.0, trend=2.0)
    met = mm.compute_index_metrics(df, ticker="^GSPC")

    assert met["dist_50"] is not None
    assert met["dist_200"] is not None
    assert met["52w_low"] is not None
    assert met["dist_52w_low"] is not None
    assert "tier1_support" in met

    t1 = met["tier1_support"]
    assert "sma_50" in t1
    assert "sma_200" in t1
    assert "52w_low" in t1
    assert t1["dist_50"] == met["dist_50"]
    assert t1["dist_200"] == met["dist_200"]
    assert t1["dist_52w_low"] == met["dist_52w_low"]
    # With upward trend, distance to 52w low is positive and substantial
    assert t1["dist_52w_low"] > 0


def test_tier2_rolling_crisis_benchmark_calculation():
    """Verify Tier 2 rolling 252-day peak-to-trough calculation and dynamic rollover."""
    dates = pd.date_range(start="2024-01-01", periods=300, freq="B")
    prices = [5000.0] * 300

    # Create a peak at index 50 (price 6000), then a deep trough at index 100 (price 4200: -30% drawdown)
    for i in range(50):
        prices[i] = 5000.0 + i * 20.0  # reaches 5980 at 49
    prices[50] = 6000.0  # Peak
    prices[100] = 4200.0  # Trough: (4200 - 6000) / 6000 = -30.0%
    # After index 100, price recovers to 5500
    for i in range(101, 300):
        prices[i] = 5500.0

    df = pd.DataFrame(
        {
            "Open": prices,
            "High": prices,
            "Low": prices,
            "Close": prices,
            "Volume": [1000000] * 300,
        },
        index=dates,
    )

    current_close = 5500.0
    res = mm.compute_rolling_crisis_benchmark(df, current_close=current_close, window=252)

    assert res["status"] == "ok"
    # Peak-to-trough was on dates[100]
    expected_trough_date = dates[100].strftime("%Y-%m-%d")
    assert res["trough_date"] == expected_trough_date
    assert res["trough_price"] == 4200.0
    assert abs(res["drawdown_pct"] - (-30.0)) < 0.1
    # Buffer: (5500 - 4200) / 4200 * 100 = 30.95%
    expected_buffer = (5500.0 - 4200.0) / 4200.0 * 100
    assert abs(res["buffer_pct"] - round(expected_buffer, 2)) < 0.1
    assert res["breached"] is False
    assert res["status_code"] == "safe_buffer"
    assert res["icon"] == "🟢"

    # Test breach scenario
    res_breach = mm.compute_rolling_crisis_benchmark(df, current_close=4000.0, window=252)
    assert res_breach["breached"] is True
    assert res_breach["status_code"] == "breakdown"
    assert res_breach["icon"] == "🔴"

    # Test rolling window rollover: window of 100 days looks only at index 200..299
    # In that window, prices are flat at 5500, so drawdown is 0%
    res_rollover = mm.compute_rolling_crisis_benchmark(df, current_close=5500.0, window=100)
    assert res_rollover["status"] == "ok"
    assert res_rollover["trough_price"] == 5500.0
    assert res_rollover["drawdown_pct"] == 0.0


def test_tier3_adaptive_crisis_tier_status_bands():
    """Verify Tier 3 4-stage proximity band classification."""
    # 1. safe_buffer (> +30%)
    s1 = mm.get_crisis_tier_status(35.5)
    assert s1["status_code"] == "safe_buffer"
    assert s1["icon"] == "🟢"
    assert "안전 완충" in s1["label"]

    # 2. approaching (+10% ~ +30%)
    s2 = mm.get_crisis_tier_status(15.2)
    assert s2["status_code"] == "approaching"
    assert s2["icon"] == "🟡"
    assert "경계권 접근" in s2["label"]

    # 3. near_breakdown (0% ~ +10%)
    s3 = mm.get_crisis_tier_status(4.8)
    assert s3["status_code"] == "near_breakdown"
    assert s3["icon"] == "🚨"
    assert "비상 경보" in s3["label"]

    # 4. breakdown (< 0%)
    s4 = mm.get_crisis_tier_status(-3.5)
    assert s4["status_code"] == "breakdown"
    assert s4["icon"] == "🔴"
    assert "붕괴" in s4["label"]

    # Boundary values
    assert mm.get_crisis_tier_status(30.01)["status_code"] == "safe_buffer"
    assert mm.get_crisis_tier_status(30.0)["status_code"] == "approaching"
    assert mm.get_crisis_tier_status(10.0)["status_code"] == "approaching"
    assert mm.get_crisis_tier_status(9.99)["status_code"] == "near_breakdown"
    assert mm.get_crisis_tier_status(0.0)["status_code"] == "near_breakdown"
    assert mm.get_crisis_tier_status(-0.01)["status_code"] == "breakdown"


def test_trend_signal_and_socratic_ladder_with_tier2_tier3():
    """Verify market regime trend signal and socratic ladder reflect Tier 2 and Tier 3 states."""
    # Near breakdown in Tier 3 should trigger 🟡 in trend even if above 200 SMA
    metrics = {
        "ticker": "^GSPC",
        "current_close": 5100.0,
        "sma_50": 5000.0,
        "sma_200": 4800.0,
        "dist_200": 6.25,
    }
    crisis_near_breakdown = [
        {
            "id": "iran_20240419",
            "name": "이란-이스라엘 1차 공습 저점",
            "crisis_low": 4950.0,
            "buffer_pct": 3.03,  # < 10% -> near_breakdown
            "breached": False,
            "status_code": "near_breakdown",
            "icon": "🚨",
        }
    ]
    tier2_eval = {
        "trough_date": "2024-08-05",
        "trough_price": 5000.0,
        "drawdown_pct": -12.5,
        "buffer_pct": 2.0,  # < 10% -> near breakdown
        "breached": False,
        "status_code": "near_breakdown",
        "icon": "🚨",
    }

    sig = mr.evaluate_trend_signal([metrics], crisis_evals=crisis_near_breakdown, tier2_eval=tier2_eval)
    assert sig["signal"] == "🟡"
    assert "임박" in sig["status"] or "접근" in sig["status"]

    # Invalidation ladder includes Tier 2 trigger
    ladder = sa.build_thesis_invalidation_ladder(
        primary_metrics=metrics,
        macro_risk={"vix": {"signal": "🟢"}},
        crisis_evals=crisis_near_breakdown,
        tier2_eval=tier2_eval,
    )
    assert any("Tier 2" in trg for trg in ladder["bull_invalidation_triggers"])
    assert any("5,000.0" in trg for trg in ladder["bull_invalidation_triggers"])

    # Cognitive bias audit detects near-breakdown (<10%)
    audit = sa.audit_cognitive_biases(
        sp500_metrics=metrics,
        macro_risk={"vix": {"signal": "🟢"}},
        trend_eval=sig,
    )
    loss_aversion = next(b for b in audit if b["bias"] == "손실 회피 편향 (Loss Aversion)")
    assert loss_aversion["triggered"] is True
    assert "비상 경보" in loss_aversion["evidence"]


def test_tier2_duplicate_timestamps_and_trailing_nans():
    """Verify Tier 2 compute_rolling_crisis_benchmark handles duplicate timestamps and trailing NaNs."""
    # 1. Duplicate timestamps on trough date
    dates = [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")]
    df_dup = pd.DataFrame(
        {"Close": [100.0, 80.0, 90.0], "Low": [95.0, 75.0, 85.0]},
        index=dates,
    )
    res_dup = mm.compute_rolling_crisis_benchmark(df_dup, current_close=90.0, window=252)
    assert res_dup["status"] == "ok"
    assert res_dup["trough_price"] == 75.0
    assert abs(res_dup["drawdown_pct"] - (-20.0)) < 0.01
    assert abs(res_dup["buffer_pct"] - 20.0) < 0.01

    # 2. Trailing NaNs in Close column
    dates_nan = pd.date_range("2024-01-01", periods=10, freq="B")
    df_nan = pd.DataFrame(
        {
            "Close": [100.0, 95.0, 90.0, 85.0, 80.0, 75.0, 70.0, 65.0, np.nan, np.nan],
            "Low": [98.0, 93.0, 88.0, 83.0, 78.0, 73.0, 68.0, 63.0, np.nan, np.nan],
        },
        index=dates_nan,
    )
    res_nan = mm.compute_rolling_crisis_benchmark(df_nan, current_close=65.0, window=3)
    assert res_nan["status"] == "ok"
    assert res_nan["trough_price"] == 63.0
    assert res_nan["trough_date"] == dates_nan[7].strftime("%Y-%m-%d")


def test_tier3_unsorted_index_handling():
    """Verify evaluate_crisis_benchmarks safely handles unsorted DatetimeIndex without error."""
    dates_unsorted = pd.to_datetime(["2024-08-07", "2024-08-03", "2024-08-06", "2024-08-01"])
    df_unsorted = pd.DataFrame(
        {"Close": [100.0, 90.0, 95.0, 85.0], "Low": [95.0, 85.0, 90.0, 80.0]},
        index=dates_unsorted,
    )
    res = mm.evaluate_crisis_benchmarks(df_unsorted, current_close=100.0)
    assert len(res) >= 2
    yen_b = next((x for x in res if "yen" in x["id"]), None)
    assert yen_b is not None
    assert yen_b["crisis_low"] is not None


def test_macro_noise_summary_with_korean_asset_and_missing_benchmarks():
    """Verify macro noise summary logic correctly detects Korean martial law breach and missing benchmarks."""
    from generate_market_report import populate_report
    import target_resolver as tr
    from market_snapshot import MarketSnapshot

    # Create dummy snapshot with KOSPI where Yen is safe (+35%) but martial law is breached (-2.5%)
    snap = MarketSnapshot()
    as_of = "2026-11-06"
    snap.record("^KS11.quote.close", 5000.0, source="yahoo", basis="index_close", as_of=as_of)
    snap.record("^KS11.ret.5d", -3.0, source="derived", basis="drawdown", as_of=as_of)
    snap.record("^KS11.diagnostics.drawdown_52w", -15.0, source="derived", basis="drawdown", as_of=as_of)
    snap.record("^KS11.ma.sma_50", 5200.0, source="derived", basis="moving_average", as_of=as_of)
    snap.record("^KS11.ma.dist_50", -3.85, source="derived", basis="moving_average", as_of=as_of)
    snap.record("^KS11.ma.sma_200", 5500.0, source="derived", basis="moving_average", as_of=as_of)
    snap.record("^KS11.ma.dist_200", -9.09, source="derived", basis="moving_average", as_of=as_of)
    snap.record("^KS11.quote.52w_low", 4500.0, source="yahoo", basis="quote", as_of=as_of)
    snap.record("^KS11.diagnostics.dist_52w_low", 11.11, source="derived", basis="drawdown", as_of=as_of)
    snap.record("^KS11.tier2.trough_date", "2026-08-01", source="derived", basis="support_check", as_of=as_of)
    snap.record("^KS11.tier2.trough_price", 4800.0, source="yahoo", basis="support_check", as_of=as_of)
    snap.record("^KS11.tier2.drawdown_pct", -20.0, source="derived", basis="drawdown", as_of=as_of)
    snap.record("^KS11.tier2.buffer_pct", 4.17, source="derived", basis="support_check", as_of=as_of)
    snap.record("^KS11.tier2.breached", False, source="derived", basis="support_check", as_of=as_of)

    # Tier 3 benchmarks: yen safe (+35%), iran safe (+35%), martial law breached (-2.5%)
    snap.record("^KS11.crisis.yen_carry_20240805.buffer_pct", 35.0, source="derived", basis="support_check")
    snap.record("^KS11.crisis.yen_carry_20240805.breached", False, source="derived", basis="support_check")
    snap.record("^KS11.crisis.iran_war_20240419.buffer_pct", 35.0, source="derived", basis="support_check")
    snap.record("^KS11.crisis.iran_war_20240419.breached", False, source="derived", basis="support_check")
    snap.record("^KS11.crisis.iran_war_20241001.buffer_pct", 35.0, source="derived", basis="support_check")
    snap.record("^KS11.crisis.iran_war_20241001.breached", False, source="derived", basis="support_check")
    snap.record("^KS11.crisis.martial_law_20241203.buffer_pct", -2.5, source="derived", basis="support_check")
    snap.record("^KS11.crisis.martial_law_20241203.breached", True, source="derived", basis="support_check")

    template_path = os.path.join(SCRIPTS_DIR, "..", "templates", "market_report_template.md")
    with open(template_path, "r", encoding="utf-8") as f:
        tmpl = f.read()

    t_info = tr.resolve_target("코스피")
    rep = populate_report(
        tmpl=tmpl,
        snapshot=snap,
        market="코스피",
        theme="위기 진단",
        now_time_str="2026-11-06 12:00 KST",
        snapshot_basename="dummy_snap.json",
        sec4_text="dummy section4",
        target_info=t_info,
    )

    # Tier 1 bullet must contain dist_50
    assert "이격도: -3.85%" in rep
    # Korean asset with breached martial law must trigger 🔴 warning, NOT 🟢 macro safe buffer
    assert "🔴 **거시 시스템 리스크 경보**" in rep
    assert "🟢 **거시 시스템 리스크 배제**" not in rep




