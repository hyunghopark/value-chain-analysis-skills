# KI-003 Yahoo 재무제표 반영 지연

> Sources: yfinance 조회 결과, 2026-10-14; check_data_sources.py 실행 결과, 2026-10-14
> Raw: [Yahoo 스냅샷](../../raw/data-checks/2026-10-14-yahoo-info-snapshot.md); [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

Yahoo의 요약 지표(info)는 새 분기를 반영했는데 손익계산서 표는 이전 분기에 머무는 경우가 있습니다. 마이크론은 lastFiscalYearEnd·mostRecentQuarter가 2026-09-03인데, 연간 표는 2025-08-31, 분기 표는 2026-05-31까지만 있었습니다. 삼성전자·SK하이닉스는 연간 2025-12-31, 분기 2026-06-30으로 요약 지표와 같았습니다.

## 영향

- 사이클 위치 판정은 연간 표의 영업이익률 범위를 씁니다. 회계연도가 막 끝난 기업은 최근 12개월이 곧 방금 끝난 회계연도인데, 그 연도가 표에 들어오면 과거 최고치가 바뀌어 실적 변화 없이도 판정이 바뀔 수 있습니다.
- 일회성 손익 감사와 P/B 밴드도 이전 분기 기준이 됩니다.

## 조치

- 표의 최신 열이 요약 지표의 기간보다 7일 넘게 늦으면 경고 `[KI-003]`을 냅니다. 값은 고치지 않습니다. 상태: 감지만 적용.

## See Also

- [Yahoo Finance](../data-sources/yahoo-finance.md)
