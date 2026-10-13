# Knowledge Base Index

## data-sources

데이터 출처별 백과. 스크립트가 무엇을 어디서 가져오는지와 알려진 특성.

| Article | Summary | Updated |
|---------|---------|---------|
| [Yahoo Finance](data-sources/yahoo-finance.md) | 시세·재무·컨센서스 기본 출처, 한국 종목 결함과 재무제표 지연 | 2026-10-14 |
| [네이버 금융](data-sources/naver-finance.md) | 한국 종목 요약 지표·수급, 2026-09-14부터 종가 기준 차이 | 2026-10-14 |
| [다음 금융](data-sources/daum-finance.md) | 한국 종목 거래소 종가 기준 출처 | 2026-10-14 |
| [WiseReport](data-sources/wisereport.md) | 한국 종목 컨센서스 EPS, 칸 위치로 읽는 구조 | 2026-10-14 |
| [Nasdaq.com](data-sources/nasdaq.md) | 미국 종목 가격 기준(정기 점검용) | 2026-10-14 |

## known-issues

데이터 출처 사건 기록. 스크립트 경고의 [KI-xxx] 번호와 연결됩니다.

| Article | Summary | Updated |
|---------|---------|---------|
| [KI-001 네이버 종가 필드가 거래소 종가와 다름](known-issues/ki-001-naver-close-basis.md) | 2026-09-14부터 수급 데이터 가격 ≠ 거래소 정규장 종가(기준 차이), 금액은 수급 데이터 가격 유지 | 2026-10-14 |
| [KI-002 Yahoo 한국 종목 최근 거래일 누락·빈값](known-issues/ki-002-yahoo-kr-latest-day-gap.md) | 최근 거래일 누락·빈 종가를 거래소 종가로 보완 | 2026-10-14 |
| [KI-003 Yahoo 재무제표 반영 지연](known-issues/ki-003-yahoo-statement-lag.md) | 재무제표 표가 요약 지표보다 늦음, 사이클 위치 판정이 바뀔 수 있음 | 2026-10-14 |
| [KI-004 WiseReport 표 구조 변경 위험](known-issues/ki-004-wisereport-layout.md) | 칸 위치로 EPS를 읽어 구조 변경 시 조용한 오류, 예방 점검 | 2026-10-14 |
| [KI-005 Yahoo 거래량 이상치](known-issues/ki-005-yahoo-volume-outlier.md) | 2026-06-10 거래량 깨짐, 감지만 | 2026-10-14 |
| [KI-006 Yahoo 한국 종목 산발적 종가 오류](known-issues/ki-006-yahoo-kr-close-errors.md) | 1년 중 수일 종가 오류, 최근 100거래일만 교정 | 2026-10-14 |
| [KI-007 Yahoo 재무상태표 주식수 이상치](known-issues/ki-007-yahoo-share-count.md) | 삼성전자 2025년 주식수 급증, 중앙값으로 보정 | 2026-10-14 |
| [KI-008 ADR 통화 불일치](known-issues/ki-008-adr-currency.md) | TSM 시세 USD·재무 TWD, 배수 역산 보정 | 2026-10-14 |
