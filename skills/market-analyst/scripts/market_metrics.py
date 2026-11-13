"""
Market analytics calculation engine:
Computes drawdowns, moving averages, historical crisis support benchmarks,
sector rotation relative strength, and macro risk indicators.
"""

import datetime
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

CRISIS_BENCHMARKS = [
    {
        "id": "yen_carry_20240805",
        "name": "엔캐리 청산 쇼크 (블랙 먼데이)",
        "target_date": "2024-08-05",
        "scope": "GLOBAL",
        "description": "2024-08-05 엔캐리 언와인딩 및 글로벌 마진콜 급락 저점",
    },
    {
        "id": "iran_war_20240419",
        "name": "이란-이스라엘 1차 공습 저점",
        "target_date": "2024-04-19",
        "scope": "GLOBAL",
        "description": "2024-04-19 중동 확전 공포 및 1차 군사 충돌 당시 저점",
    },
    {
        "id": "iran_war_20241001",
        "name": "이란-이스라엘 2차 공습 저점",
        "target_date": "2024-10-01",
        "scope": "GLOBAL",
        "description": "2024-10-01 이란 미사일 발사 및 유가 급등 당시 저점",
    },
    {
        "id": "martial_law_20241203",
        "name": "12.3 비상계엄 선포 쇼크",
        "target_date": "2024-12-03",
        "scope": "KR",
        "description": "2024-12-03 비상계엄 선포 및 외환·금융시장 단기 패닉 저점",
    },
]

CYCLICAL_SECTORS = ['XLK', 'XLC', 'XLY', 'XLI', 'XLF', 'XLB']
DEFENSIVE_SECTORS = ['XLP', 'XLU', 'XLV']
COMMODITY_SECTORS = ['XLE', 'XLRE']

INDEX_NAMES = {
    '^GSPC': 'S&P 500',
    '^NDX': '나스닥 100 (Nasdaq 100)',
    '^DJI': '다우존스 산업평균 (Dow Jones)',
    '^RUT': '러셀 2000 (Russell 2000)',
    '^SOX': '필라델피아 반도체 (PHLX Semi)',
    '^KS11': '코스피 (KOSPI)',
    '^KQ11': '코스닥 (KOSDAQ)',
    '^N225': '닛케이 225 (Nikkei 225)',
    '005930.KS': '삼성전자 (Samsung Electronics)',
    '066570.KS': 'LG전자 (LG Electronics)',
    '000660.KS': 'SK하이닉스 (SK Hynix)',
    'TSLA': '테슬라 (Tesla)',
    'NVDA': '엔비디아 (NVIDIA)',
    'TSM': 'TSMC (TSM)',
    'AAPL': '애플 (Apple)',
    'MSFT': '마이크로소프트 (Microsoft)',
    'GOOGL': '알파벳 (Alphabet)',
    'AMZN': '아마존 (Amazon)',
    'META': '메타 (Meta Platforms)',
    'AMD': 'AMD (Advanced Micro Devices)',
    '005380.KS': '현대차 (Hyundai Motor)',
    '000270.KS': '기아 (Kia)',
    '035420.KS': 'NAVER (Naver)',
    '035720.KS': '카카오 (Kakao)',
    'SMH': '반도체 ETF (VanEck Semi ETF)',
    'USDKRW=X': '원/달러 환율 (USD/KRW)',
}

SECTOR_NAMES = {
    'XLK': '기술 (Technology)',
    'XLC': '통신서비스 (Communication)',
    'XLY': '경기소비재 (Cons Discretionary)',
    'XLI': '산업재 (Industrials)',
    'XLF': '금융 (Financials)',
    'XLV': '헬스케어 (Health Care)',
    'XLE': '에너지 (Energy)',
    'XLP': '필수소비재 (Cons Staples)',
    'XLU': '유틸리티 (Utilities)',
    'XLRE': '부동산 (Real Estate)',
    'XLB': '소재 (Materials)',
    'SPY': 'S&P 500 ETF (SPY)',
}


def _safe_pct_change(current: float, base: float) -> Optional[float]:
    if base is None or base == 0 or np.isnan(base) or np.isnan(current):
        return None
    return round(float((current - base) / base * 100.0), 2)


