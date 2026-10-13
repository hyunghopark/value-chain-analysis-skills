---
name: investment-strategy
description: Use when the user requests an investment analysis of an industry, combining value chain mapping and stock valuations.
allowed-skills: value-chain-analyzer financial-analyst
---

# Investment Strategy Workflow

## Overview

The Investment Strategy Workflow coordinates the `value-chain-analyzer` and `financial-analyst` skills to generate a comprehensive, investment-grade strategy report for any industry. By combining supply chain mapping (structural analysis) with stock valuation (quantitative analysis), it helps investors identify which bottleneck companies in a supply chain offer the best risk/reward profile.

## Process Flow

> ⚠️ **[중요 원칙: 독립적 신규 분석 원칙 (Clean-Slate Policy)]**  
> 워크플로우 실행 시 기존 프로젝트에 저장되어 있는 과거 보고서 파일들(`*_Investment_Strategy_Report.md` 등)을 **일체 검색하거나 열람하지 마십시오**. 과거 보고서에 의존할 경우 낡은 데이터 오염(Data Contamination)이나 편향(Anchoring Bias)이 발생합니다. 항상 현재 시점의 새로운 웹 리서치와 실시간 API 데이터만을 바탕으로 독립적인 신규 분석을 수행해야 합니다.

When the user triggers this workflow (e.g. "I want an investment strategy for [Industry]"), execute the following steps:

### Phase 1: Value Chain Analysis & Bottleneck Identification (Skill A)
1. Trigger the `value-chain-analyzer` skill on the target [Industry].
2. Identify the Upstream, Midstream, and Downstream segments using fresh web research.
3. **[비교 분석 대상 4개사 필수 선정 규칙 (1+2+1 Framework)]**:
   - **① 타겟 기업 (1개사, [타겟])**: 분석 의뢰 기업. 다각화 복합 대기업의 경우 질의 맥락의 언급 부문(예: HBM, 스마트폰 등)을 우선하며, 언급이 없을 시 최근 영업이익 기여도 1위 사업부(예: 삼성전자는 DS 메모리)를 기준으로 함.
   - **② 수평 직접 경쟁사 (2개사, [직접경쟁])**: 핵심 사업부 기준 글로벌 시장 점유율 2위 및 3위 과점 경쟁사 (예: 삼성전자 분석 시 SK하이닉스 `000660.KS`, 마이크론 테크놀로지 `MU`).
   - **③ 수직 가치사슬 핵심 병목 (1개사, [병목협력])**: 공정 수율, 패키징 또는 납품을 좌우하는 독점적 서플라이체인 핵심 파트너/공급사 (예: TSMC `TSM` 또는 ASML).
   - **Mermaid 시각화 연동**: 다이어그램 노드에 `[타겟]`, `[직접경쟁]`, `[병목협력]` 태그를 포함하여 색상과 굵기로 역할을 시각적으로 명확히 구분합니다.
4. **[필수 시장 변동성 및 최근 현안 진단]**: 단순 장기 전망에 그치지 않고, 반드시 `search_web`을 통해 **최근 1~5일간의 주가 급변동(급락/급등 원인), 52주 고점 대비 낙폭(Drawdown %), 및 시장을 흔든 직접적 트리거(실적 피크아웃 논쟁, 경쟁사 기술 발표, 규제, 수급 등)**를 철저히 조사합니다. (검색 예: `[기업명/산업] 주가 급락 원인 최근 이슈`, `실적 피크아웃 논쟁`).
   - **수급 정량화 (필수)**: 텍스트 설명에 그치지 않고, `get_financial_stats.py`가 산출하는 **최근 5거래일 투자자별(외국인·기관·개인) 순매매 대금 추정치 및 외국인 지분율 변동 표**를 Section 1.2 및 Section 4에 필수 인용하여 수급 공백/패닉셀 여부를 정량적으로 입증합니다.

### Phase 2: High-Precision Financial Audits & Valuation (Skill B)
1. For each of the top 3 companies identified in Phase 1, trigger the `financial-analyst` skill.
2. Retrieve their correct stock tickers and listing exchanges.
3. Gather institutional-grade valuation multiples and quality metrics:
   - **4-Horizon PER & EPS**: TTM, FY0 (Current Year), FY1 (Next Year), and 12M Forward (NTM) day-weighted EPS/PER trajectory.
   - **Asset & Book Value**: Forward P/B (12M), Forward BPS (12M), P/B, and BPS.
   - **Multiples & Growth**: PEG (using NTM), EV/EBITDA, YoY Revenue & Earnings Growth.
   - **Quality & Financial Health**: ROE, ROA, DuPont Leverage ($\text{Assets} / \text{Equity} = \text{ROE} / \text{ROA}$), Debt/Equity, Dividend Payout Ratio.
