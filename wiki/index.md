# Value-Chain & Financial Valuation Wiki — Master Index

본 위키는 **Karpathy 3-Layer LLM Wiki** 아키텍처에 기반하여 구축된 금융·산업 밸류에이션 지식베이스입니다. 모든 문서는 상위 **5대 비즈니스 프로파일(5 Business Profiles)**과 하위 **GICS 11개 섹터 / 163개 세부산업(Sub-Industries)** 간에 양방향 마크다운 링크로 연결되어 있습니다.

---

## 1. 아키텍처 및 규약 (System Schema)
- [SCHEMA.md](SCHEMA.md) — Karpathy 3-Layer LLM Wiki 구조, 프론트매터 규약 및 스킬 연동 아키텍처
- [log.md](log.md) — 위키 생성 및 업데이트 이력 로그

---

## 2. 핵심 개념 및 마스터 프레임워크 (`concepts/`)
- [5대 비즈니스 프로파일 평가 체계 (`5대-비즈니스-프로파일-평가체계.md`)](concepts/5대-비즈니스-프로파일-평가체계.md) — 왜 모든 기업을 동일한 잣대(전통 제조업 기준)로 평가하면 안 되는가? 5대 비즈니스 프로파일(`GENERAL`, `CYCLICAL`, `PLATFORM_SAAS`, `FINANCIAL_REIT`, `BIOTECH_RD`)의 경제적 본질, 활성/제외 필러, 3대 치명적 오판 사례 및 자동 탐지 알고리즘 해설.
- [GICS 163개 세부산업 마스터 밸류에이션 매트릭스 (`gics-163개-세부산업-지표-매트릭스.md`)](concepts/gics-163개-세부산업-지표-매트릭스.md) — GICS 11개 섹터, 25개 산업군, 74개 산업, 163개 세부산업 전체의 코드, 프로파일 매핑, 1순위 운영 KPI 및 주력 밸류에이션 배수 통합 일람표.
- [경제학자 관점의 시스템 심층 감사: 6대 경제학 분과별 12대 사각지대 및 고도화 이론 (`경제학자-관점-12대-시스템-사각지대-및-고도화-이론.md`)](concepts/경제학자-관점-12대-시스템-사각지대-및-고도화-이론.md) — 재무경제학, 거시·국제금융학, 미시·산업조직론, 회계학, 계량·포트폴리오 이론, 시장미시구조·제도경제학 관점에서 진단한 현행 시스템의 12가지 구조적 사각지대와 이론적·수리적 해법.
- [차세대 v4.0 투자 분석 엔진: 경제학적 Moat & 밸류 트랩 게이트키퍼 시스템 설계 명세서 (`경제학-인과관계-기반-차세대-v4-투자시스템-설계명세서.md`)](concepts/경제학-인과관계-기반-차세대-v4-투자시스템-설계명세서.md) — 2단계 하이브리드 게이트키퍼 판정 파이프라인, 4대 지표(EVA, ERP, TSY, CCR) 수학적 산식, 1단계 강등 원칙, 결합 하방 시나리오(배수 C), 가치사슬 교섭력(CCC/GPM) 정량화 및 파이썬 모듈 구현 명세서.
- [공식 MCP 전면 전환 및 레거시 데이터 수집 퇴출 아키텍처 로드맵 (`공식-MCP-전환-및-레거시-수집-퇴출-로드맵.md`)](concepts/공식-MCP-전환-및-레거시-수집-퇴출-로드맵.md) — 비인가 웹 스크래퍼(PyKrx, 다음 수급, 나스닥 크롤러) 및 왜곡 대용치(HYG/LQD, ^IRX, 고정 Rf) 전면 퇴출과 6대 공식 MCP(KRX, DART, TOSS, ECOS, FRED, EDGAR) 전면 승격 및 15회차 실측 타이밍 매트릭스, Spec 003 스냅샷 재현성 보존 2단계 안전 전환 로드맵.
- [위기 지지선 매트릭스 슬림화 및 정적 위기 퇴출 아키텍처 (`위기-지지선-매트릭스-슬림화-및-정적-위기-퇴출.md`)](concepts/위기-지지선-매트릭스-슬림화-및-정적-위기-퇴출.md) — 현재 주가와 100%~760% 괴리되어 실효성을 상실한 2024년 정적 위기 4종(엔캐리, 이란 공습 1/2차, 계엄령) 전면 퇴출 및 50/200 SMA, 52주 저점, 최근 1년 롤링 조정 저점(손절 기준선) 중심 7개 실전 컬럼 슬림화 및 4단계 동적 지지 판정 명세서.
- [리포트 데이터 슬림화 및 중복 표 정리 아키텍처 (`리포트-데이터-슬림화-및-중복-표-정리-아키텍처.md`)](concepts/리포트-데이터-슬림화-및-중복-표-정리-아키텍처.md) — 신호등 이원화 충돌(표 4 단순 신호등 vs 표 5 핵심 지표) 해소 및 표 5 단일 공식 매트릭스 승격, 90% 중복 보조표(표 2-1 시계열 궤적, 표 2-3 임의 피어 평균) 퇴출, 내용 없는 빈 껍데기 헤더(표 6 일회성 손익) 조건부 숨김 처리 명세서.
- [키맨 리스크 및 실시간 뉴스 센티널 아키텍처 (`키맨-리스크-및-실시간-뉴스-센티널-아키텍처.md`)](concepts/키맨-리스크-및-실시간-뉴스-센티널-아키텍처.md) — 2026년 11월 젠슨 황 CEO 사태(불륜, 중국 스파이 연루 의혹, 이사회 해임 논의, 의회 소환) 등 정량 재무제표가 놓치는 초단기 거버넌스 위기를 포착하기 위한 Python 표준 라이브러리 기반 3채널 실시간 뉴스 센티널 및 창업자 프리미엄 박탈 평가 체계 명세서.
- [market-intelligence 신설 스킬 및 통합 4-티어 거버넌스 오버라이드 아키텍처 (`market-intelligence-신설-스킬-및-통합-4티어-거버넌스-오버라이드.md`)](concepts/market-intelligence-신설-스킬-및-통합-4티어-거버넌스-오버라이드.md) — 젠슨 황 CEO 사태 등 퀀트 재무제표가 포착할 수 없는 경영권·거버넌스 블랙스완에 대응하는 독립 신설 스킬과 Phase 0 사전 수집 + Phase 4 게이트키핑/오버라이드 하이브리드 파이프라인 명세서.
- [alpha-engine 신설 및 미래 주도주 발굴·듀얼 스코어링 아키텍처 (`alpha-engine-미래-주도주-발굴-및-듀얼-스코어링-아키텍처.md`)](concepts/alpha-engine-미래-주도주-발굴-및-듀얼-스코어링-아키텍처.md) — 기존 시스템의 과거 브리핑 및 시클리컬 역설(슈퍼사이클 마진 상투 오판)을 해소하고, 4대 동적 알파 아키타입(슈퍼사이클, 턴어라운드, 촉매, 모멘텀) 및 듀얼 스코어보드(Alpha vs Defense), 한·미 양대 시장 실시간 스크리너, Phase 3.5 통합 오케스트레이션 명세서.
- [범용 엔진 하드코딩 탈피 및 산술·금리·단위 정규화 아키텍처 패치 (`범용-엔진-하드코딩-탈피-및-산술·금리·단위-정규화-패치.md`)](concepts/범용-엔진-하드코딩-탈피-및-산술·금리·단위-정규화-패치.md) — 특정 종목/CEO 사태 하드코딩 완전 탈피(거버넌스 동적 분기 및 8-K 미접수 일반화), 시나리오 배수 A 시점 통일(Base FY1 EPS 기준 0.0% 정규화), 실질 ERP 실시간 국채금리(^TNX/FRED) 연동, 장단기 금리차 단위(bps vs %p) 분리 및 200 SMA 기술적 우선순위 보정 통합 패치 명세서.
- [글로벌 USD 백본 및 공시 기반 외환(FX) 감응도 아키텍처 (`글로벌-USD-백본-및-공시-기반-외환-감응도-아키텍처.md`)](concepts/글로벌-USD-백본-및-공시-기반-외환-감응도-아키텍처.md) — AI 모델의 비달러 통화 BPE 토큰 쪼개짐 및 산술 환각을 원천 차단하고, 글로벌 피어 간 USD 단일 체급 비교와 국내 거래소 원화 실매매를 양립시키며, DART 공시 해외매출 비중 팩트 기반의 외환(FX) 3단계 감응도 매트릭스(표 6-1)를 구축한 통합 명세서.
- [전세계 통화 관리 및 ISO 4217 환율 정규화 아키텍처 (`전세계-통화-관리-및-ISO-4217-환율-정규화-아키텍처.md`)](concepts/전세계-통화-관리-및-ISO-4217-환율-정규화-아키텍처.md) — 글로벌 23+ 주요 통화 레지스트리, 마틴 파울러 Money 패턴 Value Object, KaTeX 수식 충돌 방지(USD 백틱 래핑), 이중 통화 표기법 및 Spec 003 순수 결정론 준수 통화 관리 라이브러리(`currency_manager.py`)와 검증기 연동 통합 명세서.

