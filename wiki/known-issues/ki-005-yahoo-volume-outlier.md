# KI-005 Yahoo 거래량 이상치

> Sources: check_data_sources.py 실행 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

2026-06-10 Yahoo 거래량이 삼성전자 1,191주, SK하이닉스 151주로 기록돼 있었습니다. 같은 날 거래소(다음) 거래량은 삼성전자 26,153,569주, SK하이닉스 4,833,000주였고, Yahoo 직전 20일 중앙값은 각각 35,601,106주, 5,959,054주였습니다.

## 조치

- 직전 20일 중앙값의 1% 미만인 날을 이상치로 보고 경고 `[KI-005]`를 냅니다. 출처마다 거래량 기준이 달라 값을 바꾸지는 않습니다. 상태: 감지만 적용.

## See Also

- [Yahoo Finance](../data-sources/yahoo-finance.md)
