# Implementation Plan: 보고서 숫자 자동 대조

**Branch**: `claude/002-report-number-check` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-report-number-check/spec.md`

**Status**: Implemented (2026-10-19)

## Summary

보고서 한 건과 짝 스냅샷을 읽어 (1) Section 4 밖 본문의 숫자를 '스크립트 값 일치 / 인용 / 근거 없음'으로 분류하고, (2) Section 4가 생성 후 바뀌었는지와 Section 4 숫자가 모두 스냅샷에 있는지 확인하며, (3) 인용·참고문헌 형식과 남은 `[AI_TODO]`를 점검하는 스크립트 `check_report_numbers.py`를 만든다. 대조는 표시 자릿수 반올림·단위 환산·부호 규칙으로 하고(시제품 측정: 0.55초), 기사 대조는 로컬 선택 옵션으로 둔다. 선행 작업으로 Section 4의 스냅샷 기록 누락(약 150개)을 채우고, Section 4 기준본을 스냅샷에 남긴다. investment-strategy는 보고서 마무리 전에 점검을 반복하고 남은 문제를 '숫자 점검 결과' 섹션에 기록한다.

## Technical Context

**Language/Version**: Python 3.12 (uv 관리, CI 3.12; 로컬 venv 3.13에서도 동작)

**Primary Dependencies**: 기존 그대로 — 표준 라이브러리(`re`, `json`, `difflib`, `hashlib`, `argparse`), 기사 대조에만 `requests`·`beautifulsoup4`(이미 requirements에 있음). 새 의존성 없음.

**Storage**: 입력은 보고서 `.md`와 짝 스냅샷 `_data.json`(001 형식 + `section4`·`rules.*` 추가). 출력은 표준 출력과 선택적 JSON 파일.

**Testing**: pytest(`tests/`), 고정 검증 세트 `tests/fixtures/002/`, 기사 대조는 mock. GitHub Actions CI.

**Target Platform**: Windows(로컬), macOS(로컬), Ubuntu(CI)

**Project Type**: CLI 스크립트 (Claude Code / Antigravity 스킬)

**Performance Goals**: 보고서 1건 점검 10초 이내, 네트워크 없이(SC-006). 시제품 0.55초.

**Constraints**: 보고서·스냅샷 읽기 전용(FR-014). 짝 스냅샷 외 파일 읽지 않음(헌법 VI). 네트워크는 `--fetch-sources`일 때만. Windows 콘솔 UTF-8 출력(001과 같은 처리). CI 테스트는 네트워크 없이 돈다 — 국내 사이트에 접속하는 테스트는 `network` 표시를 달아 CI에서 건너뛰고 로컬에서만 실행한다(헌법 기술 제약).

**Scale/Scope**: 보고서 1건당 본문 숫자 약 270개(제외 후 약 185개), Section 4 숫자 약 700개, 스냅샷 값 약 3,000개, 참고문헌 10~30개.

조사 결과와 결정 근거는 [research.md](research.md)에 있다. 미해결 항목 없음.

## Constitution Check

*GATE: Phase 0 전 확인, Phase 1 설계 후 다시 확인.*

| 원칙 | 점검 | 설계 전 | 설계 후 |
|---|---|---|---|
| I. 객관성 우선 | 판정 로직·기준값을 바꾸지 않는다. 판정 기준값은 코드 상수를 스냅샷에 기록만 한다. Section 4 변경(판정 포함)을 감지한다. | ✅ | ✅ |
| II. 출처 추적 | 이 기능의 목적. 직접 계산 숫자 금지(FR-012)를 스크립트가 확인한다. Section 4 누락을 채워 "모든 숫자 → 스냅샷"을 완성한다. | ✅ | ✅ |
| III. 조용한 오류 금지 | 스냅샷·기준본이 없으면 '대조 불가' 문제로 낸다. 기사 접속 실패는 `unverifiable`이며 통과가 아니다. 남은 문제는 보고서에 기록해야 종료 코드 0. | ✅ | ✅ |
| IV. 규칙 단일 원본 | 제외 범주·단위 환산·허용 오차·인용 범위·참고문헌 형식은 `references/rules/report-number-check.md` 한 곳. 새 스냅샷 경로는 `data-snapshot.md`에 추가. 기준값을 바꾸지 않으므로 결정 기록은 '숫자 점검 도입' 1건. | ✅ | ✅ |
| V. 검증 가능한 변경 | 검증 세트를 사람이 확정(R11), Section 4 변경 주입 테스트, 수정 전후 판정 비교([quickstart.md](quickstart.md) 6). | ✅ | ✅ |
| VI. Clean-Slate | 점검 도구는 같은 보고서의 짝 스냅샷만 읽는다(사후 검증). 검증 세트의 보고서·스냅샷은 테스트 자료이며 위키에 넣지 않는다. | ✅ | ✅ |

위반 없음. 아래 Complexity Tracking은 설계상 복잡도 기록용이다.

## 현재 구조와 바뀌는 점

```
generate_strategy_report.py
  ├─ 보고서·스냅샷 파일명 결정 (001)
  ├─ subprocess: get_financial_stats.py --snapshot X_data.json   → Section 4 마크다운
  │     └─ 표 함수들: SNAP.record(...)  ← [변경] 누락 값 기록 추가, rules.* 기준값 기록
  ├─ [신규] snapshot.attach_section4(X_data.json, cleaned_financial)
  └─ 보고서 템플릿 쓰기 ([AI_TODO] 포함)

