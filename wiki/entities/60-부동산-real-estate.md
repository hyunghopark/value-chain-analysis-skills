---
title: "GICS 60: 부동산 (Real Estate) — 17개 세부산업 평가 체계"
created: 2026-11-09
updated: 2026-11-09
tags: [gics, sector-60, real-estate, reits, ffo, affo, nav, cap-rate, valuation]
sources: [msci-gics-2024, wall-street-equity-research]
---

# GICS 60: 부동산 (Real Estate) — 17개 세부산업 평가 체계

> **관련 문서**: [Index](../index.md) | [5대 비즈니스 프로파일](../concepts/5대-비즈니스-프로파일-평가체계.md) | [GICS 163개 마스터 매트릭스](../concepts/gics-163개-세부산업-지표-매트릭스.md)

## 1. 섹터 개요 및 비즈니스 프로파일 매핑

**부동산(Real Estate, GICS 60)** 섹터는 2016년 금융(GICS 40) 섹터에서 독립 신설된 섹터(모기지 리츠 `402040`만 금융 잔류)로, 지분형 리츠(Equity REITs)와 부동산 관리 및 개발업으로 구성됩니다:

- **지분형 리츠 (Equity REITs, GICS 601010 ~ 601080)**: **Type 4 (금융 / 리츠 및 인프라 고배당, `FINANCIAL_REIT`)** 프로파일이 절대적으로 적용됩니다. 부동산 자산은 실제로는 가치가 상승하거나 유지되더라도 회계상 거액의 감가상각비(Depreciation)가 비용 처리되어 당기순이익(Net Income)이 구조적으로 과소계상됩니다. 따라서 전통적 P/E는 완전히 무의미하며, 반드시 **FFO(Funds From Operations)** 및 **AFFO(Adjusted FFO)**, **P/NAV**, **배당수익률**로 평가해야 합니다.
- **부동산 관리 및 개발 (Real Estate Management & Development, GICS 602010)**: 디벨로퍼는 **Type 2 (`CYCLICAL`)**, 자산관리·중개 서비스는 **Type 1 (`GENERAL`)** 특성을 결합하여 평가합니다.

---

## 2. 산업군 및 17개 세부산업(Sub-Industry) 전체 트리

- **6010 지분형 리츠 (Equity Real Estate Investment Trusts - Equity REITs)**
  - **601010 다각화된 리츠**: `60101010` 다각화된 리츠
  - **601025 산업용 리츠**: `60102510` 산업용 리츠
  - **601030 호텔 및 리조트 리츠**: `60103010` 호텔 및 리조트 리츠
  - **601040 오피스 리츠**: `60104010` 오피스 리츠
  - **601050 헬스케어 리츠**: `60105010` 헬스케어 리츠
  - **601060 주거용 리츠**: `60106010` 다세대 주거용 리츠, `60106020` 단독주택 주거용 리츠
  - **601070 리테일 리츠**: `60107010` 리테일 리츠
  - **601080 특수 리츠 (Specialized REITs)**: `60108010` 데이터센터 리츠, `60108020` 인프라(통신타워) 리츠, `60108030` 셀프 스토리지 리츠, `60108040` 산림(Timber) 리츠, `60108050` 기타 특수 리츠
- **6020 부동산 관리 및 개발 (Real Estate Management & Development)**
  - **602010 부동산 관리 및 개발**: `60201010` 다각화된 부동산 활동, `60201020` 부동산 운영 기업, `60201030` 부동산 개발, `60201040` 부동산 서비스

---

## 3. 17개 세부산업별 핵심 성과 지표(KPI) 및 밸류에이션 매트릭스