def compute_index_metrics(df: pd.DataFrame, ticker: str = "") -> Dict[str, Any]:
    """
    Compute price metrics: 1D, 5D, 1M, 3M, YTD returns, 52W High/Low, MDD, 20 EMA, 50 SMA, 200 SMA.
    """
    if df is None or df.empty or "Close" not in df.columns:
        return {"ticker": ticker, "status": "error", "error": "Empty data"}

    close_raw = df["Close"]
    close_s = close_raw.squeeze().dropna() if isinstance(close_raw, pd.DataFrame) else close_raw.dropna()
    if len(close_s) < 2:
        return {"ticker": ticker, "status": "error", "error": "Insufficient bars"}

    current_close = float(close_s.iloc[-1])
    prev_close = float(close_s.iloc[-2])
    last_idx = close_s.index[-1]
    as_of = last_idx.strftime("%Y-%m-%d") if hasattr(last_idx, "strftime") else str(last_idx)[:10]

    ret_1d = _safe_pct_change(current_close, prev_close)
    ret_5d = _safe_pct_change(current_close, float(close_s.iloc[-6])) if len(close_s) >= 6 else _safe_pct_change(current_close, float(close_s.iloc[0]))
    ret_1m = _safe_pct_change(current_close, float(close_s.iloc[-22])) if len(close_s) >= 22 else None
    ret_3m = _safe_pct_change(current_close, float(close_s.iloc[-64])) if len(close_s) >= 64 else None

    # YTD return
    current_year = close_s.index[-1].year
    ytd_bars = close_s[close_s.index.year == current_year]
    ret_ytd = _safe_pct_change(current_close, float(ytd_bars.iloc[0])) if not ytd_bars.empty else None

    # 52-week High / Low (up to 252 bars)
    w52_bars = df.iloc[-252:] if len(df) >= 252 else df
    high_raw = w52_bars["High"] if "High" in w52_bars.columns else close_s.iloc[-252:]
    high_s = high_raw.squeeze().dropna() if isinstance(high_raw, pd.DataFrame) else high_raw.dropna()
    low_raw = w52_bars["Low"] if "Low" in w52_bars.columns else close_s.iloc[-252:]
    low_s = low_raw.squeeze().dropna() if isinstance(low_raw, pd.DataFrame) else low_raw.dropna()

    w52_high = float(high_s.max()) if not high_s.empty else current_close
    w52_low = float(low_s.min()) if not low_s.empty else current_close
    drawdown_52w = _safe_pct_change(current_close, w52_high)

    # Moving Averages
    ema_20 = float(close_s.ewm(span=20, adjust=False).mean().iloc[-1]) if len(close_s) >= 20 else None
    sma_50 = float(close_s.rolling(50).mean().iloc[-1]) if len(close_s) >= 50 else None
    sma_200 = float(close_s.rolling(200).mean().iloc[-1]) if len(close_s) >= 200 else None

    dist_50 = _safe_pct_change(current_close, sma_50) if sma_50 else None
    dist_200 = _safe_pct_change(current_close, sma_200) if sma_200 else None
    dist_52w_low = _safe_pct_change(current_close, w52_low)

    return {
        "ticker": ticker,
        "name": INDEX_NAMES.get(ticker, ticker),
        "as_of": as_of,
        "current_close": round(current_close, 2),
        "ret_1d": ret_1d,
        "ret_5d": ret_5d,
        "ret_1m": ret_1m,
        "ret_3m": ret_3m,
        "ret_ytd": ret_ytd,
        "52w_high": round(w52_high, 2),
        "52w_low": round(w52_low, 2),
        "drawdown_52w": drawdown_52w,
        "dist_52w_low": dist_52w_low,
        "ema_20": round(ema_20, 2) if ema_20 else None,
        "sma_50": round(sma_50, 2) if sma_50 else None,
        "sma_200": round(sma_200, 2) if sma_200 else None,
        "dist_50": dist_50,
        "dist_200": dist_200,
        "tier1_support": {
            "sma_50": round(sma_50, 2) if sma_50 else None,
            "dist_50": dist_50,
            "sma_200": round(sma_200, 2) if sma_200 else None,
            "dist_200": dist_200,
            "52w_low": round(w52_low, 2),
            "dist_52w_low": dist_52w_low,
        },
        "status": "ok",
    }


