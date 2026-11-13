# Wiki Activity Log

## [2026-11-13] Global Currency Management & ISO 4217 FX Normalization Library
- **Created Concept**: `concepts/전세계-통화-관리-및-ISO-4217-환율-정규화-아키텍처.md`
- **Key Architecture Decisions**:
  - **Zero-Dependency ISO 4217 Registry (`currency_manager.py`)**: Built standalone standard library module managing 23+ global currencies with canonical decimals precision (KRW 0, JPY 0, TWD 0, USD 2, EUR 2, BHD 3) and symbol prefix/suffix positioning.
  - **Martin Fowler Money Value Object (`Money`)**: Implemented immutable `Money(amount, currency)` pattern preventing illegal cross-currency addition/subtraction and providing `.to_currency(target, fx_rate)` for deterministic conversion.
  - **KaTeX Markdown Protection & Dual Formatting**: Standardized USD markdown escaping (`` `$155.80` ``) to eradicate LaTeX `$ ... $` rendering collisions, while supporting dual native/USD reporting (`₩208,000 ($155.80)`).
  - **Audit Engine Expansion**: Upgraded `check_report_numbers.py` and `check_strategy_report_numbers.py` to recognize global currency symbols (`₩$€¥£`, `NT$`, `₫`) and calibrated `PATH_KINDS['fraction']` scaling for FX sensitivity rules.
  - **Spec 003 Determinism**: Verified zero clock/network dependencies, ensuring 100% reproducible offline execution.
- **Master Index**: Updated `index.md` with bidirectional cross-links.

## [2026-11-13] Global USD Backbone & Official Disclosure-Based FX Sensitivity Architecture
- **Created Concept**: `concepts/글로벌-USD-백본-및-공시-기반-외환-감응도-아키텍처.md`
- **Key Architecture Decisions**:
  - **Zero-Hallucination FX Arithmetic**: AI models (LLMs) are strictly forbidden from performing division or currency math in natural language prompts. All currency conversion arithmetic is 100% executed deterministically by Python (`get_financial_stats.py`) using `float` arithmetic.
  - **Phase 1 SSOT FX Rate Broadcasting**: Unified exchange rate (`live_fx`: 1st Toss MCP `toss_exchange_rate`, 2nd Yahoo `USDKRW=X`) frozen in snapshot metadata and broadcast across all phases (Phase 1~4), eradicating cross-module currency mismatch.
  - **Global USD Backbone + Domestic Execution**: Global multi-peer valuation, market cap, and multiple matrices are standardized in USD to eliminate tokenizer BPE digit degradation. Domestic price and target price maintain native KRW (`₩`) for direct KRX trading execution.
  - **Rigorous yet Clean FX 3-Tier Scenario Matrix (Section 6-1)**: Reconciled the tension between cognitive fatigue ("too complex") and flimsiness ("too simple/anxious"). Rendered a clean 3-tier matrix (원화 강세 1,250원 / 기준 / 원화 약세 1,420원) anchored by DART/SEC official overseas export revenue exposure (e.g. Samsung 85.2%, LG Electronics 71.4%) with transparent mathematical sensitivity formulas in footnotes.
- **Master Index**: Updated `index.md` with bidirectional cross-links.

## [2026-11-13] Universal Engine Hardcoding Elimination & Arithmetic/Yield/Unit Normalization Patch
- **Created Concept**: `concepts/범용-엔진-하드코딩-탈피-및-산술·금리·단위-정규화-패치.md`
- **Key Architecture Decisions**:
  - **Pillar 1 (`market-intelligence`)**: Completely eradicated hardcoded governance narratives ("CEO 해임 Item 5.02") and hardcoded peer/drop figures ("AI 피어 TSMC/AMD", "-13.2%"). Implemented keyword-based dynamic severity classification (`oust/affair` -> CEO/경영권 위기, `antitrust/subpoena` -> 사법 당국 반독점·규제 리스크, etc.) and generalized 8-K non-filing diagnostic messages.
  - **Pillar 2 (`financial-analyst`)**: Unified Scenario Multiple A reference timeframe in Table 6 to Base FY1 EPS (`mult_a = price / avg`), ensuring the zero-rerating Base scenario target price matches the current price exactly (`Return = 0.0%`).
  - **Pillar 3 (`financial-analyst`)**: Directly linked Phase 1 live 10-year Treasury yield (`^TNX` / FRED `DGS10`) into `economic_auditor.py` for Implied ERP yield gap calculation, eliminating the hardcoded `rf_rate = 4.5%` fallback.
  - **Pillar 4 (`market-analyst`)**: Separated `%p` and `bps` (`* 100`) for the `10Y - 13W` yield curve spread to eliminate 100x scale distortion (e.g. `+98.1 bps (+0.981%p)`). Fixed support diagnosis priority in `market_regime.py` so that a breakdown below the 200 SMA (`dist_200 < 0`) takes strict precedence over rolling 1-year trough buffer, preventing false `🟢 안전 지지` signals during structural trend breakdowns.
