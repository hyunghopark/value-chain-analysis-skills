---
name: financial-analyst
description: A specialized skill for conducting high-precision financial analysis and stock valuation of companies. Use when the user asks about the financial health, stock price, valuation multiples, earnings surprises, or investment risks of specific companies.
version: 2.0.0
allowed-tools: run_command search_web read_url_content
---

# Financial Analyst Skill

## Overview

The Financial Analyst skill provides a structured methodology for conducting institutional-grade financial analysis and stock valuation of public companies. It focuses on collecting real-time quantitative metrics (valuation multiples, profitability, financial health), examining historical earnings surprises, performing peer relative valuation, and compiling analyst consensus to determine investment suitability.

## When to Use

Trigger this skill when the user asks questions like:
- "Analyze the stock price and valuation of [Company]."
- "Is [Company] undervalued or overvalued at its current price?"
- "What are the financial metrics and P/E ratio of [Company]?"
- "Evaluate the financial health and investment risks of [Company]."

## Core Workflow

Follow these steps to conduct a high-precision corporate financial analysis:

### Step 1: Identify Tickers and Exchange Symbols
1. Find the correct stock ticker symbol and primary listing exchange for the target company (e.g., NVIDIA -> NASDAQ: NVDA, TSMC -> NYSE: TSM, SK Hynix -> KRX: 000660).
2. Note the currency in which the stock is traded.

### Step 2: Query Real-Time Financial Metrics
1. Run the Python helper script in the skill folder to programmatically query Yahoo Finance API for the exact, real-time prices, valuation multiples, profitability, and analyst consensus targets:
   `python3 scripts/get_financial_stats.py --tickers "NVDA,TSM,000660.KS"`
2. Review the printed markdown tables. They contain:
   - **Market Data**: Current Stock Price, 52-Week Range, Market Capitalization.
   - **Valuation Multiples**: Trailing P/E, Forward P/E, PEG, EV/EBITDA, EV/Revenue, P/S, P/B.
   - **Profitability**: ROE, ROA, Operating Margin, Net Margin, Gross Margin, EBITDA Margin.
   - **Growth**: Revenue Growth (YoY), Earnings Growth (YoY).
   - **Financial Health**: Debt-to-Equity, Current Ratio.
   - **Shareholder Return & Risk**: Dividend Yield, Beta (β).
   - **Analyst Consensus**: Consensus Recommendation (BUY/HOLD/SELL), Mean Target Price, Low/High Target Prices, and Implied Upside %.
   - **Investment Signal Matrix**: 🟢🟡🔴 auto-generated traffic-light assessment per company across 4 dimensions.
3. **Cross-Validation**: If any key metric (PE, ROE, Target Price) seems unusual, use `search_web` to verify against a second source (Investing.com, WSJ, Bloomberg). If the values differ by more than 5%, note the discrepancy in the report with a ⚠️ warning.

*Note: For non-US companies, the script will fetch local currency quotes (e.g. KRW for Korean stocks). Verify the exchange and scale before compiling the report.*

### Step 3: Fetch Historical Earnings Surprises
Retrieve the consensus estimate vs. actual results for both **EPS (Earnings Per Share)** and **Revenue** for the **past 4 quarters**:
1. Check if the company beat or missed expectations (and by what percentage).
2. Look for patterns of consistent earnings surprises, which often indicate strong execution or conservative guidance.

### Step 4: Perform Peer Group Comparison
Conduct a relative valuation check against 2–3 key industry competitors:
1. Compile a table showing Ticker, Current Price, Market Cap, Forward P/E, EV/EBITDA, and Net Profit Margin for the target company and its peers.
2. Calculate the average peer Forward P/E and EV/EBITDA.
3. Compare the target company's multiples to the peer averages to identify relative valuation premiums or discounts.

### Step 5: Gather Analyst Consensus & Price Targets
1. Collect the aggregate analyst recommendations (e.g., number of Buy, Hold, Sell ratings or percentage splits).
2. Retrieve the consensus stock price targets:
   - Low Target Price
   - Mean/Median Target Price
   - High Target Price
3. Calculate the implied upside or downside percentage from the current stock price to the mean target price:
   `Implied Upside % = ((Mean Target Price - Current Price) / Current Price) * 100`

### Step 6: Identify Key Risks (필수)
1. **반드시 3가지 이상의 핵심 리스크 요인을 식별**하고, 각 리스크에 영향도를 평가한다:
   - **H (High)**: 실현 시 주가 20% 이상 하락 가능
   - **M (Medium)**: 실현 시 주가 5~20% 영향
   - **L (Low)**: 실현 시 주가 5% 미만 영향
2. 표 형태로 정리: `| 리스크 | 설명 | 영향도 |`

### Step 7: Formulate Valuation Conclusion & Write Report
1. Classify the stock's valuation status:
   - **Undervalued**: Current multiples are below peer averages and historical averages, and there is significant upside to the mean analyst target.
   - **Fairly Valued**: Current multiples are in line with peers and historical averages, and the stock is trading close to the mean analyst target.
   - **Overvalued**: Current multiples are significantly above peer averages, trading at historical highs, or trading above/near the high analyst target price.
2. **Interpret the Investment Signal Matrix** (🟢🟡🔴): Explain why each company received its traffic-light rating and what the overall signal implies for investment decisions.
3. Synthesize findings into the template provided in `templates/financial_report_template.md`.
4. **CRITICAL**: Populate the report with exact numbers and insert inline citations (e.g. `[1]`, `[2]`). Add the clickable source URLs in the `## References` section.

## Best Practices for Analysis

- **Zero-Hallucination Policy:** Always run the `get_financial_stats.py` script for quantitative data. Do not estimate or assume figures.
- **Cross-Check Sources (5% Rule):** If any API value differs from a web source by more than 5%, flag it with ⚠️ and note both values.
- **Explain the Premium/Discount:** If a company trades at a premium to its peers (e.g., Nvidia trading at a higher Forward P/E than AMD), explain why (e.g., dominant market share, software ecosystem moat, higher ROE).
- **Mandatory Risk Assessment:** Every report MUST include at least 3 risks with H/M/L impact ratings (see Step 6).
- **Signal Matrix Interpretation:** Always include a written interpretation of the 🟢🟡🔴 traffic-light matrix in the conclusion.

## Resources

- **`templates/financial_report_template.md`**: The standard layout template for corporate financial analysis reports.
