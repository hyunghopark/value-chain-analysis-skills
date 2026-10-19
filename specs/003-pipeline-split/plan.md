# Implementation Plan: 수집·정제·계산·출력 분리

**Branch**: `claude/003-pipeline-split` | **Date**: 2026-10-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-pipeline-split/spec.md`

**Status**: Draft

## Summary

외부 접속과 현재 시각 읽기를 새 수집 모듈(`collect.py`)로 모두 옮기고, 수집한 **원자료**(Yahoo `info`·시세·재무제표·컨센서스 표, 네이버·WiseReport·다음 응답)를 받은 시각과 함께 스냅샷 형식 2의 `inputs`에 저장한다. 정제·계산·출력은 스냅샷에서 읽은 원자료만으로 Section 4를 만든다. 보고서를 생성할 때도 원자료를 JSON으로 왕복시킨 뒤 같은 길로 만든다. 새 도구 `rebuild_section4.py`는 스냅샷 하나로 네트워크 없이 Section 4를 다시 만들고, 기준본·계산값·경고와 비교한다(종료 코드 0/1/2). 같은 도구로 시나리오 확률과 순환업종 지정만 바꿔 별도 파일로 재계산할 수 있다.

측정 근거([research.md](research.md)):
- 원자료 크기는 4개 종목 기준 0.86~1.66MB다(R2).
- 실제 표 28개가 JSON 왕복 후 모두 같았다(R3).
- 표 생성 중 외부 접속 2곳과 시각 읽기 5곳을 확인했다(R1).

## Technical Context

**Language/Version**: Python 3.12 (uv 관리, CI 3.12; 로컬 3.13에서도 동작)

**Primary Dependencies**: 기존 그대로(yfinance, pandas, requests, beautifulsoup4). 새 의존성은 없다.

**Storage**: 스냅샷 JSON 형식 2(`meta.format_version: 2`, 최상위 `inputs` 추가). 형식 1의 키는 형식·뜻을 유지한다. 형식은 [data-model.md](data-model.md)에 정리했다.

**Testing**: pytest. 실제 수집한 새 형식 시험 스냅샷을 `tests/fixtures/003/`에 둔다. 외부 접속·시각 차단은 실행 테스트와 코드 검사 테스트로 확인한다. 분리 전 코드와의 비교는 재생 도구(`tests/tools/replay_main.py`, 로컬 수동 실행)로 한다. CI는 GitHub Actions다.

**Target Platform**: Windows(로컬), macOS(로컬), Ubuntu(CI)

**Project Type**: CLI 스크립트 (Claude Code / Antigravity 스킬)

**Performance Goals**:
- 재현: 4개 종목 10초 이내, 네트워크 없음(SC-006).
- 수집: 지금 수준. 측정에서 원자료 수집은 9.6초였다.

**Constraints**:
- 사용자 명령과 출력 파일은 바뀌지 않는다(FR-009).
- 재현 도구는 지정한 스냅샷 하나만 읽고 고치지 않는다(FR-010).
- 스냅샷 크기는 4개 종목 기준 10MB 이하다(SC-007).
- CI 테스트는 네트워크 없이 돈다(헌법 기술 제약).

**Scale/Scope**: 종목 4~6개, 지수 2~3개, 원자료 항목은 종목당 약 15개. 스냅샷 `values`는 약 3,000개, Section 4는 약 400줄이다.

조사 결과와 결정 근거는 [research.md](research.md)에 있다. 미해결 항목은 없다.

## Constitution Check

*GATE: Phase 0 전 확인, Phase 1 설계 후 다시 확인.*

| 원칙 | 점검 | 설계 전 | 설계 후 |
|---|---|---|---|
| I. 객관성 우선 | 판정 로직·기준값을 바꾸지 않는다. 분리 전후 Section 4가 같은지 재생 비교로 확인한다(R12). 옵션 재계산은 원본을 바꾸지 않고 '보고서가 아님'을 표시한다. 결론에 맞추려고 확률을 바꾸는 용도가 되지 않게 한다. | ✅ | ✅ |
| II. 출처 추적 | 원자료를 출처·받은 시각과 함께 보존하므로, 교정 전 값과 Section 4의 모든 숫자를 원자료까지 추적할 수 있다. 수급 금액(수급 데이터 가격)과 주가(정규장 종가)의 기준 구분은 그대로다. | ✅ | ✅ |
| III. 조용한 오류 금지 | 원자료 누락은 경로를 밝힌 오류(종료 코드 2)로 낸다. 계산값이 다르면 보고한다. 수집 실패는 `status: error`로 남겨 같은 경고를 다시 낸다. 조사 중 찾은 `repo_commit` 조용한 실패(R15)를 고친다. | ✅ | ✅ |
| IV. 규칙 단일 원본 | 스냅샷 형식 2와 원자료 목록은 `references/rules/data-snapshot.md`에 둔다. 판정 기준값은 바꾸지 않으므로 기준값 결정 기록은 없다. 구조 결정은 `docs/decisions/0006`에 남긴다. | ✅ | ✅ |
| V. 검증 가능한 변경 | 재생 비교(같은 입력 → 0줄 차이)와 같은 시각 실제 실행 비교를 한다. 재현·차단·변조 테스트는 CI에서 돈다. | ✅ | ✅ |
| VI. Clean-Slate | 재현·재계산은 지정한 스냅샷 하나만 읽는다. 새 보고서 생성은 과거 스냅샷을 입력으로 쓰지 않는다. 시험 스냅샷은 테스트 자료이고 위키에 넣지 않는다. | ✅ | ✅ |

위반은 없다. 아래 Complexity Tracking은 설계상 복잡도를 기록하는 용도다.

## 현재 구조와 바뀌는 점

```
지금
get_financial_stats.py
  ├─ get_stats(sym): yf.Ticker → info/history/재무제표/컨센서스 (+네이버·WiseReport·다음 접속)  ← 수집·정제·계산 섞임
  │     └─ 덮어쓰기·KI 교정·사이클·P/B 밴드·감사 계산, SNAP.record, warn
  ├─ 표 함수들: 계산 + 글자 (+ 수급 표·시장 비교 표는 이 안에서 다시 접속, now() 읽음)
  └─ SNAP.dump(values, series, warnings)