- **Verification**: Executed assertion tests verifying dynamic classification, live ERP calculation, and 200 SMA support status logic.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-13] Alpha Engine Inflation Bug Fix & Toss MCP Korean Stock Integration
- **Bug Fix in Alpha Engine (`calculate_alpha_score.py`)**:
  - Eliminated the unconditional 25-point base catalyst score and blind analyst count scoring (`num_analysts >= 20 -> 35 pts`) that previously caused all large-cap stocks to be falsely stamped as `📅 확정 D-Day 및 촉매주` (95.0점).
  - Recalibrated `CATALYST_EVENT` to strictly measure genuine upcoming event proximity (earnings within 5~35 days: +35 pts, 36~60 days: +20 pts, >90 days: 0 pts) and analyst recommendation conviction (`strong_buy` 25 pts, `buy` 18 pts, `hold` 5 pts).
  - Implemented Structural Archetype Priority Resolution in `determine_dominant_archetype`: ensures genuine `SUPERCYCLE_LEADER` (e.g. Samsung Electronics, SK Hynix) and `TURNAROUND_INFLECTION` (e.g. LG Electronics) maintain primary archetype status over generic catalyst overlays.
- **Toss MCP Integration for Korean Tickers**:
  - Integrated `mcp_client` (`toss_stock_prices`, `toss_stock_candles`, `toss_market_indicator_candles`) into `calculate_alpha_score.py` as primary data source for Korean equities (066570, 005930, 000660, etc.).
  - Successfully eliminated Yahoo Finance's 1-day lag, missing trading days, and trading volume spikes on Korean stocks.
- **Verified Screening Output**:
  - LG Electronics (`066570.KS`): Successfully reclassified as **`🔄 바닥 탈출 턴어라운드주`** (턴어라운드 93.0점, 현재가 136,800원 via Toss).
  - Samsung Electronics (`005930.KS`): Reclassified as **`🚀 슈퍼사이클 & 실적 폭발 주도주`** (슈퍼사이클 92.0점, 현재가 206,500원 via Toss).
  - SK Hynix (`000660.KS`): Reclassified as **`🚀 슈퍼사이클 & 실적 폭발 주도주`** (슈퍼사이클 100.0점, 현재가 1,241,000원 via Toss).
  - Whirlpool (`WHR`): Accurately downgraded to **`🔴 매수 기피`** (공격 알파 32.6점, 방어 35.0점).
  - LG Display (`034220.KS`): Accurately downgraded to **`🔴 매수 기피`** (공격 알파 30.5점, 방어 35.0점).
- **Korean Stock Pipeline Strategy**:
  - Formulated comprehensive data provider blueprint: Toss (Real-time Quotes, Candles, Investor Flows) + DART (10-Yr Financials) + WiseReport/Naver (Consensus) to completely decouple from Yahoo Finance's dirty Korean data.
  - User requested holding off on LG Electronics HVAC/Chiller peer redesign (Item 3) for future proper architecture.

## [2026-11-12] Alpha Engine Skill & Forward-Looking Dual-Scoring Architecture
- **Created Concept**: `concepts/alpha-engine-미래-주도주-발굴-및-듀얼-스코어링-아키텍처.md`
- **Key Architecture Decisions**:
  - Established dedicated standalone skill `.agents/skills/alpha-engine` focused on forward-looking stock appreciation and upside potential.
  - Formulated 4 Dynamic Alpha Archetypes:
    1. `SUPERCYCLE_LEADER`: Revenue YoY > 30%, OPM expansion, GPM pricing power, PEG < 1.0.
    2. `TURNAROUND_INFLECTION`: QoQ operating margin recovery, inventory normalization, 10-yr P/B trough support.
    3. `CATALYST_EVENT`: Confirmed 3~12M D-Day schedule (new products, Capex fab ramp-up, buyback cancellation, index inclusion).
    4. `MOMENTUM_BREAKOUT`: 52W high proximity (-5%), 3-month RS > 80 vs benchmark, institutional smart money accumulation.
  - Implemented Dual Scoring Matrix (`Alpha Score` 0~100 vs `Defense Score` 0~100): decoupled aggressive upside potential from defensive risk gatekeeping.
  - Solved the **Cyclical Paradox**: Supercycle expansion margins (e.g. SK Hynix 74.5% OPM) are recognized as high-growth expansion rather than penalized as cyclical peak risks (🔴).
  - Developed Market-Wide Screener (`screen_alpha_candidates.py`): sub-2-second scanning of Korean (KOSPI/KOSDAQ) and US (S&P 500/NASDAQ) liquid universes across all 4 archetypes.
  - Integrated into `investment-strategy` v4.1.0 as **Phase 3.5**, rendering **Section 4.3 Dual Scoreboard** table and Executive Summary Dashboard card.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-12] Market Intelligence Skill & Unified 4-Tier Governance Crisis Override Architecture
