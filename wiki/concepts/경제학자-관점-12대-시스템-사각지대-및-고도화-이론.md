---
title: "경제학자 관점의 시스템 심층 감사: 6대 경제학 분과별 12대 사각지대 및 고도화 이론"
created: 2026-11-09
updated: 2026-11-09
tags: [economics, macroeconomics, industrial-organization, financial-economics, econometrics, institutional-economics, system-audit]
sources: [fama-french, damodaran-valuation, porter-io, markowitz-portfolio, kahneman-tversky]
---

# 경제학자 관점의 시스템 심층 감사: 6대 경제학 분과별 12대 사각지대 및 고도화 이론

> **관련 문서**: [Index](../index.md) | [5대 비즈니스 프로파일 평가 체계](5대-비즈니스-프로파일-평가체계.md) | [GICS 163개 세부산업 매트릭스](gics-163개-세부산업-지표-매트릭스.md)

본 문서는 현재 구축된 **3-Tier 통합 투자 전략 시스템(`market-analyst` + `value-chain-analyzer` + `financial-analyst`)**을 6대 경제학 분과(**거시·통화경제학, 미시·산업조직론, 재무경제학, 계량·포트폴리오 이론, 시장미시구조론, 제도·지정학 경제학**)의 시각에서 전수 감사(Full Audit)하여 발굴한 **12대 구조적 사각지대(Blind Spots)**와 이론적 보완 체계를 정리한 문서입니다.

---

## 한눈에 보는 6대 경제학 분과별 12대 사각지대 요약

