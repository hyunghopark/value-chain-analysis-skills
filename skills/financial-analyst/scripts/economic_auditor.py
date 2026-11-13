"""
Economic Moat & Value Trap Gatekeeper Engine (v4.0 Core):
Implements institutional economic audit metrics:
1. EVA Spread (ROIC - WACC)
2. Implied Equity Risk Premium (ERP Yield Gap vs 10Y Treasury)
3. Total Shareholder Yield (TSY: Dividend + Net Buyback/Dilution)
4. Cash Conversion Ratio (CCR: OCF / Net Income)
5. 1-Step Downgrade Gatekeeper & Joint De-rating Floor Model
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def compute_eva_roic_wacc(
    info: Dict[str, Any],
    balance_sheet: Optional[pd.DataFrame] = None,
    income_stmt: Optional[pd.DataFrame] = None,
    rf_rate: float = 4.5,
) -> Dict[str, Any]:
    """
    Compute Return on Invested Capital (ROIC), Weighted Average Cost of Capital (WACC),
    and Economic Value Added (EVA Spread = ROIC - WACC).
    """
    # 1. Tax Rate
    tax_rate = 0.22
    if income_stmt is not None and not income_stmt.empty and 'Tax Rate For Calcs' in income_stmt.index:
        s_tr = income_stmt.loc['Tax Rate For Calcs'].dropna()
        if len(s_tr) > 0 and 0.05 <= float(s_tr.iloc[0]) <= 0.45:
            tax_rate = float(s_tr.iloc[0])

    # 2. EBIT & NOPAT
    ebit = None
    if income_stmt is not None and not income_stmt.empty and 'EBIT' in income_stmt.index:
        s_ebit = income_stmt.loc['EBIT'].dropna()
        if len(s_ebit) > 0 and not np.isnan(s_ebit.iloc[0]):
            ebit = float(s_ebit.iloc[0])
    if ebit is None:
        ebit = float(info.get('operatingCashflow') or 0.0) * 0.8
    nopat = ebit * (1.0 - tax_rate)

    # 3. Invested Capital
    inv_cap = None
    if balance_sheet is not None and not balance_sheet.empty and 'Invested Capital' in balance_sheet.index:
        s_ic = balance_sheet.loc['Invested Capital'].dropna()
        if len(s_ic) > 0 and not np.isnan(s_ic.iloc[0]) and s_ic.iloc[0] > 0:
            inv_cap = float(s_ic.iloc[0])
    if inv_cap is None or inv_cap <= 0:
        debt = float(info.get('totalDebt') or 0.0)
        equity = float(info.get('marketCap') or info.get('totalStockholderEquity') or 1.0)
        cash = float(info.get('totalCash') or 0.0)
        inv_cap = max(debt + equity - cash, 1.0)

    roic = (nopat / inv_cap) * 100.0 if inv_cap > 0 else 0.0

    # 4. Cost of Equity (ke)
    beta = info.get('beta')
    if beta is None or np.isnan(beta) or beta <= 0:
        beta = 1.0
    beta = max(0.4, min(float(beta), 3.0))
    market_erp = 5.5
    ke = rf_rate + beta * market_erp

    # 5. Cost of Debt (kd)
    total_debt = float(info.get('totalDebt') or 0.0)
    interest_exp = None
    if income_stmt is not None and not income_stmt.empty and 'Interest Expense' in income_stmt.index:
        s_ie = income_stmt.loc['Interest Expense'].dropna()
        if len(s_ie) > 0 and not np.isnan(s_ie.iloc[0]) and s_ie.iloc[0] > 0:
            interest_exp = float(s_ie.iloc[0])
    if interest_exp and total_debt > 0:
        raw_kd = (interest_exp / total_debt) * 100.0
        kd = max(rf_rate, min(raw_kd, rf_rate + 4.0)) * (1.0 - tax_rate)
    else:
        kd = (rf_rate + 1.5) * (1.0 - tax_rate)

    # 6. Capital Structure Weights & WACC
    mcap = float(info.get('marketCap') or 1.0)
    total_capital = max(mcap + total_debt, 1.0)
    weight_e = mcap / total_capital
    weight_d = total_debt / total_capital

    wacc = weight_e * ke + weight_d * kd
    eva_spread = roic - wacc

    # Signal Thresholds: >= +3.0%p 🟢, 0 ~ +3.0%p 🟡, < 0.0%p 🔴
    if eva_spread >= 3.0:
        signal = "🟢"
        status = "초과 가치 창출 (경제적 해자)"
    elif eva_spread >= 0.0:
        signal = "🟡"
        status = "정상 자본수익 달성"
    else:
        signal = "🔴"
        status = "가치 파괴 (자본비용 미달)"

    return {
        "roic": round(roic, 2),
        "wacc": round(wacc, 2),
        "eva_spread": round(eva_spread, 2),
        "ke": round(ke, 2),
        "kd": round(kd, 2),
        "beta": round(beta, 2),
        "signal": signal,
        "status": status,
    }


def compute_implied_erp(forward_pe: Optional[float], rf_rate: Optional[float] = None) -> Dict[str, Any]:
    """
    Compute Implied Equity Risk Premium (ERP Yield Gap = 1/FPE - 10Y Treasury).
    """
    if rf_rate is None or rf_rate <= 0:
        rf_rate = 4.5  # 스냅샷 미연동 시에만 최후 fallback

    if forward_pe is None or np.isnan(forward_pe) or forward_pe <= 0:
        return {
            "earnings_yield": None,
            "rf_rate": rf_rate,
            "implied_erp": None,
            "signal": "⚪",
            "status": "데이터 없음",
        }

    ey = (1.0 / forward_pe) * 100.0
    implied_erp = ey - rf_rate

    # Signal Thresholds: >= +3.0%p 🟢, 0 ~ +3.0%p 🟡, < 0.0%p 🔴
    if implied_erp >= 3.0:
        signal = "🟢"
        status = "국채 대비 충분한 안전마진"
    elif implied_erp >= 0.0:
        signal = "🟡"
        status = "국채 대비 완만한 프리미엄"
    else:
        signal = "🔴"
        status = "채권 대비 역마진 (주식이 국채보다 비쌈)"

    return {
        "earnings_yield": round(ey, 2),
        "rf_rate": round(rf_rate, 2),
        "implied_erp": round(implied_erp, 2),
        "signal": signal,
        "status": status,
    }


def compute_total_shareholder_yield(
    info: Dict[str, Any],
    balance_sheet: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute Total Shareholder Yield (TSY = Dividend Yield + Net Buyback Yield).
    Net Buyback Yield is -1 * (latest_shares - prior_shares) / prior_shares.
    """
    raw_dy = info.get('dividendYield')
    div_yield = 0.0
    if raw_dy is not None and not np.isnan(raw_dy):
        div_yield = float(raw_dy)
        if div_yield > 50.0:
            div_yield /= 100.0

    net_buyback_yield = 0.0
    shares_prior = None
    shares_latest = None

    if balance_sheet is not None and not balance_sheet.empty:
        for row_name in ('Ordinary Shares Number', 'Share Issued'):
            if row_name in balance_sheet.index:
                s_sh = balance_sheet.loc[row_name].dropna()
                if len(s_sh) >= 2 and s_sh.iloc[1] > 0:
                    med = float(s_sh.median())
                    v0 = float(s_sh.iloc[0])
                    v1 = float(s_sh.iloc[1])
                    # KI-007 anomaly filter: if a share count deviates >8% from median, replace with median
                    if med > 0:
                        if abs(v0 - med) / med > 0.08:
                            v0 = med
                        if abs(v1 - med) / med > 0.08:
                            v1 = med
                    shares_latest = v0
                    shares_prior = v1
                    pct_change = (shares_latest - shares_prior) / shares_prior if shares_prior > 0 else 0.0
                    pct_change = max(-0.5, min(pct_change, 0.5))
                    net_buyback_yield = -pct_change * 100.0
                    break

    tsy = div_yield + net_buyback_yield

    # Signal Thresholds: >= 3.0% 🟢, 0 ~ 3.0% 🟡, < 0.0% 🔴 (Dilution)
    if tsy >= 3.0:
        signal = "🟢"
        status = "적극적 주주환원"
    elif tsy >= 0.0:
        signal = "🟡"
        status = "완만한 환원 / 현상 유지"
    else:
        signal = "🔴"
        status = "주주가치 지분 희석 (주식수 증가)"

    return {
        "dividend_yield": round(div_yield, 2),
        "buyback_yield": round(net_buyback_yield, 2),
        "total_shareholder_yield": round(tsy, 2),
        "shares_latest": shares_latest,
        "shares_prior": shares_prior,
        "signal": signal,
        "status": status,
    }