- **Created Concept**: `concepts/market-intelligence-신설-스킬-및-통합-4티어-거버넌스-오버라이드.md`
- **Key Architecture Decisions**:
  - Established dedicated standalone skill `.agents/skills/market-intelligence` acting as Wall Street's Special Situations / Governance Risk Desk.
  - Implemented Zero-Dictionary 2-Stage Discovery Engine (`intelligence_collector.py`): Phase 0 wide scan (`{ticker} breaking news`) -> dynamic uppercase/stopword token spike detection (`Jensen`, `Huang`, `Wachtell`, `oust`, `affair`) -> autonomous 2nd-stage multi-hop query synthesis (`NVDA oust`).
  - Integrated Regulatory Filing Cross-Verification Layer via official MCP (`edgar` sec_filings / `dart` dart_disclosures): checks SEC Form 8-K Item 5.02 (Executive Departure) vs Item 8.01 (Other Events), capturing real-time time-lag (`Pending` vs `Filed`).
  - Adopted Hybrid Execution Sequence in `investment-strategy`: Phase 0 Pre-flight Live Fetch (0s) -> Phase 1 Macro -> Phase 2 Value Chain -> Phase 3 Bottom-up Financials -> Phase 4 Event Gatekeeper & Dynamic Override Assembly.
  - Abolished arbitrary fixed discount rates (-15%, -25%) in favor of quant-derived `Multiple C: Joint De-rating Floor ($84.16, -51.6%)` and priced-in vs residual downside benchmarking.
  - Implemented `apply_event_gatekeeper` in `economic_auditor.py`: automatically downgrades 🟢 Buy verdicts to `🟡 중립/관망 (🚨 거버넌스 긴급 경보 — WATCH)`.
  - Added smart portfolio reallocation in Section 7.3: Target frozen at 0.0%, Cash expanded to 40.0%, supply chain peers allocated 60.0% (TSM 30%, AMD 20%, AVGO 10%).
  - Enforced 100% Conditional Silence on normal tickers (Level 1~2: zero dead tables or headers).
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-12] Key Person Risk & Real-time News Sentinel Architecture
- **Created Concept**: `concepts/키맨-리스크-및-실시간-뉴스-센티널-아키텍처.md`
- **Key Architecture Decisions**:
  - Addressed the fatal real-world blind spot where quantitative financial pipelines completely missed the November 2026 Jensen Huang CEO scandal (extramarital affair, Chinese MSS spy allegations, board ouster discussions, congressional probe).
  - Designed a 4-tier solution:
    1. Layer 1: Lightweight, dependency-free Google News RSS multi-channel parser (`news_sentinel.py`) using Python standard libraries (`urllib` + `xml.etree.ElementTree`) fetching live headlines in <1 second without rate limits.
    2. Layer 2: Automatic Section 1-4 News & Governance Sentinel dashboard table rendering in reports.
    3. Layer 3: Mandatory "3-Pillar Negative Sentinel Scanning" protocol in `SKILL.md` (Key Person/Governance, Defect/Supply Chain, Breaking News).
    4. Layer 4: Socratic Key Person Risk & Founder's Premium derating valuation stress test framework.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-12] Report Data Slimming & Redundant Table Cleanup Architecture
- **Created Concept**: `concepts/리포트-데이터-슬림화-및-중복-표-정리-아키텍처.md`
- **Key Architecture Decisions**:
  - Full deprecation of Table 4 (투자 판단 신호등 매트릭스) to eliminate signal contradiction with Table 5 (e.g. AMD marked 🟡 in Table 4 vs 🔴 Value Trap in Table 5).
  - Unification and promotion of Table 5 to the single official decision matrix (`### 4. ⭐ 핵심 지표 의사결정 매트릭스`) with dynamic column compression (hiding inactive `· 제외` columns when all tickers share a profile).
  - Complete elimination of Table 2-1 (시계열별 PER · EPS 궤적, 90% redundant with Table 2) and Table 2-3 (피어 평균 대비 상대가치, arbitrary peer arithmetic average without statistical rigor).
  - Conditional rendering for Table 6 (일회성 손익 회계 감사): suppresses empty skeleton header when no company exhibits >=15% non-recurring distortions.
  - Renumbering and re-ordering Section 4.2 from 16 cluttered subsections down to 7 crisp, actionable sections.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-12] Crisis Support Level Matrix Slimming & Static Historical Crisis Deprecation
