---
name: market-intelligence
description: Specialized institutional skill for special situations, breaking news anomaly detection, key-person/governance crisis tracking, and regulatory/legal subpoena alerts. Employs a zero-dictionary 2-stage adaptive multi-hop engine, applies event-driven gatekeeper downgrades (WATCH), benchmarks against trough floor multiples, and enforces strict conditional silence when normal.
version: 1.0.0
allowed-tools: run_command
---

# Market Intelligence Skill (실시간 특수 상황 및 뉴스 인텔리전스 데스크)

## 1. 개요 (Overview)

`market-intelligence` 스킬은 월가 대형 투자은행 및 헤지펀드의 **특수 상황(Special Situations) / 법적·거버넌스 리스크 분석 데스크** 역할을 수행합니다.

재무제표 수치 분석(`financial-analyst`)이나 거시경제 지수 분석(`market-analyst`)이 놓치기 쉬운 **비정형 실시간 속보, 경영진 도덕적 해이/불륜, 이사회 해임 논의, 사법 당국 조사/소환장, 시스템 셧다운 등 블랙스완 악재**를 독립적으로 감시·분석하여 파이프라인 전체에 선제적 위기 경보(Crisis Override)를 발령합니다.

---

## 2. 핵심 설계 원칙 (Core Principles)

1. **사전 키워드 관리 제로 (Zero-Dictionary)**:
   - 5,000개가 넘는 글로벌 상장사의 경영진 이름이나 업종별 리스크 단어를 사전에 하드코딩하지 않습니다.
   - 비편향 광대역 헤드라인 수집 후 고유명사/위기 토큰 빈도 스파이크 분석으로 이상 징후를 스스로 포착합니다.
2. **적응형 자율 추적 (Adaptive Multi-hop)**:
   - 1차 수집에서 이상 징후(예: `Kimberly Powell`, `Wachtell`, `Oust`)가 감지되면, 시스템이 스스로 2차 심층 질의를 연쇄 생성하여 배후 팩트(이사회 동향, 소송 여부)를 끝까지 파고듭니다.
3. **조건부 침묵 원칙 (Conditional Silence - Zero Dead Data)**:
   - 평상시(Level 1~2, 이상 징후 없음)에는 리포트에 어떠한 표나 텍스트도 남기지 않고 **100% 완전한 침묵**을 지킵니다.
   - 오직 Level 4~5의 중대 위기 발생 시에만 리포트 최상단 카드와 Section 1.2에 빨간색 비상 경보 박스를 동적으로 활성화합니다.
4. **임의의 가짜 숫자 배제 (Zero-Arbitrary Valuation)**:
   - 사람이 임의로 정한 고정 할인율(-15%, -25%)을 전면 배제합니다.
   - 대신 퀀트 시스템이 산출한 **결합 하방 바닥가(`Multiple C: Joint De-rating Floor`, Bear EPS × Band Floor)**를 소환하여 시장의 선반영도(Priced-in) 및 잔여 하방 룸을 투명하게 대조합니다.
5. **투자의견 보류(WATCH) 게이트키퍼**:
   - Level 4~5 위기 감지 시 `apply_event_gatekeeper`를 통해 투자의견을 **`🟡 중립/관망 (🚨 거버넌스 긴급 경보: 사실관계 확인 중 — WATCH)`**으로 1단계 자동 강등합니다.
6. **3대 포트폴리오 스마트 배분**:
   - 타겟 종목: `0.0% (신규 매수 전면 동결 - 🚨 WATCH)`.
   - 방출된 비중을 **긴급 안전 현금(+15%p)**과 **가치사슬/경쟁 피난처 피어(+20%p)**로 스마트 분산합니다.
7. **스냅샷 결정론 보존 (Spec 003)**:
   - 모든 수집 헤드라인과 추론 결과는 독립 스냅샷 파일(`{ticker}_intelligence.json`)에 영구 보존되어 100% 오프라인 재현이 가능합니다.
8. **공식 수시공시(SEC Form 8-K / DART) 정밀 교차 검증 (Regulatory Filing Cross-Verification)**:
   - Level 4/5 위기 발령 시, 언론 특종 보도와 공식 감독기관(미국 SEC EDGAR, 한국 DART) 공시를 자동 교차 검증합니다.
   - 미국 상장사는 SEC Form 8-K (Item 5.02: 경영진/이사진 변동, Item 8.01: 기타 주요사건) 접수 여부를 실시간 조회하여 `🚨 [공식 접수 확인]` vs `⏳ [공식 8-K 미접수 / 이사회 심의 진행 중 (Pending)]` 상태를 리포트에 명시합니다.
   - SEC 4영업일 의무 공시 시차(Time Lag)와 시장 선반영도(Priced-in)를 비교 분석하여 바이너리 리스크(Binary Outcome)를 사전 경고합니다.

---

## 3. 위기 심각도 5단계 분류 체계 (Severity Taxonomy)

| 심각도 등급 | 정의 및 발생 사건 유형 | 시스템 및 리포트 동작 |
|:---:|---|---|
| **Level 1 (일상)** | 분기 실적 발표, 단순 제품 출시, 일상적 인터뷰 | **100% 완전 침묵** (리포트 지면 미사용) |
| **Level 2 (경미)** | 사소한 특허 분쟁, 일상적인 시장 노이즈 | **100% 완전 침묵** |
| **Level 3 (주의)** | 핵심 임원 이직, 공급망 일시적 지연, 노조 파업 예고 | 리포트 Section 1.2에 1줄 참고 주석 제공 |
| **Level 4 (심각)** | CEO 사임설, 외부 감사인 사임, 회계 부정 의혹, 미 당국 정식 조사 착수 | **🚨 긴급 경보 발령**: 투자의견 WATCH 강등, 피어 대비 괴리율 표시 |
| **Level 5 (치명)** | CEO 사내불륜·스파이 연루 동시 폭로, 이사회 해임 논의, 의회 청문회 소환장, 대규모 전산망 마비(BSOD) | **🚨 최상위 비상 체제**: 타겟 0% 동결, 포트폴리오 피난처 분산, Multiple C 바닥선 명시 |

---

## 4. 파이프라인 시퀀스 및 CLI 실행 방법

### 통합 4-티어 파이프라인 시퀀스
- **Phase 0 (사전 수집)**: 리포트 시작 0초 시점에 `intelligence_collector.py`가 비동기 1.2초 만에 스캔 완료 및 `{ticker}_intelligence.json` 봉인.
- **Phase 1~3 (순수 퀀트)**: 매크로 국면 진단, 가치사슬 매핑, 바텀업 재무 밸류에이션(Multiple C 산출).
- **Phase 4 (심판 & 조립)**: Phase 0의 팩트와 Phase 3의 수치를 결합하여 게이트키퍼 가동 및 리포트 렌더링.

### 단독 실행 CLI
```bash
./venv/bin/python3 .agents/skills/market-intelligence/scripts/intelligence_collector.py \
  --ticker NVDA \
  --output reports/NVDA_intelligence.json
```