| GICS 코드 | 세부산업명 (국/영문) | 적용 프로파일 | 1순위 핵심 운영 KPI (Primary Operational KPIs) | 핵심 밸류에이션 배수 (Primary Multiples) | 제외/후순위 지표 및 주의사항 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `60101010` | **다각화된 리츠**<br>(Diversified REITs) | Type 4 (`FINANCIAL_REIT`) | 포트폴리오 가중평균 임대율(Occupancy Rate), 잔여 가중평균 임대기간(WALE), 동일자산 순영업이익(Same-Store NOI) 성장률, AFFO 배당성향 | **P/FFO**, **P/AFFO**, **P/NAV**, 배당수익률 | 복합 자산 보유로 인해 순수 섹터 리츠 대비 NAV 할인(Conglomerate Discount) 발생 경향 |
| `60102510` | **산업용 리츠 (물류센터)**<br>(Industrial REITs) | Type 4 (`FINANCIAL_REIT`) | 임대차 재계약 시 임대료 상승률(Cash Leasing Spreads), 공실률(Vacancy Rate), Same-Store NOI 성장률, 물류 거점 Cap Rate | P/FFO, P/AFFO, P/NAV, Implied Cap Rate | 이커머스 물류센터 과잉 공급 지역의 임대료 상승 둔화 여부 점검 |
| `60103010` | **호텔 및 리조트 리츠**<br>(Hotel & Resort REITs) | Type 4 (`FINANCIAL_REIT`) | **RevPAR (객실당 매출 = ADR × 객실가동률)**, 호텔 EBITDA 마진, Net Debt / EBITDA, AFFO 배당 커버리지 | P/FFO, EV/EBITDA, P/NAV | 임대계약이 사실상 '1일 단위'이므로 리츠 중 경기 민감도가 가장 높음 |
| `60104010` | **오피스 리츠**<br>(Office REITs) | Type 4 (`FINANCIAL_REIT`) | 실질 점유율(Physical vs Leased Occupancy), 임차인 인센티브(TI/무상임대) 차감 후 **유효 임대료(Effective Rent)**, 만기 차입금 차환 금리 | P/AFFO (TI·유지보수 CapEx 차감 필수), P/NAV | 재택근무 정착 및 노후(B/C급) 오피스 공실 급증으로 인한 자산 가치 상각 및 CapEx 급증 주의 (`FFO`보다 `AFFO` 필수) |
| `60105010` | **헬스케어 리츠**<br>(Health Care REITs) | Type 4 (`FINANCIAL_REIT`) | 시니어 하우징(SHOP) 가동률 및 NOI 성장률, 병원/요양시설 임차인의 임대료 커버리지 비율(EBITDAR Coverage), WALE | P/FFO, P/AFFO, 배당수익률 | 고령화 수혜가 뚜렷하나 임차 의료기관의 인건비 상승에 따른 임대료 체납 리스크 확인 |
| `60106010` | **다세대 주거용 리츠 (아파트)**<br>(Multi-Family Residential REITs) | Type 4 (`FINANCIAL_REIT`) | 신규/갱신 임대료 증감률(Blended Lease Rate Growth), 입주율(Occupancy ≥ 95%), Same-Store NOI 성장률, 지역별 신규 아파트 입주 물량 | P/FFO, P/AFFO, Implied Cap Rate | 모기지 금리 고공행진 시 내집마련 지연으로 임대 수요가 견조해지는 반사익 존재 |
| `60106020` | **단독주택 주거용 리츠**<br>(Single-Family Residential REITs) | Type 4 (`FINANCIAL_REIT`) | 평균 거주기간(Turnover Rate 감소), 유지보수 비용 통제율, Same-Store NOI 성장률, P/NAV | P/FFO, P/AFFO, P/NAV | 다세대 대비 평균 거주기간이 길고 해지율이 낮아 현금흐름 안정성 우수 |
| `60107010` | **리테일 리츠**<br>(Retail REITs) | Type 4 (`FINANCIAL_REIT`) | 임차인 평당 매출액, 점유율(Occupancy), 트리플넷(Triple-Net, NNN: 세금·보험·수선비 임차인 부담) 계약 비중, Leasing Spread | P/FFO, P/AFFO, 배당수익률 | 필수소비재 앵커(식료품점·약국) 기반의 NNN 리츠는 채권 수준의 현금흐름 안정성 보유 |
| `60108010` | **데이터센터 리츠**<br>(Data Center REITs) | Type 4 (`FINANCIAL_REIT`) | **전력 기반 수주 용량(MW Bookings)**, kW당 월 임대단가, 상호연결(Interconnection) 매출 비중, 개발 파이프라인 수익률(Development Yield) | **P/AFFO**, EV/EBITDA, P/FFO | AI 추론·학습용 고밀도 전력(Liquid Cooling) 확보 여부가 핵심 해자; 전통 리츠 대비 성장주 프리미엄 부여 |
| `60108020` | **인프라 리츠 (통신타워)**<br>(Infrastructure REITs) | Type 4 (`FINANCIAL_REIT`) | 타워당 임차 통신사 수(**Tenancy Ratio**), 연간 임대료 자동인상률(Escalator 3%+), Churn Rate, 토지 임차료 통제율 | P/AFFO, EV/EBITDA, 배당수익률 | 하나의 타워에 통신사 안테나를 추가할 때 한계비용이 거의 0에 수렴하여 높은 ROIC 창출 |
| `60108030` | **셀프 스토리지 리츠**<br>(Self-Storage REITs) | Type 4 (`FINANCIAL_REIT`) | 평당 임대료(Street Rate vs ECRI 기존고객 임대료 인상), 가동률, Same-Store NOI 마진(70%+) | P/FFO, P/AFFO, P/NAV | 유지보수 CapEx가 극히 적고 가격 전가력이 뛰어난 고마진 리츠 |
| `60108040` | **산림 리츠**<br>(Timber REITs) | Type 4 (`FINANCIAL_REIT`) | 목재 가격(Lumber Price), 에이커당 벌채량, 탄소배출권(Carbon Credit)/자연기반해법(NCS) 매출, 가용배당현금(FAD) | P/FAD, EV/EBITDA, P/NAV (에이커당 산림 가치) | 미국 주택 착공 및 리모델링 수요에 직접 연동되는 경기민감형 리츠 |
| `60108050` | **기타 특수 리츠**<br>(Other Specialized REITs) | Type 4 (`FINANCIAL_REIT`) | 카지노/체험형/옥외광고판 등 특수 자산의 **Triple-Net(NNN) 임대료 회수율**, WALE(15~30년 초장기), 연간 물가연동 에스컬레이터 | P/AFFO, 배당수익률, P/NAV | 단일 대형 임차인(Tenant Concentration) 부도 리스크 점검 필수 |
| `60201010` | **다각화된 부동산 활동**<br>(Diversified Real Estate Activities) | Type 4 / Type 2 | 임대 수익(Recurring Income) 대 개발 분양 수익 비중, 순자산가치(NAV) 대비 할인율, Net Debt / Equity | **P/NAV**, P/B, EV/EBITDA | 홍콩·일본 종합 부동산 회사의 전형적 모델로, NAV 할인율 축소 및 주주환원이 핵심 |
| `60201020` | **부동산 운영 기업**<br>(Real Estate Operating Companies) | Type 4 (`FINANCIAL_REIT`) | 리츠 비전환 법인의 FFO/NOI 성장률, 포트폴리오 Cap Rate, LTV(담보인정비율) | P/FFO, P/NAV, EV/EBITDA | 리츠 배당 의무(90%+)가 없어 현금 재투자가 자유로우나 법인세 부담 존재 |
| `60201030` | **부동산 개발 (디벨로퍼)**<br>(Real Estate Development) | Type 2 (`CYCLICAL`) | 분양 계약률(Pre-sale Rate), 개발 마진, 준공 후 미분양 재고, PF 우발채무 및 순차입금비율 | P/B, P/NAV, P/E | 금리 인상기 브릿지론/본PF 차환 실패 시 유동성 위기 직결 |
| `60201040` | **부동산 서비스**<br>(Real Estate Services) | Type 1 (`GENERAL`) | 자산관리(PM/FM) 수수료 등 **반복 매출(Recurring Revenue) 비중**, 상업용 부동산 매매/임대 중개 수수료 성장률, EBITDA 마진 | P/E, EV/EBITDA, EV/FCF | 직접 부동산을 보유하지 않는 경량 자산(Asset-light) 수수료 비즈니스이므로 Type 1 적용 |