- **Created Concept**: `concepts/위기-지지선-매트릭스-슬림화-및-정적-위기-퇴출.md`
- **Key Architecture Decisions**:
  - Full deprecation of 4 obsolete static historical crisis benchmarks from 2024 (`yen_carry_20240805`, `iran_war_20240419`, `iran_war_20241001`, `martial_law_20241203`) which are +80%~+760% away from current prices and produce dead data.
  - Slimming Table 2 from 10 columns down to 7 practical columns: `지수/종목명`, `50 SMA`, `200 SMA`, `200선 이격도`, `52주 저점 완충도`, `최근 1년 조정 저점 (손절 기준선)`, `지지력 진단`.
  - Adoption of a 4-stage practical support signal band based on 1-year low buffer: `>+10%` 🟢 Safe Support, `+3~10%` 🟡 Support Test, `0~3%` 🚨 Near Breakdown, `<0%` 🔴 Breakdown.
  - Unification of Socratic invalidation ladder and narrative summaries around 200 SMA and 1-year correction low.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-12] Official MCP Transition & Legacy Data Scraping Deprecation Architecture Roadmap
- **Created Concept**: `concepts/공식-MCP-전환-및-레거시-수집-퇴출-로드맵.md`
- **Key Architecture Decisions**:
  - Full deprecation of fragile, unauthenticated web scrapers (`pykrx_fundamental`, `daum_quote`, `daum_investor_days`, `fetch_nasdaq_history`) and distorted macro proxies (`HYG/LQD`, `^IRX` 20bp error, hardcoded `rf_rate=4.5%`).
  - Promotion of 6 official MCP servers (`krx`, `dart`, `toss`, `ecos`, `fred`, `edgar`) to primary Tier-1 data sources.
  - Integration of 15-iteration empirical timing observations (Toss 20:06:03 / 06:10:04, KRX 08:00 AM batch, ECOS 18:09 KTB rates).
  - Preservation of Spec 003 pure offline snapshot determinism and 2-phase backward compatibility for `rebuild_section4.py`.
- **Master Index**: Updated `index.md` with cross-links.

## [2026-11-09] Economist's Deep System Audit: 12 Structural Blind Spots across 6 Economic Disciplines
- **Created Concept**: `concepts/경제학자-관점-12대-시스템-사각지대-및-고도화-이론.md` documenting 12 deep economic gaps across Financial Economics (ERP, ROIC-WACC, Total Shareholder Yield/Dilution), Macroeconomics (Macro-to-Micro transmission beta, Fisher Real Yield vs BEI, Copper/Gold & Yield Curve Un-inversion), Industrial Organization (Value Chain Profit Pool & CCC Bargaining Power, Lerner Index Pricing Power & DOL), Accounting Quality (Sloan Accruals & OCF/NI Cash Conversion), Econometrics/Portfolio Theory (Covariance/Risk Parity weights, Joint EPS-Multiple Stress Test), and Market Microstructure/Institutional Economics (ADV-normalized flows, Korea Discount governance & geopolitical exposure).

## [2026-11-09] Initial Construction: 5 Business Profiles & GICS 163 Sub-Industries Valuation Taxonomy
- **Action**: Initialized Karpathy 3-Layer LLM Wiki structure (`SCHEMA.md`, `index.md`, `log.md`, `concepts/`, `entities/`, `comparisons/`, `queries/`, `raw/`).
- **Created Concepts**:
  - `concepts/5대-비즈니스-프로파일-평가체계.md`: Detailed architectural guide on the 5 Business Profiles (`GENERAL`, `CYCLICAL`, `PLATFORM_SAAS`, `FINANCIAL_REIT`, `BIOTECH_RD`), active vs. excluded financial pillars, and the `profile_detector.py` routing engine.
  - `concepts/gics-163개-세부산업-지표-매트릭스.md`: Master lookup table covering all 11 GICS Sectors, 25 Industry Groups, 74 Industries, and 163 Sub-Industries with their primary operational KPIs and valuation multiples.
- **Created Entities (11 GICS Sectors)**:
  - `entities/10-에너지-energy.md` (7 sub-industries)
  - `entities/15-소재-materials.md` (17 sub-industries)
  - `entities/20-산업재-industrials.md` (25 sub-industries)
  - `entities/25-경기소비재-consumer-discretionary.md` (27 sub-industries)
  - `entities/30-필수소비재-consumer-staples.md` (12 sub-industries)
  - `entities/35-헬스케어-health-care.md` (10 sub-industries)
  - `entities/40-금융-financials.md` (18 sub-industries)
  - `entities/45-정보기술-information-technology.md` (12 sub-industries)
  - `entities/50-통신서비스-communication-services.md` (10 sub-industries)
  - `entities/55-유틸리티-utilities.md` (6 sub-industries)
  - `entities/60-부동산-real-estate.md` (17 sub-industries)
- **Skill Integration**: Synced taxonomy files to `.agents/skills/financial-analyst/references/taxonomy/`.
