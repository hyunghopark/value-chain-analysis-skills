# 데이터 품질 규칙 (원본)

코드: `scripts/data_checks.py`, `scripts/get_financial_stats.py`, 정기 점검 `scripts/check_data_sources.py`
사건 기록: 스킬 저장소 `wiki/known-issues/` (경고의 `[KI-xxx]` 번호와 같은 번호)

## 항목별 출처 및 다중 MCP 폴백 우선순위 체크리스트 (1순위 → 2순위 → 3순위)

스킬이 수집·검증하는 모든 정량 지표와 정성 공시 항목은 **현재 구성된 스크립트 수집원(`Yahoo`, `네이버`, `WiseReport`, `다음`, `PyKrx`)**과 **`finance-api-hub`의 6대 공식 MCP 서버(`krx`, `dart`, `ecos`, `toss`, `fred`, `edgar` + `meritz`)**를 결합하여 아래의 **우선순위(1순위 → 2순위 → 3순위 → 교차검증)** 체계로 운영합니다.

### 1) 한국 종목 (`.KS` / `.KQ`) 데이터 항목별 출처 우선순위

| 분류 | 데이터 항목 / 기능 | 🥇 1순위 (Primary) | 🥈 2순위 (Secondary / 시간대 보완) | 🥉 3순위 (Fallback / 레거시) | 🔍 4순위 / 교차검증 (Audit) | 비고 및 시간대 규칙 (`DATA_TIMING.md`) |
|---|---|---|---|---|---|---|
| **시세·가격** | **현재가 (장중 / NXT 시간외)** | **네이버 금융** (`naver_integration`) / **Toss MCP** (`toss_stock_candles`) | **Meritz API** (`market_price`) / **다음 금융** (`daum_quote`) | **Yahoo Finance** (`info.currentPrice`) | **KRX MCP** (`krx_stock`, 전일 종가 대조) | 09:00~20:00 장중·NXT 시간대 실시간 체결 반영 (`KI-009`) |
| **시세·가격** | **KRX 정규장 확정 종가 & 일별 가격 이력** | **KRX MCP** (`krx_stock`: `kospi`/`kosdaq`, 2010년~) | **Meritz API** (`market_candles_days`, 당일 15:30 직후) / **다음 금융** (`daum_days`, 최근 100일) | **Toss MCP** (`toss_stock_candles`) | **Yahoo Finance** (`history`, `KI-002`·`KI-006` 보정 대상) | KRX Open API는 익일 08:10 갱신 → 당일 15:30~익일 08:00는 Meritz/다음으로 보완 |
| **시세·가격** | **52주 최고가 · 최저가** | **네이버 금융** (`naver_integration`) | **KRX MCP** (`krx_stock` 252일 시계열) / **Toss MCP** (`toss_stock_candles`) | **Yahoo Finance** (`fiftyTwoWeekHigh/Low`) | **다음 금융** (`daum_days`) | KRX 정규장 기준 일관성 유지 |
| **시세·가격** | **한국 휴장일 · 영업일 캘린더** | **Toss MCP** (`toss_kr_market_calendar`) | **KRX MCP** (`krx_index` 거래일 유무) | **다음 금융** (`daum_index_days` 최신 거래일) | **Yahoo Finance** (`^KS11` 시계열) | 평일 공휴일 `nxt_after_market` 오작동 원천 방지 |
| **주식수·시총** | **시가총액 (보통주 기준)** | **네이버 금융** (`naver_integration` 보통주 시총) / **KRX MCP** (`krx_stock.MKTCAP`) | **DART MCP** (`dart_report: stockTotqySttus` × 현재가) | **Yahoo Finance** (`info.marketCap`) | 출처 간 5% 규칙 (`cross_check`) | 당일 장중/마감 직후는 네이버·Toss, 확정 일별 시총은 KRX |
| **주식수·시총** | **발행주식수 · 유통주식수 · 자기주식수** | **DART MCP** (`dart_report: stockTotqySttus` 보통주/우선주/자사주 분리) | **KRX MCP** (`krx_stock`: `kospi_info`/`LIST_SHRS`) | **네이버 금융** (`naver_integration`) | **Yahoo Finance** (`balance_sheet` 주식수 — `KI-007` 이상치 점검 대상) | 삼성전자 등 보통주·우선주 합산 왜곡(`KI-007`) 원천 차단 |
| **밸류에이션** | **PER (TTM / 확정 실적 기준)** | **네이버 금융** (`naver_integration.per`) | **KRX MCP** (`pykrx_fundamental` / KRX 일별 PER) | **DART MCP** (`dart_financials` 지배주주순이익 ÷ 시총 자체계산) | **Yahoo Finance** (`trailingPE`) | Yahoo 한국 종목 `trailingPE` 결측/오차 방어 |
| **밸류에이션** | **12M Forward PER & 선행 EPS (FY0·FY1·NTM)** | **WiseReport** (`wisereport_eps` 컨센서스 표) | **네이버 금융** (`naver_integration.cnsPer` / `cnsEps`) | **Yahoo Finance** (`forwardPE`, `earnings_estimate`) | 출처 간 5% 규칙 (`WiseReport` vs `네이버` vs `Yahoo`) | `KI-004` 헤더 검증 통과 시 WiseReport 최우선 |
| **밸류에이션** | **PBR · BPS (현재 & 과거 P/B 밴드)** | **네이버 금융** (`pbr`, `bps`) + **DART MCP** (`dart_financials` 자본총계 ÷ `stockTotqySttus` 주식수) | **KRX MCP** (`pykrx_fundamental` PBR/BPS) | **Yahoo Finance** (`priceToBook`, `balance_sheet` — `KI-007` 필터 적용) | **Toss MCP** (재무비율 피어 비교) | 10년 장기 P/B 밴드는 DART 2015년~ 재무제표로 확장 (`spec 004`) |
| **밸류에이션** | **EV/EBITDA · PEG** | **스크립트 자체 계산** (DART/Yahoo 영업현금·상각비·차입금 + 시총 + 선행 성장률) | **Yahoo Finance** (`enterpriseToEbitda`, `pegRatio`) | **DART MCP** (`dart_indicators` 수익성/안정성 지표 결합) | — | EV 산출 시 우선주·순차입금 기준 통일 |
| **주주환원** | **배당수익률 · 주당배당금(DPS) · 배당성향** | **DART MCP** (`dart_report: alotMatter` 배당에 관한 사항 공식 공시) | **네이버 금융** (`dividendYield`, `dividend`) | **KRX MCP** (`pykrx_fundamental` 배당수익률) | **Yahoo Finance** (`dividendYield`) | 공식 사업/분반기보고서 현금배당성향 및 DPS 확보 |
| **주주환원** | **자사주 매입 · 소각 · 처분 (TSY 희석률)** | **DART MCP** (`dart_report: tesstkAcqsDspsSttus` 자기주식 취득 및 처분 현황) | **DART MCP** (`dart_disclosures` 자기주식 취득/소각 결정 주요사항보고서) | **Yahoo Finance** (`Ordinary Shares Number` 연도별 증감) | **DART MCP** (`cbIssuAcmslt` CB / `piicDecsn` 유상증자) | v4.0 총주주환원율(`TSY`) 및 코리아 디스카운트 거버넌스 감사 핵심 |
| **재무제표** | **연간·분기 손익계산서 / 재무상태표 / 현금흐름표** | **DART MCP** (`dart_financials`: 2015년~ **10년+ K-IFRS 전체 계정**) | **Yahoo Finance** (`income_stmt`, `balance_sheet`, `cashflow` 최근 4년/5분기) | **네이버 금융** / **WiseReport** 요약 재무표 | **DART MCP** (`dart_indicators` 다중기업 XBRL 주요지표, 2023 Q3~) | `KI-003` 반영 지연 해결 및 `결정 0003` 시클리컬 10년 사이클 위치 구현 |
| **재무제표** | **잠정실적 (매출·영업이익 공정공시)** | **DART MCP** (`dart_disclosures(pblntf_ty="I")` + `dart_document` 원문 표) | **네이버 금융** / **WiseReport** 잠정실적 반영분 | **실시간 웹 검색** (`search_web` 언론사 보도) | — | 실적 시즌(1·4·7·10월) 확정 보고서 제출 전 필수 조회 |
| **재무제표** | **운전자본 교섭력 ($\text{CCC} = \text{DIO}+\text{DSO}-\text{DPO}$)** | **DART MCP** (`dart_financials`: 매출채권·재고자산·매입채무·매출원가) | **Yahoo Finance** (`balance_sheet` + `income_stmt`) | **DART MCP** (`dart_indicators` 활동성 지표) | — | v4.0 가치사슬 4개사 교섭력(갑을 관계) 정량화 |
| **수급·미시** | **투자자별 순매매 (외국인·기관·개인)** | **Toss MCP** (`toss_market_investor_trading`: **실제 거래대금(억 원)** + **7대 기관 세분화** + `updatedAt`) | **Toss MCP** (`toss_stock_investor_trading`) + **네이버 금융** (`naver_trend` 수량×종가 추정) | **다음 금융** (`daum_quote` 장중 외인 지분변동 추정, `daum_investor_days`) | **KRX MCP** (`krx_stock` 거래대금 대조) | `KI-001`·`KI-009` 보강: 연기금·금융투자·사모펀드 주체 분리 확인 |
| **수급·미시** | **공매도 추이 · 프로그램 매매** | **Toss MCP** (`toss_stock_short_selling` 공매도 거래량·비중 / `toss_stock_program_trades` 차익·비차익) | **KRX 정보데이터 / 금융위 공공데이터** (공매도 잔고 비중) | **네이버 금융** 공매도/프로그램 탭 | — | v4.0 시장미시구조 사각지대(공매도·프로그램 차익 매물) 해소 |
| **컨센서스** | **목표주가 · 투자의견 · 30일 EPS 리비전 · 서프라이즈** | **WiseReport** (`wisereport_eps` EPS 리비전) + **네이버 금융** (국내 증권사 목표가 평균) | **Yahoo Finance** (`targetMeanPrice`, `eps_trend`, `eps_revisions`, `earnings_history`) | **DART MCP** (`dart_disclosures` 기업설명회 IR 자료) | 출처 간 5% 규칙 (`네이버 목표가` vs `Yahoo 목표가`) | 한국 종목은 네이버 목표가 열과 Yahoo 목표가 열을 나란히 병기 |
| **자본비용** | **무위험금리($R_f$) · 타인자본비용($k_d$) (WACC/EVA/ERP용)** | **ECOS MCP** (`ecos_market_rates`: **국고채 10년 `ktb10y`**, **회사채 AA- `corpAA` / BBB- `corpBBB`**) | **Toss MCP** (`toss_market_indicator_prices` 국채 금리) | **재무제표 실효이자율** (`이자비용 ÷ 총차입금`) | **Yahoo Finance** (`^TNX` — 미국 금리이므로 한국 기업 직접 적용 지양) | `economic_auditor.py`의 고정 `rf_rate=4.86` 하드코딩을 한국 공식 금리로 대체 |

