---
name: alpha-engine
description: Specialized forward-looking skill for detecting stocks with high upside potential. Evaluates 4 dynamic alpha archetypes (Supercycle Leader, Turnaround Inflection, Catalyst Event-Driven, Momentum Breakout), calculates Dual Scores (Alpha Score vs Defense Score), and screens market-wide leading stocks.
version: 1.0.0
allowed-tools: run_command search_web read_url_content
---

# Alpha Engine Skill (미래 주도주 및 상승 알파 발굴·검증 스킬)

## 1. 개요 (Overview)

`alpha-engine`은 기존 시스템의 후행적 회계 감사 및 방어 편향(Downside Defense)을 극복하고, **"앞으로 주가가 오를 종목인가?"**를 선제적으로 판별하기 위해 구축된 기관급 미래 지향적 알파 탐색 엔진입니다.

기업의 재무 수치와 시장 데이터를 바탕으로 **4대 동적 알파 유형(4 Alpha Archetypes)**을 감지하고, **[공격 알파 점수 (0~100)]**와 **[하방 방어 점수 (0~100)]**를 분리한 **듀얼 스코어링(Dual Scoring)**을 통해 실적이 폭발하는 슈퍼사이클 주도주를 상투 위험으로 오인하지 않고 정확하게 매수 기회로 포착합니다.

---

## 2. 4대 동적 알파 유형 (4 Alpha Archetypes)

1. **🚀 타입 1 [SUPERCYCLE_LEADER: 슈퍼사이클 & 실적 폭발 주도주]**
   - 매출 YoY 성장 가속화, 영업이익률(OPM) 전년비 급확장, 업종 내 독점적 GPM(가격 결정력), 완판(Sold-out) 기조 및 선제적 CAPA 증설.
2. **🔄 타입 2 [TURNAROUND_INFLECTION: 바닥 탈출 턴어라운드주]**
   - 과거 적자/최저 마진 바닥 탈출, 2분기 연속 QoQ 영업이익률 급반등(Z-Score 반전), 재고자산 회전율 정상화, 이익 추정치 상향 반전.
3. **📅 타입 3 [CATALYST_EVENT: 확정 D-Day 미래 촉매주]**
   - 향후 3~12개월 내 신제품 양산 개시, 대형 고객사 독점 수주 공시, 시설투자 완공 가동, 대규모 자사주 소각 등 주가를 계단식으로 밀어 올릴 확정 일정.
4. **⚡ 타입 4 [MOMENTUM_BREAKOUT: 신고가 & 수급 돌파 모멘텀주]**
   - 52주 신고가 -5% 이내 근접/돌파, 시장 지수 대비 3개월 상대강도(RS 80점 이상), 외국인/기관 스마트머니 연속 순매집 및 거래대금 폭증.

---

## 3. 핵심 원칙: 듀얼 스코어링 매트릭스 (Dual Scoring Matrix)

과거 재무제표 기준의 '마진 고점'을 무조건 상투(🔴)로 감점하던 오류를 제거합니다:
- **Alpha Score (공격 점수, 0~100)**: 미래 이익 성장, 촉매 파급력, 상대강도, 밸류에이션 리레이팅 잠재력.
- **Defense Score (방어 점수, 0~100)**: 일회성 회계 왜곡, 부채비율, 거버넌스 리스크, 매크로 지지선 이격도.

| 알파 점수 (Alpha) | 방어 점수 (Defense) | 최종 판정 (Dual Verdict) | 권장 실행 전략 |
|:---:|:---:|---|---|
| **80 ~ 100** | **70 ~ 100** | **🟢 강력 매수 (Top Pick 주도주)** | 비중 35~40% 적극 편입, 트레일링 스탑 |
| **80 ~ 100** | **50 ~ 69** | **🟢 적극 매수 (변동성 분할 진입)** | 비중 25~30%, 조정 시 지지선 분할 매수 |
| **60 ~ 79** | **70 ~ 100** | **🟢 안정 매수 (방어형 성장주)** | 비중 20~25%, 중장기 편안한 보유 |
| **60 ~ 79** | **50 ~ 69** | **🟡 조건부 매수 (촉매 확인 후 진입)** | 비중 15%, D-Day 확정 시 추가 매수 |
| **< 60** | **Any** | **🟡 중립/관망 (알파 모멘텀 부족)** | 현금 대기 및 다른 주도주 탐색 |
| **Any** | **< 40** | **🚨 매수 보류 (거버넌스/회계 경보)** | 타겟 0% 동결, WATCH 지정 |

---

## 4. CLI 도구 실행

### 1) 단일 종목 알파 정밀 진단
```bash
./venv/bin/python3 .agents/skills/alpha-engine/scripts/calculate_alpha_score.py --ticker 000660.KS
./venv/bin/python3 .agents/skills/alpha-engine/scripts/calculate_alpha_score.py --ticker NVDA
```

### 2) 시장 주도주 알파 스크리너 (예정)
```bash
./venv/bin/python3 .agents/skills/alpha-engine/scripts/screen_alpha_candidates.py --market KR --top 5
```
