#!/usr/bin/env python3
"""
calculate_alpha_score.py
Alpha Engine: 4-Archetype Forward-Looking Alpha Scoring Script
Evaluates:
  1. Supercycle Leader (실적 폭발 주도주)
  2. Turnaround Inflection (바닥 탈출 턴어라운드)
  3. Catalyst Event-Driven (확정 D-Day 및 어닝 서프라이즈 촉매)
  4. Momentum Breakout (52주 신고가 & 벤치마크 초과 상대강도 RS)
Outputs Dual Scores (Alpha Score vs Defense Score) and an Action Verdict.
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

try:
    import numpy as np
    import pandas as pd
    import yfinance as yf
except ImportError as e:
    sys.stderr.write(f"Error importing dependencies: {e}\n")
    sys.exit(1)


def is_korean_stock(ticker: str) -> bool:
    t = ticker.upper()
    return t.endswith(".KS") or t.endswith(".KQ") or (len(t) == 6 and t.isdigit())


def get_benchmark_ticker(target_ticker: str) -> str:
    if is_korean_stock(target_ticker):
        return "^KS11"
    return "^GSPC"


def fetch_toss_stock_data(symbol: str, count: int = 200) -> Tuple[Optional[float], Optional[pd.DataFrame]]:
    """Attempts to fetch real-time price and daily candles for Korean stocks via Toss MCP."""
    clean_code = symbol.split('.')[0]
    if not (len(clean_code) == 6 and clean_code.isdigit()):
        return None, None
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fa_dir = os.path.abspath(os.path.join(script_dir, "../../financial-analyst/scripts"))
        if fa_dir not in sys.path:
            sys.path.insert(0, fa_dir)
        import mcp_client

        # 1. Real-time price
        p_res = mcp_client.call_mcp("toss", "toss_stock_prices", {"symbols": [clean_code]}, timeout=5)
        price = None
        if p_res and isinstance(p_res, list) and len(p_res) > 0:
            lp = p_res[0].get("lastPrice")
            if lp is not None:
                price = float(lp)

        # 2. Daily candles
        c_res = mcp_client.call_mcp("toss", "toss_stock_candles", {"symbol": clean_code, "count": count, "interval": "1d"}, timeout=8)
        df = None
        if c_res and isinstance(c_res, dict) and "candles" in c_res:
            records = []
            for c in reversed(c_res["candles"]):
                records.append({
                    'Date': pd.to_datetime(c.get("timestamp")),
                    'Open': float(c.get("openPrice", 0)),
                    'High': float(c.get("highPrice", 0)),
                    'Low': float(c.get("lowPrice", 0)),
                    'Close': float(c.get("closePrice", 0)),
                    'Volume': float(c.get("volume", 0)),
                })
            if records:
                df = pd.DataFrame(records).set_index('Date')

        return price, df
    except Exception:
        return None, None


def fetch_toss_benchmark_data(market: str = "KOSPI", count: int = 200) -> Optional[pd.DataFrame]:
    """Fetches KOSPI/KOSDAQ daily candles via Toss MCP."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fa_dir = os.path.abspath(os.path.join(script_dir, "../../financial-analyst/scripts"))
        if fa_dir not in sys.path:
            sys.path.insert(0, fa_dir)
        import mcp_client

        sym = "KOSDAQ" if ("KQ" in market.upper() or "KOSDAQ" in market.upper()) else "KOSPI"
        res = mcp_client.call_mcp("toss", "toss_market_indicator_candles", {"symbol": sym, "count": count, "interval": "1d"}, timeout=8)
        if res and isinstance(res, dict) and "candles" in res:
            records = []
            for c in reversed(res["candles"]):
                records.append({
                    'Date': pd.to_datetime(c.get("timestamp")),
                    'Open': float(c.get("openPrice", 0)),
                    'High': float(c.get("highPrice", 0)),
                    'Low': float(c.get("lowPrice", 0)),
                    'Close': float(c.get("closePrice", 0)),
                    'Volume': float(c.get("volume", 0)),
                })
            if records:
                return pd.DataFrame(records).set_index('Date')
    except Exception:
        pass
    return None


