"""
Socratic interrogation and cognitive bias auditing engine:
Implements 6 Socratic pillars, 5 cognitive bias detectors,
and generates the quantitative Thesis Invalidation Ladder.
"""

from typing import Any, Dict, List, Optional


def audit_cognitive_biases(
    sp500_metrics: Dict[str, Any],
    macro_risk: Dict[str, Any],
    trend_eval: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Check if current price action and macro metrics trigger any of the 5 cognitive biases.
    """
    biases = []

    ret_5d = sp500_metrics.get("ret_5d") or 0.0
    dd_52w = sp500_metrics.get("drawdown_52w") or 0.0
    dist_200 = sp500_metrics.get("dist_200") or 0.0

    vix_lvl = macro_risk.get("vix", {}).get("level") or 0.0
    rate_chg = macro_risk.get("rate_10y", {}).get("chg_5d_bps") or 0.0
    credit_rs = macro_risk.get("credit", {}).get("credit_rs_5d") or 0.0
    crisis_breached = trend_eval.get("any_crisis_breached", False)

    # 1. Recency Bias (최신 편향)
    # Trigger: Recent 5-day drop < -3.0% and VIX > 25.0
    recency_triggered = bool(ret_5d <= -3.0 and vix_lvl >= 24.0)
    ret_desc = f"낙폭 {abs(ret_5d):.2f}%" if ret_5d < 0 else f"상승 +{ret_5d:.2f}%"
    biases.append({
        "bias": "최신 편향 (Recency Bias)",
        "triggered": recency_triggered,
        "evidence": f"최근 5일 {ret_desc}, VIX {vix_lvl:.2f}",
        "distortion": "최근 며칠간의 급락세를 미래로 단순 외삽하여 '영원히 하락할 것'이라는 극단적 비관론에 사로잡혀 바닥권 투매 위험.",
        "prescription": "역사적 변동성 평균 회귀와 200일선 지지 여부를 먼저 확인하고 패닉 장중 매도를 자제하십시오.",
    })

    # 2. Anchoring Bias (닻내림 편향)
    # Trigger: Drawdown > 8% but 10Y yield spiked > 10 bps
    anchoring_triggered = bool(dd_52w <= -8.0 and rate_chg >= 10.0)
    rate_desc = f"+{rate_chg:.1f}bps 변동" if rate_chg >= 0 else f"{rate_chg:.1f}bps 하락"
    biases.append({
        "bias": "닻내림 편향 (Anchoring Bias)",
        "triggered": anchoring_triggered,
        "evidence": f"52주 고점 대비 {dd_52w:+.2f}%, 10년물 금리 5일간 {rate_desc}",
        "distortion": "과거 최고가(52주 신고가)에 닻을 내리고 '고점 대비 많이 빠졌으니 무조건 싸다'고 착각. 금리 급등으로 인한 적정 밸류에이션(할인율) 상향을 무시.",
        "prescription": "단순 고점 대비 가격이 아닌, 금리 상승분을 반영한 내재가치와 선행 PER 밴드를 재산정하십시오.",
    })

    # 3. Confirmation Bias (확증 편향)
    # Trigger: Credit spread deteriorating (< -0.8%) while user or market assumes safe dip-buying
    confirmation_triggered = bool(credit_rs < -0.8)
    cr_desc = "스프레드 확대 경보" if credit_rs < -0.8 else "신용 스프레드 안정"
    biases.append({
        "bias": "확증 편향 (Confirmation Bias)",
        "triggered": confirmation_triggered,
        "evidence": f"HYG/LQD 신용 상대강도 {credit_rs:+.2f}% ({cr_desc})",
        "distortion": "포트폴리오 손실을 회피하기 위해 호재성 뉴스만 찾고, 실질적인 기업 부도 위험을 가리키는 신용 스프레드 악화를 무시.",
        "prescription": "신용 시장(HYG/LQD)이 안정화(상대강도 > 0%)될 때까지 낙관론적 편향을 배제하고 관망하십시오.",
    })

    # 4. Loss Aversion (손실 회피 편향)
    # Trigger: 200 SMA breached (< 0) or support breached or near breakdown (< 3~10%)
    near_breakdown = trend_eval.get("any_near_breakdown", False)
    loss_aversion_triggered = bool(dist_200 < 0 or crisis_breached or near_breakdown)
    if crisis_breached:
        crisis_desc = "주요 저점 지지선 붕괴 감지 (🔴)"
    elif near_breakdown:
        crisis_desc = "손절 기준선 근접 비상 경보 (🚨 <3~10%)"
    else:
        crisis_desc = "핵심 기술적 지지선 안전 방어 (🟢)"
    biases.append({
        "bias": "손실 회피 편향 (Loss Aversion)",
        "triggered": loss_aversion_triggered,
        "evidence": f"200 SMA 이격도 {dist_200:+.2f}%, 지지선 상태: {crisis_desc}",
        "distortion": "손실 확정이 두려워 장기 추세선 및 손절 기준선 붕괴라는 명백한 위험 신호에도 기계적 리스크 관리를 회피하고 '기도 매매'로 전환.",
        "prescription": "원금 회복에 집착하지 말고, 사전 정의된 손절 기준과 현금 비중 가이드(50% 이상)를 엄격히 집행하십시오.",
    })

    # 5. Action Bias (충동적 행동 편향)
    # Trigger: Extreme volatility (VIX >= 28.0)
    action_triggered = bool(vix_lvl >= 28.0)
    act_desc = "변동성 극대 구간" if vix_lvl >= 28.0 else "변동성 통제 구간"
    biases.append({
        "bias": "충동적 행동 편향 (Action Bias)",
        "triggered": action_triggered,
        "evidence": f"VIX {vix_lvl:.2f} ({act_desc})",
        "distortion": "시장 폭풍 속에서 가만히 있지 못하고 잦은 뇌동매매와 손절-재매수를 반복하여 계좌를 갉아먹음.",
        "prescription": "변동성이 가라앉고(VIX < 22 안착) 시장이 방향을 정할 때까지 일체의 뇌동 진입을 동결하십시오.",
    })

    return biases


def generate_socratic_questions(
    index_metrics: List[Dict[str, Any]],
    macro_risk: Dict[str, Any],
    sector_rotation: Dict[str, Any],
    regime_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate the 6 Socratic dialectical examination categories.
    """
    sp500 = next((m for m in index_metrics if m.get("ticker") == "^GSPC"), {})
    sox = next((m for m in index_metrics if m.get("ticker") == "^SOX"), {})

    vix_val = macro_risk.get("vix", {}).get("level", "N/A")
    rate_val = macro_risk.get("rate_10y", {}).get("yield", "N/A")
    rate_bps = macro_risk.get("rate_10y", {}).get("chg_5d_bps", "N/A")
    spread_5d = sector_rotation.get("spread_5d", 0.0)

    # 1. Clarification & Definition
    q1 = {
        "title": "1. 명료화 및 하락 성격 규명 (Clarification & Definition)",
        "question": "이번 급락은 구체적으로 어떤 성격인가? 밸류에이션 디레이팅인가, 유동성 강제 청산인가, 아니면 실적 둔화인가?",
        "context_data": f"S&P 500 5일 등락: {sp500.get('ret_5d')}%, SOX 5일 등락: {sox.get('ret_5d')}%, VIX: {vix_val}",
        "guidance": "VIX가 25를 넘고 전 섹터가 동반 하락했다면 유동성 발작 성격이 짙으며, 반도체/테크만 집중 하락하고 방어주가 견조하다면 금리 상승에 따른 고밸류 압축입니다.",
    }

    # 2. Hidden Assumptions
    q2 = {
        "title": "2. 무너진 숨은 전제 진단 (Probing Hidden Assumptions)",
        "question": "시장 컨센서스와 투자자가 당연시했던 전제 중 이번 급락으로 무너진 것은 무엇인가?",
        "context_data": f"10년물 국채금리: {rate_val}% (5일 변동 {rate_bps}bps), 유가 추이",
        "guidance": "'연준의 무조건적 유동성 지원(Fed Put)', 'AI Capex 무한 성장', '중동 지정학적 리스크의 제한성' 중 실제 데이터와 충돌한 가정을 특정하십시오.",
    }

    # 3. Empirical Evidence
    q3 = {
        "title": "3. 정량적 근거 탐색 (Probing Empirical Evidence)",
        "question": "시장이 과매도 저평가 영역이라는 주장을 뒷받침하는 명확한 숫자는 어디에 있는가?",
        "context_data": f"S&P 500 200 SMA 이격도: {sp500.get('dist_200')}%, 52주 고점 대비 낙폭: {sp500.get('drawdown_52w')}%",
        "guidance": "200 SMA가 아직 깨지지 않았는지, VIX가 역사적 공포 극단치(30+)에 도달했는지 정량 수치로만 답하십시오.",
    }

    # 4. Bear Anti-Thesis
    q4 = {
        "title": "4. 변증법적 반대 논증 (The Bear Anti-Thesis)",
        "question": "나와 반대로 이 시장을 공격적으로 매도한 기관/베어 진영은 무엇을 보고 던졌는가? 그들의 공포는 왜 정당한가?",
        "bear_arguments": [
            f"거시 금리 압박: 10년물 금리가 {rate_val}% 수준으로 고착화되면서 고성장 테크주의 적정 할인율이 영구 상향 조정됨.",
            "수급 및 레버리지 청산: 엔캐리 언와인딩 및 CTA 알고리즘이 숏으로 전환되면서 장중 매수 호가가 실종됨.",
            "실적 피크아웃 논쟁: 빅테크의 AI 인프라 투자 대비 수익화(ROI) 증명이 지연되면서 가이던스 실망 매물 누적.",
        ],
    }

    # 5. Cascading Consequences
    q5 = {
        "title": "5. 2·3차 연쇄 파급효과 시뮬레이션 (Cascading Consequences)",
        "question": "만약 핵심 지지선(200일선 또는 위기 저점)이 3거래일 이상 회복되지 못한다면 어떤 연쇄 강제 매도가 일어나는가?",
        "cascade_points": [
            "CTA(추세추종 헤지펀드)의 체계적 포지션 축소 및 숏 베팅 확대",
            "옵션 딜러들의 네거티브 감마(Negative Gamma) 진입으로 인한 장중 하방 변동성 폭발",
            "마진콜 발생 시 우량 빅테크 주식까지 담보 확보를 위해 무차별 강제 청산",
        ],
    }

    # 6. Meta-Cognitive Audit
    q6 = {
        "title": "6. 메타인지 점검 (Meta-Cognitive Evaluation)",
        "question": "지금 시장을 바라보는 나의 판단은 객관적 지표에 기반한 것인가, 아니면 심리적 함정에 빠져 있는가?",
        "guidance": "자신의 편향 점검표 결과를 검토하고, 감정적 매매를 철저히 차단하십시오.",
    }

    return {
        "q1": q1,
        "q2": q2,
        "q3": q3,
        "q4": q4,
        "q5": q5,
        "q6": q6,
    }


def build_thesis_invalidation_ladder(
    primary_metrics: Dict[str, Any],
    macro_risk: Dict[str, Any],
    crisis_evals: List[Dict[str, Any]],
    tier2_eval: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Construct explicit numerical triggers for Bull and Bear Invalidation Ladders.
    Uses the analyzed target asset name, moving averages, Tier 2 rolling trough, and Tier 3 crisis benchmarks.
    """
    target_name = primary_metrics.get("name") or "S&P 500"
    sma_200 = primary_metrics.get("sma_200") or 0.0
    sma_50 = primary_metrics.get("sma_50") or 0.0
    cur_close = primary_metrics.get("current_close") or 0.0

    bull_triggers = [
        f"{target_name} 종가 기준 200 SMA ({sma_200:,.1f}) 하회가 3거래일 연속 지속될 때",
        "VIX 종가가 30.0 이상으로 2거래일 연속 마감할 때",
        "HYG/LQD 5일 상대강도가 -1.5% 미만으로 급락하며 신용 경색이 나타날 때",
    ]

    if tier2_eval and tier2_eval.get("trough_price") is not None:
        t2_dt = tier2_eval.get("trough_date", "1년 저점")
        t2_pr = tier2_eval.get("trough_price")
        bull_triggers.append(f"Tier 2 최근 1년 최대 조정 저점 ({t2_dt} 저점: {t2_pr:,.1f})을 종가 기준 하회 이탈할 때 (손절 기준선)")
    elif crisis_evals:
        chosen_bench = next((x for x in crisis_evals if x.get("crisis_low") is not None), crisis_evals[0])
        c_low = chosen_bench.get("crisis_low")
        c_name = chosen_bench.get("name", "핵심 지지선")
        if c_low is not None:
            bull_triggers.append(f"주요 위기 지지선 ({c_name}: {c_low:,.1f})을 1.5% 이상 하회 이탈할 때 (손절 기준선)")
        else:
            bull_triggers.append(f"{target_name} 직전 스윙 저점을 종가 기준 하회 이탈할 때 (손절 기준선)")
    else:
        bull_triggers.append(f"{target_name} 직전 스윙 저점을 종가 기준 하회 이탈할 때 (손절 기준선)")

    bear_triggers = [
        "VIX 종가가 20.0 이하로 하향 안착할 때",
        f"{target_name}이(가) 50 SMA ({sma_50:,.1f})를 20일 평균 거래량 1.2배 이상으로 상향 돌파 안착할 때",
        "11개 섹터 중 경기민감주(XLK/XLI/XLF)의 5일 상대강도가 방어주를 3일 연속 압도할 때",
        "HYG/LQD 신용 비율이 5일 이동평균선을 상향 돌파하며 신용 안정화가 입증될 때",
    ]

    return {
        "bull_invalidation_triggers": bull_triggers,
        "bear_invalidation_triggers": bear_triggers,
    }
