---
name: market-analyst
description: A specialized institutional skill for top-down macro, market regime, sector rotation, drawdown diagnostics, and Socratic dialectical stress testing. Use when analyzing major US/global market indices (^GSPC, ^NDX, ^DJI, ^RUT, ^SOX), sector rotation (11 SPDR ETFs), macro risk barometers (VIX, 10Y Yield, DXY, Oil, Credit spreads), historical crisis support breakdowns (e.g. Yen carry crash, Iran war levels), or conducting Socratic questioning and cognitive bias audits on investment theses.
version: 1.0.0
allowed-tools: run_command search_web read_url_content
---

# Market Analyst Skill (소크라테스식 탑다운 시장·매크로 분석 스킬)

## Overview

The `market-analyst` skill provides an institutional-grade top-down macroeconomic and stock market regime analysis framework. While bottom-up single-company tools (`financial-analyst`) evaluate individual corporate valuations and supply-chain tools (`value-chain-analyzer`) map structural moats, `market-analyst` answers **macro-level and market-wide questions**:
- Why did the market, tech, or semiconductor sector crash or rally?
- Did major indices break below critical historical crisis support levels (e.g., 2024-08-05 Yen carry crash, 2024-04-19 Iran-Israel escalation)?
- Is money rotating into defensive safe havens or expanding into cyclical risk-on assets?
- What is the exact market regime among 6 institutional states, and what should the portfolio cash allocation be?
- **소크라테스식 주식 스킬 (Socratic Investing Engine)**: Conducting rigorous self-interrogation across 6 Socratic pillars, auditing 5 cognitive biases (Recency, Anchoring, Confirmation, Loss Aversion, Action Bias), formulating a mandatory Bear Anti-Thesis, and establishing a falsifiable Thesis Invalidation Ladder.

---

## When to Use

Trigger this skill when the user asks across 3 core use cases and 8 representative query archetypes:
1. **Top-Down Macro & Market Indices**:
   - `미국증시`: S&P 500 (`^GSPC`), Nasdaq 100 (`^NDX`), Dow (`^DJI`), Russell 2000 (`^RUT`), SOX (`^SOX`).
   - `코스피`: KOSPI (`^KS11`), KOSDAQ (`^KQ11`), USD/KRW (`USDKRW=X`), and domestic crisis supports.
   - `한국증시`: Broad Korean equity market diagnosis with foreign capital flows and exchange rate pressure.
2. **Sector & Industry Cycle Benchmarks**:
   - `반도체`: Global semiconductor cycle (^SOX, SMH, NVDA, 005930.KS, 000660.KS).
   - `기술주식`: Big Tech valuation compression and growth cycle (^NDX, XLK).
3. **Single Stock Macro Beta & Technical Posture**:
   - `삼성전자`, `LG전자`, `테슬라`: Single company ticker/name inputs.
   - Diagnoses the stock's macro sensitivity, beta vs parent index (`005930.KS.beta_parent`), 200 SMA distance, and drawdown, and automatically bridges to `financial-analyst` for bottom-up 3-statement valuation and consensus revisions.
- Commands: `/market-analyst`, `/market-analyst 코스피`, `/market-analyst 반도체`, `/market-analyst 삼성전자`

---

## Core Workflow

### Step 1: Automatic Query Profile & Benchmark Resolution
The engine automatically routes the query using `scripts/target_resolver.py` into one of 6 institutional profiles:
1. `US_MARKET` (`미국증시`): Indices: `^GSPC`, `^NDX`, `^DJI`, `^RUT`, `^SOX`. Macro: VIX, 10Y Yield, DXY, Oil, Gold, Credit.
2. `KR_INDEX` (`코스피`): Indices: `^KS11`, `^KQ11`, `^GSPC`, `^SOX`. Macro: `USDKRW=X`, VIX, 10Y, DXY, Oil, Gold, Credit.
3. `KR_MARKET` (`한국증시`): Indices: `^KS11`, `^KQ11`, `^GSPC`, `^SOX`. Macro: `USDKRW=X`, VIX, 10Y, DXY, Oil, Gold, Credit.
4. `SECTOR_SEMI` (`반도체`): Indices: `^SOX`, `SMH`, `^NDX`, `^GSPC`, `005930.KS`, `000660.KS`, `NVDA`.
5. `SECTOR_TECH` (`기술주식`): Indices: `^NDX`, `XLK`, `^SOX`, `^GSPC`.
6. `SINGLE_STOCK` (`삼성전자`, `LG전자`, `테슬라` 등): Target ticker + parent index benchmark (`^KS11` or `^NDX`/`^GSPC`) + sector ETF. Calculates beta vs benchmark and embeds an institutional handoff guide to `financial-analyst`.

