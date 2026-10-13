# Nasdaq.com

> Sources: check_data_sources.py 실행 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

미국 종목 가격의 기준 출처입니다. 정기 점검에서만 쓰고, 보고서 생성 스크립트는 쓰지 않습니다. 2025-10-22 ~ 2026-10-12 비교에서 마이크론의 Yahoo 가격은 Nasdaq.com과 일치했습니다.

## 스크립트가 쓰는 경로

- `api.nasdaq.com/api/quote/{티커}/historical`: 일별 종가·거래량 (브라우저 User-Agent 필요)

## See Also

- [Yahoo Finance](yahoo-finance.md)
