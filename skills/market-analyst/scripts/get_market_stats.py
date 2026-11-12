"""
Master analysis script for market-analyst:
Collects real-time data, calculates all metrics, diagnoses crises,
runs the Socratic auditor, evaluates the Market Regime matrix,
and outputs formatted Markdown Section 4 tables and data snapshot.
"""

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import market_collect as collect
import market_metrics as mm
import market_regime as mr
import market_raw_inputs as ri
import socratic_auditor as sa
from market_snapshot import MarketSnapshot, MARKET_HEADER

KST = datetime.timezone(datetime.timedelta(hours=9))


def format_tables_section(
    index_results: List[Dict[str, Any]],
    crisis_dict: Dict[str, List[Dict[str, Any]]],
    rotation: Dict[str, Any],
    macro: Dict[str, Any],
    regime: Dict[str, Any],
    biases: List[Dict[str, Any]],
    ladder: Dict[str, Any],
    snapshot: MarketSnapshot,
    as_of_str: Optional[str] = None,
    tier2_dict: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """Format the complete Section 4 Markdown string."""
    now_str = as_of_str or datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = []
    lines.append(MARKET_HEADER)
    lines.append(f"> 산출 시점: {now_str} (실시간 시장 데이터 기준) [1]")
    lines.append("")

    # --- 표 1: 주요 시장 지수 및 기술주 현황 ---
    lines.append("### 1. 주요 시장 지수 및 핵심 벤치마크 현황")
    lines.append("| 지수명 (티커) | 현재 종가 | 1일 등락률 | 5일 등락률 | 1개월 등락률 | 52주 최고가 | 52주 낙폭 (MDD) |")
    lines.append("|---|---|---|---|---|---|---|")
    for idx in index_results:
        sym = idx.get("ticker", "")
        name = idx.get("name", sym)
        close = f"{idx.get('current_close', 0.0):,.2f}"
        r1d = f"{idx.get('ret_1d', 0.0):+.2f}%" if idx.get("ret_1d") is not None else "-"
        r5d = f"{idx.get('ret_5d', 0.0):+.2f}%" if idx.get("ret_5d") is not None else "-"
        r1m = f"{idx.get('ret_1m', 0.0):+.2f}%" if idx.get("ret_1m") is not None else "-"
        w52_h = f"{idx.get('52w_high', 0.0):,.2f}"
        mdd = f"{idx.get('drawdown_52w', 0.0):+.2f}%" if idx.get("drawdown_52w") is not None else "-"
        lines.append(f"| **{name}** (`{sym}`) | {close} | {r1d} | {r5d} | {r1m} | {w52_h} | **{mdd}** |")
    lines.append("")

    # --- 표 2: 핵심 기술적 지지선 및 가격 방어력 진단표 ---
    lines.append("### 2. 핵심 기술적 지지선 및 가격 방어력 진단표")
    lines.append("| 지수 / 종목명 | 50 SMA | 200 SMA | 200선 이격도 | 52주 저점 완충도 | 최근 1년 조정 저점 (손절 기준선) | 지지력 진단 |")
    lines.append("|---|---|---|---|---|---|---|")
    for idx in index_results:
        sym = idx.get("ticker", "")
        name = idx.get("name", sym)
        s50 = f"{idx.get('sma_50'):,.1f}" if idx.get('sma_50') else "-"
        s200 = f"{idx.get('sma_200'):,.1f}" if idx.get('sma_200') else "-"
        d200 = f"{idx.get('dist_200'):+.2f}%" if idx.get("dist_200") is not None else "-"
        d52_low = f"{idx.get('dist_52w_low'):+.2f}%" if idx.get("dist_52w_low") is not None else "-"

        t2 = (tier2_dict or {}).get(sym, {})
        buf_val = None
        if t2 and t2.get("status") == "ok":
            t2_date = t2.get("trough_date", "-")
            t2_price = f"{t2.get('trough_price'):,.1f}" if t2.get('trough_price') is not None else "-"
            buf_val = t2.get('buffer_pct')
            t2_buf = f"{buf_val:+.1f}%" if buf_val is not None else "-"
            t2_cell = f"{t2_date} ({t2_price} / 완충 {t2_buf})"
        else:
            t2_cell = "-"

        sup_info = mr.get_support_status(buf_val)
        diag_str = f"{sup_info['icon']} {sup_info['status']}" if buf_val is not None else "⚪ 데이터 없음"

        lines.append(f"| **{name}** | {s50} | {s200} | {d200} | {d52_low} | {t2_cell} | {diag_str} |")
    lines.append("")

    # --- 표 3: 11개 SPDR 섹터 로테이션 및 상대강도표 ---
    lines.append("### 3. 11개 SPDR 섹터 로테이션 및 상대강도표 (RS vs SPY)")
    lines.append(f"> 벤치마크 SPY 5일 등락률: {rotation.get('spy_ret_5d', 0.0):+.2f}% | 1개월: {rotation.get('spy_ret_1m', 0.0):+.2f}%")
    lines.append("")
    lines.append("| 섹터명 (티커) | 구분 | 현재가 | 5일 등락률 | 5일 RS (vs SPY) | 1개월 RS (vs SPY) | 로테이션 진단 |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in rotation.get("sectors", []):
        sym = s.get("ticker", "")
        name = s.get("name", sym)
        cat = s.get("category", "")
        pr = f"`${s.get('current_price', 0.0):,.2f}`"
        r5d = f"{s.get('ret_5d', 0.0):+.2f}%"
        rs5d = f"{s.get('rs_5d', 0.0):+.2f}%"
        rs1m = f"{s.get('rs_1m', 0.0):+.2f}%"
        diag = "🟢 주도 (Outperform)" if s.get("rs_5d", 0.0) > 0 else "🔴 소외 (Underperform)"
        lines.append(f"| **{name}** (`{sym}`) | {cat} | {pr} | {r5d} | **{rs5d}** | {rs1m} | {diag} |")
    lines.append("")
    lines.append(f"* **경기민감 vs 경기방어 5일 순환매 스프레드:** **{rotation.get('spread_5d', 0.0):+.2f}%** (상태: **{rotation.get('signal')} {rotation.get('regime_desc')}**)")
    lines.append("")

    # --- 표 4: 거시 리스크 및 스트레스 바로미터 ---
    lines.append("### 4. 거시 리스크 및 스트레스 바로미터")
    lines.append("| 지표 항목 | 티커 / 출처 | 현재 수치 | 5일간 변동 | 리스크 평가 |")
    lines.append("|---|---|---|---|---|")
    vix = macro.get("vix", {})
    vix_lvl = f"{vix.get('level'):,.2f}" if vix.get("level") is not None else "-"
    vix_chg = f"{vix.get('chg_5d_pts'):+.2f}pt ({vix.get('chg_5d_pct'):+.2f}%)" if (vix.get("chg_5d_pts") is not None and vix.get("chg_5d_pct") is not None) else "-"
    vix_sig = f"{vix.get('signal', '⚪')} {vix.get('status', '데이터 없음')}"
    lines.append(f"| **CBOE 변동성 지수 (VIX)** | `^VIX` | {vix_lvl} | {vix_chg} | {vix_sig} |")

    r10 = macro.get("rate_10y", {})
    r10_yld = f"{r10.get('yield')}%" if r10.get("yield") is not None else "-"
    r10_chg = f"{r10.get('chg_5d_bps'):+.1f} bps" if r10.get("chg_5d_bps") is not None else "-"
    r10_sig = f"{r10.get('signal', '⚪')} {r10.get('status', '데이터 없음')}"
    lines.append(f"| **미국 10년물 국채금리** | `^TNX` | {r10_yld} | {r10_chg} | {r10_sig} |")

    yc = macro.get("yield_curve", {})
    if yc.get("source") == "fred":
        yc_sp = f"{yc.get('spread_10y_13w'):+.2f}%p" if yc.get('spread_10y_13w') is not None else "-"
        yc_13w = "미 연준 공식 T10Y3M"
        yc_inv = "🔴 역전 상태" if yc.get("inverted") else "🟢 정상 스프레드"
        lines.append(f"| **장단기 금리차 (10Y - 3M)** | `FRED T10Y3M` | {yc_sp} | {yc_13w} | {yc_inv} |")
    else:
        yc_sp = f"{yc.get('spread_10y_13w')} bps" if yc.get('spread_10y_13w') is not None else "-"
        yc_13w = f"13W 금리: {yc.get('irx_13w')}%" if yc.get('irx_13w') is not None else "-"
        yc_inv = "🔴 역전 상태" if yc.get("inverted") else ("🟢 정상 스프레드" if yc.get('spread_10y_13w') is not None else "-")
        lines.append(f"| **장단기 금리차 (10Y - 13W)** | `^TNX - ^IRX` | {yc_sp} | {yc_13w} | {yc_inv} |")

    cr = macro.get("credit", {})
    if cr.get("hy_oas_bps") is not None:
        cr_ratio = f"{cr.get('hy_oas_bps'):.0f} bps"
        cr_rs = f"BBB OAS: {cr.get('bbb_oas_bps'):.0f} bps" if cr.get('bbb_oas_bps') else "공식 ICE BofA"
        cr_sig = f"{cr.get('signal', '⚪')} {cr.get('status', '데이터 없음')}"
        lines.append(f"| **하이일드 신용 스프레드** | `FRED BAMLH0A0HYM2` | {cr_ratio} | {cr_rs} | {cr_sig} |")
    else:
        cr_ratio = f"{cr.get('hyg_lqd_ratio')}" if cr.get('hyg_lqd_ratio') is not None else "-"
        cr_rs = f"상대강도 {cr.get('credit_rs_5d'):+.2f}%" if cr.get('credit_rs_5d') is not None else "-"
        cr_sig = f"{cr.get('signal', '⚪')} {cr.get('status', '데이터 없음')}"
        lines.append(f"| **신용 스프레드 (HYG/LQD)** | `HYG / LQD` | {cr_ratio} | {cr_rs} | {cr_sig} |")

    dxy = macro.get("dxy", {})
    dxy_lvl = f"{dxy.get('level'):,.2f}" if dxy.get("level") is not None else "-"
    dxy_chg = f"{dxy.get('chg_5d_pct'):+.2f}%" if dxy.get("chg_5d_pct") is not None else "-"
    lines.append(f"| **달러 인덱스 (DXY)** | `DX-Y.NYB` | {dxy_lvl} | {dxy_chg} | 통화 유동성 지표 |")

    usd = macro.get("usdkrw", {})
    if usd.get("rate") is not None:
        usd_rate = f"{usd.get('rate'):,.2f}원"
        usd_chg = f"{usd.get('chg_5d_pts'):+.2f}원 ({usd.get('chg_5d_pct'):+.2f}%)" if (usd.get('chg_5d_pts') is not None and usd.get('chg_5d_pct') is not None) else "-"
        usd_sig = f"{usd.get('signal', '⚪')} {usd.get('status', '데이터 없음')}"
        lines.append(f"| **원/달러 환율 (USD/KRW)** | `USDKRW=X` | {usd_rate} | {usd_chg} | {usd_sig} |")

    oil = macro.get("crude_oil", {})
    oil_pr = f"`${oil.get('price'):,.2f}`" if oil.get("price") is not None else "-"
    oil_chg = f"{oil.get('chg_5d_pct'):+.2f}%" if oil.get("chg_5d_pct") is not None else "-"
    lines.append(f"| **WTI 원유 선물** | `CL=F` | {oil_pr} | {oil_chg} | 에너지 인플레이션 지표 |")

    gold = macro.get("gold", {})
    gold_pr = f"`${gold.get('price'):,.2f}`" if gold.get("price") is not None else "-"
    gold_chg = f"{gold.get('chg_5d_pct'):+.2f}%" if gold.get("chg_5d_pct") is not None else "-"
    lines.append(f"| **국제 금 선물** | `GC=F` | {gold_pr} | {gold_chg} | 안전자산 도피 지표 |")
    lines.append("")

    # --- 표 5: 5대 기둥 신호등 매트릭스 및 시장 국면 판정 ---
    lines.append("### 5. 5대 기둥 신호등 매트릭스 및 시장 국면 판정")
    p = regime.get("pillars", {})
    eval_name = regime.get("evaluated_name") or "S&P 500"
    vix_l_str = f"VIX {vix.get('level')}" if vix.get('level') is not None else "VIX (데이터 없음)"
    r10_bps_str = f"10년물 금리 5일 변동 {r10.get('chg_5d_bps')} bps" if r10.get('chg_5d_bps') is not None else "10년물 금리 (데이터 없음)"
    cr_rs_str = f"HYG/LQD 5일 상대강도 {cr.get('credit_rs_5d')}%" if cr.get('credit_rs_5d') is not None else "신용 스프레드 (데이터 없음)"
    sp_5d_str = f"경기민감 vs 경기방어 스프레드 {rotation.get('spread_5d')}%" if rotation.get('spread_5d') is not None else "섹터 스프레드 (데이터 없음)"
    lines.append("| 기둥 지표 | 신호 | 핵심 지표 근거 |")
    lines.append("|---|---|---|")
    lines.append(f"| **1. 추세 및 위기 지지선** | {p.get('trend')} | {eval_name} 200선 이격도 및 위기 저점 방어 상태 |")
    lines.append(f"| **2. 변동성 (공포 지수)** | {p.get('vix')} | {vix_l_str} (기준: <20 🟢, 20~25 🟡, >25 🔴) |")
    lines.append(f"| **3. 금리 및 거시 유동성** | {p.get('rates')} | {r10_bps_str} |")
    lines.append(f"| **4. 신용 리스크 (스프레드)** | {p.get('credit')} | {cr_rs_str} |")
    lines.append(f"| **5. 섹터 브레드스 (주도권)** | {p.get('breadth')} | {sp_5d_str} |")
    lines.append("")
    lines.append(f"* **최종 시장 국면 종합 판정:** **{regime.get('icon')} {regime.get('name')}**")
    lines.append(f"* **권장 현금 비중:** **{regime.get('cash_pct')}%** (주식: {regime.get('equity_pct')}%, 안전자산: {regime.get('safe_pct')}%)")
    lines.append(f"* **국면 진단:** {regime.get('summary')}")
    lines.append("")

    # --- 표 6: 소크라테스식 5대 인지 편향 감사 결과 ---
    lines.append("### 6. 소크라테스식 5대 인지 편향 정량 감사 결과")
    lines.append("| 편향 항목 | 감지 상태 | 데이터 검증 근거 | 교정 가이드 |")
    lines.append("|---|---|---|---|")
    for b in biases:
        state = "🔴 경보 발령" if b.get("triggered") else "🟢 정상 (통제됨)"
        lines.append(f"| **{b.get('bias')}** | {state} | {b.get('evidence')} | {b.get('prescription')} |")
    lines.append("")

    # --- 표 7: 가설 무효화 사다리 (Thesis Invalidation Ladder) ---
    lines.append("### 7. 가설 무효화 사다리 (Thesis Invalidation Ladder)")
    lines.append("#### 🐂 강세론 / 저가 매수 가설 무효화 조건 (즉시 비중 축소 전환):")
    for tr in ladder.get("bull_invalidation_triggers", []):
        lines.append(f"- [ ] {tr}")
    lines.append("")
    lines.append("#### 🐻 약세론 / 관망 가설 무효화 조건 (저가 매수 재개 전환):")
    for tr in ladder.get("bear_invalidation_triggers", []):
        lines.append(f"- [ ] {tr}")
    lines.append("")

    # --- 표 8: 데이터 품질 경고 ---
    lines.append("### 8. 데이터 품질 경고 (Data Quality Warnings)")
    if snapshot.warnings:
        for w in snapshot.warnings:
            lines.append(f"- `[{w.get('code')}]` ({w.get('severity')}): {w.get('message')}")
    else:
        lines.append("- 특이 데이터 품질 경고 없음: 모든 지수 및 지표가 실시간 정상 수신되었습니다.")
    lines.append("")

    return "\n".join(lines)


def run_market_analysis(
    indices: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    macro: Optional[List[str]] = None,
    include_global: bool = False,
    snapshot_path: Optional[str] = None,
    from_snapshot: Optional[str] = None,
    raw_inputs: Optional[Dict[str, Any]] = None,
    as_of_str: Optional[str] = None,
    primary_ticker: Optional[str] = None,
    parent_index: Optional[str] = None,
) -> Tuple[str, MarketSnapshot]:
    """
    Execute complete market analysis pipeline and return Section 4 Markdown and MarketSnapshot.
    Supports running purely offline from snapshot or pre-collected raw inputs.
    """
    snapshot = MarketSnapshot()
    effective_as_of = as_of_str

    # 1. Obtain raw input items (from snapshot, raw_inputs, or live collection)
    if from_snapshot:
        if not os.path.isfile(from_snapshot):
            raise FileNotFoundError(f"Snapshot file not found: {from_snapshot}")
        with open(from_snapshot, "r", encoding="utf-8") as f:
            snap_json = json.load(f)
        raw_items = snap_json.get("inputs", {})
        if not effective_as_of:
            effective_as_of = snap_json.get("meta", {}).get("generated_at")
        snap_args = snap_json.get("meta", {}).get("args", {})
        if not indices and snap_args.get("indices"):
            indices = snap_args.get("indices")
        if not primary_ticker and snap_args.get("primary_ticker"):
            primary_ticker = snap_args.get("primary_ticker")
        if not parent_index and snap_args.get("parent_index"):
            parent_index = snap_args.get("parent_index")
        if not sectors and snap_args.get("sectors"):
            sectors = snap_args.get("sectors")
        if not macro and snap_args.get("macro"):
            macro = snap_args.get("macro")
    elif raw_inputs is not None:
        raw_items = raw_inputs
    else:
        raw_items = collect.collect_market_data(
            indices=indices,
            sectors=sectors,
            macro=macro,
            include_global=include_global,
            period="3y",
        )

    # 2. Extract DataFrames
    dataframes: Dict[str, Any] = {}
    for sym, item in raw_items.items():
        if item.get("status") == "ok" and item.get("kind") == "frame":
            df = ri.dict_to_frame(item.get("data", {}))
            dataframes[sym] = df
        elif item.get("status") == "empty":
            snapshot.add_warning("EMPTY_DATA", f"{sym} 과거 거래 데이터 없음", ticker=sym, severity="warning")
        elif item.get("status") == "error":
            snapshot.add_warning("FETCH_ERROR", f"{sym} 수집 실패: {item.get('error')}", ticker=sym, severity="error")

    # 3. Calculate index metrics
    index_results = []
    target_indices = indices or collect.DEFAULT_INDICES
    if include_global:
        target_indices = target_indices + collect.SUPPLEMENTARY_GLOBAL

    for sym in target_indices:
        df = dataframes.get(sym)
        if df is not None and not df.empty:
            met = mm.compute_index_metrics(df, ticker=sym)
            index_results.append(met)

            # Record in snapshot
            as_of = met.get("as_of")
            snapshot.record(f"{sym}.quote.close", met.get("current_close"), source="yahoo", basis="index_close", as_of=as_of)
            snapshot.record(f"{sym}.ret.1d", met.get("ret_1d"), source="derived", basis="drawdown", as_of=as_of)
            snapshot.record(f"{sym}.ret.5d", met.get("ret_5d"), source="derived", basis="drawdown", as_of=as_of)
            snapshot.record(f"{sym}.ret.1m", met.get("ret_1m"), source="derived", basis="drawdown", as_of=as_of)
            snapshot.record(f"{sym}.diagnostics.drawdown_52w", met.get("drawdown_52w"), source="derived", basis="drawdown", as_of=as_of)
            snapshot.record(f"{sym}.ma.sma_50", met.get("sma_50"), source="derived", basis="moving_average", as_of=as_of)
            snapshot.record(f"{sym}.ma.dist_50", met.get("dist_50"), source="derived", basis="moving_average", as_of=as_of)
            snapshot.record(f"{sym}.ma.sma_200", met.get("sma_200"), source="derived", basis="moving_average", as_of=as_of)
            snapshot.record(f"{sym}.ma.dist_200", met.get("dist_200"), source="derived", basis="moving_average", as_of=as_of)
            snapshot.record(f"{sym}.quote.52w_low", met.get("52w_low"), source="yahoo", basis="quote", as_of=as_of)
            snapshot.record(f"{sym}.diagnostics.dist_52w_low", met.get("dist_52w_low"), source="derived", basis="drawdown", as_of=as_of)

            if met.get("dist_200") is not None and met.get("dist_200") < -3.0:
                snapshot.add_warning("TREND_BREAKDOWN", f"{sym} 200 SMA 구조적 붕괴 ({met.get('dist_200'):+.2f}%)", ticker=sym, severity="warning")

            # Single stock beta calculation vs parent index
            if not sym.startswith("^") and sym not in ("SPY", "QQQ", "IWM", "DIA", "SMH"):
                b_sym = parent_index
                if not b_sym:
                    b_sym = "^KS11" if (sym.endswith(".KS") or sym.endswith(".KQ")) else "^GSPC"
                b_df = dataframes.get(b_sym)
                if b_df is not None:
                    stock_beta = mm.compute_stock_beta(df, b_df)
                    if stock_beta is not None:
                        snapshot.record(f"{sym}.beta_parent", stock_beta, source="derived", basis="relative_strength", as_of=as_of)

    # 4. Crisis benchmark evaluation (Tier 2 rolling crisis & Tier 3 historical tail-risk)
    crisis_dict: Dict[str, List[Dict[str, Any]]] = {}
    tier2_dict: Dict[str, Dict[str, Any]] = {}
    for idx_res in index_results:
        sym = idx_res.get("ticker", "")
        df = dataframes.get(sym)
        cur_close = idx_res.get("current_close", 0.0)
        if df is not None and cur_close > 0:
            as_of = idx_res.get("as_of")
            # Tier 2 dynamic rolling 1-year crisis benchmark
            t2 = mm.compute_rolling_crisis_benchmark(df, cur_close)
            tier2_dict[sym] = t2
            snapshot.record(f"{sym}.tier2.trough_date", t2.get("trough_date"), source="derived", basis="support_check", as_of=as_of)
            snapshot.record(f"{sym}.tier2.trough_price", t2.get("trough_price"), source="yahoo", basis="support_check", as_of=as_of)
            snapshot.record(f"{sym}.tier2.drawdown_pct", t2.get("drawdown_pct"), source="derived", basis="drawdown", as_of=as_of)
            snapshot.record(f"{sym}.tier2.buffer_pct", t2.get("buffer_pct"), source="derived", basis="support_check", as_of=as_of)
            snapshot.record(f"{sym}.tier2.breached", t2.get("breached"), source="derived", basis="support_check", as_of=as_of)

            # Tier 3 historical tail risk benchmarks
            is_kr_sym = sym.endswith(".KS") or sym.endswith(".KQ") or sym in ("^KS11", "^KQ11")
            c_evals = mm.evaluate_crisis_benchmarks(df, cur_close, is_korean=is_kr_sym)
            crisis_dict[sym] = c_evals
            for c in c_evals:
                cid = c.get("id")
                snapshot.record(f"{sym}.crisis.{cid}.low", c.get("crisis_low"), source="yahoo", basis="support_check")
                snapshot.record(f"{sym}.crisis.{cid}.breached", c.get("breached"), source="derived", basis="support_check")
                snapshot.record(f"{sym}.crisis.{cid}.buffer_pct", c.get("buffer_pct"), source="derived", basis="support_check")
                if c.get("crisis_low") is None and c.get("scope") != "KR":
                    snapshot.add_warning("CRISIS_BENCHMARK_MISSING", f"{sym}의 {c.get('name')} ({c.get('target_date')}) 데이터 범위 외", ticker=sym, severity="warning")

    # 5. Sector rotation
    sector_dfs = {s: dataframes.get(s) for s in (sectors or collect.DEFAULT_SECTORS) if s in dataframes}
    spy_df = dataframes.get(collect.BENCHMARK_ETF)
    rotation = mm.compute_sector_rotation(sector_dfs, spy_df=spy_df)

    snapshot.record("sectors.rotation.spread_5d", rotation.get("spread_5d"), source="derived", basis="spread")
    snapshot.record("sectors.rotation.spread_1m", rotation.get("spread_1m"), source="derived", basis="spread")
    snapshot.record("sectors.rotation.mean_cyclical_5d_rs", rotation.get("mean_cyclical_5d_rs"), source="derived", basis="spread")
    snapshot.record("sectors.rotation.mean_defensive_5d_rs", rotation.get("mean_defensive_5d_rs"), source="derived", basis="spread")
    for s in rotation.get("sectors", []):
        sym = s.get("ticker")
        snapshot.record(f"sector.{sym}.rs_5d", s.get("rs_5d"), source="derived", basis="relative_strength")
        snapshot.record(f"sector.{sym}.ret_5d", s.get("ret_5d"), source="derived", basis="relative_strength")

    # 6. Macro risk
    macro_dfs = {m: dataframes.get(m) for m in (macro or collect.DEFAULT_MACRO) if m in dataframes}
    macro_risk = mm.compute_macro_risk(macro_dfs)

    vix_info = macro_risk.get("vix", {})
    if vix_info.get("level") is not None:
        snapshot.record("macro.vix.level", vix_info.get("level"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.vix.signal", vix_info.get("signal"), source="derived", basis="macro_indicator")

    rate_info = macro_risk.get("rate_10y", {})
    if rate_info.get("yield") is not None:
        snapshot.record("macro.rate_10y.yield", rate_info.get("yield"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.rate_10y.bps_chg", rate_info.get("chg_5d_bps"), source="derived", basis="macro_indicator")
        snapshot.record("macro.rate_10y.signal", rate_info.get("signal"), source="derived", basis="macro_indicator")

    cr_info = macro_risk.get("credit", {})
    if cr_info.get("hy_oas_bps") is not None:
        snapshot.record("macro.credit.hy_oas_bps", cr_info.get("hy_oas_bps"), source="fred", basis="oas_spread")
        snapshot.record("macro.credit.bbb_oas_bps", cr_info.get("bbb_oas_bps"), source="fred", basis="oas_spread")
        snapshot.record("macro.credit.signal", cr_info.get("signal"), source="derived", basis="macro_indicator")
    elif cr_info.get("hyg_lqd_ratio") is not None:
        snapshot.record("macro.credit.ratio", cr_info.get("hyg_lqd_ratio"), source="derived", basis="macro_indicator")
        snapshot.record("macro.credit.rs_5d", cr_info.get("credit_rs_5d"), source="derived", basis="macro_indicator")
        snapshot.record("macro.credit.signal", cr_info.get("signal"), source="derived", basis="macro_indicator")

    dxy_info = macro_risk.get("dxy", {})
    if dxy_info.get("level") is not None:
        snapshot.record("macro.dxy.level", dxy_info.get("level"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.dxy.chg_5d_pct", dxy_info.get("chg_5d_pct"), source="derived", basis="macro_indicator")

    usd_info = macro_risk.get("usdkrw", {})
    if usd_info.get("rate") is not None:
        snapshot.record("macro.usdkrw.rate", usd_info.get("rate"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.usdkrw.chg_5d_pts", usd_info.get("chg_5d_pts"), source="derived", basis="macro_indicator")
        snapshot.record("macro.usdkrw.chg_5d_pct", usd_info.get("chg_5d_pct"), source="derived", basis="macro_indicator")
        snapshot.record("macro.usdkrw.signal", usd_info.get("signal"), source="derived", basis="macro_indicator")

    oil_info = macro_risk.get("crude_oil", {})
    if oil_info.get("price") is not None:
        snapshot.record("macro.crude_oil.price", oil_info.get("price"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.crude_oil.chg_5d_pct", oil_info.get("chg_5d_pct"), source="derived", basis="macro_indicator")

    gold_info = macro_risk.get("gold", {})
    if gold_info.get("price") is not None:
        snapshot.record("macro.gold.price", gold_info.get("price"), source="yahoo", basis="macro_indicator")
        snapshot.record("macro.gold.chg_5d_pct", gold_info.get("chg_5d_pct"), source="derived", basis="macro_indicator")

    # 7. Trend evaluation & Market Regime synthesis
    primary_sym = primary_ticker
    if not primary_sym:
        for pref in ["^GSPC", "^KS11", "^NDX", "^SOX"]:
            if any(m.get("ticker") == pref for m in index_results):
                primary_sym = pref
                break
    if not primary_sym and index_results:
        primary_sym = index_results[0].get("ticker")

    primary_crisis = crisis_dict.get(primary_sym, [])
    primary_t2 = tier2_dict.get(primary_sym, {})
    trend_eval = mr.evaluate_trend_signal(index_results, primary_crisis, primary_ticker=primary_sym, tier2_eval=primary_t2)
    regime = mr.evaluate_market_regime(trend_eval, macro_risk, rotation, index_metrics=index_results)
    regime["evaluated_name"] = trend_eval.get("evaluated_name") or "S&P 500"

    snapshot.record("macro.regime.verdict", regime.get("name"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.cash_pct", regime.get("cash_pct"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.equity_pct", regime.get("equity_pct"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.safe_pct", regime.get("safe_pct"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.icon", regime.get("icon"), source="derived", basis="regime_matrix")

    # Record 5 pillar signals explicitly
    snapshot.record("macro.regime.pillar.trend", trend_eval.get("signal"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.pillar.vix", vix_info.get("signal"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.pillar.rates", rate_info.get("signal"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.pillar.credit", cr_info.get("signal"), source="derived", basis="regime_matrix")
    snapshot.record("macro.regime.pillar.breadth", rotation.get("signal"), source="derived", basis="regime_matrix")

    # 8. Socratic Auditor & Biases
    primary_met = next((m for m in index_results if m.get("ticker") == primary_sym), index_results[0] if index_results else {})
    biases = sa.audit_cognitive_biases(primary_met, macro_risk, trend_eval)
    for b in biases:
        b_key = b.get("bias", "").split()[0]
        snapshot.record(f"socratic.bias.{b_key}.triggered", b.get("triggered"), source="derived", basis="socratic_rule")

    ladder = sa.build_thesis_invalidation_ladder(primary_met, macro_risk, primary_crisis, tier2_eval=primary_t2)

    # 9. Format Markdown tables
    section4_text = format_tables_section(
        index_results,
        crisis_dict,
        rotation,
        macro_risk,
        regime,
        biases,
        ladder,
        snapshot,
        as_of_str=effective_as_of,
        tier2_dict=tier2_dict,
    )

    # 10. Save snapshot if requested
    if snapshot_path:
        meta_args = {
            "indices": target_indices,
            "sectors": list(sector_dfs.keys()),
            "macro": list(macro_dfs.keys()),
            "primary_ticker": primary_sym,
            "parent_index": parent_index,
        }
        snapshot.save(snapshot_path, meta_args=meta_args, inputs=raw_items, generated_at=effective_as_of)

    return section4_text, snapshot


def main():
    parser = argparse.ArgumentParser(description="Market Analyst quantitative metrics engine")
    parser.add_argument("--indices", type=str, default="^GSPC,^NDX,^DJI,^RUT,^SOX", help="Comma-separated index tickers")
    parser.add_argument("--sectors", type=str, default="", help="Comma-separated sector tickers (default: 11 SPDR ETFs)")
    parser.add_argument("--macro", type=str, default="", help="Comma-separated macro tickers")
    parser.add_argument("--include-global", action="store_true", help="Include KOSPI, KOSDAQ, Nikkei 225")
    parser.add_argument("--snapshot", type=str, default="", help="Output path for snapshot JSON")
    parser.add_argument("--from-snapshot", type=str, default="", help="Rebuild metrics from existing snapshot inputs without network")
    parser.add_argument("--format", type=str, choices=["tables", "json"], default="tables", help="Output format")

    args = parser.parse_args()

    indices = [s.strip() for s in args.indices.split(",") if s.strip()]
    sectors = [s.strip() for s in args.sectors.split(",") if s.strip()] if args.sectors else None
    macro = [s.strip() for s in args.macro.split(",") if s.strip()] if args.macro else None

    sec4, snapshot = run_market_analysis(
        indices=indices,
        sectors=sectors,
        macro=macro,
        include_global=args.include_global,
        snapshot_path=args.snapshot if args.snapshot else None,
        from_snapshot=args.from_snapshot if args.from_snapshot else None,
    )

    if args.format == "tables":
        print(sec4)
    else:
        print(json.dumps(snapshot.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