### Step 2: Query Real-Time Market Data & Risk Metrics (`finance-api-hub` MCP Priority Checklist)
Run the Python calculation script to fetch live market data and cross-verify or enrich macro pillars using the **Data Source & MCP Priority Checklist (`.agents/skills/financial-analyst/references/rules/data-quality.md`)**:
- **금리 & 수익률 곡선 (`10Y-2Y`, `10Y-3M`, 실질금리 TIPS, 기대인플레 BEI)**:
  - 미국: `1순위 FRED MCP (fred_bundle("rates"): DGS10, DGS2, DGS3MO, T10Y2Y, T10Y3M, DFII10, T10YIE, SOFR)` → `2순위 Toss MCP (toss_market_indicator_prices)` → `3순위 Yahoo Finance (^TNX, ^IRX — ^IRX 20bp 할인율 오차 주의)`
  - 한국: `1순위 ECOS MCP (ecos_market_rates: baseRate, ktb3y, ktb10y, cd91d, cp91d)` → `2순위 Toss MCP`
- **신용 스프레드 (`Credit Spread` & 대출태도)**:
  - 미국: `1순위 FRED MCP (fred_bundle("credit"): BAMLH0A0HYM2 하이일드 OAS, BAMLC0A0CM IG OAS, BAMLC0A4CBBB BBB OAS, DRTSCILM 대출태도)` → `2순위 Yahoo Finance (HYG/LQD 상대강도 대용치)`
  - 한국: `1순위 ECOS MCP (ecos_market_rates: corpAA - ktb3y, corpBBB - ktb3y, cp91d)` → `2순위 KRX MCP (krx_bond)`
- **글로벌 & 국내 유동성 (`Net Liquidity` & 증시주변자금)**:
  - 미국: `1순위 FRED MCP (fred_bundle("liquidity"): 연준 순유동성 WALCL - TGA - RRP 자동산출, M2SL, WRESBAL)`
  - 한국: `1순위 ECOS MCP (ecos_data("901Y056"): 고객예탁금, 신용융자잔고)` → `2순위 Toss MCP (toss_market_investor_trading 시장 전체 외인·기관·7대 기관 수급)`
- **한국 지수 · 시장 등락비율(Breadth) · 휴장일 캘린더**:
  - `1순위 KRX MCP (krx_index 공식 종가, krx_stock("market_summary") 전 종목 상승/하락 ADR)` + `Toss MCP (toss_kr_market_calendar, toss_market_indicator_prices)` → `2순위 다음 금융 (daum_index_days)` → `3순위 Yahoo Finance (^KS11, ^KQ11)`
- **환율 (`USD/KRW`, `DXY`) · 원자재 · 매크로 발표 일정**:
  - 환율: `1순위 ECOS MCP (ecos_market_rates.usdkrw 공식 매매기준율)` + `Toss MCP (toss_market_indicator_prices 실시간 환율)` → `2순위 FRED MCP (DTWEXBGS, DEXKOUS)` → `3순위 Yahoo Finance (USDKRW=X, DX-Y.NYB)`
  - 매크로 일정: `1순위 FRED MCP (fred_release_calendar CPI·고용·GDP·FOMC 일정, fred_bundle("macro"|"labor"))` → `2순위 실시간 웹 검색 (search_web)`
- **Claude Code**:
  ```bash
  uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/generate_market_report.py" --market "코스피"
  ```
- **Antigravity**:
  ```bash
  venv/bin/python3 .agents/skills/market-analyst/scripts/generate_market_report.py --market "삼성전자"
  ```
The script outputs formatted Section 4 Markdown tables and records every data point into the format-2 snapshot file.

### Step 3: 3-Tier Dynamic Support & Adaptive Crisis Benchmark Diagnostics
Review Table 1 & Table 2:
1. **Tier 1 (이동평균 추세 지지선)**:
   - 50일선(50 SMA), 200일선(200 SMA), 52주 최저가(52W Low)와 현재가 이격도.
   - 단기 추세 반전 및 200일선 장기 추세 지지 탄력성 판정 (-3% 초과 하회 시 구조적 이탈).
