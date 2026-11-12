"""
Market Intelligence Report Renderer
Formats markdown alert blocks adhering to the Conditional Silence Principle (Zero Dead Data).
"""

from typing import Any, Dict, Optional


def render_crisis_alert_box(
    intelligence: Dict[str, Any],
    peer_divergence_text: Optional[str] = None,
    multiple_c_floor_price: Optional[float] = None,
    multiple_c_downside_pct: Optional[float] = None,
    drop_from_high_pct: Optional[float] = None,
    currency: str = "$"
) -> str:
    """
    Render high-visibility crisis alert markdown box for Executive Summary.
    Adheres strictly to Conditional Silence: returns empty string if severity < 4.
    """
    sev = intelligence.get("severity", {})
    level = sev.get("level", 1)

    # Conditional Silence: If normal (Level 1~2) or mild (Level 3), suppress full alert box
    if level < 4:
        return ""

    primary = sev.get("primary_crisis", "경영진 거버넌스 및 돌발 리스크")
    desc = sev.get("description", "")
    headlines = intelligence.get("evidence_headlines", [])[:3]

    headlines_md = "\n".join(f">   - *\"{h}\"*" for h in headlines)

    # Relative divergence bullet
    div_bullet = ""
    if peer_divergence_text:
        div_bullet = f"> - **상대 괴리도**: {peer_divergence_text}\n"

    # Multiple C floor comparison bullet
    floor_bullet = ""
    if multiple_c_floor_price is not None and multiple_c_downside_pct is not None:
        drop_note = f"고점 대비 {drop_from_high_pct:.1f}% 급락으로 1차 선반영 중이나, " if drop_from_high_pct else ""
        floor_bullet = (
            f"> - **하방 바닥선 대조**: {drop_note}최악 시나리오"
            f"(**Multiple C 결합 바닥가 = `{currency}{multiple_c_floor_price:,.2f}`**, "
            f"추가 하방 **{multiple_c_downside_pct * 100:+.1f}%**)까지 열려 있어 섣부른 저가 매수 금지\n"
        )

    # Official disclosure cross-verification bullet
    disc_bullet = ""
    disclosures = intelligence.get("official_disclosures")
    if disclosures and isinstance(disclosures, dict):
        status_label = disclosures.get("status_label", "")
        diag = disclosures.get("diagnosis", "")
        auth = disclosures.get("authority", "공식 공시")
        disc_bullet = f"> - **{auth} 수시공시 검증**: {status_label} — {diag}\n"

    alert_title = f"특수 이벤트 긴급 경보: Level {level} - {primary}"
    box = f"""
> 🚨 **[{alert_title}]**
> - **발생 사건**: {desc}
{headlines_md}
{div_bullet}{floor_bullet}{disc_bullet}> - **투자 전략 조치**: **타겟 종목 신규 매수 전면 동결(WATCH)**, 기존 보유자 50% 비중 축소 권고, AI 공급망 안전 피어(TSMC, AMD)로 피난처 분산
"""
    return box.strip()


def render_section1_2_crisis_diagnosis(
    target_ticker: str,
    intelligence: Dict[str, Any],
    drop_pct_5d: Optional[float] = None,
    drop_from_high_pct: Optional[float] = None,
    peer_divergence_text: Optional[str] = None,
    multiple_c_floor_price: Optional[float] = None,
    multiple_c_downside_pct: Optional[float] = None,
    currency: str = "$"
) -> str:
    """
    Render Section 1.2 market volatility & trigger diagnosis text.
    If Level 4~5 crisis, dynamically overrides generic macro attribution with true governance diagnosis.
    """
    sev = intelligence.get("severity", {})
    level = sev.get("level", 1)

    if level < 4:
        return ""

    primary = sev.get("primary_crisis", "경영진 거버넌스 위기")
    headlines = intelligence.get("evidence_headlines", [])[:2]
    quotes = " / ".join(f"\"{h}\"" for h in headlines)

    lines = [
        f"최근 {target_ticker} 주가의 급격한 변동성은 거시경제 금리 인상이나 업종 전반의 경기침체 요인이 아니며, "
        f"**'최고경영자(CEO)의 중대 거버넌스 위기 및 사법 리스크({primary})'에 기인한 순수 기업 고유(Idiosyncratic) 충격**으로 판별됩니다.",
    ]

    if peer_divergence_text:
        lines.append(f"- **피어 대비 단독 괴리**: {peer_divergence_text}")

    if quotes:
        lines.append(f"- **언론 특종 보도**: 주요 글로벌 언론(WSJ, NYT 등)을 통해 긴급 보도된 {quotes} 등이 투자 심리를 급랭시켰습니다.")

    if multiple_c_floor_price is not None and multiple_c_downside_pct is not None:
        drop_note = f"고점 대비 {drop_from_high_pct:.1f}% 조정받았으나, " if drop_from_high_pct is not None else ""
        lines.append(
            f"- **펀더멘털 바닥가 대조**: 현재가는 {drop_note}"
            f"이사회 해임 및 실적 충격이 복합 발생할 경우 시스템이 산출한 **결합 하방 바닥가(Multiple C = `{currency}{multiple_c_floor_price:,.2f}`, {multiple_c_downside_pct * 100:+.1f}%)**를 "
            f"최종 펀더멘털 방어선으로 설정하고, 사태 수습 전까지 관망(WATCH)을 유지해야 합니다."
        )

    disclosures = intelligence.get("official_disclosures")
    if disclosures and isinstance(disclosures, dict):
        lines.append(
            f"- **공식 공시({disclosures.get('authority', '규제당국')}) 대조**: {disclosures.get('status_label')} — {disclosures.get('diagnosis')}"
        )

    return "\n".join(lines)
