# 섹터 로테이션 및 시장 브레드스 규칙 (Sector Rotation & Breadth)

이 문서는 `market-analyst` 스킬에서 미국 S&P 500 11개 섹터(SPDR Sector ETF)의 상대강도(Relative Strength)와 순환매(Sector Rotation)를 진단하는 원본 규칙입니다.

---

## 1. 11개 SPDR 섹터 ETF 분류

| 구분 | ETF 티커 | 섹터 한글명 | 경기 민감도 및 특성 |
|---|---|---|---|
| **경기 민감·성장형 (Cyclical / Growth)** | `XLK` | 기술 (Technology) | 시장 주도력 1위, 고성장·금리 민감 |
| | `XLC` | 통신서비스 (Communication Services) | 빅테크(구글·메타 등) 집중 |
| | `XLY` | 경기소비재 (Consumer Discretionary) | 소비 심리 및 경기 확장 민감 |
| | `XLI` | 산업재 (Industrials) | 설비투자, 인프라, 제조업 사이클 |
| | `XLF` | 금융 (Financials) | 금리 및 장단기 금리차, 신용 사이클 |
| | `XLB` | 소재 (Materials) | 원자재 및 글로벌 제조업 수요 |
| **경기 방어형 (Defensive)** | `XLP` | 필수소비재 (Consumer Staples) | 불황 방어, 배당 안정성 |
| | `XLU` | 유틸리티 (Utilities) | 채권 대체 성격, 금리 하락 수혜 |
| | `XLV` | 헬스케어 (Health Care) | 비탄력적 수요, 방어적 가치주 |
| **인플레·특수형 (Commodity / Real Estate)** | `XLE` | 에너지 (Energy) | 유가 및 인플레이션 헤지 |
| | `XLRE` | 부동산 (Real Estate) | 상업용 부동산, 장기금리 민감 |

- **벤치마크 ETF**: `SPY` (S&P 500 지수 추종 ETF)

---

## 2. 상대강도 (RS) 및 순환매 스프레드 산출 공식

### 2-1. SPY 대비 상대강도 (Relative Strength vs SPY)
기간 $t$(1일, 5일, 1개월, 3개월)에 대해:
$$\text{RS}_t(\text{Sector}) = \text{Return}_t(\text{Sector}) - \text{Return}_t(\text{SPY})$$
- $\text{RS} > 0$: 시장 초과수익 (Outperforming / Market Leading)
- $\text{RS} < 0$: 시장 하회 (Underperforming / Lagging)

### 2-2. 경기민감 vs 경기방어 로테이션 스프레드 (Rotation Spread)
$$\text{Spread}_t = \text{Mean}(\text{RS}_t(\text{Cyclicals})) - \text{Mean}(\text{RS}_t(\text{Defensives}))$$
여기서:
- $\text{Cyclicals} = \{\text{XLK}, \text{XLC}, \text{XLY}, \text{XLI}, \text{XLF}, \text{XLB}\}$
- $\text{Defensives} = \{\text{XLP}, \text{XLU}, \text{XLV}\}$

---

## 3. 로테이션 국면 해석 기준

| 스프레드 범위 (5일/1개월) | 로테이션 국면 | 자금 흐름 해석 및 위험도 |
|---|---|---|
| **> +2.0%** | **공격적 위험 선호 (Risk-On Aggressive)** | 유동성이 기술주 및 성장주로 유입. 강세장 주도 지속. |
| **0.0% ~ +2.0%** | **온건한 순환매 (Mild Risk-On)** | 경기민감주 중심의 건전한 상승 국면. |
| **-2.0% ~ 0.0%** | **중립 및 숨고르기 (Neutral Rotation)** | 섹터별 차별화 장세, 뚜렷한 쏠림 없음. |
| **< -2.0%** | **안전자산 도피 (Flight to Safety / Risk-Off)** | 경기방어주(유틸리티·필수소비재)로 자금 급격한 피신. 시장 경보 신호. |
