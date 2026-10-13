# 네이버 금융

> Sources: check_data_sources.py 실행 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

한국 종목의 PER·EPS·PBR·BPS·배당·52주 범위·시가총액(보통주)·컨센서스 목표가, 그리고 투자자별 순매매(수급)의 출처입니다. 공식 API가 아니라 화면용 데이터를 읽으므로 예고 없이 바뀔 수 있습니다.

## 스크립트가 쓰는 경로

- `m.stock.naver.com/api/stock/{코드}/integration`: 요약 지표와 컨센서스
- `m.stock.naver.com/api/stock/{코드}/trend`: 투자자별 순매수 수량(주)과 외국인 지분율
- `fchart.stock.naver.com/sise.nhn`: 정기 점검의 일별 시세 비교용

## 알려진 특성

- 종가 필드가 2026-09-14부터 거래소 종가와 다릅니다 → [KI-001](../known-issues/ki-001-naver-close-basis.md)
- 거래량은 Yahoo와 같은 기준으로 보이고(241/243일 일치), 거래소(다음)와는 0/244일 같았습니다.
- 장중에도 현재가를 실시간으로 갱신하므로, 당일 행은 장중 스냅샷일 수 있습니다.

## See Also

- [다음 금융](daum-finance.md)
- [WiseReport](wisereport.md)