바뀐 뒤
collect.py (네트워크·시각은 여기만)
  └─ collect_all(args) → inputs{sym: {item: {source, fetched_at, status, kind, data}}}, meta
get_financial_stats.py (CLI 그대로)
  ├─ main: collect_all → raw_inputs.dumps/loads 왕복 → build_section4(inputs, options) → SNAP.dump(+inputs)
  └─ build_section4: refine_ticker(정제) → 표 함수(계산·출력) — 원자료와 fetched_at만 읽음
raw_inputs.py: 표 형식 변환(R3), 원자료 접근(누락이면 MissingInput)
rebuild_section4.py: 스냅샷 → build_section4 → Section 4·values·warnings 비교 / 옵션 재계산
```

## 설계

### 1. 수집 모듈 `collect.py` (R1, R4, R13)

| 함수 (예) | 하는 일 |
|---|---|
| `collect_ticker(sym)` | `info`(실패 시 `_quote._info`와 사유 `note`), `history`(5년), 재무제표 4종, 컨센서스 표 4종 |
| `collect_kr(sym, info_item)` | 네이버 `integration`, WiseReport 표(머리·셀), 다음 일별 시세, pykrx(환경 변수 있을 때) |
| `collect_flows(sym)` | 네이버 `trend`를 받는다. 받은 시각 기준으로 당일 행이 없는 평일이면 다음 `quotes`와 `investor/days`도 받고, 아니면 두 항목을 `skipped`로 남긴다 |
| `collect_indices(symbols, infos, benchmarks)` | `default_benchmarks`·`market_index_for`와 같은 함수로 지수 목록을 정하고, 1년 시세와 다음 지수 시세를 받는다 |
| `collect_all(args)` | 위를 종목 순서대로 부르고 `meta`(`collected_at`, 버전, `repo_commit`)를 만든다 |

- 수집 함수는 예외를 경고로 바꾸지 않고 `status: "error"`와 `error`로 남긴다. 경고는 정제 단계가 같은 문장으로 낸다(R6).
- 다음 금융 요청 함수 3개(`fetch_daum_days`, `fetch_daum_index_days`, `fetch_naver_fchart`)는 `data_checks.py`에서 옮긴다. `fetch_nasdaq_history`도 쓰는 곳에 따라 옮긴다. `check_data_sources.py`는 바뀐 import 위치를 쓴다.

### 2. 원자료 형식 `raw_inputs.py` (R3, R10)

- `encode_frame` / `decode_frame`: 인덱스·열의 종류, 시간대 이름, 날짜 정밀도, 자료형, 이름을 보존한다.
- `RawInputs(snapshot_dict)`: `get(sym, item)`은 항목을 돌려준다. 항목이 없으면 `MissingInput("inputs.<sym>.<item>")`, 형식이 틀리면 `InvalidInput`을 낸다. `frame(sym, item)`은 `ok`일 때 DataFrame, `empty`·`error`·`skipped`일 때 `None`과 항목을 함께 돌려준다.
- `dumps` / `loads`: 생성과 재현이 같은 함수를 쓴다(R7). 형식 버전을 검사해 이전 형식이면 `LegacyFormat`을 낸다.

### 3. 정제·계산·출력 (`get_financial_stats.py`)

- `get_stats(sym)` → `refine_ticker(sym, raw)`: `t.xxx`와 `requests.get` 대신 원자료를 읽는다. 처리 순서와 경고 위치는 지금과 같다(R6). 시각이 필요한 곳은 원자료의 `fetched_at`을 인자로 받는다.
  - `compute_ntm_eps(today=)`, `fetch_wisereport_ntm_eps` → `parse_wisereport_eps(table, today)`
  - `earnings_dates(info, now)`
  - 수급 표의 `now_kst` → `naver_trend.fetched_at`
- 수급 표와 시장 비교 표는 접속 대신 원자료를 읽는다. 지수 대조(`check_krx_index`)는 원자료로 하되, 지금과 같은 자리(시장 비교 표 안)에서 실행해 경고 순서를 지킨다.
- `data_basis_block`의 생성 시각은 `meta.collected_at`이다.
- `build_section4(inputs, meta, options)`: 지금의 `generate_report` 본문을 옮긴 순수 함수다. 시작할 때 `reset_state()`로 `WARNINGS`·`HISTORY`·`SNAP`을 비운다.
- `collect_meta`의 `import os` 누락을 고친다(R15). 버전에 python·numpy를 더한다(R16).

### 4. 재현 도구 `rebuild_section4.py` (R8, R9)

- 스냅샷 읽기 → `RawInputs`(이전 형식이면 2) → `build_section4` → 비교 3종(Section 4 줄, `values` 경로별 정확 비교, `warnings` 순서 포함) → 요약·JSON·종료 코드.
- 기준본과 같은 형태로 비교하려고, 보고서 생성 때 붙인 Section 4와 같은 방식으로 머리 줄을 뗀다. 머리 줄 떼기 함수는 `generate_strategy_report.py`와 같이 쓴다.
- 옵션 재계산: `--weights`·`--cyclical`·`--not-cyclical`만 받는다. 스냅샷에 없는 지수·종목이 필요해지면 `option_needs_data`를 낸다. `--out`은 새 파일이어야 한다. 결과 머리에 원본 경로·SHA-256, 바꾼 옵션, '보고서가 아님'을 적는다.

### 5. 규칙 원본·스킬 문서

- `references/rules/data-snapshot.md`: 형식 2, 원자료 항목·목록·표 형식, 받은 시각 규칙, 이전 형식 판별, 재현 도구와 종료 코드.
- `financial-analyst/SKILL.md`: Resources에 재현 도구를 추가하고, `--snapshot` 설명을 사실에 맞게 고친다. 버전은 3.4.0.
- `docs/decisions/0006-pipeline-split.md`: 원자료 저장과 정제 재실행(R5), 받은 시각(R4), 계산·출력 모듈 분리를 미룬 이유(Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/003-pipeline-split/
├── spec.md              # 요구사항 (명확화 1건, plan 중 FR-002·Edge Case 조정)
├── plan.md              # 이 문서
├── research.md          # Phase 0: 조사·측정과 결정 R1~R16
├── data-model.md        # Phase 1: 스냅샷 형식 2, 원자료 항목·목록, 재현 결과
├── quickstart.md        # Phase 1: 끝에서 끝까지 검증 절차
├── contracts/cli.md     # Phase 1: 명령·종료 코드·출력 형식
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks에서 생성
```