def get_crisis_tier_status(buffer_pct: Optional[float]) -> Dict[str, str]:
    """
    Tier 3 adaptive 4-stage proximity band classification:
    > +30%: 🟢 안전 완충 (Macro Safe Buffer: +XX.X%)
    +10% ~ +30%: 🟡 경계권 접근 (Approaching: +XX.X%)
    0% ~ +10%: 🚨 비상 경보 (Near Breakdown: +X.X%)
    < 0%: 🔴 붕괴 (Structural Breakdown: -X.X%)
    """
    if buffer_pct is None:
        return {
            "status_code": "unknown",
            "icon": "⚪",
            "label": "데이터 없음",
            "full_label": "⚪ 데이터 없음",
        }
    if buffer_pct > 30.0:
        return {
            "status_code": "safe_buffer",
            "icon": "🟢",
            "label": f"안전 완충 (Macro Safe Buffer: {buffer_pct:+.1f}%)",
            "full_label": f"🟢 안전 완충 (Macro Safe Buffer: {buffer_pct:+.1f}%)",
        }
    elif buffer_pct >= 10.0:
        return {
            "status_code": "approaching",
            "icon": "🟡",
            "label": f"경계권 접근 (Approaching: {buffer_pct:+.1f}%)",
            "full_label": f"🟡 경계권 접근 (Approaching: {buffer_pct:+.1f}%)",
        }
    elif buffer_pct >= 0.0:
        return {
            "status_code": "near_breakdown",
            "icon": "🚨",
            "label": f"비상 경보 (Near Breakdown: {buffer_pct:+.1f}%)",
            "full_label": f"🚨 비상 경보 (Near Breakdown: {buffer_pct:+.1f}%)",
        }
    else:
        return {
            "status_code": "breakdown",
            "icon": "🔴",
            "label": f"붕괴 (Structural Breakdown: {buffer_pct:+.1f}%)",
            "full_label": f"🔴 붕괴 (Structural Breakdown: {buffer_pct:+.1f}%)",
        }


def compute_rolling_crisis_benchmark(
    df: pd.DataFrame,
    current_close: float,
    window: int = 252,
) -> Dict[str, Any]:
    """
    Tier 2: Dynamic rolling 1-year (252 trading days) peak-to-trough crisis benchmark.
    Identifies maximum peak-to-trough drawdown (Close - RollingMax) / RollingMax,
    the trough date, trough price, drawdown percentage, and buffer from current price.
    Automatically rolls over as time moves forward.
    """
    if df is None or df.empty or "Close" not in df.columns or current_close is None or current_close <= 0:
        return {
            "status": "error",
            "trough_date": None,
            "trough_price": None,
            "drawdown_pct": None,
            "buffer_pct": None,
            "breached": False,
            "status_code": "unknown",
            "icon": "⚪",
            "status_label": "데이터 없음",
            "full_label": "⚪ 데이터 없음",
        }

    valid_mask = ~df["Close"].isna()
    clean_df = df[valid_mask]
    if clean_df.empty or len(clean_df) < 2:
        return {
            "status": "error",
            "trough_date": None,
            "trough_price": None,
            "drawdown_pct": None,
            "buffer_pct": None,
            "breached": False,
            "status_code": "unknown",
            "icon": "⚪",
            "status_label": "데이터 없음",
            "full_label": "⚪ 데이터 없음",
        }

    # Rolling window of up to `window` (252) trading bars
    w_bars = clean_df.iloc[-window:] if len(clean_df) >= window else clean_df
    w_close_raw = w_bars["Close"]
    w_close = w_close_raw.iloc[:, 0] if isinstance(w_close_raw, pd.DataFrame) else w_close_raw.squeeze()

    # Peak-to-Trough drawdown: (Close - RollingMax) / RollingMax
    rolling_max = w_close.cummax()
    drawdowns = (w_close - rolling_max) / rolling_max
    if drawdowns.empty or drawdowns.dropna().empty:
        return {
            "status": "error",
            "trough_date": None,
            "trough_price": None,
            "drawdown_pct": None,
            "buffer_pct": None,
            "breached": False,
            "status_code": "unknown",
            "icon": "⚪",
            "status_label": "데이터 없음",
            "full_label": "⚪ 데이터 없음",
        }

    trough_idx = drawdowns.idxmin()
    max_dd = float(drawdowns.min())
    dd_pct = round(max_dd * 100.0, 2)

    trough_date = trough_idx.strftime("%Y-%m-%d") if hasattr(trough_idx, "strftime") else str(trough_idx)[:10]

    # Trough price: Low on that day if available, otherwise Close
    low_col = "Low" if "Low" in w_bars.columns else "Close"
    low_raw = w_bars[low_col]
    low_s = low_raw.squeeze().dropna() if isinstance(low_raw, pd.DataFrame) else low_raw.dropna()
    trough_price = None
    if trough_idx in low_s.index:
        trough_val = low_s.loc[trough_idx]
        t_scalar = float(trough_val.min()) if isinstance(trough_val, pd.Series) else float(trough_val)
        if not np.isnan(t_scalar) and t_scalar > 0:
            trough_price = t_scalar

    if trough_price is None:
        c_val = w_close.loc[trough_idx]
        c_scalar = float(c_val.min()) if isinstance(c_val, pd.Series) else float(c_val)
        trough_price = c_scalar if not np.isnan(c_scalar) and c_scalar > 0 else float(current_close)

    trough_price = round(trough_price, 2)
    buffer_pct = _safe_pct_change(current_close, trough_price)
    breached = bool(current_close < trough_price)

    tier_status = get_crisis_tier_status(buffer_pct)

    return {
        "status": "ok",
        "trough_date": trough_date,
        "trough_price": trough_price,
        "drawdown_pct": dd_pct,
        "buffer_pct": buffer_pct,
        "breached": breached,
        "status_code": tier_status["status_code"],
        "icon": tier_status["icon"],
        "status_label": tier_status["label"],
        "full_label": tier_status["full_label"],
    }