| 경제학 분과 | 사각지대 번호 및 핵심 주제 | 현재 시스템(`v3.4`)의 한계 | 경제학적 본질 및 이론적 해법 |
| :--- | :--- | :--- | :--- |
| **I. 재무경제학**<br>(Financial Economics) | **① 무위험금리($R_f$)·자본비용(WACC) 단절**<br>(Static Multiples Trap) | 금리가 1%든 5%든 `PER < 18 = 🟢`, `배당 ≥ 5% = 🟢` 고정 상수 판정 | **주식위험프리미엄($\text{ERP} = E/P - R_f$)** 및 **초과이윤($\text{EVA Spread} = \text{ROIC} - \text{WACC}$)** 도입 |
| **I. 재무경제학**<br>(Financial Economics) | **② 총주주환원율(TSY) 및 희석(Dilution) 누락**<br>(Incomplete Capital Allocation) | 현금배당수익률(`div_yield`)만 반영하고 자사주 매입/소각 및 유상증자·SBC 희석 미반영 | **총주주환원율($\text{Dividend} + \text{Net Buyback} + \text{Debt Paydown}$)** 및 주식수 증감률($\Delta\text{Shares}$) 추적 |
| **II. 거시·국제금융학**<br>(Macro & Int'l Finance) | **③ 거시변수 → 개별기업 손익 전이(Transmission) 단절**<br>(Macro-to-Micro Disconnect) | `USD/KRW > 1,420원 = 🔴`처럼 모든 기업에 동일한 거시 부호 적용 | 산업·기업별 **거시 민감도 벡터(FX Beta, Rate Beta, Commodity Beta)**로 수혜/피해 방향 분기 |
| **II. 거시·국제금융학**<br>(Macro & Int'l Finance) | **④ 명목금리만 보고 실질금리(Real Yield)·기대인플레 누락**<br>(Nominal Illusion) | 미국 10년물 명목금리(`^TNX`) 수준과 5일 변동폭(bps)만 측정 | 피셔 방정식($r = i - \pi^e$)에 따른 **실질금리(TIPS) vs 기대인플레이션(BEI)** 분해로 금리 상승 원인 규명 |
| **II. 거시·국제금융학**<br>(Macro & Int'l Finance) | **⑤ 실물 경기 선행지표 및 글로벌 유동성(M2/TGA) 부재**<br>(Financial Price Bias) | 주가 이평선, VIX, ETF 가격 등 금융시장 후행·동행 가격에만 의존 | **구리/금 비율(Copper/Gold)**, **장단기 금리차 역전 해소(Un-inversion)**, **글로벌 순유동성** 개념 결합 |
| **III. 미시·산업조직론**<br>(Micro & Industrial Org.) | **⑥ 가치사슬 교섭력(Bargaining Power) 정량화 부재**<br>(Qualitative Value Chain) | Phase 2(`generate_mermaid.py`)가 단순 텍스트 화살표(`Upstream → Midstream → Downstream`)만 그림 | 각 가치사슬 단계의 **영업이익 풀(Profit Pool) 점유율**, **시장집중도(HHI/CR3)**, **운전자본 전가력(CCC 차이)** 정량 비교 |
| **III. 미시·산업조직론**<br>(Micro & Industrial Org.) | **⑦ 가격결정력(Pricing Power)과 영업레버리지(DOL) 미분해**<br>(Volume vs. Price Blindness) | 명목 매출성장률(`rg`)과 영업이익률(`OPM`) 단일 시점 수치만 확인 | 원가 상승기 **$\Delta\text{GPM}$(매출총이익률 방어력)** 및 **영업레버리지 도($\text{DOL} = \%\Delta\text{EBIT} / \%\Delta\text{Sales}$)** 측정 |
| **IV. 회계·기업재무학**<br>(Corporate Finance) | **⑧ 발생주의 이익의 질(Accruals Quality)과 현금전환율 누락**<br>(Earnings Manipulation Risk) | 일회성 손익(`Unusual Items`)만 체크하고 운전자본 부풀리기(매출채권·재고 급증) 미감지 | **슬로언 발생액 비율(Sloan Accruals)** 및 **현금전환율($\text{OCF} / \text{Net Income} \ge 1.0$)** 감사 추가 |
| **V. 계량·포트폴리오 이론**<br>(Econometrics & Portfolio) | **⑨ 단일 팩터 베타를 넘어선 다중 팩터(Multi-Factor) 및 공분산 부재**<br>(Naive Diversification) | 60일 단순 시장 베타(`compute_stock_beta`)와 사용자 임의 비중(`--weights`)만 사용 | 4개 비교 종목 간 **수익률 상관계수 행렬(Correlation Matrix)**, **변동성 역가중(Risk Parity)** 비중 산출 |
| **V. 계량·포트폴리오 이론**<br>(Econometrics & Portfolio) | **⑩ 시나리오 테스트의 '실적-멀티플 독립성 오류'**<br>(Zero-Correlation Stress Test) | Table 7이 `Bear EPS × 현재 멀티플(Multiple A)`처럼 이익과 배수를 독립 변수로 곱함 | 실제 침체기에는 **EPS 하락과 멀티플 수축(De-rating)이 동시 발생(양의 상관관계)**하는 **Joint Stress Test** 필요 |
| **VI. 시장미시구조·행동경제**<br>(Market Microstructure) | **⑪ 수급의 시가총액/거래대금 대비 정규화(Normalization) 부재**<br>(Absolute Flow Distortion) | 외국인·기관 5일 순매매 금액(억 원) 절대치만 나열 | **유동주식 시가총액 대비 순매수 비중(% of Float)** 및 **일평균 거래대금(ADV) 대비 수급 강도(Flow Z-Score)** 필요 |
| **VII. 제도·지정학 경제학**<br>(Institutional Economics) | **⑫ 코리아 디스카운트(거버넌스) 및 공급망 지정학 리스크 정량화 부재**<br>(Institutional Blindness) | 한국 기업과 미국 기업에 동일한 PBR/PER 잣대를 적용하거나 정성 서술에 그침 | **지배주주 지분율·자사주 미소각·중복상장 할인율** 및 **관세/보조금(IRA·CHIPS)/수출통제 노출도** 체계화 |

---

## 분과별 심층 분석 및 경제학 이론 상세

### I. 재무경제학 (Financial Economics): 기회비용과 자본배분의 경제학

#### 사각지대 ①: 무위험이자율($R_f$)과 자본비용(WACC)이 제거된 '절대 배수'의 함정
- **현재 코드 진단**: [`verdict-matrix.md`](../../.agents/skills/financial-analyst/references/rules/verdict-matrix.md)는 `Forward P/E < 18 = 🟢`, `ROE > 20% = 🟢`를 고정 상수로 정의합니다.
- **경제학적 비판**:
  1. **고든 성장 모델(Gordon Growth Model)**에 따르면 적정 주가수익비율(Justified P/E)은 다음과 같습니다:
     $$\frac{P_0}{E_1} = \frac{1 - b}{k_e - g} = \frac{\text{Payout Ratio}}{R_f + \beta \cdot \text{ERP} - g}$$
     즉, 무위험금리($R_f$, 국채 10년물)가 상승하면 분모인 자기자본비용($k_e$)이 커져 적정 P/E는 필연적으로 하락해야 합니다.
  2. **회계적 이익(Accounting Profit) vs 경제적 이익(Economic Profit / EVA)**:
     회계사는 당기순이익이 0보다 크면 흑자라고 부르지만, 경제학자는 **투하자본수익률(ROIC)이 가중평균자본비용(WACC)을 초과($\text{ROIC} - \text{WACC} > 0$)할 때만 진정한 부(Wealth)가 창출**된다고 봅니다. 만약 $\text{ROIC} = 6\%$인데 $\text{WACC} = 9\%$인 기업이 설비투자를 늘려 매출을 20% 성장시키면, 현재 시스템은 `매출성장 > 20% = 🟢`를 주지만 실제로는 **성장할수록 기업가치가 파괴되는 '가치 파괴적 성장(Value-Destructive Growth)'**입니다.
- **고도화 지표**:
  - **일드 갭(Yield Gap / Implied ERP)**: $\text{Forward Earnings Yield}(1/\text{FPE}) - \text{10Y Treasury Yield}(R_f)$
  - **초과이윤 스프레드(EVA Spread)**: $\text{ROIC} - \text{WACC}$ (또는 금융주의 경우 $\text{ROE} - k_e$)

#### 사각지대 ②: 현금배당만 보고 '총주주환원(Total Shareholder Yield)'과 '주식 희석'을 놓침
- **현재 코드 진단**: `get_financial_stats.py`는 `dividendYield`만 수집합니다.
- **경제학적 비판**:
  - **밀러-모디글리아니(Modigliani-Miller) 배당 무관련 정리**와 현대 기업재무에서 주주환원의 핵심은 배당만이 아닙니다. 애플, 메타, 미국 은행들은 배당수익률은 0.5~2%에 불과하지만 매년 시가총액의 3~6%를 **자사주 매입 및 소각(Net Share Repurchase)**합니다.
  - 반대로 한국 코스닥 기업이나 미국 초기 SaaS 기업은 유상증자·전환사채(CB) 전환·주식보상비용(SBC)으로 매년 유통주식수를 3~10%씩 늘려 **기존 주주의 주당 가치를 희석(Dilution)**시킵니다.
- **고도화 지표**:
  - **총주주환원수익률(Total Shareholder Yield)**:
    $$\text{TSY} = \text{Dividend Yield} + \text{Net Buyback Yield} \left(-\frac{\Delta \text{Diluted Shares}}{\text{Shares}_{t-1}}\right)$$

---

### II. 거시경제학 및 국제금융학 (Macroeconomics & International Finance)

#### 사각지대 ③: 거시변수(금리·환율·유가)와 기업 손익 간 전이 메커니즘(Transmission Mechanism) 단절
- **현재 코드 진단**: [`market_metrics.py`](../../.agents/skills/market-analyst/scripts/market_metrics.py)는 `USD/KRW > 1,420원 = 🔴`, `10년물 금리 +15bps 급등 = 🔴`로 일괄 판정합니다.
- **경제학적 비판**:
  - 거시 충격은 모든 경제주체에 대칭적(Symmetric)으로 작용하지 않으며, **부문별 상대가격(Relative Prices)과 소득 재분배**를 일으킵니다.
  - **환율 경로(Exchange Rate Channel)**: 마샬-러너 조건(Marshall-Lerner Condition)과 J-커브 효과에 따라, 원화 약세(고환율)는 달러 결제 비중이 높은 **반도체·자동차·조선·방산·K-푸드 수출 기업**의 원화 환산 영업이익률을 즉각 개선시킵니다. 반면 LNG·원유·곡물을 달러로 수입해 원화로 파는 **전력(한국전력)·가스·항공·내수 식음료**에는 치명적 비용 인플레이션입니다.
- **고도화 지표**:
  - 163개 세부산업별 **거시 민감도 부호 매트릭스(Macro Sensitivity Vector)**: $[\beta_{\text{FX}}, \beta_{\text{Rate}}, \beta_{\text{Oil}}]$을 정의하여 거시 국면과 개별 종목의 궁합(Macro-Fit)을 판정.

#### 사각지대 ④: 명목금리(Nominal Yield)의 착시 — 피셔 방정식(실질금리 vs 기대인플레) 미분해
- **현재 코드 진단**: 명목 10년물 국채 금리(`^TNX`)만 추적합니다.
- **경제학적 비판**:
  - 어빙 피셔(Irving Fisher)의 방정식에 따르면 명목금리($i$)는 **실질금리($r$, Real Yield)**와 **기대인플레이션($\pi^e$, Breakeven Inflation)**의 합입니다:
    $$i = r + \pi^e$$
  - 똑같이 명목 10년물 금리가 20bps 상승하더라도:
    1. **기대인플레이션($\pi^e$) 주도 상승 (리플레이션)**: 경기 회복 기대감으로 시클리컬·소재·산업재·금융주가 강세를 보입니다.
    2. **실질금리($r$, TIPS 금리) 주도 상승 (긴축 충격)**: 중앙은행의 유동성 흡수 및 실질 할인율 급등으로, 성장주(Tech/SaaS)·금(Gold)·리츠가 동반 급락합니다.

#### 사각지대 ⑤: 금융시장 가격 편향 — 실물 경기 선행지표(Real Economy Proxies) 부재
- **현재 코드 진단**: Phase 1의 5대 기둥이 모두 주식·채권·옵션(VIX) 가격입니다.
- **경제학적 비판**:
  - 실물 경기 순환(Kitchin 재고 사이클 3~4년, Juglar 설비투자 사이클 7~10년)을 읽으려면 실물 산업 수요를 반영하는 상대가격 지표가 필요합니다.
  - **구리/금 비율(Copper-to-Gold Ratio = `HG=F` / `GC=F`)**: '닥터 코퍼(Dr. Copper)'로 불리는 산업용 구리 가격을 안전자산인 금 가격으로 나눈 비율은 글로벌 제조업 PMI와 10년물 적정 금리의 가장 강력한 실물 선행지표입니다.
  - **수익률 곡선 스티프닝(Bull/Bear Steepening after Inversion)**: 현재 코드는 `10Y - 3M < 0`인 '역전(Inverted)' 상태만 체크하지만, 역사적으로 실제 경기침체와 증시 폭락은 역전된 금리차가 **다시 플러스로 풀리는 순간(Un-inversion / Bull Steepening)**에 발생했습니다.

---

### III. 미시경제학 및 산업조직론 (Microeconomics & Industrial Organization)

#### 사각지대 ⑥: 가치사슬(Value Chain)의 정성적 나열 — 교섭력(Bargaining Power)과 이익 풀(Profit Pool) 미정량화
- **현재 코드 진단**: Phase 2(`value-chain-analyzer`)는 Upstream → Midstream → Downstream을 화살표로 연결하고 `[타겟]`, `[직접경쟁]`, `[병목협력]` 태그를 붙입니다.
- **경제학적 비판**:
  - 마이클 포터(Michael Porter)의 산업구조 분석(5 Forces)과 스탠퍼드 경영대학원의 **스마일 커브(Smile Curve) / 이익 풀(Profit Pool) 이론**에 따르면, 공급망에서 '누가 누구에게 납품하는가'보다 **'전체 산업 부가가치 중 누가 가장 높은 마진과 현금흐름을 독식하는가'**가 핵심입니다.
  - **운전자본을 통한 갑을 관계(Bargaining Power via CCC)의 증명**:
    진정한 병목 독점 기업(예: 애플, TSMC, 코스트코)은 고객에게는 돈을 먼저 받고(낮은 매출채권 회전일수 DSO, 선수금 수취), 납품업체에게는 대금을 늦게 지급하여(높은 매입채무 회전일수 DPO) **현금전환주기($\text{CCC} = \text{DIO} + \text{DSO} - \text{DPO}$)가 음수(-)이거나 극도로 짧습니다**. 반면 교섭력이 약한 하청 부품사는 재고(DIO)와 외상매출금(DSO)을 떠안아 매출이 늘수록 현금이 고갈됩니다.

#### 사각지대 ⑦: 가격결정력(Pricing Power)과 영업레버리지 도(Degree of Operating Leverage, DOL)
- **현재 코드 진단**: 단일 연도 매출성장률(`rg`)과 영업이익률(`OPM`)만 표시합니다.
- **경제학적 비판**:
  - 미시경제학의 **러너 지수(Lerner Index)**:
    $$L = \frac{P - MC}{P} \approx \text{Gross Profit Margin (GPM)}$$
    기업의 독점력(시장지배력)은 한계비용($MC$) 대비 가격($P$)을 얼마나 높게 책정할 수 있는지, 즉 **매출총이익률(GPM)의 절대 수준과 원가 상승기 GPM 방어력($\Delta\text{GPM}$)**으로 측정됩니다.
  - **고정비 vs 변동비 구조와 영업레버리지 도(DOL)**:
    $$\text{DOL} = \frac{\%\Delta \text{Operating Income (EBIT)}}{\%\Delta \text{Revenue}} = \frac{\text{Contribution Margin}}{\text{EBIT}}$$
    고정비 비중이 높은 산업(반도체 파운드리, 항공, 호텔, SaaS)은 손익분기점(BEP)을 넘는 순간 매출이 10%만 늘어도 영업이익이 50% 폭증하지만, 반대로 불황기 매출이 10% 줄면 영업이익이 적자로 추락합니다.

---

### IV. 회계학 및 기업재무 (Accounting Quality & Corporate Finance)

#### 사각지대 ⑧: 발생주의 회계의 함정 — 이익의 질(Accruals Quality) 및 현금전환율 감사 부재
- **현재 코드 진단**: Table 6(`[회계 감사] 일회성 손익 감지`)은 영업외 일회성 항목(`Total Unusual Items`)만 걸러냅니다.
- **경제학적 비판**:
  - 리처드 슬로언(Richard Sloan, 1996)의 유명한 **발생액 이상현상(Accrual Anomaly)** 연구에 따르면, 당기순이익이나 영업이익이 높더라도 영업현금흐름(OCF)이 뒷받침되지 않는 이익(즉, 밀어내기 매출로 매출채권이 급증하거나 안 팔리는 재고자산이 쌓여서 만들어진 회계상 이익)은 향후 주가 급락으로 이어집니다.
- **고도화 지표**:
  - **이익 현금전환율(Cash Conversion Ratio)**: $\frac{\text{Operating Cash Flow (OCF)}}{\text{Net Income}}$ (1.0 이상이면 우량, 0.7 미만이면 이익의 질 경고)
  - **슬로언 발생액 비율(Sloan Accrual Ratio)**: $\frac{\text{Net Income} - \text{OCF}}{\text{Total Assets}}$ (10% 초과 시 분식·밀어내기 매출 경보 🔴)

---

### V. 계량경제학 및 포트폴리오 이론 (Econometrics & Portfolio Theory)

#### 사각지대 ⑨: 종목 간 상관관계(Correlation)를 무시한 포트폴리오 배분
- **현재 코드 진단**: 사용자가 `--weights "0.2,0.5,0.3"`을 수동 입력하거나 임의 배분합니다.
- **경제학적 비판**:
  - 해리 마코위츠(Harry Markowitz)의 **현대 포트폴리오 이론(MPT)**에서 포트폴리오의 위험(분산 $\sigma_p^2$)은 개별 종목의 분산뿐만 아니라 **종목 간 공분산(Covariance / Correlation $\rho_{ij}$)**에 의해 결정됩니다:
    $$\sigma_p^2 = \sum_i w_i^2 \sigma_i^2 + \sum_i \sum_{j \neq i} w_i w_j \sigma_i \sigma_j \rho_{ij}$$
  - 같은 밸류체인 내 4개 종목(예: 삼성전자, SK하이닉스, 마이크론, TSMC)은 상관계수($\rho$)가 0.7~0.85에 달해 분산투자 효과가 낮습니다. 반면 개별 종목의 변동성($\sigma_i$)은 마이크론이 삼성전자의 2배일 수 있으므로, 동일 비중으로 담으면 고변동성 종목 하나가 포트폴리오 전체 손익을 지배합니다.
- **고도화 지표**:
  - **역변동성 가중(Inverse-Volatility / Risk Parity Weighting)** 권장 비중 자동 계산 및 **종목 간 60일 수익률 상관계수 행렬** 표시.

#### 사각지대 ⑩: 시나리오 스트레스 테스트(Table 7)의 '실적-멀티플 독립성 오류'
- **현재 코드 진단**: Table 7은 Bear/Base/Bull EPS에 `Multiple A(현재 PER 고정)`와 `Multiple B(목표가 내재 PER 고정)`를 곱합니다.
- **경제학적 비판**:
  - 금융시장에서 **이익(EPS)과 밸류에이션 멀티플(P/E)은 독립 변수가 아니라 강한 양(+)의 상관관계($\text{Cov}(\Delta\text{EPS}, \Delta\text{Multiple}) > 0$)**를 갖습니다(단, 시클리컬 정점 제외).
  - 즉, 비관적 시나리오(Bear Case)에서 기업 실적이 컨센서스 하단(Low EPS)으로 추락할 때 시장은 절대 현재의 높은 PER(Multiple A)를 그대로 주지 않으며, **실적 하향(Earnings Miss)과 멀티플 수축(Multiple Contraction / De-rating)이 동시에 발생하는 '더블 타격(Double Whammy)'**이 일어납니다.
- **고도화 지표**:
  - Bear 시나리오에서는 `Low EPS × 과거 밴드 하단 멀티플(De-rated Multiple)`을 결합한 **결합 스트레스 테스트(Joint EPS-Multiple Stress Test)**로 진정한 최대 낙폭(Max Downside Risk)을 산출해야 합니다.

---

### VI. 시장미시구조론 및 행동경제학 (Market Microstructure & Behavioral Finance)

#### 사각지대 ⑪: 수급 데이터의 규모 정규화(Normalization) 및 공매도/대차잔고 부재
- **현재 코드 진단**: Table 1-1에서 외국인·기관의 최근 5일 순매매 금액(억 원)만 표시합니다.
- **경제학적 비판**:
  - 시장미시구조론(Kyle 1985 모형 등)에서 가격 충격(Price Impact)은 절대 금액이 아니라 **유동성(일평균 거래대금 ADV 및 유통주식 시가총액 Free-Float Market Cap) 대비 주문 불균형(Order Imbalance)**에 비례합니다.
  - 삼성전자에서 외국인 500억 원 순매수는 일평균 거래대금의 3%에 불과한 노이즈이지만, 중형 소부장 기업에서 500억 원 순매수는 유통물량의 5%를 흡수하는 강력한 정보 거래(Informed Trading)입니다.

---

### VII. 제도경제학 및 지정학 (Institutional & Geopolitical Economics)

#### 사각지대 ⑫: 거버넌스(코리아 디스카운트) 및 산업정책·지정학 노출도
- **현재 코드 진단**: 한국 상장사(`.KS`/`.KQ`)와 미국 상장사에 동일한 밸류에이션 멀티플 기준을 적용합니다.
- **경제학적 비판**:
  - 더글러스 노스(Douglass North)의 **신제도경제학**과 라 포르타(La Porta et al., LLSV)의 **법과 금융(Law and Finance)** 이론에 따르면, 소액주주 보호 법제와 이사회 독립성이 취약한 시장에서는 지배주주의 사적 편익 추출 위험(Tunneling Risk) 때문에 **자기자본비용($k_e$)에 거버넌스 위험 프리미엄이 가산**됩니다.
  - 따라서 한국 기업 분석 시에는 ① **모자회사 중복상장(Double Counting) 여부**, ② **자사주 보유분 중 소각 약정 비율**, ③ **배당성향 및 밸류업 공시 이행 여부**, ④ **미·중 공급망 디커플링(관세·IRA·반도체 수출통제) 노출도**가 반드시 밸류에이션 할인/할증 요인으로 정량 체크되어야 합니다.

---

## 요약: 차세대 시스템을 위한 로드맵 매트릭스

| 단계 | 적용 레이어 | 핵심 추가 지표 (Proposed Metrics) | 데이터 수집 가능 여부 (`yfinance` / `Naver` 무료 API) |
| :---: | :--- | :--- | :--- |
| **Tier 1** | **Phase 3 (기업 재무·밸류)** | • **ERP 스프레드** ($E/P - R_f$)<br>• **ROIC vs WACC** 스프레드<br>• **총주주환원율 (TSY)** = 배당 + 자사주 소각/희석<br>• **이익 현금전환율** ($\text{OCF}/\text{NI}$) & **$\Delta\text{GPM}$ (가격결정력)**<br>• **결합 스트레스 테스트** (Bear EPS × De-rated Multiple) | **100% 즉시 가능** (기존 수집된 재무제표·현금흐름표·주식수 이력 및 `^TNX` 금리 결합으로 추가 API 호출 없이 계산 가능) |
| **Tier 2** | **Phase 1 & 2 (거시·가치사슬)** | • **구리/금 비율** (`HG=F` / `GC=F`) 실물 선행지표<br>• **장단기 금리차 역전 해소(Un-inversion)** 경보<br>• **거시-미시 민감도 매트릭스** (환율·금리·유가 수혜/피해 자동 판별)<br>• **가치사슬 4개사 이익 풀(GPM/OPM/CCC) 교섭력 비교표** | **100% 즉시 가능** (`HG=F` 선물 1개 추가 및 4개사 운전자본 회전일수 계산) |
| **Tier 3** | **Phase 3 & Section 7 (포트폴리오)** | • **4개 종목 간 수익률 상관계수 행렬 (Correlation Matrix)**<br>• **역변동성(Risk-Parity) 기반 권장 포트폴리오 비중**<br>• **일평균 거래대금(ADV) 대비 수급 강도 정규화** | **100% 즉시 가능** (기존 수집된 일별 주가·거래량 시계열로 즉시 계산 가능) |
