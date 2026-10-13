# WiseReport

> Sources: check_data_sources.py 실행 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

한국 종목의 올해·내년 컨센서스 EPS 출처입니다(네이버 증권 기업분석 화면의 데이터). 12개월 선행 EPS·PER 계산에 씁니다. 점검 시점에 삼성전자·SK하이닉스 표 구조는 정상이었습니다.

## 스크립트가 쓰는 경로

- `navercomp.wisereport.co.kr/v2/company/cF1002.aspx`: 연간 실적·추정 표. 행의 EPS를 칸 위치로 읽습니다.

## 알려진 특성

- 머리글 '매출액(억원, %)'은 값과 증감률 두 칸을 차지해, 머리글 순서와 행의 칸 순서가 맞지 않습니다.
- 구조 변경 위험과 예방 점검 → [KI-004](../known-issues/ki-004-wisereport-layout.md)
- Yahoo 컨센서스와 내년 EPS가 몇 % 차이 날 수 있어, 출처 간 5% 규칙으로 경고합니다.

## See Also

- [네이버 금융](naver-finance.md)
