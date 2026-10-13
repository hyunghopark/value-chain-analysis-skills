# Yahoo Finance

> Sources: check_data_sources.py 실행 결과, 2026-10-14; yfinance 조회 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md); [Yahoo 스냅샷](../../raw/data-checks/2026-10-14-yahoo-info-snapshot.md)
> Updated: 2026-10-14

## Overview

시세 이력, 재무제표, 컨센서스(EPS 추정·수정 건수·목표가)의 기본 출처입니다. 미국 종목 가격은 Nasdaq.com과 1년간 완전히 일치했지만, 한국 종목은 가격 이력과 요약 지표에 결함이 있습니다. 재무제표 표가 요약 지표보다 늦는 문제는 두 시장 모두에서 생깁니다.

## 스크립트가 쓰는 항목

- 가격 이력 `history(auto_adjust=False)`: 기술적 지표, 시장 비교, P/B 밴드
- 연간·분기 손익계산서, 재무상태표: 사이클 위치, P/B 밴드, 일회성 손익 감사
- `earnings_estimate`·`eps_trend`·`eps_revisions`: 시나리오 표, 추정치 방향
- 한국 종목의 PER·EPS·PBR·BPS는 네이버 값으로 덮어씁니다(Yahoo 값이 비어 있음).

## 한국 종목 결함

- 요약 지표: 삼성전자·SK하이닉스 모두 trailingPE, trailingEps, priceToBook, bookValue가 None입니다.
- 최근 거래일 누락·빈값 → [KI-002](../known-issues/ki-002-yahoo-kr-latest-day-gap.md)
- 산발적 종가 오류 → [KI-006](../known-issues/ki-006-yahoo-kr-close-errors.md)
- 거래량 이상치 → [KI-005](../known-issues/ki-005-yahoo-volume-outlier.md)
- 주식수 이상치 → [KI-007](../known-issues/ki-007-yahoo-share-count.md)
- 거래량 기준: Yahoo와 네이버 거래량은 241/243일 같았고, 거래소(다음)와는 0/243일 같았습니다.

## 미국 종목

- 마이크론 가격·거래량은 Nasdaq.com과 일치했습니다(누락 0일, 종가 불일치 0일, 거래량 5% 초과 차이 0일).
- 재무제표 반영 지연 → [KI-003](../known-issues/ki-003-yahoo-statement-lag.md)
- ADR은 시세 통화와 재무 통화가 다를 수 있습니다 → [KI-008](../known-issues/ki-008-adr-currency.md)

## See Also

- [Nasdaq.com](nasdaq.md)
- [다음 금융](daum-finance.md)
