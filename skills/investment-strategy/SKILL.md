---
name: investment-strategy
description: Use when the user requests an investment analysis of an industry, combining value chain mapping (upstream/midstream/downstream), bottleneck identification, and stock valuation (4-horizon P/E, cyclical-aware decision matrix, consensus revisions, data-driven scenario stress test, and a verdict-conditional trading plan).
version: 2.0.0
allowed-skills: value-chain-analyzer financial-analyst
---

# Investment Strategy

## Overview

The Investment Strategy Skill coordinates the `value-chain-analyzer` and `financial-analyst` skills to generate a comprehensive, investment-grade strategy report for any industry. By combining supply chain mapping (structural analysis) with stock valuation (quantitative analysis), it helps investors judge which bottleneck companies in a supply chain offer a favorable risk/reward profile — **and which do not**.

## 🧭 객관성 원칙 (Objectivity Rules) — 모든 단계에 우선 적용

> 이 스킬은 "매수 근거를 찾는 도구"가 아니라 "판단을 검증하는 도구"입니다.

1. **결론을 먼저 정하지 않습니다.** 어떤 섹션도 '증명·입증'을 목표로 쓰지 않습니다. 데이터가 기존 논리와 반대로 나오면 그대로 씁니다.
2. **스크립트 판정과 일치시킵니다.** 한 줄 결론과 기업별 판정은 Section 4 › 5번 매트릭스의 '종합 판단'과 같아야 합니다. 다르게 쓰려면 Section 6.2에 이유와 출처를 적습니다.
3. **급락은 그 자체로 매수 근거가 아닙니다.** 먼저 하락 원인을 기업 고유 / 업종 전반 / 시장 전체로 판별하고(Section 4 › 1-3 시장 비교 표), 매매 전략은 판정에 따라 씁니다.
4. **숫자는 스크립트나 출처에서만 가져옵니다.** 스크립트에 없는 수치(영업이익 전망, 점유율, 가격 민감도 등)는 출처 제목·발행일·URL을 붙여 인용하고, 출처가 없으면 쓰지 않습니다. 직접 추정 계산을 만들지 않습니다.
5. **과거 비교는 데이터 범위 안에서만 합니다.** 밸류에이션 역사 비교는 Section 4 › 2-2 밴드 표의 기간 안에서만 합니다. 표에 없는 시기(예: 2008년)와 비교하지 않습니다.
6. **최신 정보만 촉매로 씁니다.** 촉매·기술 현황은 90일 이내 출처로 확인합니다. 더 오래된 정보는 날짜를 밝히고 '과거 정보'로 표시합니다.
7. **추정·잠정은 그대로 표기합니다.** 수급 금액은 '추정', 장중 데이터는 '잠정'으로 쓰고 '확정·증명·입증' 같은 표현을 쓰지 않습니다.
8. **데이터 품질 경고를 무시하지 않습니다.** Section 4 › 8번 경고에 나온 수치를 본문에서 인용할 때는 경고 내용을 함께 밝힙니다.

## Process Flow

> ⚠️ **[중요 원칙: 독립적 신규 분석 원칙 (Clean-Slate Policy)]**  
> 스킬 실행 시 기존 프로젝트에 저장되어 있는 과거 보고서 파일들(`*_Investment_Strategy_Report.md` 등)을 **일체 검색하거나 열람하지 마십시오**. 과거 보고서에 의존할 경우 낡은 데이터 오염(Data Contamination)이나 편향(Anchoring Bias)이 발생합니다. 항상 현재 시점의 새로운 웹 리서치와 실시간 API 데이터만을 바탕으로 독립적인 신규 분석을 수행해야 합니다.

When the user triggers this skill (e.g. "I want an investment strategy for [Industry]" or typing `/investment-strategy`), execute the following steps:

### Phase 1: Value Chain Analysis & Bottleneck Identification (Skill A)
1. Trigger the `value-chain-analyzer` skill on the target [Industry].
2. Identify the Upstream, Midstream, and Downstream segments using fresh web research.
3. **[비교 분석 대상 4개사 필수 선정 규칙 (1+2+1 Framework)]**:
   - **① 타겟 기업 (1개사, [타겟])**: 분석 의뢰 기업. 다각화 복합 대기업의 경우 질의 맥락의 언급 부문(예: HBM, 스마트폰 등)을 우선하며, 언급이 없을 시 최근 영업이익 기여도 1위 사업부(예: 삼성전자는 DS 메모리)를 기준으로 함.
   - **② 수평 직접 경쟁사 (2개사, [직접경쟁])**: 핵심 사업부 기준 글로벌 시장 점유율 2위 및 3위 과점 경쟁사 (예: 삼성전자 분석 시 SK하이닉스 `000660.KS`, 마이크론 테크놀로지 `MU`).
   - **③ 수직 가치사슬 핵심 병목 (1개사, [병목협력])**: 공정 수율, 패키징 또는 납품을 좌우하는 독점적 서플라이체인 핵심 파트너/공급사 (예: ASML, TSMC `TSM`).
   - **역할이 겹치면 함께 표기**: 병목 기업이 타겟의 특정 사업부와 경쟁 관계이면 `[병목협력·경쟁]`처럼 두 역할을 모두 표기하고 본문에 설명합니다 (예: 삼성전자 분석 시 TSMC는 AI 칩·HBM 생태계의 병목이자 삼성 파운드리의 경쟁사).
   - **Mermaid 시각화 연동**: 다이어그램 노드에 `[타겟]`, `[직접경쟁]`, `[병목협력]` 태그를 포함하여 색상과 굵기로 역할을 구분합니다. 항목 이름 안에는 쉼표를 쓰지 않습니다(필요하면 `·` 사용).
4. **[필수 시장 변동성 및 최근 현안 진단]**: 웹 검색(Antigravity `search_web` · Claude Code `WebSearch`)으로 **최근 1~5일간의 주가 급변동, 52주 고점 대비 낙폭, 시장을 흔든 직접적 트리거**(실적·피크아웃 논쟁, 경쟁사 기술 발표, 규제, 수급 등)를 조사합니다. (검색 예: `[기업명/산업] 주가 급락 원인`, `[기업명] 잠정실적`).
   - **원인 판별은 데이터로**: Section 4 › 1-3 시장 비교 표(지수·해외 피어 등락)를 근거로 '기업 고유 / 업종 전반 / 시장 전체' 중 무엇인지 먼저 판단합니다. 공매도 잔고는 보조 지표일 뿐, 하락 원인을 '국내 수급'으로 단정하는 근거가 되지 않습니다.
   - **수급 정량화**: `get_financial_stats.py`의 1-1 표(최근 5거래일 투자자별 순매매 추정, 외국인 지분율)를 Section 1.2와 Section 4에 인용합니다. 금액은 '추정', 당일 행이 잠정이면 '잠정'으로 표기합니다.
5. **[검증 체크리스트 (필수 — 보고서 Section 1.3)]**: 각 항목에 출처 제목·발행일·URL을 붙입니다.
   - 타겟·경쟁사의 **최근 실적 및 잠정실적** (한국 기업은 잠정실적 공시가 확정 실적보다 3주가량 앞섭니다) — 스크립트 7번 시나리오의 EPS 범위와 맞는지 확인
   - **다음 실적 발표일** (Section 4 › 3-1)
   - **최근 30일 이익 추정치 방향** (Section 4 › 3-1)
   - **지수·해외 피어 동반 등락 여부** (Section 4 › 1-3)
   - **트리거의 사실관계**: 발표 원문 확인, 공개된 사양·수율·고객사 여부
   - **핵심 촉매의 현재 상태**: 90일 이내 출처만

### Phase 2: High-Precision Financial Audits & Valuation (Skill B)
1. For each of the **4 companies** selected in Phase 1 (1+2+1), trigger the `financial-analyst` skill.
2. Retrieve their correct stock tickers and listing exchanges.
3. **[경기순환 업종 지정]**: 메모리 반도체·화학·철강·해운·정유·디스플레이처럼 이익이 업황에 따라 크게 출렁이는 기업은 `--cyclical`로 지정합니다. 스크립트도 연간 순이익이 50% 이상 감소한 이력으로 자동 감지하지만, 가용 기간(약 4년)이 짧아 놓칠 수 있습니다. 잘못 감지된 기업은 `--not-cyclical`로 제외합니다.
   - 순환업종은 이익 정점에서 PER·PEG가 가장 낮아 보입니다. 그래서 스크립트는 순환업종을 **P/B 밴드 위치 · 사이클 위치(이익률) · 추정치 방향 · 부채비율**로 판정하고, PER·PEG·매출성장·EV/EBITDA·ROE는 '제외'로 표시합니다.
