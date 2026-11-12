"""
Market Regime decision engine:
Evaluates 5 pillar signals (trend, vix, rates, credit, breadth)
and classifies the market into one of the 6 institutional regimes with action guidance.
"""

from typing import Any, Dict, List, Optional


def get_support_status(buffer_pct: Optional[float]) -> Dict[str, Any]:
    """
    4-stage practical support signal band based on 1-year low buffer:
    - buffer > +10.0%: 🟢 안전 지지 (Safe Support)
    - +3.0% ~ +10.0%: 🟡 지지 테스트 (Support Test)
    - 0.0% ~ +3.0%: 🚨 손절선 임박 (Near Breakdown)
    - < 0.0%: 🔴 지지선 붕괴 (Breakdown)
    """
    if buffer_pct is None:
        return {"icon": "⚪", "status": "데이터 없음", "status_code": "no_data"}
    if buffer_pct > 10.0:
        return {"icon": "🟢", "status": "안전 지지", "status_code": "safe"}
    elif buffer_pct >= 3.0:
        return {"icon": "🟡", "status": "지지 테스트", "status_code": "testing"}
    elif buffer_pct >= 0.0:
        return {"icon": "🚨", "status": "손절선 임박", "status_code": "near_stop"}
    else:
        return {"icon": "🔴", "status": "지지선 붕괴 (손절 집행)", "status_code": "breakdown"}