---

### 2) 미국 및 글로벌 종목 (`NVDA`, `MU`, `TSM`, `ASML` 등) 데이터 항목별 출처 우선순위

| 분류 | 데이터 항목 / 기능 | 🥇 1순위 (Primary) | 🥈 2순위 (Secondary / 백업) | 🥉 3순위 (Fallback) | 🔍 4순위 / 교차검증 (Audit) | 비고 및 활용 규칙 |
|---|---|---|---|---|---|---|
| **시세·주식수** | **현재가 · 일별 가격 이력 · 52주 고저** | **Yahoo Finance** (`info`, `history` 5년 시계열) | **Toss MCP** (`toss_stock_candles` 해외주식코드 변환 시) | **Nasdaq.com API** (`check_data_sources.py` 검증 경로) | — | ADR 종목(`TSM`, `ASML`)은 주가 통화(`USD`)와 재무 통화(`TWD`, `EUR`) 분리 확인 (`KI-008`) |
| **시세·주식수** | **보통주 발행주식수 · 희석주식수 (TSY 희석률)** | **SEC EDGAR MCP** (`sec_concept`: `dei:EntityCommonStockSharesOutstanding`, `us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding`) | **SEC EDGAR MCP** (`sec_financials` 내 `CommonStockSharesOutstanding`) | **Yahoo Finance** (`balance_sheet` `Ordinary Shares Number`) | — | 미국 빅테크·SaaS 기업의 자사주 매입/소각 및 SBC 주식보상 희석률 정밀 산출 |
| **재무제표** | **연간(10-K) · 분기(10-Q) 3대 재무제표 및 파생 Q4** | **SEC EDGAR MCP** (`sec_financials`: **10년+ XBRL**, **파생 4분기(Q4) 자동 산출**, 정정공시 자동 중복제거, 공시 후 **1분 내 반영**) | **Yahoo Finance** (`income_stmt`, `quarterly_income_stmt`, `balance_sheet`, `cashflow` 최근 4년) | **SEC EDGAR MCP** (`sec_concept` 개별 XBRL 태그 직접 조회) | **SEC EDGAR MCP** (`sec_frames` 동종업계 전체 횡단면 비교) | `KI-003` 재무제표 반영 지연 원천 해결 및 10년+ 장기 사이클 위치(`결정 0003`) 산출 |
| **재무제표** | **MD&A · 어닝 릴리즈(8-K) · 공급망/수주 원문** | **SEC EDGAR MCP** (`sec_filings` + `sec_document(section="item7" \| "item1a" \| "item2.02")`) | **SEC EDGAR MCP** (`sec_search` 전체 공시 키워드 전문 검색, 예: `"HBM3E"`, `"CoWoS"`) | **실시간 웹 검색** (`search_web`) | — | Section 1.3 체크리스트, Section 3 병목 해자, Section 5 리스크 요인에 SEC 원문 직결 |
| **밸류·컨센서스** | **Forward P/E · EPS 추정치(FY0/FY1/NTM) · 리비전 · 서프라이즈 · 목표가** | **Yahoo Finance** (`info`, `earnings_estimate`, `eps_trend`, `eps_revisions`, `earnings_history`) | *(확장 권장)* **Finnhub / FMP MCP** (`/stock/eps-estimate`, `/analyst-estimates`, `/price-target`) | **SEC EDGAR MCP** (`8-K` Item 2.02 회사 공식 가이던스) | — | 과거 실적(TTM)은 SEC EDGAR로 교차검증하고, 선행 추정치는 Yahoo(+향후 Finnhub/FMP) 사용 |
| **자본비용** | **무위험금리($R_f$) · 회사채 스프레드($k_d$) (WACC/EVA/ERP용)** | **FRED MCP** (`fred_bundle("rates")`: **미국채 10년 `DGS10`**, **10Y TIPS 실질금리 `DFII10`**) + **FRED MCP** (`fred_bundle("credit")`: **BBB OAS `BAMLC0A4CBBB`**) | **Yahoo Finance** (`^TNX`) | **재무제표 실효이자율** (`Interest Expense ÷ Total Debt`) | — | `economic_auditor.py`에 실시간 `DGS10` 및 `BBB OAS` 주입 |

