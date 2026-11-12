---
name: investment-strategy
description: Use when the user requests an investment analysis of an industry, combining pre-flight breaking event intelligence (market-intelligence), top-down macro regime and crisis supports (market-analyst), structural supply chain mapping and bottleneck identification (value-chain-analyzer), and bottom-up corporate valuation with consensus revisions and scenario stress testing (financial-analyst).
version: 4.0.0
allowed-skills: market-analyst value-chain-analyzer financial-analyst market-intelligence
---

# 통합 4-티어 투자 전략 (Unified 4-Tier Investment Strategy)

## 1. 개요 (Overview)

`investment-strategy` 스킬은 4개 전문 분석 스킬(`market-intelligence`, `market-analyst`, `value-chain-analyzer`, `financial-analyst`)을 유기적으로 통합 오케스트레이션하여 기관 투자자 수준의 포괄적 투자 전략 보고서를 자동 생성합니다:
0. **Phase 0: 사전 특수 상황 및 뉴스 인텔리전스 (`market-intelligence`)**: 시작 즉시 1~2초 만에 비편향 광대역 헤드라인 수집, 고유명사/위기 토큰 스파이크 감지, 적응형 2단계 자율 멀티홉(Adaptive Multi-hop) 질의를 통해 경영진 거버넌스·사법 리스크·블랙스완을 사전 스캔하여 독립 스냅샷(`{ticker}_intelligence.json`) 봉인.
1. **Phase 1: 탑다운 거시 시장 및 국면 진단 (`market-analyst`)**: 거시 시장 체제(6대 Market Regime), 3단계 동적 지지선 및 적응형 위기 벤치마크(Tier 1 단기전술·Tier 2 롤링 1년 최대조정·Tier 3 적응형 4단계 근접도 밴드), 11개 SPDR 섹터 순환매, 거시 스트레스 지표(VIX, 10년물 금리, 신용 스프레드, 환율), 소크라테스식 6대 질문, 5대 인지 편향 감사, 가설 무효화 사다리(Thesis Invalidation Ladder).
2. **Phase 2: 산업 가치사슬 및 핵심 병목 해자 매핑 (`value-chain-analyzer`)**: 전방(Upstream), 중방(Midstream), 후방(Downstream) 구조화, 1+2+1 비교 프레임워크([타겟], [직접경쟁], [병목협력]), Mermaid 구조도.
3. **Phase 3: 바텀업 기업 정밀 밸류에이션 및 시나리오 스트레스 테스트 (`financial-analyst`)**: 4-호라이즌 PER, 역사적 P/B 밴드(동일 산식), 30일 이익 추정치 리비전, 4분기 어닝 서프라이즈, 정량 팩터 신호등 및 종합 판단 매트릭스, 일회성 손익 회계 감사, 데이터 기반 2-티어 시나리오 스트레스 테스트 및 결합 하방 바닥가(Multiple C: Joint De-rating Floor).
4. **Phase 4: 이벤트 게이트키퍼 & 비상 오버라이드 조립 (Unified Resynthesis)**:
   - Phase 0의 팩트와 Phase 3의 퀀트 수치(피어 등락률, Multiple C 바닥가)를 결합.
   - Level 4~5 위기 시 `apply_event_gatekeeper`를 통해 투자의견을 **`🟡 중립/관망 (🚨 거버넌스 긴급 경보: 사실관계 확인 중 — WATCH)`**으로 자동 강등.
   - Section 1.2에서 '금리 탓'을 배제하고 '피어 대비 단독 괴리율 및 CEO 해임 리스크'로 원인 진단을 전면 대체.
   - 모델 포트폴리오를 **타겟 0.0% 동결, 안전 현금 40.0%, 피어 50.0%**로 스마트 재배분.

---

## 🧭 객관성 및 신뢰성 원칙 (Objectivity Rules)

