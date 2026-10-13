---
name: financial-analyst
description: A specialized skill for conducting high-precision financial analysis and stock valuation of companies. Use when the user asks about the financial health, stock price, valuation multiples, earnings surprises, or investment risks of specific companies.
version: 2.1.0
allowed-tools: run_command search_web read_url_content
---

# Financial Analyst Skill

## Overview

The Financial Analyst skill provides a structured methodology for conducting institutional-grade financial analysis and stock valuation of public companies. It focuses on collecting real-time quantitative metrics (valuation multiples, profitability, financial health), examining 4-horizon earnings trajectories (TTM, FY0, FY1, NTM), performing DuPont capital quality decomposition, and executing a conservative, risk-controlled decision matrix to determine investment suitability.

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

### Step 2: Query Real-Time Financial Metrics
1. Run the Python helper script in the skill folder using the project virtual environment:
   ```bash
   venv/bin/python3 .agents/skills/financial-analyst/scripts/get_financial_stats.py --tickers "NVDA,TSM,000660.KS"
   ```
2. The script programmatically pulls real-time market data from Yahoo Finance API and blends official WiseReport / Naver Finance consensus for Korean stocks.
3. Review the generated tables:
   - **1. 주요 주가 및 시가총액 현황**: Stock Price, 52-Week Range, Market Capitalization, Currency.
   - **1-1. 📉 최근 5거래일 투자자별 수급 동향 (외국인 · 기관 · 개인 거래대금 추정)**: 최근 5거래일간 외국인/기관/개인의 순매매 수량 및 추정 대금(억 원), 외국인 지분율 변동을 정량 집계하여 수급 공백 및 패닉셀 여부 진단.
   - **2. 핵심 재무 및 밸류에이션 지표 (별표 체계 적용)**:
     - ⭐⭐⭐ **Tier 1 핵심 결정 지표**: Forward P/E (12M NTM), PEG Ratio, YoY Revenue Growth.
     - ⭐⭐ **Tier 2 확신 강화 지표**: EV/EBITDA, ROE, Debt/Equity.
     - **보조 지표**: Trailing P/E, Trailing EPS, Forward EPS, EV/Revenue, P/S, P/B, Forward P/B (12M), BPS, Forward BPS (12M), ROA, 듀퐁 재무레버리지 ($\text{Assets}/\text{Equity} = \text{ROE}/\text{ROA}$), OPM, NPM, GPM, EBITDA Margin, YoY Earnings Growth, 선행 EPS 성장률, 유동비율, 배당수익률, 배당성향, 베타 (β).
   - **2-1. 시계열별 PER · EPS 상세 궤적 및 TTM 기반 내재가치 (보조 시각화)**:
     - ① TTM, ② 올해(FY0), ③ 내년(FY1), ④ 12M 선행(NTM) 4종 PER 및 EPS 추이.
     - 자본 누적 효과를 반영한 Trailing P/B vs 12M Forward P/B, Trailing BPS vs 12M Forward BPS.
     - 선행 EPS 성장률 및 TTM PER 멀티플 유지 가정 시 1년 뒤 이론적 내재주가.
   - **3. 애널리스트 투자의견 및 목표 주가**: Consensus rating, Mean, Low/High Target Prices, Implied Upside %.
   - **4. 투자 판단 신호등 매트릭스**: 4개 차원(밸류에이션, 수익성, 성장성, 재무건전성) 🟢🟡🔴 기초 평가.
   - **5. ⭐ 핵심 지표 의사결정 매트릭스**: 6대 핵심 지표(Forward PE, PEG, 매출성장, EV/EBITDA, ROE, 부채비율)에 대한 보수적 판정 및 최종 종합 투자 의견.
   - **6. 🔍 [회계 감사] 일회성 비경상 손익(Unusual Items) 감지 및 정규화(Normalized) 지표 비교**:
     - `get_financial_stats.py`가 분기 손익계산서를 스캔하여 `Total Unusual Items > 세전이익 15%` 또는 `NPM > OPM` 역전 발생 시 자동 감지.
     - 일회성 이익(예: 투자자산 평가익, 자산처분 등)을 발라낸 **정규화 순이익(Normalized Net Income), 정규화 TTM EPS, 정규화 ROE**를 산출하여 명목 지표와 자동 대조.