def evaluate_trend_signal(
    index_metrics: List[Dict[str, Any]],
    crisis_evals: Optional[List[Dict[str, Any]]] = None,
    primary_ticker: Optional[str] = None,
    tier2_eval: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate trend pillar based on primary index / stock 200 SMA distance and practical support status.
    """
    target = None
    if primary_ticker:
        target = next((m for m in index_metrics if m.get("ticker") == primary_ticker), None)
    if not target:
        for preferred in ["^GSPC", "^KS11", "^NDX", "^SOX"]:
            target = next((m for m in index_metrics if m.get("ticker") == preferred), None)
            if target:
                break
    if not target and index_metrics:
        target = index_metrics[0]

    dist_200 = target.get("dist_200") if target else None
    dist_50 = target.get("dist_50") if target else None

    # Check breach: Tier 2 (1-year rolling trough) or 200 SMA structural breakdown
    tier2_breached = bool(tier2_eval.get("breached")) if tier2_eval else False
    tier3_breached = any(b.get("breached") for b in (crisis_evals or []))
    any_crisis_breached = tier2_breached or tier3_breached

    tier2_near = bool(tier2_eval.get("status_code") in ("near_breakdown", "near_stop")) if tier2_eval else False
    any_near_breakdown = tier2_near or any(b.get("status_code") == "near_breakdown" for b in (crisis_evals or []))

    if (dist_200 is not None and dist_200 < -3.0) or any_crisis_breached:
        signal = "🔴"
        status = "장기 지지선(200일선) 또는 주요 저점 지지선 붕괴"
    elif any_near_breakdown:
        signal = "🟡"
        status = "손절 기준선 접근 (<3~10%) 및 지지선 테스트 경계"
    elif dist_50 is not None and dist_50 < 0:
        signal = "🟡"
        status = "50 SMA 하회 (단기 조정), 200 SMA 지지 중"
    elif dist_200 is not None and dist_200 >= 0:
        signal = "🟢"
        status = "주요 이동평균선(50·200 SMA) 상회 (상승 추세)"
    else:
        signal = "⚪"
        status = "추세 데이터 불충분"

    return {
        "signal": signal,
        "status": status,
        "dist_200": dist_200,
        "dist_50": dist_50,
        "any_crisis_breached": any_crisis_breached,
        "any_near_breakdown": any_near_breakdown,
        "tier2_breached": tier2_breached,
        "tier3_breached": tier3_breached,
        "evaluated_ticker": target.get("ticker") if target else None,
        "evaluated_name": target.get("name") if target else None,
    }


def evaluate_market_regime(
    trend_eval: Dict[str, Any],
    macro_risk: Dict[str, Any],
    sector_rotation: Dict[str, Any],
    index_metrics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Synthesize all 5 pillars and determine market regime.
    """
    trend_sig = trend_eval.get("signal", "⚪")
    vix_info = macro_risk.get("vix", {})
    vix_sig = vix_info.get("signal", "⚪")
    vix_lvl = vix_info.get("level")

    rate_info = macro_risk.get("rate_10y", {})
    rate_sig = rate_info.get("signal", "⚪")
    bps_chg = rate_info.get("chg_5d_bps", 0.0)

    credit_info = macro_risk.get("credit", {})
    credit_sig = credit_info.get("signal", "⚪")

    breadth_sig = sector_rotation.get("signal", "⚪")
    breadth_spread = sector_rotation.get("spread_5d", 0.0)

    oil_chg = macro_risk.get("crude_oil", {}).get("chg_5d_pct") or 0.0

    # 1. Structural Bear Market
    if (trend_sig == "🔴" and credit_sig == "🔴") or (trend_eval.get("dist_200") is not None and trend_eval["dist_200"] < -5.0 and credit_sig == "🔴"):
        code = "structural_bear"
        name = "구조적 약세 국면 (Structural Bear Market)"
        icon = "🔴"
        cash_pct = 70
        equity_pct = 15
        safe_pct = 15
        summary = "주요 지수의 200일선 붕괴와 신용 스프레드 위험 급확대가 결합된 침체형 약세장입니다. 밸류에이션 저가 매수를 엄격히 금지하고 자본 보존을 최우선으로 실행해야 합니다."
        playbook = [
            "신규 주식 매수 전면 동결 및 현금 비중 60~80% 확보",
            "기술적 반등 발생 시 손실 최소화 관점의 비중 축소 기회로 활용",
            "신용 위험이 높은 중소형주 및 고부채 기업 우선 정리",
        ]

    # 2. Liquidity Shock / Panic Dip
    elif vix_sig == "🔴" and (trend_sig == "🔴" or credit_sig == "🔴" or (vix_lvl is not None and vix_lvl >= 28.0)):
        code = "liquidity_shock"
        name = "유동성 충격 / 패닉 국면 (Liquidity Shock / Panic Dip)"
        icon = "🔴"
        cash_pct = 45
        equity_pct = 45
        safe_pct = 10
        summary = "공포 지수(VIX) 급등과 함께 마진콜·기계적 손절(CTA) 등 레버리지 강제 청산이 촉발된 패닉성 투매 국면입니다. 바닥권 투매에 동참하지 말고 VIX 하락 반전을 기다려야 합니다."
        playbook = [
            "패닉 장중 투매 동참 금지 (VIX 30 부근은 역사적으로 단기 공포 극대 구간)",
            "VIX 종가가 25 이하로 안착하고 10일선 지지 확인 시 분할 진입 준비",
            "강제 청산으로 함께 떨어진 펀더멘털 최상위 독점 빅테크 관찰 목록 압축",
        ]

    # 3. Stagflation / Supply Shock
    elif rate_sig == "🔴" and oil_chg > 4.0 and trend_sig in ("🟡", "🔴"):
        code = "stagflation"
        name = "스태그플레이션 / 공급 쇼크 (Stagflation / Supply Shock)"
        icon = "🔴"
        cash_pct = 50
        equity_pct = 35
        safe_pct = 15
        summary = "유가 급등과 장기 금리 상승이 동반되며 밸류에이션 할인율 압박과 마진 압박이 동시에 발생하는 스태그플레이션형 경보 국면입니다."
        playbook = [
            "고밸류 성장주 및 순수 AI 테마주 비중 축소",
            "에너지(XLE), 원자재(XLB) 및 금 등 인플레이션 헤지 자산 편입",
            "금리 민감 고부채 기업 비중 축소",
        ]

    # 4. Healthy Correction / Pullback
    elif (trend_sig == "🟡" or vix_sig == "🟡") and trend_sig != "🔴" and credit_sig != "🔴":
        code = "correction"
        name = "건전한 조정 국면 (Healthy Correction / Pullback)"
        icon = "🟡"
        cash_pct = 25
        equity_pct = 65
        safe_pct = 10
        summary = "장기 200일선 상승 추세가 견고하게 유지되는 가운데, 단기 과열 해소 및 차익 매물 소화가 진행되는 건전한 기술적 조정 국면입니다."
        playbook = [
            "50 SMA 또는 주요 피보나치 지지선(고점 대비 -5~8%)에서 실적 주도주 분할 매수",
            "상대강도(RS)가 유지되는 주도 섹터(반도체/테크) 집중",
            "단기 추세선 이탈 시 손절 기준 명확히 설정",
        ]

    # 5. Overheating / Late Cycle
    elif trend_sig == "🟢" and breadth_sig == "🔴":
        code = "overheating"
        name = "과열 / 후기 국면 (Overheating / Late Cycle)"
        icon = "🟡"
        cash_pct = 30
        equity_pct = 55
        safe_pct = 15
        summary = "지수는 상승세이나 상승 종목 수가 급감하고 소수 빅테크로만 지수가 유지되는 다이버전스(과열 후기) 신호가 감지됩니다."
        playbook = [
            "신규 레버리지 매수 중단 및 목표가 도달 종목 분할 차익 실현",
            "방어적 헬스케어(XLV) 및 필수소비재(XLP)로의 포트폴리오 완충 비중 확대",
            "하방 방어를 위한 인덱스 풋옵션 또는 현금 비중 확충",
        ]

    # 6. Bull Expansion
    elif trend_sig == "🟢" and vix_sig == "🟢" and credit_sig == "🟢":
        code = "bull_expansion"
        name = "상승 확장 국면 (Bull Expansion)"
        icon = "🟢"
        cash_pct = 10
        equity_pct = 85
        safe_pct = 5
        summary = "낮은 변동성(VIX < 20)과 건전한 신용 환경, 견고한 지수 이동평균선 상회가 유지되는 최적의 위험 선호(Risk-On) 확장 국면입니다."
        playbook = [
            "실적 호전 주도 섹터(XLK, SOX, XLI) 적극적 비중 확대 및 추세 추종",
            "현금 비중을 최소화(10%)하고 시장 초과 수익률(알파) 창출 주력",
            "개별 기업 실적 서프라이즈 및 가치사슬 병목 기업 중심 포트폴리오 압축",
        ]

    # 7. Neutral Transition
    else:
        code = "neutral_transition"
        name = "중립 / 국면 전환기 (Neutral Transition)"
        icon = "🟡"
        cash_pct = 30
        equity_pct = 60
        safe_pct = 10
        summary = "시장 지표 간 상충 신호가 나타나는 국면 전환기입니다. 지수 방향성이 확정되기 전까지 무리한 포지션 확대를 자제합니다."
        playbook = [
            "현금 30%를 유지하며 주요 지수 50·200 SMA 지지 테스트 관찰",
            "VIX 20 이하 안착 또는 신용 스프레드 축소 확인 후 방향성 대응",
        ]

    return {
        "code": code,
        "name": name,
        "icon": icon,
        "cash_pct": cash_pct,
        "equity_pct": equity_pct,
        "safe_pct": safe_pct,
        "summary": summary,
        "playbook": playbook,
        "pillars": {
            "trend": trend_sig,
            "vix": vix_sig,
            "rates": rate_sig,
            "credit": credit_sig,
            "breadth": breadth_sig,
        },
    }