2. **Tier 2 (최근 1년 실전 조정 저점 및 손절 기준선)**:
   - 롤링 252거래일(1년) 동안 피크-투-트러프(Peak-to-Trough) 낙폭 `(Close - RollingMax) / RollingMax`가 최대였던 날짜의 저점 가격(Trough Price), 당시 낙폭률(%), 현재가 대비 완충도(Buffer %)를 알고리즘으로 자동 추출하여 시간이 흐르면 최신 위기로 자동 롤오버.
   - 실전 매매에서 1차 기계적 손절선으로 직결.
   - 4단계 실전 완충도 판정:
     - `> +10.0%`: `🟢 안전 지지` (하방 안전마진 확보, 분할 매수 유지)
     - `+3.0% ~ +10.0%`: `🟡 지지 테스트` (단기 지지선 방어 확인 필요, 신규 매수 보류)
     - `0.0% ~ +3.0%`: `🚨 손절선 임박` (직전 파동 저점 근접, 이탈 시 즉시 비중 축소 준비)
     - `< 0.0%`: `🔴 지지선 붕괴 (손절 집행)` (구조적 지지선 붕괴, 기계적 손절 및 현금화)
3. **외환 리스크 바로미터 (USD/KRW)**:
   - `< 1,350원`: 🟢 환율 안정 (외인 수급 우호)
   - `1,350원 ~ 1,420원`: 🟡 환율 경계 (외인 수급 압박)
   - `> 1,420원`: 🔴 고환율 경보 (외인 이탈 가속 및 시스템 리스크)
5. **하락 메커니즘 3요소 분해**:
   - 밸류에이션 압축 vs 유동성 강제 청산 / 외환 유출 vs 펀더멘털 실적 하향.

### Step 4: Sector Rotation & Breadth Analysis
Review Table 3:
1. Examine 5-day and 1-month Relative Strength (RS) vs SPY.
2. Check the **경기민감 vs 경기방어 5일 순환매 스프레드**:
   - `> +2.0%`: 공격적 위험 선호 (Risk-On)
   - `0.0% ~ +2.0%`: 온건한 순환매 (Mild Risk-On)
   - `-2.0% ~ 0.0%`: 중립 및 숨고르기 (Neutral Rotation)
   - `< -2.0%`: 안전자산 도피 (Flight to Safety / Risk-Off)

### Step 5: Socratic Dialectical Examination (소크라테스식 6대 질문)
Address the 6 Socratic interrogation pillars in Section 6:
1. **명료화 (Clarification)**: Define the exact nature of the drop without emotional wording.
2. **숨은 가정 검증 (Hidden Assumptions)**: Identify which market assumptions (e.g. Fed put, infinite AI capex) broke.
3. **정량적 근거 탐색 (Empirical Evidence)**: Cite hard numbers (200 SMA distance, forward P/E, credit spread).
4. **변증법적 반대 논증 (Bear Anti-Thesis)**: Formulate the 3 core arguments of the institutional bear camp.
5. **연쇄 파급효과 시뮬레이션 (Cascading Consequences)**: Detail what happens if support fails (CTA short flip, negative gamma, forced liquidations).
6. **메타인지 점검 (Meta-Cognitive Evaluation)**: Audit personal psychological state against objective data.

### Step 6: Cognitive Bias Audit & Thesis Invalidation Ladder
1. **5대 인지 편향 정량 감사**:
   - 최신 편향 (Recency Bias)
   - 닻내림 편향 (Anchoring Bias)
   - 확증 편향 (Confirmation Bias)
   - 손실 회피 편향 (Loss Aversion)
   - 충동적 행동 편향 (Action Bias)
2. **가설 무효화 사다리 (Thesis Invalidation Ladder)**:
   - State explicit numerical criteria that will invalidate the Bull hypothesis (e.g., 3-day close below 200 SMA, VIX > 30 for 2 days).
   - State explicit numerical criteria that will invalidate the Bear hypothesis (e.g., VIX < 20, 50 SMA volume breakout).