def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def compute_relative_strength(stock_df: pd.DataFrame, bench_df: pd.DataFrame, days: int = 60) -> float:
    """
    Computes Relative Strength (RS) over `days` trading days vs benchmark index.
    Returns percentile-like score (0 to 100).
    """
    try:
        if stock_df.empty or bench_df.empty or len(stock_df) < days or len(bench_df) < days:
            return 50.0

        stock_close = stock_df['Close'].dropna()
        bench_close = bench_df['Close'].dropna()

        stock_ret = (stock_close.iloc[-1] / stock_close.iloc[-days] - 1.0)
        bench_ret = (bench_close.iloc[-1] / bench_close.iloc[-days] - 1.0)

        # Alpha excess return over benchmark
        excess = stock_ret - bench_ret

        # Convert excess return to 0-100 RS scale:
        # +30% excess -> 95, 0% excess -> 50, -30% excess -> 5
        rs_score = 50.0 + (excess * 150.0)
        return float(np.clip(rs_score, 0.0, 100.0))
    except Exception:
        return 50.0


def evaluate_alpha(ticker: str) -> Dict[str, Any]:
    norm_ticker = ticker.upper()
    if len(norm_ticker) == 6 and norm_ticker.isdigit():
        norm_ticker = f"{norm_ticker}.KS"

    bench_ticker = get_benchmark_ticker(norm_ticker)

    # 1. Fetch live stock and benchmark data
    stk = yf.Ticker(norm_ticker)
    info = stk.info or {}

    current_price = None
    hist = pd.DataFrame()
    bench_hist = pd.DataFrame()

    # Prioritize Toss MCP for Korean stocks (eliminates Yahoo 1-day lag, missing dates, volume spikes)
    if is_korean_stock(norm_ticker):
        toss_p, toss_df = fetch_toss_stock_data(norm_ticker, count=200)
        if toss_p is not None and toss_p > 0:
            current_price = toss_p
        if toss_df is not None and not toss_df.empty:
            hist = toss_df

        toss_bench_df = fetch_toss_benchmark_data(bench_ticker, count=200)
        if toss_bench_df is not None and not toss_bench_df.empty:
            bench_hist = toss_bench_df

    # Fallback to Yahoo if Toss is unavailable or ticker is non-KR
    if hist.empty:
        try:
            hist = stk.history(period="1y")
        except Exception:
            hist = pd.DataFrame()

    if bench_hist.empty:
        try:
            bench = yf.Ticker(bench_ticker)
            bench_hist = bench.history(period="1y")
        except Exception:
            bench_hist = pd.DataFrame()

    if current_price is None or current_price <= 0:
        current_price = safe_float(info.get('currentPrice') or info.get('regularMarketPrice'))
        if current_price <= 0 and not hist.empty:
            current_price = float(hist['Close'].iloc[-1])

    high_52w = safe_float(info.get('fiftyTwoWeekHigh'))
    low_52w = safe_float(info.get('fiftyTwoWeekLow'))
    if not hist.empty:
        if 'High' in hist.columns and (high_52w <= 0 or is_korean_stock(norm_ticker)):
            high_52w = float(hist['High'].max())
        elif high_52w <= 0:
            high_52w = float(hist['Close'].max())

        if 'Low' in hist.columns and (low_52w <= 0 or is_korean_stock(norm_ticker)):
            low_52w = float(hist['Low'].min())
        elif low_52w <= 0:
            low_52w = float(hist['Close'].min())

    rev_growth = safe_float(info.get('revenueGrowth'))  # e.g., 0.35 for 35%
    op_margin = safe_float(info.get('operatingMargins'))  # e.g., 0.25 for 25%
    gross_margin = safe_float(info.get('grossMargins'))
    forward_pe = safe_float(info.get('forwardPE'))
    peg_ratio = safe_float(info.get('pegRatio'))
    target_mean = safe_float(info.get('targetMeanPrice'))
    debt_to_equity = safe_float(info.get('debtToEquity'))  # e.g. 45 for 45%
    fcf = safe_float(info.get('freeCashflow'))

    # =========================================================================
    # 1. TYPE 1: SUPERCYCLE LEADER (실적 폭발 주도주) - 100 pts max
    # =========================================================================
    sc_pts = 0.0

    # 1.1 Revenue YoY Growth (max 30 pts)
    if rev_growth >= 0.50:
        sc_pts += 30.0
    elif rev_growth >= 0.25:
        sc_pts += 22.0
    elif rev_growth >= 0.15:
        sc_pts += 15.0
    elif rev_growth >= 0.05:
        sc_pts += 8.0

    # 1.2 Operating Margin & Expansion (max 30 pts)
    # Recognize supercycle margins instead of penalizing them
    if op_margin >= 0.40:
        sc_pts += 30.0
    elif op_margin >= 0.25:
        sc_pts += 24.0
    elif op_margin >= 0.15:
        sc_pts += 16.0
    elif op_margin >= 0.08:
        sc_pts += 8.0

    # 1.3 Gross Margin Moat / Pricing Power (max 20 pts)
    if gross_margin >= 0.60:
        sc_pts += 20.0
    elif gross_margin >= 0.45:
        sc_pts += 15.0
    elif gross_margin >= 0.30:
        sc_pts += 10.0
    elif gross_margin >= 0.15:
        sc_pts += 5.0

    # 1.4 PEG / Valuation Expansion Room (max 20 pts)
    if 0.1 <= peg_ratio <= 1.2:
        sc_pts += 20.0
    elif 1.2 < peg_ratio <= 1.8:
        sc_pts += 14.0
    elif peg_ratio <= 0 and rev_growth > 0.30:  # Hypergrowth proxy
        sc_pts += 15.0
    elif forward_pe > 0 and forward_pe < 25:
        sc_pts += 12.0

    supercycle_score = min(100.0, sc_pts)

    # =========================================================================
    # 2. TYPE 2: TURNAROUND INFLECTION (바닥 탈출 턴어라운드) - 100 pts max
    # =========================================================================
    turn_pts = 0.0

    # 2.1 Margin Inflection / Low Base (max 35 pts)
    # Check if recovering from low margin or negative
    if 0.01 <= op_margin <= 0.12 and rev_growth > 0.10:
        turn_pts += 35.0  # Classic margin turnaround from thin margin
    elif -0.05 <= op_margin < 0.01 and rev_growth > 0.15:
        turn_pts += 30.0  # On the cusp of breaking even
    elif op_margin > 0.12 and rev_growth > 0.20:
        turn_pts += 20.0

    # 2.2 Trough Price Support: Distance from 52W Low (max 25 pts)
    # Ideal turnaround entry: 10% to 35% above 52W low (bounced off bottom)
    if low_52w > 0 and current_price > 0:
        pct_from_low = (current_price - low_52w) / low_52w
        if 0.05 <= pct_from_low <= 0.30:
            turn_pts += 25.0
        elif 0.30 < pct_from_low <= 0.50:
            turn_pts += 18.0
        elif pct_from_low < 0.05:
            turn_pts += 12.0  # Still probing floor
        else:
            turn_pts += 5.0

    # 2.3 Solvency for Survival (max 20 pts)
    if debt_to_equity > 0:
        if debt_to_equity < 80.0:
            turn_pts += 20.0
        elif debt_to_equity < 150.0:
            turn_pts += 12.0
        else:
            turn_pts += 4.0
    else:
        turn_pts += 12.0

    # 2.4 Consensus Revision / Recommendation (max 20 pts)
    rec = str(info.get('recommendationKey') or "").lower()
    if 'buy' in rec:
        turn_pts += 20.0
    elif 'hold' in rec:
        turn_pts += 10.0
    else:
        turn_pts += 5.0

    turnaround_score = min(100.0, turn_pts)

    # =========================================================================
    # 3. TYPE 3: CATALYST EVENT-DRIVEN (확정 D-Day 및 촉매) - 100 pts max
    # =========================================================================
    cat_pts = 0.0

    # 3.1 Implied Upside to Analyst Target (max 30 pts)
    # Upside indicated by consensus target price, reinforced by buy conviction
    implied_upside = 0.0
    rec = str(info.get('recommendationKey') or "").lower()
    if target_mean > 0 and current_price > 0:
        implied_upside = (target_mean - current_price) / current_price
        if implied_upside >= 0.40:
            cat_pts += 30.0 if ('buy' in rec) else 15.0
        elif implied_upside >= 0.25:
            cat_pts += 22.0 if ('buy' in rec) else 12.0
        elif implied_upside >= 0.15:
            cat_pts += 15.0
        elif implied_upside >= 0.05:
            cat_pts += 8.0

    # 3.2 Earnings / Event Catalyst Proximity Window (max 35 pts)
    # Only award points if there is a verified upcoming earnings/event within an imminent catalyst window
    cal = getattr(stk, 'calendar', None)
    earnings_dates = cal.get('Earnings Date') if isinstance(cal, dict) else None
    days_to_earnings = None
    if earnings_dates and len(earnings_dates) > 0:
        ed = earnings_dates[0]
        if hasattr(ed, 'date'):
            ed = ed.date()
        today = datetime.now().date()
        if isinstance(ed, datetime):
            ed = ed.date()
        try:
            days_to_earnings = (ed - today).days
        except Exception:
            days_to_earnings = None

    if days_to_earnings is not None and 0 <= days_to_earnings <= 35:
        cat_pts += 35.0  # Immediate catalyst window (within 5 weeks)
    elif days_to_earnings is not None and 35 < days_to_earnings <= 60:
        cat_pts += 20.0
    elif days_to_earnings is not None and 60 < days_to_earnings <= 90:
        cat_pts += 10.0
    else:
        cat_pts += 0.0  # Far away (>90 days) or unknown: no free points

    # 3.3 Analyst Quality & Upgrade Momentum (max 35 pts)
    num_analysts = safe_float(info.get('numberOfAnalystOpinions'))
    if 'strong_buy' in rec:
        cat_pts += 25.0
    elif 'buy' in rec:
        cat_pts += 18.0
    elif 'hold' in rec:
        cat_pts += 5.0
    else:
        cat_pts += 0.0

    if 'buy' in rec:
        if num_analysts >= 20:
            cat_pts += 10.0
        elif num_analysts >= 10:
            cat_pts += 5.0

    catalyst_score = min(100.0, cat_pts)

    # =========================================================================
    # 4. TYPE 4: MOMENTUM BREAKOUT (52주 신고가 & 수급 상대강도) - 100 pts max
    # =========================================================================
    mom_pts = 0.0

    # 4.1 52W High Proximity (max 30 pts)
    pct_from_high = 0.0
    if high_52w > 0 and current_price > 0:
        pct_from_high = (current_price - high_52w) / high_52w
        if -0.05 <= pct_from_high <= 0.02:
            mom_pts += 30.0  # Right at the breakout door
        elif -0.12 <= pct_from_high < -0.05:
            mom_pts += 22.0
        elif -0.20 <= pct_from_high < -0.12:
            mom_pts += 15.0
        else:
            mom_pts += 5.0

    # 4.2 Relative Strength (RS) vs Benchmark (max 35 pts)
    rs_val = compute_relative_strength(hist, bench_hist, days=60)
    if rs_val >= 80.0:
        mom_pts += 35.0
    elif rs_val >= 65.0:
        mom_pts += 26.0
    elif rs_val >= 50.0:
        mom_pts += 18.0
    else:
        mom_pts += 5.0

    # 4.3 Moving Average Posture (max 20 pts)
    if len(hist) >= 200:
        sma50 = hist['Close'].rolling(50).mean().iloc[-1]
        sma200 = hist['Close'].rolling(200).mean().iloc[-1]
        last_close = hist['Close'].iloc[-1]
        if last_close > sma50 > sma200:
            mom_pts += 20.0  # Perfect bullish alignment
        elif last_close > sma200:
            mom_pts += 12.0
        else:
            mom_pts += 4.0
    elif len(hist) >= 50:
        sma50 = hist['Close'].rolling(50).mean().iloc[-1]
        if hist['Close'].iloc[-1] > sma50:
            mom_pts += 15.0

    # 4.4 Volume Expansion (max 15 pts)
    if len(hist) >= 20:
        recent_vol = hist['Volume'].iloc[-5:].mean()
        avg_vol = hist['Volume'].iloc[-20:].mean()
        if avg_vol > 0:
            vol_ratio = recent_vol / avg_vol
            if vol_ratio >= 1.5:
                mom_pts += 15.0
            elif vol_ratio >= 1.1:
                mom_pts += 10.0
            else:
                mom_pts += 5.0

    momentum_score = min(100.0, mom_pts)

    # =========================================================================
    # 5. DEFENSE SCORE (하방 방어 안전 점수) - 100 pts max
    # =========================================================================
    def_pts = 0.0

    # Financial health (Debt/Equity < 100%) -> 30 pts
    if debt_to_equity < 80:
        def_pts += 30.0
    elif debt_to_equity < 150:
        def_pts += 20.0
    else:
        def_pts += 10.0

    # Positive Cash Flow -> 25 pts
    if fcf > 0:
        def_pts += 25.0
    elif op_margin > 0.10:
        def_pts += 15.0

    # Max Drawdown health (not collapsed > -60%) -> 25 pts
    if pct_from_high >= -0.25:
        def_pts += 25.0
    elif pct_from_high >= -0.45:
        def_pts += 15.0
    else:
        def_pts += 5.0

    # Beta stability -> 20 pts
    beta = safe_float(info.get('beta'), default=1.0)
    if 0.5 <= beta <= 1.5:
        def_pts += 20.0
    elif beta <= 2.2:
        def_pts += 12.0
    else:
        def_pts += 5.0

    defense_score = min(100.0, def_pts)

    # =========================================================================
    # 6. ARCHETYPE RESOLUTION & COMPOSITE ALPHA SCORE
    # =========================================================================
    scores = {
        'SUPERCYCLE_LEADER': supercycle_score,
        'TURNAROUND_INFLECTION': turnaround_score,
        'CATALYST_EVENT': catalyst_score,
        'MOMENTUM_BREAKOUT': momentum_score,
    }

    # Structural Archetype Priority Resolution:
    # 1. Supercycle priority: if supercycle_score >= 80, structural expansion dominates
    # 2. Turnaround priority: if turnaround_score >= 75 and severely beaten down, turnaround inflection dominates
    # 3. Momentum priority: if momentum_score >= 80 and near breakout, momentum dominates
    # 4. Otherwise, max score
    highest_score = max(scores.values())
    if supercycle_score >= 80.0 and supercycle_score >= (highest_score - 8.0):
        primary_archetype = 'SUPERCYCLE_LEADER'
    elif turnaround_score >= 75.0 and turnaround_score >= (highest_score - 8.0):
        primary_archetype = 'TURNAROUND_INFLECTION'
    elif momentum_score >= 80.0 and momentum_score >= (highest_score - 8.0):
        primary_archetype = 'MOMENTUM_BREAKOUT'
    else:
        primary_archetype = max(scores, key=scores.get)

    max_alpha = scores[primary_archetype]

    # Composite Alpha: 60% highest engine + 40% average of other engines
    other_avg = (sum(scores.values()) - max_alpha) / 3.0
    composite_alpha = (max_alpha * 0.60) + (other_avg * 0.40)

    # =========================================================================
    # 7. DUAL VERDICT SYNTHESIS
    # =========================================================================
    if composite_alpha >= 80.0:
        if defense_score >= 65.0:
            verdict = "🟢 강력 매수 (Top Pick 주도주)"
            action = "적극 비중 확대 (포트폴리오 35~40%), 50일선 트레일링 스탑 적용"
        else:
            verdict = "🟢 적극 매수 (변동성 분할 진입)"
            action = "비중 25~30% 편입, 조정 시 Tier 2 지지선 분할 매수"
    elif composite_alpha >= 65.0:
        if defense_score >= 65.0:
            verdict = "🟢 안정 매수 (실적 가치 성장주)"
            action = "비중 20~25% 편입, 중장기 호라이즌 보유"
        else:
            verdict = "🟡 조건부 매수 (촉매 확인 후 진입)"
            action = "비중 15% 진입, 확정 촉매 D-Day 발표 시 추가 매수"
    elif composite_alpha >= 50.0:
        verdict = "🟡 중립/관망 (알파 모멘텀 부족)"
        action = "신규 매수 보류, 턴어라운드/수급 변곡점 확인 시 재평가"
    else:
        verdict = "🔴 매수 기피 (상승 동력 결핍)"
        action = "현금 확보 또는 다른 주도주 교체 매매"

    if defense_score < 35.0:
        verdict = "🚨 매수 보류 (재무/변동성 경보)"
        action = "타겟 비중 0% 동결, 밸류 트랩 및 급락 리스크 점검"

    archetype_labels = {
        'SUPERCYCLE_LEADER': '🚀 슈퍼사이클 & 실적 폭발 주도주',
        'TURNAROUND_INFLECTION': '🔄 바닥 탈출 턴어라운드주',
        'CATALYST_EVENT': '📅 확정 D-Day 및 촉매주',
        'MOMENTUM_BREAKOUT': '⚡ 신고가 & 수급 돌파 모멘텀주',
    }

    return {
        'ticker': norm_ticker,
        'company_name': info.get('shortName') or norm_ticker,
        'current_price': current_price,
        'currency': info.get('currency', 'KRW' if is_korean_stock(norm_ticker) else 'USD'),
        'primary_archetype': primary_archetype,
        'primary_label': archetype_labels.get(primary_archetype, primary_archetype),
        'composite_alpha_score': round(composite_alpha, 1),
        'defense_score': round(defense_score, 1),
        'scores': {
            'supercycle': round(supercycle_score, 1),
            'turnaround': round(turnaround_score, 1),
            'catalyst': round(catalyst_score, 1),
            'momentum': round(momentum_score, 1),
        },
        'dual_verdict': verdict,
        'recommended_action': action,
        'metrics': {
            'revenue_growth_yoy': f"{round(rev_growth * 100, 1)}%",
            'operating_margin': f"{round(op_margin * 100, 1)}%",
            'gross_margin': f"{round(gross_margin * 100, 1)}%",
            'peg_ratio': round(peg_ratio, 2) if peg_ratio else 'N/A',
            'forward_pe': round(forward_pe, 1) if forward_pe else 'N/A',
            'relative_strength_rs': round(rs_val, 1),
            'dist_from_52w_high': f"{round(pct_from_high * 100, 1)}%",
            'implied_upside': f"{round(implied_upside * 100, 1)}%",
        },
        'evaluated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
    }


