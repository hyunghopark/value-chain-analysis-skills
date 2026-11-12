---
name: financial-analyst
description: A specialized skill for conducting high-precision financial analysis and stock valuation of companies. Use when the user asks about the financial health, stock price, valuation multiples, earnings surprises, or investment risks of specific companies.
version: 3.4.0
allowed-tools: run_command search_web read_url_content
---

# Financial Analyst Skill

## Overview

The Financial Analyst skill provides a structured methodology for conducting institutional-grade financial analysis and stock valuation of public companies. It collects quantitative metrics (valuation multiples, profitability, financial health), examines 4-horizon earnings trajectories (TTM, FY0, FY1, NTM), checks the earnings cycle and historical valuation band, tracks consensus revisions, and applies a conservative decision matrix whose rules differ for cyclical and non-cyclical companies.

## When to Use

Trigger this skill when the user asks questions like:
- "Analyze the stock price and valuation of [Company]."
- "Is [Company] undervalued or overvalued at its current price?"
- "What are the financial metrics, 4-horizon EPS/PER, and P/E ratio of [Company]?"
- "Evaluate the financial health, DuPont leverage, and investment risks of [Company]."

## Core Workflow

Follow these steps to conduct a high-precision corporate financial analysis:

### Step 1: Identify Tickers and Exchange Symbols
1. Find the correct stock ticker symbol and primary listing exchange for the target company (e.g., NVIDIA -> NASDAQ: NVDA, TSMC -> NYSE: TSM, SK Hynix -> KRX: 000660).
2. Note the currency in which the stock is traded and identify foreign currency/ADR quote distortions if applicable.
3. Decide whether the company is **cyclical** (memory semiconductors, chemicals, steel, shipping, refining, displays …). Pass such tickers with `--cyclical`; wrongly auto-detected ones with `--not-cyclical`.

### Step 2: Query Financial Metrics
1. Run the Python helper script in this skill folder (packages: `requirements.txt` in this skill folder).
   - **Claude Code** — `${CLAUDE_SKILL_DIR}` is replaced with this skill's folder. With [uv](https://docs.astral.sh/uv/) no setup is needed; otherwise `pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt"` into a virtual environment and run the script with that Python:
     ```bash
     uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/get_financial_stats.py" --tickers "NVDA,TSM,000660.KS" [--cyclical "000660.KS"] [--not-cyclical "..."] [--benchmarks "^KS11,^SOX"] [--weights "0.2,0.5,0.3"] [--snapshot "path/to/snapshot_data.json"]
     ```
   - **Antigravity** — use the project virtual environment (Windows: `venv\Scripts\python.exe`):
     ```bash
     venv/bin/python3 .agents/skills/financial-analyst/scripts/get_financial_stats.py --tickers "NVDA,TSM,000660.KS" [--cyclical "000660.KS"] [--not-cyclical "..."] [--benchmarks "^KS11,^SOX"] [--weights "0.2,0.5,0.3"] [--snapshot "path/to/snapshot_data.json"]
     ```
   - Pass `--snapshot <filepath>` to save a structured snapshot JSON file next to the report: every raw source response with the time it was received (`inputs`), and every number Section 4 shows with its source, basis, time and corrections (`values`). Section 4 is built from those raw inputs only, so `rebuild_section4.py` can rebuild the same Section 4 from the file later without network access.