---

### 3) 거시 경제 · 시장 국면 진단 (`market-analyst`) 항목별 출처 우선순위

| 거시 기둥 | 데이터 항목 / 기능 | 🥇 1순위 (Primary) | 🥈 2순위 (Secondary) | 🥉 3순위 (Fallback / 기존 대용치) | 개선 효과 |
|---|---|---|---|---|---|
| **1. 지수·추세** | **한국 지수(`^KS11`, `^KQ11`) 및 시장 등락비율(Breadth)** | **KRX MCP** (`krx_index` 공식 종가 + `krx_stock("market_summary")` 상승/하락 종목수 ADR) | **Toss MCP** (`toss_market_indicator_prices`) / **다음 금융** (`daum_index_days`) | **Yahoo Finance** (`^KS11`, `^KQ11` — `KI-006` 보정 대상) | 지수 왜곡을 잡아내는 시장 전체 상승/하락 종목수(Breadth) 확보 |
| **1. 지수·추세** | **미국·글로벌 지수(`^GSPC`, `^NDX`, `^SOX`) & 11개 SPDR 섹터** | **Yahoo Finance** (`market_collect.py` 지수 및 11개 섹터 ETF 시계열) | **Toss MCP** (`toss_market_indicator_prices` 주요 글로벌 지수) | **FRED MCP** (`SP500`, `NASDAQCOM`, `NASDAQ100`) | 실시간 50/200 SMA 및 Tier 1·2·3 위기 지지선 판정 |
| **2. 변동성** | **VIX (`^VIX`) 및 변동성 기간구조** | **Yahoo Finance** (`^VIX` 장중/종가) | **FRED MCP** (`VIXCLS` CBOE 공식 일별 종가) | **Toss MCP** (`toss_market_indicator_prices` VIX) | 장중에는 Yahoo, 일별 확정 시계열은 FRED 교차검증 |
| **3. 금리·인플레** | **미국 국채 금리 · 장단기 금리차(`10Y-2Y`, `10Y-3M`) · 실질금리(TIPS) · 기대인플레(BEI)** | **FRED MCP** (`fred_bundle("rates")`: `DGS10`, `DGS2`, `DGS3MO`, `T10Y2Y`, `T10Y3M`, `DFII10`, `T10YIE`, `SOFR`) | **Toss MCP** (`toss_market_indicator_prices` 채권) | **Yahoo Finance** (`^TNX`, `^IRX` — `^IRX`는 할인율 기준이라 **약 20bp 오차** 존재) | `^IRX` 20bp 오차 제거 및 **피셔 방정식($i = r + \pi^e$: 실질금리 vs 기대인플레)** 분해 완성 |
| **3. 금리·인플레** | **한국 기준금리 · 국고채(3Y/10Y) · 통안채 · 코리보** | **ECOS MCP** (`ecos_market_rates`: `baseRate`, `callRate`, `cd91d`, `cp91d`, `ktb3y`, `ktb10y`) | **ECOS MCP** (`ecos_data` 통계표 `817Y002`) | — | 한국형 금리 사이클 및 한·미 금리 역전폭 실시간 계산 |
| **4. 신용 리스크** | **미국 하이일드(HY) · 투자등급(IG/BBB) 신용 스프레드 & 대출태도** | **FRED MCP** (`fred_bundle("credit")`: `BAMLH0A0HYM2` HY OAS, `BAMLC0A0CM` IG OAS, `BAMLC0A4CBBB` BBB OAS, `DRTSCILM` 대출태도) | **Yahoo Finance** (`HYG / LQD` ETF 상대강도 비율) | — | ETF 듀레이션 착시가 섞인 `HYG/LQD` 대용치를 **실제 ICE BofA OAS 스프레드(bp)** 로 격상 |
| **4. 신용 리스크** | **한국 회사채 신용 스프레드 (`AA-`, `BBB-`) 및 CP 스프레드** | **ECOS MCP** (`ecos_market_rates`: `corpAA - ktb3y`, `corpBBB - ktb3y`, `cp91d - cd91d`) | **KRX MCP** (`krx_bond` 국채/특수채 전문유통수익률) | — | 국내 부동산 PF·단기자금시장 경색 및 한계기업 신용위험 직접 감지 |
| **5. 유동성·환율** | **연준 순유동성 ($\text{Net Liquidity} = \text{WALCL} - \text{TGA} - \text{RRP}$)** | **FRED MCP** (`fred_bundle("liquidity")`: `WALCL`, `WTREGEN`, `RRPONTSYD`, `WRESBAL`, `M2SL` 및 `derived.netLiquidity`) | **FRED MCP** (`fred_series` 개별 시계열) | — | v4.1 글로벌 유동성 증감과 나스닥/반도체 밸류에이션 멀티플 동조화 진단 |
| **5. 유동성·환율** | **원/달러 환율(`USD/KRW`) · 달러 인덱스(`DXY`) · 증시주변자금(고객예탁금·신용융자)** | **ECOS MCP** (`ecos_market_rates.usdkrw` 공식 매매기준율 + `ecos_data("901Y056")` 예탁금/신용잔고) + **Toss MCP** (`toss_market_indicator_prices` 실시간 환율) | **FRED MCP** (`DTWEXBGS` 무역가중 달러지수, `DEXKOUS`) | **Yahoo Finance** (`USDKRW=X`, `DX-Y.NYB`) | 장중 실시간 환율은 Toss/Yahoo, 일별 공식 환율 및 예탁금/신용 레버리지 비율은 ECOS |
| **6. 실물·일정** | **원자재(WTI 유가, 금, 구리/금 비율) & 주요 경제지표 발표 일정** | **Toss MCP** (`toss_market_indicator_prices` 원자재) + **Yahoo Finance** (`CL=F`, `GC=F`, `HG=F`) + **FRED MCP** (`fred_release_calendar`, `fred_bundle("macro"\|"labor")`) | **FRED MCP** (`DCOILWTICO` WTI 현물) | **실시간 웹 검색** (`search_web`) | 구리/금 비율(`HG=F / GC=F`) 실물 선행지표 및 향후 CPI·고용·GDP 발표 캘린더 자동 연동 |