1. **결론 사전 확정 금지 (Clean-Slate Policy)**: 어떤 섹션도 사전 확정된 결론을 입증하기 위해 쓰지 않습니다. 과거 작성된 보고서 파일이나 과거 데이터 스냅샷을 일체 참조하지 않고, 오직 실시간 API 데이터와 독립적 신규 리서치에 기반합니다.
2. **헤더 듀얼 신호등 요약 & Executive Summary**:
   - 보고서 최상단에 바쁜 투자자를 위한 **Executive Summary & Signal Dashboard** 카드를 배치합니다:
     - 3줄 핵심 결론
     - 거시 시장 신호 vs 기업 밸류 신호 대시보드
     - 권장 모델 포트폴리오 비중
3. **통화 기호 백틱 감싸기 (KaTeX 수식 충돌 100% 방지)**:
   - 본문 및 모든 마크다운 표에서 달러 기호(`$`) 및 외화 표기는 반드시 백틱(예: `` `$91.25` ``, `` `$490.54` ``)으로 감싸 뷰어의 KaTeX(수식 렌더러)와 충돌하여 표 레이아웃이 무너지는 현상을 원천 방지합니다.
4. **실시간 Web 조사(`search_web`) 및 실제 URL(HTTP 200) 직결 원칙 (Zero-Hallucination & No-404 Policy)**:
   - 가상 URL 생성 및 임의의 기사 주소 날조를 엄격히 금지합니다.
   - Section 1.1(산업 전망), Section 1.3(체크리스트), Section 5(기업별 촉매 및 리스크), Section 8(참고문헌)의 모든 자료는 **반드시 `search_web` 툴을 실행하여 검색된 실제 언론사/기관의 원문 URL(HTTP 200 OK 확인)과 실제 발행일, 실제 기사 제목**으로 작성합니다.
   - 클릭 시 404가 발생하는 임의 조합 URL(예: `20261015-12345.html` 등)은 절대 금지되며, 반드시 실제 브라우저에서 열리는 유효한 링크만 인용합니다.
5. **하이브리드 의사결정 실행 전략 (Hybrid Execution Framework)**:
   - **탑다운 거시 현금 제약 (Cash Allocation Constraint)**: 시장 국면(Phase 1 Table 5)에서 도출된 최소 권장 현금 비중(예: 25% 이상, 45% 이상)을 엄격히 준수합니다.
   - **바텀업 판정 & 무효화 사다리 연계 분할 매수**: 기업 판정이 🟢(매수 후보)일지라도, 거시 지지선 및 6.3 가설 무효화 사다리의 트리거 조건과 연동하여 단계별 분할 매수 계획을 수립합니다.
6. **Section 4 수치 직접 수정 절대 금지**: Section 4의 모든 표와 숫자는 파이썬 스크립트가 자동 산출하며, SHA-256 해시로 봉인됩니다. 단 한 글자라도 임의 수정 시 검증 도구가 실패 처리합니다.
7. **플레이스홀더 제로 원칙 (Zero-Unpopulated Placeholders)**: 보고서 본문에 `[AI_TODO]`, `[수치]`, `[XX%]`, `[🟢/🟡/🔴]`, `[출처]`, `[방어 유지]` 등 미완성 플레이스홀더가 하나라도 남아있으면 검증 도구가 실패 처리합니다.
8. **엄격한 숫자 추적성 (Traceability)**: 본문에 인용된 모든 숫자는 동반 데이터 스냅샷(`*_data.json`)에 존재하는 값이거나, [번호] 인용 출처가 동일 문장에 명시되어야 합니다.

---

## 2. 통합 3-티어 워크플로우 (3-Tier Process Flow)

### 🚀 Phase 1: 탑다운 거시 시장 및 국면 진단 (Skill A: market-analyst)
1. **스마트 벤치마크 자동 감지**:
   - 산업 키워드에 "반도체"/"메모리" 포함 시: `반도체` (^SOX, SMH, NVDA, 005930.KS, 000660.KS).
   - 산업 키워드에 "기술"/"빅테크"/"소프트웨어"/"AI" 포함 시: `기술주식` (^NDX, XLK).
   - 타겟 티커가 `.KS`/`.KQ` 또는 6자리 숫자일 시: `한국증시` (^KS11, ^KQ11, USDKRW=X).
   - 미국 상장 티커일 시: `미국증시` (^GSPC, ^NDX, ^DJI, ^RUT, ^SOX).
   - `--market` 플래그로 명시적 오버라이드 가능.