---

## 3. GICS 11대 섹터별 세부산업 딥다이브 (`entities/`)
1. [GICS 10: 에너지 (Energy) — 7개 세부산업](entities/10-에너지-energy.md) — 원유·가스 시추, 장비, 종합 E&P, 정제, 미드스트림(MLP), 석탄 (`EV/DACF`, `PV-10`, `Crack Spread`, `DCF`)
2. [GICS 15: 소재 (Materials) — 17개 세부산업](entities/15-소재-materials.md) — 범용/특수화학, 산업용 가스, 건자재, 포장재, 구리·금·철강, 제지 (`P/B-ROE`, `AISC`, `C1 Cash Cost`, `에틸렌 스프레드`)
3. [GICS 20: 산업재 (Industrials) — 25개 세부산업](entities/20-산업재-industrials.md) — 방산, 건설·전력기기, 중장비, 상사, 폐기물·컨설팅, 해운·항공·철도 (`Backlog`, `Book-to-Bill`, `Operating Ratio`, `EV/EBITDAR`)
4. [GICS 25: 경기소비재 (Consumer Discretionary) — 27개 세부산업](entities/25-경기소비재-consumer-discretionary.md) — 자동차·전장, 주택건설, 가전·의류·명품, 호텔·카지노·외식, 이커머스·소매 (`SSS`, `GMV`, `RevPAR`, `재고회전율`)
5. [GICS 30: 필수소비재 (Consumer Staples) — 12개 세부산업](entities/30-필수소비재-consumer-staples.md) — 식료품·할인점 유통, 음료·주류, 포장식품(K-푸드), 담배, 생활용품·화장품 (`Organic Growth: Price vs Volume`, `CCC`, `FCF 전환율`)
6. [GICS 35: 헬스케어 (Health Care) — 10개 세부산업](entities/35-헬스케어-health-care.md) — 의료기기(소모품 면도기 모델), 의약품 유통, 관리형 의료보험(MLR), 바이오텍(임상 파이프라인), 빅파마, CDMO (`rNPV`, `Cash Runway`, `PoS`, `MLR`)
7. [GICS 40: 금융 (Financials) — 18개 세부산업](entities/40-금융-financials.md) — 대형/지역은행, 지주사, 결제 네트워크(핀테크), 자산운용(AUM), IB, 거래소, 생명/손해/재보험 (`P/TBV`, `ROE-COE`, `CET1`, `NIM`, `CSM`, `Combined Ratio`)
8. [GICS 45: 정보기술 (Information Technology) — 12개 세부산업](entities/45-정보기술-information-technology.md) — SaaS/시스템 소프트웨어, IT 서비스, 통신·하드웨어 장비, EMS, 전자부품, 반도체 및 장비 (`Rule of 40`, `NRR`, `SBC 조정 FCF`, `메모리 P/B 밴드`)
9. [GICS 50: 통신서비스 (Communication Services) — 10개 세부산업](entities/50-통신서비스-communication-services.md) — 유무선 통신사, 광고·방송·케이블, OTT·엔터테인먼트, 게임, 인터랙티브 미디어 플랫폼 (`ARPU`, `Churn`, `MAU/DAU`, `Cash Content Spend`, `SOTP`)
10. [GICS 55: 유틸리티 (Utilities) — 6개 세부산업](entities/55-유틸리티-utilities.md) — 전력·가스·복합·수도 규제 유틸리티, 독립 발전(IPP) 및 재생에너지 (`Rate Base`, `Allowed ROE`, `PPA 단가`, `P/CAFD`)
11. [GICS 60: 부동산 (Real Estate) — 17개 세부산업](entities/60-부동산-real-estate.md) — 물류·오피스·주거·리테일·데이터센터·통신타워 등 지분형 리츠(Equity REITs) 및 부동산 개발·서비스 (`P/FFO`, `P/AFFO`, `P/NAV`, `Cap Rate`, `Same-Store NOI`)