### Step 3: Fetch Historical Earnings Surprises
Retrieve consensus estimates vs. actual results for both **EPS** and **Revenue** for the **past 4 quarters**:
1. Check whether the company beat or missed expectations (and by what percentage).
2. Look for patterns of consistent earnings surprises, which often indicate strong execution or conservative guidance.

### Step 4: Perform Peer Group Comparison
Conduct a relative valuation check against 2–3 key industry competitors:
1. Compile a table showing Ticker, Current Price, Market Cap, Forward P/E, EV/EBITDA, Net Profit Margin, and ROE for the target company and its peers.
2. Calculate the average peer Forward P/E and EV/EBITDA.
3. Compare the target company's multiples to peer averages to identify relative valuation premiums or discounts.

### Step 5: Gather Analyst Consensus & Price Targets
1. Collect aggregate analyst recommendations (Buy/Hold/Sell distributions).
2. Retrieve consensus price targets (Low, Mean, High).
3. Calculate implied upside/downside percentage:
   $$\text{Implied Upside \%} = \frac{\text{Mean Target Price} - \text{Current Price}}{\text{Current Price}} \times 100$$

### Step 6: Identify Key Risks (필수)
1. **반드시 3가지 이상의 핵심 리스크 요인을 식별**하고, 각 리스크에 영향도를 평가한다:
   - **H (High)**: 실현 시 주가 20% 이상 하락 가능
   - **M (Medium)**: 실현 시 주가 5~20% 영향
   - **L (Low)**: 실현 시 주가 5% 미만 영향
2. 표 형태로 정리: `| 리스크 요인 | 영향도 (H/M/L) | 설명 및 모니터링 포인트 |`

### Step 7: Formulate Valuation Conclusion & Write Report
1. Classify the stock's valuation status by strictly adhering to the **보수적 의사결정 매트릭스 규칙**:
   - **🟢 강력 매수 (Strong Buy)**: 🟢 4개 이상 AND **🔴 0개 (무결점 필수)**.
   - **🟢 매수 고려 (Buy)**: 🟢 3개 이상 AND 🔴 최대 1개.
   - **🟡 중립/관망 (Hold)**: 🟡 위주이거나 🟢와 🔴가 팽팽히 대립하는 경우.
   - **🔴 신중 접근 (Caution/Overvalued)**: **🔴 2개 이상 발생 시 밸류에이션/리스크 불문 즉시 강등**.
2. **Quality Audit (DuPont Decomposition)**:
   - Check DuPont Leverage ($\text{ROE} / \text{ROA}$). If ROE is high solely due to financial leverage (leverage > 3~4배), flag it as a capital structure risk.
3. Synthesize findings into the template provided in `templates/financial_report_template.md`.
4. **CRITICAL**: Populate the report with exact numbers and insert inline citations (e.g. `[1]`, `[2]`). Add clickable source URLs in the `## References` section.

## Best Practices for Analysis

- **Zero-Hallucination Policy:** Always run the `get_financial_stats.py` script for quantitative data. Do not estimate or assume figures.
- **Cross-Check Sources (5% Rule):** If any API value differs from a web source by more than 5%, flag it with ⚠️ and note both values.
- **Explain the Premium/Discount:** If a company trades at a premium to its peers (e.g., Nvidia trading at a higher Forward P/E than AMD), explain why (e.g., dominant market share, software ecosystem moat, higher ROE).
- **Mandatory Risk Assessment:** Every report MUST include at least 3 risks with H/M/L impact ratings (see Step 6).
- **Signal Matrix Interpretation:** Always include a written interpretation of the 🟢🟡🔴 traffic-light matrix and the 6-pillar conservative matrix in the conclusion.

## Resources

- **`templates/financial_report_template.md`**: The standard layout template for corporate financial analysis reports.