2. **실시간 시장 데이터 수집 및 5대 기둥 국면 판정**:
   - 6대 시장 국면: 상승 확장(현금 10%), 과열/후기(현금 25~35%), 건전한 조정(현금 20~30%), 유동성 충격(현금 40~50%), 스태그플레이션(현금 40~60%), 구조적 약세(현금 60~80%).
   - 3단계 동적 지지선 및 적응형 위기 벤치마크 (Tier 1 단기전술, Tier 2 롤링 1년 최대조정, Tier 3 역사적 위기 적응형 4단계 근접도 밴드).
   - 11개 SPDR 섹터 순환매 스프레드(경기민감 vs 경기방어).
   - 소크라테스 5대 인지 편향 정량 감사 및 가설 무효화 사다리(Thesis Invalidation Ladder).

### 🔍 Phase 2: 가치사슬 구조화 및 핵심 병목 해자 매핑 (Skill B: value-chain-analyzer)
1. 산업 가치사슬을 Upstream, Midstream, Downstream으로 분해.
2. **비교 분석 대상 4개사 필수 선정 (1+2+1 Framework)**:
   - **① 타겟 기업 (1개사, [타겟])**: 분석 대상 핵심 기업.
   - **② 수평 직접 경쟁사 (2개사, [직접경쟁])**: 글로벌 점유율 2위 및 3위 과점 경쟁사.
   - **③ 수직 가치사슬 핵심 병목 (1개사, [병목협력])**: 공정 수율, 패키징 또는 독점 장비/소재 파트너.
   - 역할이 겹칠 시 `[병목협력·경쟁]`처럼 병기.
3. Mermaid 시각화 다이어그램 자동 렌더링.
4. **경제학적 교섭력 분석**: 매출총이익률(GPM, 러너 독점도 지수 대용) 및 현금전환주기(CCC = 재고자산회전일수 + 매출채권회전일수 - 매입채무회전일수)를 통해 밸류체인 내 가격 전가력과 운전자본 우위 검증.

### 📊 Phase 3: 기업 정밀 밸류에이션 및 시나리오 스트레스 테스트 (Skill C: financial-analyst)
1. 선정된 4개사에 대해 재무 데이터 및 컨센서스 수집.
2. **섹터 적응형 5대 비즈니스 프로파일(`profile_detector.py`) 자동 감지** 및 `--cyclical` 지정:
   - **Type 1 (`GENERAL`, 전통 제조/내수)**: Forward P/E, PEG, 매출성장률, EV/EBITDA, ROE, 부채비율, 30일 추정치 방향 (7개 기둥).
   - **Type 2 (`CYCLICAL`, 반도체/시클리컬)**: 이익 정점의 왜곡된 저PER 대신 **P/B 밴드 위치, 사이클 위치(영업이익률), 추정치 방향, 부채비율** (4개 기둥)로 엄격 판정.
   - **Type 3 (`PLATFORM_SAAS`, 플랫폼/SaaS)**: 매출성장률, FCF 마진율, Rule of 40, EV/Sales, PEG, 추정치 방향 (6개 기둥, 전통 PBR/부채비율 배제).
   - **Type 4 (`FINANCIAL_REIT`, 금융/리츠/고배당 인프라)**: P/B 밴드, ROE, 배당수익률, Forward P/E, 추정치 방향 (5개 기둥, 일반 부채비율/EV·EBITDA 배제).
   - **Type 5 (`BIOTECH_RD`, 바이오/딥테크 R&D)**: Cash Runway(현금런웨이), 순현금/시총 비중, R&D 집약도, 추정치 방향, 부채비율 (5개 기둥, 전통 PER/ROE 배제).
   - **상세 레퍼런스 및 GICS 163개 세부산업 매트릭스**: `.agents/skills/financial-analyst/references/taxonomy/business-profiles.md`, `gics-163-subindustries.md` 및 프로젝트 로컬 위키(`wiki/index.md`, `wiki/entities/10~60-*.md`) 참조.