### Source Code (repository root)

```text
skills/financial-analyst/
├── references/rules/data-snapshot.md   # 변경: 형식 2, 원자료, 재현
├── scripts/
│   ├── collect.py                      # 신규: 외부 접속·시각 (유일)
│   ├── raw_inputs.py                   # 신규: 원자료 형식·접근
│   ├── rebuild_section4.py             # 신규: 재현 확인·옵션 재계산
│   ├── get_financial_stats.py          # 변경: 접속 제거, 원자료 기반 정제·계산·출력, build_section4, repo_commit 수정
│   ├── data_checks.py                  # 변경: 요청 함수를 collect.py로 이동 (해석 함수는 유지)
│   ├── check_data_sources.py           # 변경: 요청 함수 import 위치
│   └── snapshot.py                     # 변경: 형식 버전, inputs 직렬화 연결
└── SKILL.md                            # 변경: Resources, --snapshot 설명, 3.4.0
skills/investment-strategy/scripts/generate_strategy_report.py  # 변경: 머리 줄 떼기 함수 공유(동작 그대로)
tests/
├── test_raw_inputs.py                  # 신규: 표 왕복(실제 표 형태), 누락·형식 오류, 이전 형식
├── test_rebuild.py                     # 신규: 재현 동일성, 변조·누락, 옵션 재계산, 기준값 영향 범위, 차단 실행, 코드 검사
├── test_snapshot.py                    # 변경: 생성 경로가 원자료 기반으로 바뀐 테스트 갱신, repo_commit
├── test_data_checks.py                 # 변경: 이동한 요청 함수 import
├── fixtures/003/                       # 신규: 실제 수집 형식 2 스냅샷(장중), README(출처·수집 시각)
├── requirements-pinned.txt             # 신규: 시험 스냅샷과 같은 pandas·numpy 고정 버전(CI·로컬 테스트 공용)
└── tools/replay_main.py                # 신규: 분리 전 코드 재생 비교(로컬 수동, 테스트 수집 대상 아님)
docs/decisions/0006-pipeline-split.md   # 신규
.github/workflows/ci.yml                # 변경: 테스트 단계에 --with-requirements tests/requirements-pinned.txt
```

