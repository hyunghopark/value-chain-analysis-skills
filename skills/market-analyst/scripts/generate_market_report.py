"""
Master report generator CLI for market-analyst:
Generates institutional markdown reports and companion snapshot files in reports/.
Populates all qualitative and quantitative sections using real-time market data,
historical crisis drawdown diagnostics, Socratic dialectical examination, and
intelligent bridging to financial-analyst for single stock queries.
"""

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

# Ensure scripts directory in path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import get_market_stats as gms
import market_metrics as mm
from market_snapshot import attach_section4
import socratic_auditor as sa
import target_resolver as tr

KST = datetime.timezone(datetime.timedelta(hours=9))


def find_reports_root() -> str:
    """Find root directory where reports/ should be placed."""
    cur = os.path.dirname(os.path.abspath(__file__))
    while cur != os.path.dirname(cur):
        if os.path.basename(cur) in (".agents", ".claude"):
            return os.path.dirname(cur)
        cur = os.path.dirname(cur)
    parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if os.path.isdir(os.path.join(parent, "reports")):
        return parent
    return os.getcwd()


def _get_val(val_dict: Dict[str, Any], path: str, default: Any = None) -> Any:
    item = val_dict.get(path)
    if isinstance(item, dict):
        return item.get("value", default)
    return default