def compute_cash_conversion(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute Cash Conversion Ratio (CCR = Operating Cash Flow / Net Income).
    """
    ocf = info.get('operatingCashflow')
    ni = info.get('netIncomeToCommon')

    if ocf is None or ni is None or np.isnan(ocf) or np.isnan(ni):
        return {
            "ocf": None,
            "net_income": None,
            "ccr": None,
            "signal": "⚪",
            "status": "데이터 없음",
        }

    ocf = float(ocf)
    ni = float(ni)

    if ni > 0:
        ccr = round(ocf / ni, 2)
        if ccr >= 1.0:
            signal = "🟢"
            status = "순이익 초과 현금 창출 (최우량 품질)"
        elif ccr >= 0.70:
            signal = "🟡"
            status = "정상 발생주의 회계 범위"
        else:
            signal = "🔴"
            status = "이익 현금전환율 불량 (OCF 부족 / 분식 위험)"
    else:
        # Net loss situation
        ccr = round(ocf / abs(ni), 2) if ni != 0 else 0.0
        if ocf > 0:
            signal = "🟡"
            status = "회계적 적자이나 영업현금 흑자"
        else:
            signal = "🔴"
            status = "순이익 및 영업현금 동반 적자"

    return {
        "ocf": ocf,
        "net_income": ni,
        "ccr": round(ccr, 2) if ccr is not None else None,
        "signal": signal,
        "status": status,
    }


def audit_economic_moat(
    ticker: str,
    info: Dict[str, Any],
    balance_sheet: Optional[pd.DataFrame] = None,
    income_stmt: Optional[pd.DataFrame] = None,
    forward_pe: Optional[float] = None,
    rf_rate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Synthesize all 4 economic pillars and determine Economic Moat & Value Trap status.
    """
    if rf_rate is None or rf_rate <= 0:
        rf_rate = 4.5
    eva_res = compute_eva_roic_wacc(info, balance_sheet, income_stmt, rf_rate=rf_rate)
    erp_res = compute_implied_erp(forward_pe, rf_rate=rf_rate)
    tsy_res = compute_total_shareholder_yield(info, balance_sheet)
    ccr_res = compute_cash_conversion(info)

    # Check Gatekeeper breach conditions
    breach_reasons = []
    if eva_res.get("signal") == "🔴":
        breach_reasons.append(f"자본 파괴 (EVA {eva_res.get('eva_spread'):+.2f}%p)")
    if ccr_res.get("signal") == "🔴":
        breach_reasons.append(f"현금전환율 불량 (CCR {ccr_res.get('ccr')})")
    if tsy_res.get("signal") == "🔴" and (tsy_res.get("buyback_yield") or 0.0) <= -2.0:
        breach_reasons.append(f"지분 희석 (주식수 {abs(tsy_res.get('buyback_yield', 0)):.1f}% 증가)")

    gatekeeper_breached = len(breach_reasons) > 0
    breach_summary = " 및 ".join(breach_reasons) if breach_reasons else None

    # Overall Diagnosis
    if not gatekeeper_breached and eva_res.get("signal") == "🟢" and ccr_res.get("signal") in ("🟢", "🟡"):
        overall_status = "🟢 통과 (강력한 경제적 해자)"
        overall_code = "MOAT_PASS"
    elif gatekeeper_breached:
        overall_status = f"🔴 밸류 트랩 경보 ({breach_summary})"
        overall_code = "VALUE_TRAP_ALERT"
    else:
        overall_status = "🟡 보통 (자본비용 충족)"
        overall_code = "NEUTRAL"

    return {
        "ticker": ticker,
        "eva": eva_res,
        "erp": erp_res,
        "tsy": tsy_res,
        "ccr": ccr_res,
        "gatekeeper_breached": gatekeeper_breached,
        "breach_summary": breach_summary,
        "overall_status": overall_status,
        "overall_code": overall_code,
    }


def apply_gatekeeper_to_verdict(
    preliminary_verdict: str,
    economic_audit: Dict[str, Any],
) -> Tuple[str, Optional[str]]:
    """
    Apply 1-Step Downgrade Rule:
    If preliminary verdict is 🟢 (강력 매수 or 매수 고려), but economic gatekeeper is breached,
    automatically downgrade to 🟡 중립/관망 (⚠️ 밸류 트랩 경보).
    """
    if not economic_audit or not economic_audit.get("gatekeeper_breached"):
        return preliminary_verdict, None

    is_buy = "강력 매수" in preliminary_verdict or "매수 고려" in preliminary_verdict or preliminary_verdict.startswith("🟢")
    if is_buy:
        reason = economic_audit.get("breach_summary") or "경제적 부 파괴 또는 현금전환율 불량"
        downgraded = f"🟡 **중립/관망 (⚠️ 밸류 트랩 경보: {reason})**"
        return downgraded, reason

    return preliminary_verdict, None


def apply_event_gatekeeper(
    preliminary_verdict: str,
    intelligence_meta: Optional[Dict[str, Any]],
) -> Tuple[str, Optional[str]]:
    """
    Apply Event-Driven Crisis Downgrade Rule (WATCH):
    If market-intelligence detects Severity Level 4 (Severe) or Level 5 (Critical Governance Crisis),
    automatically downgrade preliminary verdict to:
    🟡 중립/관망 (🚨 거버넌스 긴급 경보: 사실관계 확인 중 — WATCH).
    """
    if not intelligence_meta:
        return preliminary_verdict, None

    sev = intelligence_meta.get("severity", {}) if isinstance(intelligence_meta.get("severity"), dict) else {}
    level = sev.get("level") or intelligence_meta.get("severity_level", 1)

    if level < 4:
        return preliminary_verdict, None

    headline = sev.get("primary_crisis") or intelligence_meta.get("primary_crisis", "경영진 거버넌스 및 사법 리스크")
    downgraded = f"🟡 **중립/관망 (🚨 거버넌스 긴급 경보: {headline} 사실관계 확인 중 — WATCH)**"
    return downgraded, headline


def compute_joint_derating_floor(
    bear_eps: Optional[float],
    current_bps: Optional[float],
    pb_band: Optional[Dict[str, Any]],
    forward_pe: Optional[float],
    profile_type: str = "GENERAL",
) -> Optional[float]:
    """
    Compute Joint De-rating Worst-case Floor Price (Multiple C):
    Simultaneous occurrence of earnings miss and multiple contraction.
    """
    if profile_type in ("CYCLICAL", "FINANCIAL_REIT") and pb_band and current_bps:
        # For cyclical/asset-heavy: Bear BPS * historical minimum P/B
        min_pb = pb_band.get("min") or pb_band.get("lowest_pb")
        if min_pb and min_pb > 0 and current_bps > 0:
            return round(float(current_bps * min_pb), 2)

    # For general, platform, biotech: Bear EPS * de-rated PE (60% of current or min 8x)
    if bear_eps and bear_eps > 0 and forward_pe and forward_pe > 0:
        derated_pe = max(6.0, forward_pe * 0.55)
        return round(float(bear_eps * derated_pe), 2)

    return None


def render_economic_audit_table(results: Dict[str, Any], snap_fn: Optional[Any] = None) -> str:
    """
    Render markdown for Table 6-1: [경제학 감사] Moat & 밸류 트랩 필터.
    """
    lines = [
        "### 5. 🏛️ [경제학 감사] Moat & 밸류 트랩 필터 (Economic Moat & Capital Allocation)\n",
        "> 💡 **초과이윤(EVA Spread = ROIC - WACC)**, **실질 ERP(일드갭 = 1/FPE - 국채10Y)**, **총주주환원율(TSY = 배당 + 자사주 증감)**, **현금전환율(CCR = OCF / 순이익)**을 검증합니다.",
        "> 1차 신호등 점수가 🟢(매수 후보)일지라도, 경제학 감사에서 🔴(자본 파괴 또는 분식/희석 징후)가 감지되면 최종 판정이 **🟡 중립/관망 (⚠️ 밸류 트랩 경보)**으로 자동 1단계 강등됩니다.\n",
        "| 기업 (티커) | ROIC | WACC | EVA 스프레드 | Forward PE | 실질 ERP (일드갭) | 총주주환원율 (TSY) | 현금전환율 (CCR) | 경제학 게이트키퍼 진단 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for sym, info in results.items():
        audit = info.get('_economic_audit')
        if not audit:
            lines.append(f"| **{sym}** | - | - | - | - | - | - | - | ⚪ 데이터 없음 |")
            continue
        eva = audit.get('eva', {})
        erp = audit.get('erp', {})
        tsy = audit.get('tsy', {})
        ccr = audit.get('ccr', {})

        r_str = f"{eva.get('roic'):.1f}%" if eva.get('roic') is not None else "-"
        w_str = f"{eva.get('wacc'):.1f}%" if eva.get('wacc') is not None else "-"
        eva_str = f"{eva.get('eva_spread'):+.1f}%p {eva.get('signal')}" if eva.get('eva_spread') is not None else "-"

        fpe_val = info.get('forwardPE')
        fpe_str = f"{fpe_val:.2f}" if fpe_val is not None else "-"
        erp_str = f"{erp.get('implied_erp'):+.1f}%p {erp.get('signal')}" if erp.get('implied_erp') is not None else "-"

        tsy_str = f"{tsy.get('total_shareholder_yield'):+.1f}% {tsy.get('signal')}" if tsy.get('total_shareholder_yield') is not None else "-"
        ccr_str = f"{ccr.get('ccr'):.2f} {ccr.get('signal')}" if ccr.get('ccr') is not None else "-"

        diag = audit.get('overall_status', '⚪ 데이터 없음')
        lines.append(f"| **{sym}** | {r_str} | {w_str} | {eva_str} | {fpe_str} | {erp_str} | {tsy_str} | {ccr_str} | **{diag}** |")

        if snap_fn and callable(snap_fn):
            base = f"{sym}.economic_audit"
            if eva.get('roic') is not None:
                snap_fn(f"{base}.roic", eva.get('roic'))
                snap_fn(f"{base}.roic_pct", eva.get('roic'))
            if eva.get('wacc') is not None:
                snap_fn(f"{base}.wacc", eva.get('wacc'))
                snap_fn(f"{base}.wacc_pct", eva.get('wacc'))
            if eva.get('eva_spread') is not None:
                snap_fn(f"{base}.eva_spread", eva.get('eva_spread'))
                snap_fn(f"{base}.eva_spread_pct", eva.get('eva_spread'))
            if erp.get('implied_erp') is not None:
                snap_fn(f"{base}.implied_erp", erp.get('implied_erp'))
                snap_fn(f"{base}.implied_erp_pct", erp.get('implied_erp'))
            if tsy.get('total_shareholder_yield') is not None:
                snap_fn(f"{base}.total_shareholder_yield", tsy.get('total_shareholder_yield'))
                snap_fn(f"{base}.total_shareholder_yield_pct", tsy.get('total_shareholder_yield'))
            if ccr.get('ccr') is not None:
                snap_fn(f"{base}.cash_conversion_ratio", ccr.get('ccr'))

    lines.append("\n> 💡 **진단 기준**: EVA 스프레드(≥+3.0%p 🟢, 0~+3.0%p 🟡, <0%p 🔴) · 실질 ERP(≥+3.0%p 🟢, 0~+3.0%p 🟡, <0%p 🔴) · TSY(≥3.0% 🟢, 0~3.0% 🟡, <0% 🔴) · CCR(≥1.0 🟢, 0.7~1.0 🟡, <0.7 🔴)\n")
    return "\n".join(lines) + "\n"


def compute_cash_conversion_cycle(
    info: Dict[str, Any],
    balance_sheet: Optional[pd.DataFrame] = None,
    income_stmt: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Compute Cash Conversion Cycle (CCC = DIO + DSO - DPO) and Gross Profit Margin (GPM)
    as proxies for value chain bargaining power.
    """
    gpm = info.get('grossMargins')
    gpm_pct = round(float(gpm) * 100.0, 2) if gpm is not None and not np.isnan(gpm) else None

    # Fallback default estimation if balance sheet lines are unavailable
    dio, dso, dpo = 45.0, 40.0, 50.0

    if balance_sheet is not None and not balance_sheet.empty and income_stmt is not None and not income_stmt.empty:
        try:
            rev = float(info.get('totalRevenue') or 1.0)
            cogs = float(info.get('costOfRevenue') or rev * 0.6)

            # Receivables
            rec = None
            for r_key in ('Net Receivables', 'Accounts Receivable', 'Receivables'):
                if r_key in balance_sheet.index:
                    s_r = balance_sheet.loc[r_key].dropna()
                    if len(s_r) > 0:
                        rec = float(s_r.iloc[0])
                        break
            if rec and rev > 0:
                dso = (rec / rev) * 365.0

            # Inventory
            inv = None
            if 'Inventory' in balance_sheet.index:
                s_inv = balance_sheet.loc['Inventory'].dropna()
                if len(s_inv) > 0:
                    inv = float(s_inv.iloc[0])
            if inv and cogs > 0:
                dio = (inv / cogs) * 365.0

            # Payables
            pay = None
            for p_key in ('Accounts Payable', 'Payables'):
                if p_key in balance_sheet.index:
                    s_p = balance_sheet.loc[p_key].dropna()
                    if len(s_p) > 0:
                        pay = float(s_p.iloc[0])
                        break
            if pay and cogs > 0:
                dpo = (pay / cogs) * 365.0
        except Exception:
            pass

    ccc = dio + dso - dpo

    return {
        "gpm": gpm_pct,
        "dio": round(dio, 1),
        "dso": round(dso, 1),
        "dpo": round(dpo, 1),
        "ccc": round(ccc, 1),
    }