**Structure Decision**: 기존 스킬 구조를 유지한다. 새 모듈은 모두 `financial-analyst/scripts/`에 두어 스킬 폴더 안에서 자기완결적으로 동작한다(헌법 기술 제약). 경계를 모듈로 강제하는 곳은 외부 접속 한 곳(`collect.py`)뿐이다. 정제와 계산·출력은 같은 파일 안에서 실행 순서와 값 비교로 구분한다.

## 단계와 순서

| 단계 | 내용 | 사용자 시나리오 | 앞 단계 |
|---|---|---|---|
| A | 기준 확보: 분리 전 코드로 장중·마감 후 Section 4와 원자료(재생용)를 남긴다. `repo_commit` 수정 | — | — |
| B | `raw_inputs.py`: 표 형식·접근·이전 형식 판별과 테스트 | US1 | — |
| C | `collect.py`: 모든 외부 접속 이동, 받은 시각·실패 기록 | US1 | B |
| D | `get_financial_stats.py`: 원자료 기반 정제·계산·출력, `build_section4`, 생성 경로 왕복 | US1 | B, C |
| E | 재생 비교로 분리 전후 같음 확인(R12). 차이를 0으로 만들거나 원인 기록 | FR-014 | A, D |
| F | `rebuild_section4.py` 확인 모드, 시험 스냅샷 커밋, 재현·차단·변조 테스트 | US1 (MVP) | D |
| G | 기준값 영향 범위 테스트, 계산값과 글자 차이 구분 보고 | US2 | F |
| H | 옵션 재계산 | US3 | F |
| I | 규칙 원본, SKILL.md, 결정 기록, README·ROADMAP·CLAUDE.md, quickstart 전체 실행, CI | 전체 | 전부 |