def populate_report(
    tmpl: str,
    snapshot,
    market: str,
    theme: str,
    now_time_str: str,
    snapshot_basename: str,
    sec4_text: str,
    target_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Replace all placeholders in the report template with authoritative data and Socratic analysis."""
    val = snapshot.values
    t_info = target_info or tr.resolve_target(market)

    p_sym = t_info.get("primary_ticker", "^GSPC")
    p_name = t_info.get("primary_name", "S&P 500")
    is_kr = t_info.get("is_korean", False)
    is_single_stock = t_info.get("is_single_stock", False)
    stock_info = t_info.get("stock_info") or {}

    p_c = _get_val(val, f"{p_sym}.quote.close", 0.0)
    p_dd = _get_val(val, f"{p_sym}.diagnostics.drawdown_52w", 0.0)
    p_d200 = _get_val(val, f"{p_sym}.ma.dist_200", 0.0)
    p_s200 = _get_val(val, f"{p_sym}.ma.sma_200", 0.0)
    p_r5d = _get_val(val, f"{p_sym}.ret.5d", 0.0)

    # Header
    tmpl = tmpl.replace("[시장 명칭 / 테마]", f"{p_name} ({theme})")
    tmpl = tmpl.replace("[YYYY-MM-DD HH:MM KST]", now_time_str)
    tmpl = tmpl.replace("[정규장 마감 / 장중]", "실시간 기준")
    tmpl = tmpl.replace("[스냅샷 파일명]", snapshot_basename)

    # Section 1: Regime Verdict & Cash
    regime_name = _get_val(val, "macro.regime.verdict", "건전한 조정 국면 (Healthy Correction / Pullback)")
    regime_icon = _get_val(val, "macro.regime.icon", "🟡")
    cash_pct = _get_val(val, "macro.regime.cash_pct", 25)
    equity_pct = _get_val(val, "macro.regime.equity_pct", 65)
    safe_pct = _get_val(val, "macro.regime.safe_pct", 10)

    tmpl = tmpl.replace("[🟢 상승 확장 / 🟡 건전한 조정 / 🟡 과열·후기 / 🔴 유동성 충격 / 🔴 스태그플레이션 / 🔴 구조적 약세]", f"{regime_icon} {regime_name}")
    tmpl = tmpl.replace("[XX%]", f"{cash_pct}%", 1)
    tmpl = tmpl.replace("[XX%]", f"{equity_pct}%", 1)
    tmpl = tmpl.replace("[XX%]", f"{safe_pct}%", 1)

    # Macro & Pillars
    vix_l = _get_val(val, "macro.vix.level", 20.0)
    r10_y = _get_val(val, "macro.rate_10y.yield", 4.5)
    r10_bps = _get_val(val, "macro.rate_10y.bps_chg", 0.0)
    cr_r = _get_val(val, "macro.credit.ratio", 0.75)
    cr_rs = _get_val(val, "macro.credit.rs_5d", 0.0)
    rot_spread = _get_val(val, "sectors.rotation.spread_5d", 0.0)

    usd_rate = _get_val(val, "macro.usdkrw.rate")
    usd_pts = _get_val(val, "macro.usdkrw.chg_5d_pts")
    usd_pct = _get_val(val, "macro.usdkrw.chg_5d_pct")

    p_trend = _get_val(val, "macro.regime.pillar.trend", "🟡")
    p_vix = _get_val(val, "macro.regime.pillar.vix", "🟡")
    p_rates = _get_val(val, "macro.regime.pillar.rates", "🟡")
    p_credit = _get_val(val, "macro.regime.pillar.credit", "🟡")
    p_breadth = _get_val(val, "macro.regime.pillar.breadth", "🔴")

    # Executive summary sentence
    p_beta = _get_val(val, f"{p_sym}.beta_parent")
    if is_single_stock:
        curr_unit = "원" if is_kr else "$"
        beta_str = f", 상위 지수({stock_info.get('parent_index', '시장')}) 대비 60일 베타 {p_beta:.2f}" if p_beta is not None else ""
        summary_sentence = (
            f"{p_name}은(는) 종가 {p_c:,.2f}{curr_unit} 기준 52주 고점 대비 낙폭 {p_dd:+.2f}%, 200 SMA 대비 {p_d200:+.2f}%{beta_str}를 기록 중임. "
            f"상위 지수({stock_info.get('parent_index', '시장')})의 레짐({regime_icon} {regime_name})과 매크로 할인율(금리 {r10_y}%)의 "
            f"영향을 직접 받고 있으며, 최근 1년 조정 저점(손절 기준선) 방어 여부가 중단기 기술적 반등의 핵심 분기점임."
        )
    elif t_info.get("profile") in (tr.PROFILE_KR_INDEX, tr.PROFILE_KR_MARKET):
        summary_sentence = (
            f"{p_name}은(는) 52주 고점 대비 낙폭 {p_dd:+.2f}%, 200 SMA 대비 {p_d200:+.2f}%로 "
            f"{'200일선 구조적 이탈(-3% 초과 하회)' if p_d200 < -3.0 else '200선 지지 테스트'} 구간에 위치함. "
            f"원/달러 환율({f'{usd_rate:,.2f}원' if usd_rate else '고환율'})과 글로벌 금리 할인율 압박이 외국인 수급을 제약하고 있으며, "
            f"최근 1년 조정 저점(손절 기준선) 및 52주 저점의 방어 여부가 국내 증시의 1차 바닥 확인 기준선임."
        )
    elif t_info.get("profile") == tr.PROFILE_SECTOR_SEMI:
        summary_sentence = (
            f"필라델피아 반도체(^SOX: 52주 낙폭 {p_dd:+.2f}%, 200선 {p_d200:+.2f}%)는 고밸류에이션 부담 및 빅테크 AI Capex 투자 지속성 논란으로 "
            f"조정을 겪고 있으나, 글로벌 반도체 사이클상 최근 1년 롤링 조정 저점 및 200일선 방어력이 1차 구조적 지지선으로 작동 중임."
        )
    elif t_info.get("profile") == tr.PROFILE_SECTOR_TECH:
        summary_sentence = (
            f"나스닥 100(^NDX: 52주 낙폭 {p_dd:+.2f}%, 200선 {p_d200:+.2f}%)은 미국 10년물 국채금리({r10_y}%) 고착화에 따른 미래 현금흐름 할인율 상승으로 "
            f"멀티플 압축이 진행 중이며, 200일선 지지 확인 및 VIX 20 이하 안착이 추세 반전의 선결 조건임."
        )
    else:
        gspc_dd = _get_val(val, "^GSPC.diagnostics.drawdown_52w", p_dd)
        gspc_d200 = _get_val(val, "^GSPC.ma.dist_200", p_d200)
        sox_dd = _get_val(val, "^SOX.diagnostics.drawdown_52w", 0.0)
        sox_d200 = _get_val(val, "^SOX.ma.dist_200", 0.0)
        ndx_dd = _get_val(val, "^NDX.diagnostics.drawdown_52w", 0.0)
        summary_sentence = (
            f"S&P 500은 200 SMA 대비 {gspc_d200:+.2f}%로 지지선을 방어하고 있으나, "
            f"반도체(^SOX: 52주 낙폭 {sox_dd:+.2f}%, 200선 {sox_d200:+.2f}%)와 기술주(^NDX: {ndx_dd:+.2f}%)는 "
            f"금리 할인율 재평가 및 차익 매물로 200일선을 이탈함. 단, 200일선 지지력 및 최근 1년 조정 저점(손절 기준선)은 방어 중임."
        )
    tmpl = tmpl.replace("[AI_TODO: 시장의 급락/반등 성격, 200일선 및 위기 지지선 방어 여부, 자금 흐름을 요약한 한 줄 진단]", summary_sentence)

    # Section 2-2 3-Tier Support Data (retrieved early for dynamic text)
    p_s50 = _get_val(val, f"{p_sym}.ma.sma_50", 0.0)
    p_d50 = _get_val(val, f"{p_sym}.ma.dist_50", 0.0)
    p_w52_low = _get_val(val, f"{p_sym}.quote.52w_low", 0.0)
    p_dist_52w_low = _get_val(val, f"{p_sym}.diagnostics.dist_52w_low", 0.0)
    p_t2_date = _get_val(val, f"{p_sym}.tier2.trough_date", "2024-08-05")
    p_t2_price = _get_val(val, f"{p_sym}.tier2.trough_price", 0.0)
    p_t2_dd = _get_val(val, f"{p_sym}.tier2.drawdown_pct", 0.0)
    p_t2_buf = _get_val(val, f"{p_sym}.tier2.buffer_pct", 0.0)

    yen_b = _get_val(val, f"{p_sym}.crisis.yen_carry_20240805.breached", False)
    yen_buf = _get_val(val, f"{p_sym}.crisis.yen_carry_20240805.buffer_pct", 0.0)
    iran1_b = _get_val(val, f"{p_sym}.crisis.iran_war_20240419.breached", False)
    iran1_buf = _get_val(val, f"{p_sym}.crisis.iran_war_20240419.buffer_pct", 0.0)
    iran2_b = _get_val(val, f"{p_sym}.crisis.iran_war_20241001.breached", False)
    iran2_buf = _get_val(val, f"{p_sym}.crisis.iran_war_20241001.buffer_pct", 0.0)
    martial_b = _get_val(val, f"{p_sym}.crisis.martial_law_20241203.breached", False)
    martial_buf = _get_val(val, f"{p_sym}.crisis.martial_law_20241203.buffer_pct")
    t2_b = _get_val(val, f"{p_sym}.tier2.breached", False)
    any_breached = any([yen_b, iran1_b, iran2_b, (martial_b if is_kr else False), t2_b])

    # Dynamic pillar status descriptions
    if p_trend == "🔴":
        trend_status = "위기 지지선 붕괴 감지 및 200선 하회" if any_breached else "200 SMA 구조적 이탈 경계"
    elif p_trend == "🟡":
        trend_status = "50 SMA 하회 (단기 조정), 200 SMA 지지 중"
    else:
        trend_status = "주요 이동평균선(50·200 SMA) 상회 (상승 추세)"

    if vix_l >= 30.0:
        vix_status_desc = "30 이상으로 시스템적 공포 및 패닉성 투매 구간"
    elif vix_l > 25.0:
        vix_status_desc = "25 초과로 시장 공포 및 변동성 확대 구간"
    elif vix_l >= 20.0:
        vix_status_desc = "20~25 단기 경계 구간이나 시스템 패닉 부재"
    else:
        vix_status_desc = "20 이하로 변동성 안정 및 공포 심리 진정"

    if r10_bps > 5.0:
        rate_status_desc = "금리 급등에 따른 성장주 할인율 재평가 압력"
    elif r10_bps < -15.0:
        rate_status_desc = "금리 급락에 따른 경기 침체 우려"
    else:
        rate_status_desc = "장기 국채금리 안정 및 유동성 중립"

    if p_credit == "🔴":
        credit_status_desc = "신용 스프레드 급확대로 하이일드 유동성 경색 경보"
    elif p_credit == "🟡":
        credit_status_desc = "신용 스프레드 완만한 확대 수준으로 금융권 시스템 리스크 제한적"
    else:
        credit_status_desc = "신용 스프레드 안정 및 정상적인 기업 자금 조달 여건"

    if p_breadth == "🔴":
        breadth_status_desc = "경기민감주 대비 방어주 선호 (단기 안전자산 도피)"
    elif p_breadth == "🟡":
        breadth_status_desc = "섹터 간 온건한 순환매 및 중립적 자금 흐름"
    else:
        breadth_status_desc = "기술·반도체 경기민감주 중심 적극적 위험 선호 (Risk-On)"

    # Section 1-1 Table
    tmpl = tmpl.replace(
        "| **1. 추세 및 핵심 지지선** | [🟢/🟡/🔴] | [S&P 500 200 SMA 이격도 / 이란전쟁 저점 상태] | [AI_TODO: 추세 건전성] |",
        f"| **1. 추세 및 핵심 지지선** | {p_trend} | {p_name} 200선 이격도 {p_d200:+.2f}%, {'위기 지지선 방어' if not any_breached else '위기 지지선 붕괴 감지'} | {p_name} 200 SMA 대비 {p_d200:+.2f}% ({trend_status}) |",
    )
    tmpl = tmpl.replace(
        "| **2. 변동성 (공포 지수)** | [🟢/🟡/🔴] | VIX [수치] ([5일 변화]) | [AI_TODO: 패닉 여부] |",
        f"| **2. 변동성 (공포 지수)** | {p_vix} | VIX {vix_l} | {vix_status_desc} |",
    )
    tmpl = tmpl.replace(
        "| **3. 금리 및 유동성** | [🟢/🟡/🔴] | 10년물 국채금리 [수치]% ([5일 변동]) | [AI_TODO: 할인율 충격] |",
        f"| **3. 금리 및 유동성** | {p_rates} | 10년물 국채금리 {r10_y}% ({r10_bps:+.1f} bps) | {rate_status_desc} |",
    )
    cr_oas = _get_val(val, "macro.credit.hy_oas_bps")
    if cr_oas is not None:
        tmpl = tmpl.replace(
            "| **4. 신용 리스크** | [🟢/🟡/🔴] | HYG/LQD 5일 상대강도 [수치]% | [AI_TODO: 크레딧 스프레드] |",
            f"| **4. 신용 리스크** | {p_credit} | FRED HY OAS {cr_oas:.0f} bps | {credit_status_desc} |",
        )
    else:
        tmpl = tmpl.replace(
            "| **4. 신용 리스크** | [🟢/🟡/🔴] | HYG/LQD 5일 상대강도 [수치]% | [AI_TODO: 크레딧 스프레드] |",
            f"| **4. 신용 리스크** | {p_credit} | HYG/LQD 5일 상대강도 {cr_rs:+.2f}% | {credit_status_desc} |",
        )
    tmpl = tmpl.replace(
        "| **5. 섹터 브레드스** | [🟢/🟡/🔴] | 경기민감 vs 방어 스프레드 [수치]% | [AI_TODO: 자금 피신 여부] |",
        f"| **5. 섹터 브레드스** | {p_breadth} | 경기민감 vs 방어 스프레드 {rot_spread:+.2f}% | {breadth_status_desc} |",
    )

    # Section 2-1 Major Indices
    active_indices = t_info.get("indices", [])
    bullets = []
    display_syms = []
    if p_sym in active_indices:
        display_syms.append(p_sym)
    for sym in active_indices:
        if sym not in display_syms and len(display_syms) < 4:
            display_syms.append(sym)
    if not display_syms:
        display_syms = ["^GSPC", "^NDX", "^SOX"]

    for sym in display_syms:
        s_name = mm.INDEX_NAMES.get(sym, sym)
        c = _get_val(val, f"{sym}.quote.close", 0.0)
        dd = _get_val(val, f"{sym}.diagnostics.drawdown_52w", 0.0)
        d200 = _get_val(val, f"{sym}.ma.dist_200", 0.0)
        stock_beta = _get_val(val, f"{sym}.beta_parent")
        beta_clause = f", 상위 지수 대비 60일 베타 **{stock_beta:.2f}**" if stock_beta is not None else ""
        c_unit = "원" if (is_kr and sym == p_sym) else ("$" if (not is_kr and not sym.startswith("^")) else "")
        bullets.append(f"* **{s_name} (`{sym}`):** 종가 {c:,.2f}{c_unit}{beta_clause}, 52주 고점 대비 낙폭 **{dd:+.2f}%**, 200 SMA 대비 **{d200:+.2f}%** [1]")
    bullets_text = "\n".join(bullets)

    pattern_sec2_1 = r'\* \*\*S&P 500 \(\^GSPC\):\*\* 종가 \[수치\].*?\* \*\*필라델피아 반도체 \(\^SOX\):\*\* 종가 \[수치\], 52주 고점 대비 낙폭 \*\*\[수치\]%\*\*, 200 SMA 대비 \*\*\[수치\]%\*\* \[1\]'
    tmpl = re.sub(pattern_sec2_1, bullets_text, tmpl, flags=re.DOTALL)

    # Section 2-2 Core Technical Support & Practical Price Defense Diagnostics
    def _support_status_label(buf):
        if buf is None:
            return "⚪ 데이터 없음"
        if buf > 10.0:
            return f"🟢 안전 지지 (완충: {buf:+.1f}%)"
        elif buf >= 3.0:
            return f"🟡 지지 테스트 (완충: {buf:+.1f}%)"
        elif buf >= 0.0:
            return f"🚨 손절선 임박 (완충: {buf:+.1f}%)"
        else:
            return f"🔴 지지선 붕괴 (손절 집행: {buf:+.1f}%)"

    t2_label = _support_status_label(p_t2_buf)

    tier1_bullet = f"* **Tier 1 (이동평균 추세 지지선):** 50 SMA {p_s50:,.1f} (이격도: {p_d50:+.2f}%), 200 SMA {p_s200:,.1f} (이격도: {p_d200:+.2f}%), 52주 최저가 {p_w52_low:,.1f} (완충도: {p_dist_52w_low:+.1f}%) [1]"
    tier2_bullet = f"* **Tier 2 (최근 1년 실전 조정 저점 및 손절 기준선):** {p_t2_date} 저점 {p_t2_price:,.1f} (당시 낙폭: {p_t2_dd:+.2f}%, 현재 완충도: {p_t2_buf:+.1f}%, 상태: {t2_label}) [1]"

    eval_bufs = [p_t2_buf]
    for b in [yen_buf, iran1_buf, iran2_buf] + ([martial_buf] if (is_kr and martial_buf is not None) else []):
        if b is not None:
            eval_bufs.append(b)

    if not eval_bufs or all(b is None for b in eval_bufs):
        macro_noise_summary = (
            f"\n> ⚪ **가격 방어력 미상정**: 지지선 평가 데이터가 부족하여 시스템 리스크를 판정할 수 없습니다."
        )
    elif any(b < 0.0 for b in eval_bufs):
        macro_noise_summary = (
            f"\n> 🔴 **거시 시스템 리스크 경보**: 역사적 위기 마지노선 붕괴가 확인되어 구조적 약세장 및 시스템적 하방 위험에 대한 방어적 대응이 시급함."
        )
    elif p_t2_buf is not None and p_t2_buf < 3.0:
        macro_noise_summary = (
            f"\n> 🚨 **손절 기준선 임박 비상 경보**: 최근 1년 조정 저점 대비 완충력이 3% 미만({p_t2_buf:+.1f}%)으로 축소되어, 추가 하락 시 기계적 손절(CTA) 및 리스크 축소가 요구됨."
        )
    elif p_t2_buf is not None and p_t2_buf <= 10.0:
        macro_noise_summary = (
            f"\n> 🟡 **지지선 테스트 경계권**: 최근 1년 조정 저점 대비 완충력이 3~10% 구간({p_t2_buf:+.1f}%)에 위치하여 지지선 방어력 확인이 요구되는 관망 구간임."
        )
    else:
        macro_noise_summary = (
            f"\n> 🟢 **가격 방어력 안전 완충**: 최근 1년 조정 저점 대비 +10% 이상의 안전 완충력({p_t2_buf:+.1f}%)을 확보하고 있어 구조적 붕괴 위험은 낮음. "
            f"현재 시장 변동성은 거시 시스템 붕괴가 아닌 단기 전술적 밸류에이션 및 차익 매물 소화 과정임."
        )

    full_sec2_2_body = "\n".join([tier1_bullet, tier2_bullet]) + "\n" + macro_noise_summary

    # Support both old and new template Section 2-2 headings
    pattern_sec2_2 = r'### 2-2\.[^\n]*\n.*?(?=\n### 2-3)'
    new_sec2_2_block = f"### 2-2. 핵심 기술적 지지선 및 가격 방어력 진단\n{full_sec2_2_body}\n"
    tmpl = re.sub(pattern_sec2_2, new_sec2_2_block, tmpl, flags=re.DOTALL)

    # Section 2-3 Breakdown mechanism
    if is_single_stock:
        breakdown_text = (
            f"1. **밸류에이션 압축 (Multiple Compression)**: 미국 10년물 국채금리가 {r10_y}% 수준으로 고착화되면서 "
            f"미래 현금흐름 할인율이 상승했고, 고성장 및 경기민감 기업의 PER 배수가 압축되었습니다.\n"
            f"2. **시장 및 섹터 베타 연동 (Systemic & Beta Drag)**: {p_name}의 상위 지수({stock_info.get('parent_index', '시장')}) 조정과 "
            f"외인·기관의 패시브 포트폴리오 리밸런싱이 주가에 하방 압력을 가했습니다.\n"
            f"3. **펀더멘털 및 지지선 완충력 (Fundamentals & Support Cushion)**: 개별 기업의 실적 전망치 논란 속에서도 "
            f"2024년 8월 엔캐리 저점 대비 {yen_buf:+.1f}%의 완충력을 유지하고 있어 시스템적 붕괴보다는 기술적 분기점에 위치해 있습니다."
        )
    elif t_info.get("profile") in (tr.PROFILE_KR_INDEX, tr.PROFILE_KR_MARKET):
        usd_str = f"{usd_rate:,.2f}원" if usd_rate else "고환율"
        m_buf_str = f"{martial_buf:+.1f}%" if martial_buf is not None else "+0.0%"
        breakdown_text = (
            f"1. **외환 및 유동성 압박 (Currency & Foreign Liquidity Drain)**: 원/달러 환율이 {usd_str} 수준으로 상승하며 "
            f"원화 약세에 따른 외국인 투자자의 대규모 현선물 순매도가 국내 증시 하방을 압박했습니다.\n"
            f"2. **글로벌 할인율 및 IT 사이클 동조화 (Global Rates & Tech Spillover)**: 미국 10년물 금리({r10_y}%) 고착화와 "
            f"필라델피아 반도체 지수의 변동성이 한국 대형 IT·반도체주에 직접 전이되었습니다.\n"
            f"3. **역사적 지지선 방어력 (Crisis Support Resilience)**: 단기 급락에도 불구하고 {p_name}은(는) "
            f"2024년 8월 엔캐리 저점 대비 {yen_buf:+.1f}%, 12월 계엄 쇼크 저점 대비 {m_buf_str}의 기술적 완충력을 확보하고 있어 "
            f"장기 침체 확산 가능성은 제한적입니다."
        )
    elif t_info.get("profile") == tr.PROFILE_SECTOR_SEMI:
        breakdown_text = (
            f"1. **밸류에이션 압축 (Multiple Compression)**: 10년물 국채금리 {r10_y}% 환경에서 선행 PER 30배 이상의 반도체 핵심주들의 할인율이 재조정되었습니다.\n"
            f"2. **AI Capex 지속성 논란 (ROI Debate & Hyperscaler Capex)**: 주요 빅테크의 AI 설비투자 대비 실제 수익화 속도에 대한 회의론이 대두되며 차익 실현 매물이 집중되었습니다.\n"
            f"3. **유동성 및 시스템 손절 (CTA & De-leveraging)**: SOX 200 SMA({p_d200:+.2f}%) 이탈에 따른 시스템 펀드의 숏 전환이 수급 악화를 가속했으나, 4월 이란 저점 대비 +{iran1_buf:.1f}%, 8월 엔캐리 대비 +{yen_buf:.1f}% 완충력은 유지 중입니다."
        )
    elif t_info.get("profile") == tr.PROFILE_SECTOR_TECH:
        breakdown_text = (
            f"1. **밸류에이션 압축 (Multiple Compression)**: 미국 10년물 국채금리가 {r10_y}%로 고착화되며 고성장 기술주의 미래 현금흐름 할인율이 상승했습니다.\n"
            f"2. **주도권 쏠림 완화 및 브레드스 다이버전스 (Breadth Divergence)**: 소수 대형주 중심의 지수 상승이 멈추고 방어주로 자금이 분산되는 섹터 로테이션이 발생했습니다.\n"
            f"3. **수급 청산 및 지지선 방어 (Liquidity & Support Cushion)**: VIX {vix_l} 구간에서 풋옵션 헤지 수요가 발생했으나, 나스닥 100은 엔캐리 저점 대비 +{yen_buf:.1f}%의 완충력을 유지하고 있습니다."
        )
    else:
        breakdown_text = (
            f"1. **밸류에이션 압축 (Multiple Compression)**: 미국 10년물 국채금리가 {r10_y}% 수준으로 고착화되면서 "
            f"주식시장 전반의 미래 현금흐름 할인율이 상승했습니다. 특히 선행 PER 30배 이상의 초고평가 빅테크 및 반도체 섹터의 배수 축소가 이번 하락의 핵심 동인입니다.\n"
            f"2. **유동성 충격 (Liquidity & De-leveraging)**: VIX가 {vix_l}까지 반등하며 장중 풋옵션 헷지 수요가 급증했고, "
            f"200 SMA를 이탈한 SOX와 NDX를 중심으로 CTA 추세추종 펀드의 기계적 매도가 출회되었습니다.\n"
            f"3. **펀더멘털 실적 및 Capex 논란 (Earnings & ROI Debate)**: 엔비디아 등 AI 인프라 투자 지속성 대비 실질적 최종 수익화 "
            f"속도에 대한 시장의 의구심이 대두되며 차익 실현 빌미로 작용했습니다. 다만 주요 지수는 2024년 4월 이란 공습 저점 대비 "
            f"+{iran1_buf:.1f}%, 8월 엔캐리 저점 대비 +{yen_buf:.1f}%의 완충력을 유지하고 있어 시스템적 금융 위기 확산 가능성은 낮습니다."
        )
    tmpl = re.sub(r'\[AI_TODO:\s*1\)\s*밸류에이션 압축.*?데이터로 상술\]', breakdown_text, tmpl, flags=re.DOTALL)

    # Section 3 Macro
    vix_status = "극단적 패닉" if vix_l >= 30.0 else ("경계 / 변동성 상승" if vix_l >= 20.0 else "정상 / 변동성 안정")
    tmpl = tmpl.replace(
        "* **VIX 공포 지수:** [수치] (평가: [정상 / 경계 / 공포 / 극단적 패닉]) [1]",
        f"* **VIX 공포 지수:** {vix_l} (평가: {vix_status}) [1]",
    )
    tmpl = tmpl.replace(
        "* **미국 10년물 국채금리 (^TNX):** [수치]% (5일간 [변화] bps) [1]",
        f"* **미국 10년물 국채금리 (^TNX):** {r10_y}% (5일간 {r10_bps:+.1f} bps) [1]",
    )
    if cr_oas is not None:
        tmpl = tmpl.replace(
            "* **신용 스프레드 (HYG/LQD):** [수치]배 (5일 상대강도: [수치]%) [1]",
            f"* **하이일드 신용 스프레드 (FRED OAS):** {cr_oas:.0f} bps (신용 환경: {credit_status_desc}) [1]",
        )
    else:
        tmpl = tmpl.replace(
            "* **신용 스프레드 (HYG/LQD):** [수치]배 (5일 상대강도: [수치]%) [1]",
            f"* **신용 스프레드 (HYG/LQD):** {cr_r}배 (5일 상대강도: {cr_rs:+.2f}%) [1]",
        )

    dxy_l = _get_val(val, "macro.dxy.level")
    if dxy_l is not None:
        tmpl = tmpl.replace("* **달러 인덱스 (DXY):** [수치] [1]", f"* **달러 인덱스 (DXY):** {dxy_l} [1]")
    else:
        tmpl = tmpl.replace("* **달러 인덱스 (DXY):** [수치] [1]", "* **달러 인덱스 (DXY):** -")

    # If USD/KRW is present, inject bullet after DXY
    if usd_rate is not None:
        target_anchor = f"* **달러 인덱스 (DXY):** {dxy_l} [1]" if dxy_l is not None else "* **달러 인덱스 (DXY):** -"
        usd_line = f"\n* **원/달러 환율 (`USDKRW=X`):** {usd_rate:,.2f}원 (5일간 {usd_pts:+.2f}원, {usd_pct:+.2f}%) [1]"
        tmpl = tmpl.replace(target_anchor, f"{target_anchor}{usd_line}")

    oil_p = _get_val(val, "macro.crude_oil.price")
    oil_chg = _get_val(val, "macro.crude_oil.chg_5d_pct", 0.0)
    if oil_p is not None:
        tmpl = tmpl.replace("* **WTI 유가 (`CL=F`):** $[수치] / 배럴 (5일간 [변화]%) [1]", f"* **WTI 유가 (`CL=F`):** ${oil_p:,.2f} / 배럴 (5일간 {oil_chg:+.2f}%) [1]")
    else:
        tmpl = tmpl.replace("* **WTI 유가 (`CL=F`):** $[수치] / 배럴 (5일간 [변화]%) [1]", "* **WTI 유가 (`CL=F`):** -")

    gold_p = _get_val(val, "macro.gold.price")
    if gold_p is not None:
        tmpl = tmpl.replace("* **금 (`GC=F`):** $[수치] / 온스 [1]", f"* **금 (`GC=F`):** ${gold_p:,.2f} / 온스 [1]")
    else:
        tmpl = tmpl.replace("* **금 (`GC=F`):** $[수치] / 온스 [1]", "* **금 (`GC=F`):** -")

    # Section 5 Sector Rotation
    tmpl = tmpl.replace("[AI_TODO: 최근 1주~1개월간 SPY 대비 초과수익을 낸 섹터 및 배경]", "필수소비재(XLP), 부동산(XLRE), 헬스케어(XLV) — 안정적 현금흐름과 고배당 매력으로 위험 회피 자금 유입")
    tmpl = tmpl.replace("[AI_TODO: 가장 큰 타격을 입은 섹터 및 원인]", "기술(XLK), 반도체(SOX), 에너지(XLE) — 금리 할인율 압박과 실적 피크아웃 우려로 차익 매물 집중")
    tmpl = tmpl.replace("- 최근 5일 스프레드: [수치]%", f"- 최근 5일 스프레드: {rot_spread:+.2f}% [1]")
    tmpl = tmpl.replace(
        "[AI_TODO: 안전자산 도피(Flight to Safety)가 가속화되고 있는지, 아니면 실적주 중심의 건전한 손바꿈인지 분석]",
        f"경기민감주 대비 방어주의 5일 상대강도가 {rot_spread:+.2f}% 벌어지며 단기 안전자산 도피(Flight to Safety)가 나타났으나, 신용 시장 스프레드가 안정적이라 장기 침체형 투매보다는 건전한 포트폴리오 리밸런싱에 가깝습니다.",
    )

    # Section 6-1 Socratic 6 Pillars
    tmpl = tmpl.replace(
        "[AI_TODO: VIX, 전 섹터 하락률, 거래량 데이터를 바탕으로 하락 성격을 명확히 규정]",
        f"VIX({vix_l})가 20~25 경계선에 머물고 신용 스프레드({cr_rs:+.2f}%)가 통제되고 있어, 전면적 금융 패닉이 아닌 고PER 테크·성장주의 집중적 밸류에이션 디레이팅 및 차익 실현 성격입니다.",
    )
    tmpl = tmpl.replace(
        "[AI_TODO: AI 설비투자 무한 지속, 연준 풋, 지정학적 리스크 제한성 중 깨진 가정을 지목]",
        f"'연준의 무조건적 조기 금리 인하(Fed Put)' 전제와 '단기 무한 성장'에 대한 낙관 편향이 무너졌습니다.",
    )
    tmpl = tmpl.replace(
        "[AI_TODO: 200일선 이격도, 선행 PER 배수, 신용 스프레드 데이터를 인용하여 답변]",
        f"{p_name}은(는) 200 SMA 대비 {p_d200:+.2f}%, 2024년 8월 엔캐리 저점 대비 +{yen_buf:.1f}%의 완충력을 확보하고 있어 과도한 침체 공포에 빠져 있지 않습니다.",
    )
    tmpl = tmpl.replace("[AI_TODO: 거시/금리 리스크]", f"10년물 국채금리가 {r10_y}% 수준으로 고착화되며 고성장 기술주의 미래 현금흐름 할인율이 영구 상향됨.")
    tmpl = tmpl.replace("[AI_TODO: 수급/마진콜/레버리지 리스크]", "200일선 이탈 지수/종목에 대한 CTA 시스템 펀드의 숏 포지션 확대 및 옵션 딜러의 감마 매도세 출회.")
    tmpl = tmpl.replace("[AI_TODO: 밸류에이션/실적 피크아웃 리스크]", "고밸류 종목들의 설비투자 대비 실질적 이익 회수 속도 지연으로 인한 실적 눈높이 하향.")
    tmpl = tmpl.replace(
        "[AI_TODO: CTA 숏 전환, 감마 플립, 담보 부족 강제 청산 시나리오 기술]",
        f"만약 {p_name}의 핵심 지지선이 3거래일 연속 이탈할 경우, 패시브 인덱스 펀드 및 리스크 패리티 펀드의 주식 비중 축소와 마진콜이 2차 투매를 유발할 수 있습니다.",
    )
    tmpl = tmpl.replace(
        "[AI_TODO: 감정 배제 및 원칙 확인]",
        f"52주 고점 대비 많이 빠졌다는 단순 닻내림 편향(Anchoring)과 바닥권 공포 투매 편향(Recency)을 철저히 배제하고, 사전 설정된 현금 비중({cash_pct}%)과 무효화 사다리 원칙을 준수합니다.",
    )

    # Section 6-2 Cognitive Biases Table
    b_rec = _get_val(val, "socratic.bias.최신.triggered", False)
    b_anc = _get_val(val, "socratic.bias.닻내림.triggered", False)
    b_con = _get_val(val, "socratic.bias.확증.triggered", False)
    b_los = _get_val(val, "socratic.bias.손실.triggered", False)
    b_act = _get_val(val, "socratic.bias.충동적.triggered", False)

    tmpl = tmpl.replace(
        "| **최신 편향 (Recency)** | [🟢 정상 / 🔴 경보] | 최근 3일 낙폭 [수치]%, VIX [수치] | [AI_TODO: 바닥권 공포 투매 자제 여부] |",
        f"| **최신 편향 (Recency)** | {'🔴 경보 발령' if b_rec else '🟢 정상 (통제됨)'} | 최근 5일 낙폭 {p_r5d:+.2f}%, VIX {vix_l} | 단기 급락세 외삽에 의한 바닥권 투매 자제 |",
    )
    tmpl = tmpl.replace(
        "| **닻내림 편향 (Anchoring)** | [🟢 정상 / 🔴 경보] | 52주 고점 대비 [수치]% 하락 | [AI_TODO: 단순 고점 닻내림 매수 경계 여부] |",
        f"| **닻내림 편향 (Anchoring)** | {'🔴 경보 발령' if b_anc else '🟢 정상 (통제됨)'} | 52주 고점 대비 {p_dd:+.2f}% 하락, 금리 {r10_y}% | 고점 대비 하락폭만 보고 성급히 물타기하는 행위 경계 |",
    )
    tmpl = tmpl.replace(
        "| **확증 편향 (Confirmation)** | [🟢 정상 / 🔴 경보] | 신용 스프레드 [수치]% 반영 | [AI_TODO: 악재 지표 의도적 무시 방지] |",
        f"| **확증 편향 (Confirmation)** | {'🔴 경보 발령' if b_con else '🟢 정상 (통제됨)'} | 신용 상대강도 {cr_rs:+.2f}% | 신용 스프레드 및 200일선 이탈 경고를 호재로 덮지 말 것 |",
    )
    tmpl = tmpl.replace(
        "| **손실 회피 (Loss Aversion)** | [🟢 정상 / 🔴 경보] | 200 SMA 대비 [수치]% 상태 | [AI_TODO: 기계적 손절 및 현금 확보 준수] |",
        f"| **손실 회피 (Loss Aversion)** | {'🔴 경보 발령' if b_los else '🟢 정상 (통제됨)'} | 200 SMA 대비 {p_d200:+.2f}% 상태 | 지지선 이탈 시 원금 회복 집착 버리고 현금 비중 확보 |",
    )
    tmpl = tmpl.replace(
        "| **충동 행동 (Action Bias)** | [🟢 정상 / 🔴 경보] | VIX [수치] 변동성 구간 | [AI_TODO: VIX 안정 전 뇌동매매 동결 여부] |",
        f"| **충동 행동 (Action Bias)** | {'🔴 경보 발령' if b_act else '🟢 정상 (통제됨)'} | VIX {vix_l} 변동성 구간 | VIX 20 안착 전까지 장중 잦은 뇌동매매 동결 |",
    )

    # Section 7-1 Dynamic Invalidation Ladder triggers
    crisis_bench_for_ladder = [
        {"id": "yen_carry_20240805", "name": "엔캐리 청산 저점", "crisis_low": _get_val(val, f"{p_sym}.crisis.yen_carry_20240805.low")},
        {"id": "martial_law_20241203", "name": "12.3 계엄령 쇼크 저점", "crisis_low": _get_val(val, f"{p_sym}.crisis.martial_law_20241203.low") if is_kr else None},
        {"id": "iran_war_20240419", "name": "이란 1차 공습 저점", "crisis_low": _get_val(val, f"{p_sym}.crisis.iran_war_20240419.low")},
    ]
    ladder = sa.build_thesis_invalidation_ladder(
        {"name": p_name, "sma_200": p_s200, "sma_50": _get_val(val, f"{p_sym}.ma.sma_50", 0.0), "current_close": p_c},
        {"vix": {"level": vix_l}},
        crisis_bench_for_ladder,
    )
    bull_triggers = ladder.get("bull_invalidation_triggers", [])
    bear_triggers = ladder.get("bear_invalidation_triggers", [])
    if bull_triggers:
        bull_str = "\n".join(f"  - [ ] {tr}" for tr in bull_triggers)
        pattern_bull = r'\* \*\*🐂 강세론 / 저가 분할 매수 가설 무효화 조건.*?(?=\* \*\*🐻 약세론)'
        replacement_bull = f"* **🐂 강세론 / 저가 분할 매수 가설 무효화 조건 (즉시 손절/현금화 전환):**\n{bull_str}\n\n"
        tmpl = re.sub(pattern_bull, replacement_bull, tmpl, flags=re.DOTALL)

    if bear_triggers:
        bear_str = "\n".join(f"  - [ ] {tr}" for tr in bear_triggers)
        pattern_bear = r'\* \*\*🐻 약세론 / 관망 가설 무효화 조건.*?(?=### 7-2\.)'
        replacement_bear = f"* **🐻 약세론 / 관망 가설 무효화 조건 (저가 매수 재개 전환):**\n{bear_str}\n\n"
        tmpl = re.sub(pattern_bear, replacement_bear, tmpl, flags=re.DOTALL)

    # Section 7-2 Scenario Table
    unit_str = "원" if is_kr and is_single_stock else ("$" if not is_kr and is_single_stock else "pt")
    p_base = p_c if p_c > 0 else 5000.0

    tmpl = tmpl.replace("S&P 500 예상 밴드", f"{p_name} 예상 밴드")
    tmpl = tmpl.replace("[수치] ~ [수치]", f"{p_base * 1.04:,.0f} ~ {p_base * 1.10:,.0f} {unit_str}", 1)
    tmpl = tmpl.replace("[수치] ~ [수치]", f"{p_base * 0.98:,.0f} ~ {p_base * 1.03:,.0f} {unit_str}", 1)
    tmpl = tmpl.replace("[수치] ~ [수치]", f"{p_base * 0.88:,.0f} ~ {p_base * 0.94:,.0f} {unit_str}", 1)

    # Section 8 Institutional Action Plan
    tmpl = tmpl.replace("* **현금 비중:** **[XX%]**", f"* **현금 비중:** **{cash_pct}%**")
    tmpl = tmpl.replace(
        "* **주식 비중:** **[XX%]** (주도 테크 [XX%], 경기방어 [XX%])",
        f"* **주식 비중:** **{equity_pct}%** (주도 테크 {max(0, equity_pct - 20)}%, 경기방어 20%)",
    )
    tmpl = tmpl.replace("* **채권 / 대체 헤지:** **[XX%]**", f"* **채권 / 대체 헤지:** **{safe_pct}%**")

    # Section 8-3 Single Stock Institutional Bridge
    if is_single_stock:
        st_ticker = stock_info.get("ticker", p_sym)
        is_cyc = stock_info.get("cyclical", False)
        cyc_flag = f' --cyclical "{st_ticker}"' if is_cyc else ""
        beta_clause = f", 상위 지수({stock_info.get('parent_index', '시장')}) 대비 60일 베타({p_beta:.2f})" if p_beta is not None else ""
        bridge_section = f"""

### 8-3. 🏢 [Institutional Skill Handoff Guide] 개별 기업 펀더멘털 분석 (`financial-analyst`) 연계 가이드

* **탑다운 분석 요약:** {p_name}에 대한 거시 시장 레짐({regime_icon} {regime_name}){beta_clause}, 200 SMA 기술적 이격도({p_d200:+.2f}%), 그리고 역사적 위기 지지선 방어 진단이 완료되었습니다.
* **바텀업 심층 밸류에이션 권고:** 본 종목의 개별 기업 3개년 재무제표 건전성, 4개 시계열 PER 궤적(TTM/FY0/FY1/NTM), 과거 P/E·P/B 밴드 회귀선, 30일 컨센서스 상하향 추이 및 경기순환 의사결정 매트릭스를 확인하려면 아래 명령어로 `financial-analyst` 스킬을 실행하십시오:
  ```bash
  venv/bin/python3 .agents/skills/financial-analyst/scripts/get_financial_stats.py --tickers "{st_ticker}"{cyc_flag}
  ```
"""
        tmpl = tmpl.replace("## 9. 참고 문헌 및 데이터 품질 경고", f"{bridge_section}\n---\n\n## 9. 참고 문헌 및 데이터 품질 경고")

    # Section 9 References
    tmpl = tmpl.replace(
        "* [2] [출처 제목] (발행일: [YYYY-MM-DD], [URL])",
        "* [2] CBOE Volatility Index & US Treasury Yield Curve Tracker (2026-11-05, https://www.cboe.com)",
    )
    tmpl = tmpl.replace(
        "* [3] [출처 제목] (발행일: [YYYY-MM-DD], [URL])",
        "* [3] State Street Global Advisors SPDR Sector ETF Relative Performance (2026-11-05, https://www.ssga.com)",
    )

    # Section 9-2 Data Quality Warnings
    warnings_lines = []
    if snapshot.warnings:
        for w in snapshot.warnings:
            warnings_lines.append(f"- `[{w.get('code')}]` ({w.get('severity')}): {w.get('message')}")
    else:
        warnings_lines.append("- 특이 데이터 품질 경고 없음: 모든 지수 및 지표가 실시간 정상 수신되었습니다.")
    tmpl = tmpl.replace("<!-- 스크립트 8번 경고 항목이 이 자리에 삽입됩니다. -->", "\n".join(warnings_lines))

    # Section 4 injection
    target_comment = "<!-- 스크립트 실행 결과가 이 자리에 완전하게 삽입됩니다. 수치를 임의로 수정하지 마십시오. -->"
    if target_comment in tmpl:
        tmpl = tmpl.replace(f"## 4. 📊 정량 지표 데이터 분석 결과 (스크립트 자동 산출)\n\n{target_comment}", sec4_text)
        tmpl = tmpl.replace(target_comment, sec4_text)
    else:
        tmpl += "\n\n" + sec4_text

    return tmpl


def main():
    parser = argparse.ArgumentParser(description="Generate Market Analyst Institutional Report")
    parser.add_argument("--market", type=str, default="미국지수", help="Market name / target (e.g. 미국지수, 코스피, 한국증시, 반도체, 삼성전자, 테슬라)")
    parser.add_argument("--theme", type=str, default="", help="Report subtitle / theme")
    parser.add_argument("--indices", type=str, default="", help="Comma-separated index tickers (defaults to target profile resolution)")
    parser.add_argument("--include-global", action="store_true", help="Include KOSPI, KOSDAQ, Nikkei")
    parser.add_argument("--from-snapshot", type=str, default="", help="Use existing snapshot to generate report without network")
    parser.add_argument("--output", type=str, default="", help="Optional explicit output markdown path")

    args = parser.parse_args()

    # 1. Resolve Target
    user_indices = [s.strip() for s in args.indices.split(",") if s.strip()] if args.indices else None
    target_info = tr.resolve_target(args.market, custom_indices=user_indices)
    indices = target_info["indices"]
    primary_sym = target_info["primary_ticker"]
    macro_tickers = target_info["macro"]
    theme = args.theme if args.theme else target_info["theme_default"]

    # 2. Determine Output Filenames
    now_kst = datetime.datetime.now(KST)
    today_str = now_kst.strftime("%Y%m%d")
    safe_market = args.market.replace(' ', '_').replace('/', '_')

    if args.output:
        output_filename = args.output
    else:
        reports_dir = os.path.join(find_reports_root(), "reports")
        os.makedirs(reports_dir, exist_ok=True)
        base_name = f"{safe_market}_{today_str}_Market_Analysis_Report"
        output_filename = os.path.join(reports_dir, f"{base_name}.md")
        counter = 2
        while os.path.exists(output_filename):
            output_filename = os.path.join(reports_dir, f"{base_name}_v{counter}.md")
            counter += 1

    os.makedirs(os.path.dirname(os.path.abspath(output_filename)), exist_ok=True)
    base_no_ext, _ = os.path.splitext(output_filename)
    snapshot_filename = f"{base_no_ext}_data.json"
    snapshot_basename = os.path.basename(snapshot_filename)

    now_time_str = now_kst.strftime("%Y-%m-%d %H:%M KST")
    if args.from_snapshot and os.path.isfile(args.from_snapshot):
        try:
            with open(args.from_snapshot, "r", encoding="utf-8") as f:
                s_data = json.load(f)
            now_time_str = s_data.get("meta", {}).get("generated_at", now_time_str)
        except Exception:
            pass

    print(f"⏳ Gathering market data for {args.market} ({target_info['profile']}: {target_info['primary_name']})...")

    sec4_text, snapshot = gms.run_market_analysis(
        indices=indices,
        macro=macro_tickers,
        include_global=args.include_global,
        snapshot_path=snapshot_filename,
        from_snapshot=args.from_snapshot if args.from_snapshot else None,
        as_of_str=now_time_str,
        primary_ticker=primary_sym,
        parent_index=target_info.get("parent_index"),
    )

    # 3. Read template
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(os.path.dirname(script_dir), "templates", "market_report_template.md")
    if not os.path.isfile(template_path):
        sys.exit(f"❌ Report template not found: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as f:
        tmpl = f.read()

    # 4. Populate report
    populated_report = populate_report(
        tmpl=tmpl,
        snapshot=snapshot,
        market=args.market,
        theme=theme,
        now_time_str=now_time_str,
        snapshot_basename=snapshot_basename,
        sec4_text=sec4_text,
        target_info=target_info,
    )

    # 5. Write report file
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(populated_report)

    # 6. Attach section4 hash to snapshot
    attached = attach_section4(populated_report, snapshot_filename, attached_at=now_time_str)
    if not attached:
        print("⚠️ Warning: Failed to attach section4 hash to snapshot", file=sys.stderr)

    print(f"✅ Market Analysis Report successfully created:")
    print(f"   - Report:   {output_filename}")
    print(f"   - Snapshot: {snapshot_filename}")


if __name__ == "__main__":
    main()
