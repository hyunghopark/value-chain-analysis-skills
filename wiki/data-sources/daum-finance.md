# 다음 금융

> Sources: check_data_sources.py 실행 결과, 2026-10-14; 뉴스핌·싱글리스트·인포스탁데일리 마감 시황, 2026-10-13
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md); [언론 보도 종가 메모](../../raw/news/2026-10-13-krx-close-press-reports.md); [수급 데이터 가격 기준](../../raw/data-checks/2026-10-14-investor-feed-price-basis.md)
> Updated: 2026-10-14

## Overview

한국 종목의 거래소 종가 기준 출처입니다. 삼성전자 2026-10-12 종가 250,500은 언론 보도 종가와 같고, 2026-10-13 종가 232,000은 보도 등락률(7.39% 하락)과 맞습니다. Yahoo·네이버와 무관한 별도 출처라 교차 점검의 기준으로 씁니다.

## 스크립트가 쓰는 경로

- `finance.daum.net/api/quote/A{코드}/days`: 일별 OHLCV — Yahoo 종목 이력 보완·교정 (거래소 정규장 종가)
- `finance.daum.net/api/market_index/days`: 코스피·코스닥 지수 — Yahoo 지수 이력 보완
- 수급 API(`/api/investor/days`)의 가격은 일별 시세 종가가 아니라 네이버 수급 종가와 같습니다 → [KI-001](../known-issues/ki-001-naver-close-basis.md)
- `finance.daum.net/api/quotes/A{코드}`, `/api/investor/days`: 당일 장중 외국인 지분 변동 추정

## 알려진 특성

- 거래량은 Yahoo·네이버와 하루도 같지 않았습니다(0/243일, 0/244일). 거래소 단독 거래량으로 보이지만 확인하지 못했습니다.
- 공식 API가 아니며 Referer 헤더가 필요합니다.

## See Also

- [KI-001 네이버 종가 필드가 거래소 종가와 다름](../known-issues/ki-001-naver-close-basis.md)
- [Yahoo Finance](yahoo-finance.md)