4. The script gathers (do not retype these numbers by hand):
   - **4-Horizon PER & EPS**: TTM, FY0, FY1, and 12M Forward (NTM) day-weighted EPS/PER. NTM이 아닌 기준이면 표에 기준이 함께 표시됩니다.
   - **Asset & Book Value**: P/B, BPS, simple Forward P/B·BPS(과거 P/B와 비교 금지), and the **historical P/B band computed with the same method as the current P/B** (Section 4 › 2-2).
   - **Multiples & Growth**: PEG, EV/EBITDA, YoY Revenue & Earnings Growth.
   - **Quality & Financial Health**: ROE, ROA, DuPont Leverage, Debt/Equity, Dividend Payout Ratio.
   - **Market comparison** (Section 4 › 1-3), **peer averages** (2-3), **consensus targets from one source** (3), **30-day EPS revisions and earnings dates** (3-1), **last 4 quarters' EPS surprises** (3-2).
5. Review the decision matrices (Section 4 › 4, 5). Verdicts: 🟢 강력 매수 후보 / 🟢 매수 고려 / 🟡 중립·관망 / 🔴 신중 접근 / ⚪ 판단 보류(데이터 부족).
6. **[회계 감사: 일회성 손익 분리 & 정규화 지표]**: 스크립트가 최근 4분기에서 큰 일회성 손익(`Total Unusual Items > 세전이익 15%` 또는 `순이익 > 영업이익`)을 감지하면, 명목·정규화 ROE/EPS를 **같은 분모**로 다시 계산합니다. 분류는 Yahoo 기준이라 큰 항목은 공시(DART·IR)로 확인하고, 평가이익이 이후 분기에 되돌려질 가능성(관련 자산 가격 변동)을 함께 적습니다.
7. **[시나리오 스트레스 테스트]**: 스크립트가 내년(FY1) 컨센서스 EPS 최저·평균·최고에 두 가지 배수(A: 현재 배수 유지, B: 목표가 내재 배수)를 적용해 계산합니다. 보고서는 이 표를 그대로 인용합니다.
8. **[데이터 품질 경고]**: Section 4 › 8번에 출처 간 5% 이상 차이, 통화 보정, 잠정 수급, 가격 이력 누락 등이 모입니다. 해당 수치를 인용할 때 경고를 함께 밝힙니다.

### Phase 3: Synthesis & Strategy Formulation
To prevent omissions (e.g., missing financial tables), you MUST use the master script to auto-generate the report template.

1. Execute the master template script. The three skills (`investment-strategy`, `financial-analyst`, `value-chain-analyzer`) must sit side by side in the same skills folder, because this script runs the other two.
   - **Claude Code** — `${CLAUDE_SKILL_DIR}` is replaced with this skill's folder. With [uv](https://docs.astral.sh/uv/) no setup is needed; otherwise `pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt"` into a virtual environment and run the script with that Python:
     ```bash
     uv run --no-project --with-requirements "${CLAUDE_SKILL_DIR}/requirements.txt" python "${CLAUDE_SKILL_DIR}/scripts/generate_strategy_report.py" --industry "[Industry Name]" --upstream "[Upstream info]" --midstream "[Midstream info]" --downstream "[Downstream info]" --tickers "[Target,Peer1,Peer2,Bottleneck]" [--cyclical "[Tickers]"] [--not-cyclical "[Tickers]"] [--benchmarks "^KS11,^SOX"] [--weights "0.2,0.5,0.3"]
     ```
   - **Antigravity** — activate the project virtual environment (Windows: `venv\Scripts\python.exe`):
     ```bash
     venv/bin/python3 .agents/skills/investment-strategy/scripts/generate_strategy_report.py --industry "[Industry Name]" --upstream "[Upstream info]" --midstream "[Midstream info]" --downstream "[Downstream info]" --tickers "[Target,Peer1,Peer2,Bottleneck]" [--cyclical "[Tickers]"] [--not-cyclical "[Tickers]"] [--benchmarks "^KS11,^SOX"] [--weights "0.2,0.5,0.3"]
     ```
   - 보조 스크립트(다이어그램·재무 데이터)가 실패하면 보고서 파일을 만들지 않고 종료합니다. **표를 손으로 채우지 말고** 오류를 해결한 뒤 다시 실행합니다.