AI가 [AI_TODO] 채움
  └─ [신규] check_report_numbers.py X.md  → 수정·재점검 반복 → --section 블록 붙이고 사유 작성 → exit 0
```

## 설계

### 1. 점검 도구 `skills/financial-analyst/scripts/check_report_numbers.py`

한 파일 안에서 단계별 함수로 나눈다. 단계 사이는 [data-model.md](data-model.md)의 엔터티로 주고받는다.

| 단계 | 함수 (예) | 하는 일 | 근거 |
|---|---|---|---|
| 읽기 | `load_report`, `find_snapshot` | 보고서를 섹션으로 나누고(제목 기준: 머리, 1~3, 4, 5~7, 8 참고문헌, 9 점검 결과), 머리의 스냅샷 파일명을 찾는다 | FR-001 |
| 숫자 찾기 | `extract_mentions` | 토크나이저 + 제외 범주 + 인용 범위·종목 문맥 부여 | R3, R5, FR-002·005 |
| 대조 | `classify` | 표시 자릿수·단위·부호·정보량 규칙으로 스냅샷 대조 → 인용 → 근거 없음 | R4, FR-003·004·012 |
| Section 4 | `check_section4` | 기준본과 줄 비교, 기준본 숫자 → 스냅샷 전수 대조, 경고 문장 대조 | R2, R10, FR-006·015 |
| 참고문헌 | `check_references` | 항목 파싱, 형식·홈페이지·없는 인용·미사용 | R6, FR-007 |
| 미완성 | `find_ai_todo` | `[AI_TODO]` 위치 | FR-008 |
| 기록 확인 | `read_check_section` | '9. 숫자 점검 결과' 섹션의 개수·ID·사유를 현재 결과와 비교 | R9, FR-011 |
| 기사 대조 | `fetch_and_verify` | `--fetch-sources`일 때만 | R7, FR-010 |
| 출력 | `render_summary`, `render_section`, `to_json` | 표준 출력·섹션 블록·JSON, 종료 코드 | R8, FR-009 |

- 숫자 해석(토크나이저·단위 환산)은 본문·Section 4·기사에서 같은 함수를 쓴다.
- 제외 범주, 단위 배율, 기간 단위, 규격 단위, 정보량 낮은 숫자 기준은 코드 상단 상수로 두고, 규칙 원본의 표와 같은 값인지 테스트로 확인한다.

### 2. 스냅샷 보완 (`get_financial_stats.py`, `snapshot.py`)

- [research.md R10](research.md#r10-section-4와-스냅샷-대응-fr-015)의 표 함수에 `SNAP.record` 추가. 계산·표 출력은 바꾸지 않는다.
- 판정 기준값: 판정 함수가 쓰는 코드 상수를 `rules.*`로 기록한다.
- `snapshot.py`에 `attach_section4(path, text)` 추가: JSON을 읽어 `section4`를 넣고 다시 쓴다. 실패하면 예외 → 호출자가 경고.
- 경로 이름은 구현 때 확정해 `data-snapshot.md` §6에 추가한다.

### 3. 보고서 생성·스킬 연동

- `generate_strategy_report.py`: 하위 프로세스 결과로 `attach_section4` 호출(스냅샷 파일이 있을 때만). 실패하면 보고서 머리에 표시.
- `investment-strategy/SKILL.md` Phase 3에 5~8단계 추가([contracts/cli.md](contracts/cli.md#investment-strategy-연동-skillmd-phase-3에-추가)). Best Practices의 'Enforce Referencing'에 점검 도구를 연결.
- `financial-analyst/SKILL.md` Resources에 점검 도구와 규칙 원본 추가.

### 4. 검증 세트

- `tests/fixtures/002/report.md`, `report_data.json`: 측정 보고서와 그 스냅샷 복사본(001 보완 이전 버전, 기준본 없음).
- `labels.json`: 초안을 도구로 만들고 **사람이 전부 검토해 확정**한다. 확정 전에는 해당 작업을 '완료'로 표시하지 않는다(헌법 V).
- 합성 자료: 작은 보고서·스냅샷을 테스트 코드 안에서 만들어 단위 환산, 부호, 범위, 한글 금액, 인용 범위, 섹션 기록 흐름, Section 4 변경 주입을 시험한다.

## Project Structure

### Documentation (this feature)

```text
specs/002-report-number-check/
├── spec.md              # 요구사항 (명확화 완료)
├── plan.md              # 이 문서
├── research.md          # Phase 0: 측정과 결정 R1~R12
├── data-model.md        # Phase 1: 스냅샷 확장, 점검 엔터티
├── quickstart.md        # Phase 1: 끝에서 끝까지 검증 절차
├── contracts/cli.md     # Phase 1: 명령·종료 코드·출력·보고서 섹션 형식
├── checklists/requirements.md
├── baseline-section4.md # T002: 수정 전 Section 4 회귀 기준
└── tasks.md             # /speckit-tasks에서 생성
```

### Source Code (repository root)

```text
skills/financial-analyst/
├── references/rules/
│   ├── report-number-check.md      # 신규: 제외 범주, 단위 환산, 허용 오차, 인용 범위, 참고문헌 형식
│   └── data-snapshot.md            # 변경: section4, rules.*, 추가 경로
├── scripts/
│   ├── check_report_numbers.py     # 신규: 점검 도구
│   ├── snapshot.py                 # 변경: attach_section4
│   └── get_financial_stats.py      # 변경: Section 4 누락 값·기준값 기록
└── SKILL.md                        # 변경: Resources
skills/investment-strategy/
├── scripts/generate_strategy_report.py  # 변경: section4 덧붙이기
└── SKILL.md                             # 변경: Phase 3 점검 단계
tests/
├── test_report_numbers.py          # 신규: 합성 자료 단위 테스트, 검증 세트, Section 4 주입, 참고문헌, 기사 대조 mock
├── test_snapshot.py                # 변경: section4, 추가 경로
├── conftest.py                     # 신규: network 표시 등록
└── fixtures/002/                   # 신규: report.md, report_data.json, labels.json, README.md(출처)
docs/decisions/0005-report-number-check.md   # 신규: 직접 계산 금지·기사 대조 선택 실행·섹션 기록 방식
```

**Structure Decision**: 기존 스킬 구조를 유지한다. 점검 도구는 스냅샷 모듈·규칙 원본과 같은 financial-analyst에 두고, investment-strategy가 형제 스킬 스크립트로 부른다(001의 데이터 수집과 같은 방식).

## 단계와 순서

| 단계 | 내용 | 사용자 시나리오 | 앞 단계 |
|---|---|---|---|
| A | 규칙 원본 초안, 점검 도구 뼈대(읽기·숫자 찾기·출력·종료 코드) | — | — |
| B | 스냅샷 누락 채우기, `rules.*`, `section4` 덧붙이기 | US2 | — (A와 병렬) |
| C | 본문 분류(대조·인용·제외), 검증 세트 초안 | US1 (MVP) | A |
| D | Section 4 변경·스냅샷 대응 점검 | US2 | A, B |
| E | 참고문헌·`[AI_TODO]`·점검 결과 섹션 기록 확인 | US3 | A |
| F | 기사 대조(선택) | FR-010 b | C, E |
| G | 스킬 연동(SKILL.md 2개, 보고서 생성), 결정 기록, README·ROADMAP | FR-011 | C, D, E |
| H | 검증 세트 사람 확정 → SC 테스트, 수정 전후 판정 비교, CI | SC 전체 | 전부 |

## Complexity Tracking

| 복잡도 | 필요한 이유 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 숫자 해석 규칙(제외 9범주, 단위 배율, 정보량 규칙) | 한국어 보고서는 같은 값을 여러 단위로 쓰고, 연도·규격 숫자가 많다. 측정에서 잡음 대부분이 여기서 나왔다 | 단순 숫자 일치는 오탐이 많아 검토 부담이 줄지 않는다(SC-002·003) |
| 점검 결과 섹션의 ID·사유 확인 | FR-011 "남은 항목을 적지 않고 마무리하지 않는다"를 스크립트로 확인해야 한다 | 섹션 존재만 확인하면 오래된 섹션이 그대로 통과한다 |
| Section 4 기준본 전체 저장(약 30KB) | 바뀐 줄과 원래 값을 보여 줘야 한다(FR-006) | 해시만 저장하면 무엇이 바뀌었는지 알 수 없다 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 정보량 낮은 숫자의 우연한 일치로 '잘못 통과' | 종목 문맥 제한, `weak` 표시와 별도 목록, 검증 세트의 '잘못 통과 0건' 테스트 |
| 검증 세트 정답을 도구 결과로 만들어 순환 검증 | 사람이 전부 검토해 확정(R11). 확정 전에는 완료로 보지 않음 |
| 스냅샷 누락 보완 중 판정 회귀 | 기록만 추가. 같은 시각 수정 전후 Section 4 비교([quickstart.md](quickstart.md) 6) |
| AI가 점검 통과만을 위해 숫자를 지우거나 모호하게 씀 | SKILL.md에 '숫자를 지울 때는 그 주장도 함께 빼거나 출처를 찾는다'를 명시. 기록된 예외는 사유가 보고서에 남아 사람이 본다 |
| 기사 대조의 사이트별 차단·유료 | `unverifiable`로 표시(통과 아님), CI 제외, 형식 점검이 먼저 |
| 001 커버리지 테스트처럼 '키 목록' 점검으로 다시 누락 | Section 4 숫자 → 스냅샷 전수 대조(FR-015)를 테스트로 상시 실행 |