## Complexity Tracking

| 복잡도 | 필요한 이유 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 원자료 표를 자료형·시간대·정밀도까지 저장 | 같은 스냅샷에서 같은 Section 4를 내려면, 계산이 읽는 DataFrame이 원래와 완전히 같아야 한다(R3: 문자열 인덱스만 저장하면 9/28 표가 달랐다) | `DataFrame.to_json`과 같은 기본 직렬화는 시간대·정밀도·인덱스 자료형을 잃는다 |
| 원자료별 받은 시각 | 장중·장 마감 판단과 NTM 가중이 지금처럼 각 값을 받은 시각 기준으로 나와야 한다(R4) | 시각 하나로 통일하면 15:40 경계 실행에서 판정이 달라진다 |
| 정제를 다시 실행하고 저장값과 비교 | 교정 전 원래 값을 보존하고, 데이터 품질 규칙 변경도 같은 입력으로 비교할 수 있다(R5) | 정제 결과만 저장하면 원래 값과 정제 코드의 변화를 확인할 수 없다 |
| 재생 비교 도구 | 분리 전후 같음을 시세 변동 없이 확인한다(R12) | 같은 시각 실행 비교만으로는 22초 사이 시세 변동이 섞인다(002 T037) |
| **계산과 출력은 같은 표 함수에 남김** (모듈 분리를 하지 않음) | 표 함수 15개를 '값 계산'과 '글자 만들기'로 쪼개면 약 1,500줄이 바뀌고, 글자 단위 같음(SC-004)을 깨뜨릴 위험이 크다. 두 단계 모두 원자료만 읽는 순수 함수이고 계산 결과가 `values`에 모두 기록되므로, spec의 성공 기준(재현, 차단, 계산값과 글자 구분)은 모듈 분리 없이도 확인된다 | 이번 단계에서 하면 위험 대비 얻는 검증 가능성이 없다. 계산 결과를 별도 자료 구조로 넘기는 분리는 이후 표 형식 변경이 필요할 때 다시 판단한다(결정 0006에 기록) |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 수집 이동 중 한 곳이라도 접속이 남음 | 코드 검사 테스트(접속 라이브러리 import, 시각 호출 금지)와 소켓 차단 실행 테스트(R11) |
| 경고 순서·문장이 분리 전과 달라짐 | 수집은 경고를 내지 않고 실패만 기록한다. 경고 위치는 지금 코드 자리를 유지한다. 재생 비교로 Section 8까지 글자 비교한다 |
| yfinance 내부 대체 경로(`_quote._info`)와 원자료 저장의 불일치 | `info` 항목에 대체 사유 `note`를 남기고, 정제가 같은 경고를 낸다. 재생 도구도 같은 경로를 재생한다 |
| 시험 스냅샷의 실제 데이터가 CI 저장소를 키움(약 2MB) | 한 벌만 커밋하고(장중), 마감 후 시나리오는 로컬 확인. 필요하면 들여쓰기 없는 JSON으로 저장 |
| 라이브러리 버전 차이로 미세한 계산 차이 (CI가 받는 pandas·numpy가 시험 스냅샷과 달라져 무관한 PR이 실패) | 버전을 기록하고 경고한다(R16). `tests/requirements-pinned.txt`에 시험 스냅샷을 만든 pandas·numpy 정확한 버전을 고정하고, CI와 로컬 테스트 명령이 함께 쓴다. 고정 버전이 시험 스냅샷의 `meta.versions`와 같은지 테스트로 확인하므로, 버전을 올리려면 시험 스냅샷을 다시 만들어야 한다(조용한 건너뜀 없음, 헌법 III·V) |
| 이전 형식 스냅샷을 쓰는 002 점검이 깨짐 | `values`·`series`·`section4` 형식을 유지하고, 002 검증 세트 테스트를 그대로 실행한다(SC-008) |
| 리팩터링 중 판정 회귀 | 단계 A의 기준 Section 4와 재생 비교. 판정 기호 행 100% 같음을 확인한 뒤 완료로 표시한다 |