4. Conduct relative valuation (peer comparisons) and check historical earnings surprises.
5. Retrieve analyst consensus targets and calculate implied upside.
6. Review the conservative 6-pillar Traffic-Light Matrix (🟢/🟡/🔴) and automatic synthesis verdict.
7. **[필수 회계 감사: 일회성 비경상 손익(Unusual Items) 자동 분리 & 정규화(Normalized) 지표 점검]**:
   - `get_financial_stats.py`가 분기 손익계산서를 자동 감사하여 대규모 일회성 이익/손실(`Total Unusual Items > 15%` 또는 `NPM > OPM`) 발생 시 '정규화 ROE/EPS'를 자동 산출합니다.
   - 보고서 Section 4의 6번 표(회계 감사 박스)에 이를 명시하고, Section 5 개별 기업 분석 시 명목 지표 착시와 본업 실적을 반드시 분리하여 평가합니다.

### Phase 3: Synthesis & Strategy Formulation
To prevent human-like omissions (e.g., missing financial tables), you MUST use the master script to auto-generate the report template.

1. Execute the master template script (ensure the project virtual environment is active):
   ```bash
   venv/bin/python3 .agents/workflows/scripts/generate_strategy_report.py --industry "[Industry Name]" --upstream "[Upstream info]" --midstream "[Midstream info]" --downstream "[Downstream info]" --tickers "[Ticker1,Ticker2...]"
   ```
2. The script will automatically create a brand new file in the `reports/` folder named `reports/[Industry_Name]_[YYYYMMDD]_Investment_Strategy_Report.md`. (If executed multiple times on the same day, it automatically increments version tags like `_v2.md` to prevent any overwriting and preserve audit history). This file will already contain:
   - Standardized 8-section institutional report layout with top-level Executive Stance callout.
   - Mermaid value chain flowchart.
   - Fully populated real-time financial tables (Market data, Multiples, 4-Horizon PER/EPS trajectory, Consensus, and Conservative Signal Matrix).
   - Ticker-specific analysis sections dynamically generated under Section 5.
3. Use the `replace_file_content` (or similar editing tools) to locate the `[AI_TODO]` placeholders within the generated file.
4. Replace these placeholders with your detailed research analysis (e.g., market overview, moat analysis, valuation verdicts, risk factors). Do NOT manually type out the financial tables; the script handles that.

## Best Practices

- **Zero-Prior-File Dependency (Clean-Slate):** 과거 작성된 보고서 파일을 참조하지 않고, 오직 실시간 시장 데이터와 최신 공시/뉴스만을 기준으로 리포트를 작성합니다.
- **Never Overwrite (히스토리 보존):** 보고서는 항상 `reports/` 디렉토리에 실행 날짜 기반 신규 파일로 누적 보관되어 시계열적 투자 판단 변화를 추적할 수 있도록 합니다.
- **하이브리드 시각 견지 (구조적 해자 + 당일 시황 변동성):** 장기 밸류체인 구조(10년 해자)와 당일 급락/급등의 시장 상황(단기 노이즈 vs 펀더멘털 타격)을 반드시 균형 있게 다룹니다. 급락장에서는 "왜 빠졌는지"와 "분할 매수 타이밍"을 실전적으로 제시해야 합니다.
- **Connect Supply Chain Strengths to Financial Multiples:** Explain *why* a company trades at a premium or discount. For example, "Company X trades at a premium Forward P/E of 40x because it holds a 90% market share in the critical packaging segment, giving it immense pricing power."
- **Strict Risk Matrix Alignment:** Respect the conservative decision rules (no 'Strong Buy' if any red signal exists; automatic downgrade to 'Caution' if 2 or more red signals exist).
- **Enforce Referencing:** Every quantitative figure (market share, P/E ratio, consensus target price) must be accompanied by an inline citation and a clickable URL reference.
- **Maintain Modular Outputs:** Do not mix up the phases; complete the supply chain mapping first, then fetch the financial data, and finally synthesize the investment strategy.