3. 4-호라이즌 PER, P/B 밴드, 프로파일별 특화 보조지표(Table 4.3-4), 30일 이익 추정치 리비전 방향, 최근 4분기 어닝 서프라이즈, 종합 투자 시그널 매트릭스 산출.
4. 일회성 손익 분리 회계 감사 및 정규화 ROE.
5. **2-Tier 경제학 해자 및 밸류 트랩 게이트키퍼 (Table 4.3-6.1)**:
   - EVA Spread ($\text{ROIC}-\text{WACC}$), Implied ERP, 주주환원율(배당+순자사주), 현금전환비율(OCF/NI) 감사.
   - 1차 매트릭스가 🟢라도 게이트키퍼 🔴(자본잠식/주주가치 희석/이익 품질 불량) 발생 시 자동으로 `🟡 중립/관망 (⚠️ 밸류 트랩 경보)`로 1단계 하향.
6. **3-Tier 시나리오 스트레스 테스트**:
   - Multiple A (현재 배수 유지), Multiple B (애널리스트 목표가 내재 배수) 외에 **Multiple C (Joint De-rating Floor: Bear EPS × Band Lowest Multiple)**를 필수 산출하여 이익 급감과 배수 동시 압축 시의 최악 바닥가 및 하방 마진 점검.

---

## 3. 실행 방법 (CLI Instructions)

### 1단계: 마스터 보고서 템플릿 및 동반 스냅샷 생성

마스터 스크립트를 실행하여 통합 보고서 마크다운 파일과 단일 통합 데이터 스냅샷(`*_data.json`)을 동시 생성합니다:

```bash
# Antigravity 환경 실행 예시
./venv/bin/python3 .agents/skills/investment-strategy/scripts/generate_strategy_report.py \
  --industry "AI 메모리 반도체" \
  --upstream "실리콘 웨이퍼, 포토레지스트, EUV 노광장비(ASML), HBM 전용 TC 본더" \
  --midstream "DRAM/NAND 칩 제조, HBM3E 패키징, 첨단 파운드리 TSMC CoWoS" \
  --downstream "CSP 데이터센터(MSFT/GOOGL), AI 가속기 서버(NVDA HGX B200), 온디바이스 스마트폰" \
  --tickers "005930.KS,000660.KS,MU,TSM" \
  --cyclical "005930.KS,000660.KS,MU,TSM" \
  --benchmarks "^KS11,^SOX" \
  --weights "0.2,0.5,0.3"
```

생성 결과물:
- `reports/[Industry]_[YYYYMMDD]_Investment_Strategy_Report.md`: 통합 보고서 본문.
- `reports/[Industry]_[YYYYMMDD]_Investment_Strategy_Report_data.json`: 거시 및 재무 데이터 통합 동반 스냅샷.

### 2단계: AI 에이전트 분석 작성 (Fill `[AI_TODO]` — 다중 MCP 우선순위 체크리스트 적용)

파일 편집 도구를 사용하여 보고서 내부의 모든 `[AI_TODO]` 영역을 채울 때, 단순 웹 검색에 앞서 **`.agents/skills/financial-analyst/references/rules/data-quality.md`의 항목별 출처 및 다중 MCP 폴백 우선순위 체크리스트(1순위 → 2순위 → 3순위)**를 우선 적용합니다:
- **Section 1.2 (거시/업황 트리거 및 수급 진단)**:
  - 금리·신용·유동성: `1순위 FRED MCP (fred_bundle: rates/credit/liquidity) & ECOS MCP (ecos_market_rates)` → `2순위 Toss MCP (toss_market_indicator_prices)` → `3순위 Yahoo Finance`
  - 국내 시장·업종 수급: `1순위 Toss MCP (toss_market_investor_trading 7대 기관 세분화, toss_sector_rankings)` → `2순위 KRX MCP (krx_stock market_summary)` → `3순위 네이버/다음 금융`