---

## 4. 데이터 출처별 기술 규격 (`data-sources/`)
- [Yahoo Finance](data-sources/yahoo-finance.md) — 시세·재무·컨센서스 기본 출처, 한국 종목 결함과 재무제표 지연
- [네이버 금융](data-sources/naver-finance.md) — 한국 종목 요약 지표·수급, 2026-09-14부터 종가 기준 차이(NXT 포함), 당일 수급 행은 NXT 마감 뒤
- [다음 금융](data-sources/daum-finance.md) — 한국 종목 거래소 종가 기준 출처, 시세 marketStatus로 NXT 시간외 구분
- [WiseReport](data-sources/wisereport.md) — 한국 종목 컨센서스 EPS, 칸 위치로 읽는 구조
- [Nasdaq.com](data-sources/nasdaq.md) — 미국 종목 가격 기준(정기 점검용)

---

## 5. 데이터 출처 이슈 및 대응 이력 (`known-issues/`)
- [KI-001 네이버 종가 필드가 거래소 종가와 다름](known-issues/ki-001-naver-close-basis.md)
- [KI-002 Yahoo 한국 종목 최근 거래일 누락·빈값](known-issues/ki-002-yahoo-kr-latest-day-gap.md)
- [KI-003 Yahoo 재무제표 반영 지연](known-issues/ki-003-yahoo-statement-lag.md)
- [KI-004 WiseReport 표 구조 변경 위험](known-issues/ki-004-wisereport-layout.md)
- [KI-005 Yahoo 거래량 이상치](known-issues/ki-005-yahoo-volume-outlier.md)
- [KI-006 Yahoo 한국 종목 산발적 종가 오류](known-issues/ki-006-yahoo-kr-close-errors.md)
- [KI-007 Yahoo 재무상태표 주식수 이상치](known-issues/ki-007-yahoo-share-count.md)
- [KI-008 ADR 통화 불일치](known-issues/ki-008-adr-currency.md)
- [KI-009 KRX 마감 후 NXT 시간외 거래 시간대의 당일 수급·가격](known-issues/ki-009-nxt-after-market-window.md)