---

## 4. 실전 투자 분석 체크리스트 (Red Flags)

1. **전통 P/E 적용 금지 원칙 (`601010` ~ `601080`)**: 리츠는 건물 감가상각비가 회계상 비용으로 차감되어 GAAP 당기순이익(EPS)이 극도로 낮게 나오며, 이로 인해 전통적 P/E는 40~100배 이상으로 왜곡됩니다. 반드시 감가상각비를 다시 더해주고 자산매각손익을 제거한 **P/FFO**와, 실질 유지보수 CapEx까지 차감한 **P/AFFO**를 사용하십시오.
2. **FFO와 AFFO의 괴리 (오피스 리츠의 함정, `60104010`)**: 임차인을 유치하기 위해 제공하는 무상임대(Free Rent)와 인테리어 지원금(Tenant Improvements, TI), 중개수수료(Leasing Commissions)가 급증하면 명목 FFO는 유지되더라도 실제 배당 재원인 **AFFO**는 급감합니다.
3. **Cap Rate 스프레드와 차환(Refinancing) 리스크**: 보유 부동산의 자본환원율(Cap Rate = NOI / 자산가치)보다 신규 만기 연장 차입금의 조달 금리가 높아지면 역레버리지(Negative Leverage)가 발생하여 주당 배당금(DPS) 삭감이 불가피해집니다.