- **Section 1.3 (검증 체크리스트 — 잠정실적·발표일·트리거 사실관계)**:
  - 한국 기업 실적·잠정실적: `1순위 DART MCP (dart_disclosures + dart_document 공정공시 원문 표)` → `2순위 WiseReport / 네이버 금융` → `3순위 search_web`
  - 미국 기업 실적·가이던스: `1순위 SEC EDGAR MCP (sec_filings + sec_document 10-K/10-Q/8-K Item 2.02)` → `2순위 Yahoo Finance` → `3순위 search_web`
  - 매크로 이벤트 일정: `1순위 FRED MCP (fred_release_calendar)` → `2순위 search_web`
- **Section 3 & Section 5 (4개사 가치사슬 교섭력 CCC/GPM, 핵심 촉매, 오버행·거버넌스 리스크)**:
  - 재무·운전자본(CCC)·자사주·오버행: `1순위 DART MCP (dart_financials, dart_report: stockTotqySttus / tesstkAcqsDspsSttus / alotMatter / cbIssuAcmslt) & SEC EDGAR MCP (sec_financials, sec_search 공급망 키워드 검색)` → `2순위 KRX MCP / 네이버 금융` → `3순위 Yahoo Finance`
  - 종목별 공매도·프로그램 수급: `1순위 Toss MCP (toss_stock_short_selling, toss_stock_program_trades)` → `2순위 네이버 금융`
- **Section 6**:
  - 6.1 시나리오 스트레스 테스트 해석(하방 위험 직시: Multiple A, B 및 최악 복합 디레이팅 바닥가 Multiple C 하방 마진 점검).
  - 6.2 소크라테스 6대 질문(명료화, 숨은 가정, 정량 근거, Bear Anti-Thesis 반대 논증, 연쇄 파급효과, 메타인지).
  - 6.3 5대 인지 편향 교정 점검 및 가설 무효화 사다리(Thesis Invalidation Ladder).
- **Section 7**:
  - 7.1 탑다운 거시 현금 제약(권장 현금 비중 준수).
  - 7.2 판정 연동 실행 전략(분할 매수 가격대, 무효화 트리거 발생 시 즉시 대응).
  - 7.3 포트폴리오 비중 제안.
- **Section 8**: 참고 문헌 `[번호] 제목 — 발행일 — URL`.

### 3단계: 통합 검증 도구 실행 (`check_strategy_report_numbers.py`)

보고서 작성이 완료되면 반드시 통합 검증기를 실행하여 무결성을 검증합니다:

```bash
./venv/bin/python3 .agents/skills/investment-strategy/scripts/check_strategy_report_numbers.py \
  "reports/AI_메모리_반도체_20261106_Investment_Strategy_Report.md"
```

- **종료 코드 `0`**: 모든 검증 통과 (Section 4 해시 일치, 플레이스홀더 0개, 모든 숫자 스냅샷/출처 추적 완료).
- **종료 코드 `1`**: 수정 필요 항목 존재 (미완성 `[AI_TODO]`, Section 4 임의 수정, 출처 없는 숫자 등).
- **종료 코드 `2`**: 파일 경로 오류.

남은 문제 사유를 문서화해야 할 경우 `--section` 옵션을 붙여 `## 9. 숫자 점검 결과` 블록을 생성할 수 있습니다.

---

## 4. 모범 사례 및 금지 사항 (Best Practices)

- **장단기 입체적 조망**: 거시 시장 체제와 단기 급락 트리거(1~5일)를 먼저 분석하고, 중장기 가치사슬 해자 및 정밀 밸류에이션을 결합합니다.
- **급락을 그 자체로 저가 매수 근거로 삼지 마십시오**: 낙폭 과대나 RSI 과매도만으로 매수를 추천하지 않습니다. 펀더멘털 손상 여부와 거시 현금 제약을 먼저 확인합니다.
- **소크라테스식 반대 논증 (Bear Anti-Thesis) 필수**: 분석자가 아무리 확신하더라도, 기관 공매도 세력의 핵심 반대 논리 3가지를 반드시 서술합니다.
- **가설 무효화 조건 명시**: 어떤 정량적 수치나 이벤트가 발생하면 기존 투자 결론을 즉시 폐기하고 비중을 축소할지 명확한 사다리를 정의합니다.
- **면책 문구 보존**: 보고서 최하단의 법적 고지 및 면책 문구를 절대 삭제하지 않습니다.