2. The script creates a new file `reports/[Industry_Name]_[YYYYMMDD]_Investment_Strategy_Report.md` (KST date; same-day reruns get `_v2.md`, `_v3.md` ... so nothing is overwritten). `reports/` goes in the project folder when the skills are installed inside a project (`<project>/.agents/skills` or `<project>/.claude/skills`), and in the current working folder for personal installs (`~/.claude/skills`, `~/.agents/skills`); `--output` sets the path explicitly. The file already contains:
   - The analysis timestamp (KST) and market state of each ticker.
   - Mermaid value chain flowchart.
   - All quantitative tables (Section 4), including the verdicts, cyclical diagnostics, scenario table and data-quality warnings.
   - Ticker-specific analysis blocks under Section 5, the verification checklist (1.3), and the Bear-thesis section (6.2).
3. Use your file-editing tool to locate the `[AI_TODO]` placeholders within the generated file.
4. Replace these placeholders with your research analysis. Do NOT manually type out or edit the numbers in Section 4; the script handles that.

## Best Practices

- **Zero-Prior-File Dependency (Clean-Slate):** 과거 작성된 보고서 파일을 참조하지 않고, 오직 실시간 시장 데이터와 최신 공시/뉴스만을 기준으로 리포트를 작성합니다.
- **Never Overwrite (히스토리 보존):** 보고서는 항상 `reports/` 디렉토리에 실행 날짜 기반 신규 파일로 누적 보관되어 시계열적 투자 판단 변화를 추적할 수 있도록 합니다.
- **장기 구조 + 단기 시황을 함께 보되, 순서를 지킵니다:** 장기 밸류체인 구조(해자)와 단기 급변동을 균형 있게 다룹니다. 급락장에서는 "왜 빠졌는지"를 데이터로 먼저 판별하고, 매매 전략은 판정에 따라 제시합니다.
- **Connect Supply Chain Strengths to Financial Multiples:** Explain *why* a company trades at a premium or discount. For cyclical companies, explain the multiple in the context of the earnings cycle (a low P/E at peak earnings is not, by itself, cheapness).
- **Strict Risk Matrix Alignment:** 🔴 2개 이상이면 '신중 접근', 🔴가 1개라도 있으면 '강력 매수' 불가, 유효 신호가 4개 미만이면 '판단 보류'입니다.
- **Enforce Referencing:** 웹에서 가져온 모든 수치(점유율, 실적, 목표가 등)에는 본문 인용 번호와 함께 출처 제목·발행일·URL을 붙입니다. 사이트 홈페이지만 가리키는 링크는 출처로 인정하지 않습니다.
- **Maintain Modular Outputs:** Complete the supply chain mapping first, then fetch the financial data, and finally synthesize the investment strategy.
- **시나리오 스트레스 테스트 인용:** Section 6.1은 스크립트 7번 표를 그대로 인용합니다. 하방이 음수면 그대로 적고, 결론에 맞추려고 배수·확률·EPS를 바꾸지 않습니다. 확률은 `--weights`로만 바꾸며, 바꿨다면 이유를 적습니다.
- **반대 논리 (Bear Thesis) 필수:** Section 6.2에 판단이 틀릴 수 있는 이유 3가지와 판단 무효화 조건을 출처와 함께 적습니다.
- **기술적 지표는 보조 수단:** RSI·볼린저밴드는 판정이 나온 뒤 진입 시점을 고르는 데만 씁니다. 과매도 자체를 매수 근거로 쓰지 않습니다.
- **판정 연동 실행 전략:** 7.1은 판정(🟢/🟡/🔴)에 따라 분할 매수 계획 / 관망 조건 / 비중 축소 근거 중 하나로 씁니다. 7.2 배분은 판정과 연동하고(🔴 판정 기업은 0% 또는 축소), 현금 비중과 업종 집중 위험을 함께 밝힙니다.
- **면책 문구 유지:** 보고서 끝의 면책 문구를 지우지 않습니다.