## 점검 규칙

<a id="cross-source-5"></a>
### 출처 간 5% 규칙 (`cross_check`)

한국 종목의 올해·내년 EPS(WiseReport vs Yahoo, WiseReport vs 네이버), 평균 목표가(네이버 vs Yahoo), 시가총액(네이버 보통주 vs Yahoo)이 5% 넘게 다르면 경고합니다.

### 가격 이력 (KI-002, KI-006)

- 한국 종목은 다음 금융 일별 시세를 거래소 종가 기준으로 봅니다.
- 다음 금융 최근 100거래일 안에서 Yahoo에 없거나 빈 날은 채우고, 종가가 다른 날은 거래소 종가로 바꿉니다. 채운 날의 거래량은 다음 금융 값입니다(기준이 다를 수 있음).
- 코스피(`^KS11`)·코스닥(`^KQ11`) 지수 이력도 다음 금융 지수 종가(`/api/market_index/days`)로 같은 방식으로 보완합니다. 지수는 한국 종목 등락 계산의 거래일 달력이기도 합니다.

### 수급 금액 (KI-001)

- 네이버 순매수 수량 × **같은 수급 데이터의 종가**로 계산합니다. 다음 금융 수급 API도 같은 가격을 주므로 이 가격이 수량과 같은 기준입니다.
- 거래소 정규장 종가와 다르면 경고만 냅니다. 수량은 수급 데이터, 가격은 정규장으로 섞지 않습니다.
- '수량 × 하루 한 가격'은 근사치입니다(하루 가격 범위가 종가 기준 차이보다 큼). 금액은 항상 '추정'입니다.
- 주가 등락·기술적 지표는 거래소 종가(가격 이력 규칙)를 씁니다. 가격 용도마다 기준을 구분합니다.