### Step 7: Formulate Market Regime Verdict & Action Guidance
Adopt the script's decision matrix verdict from Table 5:
- 🟢 **상승 확장 국면 (Bull Expansion)**: 현금 10%
- 🟡 **과열 / 후기 국면 (Overheating / Late Cycle)**: 현금 25~35%
- 🟡 **건전한 조정 국면 (Healthy Correction / Pullback)**: 현금 20~30%
- 🔴 **유동성 충격 / 패닉 국면 (Liquidity Shock / Panic Dip)**: 현금 40~50%
- 🔴 **스태그플레이션 / 공급 쇼크 (Stagflation / Supply Shock)**: 현금 40~60%
- 🔴 **구조적 약세 국면 (Structural Bear Market)**: 현금 60~80%

### Step 8: Master Report Generation & Verification
1. Generate the complete institutional report file:
   - **Claude Code**:
     ```bash
     uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/generate_market_report.py" --market "미국지수" --theme "빅테크 및 반도체 급락 진단"
     ```
   - **Antigravity**:
     ```bash
     venv/bin/python3 .agents/skills/market-analyst/scripts/generate_market_report.py --market "미국지수" --theme "빅테크 및 반도체 급락 진단"
     ```
   Creates `reports/[Market]_[YYYYMMDD]_Market_Analysis_Report.md` and `*_data.json`.
2. Populate the research `[AI_TODO]` placeholders.
3. Verify numbers and Section 4 hash:
   - **Claude Code**:
     ```bash
     uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/check_market_report_numbers.py" "reports/[보고서].md"
     ```
   - **Antigravity**:
     ```bash
      venv/bin/python3 .agents/skills/market-analyst/scripts/check_market_report_numbers.py "reports/[보고서].md"
      ```
4. Rebuild Section 4 offline to verify snapshot determinism:
   - **Claude Code**:
     ```bash
     uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/rebuild_market_section4.py" "reports/[보고서]_data.json"
     ```
   - **Antigravity**:
     ```bash
     venv/bin/python3 .agents/skills/market-analyst/scripts/rebuild_market_section4.py "reports/[보고서]_data.json"
     ```

---

## Best Practices & Objectivity Rules

1. **Zero-Hallucination Policy**: Every single number in Section 4 is generated directly by the Python calculation script. Never edit or overwrite numbers in Section 4 by hand.
2. **Clean-Slate Policy**: Never read past report files or snapshot files when initiating a new analysis. Always query fresh real-time data from APIs.
3. **Mandatory Bear Anti-Thesis**: Even if the analyst or user is extremely bullish, the report MUST articulate 3 sound institutional bear arguments.
4. **Falsifiability (Invalidation Ladder)**: Every verdict must be accompanied by explicit numerical conditions that would prove the thesis wrong.
5. **No Silent Overrides**: The final market regime and cash recommendation must match the script's Section 4 Table 5 output.

---

## Resources

- `templates/market_report_template.md`: Institutional markdown report layout.
- `references/rules/market-regime-matrix.md`: Source of truth for 6 market regimes and 5 pillars.
- `references/rules/socratic-audit-rules.md`: Rules for Socratic 6 pillars, 5 cognitive biases, and invalidation ladders.
- `references/rules/drawdown-diagnostics.md`: Formulations for drawdowns, 200 SMA distance, and crisis support benchmarks.
- `references/rules/sector-rotation.md`: Classification of 11 SPDR sectors and relative strength spread rules.
- `references/rules/data-snapshot.md`: Data snapshot schema specifications.
- `references/rules/report-number-check.md`: Report number verification standards.
- `scripts/target_resolver.py`: Query classifier and target ticker profile resolver.
- `scripts/get_market_stats.py`: Master analysis and calculation engine.
- `scripts/generate_market_report.py`: Master report generation CLI.
- `scripts/check_market_report_numbers.py`: Report number and hash validation tool.
- `scripts/rebuild_market_section4.py`: Offline Section 4 rebuild and SHA-256 verification tool.
- `scripts/market_metrics.py`: Metric calculation library.
- `scripts/market_regime.py`: Regime decision matrix library.
- `scripts/socratic_auditor.py`: Socratic questioning and cognitive bias auditing library.
- `scripts/market_collect.py`: Yahoo Finance real-time market data collector.
- `scripts/market_raw_inputs.py`: Raw input serialization and deserialization.
- `scripts/market_snapshot.py`: Snapshot recorder and Section 4 baseline attacher.
