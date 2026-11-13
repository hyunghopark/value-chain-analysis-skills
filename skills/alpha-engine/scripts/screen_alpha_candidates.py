#!/usr/bin/env python3
"""
screen_alpha_candidates.py
Alpha Engine Market-Wide Screener
Screens liquid universe tickers across Korea (KR) and US (US) markets,
identifying the top stocks firing across the 4 Alpha Archetypes:
  1. 🚀 Supercycle Leader (실적 폭발 주도주)
  2. 🔄 Turnaround Inflection (바닥 탈출 턴어라운드)
  3. 📅 Catalyst Event-Driven (확정 D-Day 및 촉매주)
  4. ⚡ Momentum Breakout (신고가 & 수급 돌파 모멘텀)
"""

import argparse
import json
import sys
import os
from datetime import datetime
from typing import Any, Dict, List

# Ensure calculate_alpha_score is importable
cur_dir = os.path.dirname(os.path.abspath(__file__))
if cur_dir not in sys.path:
    sys.path.insert(0, cur_dir)

try:
    from calculate_alpha_score import evaluate_alpha
except ImportError as e:
    sys.stderr.write(f"Error importing calculate_alpha_score: {e}\n")
    sys.exit(1)


UNIVERSE_KR = [
    # 반도체 / AI 하드웨어
    "000660.KS", "005930.KS", "042700.KS", "403870.KQ",
    # 방산 / 전력인프라 / 조선
    "012450.KS", "267260.KS", "010140.KS",
    # 자동차 / 모빌리티
    "005380.KS", "012330.KS",
    # 플랫폼 / 바이오 / 금융
    "035420.KS", "207940.KS", "196170.KQ", "105560.KS"
]

UNIVERSE_US = [
    # AI 가속기 & 반도체
    "NVDA", "TSM", "AVGO", "AMD", "MU", "ARM",
    # 빅테크 & 고성장 소프트웨어
    "MSFT", "GOOGL", "META", "AMZN", "TSLA", "PLTR", "APP",
    # AI 전력 / 인프라
    "GEV", "VRT"
]


def screen_universe(market: str = "KR", top_n: int = 3) -> Dict[str, Any]:
    market_upper = market.upper()
    tickers = UNIVERSE_KR if market_upper == "KR" else UNIVERSE_US
    market_name = "한국 시장 (KOSPI / KOSDAQ)" if market_upper == "KR" else "미국 시장 (S&P 500 / NASDAQ)"

    print(f"⏳ [{market_name}] 4대 알파 주도주 스크리닝 진행 중 (유니버스 {len(tickers)}개사)...", file=sys.stderr)

    results = []
    for t in tickers:
        try:
            res = evaluate_alpha(t)
            results.append(res)
        except Exception as e:
            # Skip if any ticker query fails
            continue

    # Group by primary archetype
    grouped: Dict[str, List[Dict[str, Any]]] = {
        'SUPERCYCLE_LEADER': [],
        'TURNAROUND_INFLECTION': [],
        'CATALYST_EVENT': [],
        'MOMENTUM_BREAKOUT': [],
    }

    for r in results:
        arch = r.get('primary_archetype', 'SUPERCYCLE_LEADER')
        if arch in grouped:
            grouped[arch].append(r)

    # Sort each group by composite alpha score descending
    for arch in grouped:
        grouped[arch].sort(key=lambda x: x.get('composite_alpha_score', 0.0), reverse=True)

    # Pick top N per archetype
    top_picks = {}
    for arch, items in grouped.items():
        top_picks[arch] = items[:top_n]

    return {
        'market': market_upper,
        'market_name': market_name,
        'screened_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S KST"),
        'total_scanned': len(results),
        'top_picks': top_picks
    }


def format_screening_report(data: Dict[str, Any]) -> str:
    m_name = data['market_name']
    s_time = data['screened_at']
    picks = data['top_picks']

    archetype_headers = {
        'SUPERCYCLE_LEADER': '🚀 1. 슈퍼사이클 & 실적 폭발 주도주 (Supercycle Leaders)',
        'TURNAROUND_INFLECTION': '🔄 2. 바닥 탈출 턴어라운드주 (Turnaround Inflections)',
        'CATALYST_EVENT': '📅 3. 확정 D-Day 및 미래 촉매주 (Catalyst Event-Driven)',
        'MOMENTUM_BREAKOUT': '⚡ 4. 신고가 & 수급 돌파 모멘텀주 (Momentum Breakouts)',
    }

    lines = []
    lines.append(f"## 🏆 [{m_name}] 미래 주도주 4대 알파 스크리닝 리포트")
    lines.append(f"> **스크리닝 시각**: {s_time} | **분석 대상**: 유동성 상위 {data['total_scanned']}개 주도 기업")
    lines.append("> **선별 기준**: 4대 동적 알파 엔진 점수(0~100) 및 듀얼 스코어링\n")

    for arch, header in archetype_headers.items():
        lines.append(f"### {header}")
        items = picks.get(arch, [])
        if not items:
            lines.append("*(현재 시장에서 해당 조건에 부합하는 기준 점수 초과 종목 없음)*\n")
            continue

        lines.append("| 순위 | 기업명 | 티커 | 공격 알파 | 방어 점수 | 최종 판정 | 핵심 상승 근거 (P×Q / 촉매) |")
        lines.append("|:---:|---|:---:|:---:|:---:|---|---|")
        for i, item in enumerate(items, 1):
            m = item['metrics']
            v_short = item['dual_verdict'].split('(')[0].strip()
            lines.append(
                f"| **{i}위** | **{item['company_name']}** | `{item['ticker']}` | "
                f"**{item['composite_alpha_score']}점** | {item['defense_score']}점 | "
                f"{v_short} | 매출 YoY {m['revenue_growth_yoy']}, OPM {m['operating_margin']}, 컨센서스 여력 {m['implied_upside']} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Alpha Engine Market Screener")
    parser.add_argument("--market", default="KR", choices=["KR", "US", "kr", "us"], help="Target market (KR or US)")
    parser.add_argument("--top", type=int, default=3, help="Top N candidates per archetype")
    parser.add_argument("--json", action="store_true", help="Output raw JSON format")
    args = parser.parse_args()

    data = screen_universe(market=args.market, top_n=args.top)

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(format_screening_report(data))


if __name__ == "__main__":
    main()
