# KI-004 WiseReport 표 구조 변경 위험

> Sources: check_data_sources.py 실행 결과, 2026-10-14
> Raw: [교차 점검](../../raw/data-checks/2026-10-14-cross-source-check.md)
> Updated: 2026-10-14

## Overview

WiseReport 연간 실적 표(`cF1002`)의 EPS를 행의 칸 위치로 읽습니다. 사이트 구조가 바뀌면 오류 없이 다른 숫자를 EPS로 읽을 수 있습니다. 점검 시점에는 두 종목 모두 머리글이 예상과 같아 정상이었습니다.

## 조치

- 머리글 앞 6칸이 예상과 다르거나, 같은 행의 순이익과 EPS 부호가 다르면 값을 쓰지 않고 경고 `[KI-004]`를 냅니다. 상태: 예방 점검 적용.
- 정기 점검 도구가 같은 검사를 합니다.

## See Also

- [WiseReport](../data-sources/wisereport.md)