2. The script pulls market data from the Yahoo Finance API and blends Naver Finance / WiseReport consensus for Korean stocks. For Korean stocks it also reconciles Yahoo's price history with the KRX close from Daum Finance (fills missing days, replaces wrong closes in the last 100 trading days). Yahoo quotes are delayed 15–20 minutes; the first line of the output states the generation time (KST) and the market state of each ticker.
3. Review the generated tables:
   - **1. 주요 주가 및 시가총액 현황**: Price, 52-week range, market cap (KRX stocks show Naver's common-share market cap).
   - **1-1. 최근 5거래일 투자자별 순매매 (추정)**: 순매수 수량 × 해당일 종가(수급 데이터 기준)로 추정한 금액과 외국인 지분율. 이 종가는 거래소 정규장 종가와 다를 수 있어(KI-001) 주가 등락은 1-3 표를 씁니다. 당일 행이 장중 스냅샷이면 '잠정'으로 표시됩니다.
   - **1-2. 기술적 지표 (RSI · 볼린저밴드)**: 진입 시점 보조용. 판정에는 쓰지 않습니다.
   - **1-3. 시장 비교 (지수·피어 동반 등락)**: 급락·급등이 기업 고유인지 업종·시장 전반인지 판별하는 근거.
   - **2. 핵심 재무 및 밸류에이션 지표 (별표 체계)**: ⭐⭐⭐ Forward P/E (12M NTM), PEG, YoY Revenue Growth · ⭐⭐ EV/EBITDA, ROE, Debt/Equity · 보조 지표. Forward P/E가 NTM이 아니면 기준(FY0 등)이 괄호로 표시됩니다.
   - **2-1. 경기순환 진단 및 과거 밸류에이션 밴드**: 순환업종 분류 근거, 연간 영업이익률 범위 대비 TTM 이익률(사이클 위치), 같은 방식으로 계산한 과거 P/B 밴드와 현재 P/B, 밴드 최저 회귀 시 주가.
   - **3. 투자의견·목표가 (단일 출처) / 3-1. 30일 추정치 동향·실적 일정 / 3-2. 최근 4분기 EPS 서프라이즈**.
   - **4. ⭐ 핵심 지표 의사결정 매트릭스**: 단일 공식 의사결정 매트릭스로 승격. 비즈니스 프로파일에 따라 무의미한 '· 제외' 열을 숨기는 동적 컬럼 압축이 적용되며 경제학 게이트키퍼 감등이 연동됩니다.
   - **5. 🏛️ [경제학 감사] Moat & 밸류 트랩 필터**: ROIC-WACC 초과이윤(EVA 스프레드), 실질 ERP, 총주주환원율(TSY), 현금전환율(CCR) 감사.
   - **(조건부 5-1) [회계 감사] 일회성 손익 감지 및 정규화 지표**: `Total Unusual Items > 세전이익 15%` 왜곡이 감지된 기업이 있을 때만 조건부 출력됩니다.
   - **6. 시나리오 스트레스 테스트**: 내년(FY1) 컨센서스 EPS 최저·평균·최고 × 배수 A(현재 배수 유지)·배수 B(목표가 내재 배수), 확률가중 기대값과 상방/하방 비율.
   - **7. 데이터 품질 경고**: 출처 간 5% 이상 차이, ADR 통화 보정, 잠정 수급, 가격 이력 보완·교정, 재무제표 반영 지연, 거래량 이상치, NTM이 아닌 Forward P/E 등. 앞에 붙은 `[KI-xxx]`는 스킬 저장소 `wiki/known-issues/`의 사건 문서 번호이며, 규칙은 `references/rules/data-quality.md`에 있습니다.

### Step 3: Review Historical Earnings Surprises & Official Filings (`finance-api-hub` MCP Priority Checklist)
1. Use table 3-2 (last 4 quarters, EPS estimate vs. actual) from the script.
2. When verifying figures, filling qualitative sections, or resolving missing/conflicting metrics, follow the **Data Source & MCP Priority Checklist (`references/rules/data-quality.md`)**:
   - **PER (TTM) / PBR / BPS**: `1순위 네이버 금융` → `2순위 KRX MCP (krx_stock) / DART MCP (dart_financials + stockTotqySttus)` → `3순위 Toss MCP` → `4순위 Yahoo Finance`
   - **12M Forward PER / 선행 EPS (한국)**: `1순위 WiseReport` → `2순위 네이버 금융 (cnsPer/cnsEps)` → `3순위 Yahoo Finance`
   - **현재가 / 정규장 종가 (한국)**: `1순위 KRX MCP (krx_stock 정규장 확정 종가)` · 장중/당일 15:30 직후는 `네이버 금융 / Toss MCP (toss_stock_candles) / Meritz API` → `2순위 다음 금융 (daum_days)` → `3순위 Yahoo Finance`
   - **재무제표 & 10년 사이클 밴드**:
     - 한국: `1순위 DART MCP (dart_financials 10년+ K-IFRS / dart_indicators)` → `2순위 Yahoo Finance` → `3순위 네이버/WiseReport`
     - 미국: `1순위 SEC EDGAR MCP (sec_financials 10년+ XBRL + 파생 Q4 자동산출 / sec_concept)` → `2순위 Yahoo Finance`
   - **발행주식수 · 자기주식수 · 총주주환원율(TSY) 희석 검증**:
     - 한국: `1순위 DART MCP (dart_report: stockTotqySttus 보통주·우선주·자사주 분리, tesstkAcqsDspsSttus 자사주 취득·처분·소각, alotMatter 배당)` → `2순위 KRX MCP (LIST_SHRS)` → `3순위 네이버 금융` → `4순위 Yahoo Finance (KI-007 점검)`
     - 미국: `1순위 SEC EDGAR MCP (dei:EntityCommonStockSharesOutstanding)` → `2순위 Yahoo Finance`
   - **수급 · 공매도 · 프로그램 매매 (한국)**: `1순위 Toss MCP (toss_market_investor_trading 실제 거래대금+7대 기관 세분화, toss_stock_investor_trading, toss_stock_short_selling, toss_stock_program_trades)` → `2순위 네이버 금융 (naver_trend 수량×종가 추정)` → `3순위 다음 금융 (daum_quote 장중 외인 지분율 추정)`
   - **무위험금리($R_f$) & 타인자본비용($k_d$) (WACC / EVA / Implied ERP)**:
     - 한국: `1순위 ECOS MCP (ecos_market_rates: 국고채 10년 ktb10y, 회사채 AA- corpAA / BBB- corpBBB)` → `2순위 Toss MCP (toss_market_indicator_prices)`
     - 미국: `1순위 FRED MCP (fred_bundle("rates") DGS10/DFII10, fred_bundle("credit") BAMLC0A4CBBB)` → `2순위 Yahoo Finance (^TNX)`
   - **잠정실적 · 매출 서프라이즈 · 수주 · 오버행 리스크 원문**:
     - 한국: `1순위 DART MCP (dart_disclosures(pblntf_ty="I") + dart_document 원문 표, cbIssuAcmslt 전환사채, piicDecsn 유상증자)` → `2순위 실시간 웹 검색 (search_web)`
     - 미국: `1순위 SEC EDGAR MCP (sec_filings + sec_document(section="item7"|"item1a"|"item2.02"), sec_search 키워드 검색)` → `2순위 실시간 웹 검색 (search_web)`
3. Look for patterns of consistent beats or misses, and note whether the latest quarter broke the pattern.

### Step 4: Perform Peer Group Comparison
1. Use table 2-3 (peer averages and premium/discount) from the script.
2. Explain the premium or discount. When cyclical and non-cyclical companies are mixed, say that the average is only indicative.

### Step 5: Gather Analyst Consensus & Price Targets
1. Use table 3: the mean, low and high targets and the analyst count all come from Yahoo so that one row uses one source; the Korean consensus (Naver) is a separate column for comparison.
2. Use table 3-1 for the 30-day estimate direction and the next earnings date.
3. Implied upside:
   $$\text{Implied Upside \%} = \frac{\text{Mean Target Price} - \text{Current Price}}{\text{Current Price}} \times 100$$
   A consensus target is the analysts' assumption, not evidence of value; compare it with scenario multiple B in table 7.

### Step 6: Identify Key Risks (필수)
1. **반드시 3가지 이상의 핵심 리스크 요인을 식별**하고, 각 리스크에 영향도를 평가한다:
   - **H (High)**: 실현 시 주가 20% 이상 하락 가능
   - **M (Medium)**: 실현 시 주가 5~20% 영향
   - **L (Low)**: 실현 시 주가 5% 미만 영향
2. 표 형태로 정리: `| 리스크 요인 | 영향도 (H/M/L) | 설명 및 모니터링 포인트 |`
3. Write at least one **counter-thesis** (why the verdict could be wrong) and the data that would change the verdict.

### Step 7: Formulate Valuation Conclusion & Write Report
1. The verdict comes from the script's decision matrix (table 5). Do not override it silently; if you disagree, say why with sources. The authoritative rules are `references/rules/verdict-matrix.md` and `references/rules/cycle-position.md`; the summary below must match them. The cycle-position 🔴 means the margin broke its ~4-year record, not that a peak is confirmed.
   - **Pillars**
     - 일반 기업 (7개): Forward PE(<18 🟢 <30 🟡) · PEG(<1 🟢 <2 🟡) · 매출성장(>20% 🟢 >5% 🟡) · EV/EBITDA(<12 🟢 <20 🟡) · ROE(>20% 🟢 >10% 🟡, 일회성 감지 시 정규화 ROE) · D/E(<50% 🟢 <100% 🟡) · 30일 추정치 방향((상향−하향)/전체 ≥ +30% 🟢, ≤ −30% 🔴)
     - 🔄 순환업종 (4개): P/B 밴드 위치(중앙값 이하 🟢, 최고 이하 🟡, 최고 초과 🔴) · 사이클 위치(TTM 영업이익률이 과거 중앙값 미만 🟢, 최고 이하 🟡, 최고 초과 🔴) · 30일 추정치 방향 · D/E. Forward PE·PEG·매출성장·EV/EBITDA·ROE는 이익 정점에서 좋아 보이므로 '제외'됩니다.
   - **Verdict rules** (applied in this order)
     - **🔴 신중 접근**: 🔴 2개 이상
     - **⚪ 판단 보류**: 유효 신호 4개 미만 (데이터 부족을 매수로 읽지 않음)
     - **🟢 강력 매수 후보**: 🟢 4개 이상 AND 🔴 0개
     - **🟢 매수 고려**: 🟢 3개 이상 AND 🔴 1개 이하
     - **🟡 중립/관망**: 그 외
   - **2-Tier 경제학 해자 & 밸류 트랩 게이트키퍼 (1단계 하향 원칙)**:
     - 1차 매트릭스 판정이 🟢(강력 매수 후보/매수 고려)라도, **Table 6-1 [경제학 감사]** 지표에서 🔴(자본잠식/주주가치 훼손/이익 품질 부실)이 발생하면 자동으로 **`🟡 중립/관망 (⚠️ 밸류 트랩 경보: [사유])`**으로 1단계 하향 조정합니다.
     - 4대 감사 지표:
       1. **EVA Spread** ($\text{ROIC} - \text{WACC}$): $\ge +3\%p$ 🟢, $0\sim 3\%p$ 🟡, $<0\%p$ 🔴 (음수 시 초과이익 소멸 및 자본잠식)
       2. **Implied ERP** ($1/\text{Forward PE} - R_f$): $\ge +3\%p$ 🟢, $0\sim 3\%p$ 🟡, $<0\%p$ 🔴 (주식 위험 프리미엄 결여 시 채권 대비 열위)
       3. **Total Shareholder Yield** ($\text{Dividend Yield} + \text{Net Buyback Yield}$): $\ge 3\%$ 🟢, $0\sim 3\%$ 🟡, $<0\%$ 🔴 (유상증자 등 희석 시 주주가치 훼손)
       4. **Cash Conversion Ratio** ($\text{OCF} / \text{Net Income}$): $\ge 1.0$ 🟢, $0.7\sim 1.0$ 🟡, $<0.7$ 🔴 (이익의 현금화 실패 시 분식/운전자본 부실 경보)
2. **Quality Audit (DuPont Decomposition)**:
   - Check DuPont Leverage ($\text{ROE} / \text{ROA}$). If ROE is high solely due to financial leverage (leverage > 3~4배), flag it as a capital structure risk.
3. **Worst-Case Joint De-rating Floor (Multiple C)**:
   - 시나리오 분석(Table 7)에 Bear EPS와 밴드 역사적 최저 배수를 결합한 복합 디레이팅 바닥가(`Multiple C`)를 추가하여, 이익 급감과 멀티플 동시 압축 시의 최대 하방 위험을 점검합니다.
3. Synthesize findings into the template provided in `templates/financial_report_template.md`.
4. **CRITICAL**: Populate the report with exact numbers and insert inline citations (e.g. `[1]`, `[2]`). Add source titles, publication dates and clickable URLs in the `## References` section (not just a site's home page).

## Best Practices for Analysis

- **Zero-Hallucination Policy:** Always run `get_financial_stats.py` for quantitative data, including the scenario table. Do not estimate or assume figures (operating profit forecasts, target multiples, market shares) without a cited source.
- **Cross-Check Sources (5% Rule):** The script now flags gaps above 5% between sources automatically (table 8). When you quote such a figure, mention both values and which one the tables use.
- **Cyclical Awareness:** For cyclical companies a low P/E or PEG near peak margins is not, by itself, evidence of undervaluation. Use the P/B band and cycle position in table 2-2, and compare history only within that table's period.
- **Explain the Premium/Discount:** If a company trades at a premium to its peers, explain why (e.g., dominant market share, software ecosystem moat, higher ROE).
- **Label estimates honestly:** Investor-flow amounts are estimates; intraday rows are provisional. Do not call them 확정 or say they 증명 anything.
- **Mandatory Risk Assessment:** Every report MUST include at least 3 risks with H/M/L impact ratings (see Step 6) and a counter-thesis.
- **Signal Matrix Interpretation:** Always include a written interpretation of the 🟢🟡🔴 matrices in the conclusion, including which pillars drove the verdict.
- **Clean-Slate Policy for Snapshots:** Past snapshot files (`*_data.json`) are strictly for post-run audit, verification, and debugging. When executing a new analysis, NEVER read or anchor to past snapshot files. Always collect fresh real-time data from APIs and live sources.

## Resources

- **`templates/financial_report_template.md`**: The standard layout template for corporate financial analysis reports.
- **`references/taxonomy/`**: Official reference documentation for the **5 Business Profiles (`business-profiles.md`)**, the **GICS 163 Sub-Industries Valuation Matrix (`gics-163-subindustries.md`)**, and the **Economist's 12 Structural Blind Spots & Upgrade Theory (`economic-12-blindspots.md`)** (mirrored in the project's Karpathy 3-Layer LLM Wiki at `wiki/index.md`, `wiki/concepts/`, and `wiki/entities/`).
- **`references/rules/`**: Source of truth for verdict thresholds (`verdict-matrix.md`), the cycle-position signal (`cycle-position.md`), data-source rules (`data-quality.md`), data snapshot format (`data-snapshot.md`), and report number checks (`report-number-check.md`).
- **`scripts/profile_detector.py`**: Sector-Adaptive 5-Profile routing engine (`GENERAL`, `CYCLICAL`, `PLATFORM_SAAS`, `FINANCIAL_REIT`, `BIOTECH_RD`) that automatically classifies tickers and selects profile-specific evaluation pillars and Table 2-4 auxiliary KPIs.
- **`scripts/economic_auditor.py`**: Economic Moat & Value Trap Gatekeeper engine. Calculates EVA Spread ($\text{ROIC}-\text{WACC}$), Implied ERP, Total Shareholder Yield (dividend + net buyback), Cash Conversion Ratio (OCF/NI), Cash Conversion Cycle (CCC), and worst-case Joint De-rating Floor (Multiple C). Applies 1-step downgrade rule for Table 6-1.
- **`scripts/snapshot.py`**: Standard data snapshot recorder and serializer. Every number shown in Section 4 is recorded, including the verdict thresholds under `rules.*`; `attach_section4` stores the Section 4 baseline after the report is assembled.
- **`scripts/check_report_numbers.py`**: Checks a finished report against its paired snapshot — body numbers (script value / cited / unsupported), Section 4 edits and snapshot coverage, citations and references, leftover `[AI_TODO]`. `--section` prints the '숫자 점검 결과' block, `--json` writes the structured result, `--fetch-sources` (local only) compares cited numbers with the articles. Exit code 0 = no undocumented problems, 1 = problems, 2 = cannot run.
- **`scripts/collect.py`**: The only code that reaches external sources (Yahoo, Naver, WiseReport, Daum, PyKrx) or reads the clock. Stores each response with its receive time as a raw input; failures are recorded, not raised.
- **`scripts/raw_inputs.py`**: Raw input format of a format-2 snapshot (tables keep dtype, timezone name, datetime unit and index names) and read access; a missing item names its path.
- **`scripts/rebuild_section4.py`**: Rebuilds Section 4 from a snapshot alone and compares it with the stored baseline, values and warnings (exit 0 same / 1 differs / 2 cannot rebuild). `--weights`/`--cyclical`/`--not-cyclical` with `--out` recompute under other assumptions into a new file marked as not a report. Rules: `data-snapshot.md` §9.
- **`scripts/check_data_sources.py`**: Periodic cross-source health check (Yahoo vs KRX close via Daum vs Naver, Yahoo vs Nasdaq.com, statement freshness, WiseReport layout).