### KRX 마감 후 NXT 시간외 거래 시간대 (KI-009)

한국 종목은 KRX 정규장이 15:30에 끝난 뒤에도 넥스트레이드(NXT)에서 20:00까지 거래됩니다. 그 사이에 실행하면 시세와 수급이 서로 다른 시장을 가리킬 수 있어, 기준을 글로 밝힙니다. 시각은 모두 원자료의 받은 시각입니다(`data-snapshot.md` §9-4).

- **시세·등락·기술적 지표**: 계속 KRX 정규장 종가(Yahoo, 다음 일별 시세)입니다. NXT 체결가로 바꾸지 않습니다.
- **데이터 기준 줄**: 한국 종목 시세를 받은 시각(`info.fetched_at`)이 평일 15:30~20:00이고 Yahoo 최종 체결(`regularMarketTime`)이 같은 날이면(KRX 휴장일 제외) `KRX 장 마감(최종 체결 …, NXT 시간외 거래는 20:00까지)`로 적고, 이 시간대에는 수급 당일 행이 잠정치라는 문장을 덧붙입니다.
- **수급 표 당일 행 — 네이버 행이 아직 없어 다음 금융 시세로 추정할 때**: 다음 시세의 `marketStatus`로 표시를 정합니다.

  | `marketStatus` | 표시 | 가격 |
  |---|---|---|
  | `AFTER_MARKET` (KRX 마감 후, NXT 거래 중) | `NXT 시간외 잠정` | NXT 체결가(`tradePrice`, 체결 시각 `tradeTime`) |
  | `CLOSING` (NXT까지 마감) | `마감 후 잠정` | NXT 최종 체결가 |
  | 그 밖의 값·없음 | `장중 잠정` | 현재가 |

  `AFTER_MARKET`·`CLOSING`이면 KRX 정규장 종가(`regularTradePrice`)를 표 위 안내와 경고 `[KI-009]`에 함께 적고, 스냅샷에 `flows.<날짜>.krx_close`(`krx_regular_close`, `ki: KI-009`)로 남깁니다. 다음 금융의 외국인 보유 주식 수는 KRX 마감 후 바뀌지 않으므로, 이 시간대에 금액이 바뀌는 것은 가격 때문입니다.