def format_card(res: Dict[str, Any]) -> str:
    m = res['metrics']
    s = res['scores']
    cur = res['currency']
    p = f"{res['current_price']:,} {cur}"

    md = []
    md.append(f"### 🎯 [{res['company_name']} ({res['ticker']})] 미래 알파(Alpha) 정밀 진단")
    md.append(f"> **현재가**: {p} | **평가 시각**: {res['evaluated_at']}")
    md.append(f"> **주요 상승 동력 (Primary Archetype)**: **{res['primary_label']}**")
    md.append(f"> **종합 판단**: **{res['dual_verdict']}** — *{res['recommended_action']}*\n")

    md.append("#### 📊 듀얼 스코어보드 (Dual Scoreboard)")
    md.append("| 평가 축 | 점수 (0~100) | 상태 신호 | 핵심 해석 |")
    md.append("|---|:---:|:---:|---|")

    alpha_sig = "🟢 최상위" if res['composite_alpha_score'] >= 80 else ("🟡 양호" if res['composite_alpha_score'] >= 65 else "⚪ 보통")
    def_sig = "🛡️ 견고" if res['defense_score'] >= 65 else ("⚠️ 보통" if res['defense_score'] >= 50 else "🚨 취약")

    md.append(f"| **공격 알파 (Alpha Score)** | **{res['composite_alpha_score']}점** | {alpha_sig} | 미래 주가 상승 잠재력 및 초과이익 동력 |")
    md.append(f"| **하방 방어 (Defense Score)** | **{res['defense_score']}점** | {def_sig} | 재무 안정성 및 하방 경직성 안전마진 |")

    md.append("\n#### 🔬 4대 동적 알파 엔진별 세부 점수")
    md.append("| 엔진 유형 | 점수 | 핵심 입력 지표 (P×Q / 모멘텀) |")
    md.append("|---|:---:|---|")
    md.append(f"| 🚀 **슈퍼사이클 주도주** | **{s['supercycle']}점** | 매출 성장률 {m['revenue_growth_yoy']}, OPM {m['operating_margin']}, GPM {m['gross_margin']} |")
    md.append(f"| 🔄 **바닥 탈출 턴어라운드** | **{s['turnaround']}점** | 52주 고점 대비 {m['dist_from_52w_high']}, PEG {m['peg_ratio']} |")
    md.append(f"| 📅 **확정 D-Day 및 촉매** | **{s['catalyst']}점** | 컨센서스 상승 여력 {m['implied_upside']}, Forward PE {m['forward_pe']}배 |")
    md.append(f"| ⚡ **신고가 & 수급 모멘텀** | **{s['momentum']}점** | 시장 대비 상대강도 RS **{m['relative_strength_rs']}점**, 신고가 이격도 {m['dist_from_52w_high']} |")

    return "\n".join(md)


def format_alpha_section_table(results_list: list) -> str:
    """Formats Section 4.3 summary table for investment-strategy reports."""
    lines = [
        "| 기업명 | 티커 | 주요 상승 동력 (Archetype) | 공격 알파 점수 | 하방 방어 점수 | 종합 듀얼 판정 | 핵심 견인 지표 (P×Q / 모멘텀) |",
        "|---|:---:|---|:---:|:---:|:---:|---|"
    ]
    for r in results_list:
        m = r['metrics']
        lines.append(
            f"| **{r['company_name']}** | `{r['ticker']}` | {r['primary_label']} | "
            f"**{r['composite_alpha_score']}점** | **{r['defense_score']}점** | "
            f"{r['dual_verdict'].split('(')[0].strip()} | "
            f"매출 YoY {m['revenue_growth_yoy']}, OPM {m['operating_margin']}, RS {m['relative_strength_rs']}점 |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Alpha Engine Scoring Prototype")
    parser.add_argument("--ticker", required=True, help="Stock ticker (e.g. 000660.KS, NVDA)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    args = parser.parse_args()

    result = evaluate_alpha(args.ticker)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_card(result))


if __name__ == "__main__":
    main()