def evaluate_crisis_benchmarks(
    df: pd.DataFrame,
    current_close: float,
    is_korean: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Find minimum prices on target crisis dates and check if current price breaches them.
    Ensures safe tz-naive datetime comparisons, 1D series extraction, and date-range bounding.
    If is_korean is False, domestic Korean crisis benchmarks (e.g. martial law) are skipped.
    """
    results = []
    if df is None or df.empty:
        return results

    low_col = "Low" if "Low" in df.columns else "Close"

    # Ensure tz-naive index for safe timestamp comparisons and sort chronologically
    clean_df = df.copy()
    if getattr(clean_df.index, "tz", None) is not None:
        try:
            clean_df.index = clean_df.index.tz_localize(None)
        except Exception:
            clean_df.index = pd.to_datetime([getattr(idx, 'tz_localize', lambda tz: idx)(None) for idx in clean_df.index])

    try:
        clean_df = clean_df.sort_index()
    except Exception:
        pass

    for bench in CRISIS_BENCHMARKS:
        # If asset is specifically non-Korean, skip KR-scoped crisis benchmarks
        if is_korean is False and bench.get("scope") == "KR":
            results.append({
                "id": bench["id"],
                "name": bench["name"],
                "target_date": bench["target_date"],
                "actual_date": bench["target_date"],
                "crisis_low": None,
                "breached": False,
                "buffer_pct": None,
                "status_code": "not_applicable",
                "icon": "⚪",
                "status_label": "해당 없음",
                "full_label": "⚪ 해당 없음",
                "description": bench["description"],
                "scope": bench.get("scope", "GLOBAL"),
                "status": "not_applicable",
            })
            continue

        target_dt = pd.to_datetime(bench["target_date"])
        # Window: target_dt +/- 2 calendar days
        window_start = target_dt - pd.Timedelta(days=2)
        window_end = target_dt + pd.Timedelta(days=2)

        window_df = clean_df[(clean_df.index >= window_start) & (clean_df.index <= window_end)]
        if window_df.empty and len(clean_df) > 0:
            # Nearest trading day before or after target_dt (strictly within 5 calendar days)
            idx_loc = clean_df.index.get_indexer([target_dt], method="nearest")[0]
            if 0 <= idx_loc < len(clean_df):
                nearest_dt = clean_df.index[idx_loc]
                if abs((nearest_dt - target_dt).days) <= 5:
                    window_df = clean_df.iloc[max(0, idx_loc - 1): min(len(clean_df), idx_loc + 2)]

        crisis_low = None
        min_date = bench["target_date"]

        if not window_df.empty and low_col in window_df.columns:
            low_raw = window_df[low_col]
            low_s = low_raw.squeeze().dropna() if isinstance(low_raw, pd.DataFrame) else low_raw.dropna()
            if not low_s.empty:
                crisis_low = float(low_s.min())
                min_idx = low_s.idxmin()
                if pd.notna(min_idx) and hasattr(min_idx, "strftime"):
                    min_date = min_idx.strftime("%Y-%m-%d")
                elif pd.notna(min_idx):
                    min_date = str(min_idx)[:10]

        if crisis_low is not None and crisis_low > 0:
            breached = bool(current_close < crisis_low)
            buffer_pct = _safe_pct_change(current_close, crisis_low)
        else:
            breached = False
            buffer_pct = None

        tier_status = get_crisis_tier_status(buffer_pct)

        results.append({
            "id": bench["id"],
            "name": bench["name"],
            "target_date": bench["target_date"],
            "actual_date": min_date,
            "crisis_low": round(crisis_low, 2) if crisis_low is not None else None,
            "breached": breached,
            "buffer_pct": buffer_pct,
            "status_code": tier_status["status_code"],
            "icon": tier_status["icon"],
            "status_label": tier_status["label"],
            "full_label": tier_status["full_label"],
            "description": bench["description"],
            "scope": bench.get("scope", "GLOBAL"),
        })

    return results


def _get_series(df: Optional[pd.DataFrame], col: str = "Close") -> pd.Series:
    """Safely extract 1D Series from DataFrame regardless of single or MultiIndex columns."""
    if df is None or df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    raw = df[col]
    s = raw.squeeze().dropna() if isinstance(raw, pd.DataFrame) else raw.dropna()
    return s


def compute_sector_rotation(
    sector_dfs: Dict[str, pd.DataFrame],
    spy_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute relative strength vs SPY for 11 SPDR sectors and calculate Cyclical vs Defensive spread.
    """
    spy_ret_1d = 0.0
    spy_ret_5d = 0.0
    spy_ret_1m = 0.0
    spy_c = _get_series(spy_df, "Close")
    if len(spy_c) >= 2:
        spy_ret_1d = _safe_pct_change(float(spy_c.iloc[-1]), float(spy_c.iloc[-2])) or 0.0
    if len(spy_c) >= 6:
        spy_ret_5d = _safe_pct_change(float(spy_c.iloc[-1]), float(spy_c.iloc[-6])) or 0.0
    if len(spy_c) >= 22:
        spy_ret_1m = _safe_pct_change(float(spy_c.iloc[-1]), float(spy_c.iloc[-22])) or 0.0

    sectors_data = []
    cyc_5d_rs = []
    def_5d_rs = []
    cyc_1m_rs = []
    def_1m_rs = []

    for sym, df in sector_dfs.items():
        if sym == "SPY" or df is None or df.empty or "Close" not in df.columns:
            continue
        c_s = _get_series(df, "Close")
        if len(c_s) < 2:
            continue

        c_last = float(c_s.iloc[-1])
        c_prev = float(c_s.iloc[-2])
        r1d = _safe_pct_change(c_last, c_prev) or 0.0
        r5d = _safe_pct_change(c_last, float(c_s.iloc[-6])) if len(c_s) >= 6 else (_safe_pct_change(c_last, float(c_s.iloc[0])) or 0.0)
        r1m = _safe_pct_change(c_last, float(c_s.iloc[-22])) if len(c_s) >= 22 else 0.0

        rs_5d = round(r5d - spy_ret_5d, 2)
        rs_1m = round(r1m - spy_ret_1m, 2)

        is_cyc = sym in CYCLICAL_SECTORS
        is_def = sym in DEFENSIVE_SECTORS

        if is_cyc:
            cyc_5d_rs.append(rs_5d)
            cyc_1m_rs.append(rs_1m)
        elif is_def:
            def_5d_rs.append(rs_5d)
            def_1m_rs.append(rs_1m)

        category = "경기민감" if is_cyc else ("경기방어" if is_def else "인플레/특수")

        sectors_data.append({
            "ticker": sym,
            "name": SECTOR_NAMES.get(sym, sym),
            "category": category,
            "current_price": round(c_last, 2),
            "ret_1d": r1d,
            "ret_5d": r5d,
            "ret_1m": r1m,
            "rs_5d": rs_5d,
            "rs_1m": rs_1m,
        })

    # Sort sectors by 5D RS descending
    sectors_data.sort(key=lambda x: x["rs_5d"], reverse=True)

    mean_cyc_5d = round(float(np.mean(cyc_5d_rs)), 2) if cyc_5d_rs else 0.0
    mean_def_5d = round(float(np.mean(def_5d_rs)), 2) if def_5d_rs else 0.0
    spread_5d = round(mean_cyc_5d - mean_def_5d, 2)

    mean_cyc_1m = round(float(np.mean(cyc_1m_rs)), 2) if cyc_1m_rs else 0.0
    mean_def_1m = round(float(np.mean(def_1m_rs)), 2) if def_1m_rs else 0.0
    spread_1m = round(mean_cyc_1m - mean_def_1m, 2)

    if spread_5d > 2.0:
        regime_desc = "공격적 위험 선호 (Risk-On Aggressive)"
        signal = "🟢"
    elif spread_5d >= 0.0:
        regime_desc = "온건한 순환매 (Mild Risk-On)"
        signal = "🟢"
    elif spread_5d >= -2.0:
        regime_desc = "중립 및 숨고르기 (Neutral Rotation)"
        signal = "🟡"
    else:
        regime_desc = "안전자산 도피 (Flight to Safety / Risk-Off)"
        signal = "🔴"

    return {
        "sectors": sectors_data,
        "spy_ret_5d": spy_ret_5d,
        "spy_ret_1m": spy_ret_1m,
        "mean_cyclical_5d_rs": mean_cyc_5d,
        "mean_defensive_5d_rs": mean_def_5d,
        "spread_5d": spread_5d,
        "spread_1m": spread_1m,
        "regime_desc": regime_desc,
        "signal": signal,
    }


def compute_macro_risk(macro_dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Compute macro stress barometers: VIX, 10Y yield, 10Y-13W spread, DXY, WTI, Gold, Credit Spread (HYG/LQD).
    """
    out: Dict[str, Any] = {}

    # 1. VIX
    vix_c = _get_series(macro_dfs.get('^VIX'), 'Close')
    if len(vix_c) >= 1:
        vix_cur = float(vix_c.iloc[-1])
        vix_prev5 = float(vix_c.iloc[-6]) if len(vix_c) >= 6 else float(vix_c.iloc[0])
        vix_chg_pts = round(vix_cur - vix_prev5, 2)
        vix_chg_pct = _safe_pct_change(vix_cur, vix_prev5)
        if vix_cur < 20.0:
            vix_signal = "🟢"
            vix_status = "정상 / 변동성 안정"
        elif vix_cur <= 25.0:
            vix_signal = "🟡"
            vix_status = "경계 / 변동성 상승"
        else:
            vix_signal = "🔴"
            vix_status = "극단적 패닉" if vix_cur >= 30.0 else "시장 공포 / 조정"
        out["vix"] = {
            "level": round(vix_cur, 2),
            "chg_5d_pts": vix_chg_pts,
            "chg_5d_pct": vix_chg_pct,
            "signal": vix_signal,
            "status": vix_status,
        }
    else:
        out["vix"] = {"level": None, "signal": "⚪", "status": "데이터 없음"}

    # 2. 10Y Yield (^TNX)
    tnx_c = _get_series(macro_dfs.get('^TNX'), 'Close')
    if len(tnx_c) >= 1:
        tnx_cur = float(tnx_c.iloc[-1])
        tnx_prev5 = float(tnx_c.iloc[-6]) if len(tnx_c) >= 6 else float(tnx_c.iloc[0])
        # In yfinance, ^TNX is yield in percent (e.g. 4.85 for 4.85%)
        bps_chg = round((tnx_cur - tnx_prev5) * 100.0, 1)
        if abs(bps_chg) <= 5.0:
            rate_signal = "🟢"
            rate_status = "금리 안정"
        elif abs(bps_chg) <= 15.0:
            rate_signal = "🟡"
            rate_status = "금리 변동 확대"
        else:
            rate_signal = "🔴"
            rate_status = "금리 급등 (할인율 충격)" if bps_chg > 0 else "경기 침체 우려 금리 급락"
        out["rate_10y"] = {
            "yield": round(tnx_cur, 3),
            "chg_5d_bps": bps_chg,
            "signal": rate_signal,
            "status": rate_status,
        }
    else:
        out["rate_10y"] = {"yield": None, "signal": "⚪", "status": "데이터 없음"}

    # 3. 13-Week T-Bill & Spread (Official FRED T10Y3M or Yahoo ^IRX)
    fred_rates = macro_dfs.get('FRED_RATES')
    t10y3m = None
    if isinstance(fred_rates, dict) and 'series' in fred_rates:
        try:
            t10y3m_val = fred_rates['series'].get('T10Y3M', {}).get('latest', {}).get('value')
            if t10y3m_val is not None:
                t10y3m = float(t10y3m_val)
        except Exception:
            pass

    irx_c = _get_series(macro_dfs.get('^IRX'), 'Close')
    if t10y3m is not None:
        spread_pct = round(t10y3m, 3)
        spread_bps = round(spread_pct * 100.0, 1)
        out["yield_curve"] = {
            "irx_13w": None,
            "spread_10y_13w": spread_pct,
            "spread_10y_13w_bps": spread_bps,
            "inverted": bool(spread_pct < 0),
            "source": "fred",
        }
    elif len(irx_c) >= 1 and out.get("rate_10y", {}).get("yield") is not None:
        irx_cur = float(irx_c.iloc[-1])
        spread_pct = round(out["rate_10y"]["yield"] - irx_cur, 3)
        spread_bps = round(spread_pct * 100.0, 1)
        out["yield_curve"] = {
            "irx_13w": round(irx_cur, 3),
            "spread_10y_13w": spread_pct,
            "spread_10y_13w_bps": spread_bps,
            "inverted": bool(spread_pct < 0),
            "source": "yahoo",
        }
    else:
        out["yield_curve"] = {"irx_13w": None, "spread_10y_13w": None, "spread_10y_13w_bps": None, "inverted": False}

    # 4. Dollar Index (DX-Y.NYB)
    dxy_c = _get_series(macro_dfs.get('DX-Y.NYB'), 'Close')
    if len(dxy_c) >= 1:
        dxy_cur = float(dxy_c.iloc[-1])
        dxy_prev5 = float(dxy_c.iloc[-6]) if len(dxy_c) >= 6 else float(dxy_c.iloc[0])
        out["dxy"] = {
            "level": round(dxy_cur, 2),
            "chg_5d_pct": _safe_pct_change(dxy_cur, dxy_prev5),
        }
    else:
        out["dxy"] = {"level": None, "chg_5d_pct": None}

    # 5. Crude Oil (CL=F)
    oil_c = _get_series(macro_dfs.get('CL=F'), 'Close')
    if len(oil_c) >= 1:
        oil_cur = float(oil_c.iloc[-1])
        oil_prev5 = float(oil_c.iloc[-6]) if len(oil_c) >= 6 else float(oil_c.iloc[0])
        out["crude_oil"] = {
            "price": round(oil_cur, 2),
            "chg_5d_pct": _safe_pct_change(oil_cur, oil_prev5),
        }
    else:
        out["crude_oil"] = {"price": None, "chg_5d_pct": None}

    # 6. Gold (GC=F)
    gold_c = _get_series(macro_dfs.get('GC=F'), 'Close')
    if len(gold_c) >= 1:
        gold_cur = float(gold_c.iloc[-1])
        gold_prev5 = float(gold_c.iloc[-6]) if len(gold_c) >= 6 else float(gold_c.iloc[0])
        out["gold"] = {
            "price": round(gold_cur, 2),
            "chg_5d_pct": _safe_pct_change(gold_cur, gold_prev5),
        }
    else:
        out["gold"] = {"price": None, "chg_5d_pct": None}

    # 7. Credit Spread: Official FRED ICE BofA OAS or HYG vs LQD fallback
    fred_credit = macro_dfs.get('FRED_CREDIT')
    hy_oas = None
    bbb_oas = None
    if isinstance(fred_credit, dict) and 'series' in fred_credit:
        try:
            hy_oas_raw = fred_credit['series'].get('BAMLH0A0HYM2', {}).get('latest', {}).get('value')
            bbb_oas_raw = fred_credit['series'].get('BAMLC0A4CBBB', {}).get('latest', {}).get('value')
            if hy_oas_raw is not None:
                hy_oas = float(hy_oas_raw)
            if bbb_oas_raw is not None:
                bbb_oas = float(bbb_oas_raw)
        except Exception:
            pass

    hyg_c = _get_series(macro_dfs.get('HYG'), 'Close')
    lqd_c = _get_series(macro_dfs.get('LQD'), 'Close')
    cur_ratio = None
    credit_rs_5d = None
    if not hyg_c.empty and not lqd_c.empty:
        common_idx = hyg_c.index.intersection(lqd_c.index)
        if len(common_idx) >= 2:
            ratio_s = hyg_c.loc[common_idx] / lqd_c.loc[common_idx]
            cur_ratio = round(float(ratio_s.iloc[-1]), 4)
            prev_ratio5 = float(ratio_s.iloc[-6]) if len(ratio_s) >= 6 else float(ratio_s.iloc[0])
            credit_rs_5d = round((cur_ratio - prev_ratio5) / prev_ratio5 * 100.0, 2)

    if hy_oas is not None:
        # Convert percent to bps if in percent (e.g. 2.85 -> 285 bps)
        hy_oas_bps = round(hy_oas * 100.0 if hy_oas < 20.0 else hy_oas, 1)
        bbb_oas_bps = round(bbb_oas * 100.0 if bbb_oas and bbb_oas < 20.0 else (bbb_oas or 0.0), 1)

        if hy_oas_bps <= 350.0:
            credit_signal = "🟢"
            credit_status = f"신용 환경 건전 (HY OAS {hy_oas_bps:.0f} bps)"
        elif hy_oas_bps <= 500.0:
            credit_signal = "🟡"
            credit_status = f"신용 스프레드 주의 (HY OAS {hy_oas_bps:.0f} bps)"
        else:
            credit_signal = "🔴"
            credit_status = f"신용 경색 경보 (HY OAS {hy_oas_bps:.0f} bps 급등)"

        out["credit"] = {
            "hy_oas_bps": hy_oas_bps,
            "bbb_oas_bps": bbb_oas_bps,
            "hyg_lqd_ratio": cur_ratio,
            "credit_rs_5d": credit_rs_5d,
            "signal": credit_signal,
            "status": credit_status,
            "source": "fred",
        }
    elif cur_ratio is not None:
        if credit_rs_5d is not None and credit_rs_5d >= 0.0:
            credit_signal = "🟢"
            credit_status = "신용 환경 건전 (위험 선호)"
        elif credit_rs_5d is not None and credit_rs_5d >= -1.0:
            credit_signal = "🟡"
            credit_status = "신용 스프레드 완만한 확대"
        else:
            credit_signal = "🔴"
            credit_status = "신용 경색 경보 (하이일드 스프레드 급확대)"

        out["credit"] = {
            "hy_oas_bps": None,
            "bbb_oas_bps": None,
            "hyg_lqd_ratio": cur_ratio,
            "credit_rs_5d": credit_rs_5d,
            "signal": credit_signal,
            "status": credit_status,
            "source": "yahoo",
        }
    else:
        out["credit"] = {
            "hy_oas_bps": None,
            "bbb_oas_bps": None,
            "hyg_lqd_ratio": None,
            "credit_rs_5d": None,
            "signal": "⚪",
            "status": "데이터 없음",
        }

    # 8. USD/KRW Exchange Rate (USDKRW=X)
    usd_c = _get_series(macro_dfs.get('USDKRW=X'), 'Close')
    if len(usd_c) >= 1:
        usd_cur = float(usd_c.iloc[-1])
        usd_prev5 = float(usd_c.iloc[-6]) if len(usd_c) >= 6 else float(usd_c.iloc[0])
        usd_chg_pts = round(usd_cur - usd_prev5, 2)
        usd_chg_pct = _safe_pct_change(usd_cur, usd_prev5)
        if usd_cur < 1350.0:
            usd_signal = "🟢"
            usd_status = "환율 안정 (외인 수급 우호)"
        elif usd_cur <= 1420.0:
            usd_signal = "🟡"
            usd_status = "환율 경계 (외인 수급 압박)"
        else:
            usd_signal = "🔴"
            usd_status = "고환율 경보 (외인 이탈 가속)"
        out["usdkrw"] = {
            "rate": round(usd_cur, 2),
            "chg_5d_pts": usd_chg_pts,
            "chg_5d_pct": usd_chg_pct,
            "signal": usd_signal,
            "status": usd_status,
        }
    else:
        out["usdkrw"] = {"rate": None, "signal": "⚪", "status": "데이터 없음"}

    return out


def compute_stock_beta(stock_df: Optional[pd.DataFrame], benchmark_df: Optional[pd.DataFrame], window: int = 60) -> Optional[float]:
    """
    Calculate beta of stock vs benchmark using daily returns over given trading window.
    Beta = Cov(R_stock, R_bench) / Var(R_bench)
    """
    if stock_df is None or benchmark_df is None:
        return None
    s_close = _get_series(stock_df, "Close")
    b_close = _get_series(benchmark_df, "Close")
    if len(s_close) < 10 or len(b_close) < 10:
        return None

    common_idx = s_close.index.intersection(b_close.index)
    if len(common_idx) < 10:
        return None

    s_ret = s_close.loc[common_idx].pct_change().dropna()
    b_ret = b_close.loc[common_idx].pct_change().dropna()

    if len(s_ret) > window:
        s_ret = s_ret.iloc[-window:]
        b_ret = b_ret.iloc[-window:]

    cov = np.cov(s_ret, b_ret)[0][1]
    var_b = np.var(b_ret)
    if var_b == 0 or np.isnan(cov) or np.isnan(var_b):
        return None
    return round(float(cov / var_b), 2)