- **수급 표 당일 행 — 네이버 행이 있을 때**: 받은 시각(`naver_trend.fetched_at`)이 15:40 전이면 '장 마감(15:30) 전 실행', 15:40~20:10이면 'KRX 마감 후 NXT 시간외 거래(20:00 마감) 중 실행'으로 잠정이며 경고에 `[KI-009]`를 붙입니다. 20:10(NXT 마감 + 10분) 이후에 받은 행은 '마감 후 집계'(확정)입니다. 네이버 행의 종가·거래량은 NXT 체결을 포함한 값이라 KRX 정규장만 담은 Yahoo 시세와 다른 것이 정상이므로, 20:10 이후에는 이 차이로 잠정 처리하지 않고 수급 표의 기준 차이 경고 `[KI-001]`로만 알립니다. 20:10 전에는 그 차이를 잠정 사유에 함께 적습니다.

### 거래량 이상치 (KI-005)

- Yahoo 거래량이 직전 20일 중앙값(최소 10일)의 1% 미만이면 경고합니다. 값은 바꾸지 않습니다.

### 재무제표 반영 지연 (KI-003)

- 연간 표 최신 열이 `lastFiscalYearEnd`보다, 분기 표 최신 열이 `mostRecentQuarter`보다 7일 넘게 이르면 경고합니다.

### WiseReport 구조 (KI-004)

- 머리글 앞 6칸이 `재무년월, 매출액(억원, %), 영업이익(억원, %), 당기순이익(억원, %), EPS(원), PER(배)`가 아니거나, 행의 순이익(4번째 칸)과 EPS(5번째 칸) 부호가 다르면 WiseReport 값을 쓰지 않습니다.

## 새 데이터 문제를 발견했을 때

1. `check_data_sources.py`(또는 직접 대조)로 근거를 만들고 `raw/data-checks/`에 저장합니다.
2. 위키에 사건 문서 `wiki/known-issues/ki-NNN-*.md`를 만들고(ingest), `data_checks.KNOWN_ISSUES`에 번호를 추가합니다.
3. 감지·우회 코드를 넣고, 경고 앞에 `ki('KI-NNN', ...)`를 붙입니다.
4. `tests/test_data_checks.py`에 그 사례를 재현하는 테스트를 추가합니다.
5. 이 문서의 해당 규칙을 고칩니다.
