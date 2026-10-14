# 검증 세트 002 — 보고서 숫자 자동 대조

`check_report_numbers.py`의 분류 정확도(spec 002 SC-001~SC-003, SC-005)를 확인하는 고정 자료입니다.

| 파일 | 출처 | 비고 |
|---|---|---|
| `report.md` | 분석 프로젝트 `reports/AI_메모리_반도체_20261014_Investment_Strategy_Report.md` (SHA-256 앞자리 `942992faef0e6f8e`) | 머리의 `**데이터 스냅샷**:` 줄만 `report_data.json`으로 바꿈. 나머지 글자는 원본 그대로 |
| `report_data.json` | 같은 보고서의 짝 스냅샷 (SHA-256 앞자리 `8c867c65e8a211d9`, 생성 2026-10-14 13:04 KST) | 001 보완(`215b8f1`) **이전** 버전: 수급 '최근 5일 누적'·외국인 지분율이 없고, `section4` 기준본도 없음 |
| `labels.json` | 점검 도구 초안 → 사람이 확정 | `"reviewed": true`가 되기 전에는 `test_validation_set`이 건너뛰어진다 |

- 이 자료는 테스트용이다. 기업별 판정·결론을 위키에 옮기지 않는다(헌법 VI). 새 분석의 입력으로 쓰지 않는다.
- 위 스냅샷 한계 때문에, Section 4에는 있으나 이 스냅샷에 없는 값("-3.93조 원" 5일 누적, "46.18%" 지분율, 시나리오 등락률, 백분위 등)은 라벨 `script_gap`으로 둔다. 도구가 `unsupported`로 내면 맞은 것으로 세고, 부담 비율(SC-002)에서는 뺀다(US2에서 스냅샷을 보완하므로).

## coverage/ — Section 4 → 스냅샷 대응 (FR-015, T024)

| 파일 | 출처 |
|---|---|
| `coverage/section4.md` | 002 T018~T022 반영 코드로 `get_financial_stats.py --tickers 005930.KS,000660.KS,MU,TSM --cyclical 005930.KS,000660.KS,MU --snapshot …`을 실행한 표준 출력 (2026-10-14 18:1x KST) |
| `coverage/section4_data.json` | 같은 실행의 스냅샷 |

`test_section4_fixture_fully_in_snapshot`이 네트워크 없이 "Section 4 숫자 중 스냅샷에 없는 것 0건"을 확인한다. 표 코드가 바뀌어 생기는 새 누락은 `network` 표시 테스트(`test_section4_live_fully_in_snapshot`)가 로컬에서 잡는다. 표 코드를 바꾸면 이 자료도 다시 만든다.
