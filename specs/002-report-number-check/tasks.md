# Tasks: 보고서 숫자 자동 대조

**Input**: Design documents from `specs/002-report-number-check/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md), [quickstart.md](quickstart.md)

**Tests**: 포함 — 헌법 V(검증 가능한 변경)와 SC-001~SC-007이 테스트를 요구한다. 각 시나리오는 테스트를 먼저 쓰고 실패를 확인한 뒤 구현한다.

**Organization**: 사용자 시나리오(US1~US3)별로 나눴다. 커밋 하나에 작업 하나, 각 작업은 테스트가 통과한 상태로 커밋한다(실패를 확인하는 테스트 작업은 다음 구현 작업과 함께 커밋).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일을 고쳐 병렬로 할 수 있음
- **[Story]**: US1·US2·US3
- 경로 약어: `FA` = `skills/financial-analyst`, `IS` = `skills/investment-strategy`, `CHK` = `FA/scripts/check_report_numbers.py`, `TRN` = `tests/test_report_numbers.py`

---

## Phase 1: Setup

- [x] T001 spec·plan 검토와 승인 (사용자, 2026-10-14) → `spec.md`·`plan.md`의 Status를 Approved(날짜)로 바꾼다
- [x] T002 회귀 기준 저장: 수정 전 코드(`main`)로 `get_financial_stats.py --tickers 000660.KS,005930.KS,MU,TSM`을 실행해 Section 4를 `specs/002-report-number-check/baseline-section4.md`에 저장한다(실행 시각·커밋 기록). 판정·종합 판단 비교용
- [x] T003 [P] 검증 세트 자료 복사: 분석 프로젝트의 `reports/AI_메모리_반도체_20261014_Investment_Strategy_Report.md`와 `_data.json`을 `tests/fixtures/002/report.md`, `tests/fixtures/002/report_data.json`으로 복사한다. `report.md` 머리의 `**데이터 스냅샷**:` 줄을 `report_data.json`으로 바꾼다(그 밖의 글자는 고치지 않음). `tests/fixtures/002/README.md`에 출처·생성 시각·"001 보완 이전 스냅샷, section4 기준본 없음"을 적는다

---

## Phase 2: Foundational (모든 시나리오의 전제)

- [x] T004 [P] 규칙 원본 `FA/references/rules/report-number-check.md` 작성: 섹션 구분 규칙(머리, 1~3, 4, 5~7, 8 참고문헌, 9 숫자 점검 결과), 제외 9범주와 예(research R3 표 그대로), 단위 배율 표(R4-2), 허용 오차 "|후보 − 표기| ≤ 0.5×10⁻ᵈ"(R4-1), 부호 규칙(R4-3), 정보량 낮은 숫자 "소수점 없는 두 자리 이하 정수"와 종목 문맥 규칙(R4-4), 인용 범위(R5), 참고문헌 형식·홈페이지 판정(R6), 기사 대조 상태 3종과 "본문 글자 500자 미만"(R7), 용량 단위(GB·TB)는 수량, 규격 단위(nm·나노·단·Hi·bit)는 제외(spec Edge Cases), 종료 코드 0/1/2(R8), 문제 ID 형식 `{섹션 제목 해시 4자}-{원문 표기}-{같은 섹션 안 몇 번째 등장}`(R9)
- [x] T005 `CHK` 뼈대 + `TRN` 첫 테스트: `argparse`(인자 `REPORT`, `--snapshot`, `--json`, `--section`, `--fetch-sources`, `--verbose` — contracts/cli.md 표 그대로), Windows UTF-8 출력(`get_financial_stats.py`와 같은 처리), `load_report`(섹션 구분), `find_snapshot`(머리의 `**데이터 스냅샷**:` 줄 → 보고서와 같은 폴더), data-model §2의 엔터티를 `dataclass`로 정의, 보고서 없음·읽기 실패·인자 오류 → 종료 코드 `2`. 테스트: 섹션 구분, 스냅샷 찾기, 종료 코드 2
- [x] T006 `CHK` 숫자 해석 함수 `parse_numbers(text)` + `TRN` 표 형식 테스트: 부호(`+`, `-`, `−`), 통화 기호(₩, $), 쉼표 숫자, 소수 자릿수, 단위(`%`, `%p`, `배`, `x`, `조`, `억`, `만`, `원`, `T`, `B`, `M`, `건`, `주`), 한글 금액 결합("3조 9,334억 원" → 하나, 값 -3.9334·단위 `조`), 범위 분리("26.5%~31.2%" → 둘), 말로 쓴 방향("34.3% 하락" → 부호 없음 표기). 본문·Section 4·기사에서 같은 함수를 쓴다
- [x] T007 `CHK` 제외 규칙 + `TRN` 테스트: 9범주(`date`, `year`, `period_label`, `duration`, `numbering`, `citation`, `ticker_code`, `product_spec`, `diagram_style`)를 판별하고 범주별 개수를 센다. research R3 표의 예가 모두 제외되고, "52.18%", "₩237,500", "-39,334억 원", "2.44배"는 제외되지 않음을 확인한다. 코드 상수(범주·단위 배율·기간 단위·규격 단위)가 규칙 원본 표와 같은지 확인하는 테스트 포함

**Checkpoint**: `CHK REPORT`가 섹션을 나누고 숫자를 찾아 제외 개수와 함께 출력한다(분류는 아직 없음).

---

## Phase 3: User Story 1 - 본문 숫자의 근거 자동 분류 (Priority: P1) 🎯 MVP

**Goal**: Section 4 밖 본문의 모든 숫자가 `script`·`cited`·`unsupported`로 분류되고, 검토자는 근거 없음 목록만 본다.

**Independent Test**: 검증 세트(`tests/fixtures/002/`)로 점검을 실행해 사람이 확정한 라벨과 비교한다.

- [x] T008 [US1] `TRN`에 합성 보고서·스냅샷으로 US1 인수 시나리오 1~8 테스트 작성(실패 확인): 52.18% ↔ 0.52183 일치·경로 표시, "P/B 2.44배" ↔ 2.4417, "107.4조 원 [7]" → `cited`·참고문헌 7, 표 행의 '출처' 칸 인용, 근거 없음 → 위치(섹션 제목·줄)·문맥, "-3조 9,334억 원" ↔ 억 원 단위 -39334 일치, 스냅샷 값 두 개의 합(스크립트가 내지 않는 값) → `unsupported`, 수량 아닌 표기 제외. 추가: 부호 불일치("+34.3%" ↔ -0.343) → 불일치, 정보량 낮은 숫자의 종목 문맥 제한과 `weak`
- [x] T009 [US1] `CHK` 인용 범위와 종목 문맥 부여: 문장 나누기(`다.`·`. `·`<br>`·줄바꿈 — 목록 항목도 문장 단위로 나눔, spec FR-005), 표 행(`|`로 시작하는 줄) 단위로 `[n]`·`[n], [m]`을 `scope_citations`에 넣는다. 가장 가까운 상위 제목이나 같은 줄의 종목 코드(스냅샷 meta의 tickers)로 `ticker_context`를 정한다
- [x] T010 [US1] `CHK` `classify`: 분류 순서 "제외 → 스냅샷 일치(`script`) → 범위 내 인용(`cited`) → 나머지(`unsupported`)". 일치 규칙 R4-1~5. `NumberMention` 필드(`id`, `raw`, `value`, `unit`, `decimals`, `explicit_sign`, `section`, `line`, `context`, `ticker_context`, `scope_citations`, `classification`, `weak`, `matched_path`, `match_count`, `snapshot_status`)를 data-model §2-1대로 채운다. `series` 값도 후보에 넣는다. T008 통과
- [x] T011 [US1] `CHK` 출력: `render_summary`(contracts/cli.md '표준 출력' 형식: 분류별 개수 표, 문제 목록, 약한 일치 목록), `to_json`(`CheckResult` 최상위 키 `report`, `snapshot`, `checked_at`, `counts`, `mentions`, `section4`, `references`, `ai_todo`, `issues`, `exit_code`), `unsupported_number` 문제가 있으면 종료 코드 1, `--verbose`. 짝 스냅샷이 없으면 `no_snapshot` 문제를 내고 스크립트 값 대조는 '대조 불가'로 표시(조용히 통과하지 않음). 읽기 전용 테스트(FR-014): 점검 전후 보고서·스냅샷 파일의 해시가 같고, 짝 스냅샷 외의 `*_data.json`·보고서 파일을 열지 않는다(`open`을 감시)
- [x] T012 [US1] 검증 세트 라벨 초안: 점검 도구 결과로 `tests/fixtures/002/labels.json` 초안을 만든다(data-model §4 형식, 최상위에 `"reviewed": false`). `TRN`에 `test_validation_set` 추가 — `reviewed`가 false면 이유를 밝히고 skip, true면 SC-001(일치율 95% 이상, `unsupported`인데 다른 분류 0건), SC-002(근거 없음 ≤ 제외 대상을 뺀 본문 숫자의 25%), SC-003(제외 대상의 근거 없음 오탐 ≤ 근거 없음 목록의 5%), SC-006(10초 이내) 확인
- [ ] T013 [US1] **사람 검토** (사용자): `labels.json`의 라벨을 전부 확인해 고치고 `"reviewed": true`로 바꾼다. 이후 `test_validation_set`이 통과할 때까지 T010 규칙을 조정한다(규칙을 바꾸면 규칙 원본도 같은 커밋에서 수정). 통과 전에는 이 작업과 US1을 완료로 표시하지 않는다

**Checkpoint**: 검증 세트 보고서의 근거 없는 숫자 목록이 위치·문맥과 함께 나온다(MVP).

---

## Phase 4: User Story 2 - Section 4 수정 감지와 스냅샷 대응 (Priority: P2)

**Goal**: Section 4가 생성 후 바뀌면 바뀐 줄과 원래 값이 나오고, 새로 만든 보고서의 Section 4 숫자는 모두 스냅샷에 있다.

**Independent Test**: 새 보고서의 Section 4 숫자 하나와 판정 하나를 고쳐 점검하면 둘 다 보고되고, 생성 직후에는 스냅샷 누락 0건.

- [x] T014 [US2] `TRN`·`tests/test_snapshot.py`에 테스트 작성(실패 확인): `attach_section4`가 `section4.text`·`sha256`·`attached_at`(KST)을 쓴다, 스냅샷 파일 없으면 예외. `check_section4`가 숫자 변경·판정 기호(🟢🟡🔴) 변경·판정 문구 변경을 `{line, current, original}`로 보고, 기준본 없음 → `no_baseline`, 경고 줄이 스냅샷 `warnings`에 없음 → `warning_not_in_snapshot`
- [x] T015 [P] [US2] `FA/scripts/snapshot.py`에 `attach_section4(path, text)` 추가(JSON 읽기 → 최상위 `section4` 추가 → 다시 쓰기, 실패 시 예외)
- [x] T016 [US2] `IS/scripts/generate_strategy_report.py`: 하위 프로세스 결과(`cleaned_financial`)로 `attach_section4` 호출(스냅샷 파일이 있을 때만). 실패하면 보고서 머리의 '데이터 스냅샷' 줄 옆에 "(Section 4 기준본 저장 실패: 사유)" 표시
- [x] T017 [US2] `CHK` `check_section4`: 기준본과 현재 Section 4를 `difflib`로 줄 비교, 기준본 Section 4 숫자를 T006·T007·T010 규칙으로 스냅샷과 전수 대조해 `section4_not_in_snapshot` 보고, 8번 데이터 품질 경고 줄은 숫자 대조 대신 스냅샷 `warnings[].msg`에 같은 문장이 있는지 확인. 비교 범위는 data-model §1-1(`## 4.` 다음 줄부터 다음 `---`·`## ` 전까지, 앞뒤 빈 줄·줄 끝 공백 무시) — 생성 직후 보고서에서 변경 0건이어야 한다. T014 통과
- [x] T018 [US2] `FA/scripts/get_financial_stats.py` `consensus_tables`: 목표가 최저·평균·최고와 상승여력, 추정치 30일 변화율, EPS 서프라이즈 표(분기별 실제·추정 EPS·서프라이즈 %)를 `SNAP.record`로 기록(research R10 표 경로 예를 따르되 표 열 이름에 맞춰 확정). 계산·표 출력 불변
- [x] T019 [US2] `get_financial_stats.py` `audit_table`: 일회성 손익, 명목·정규화 ROE·EPS 등 표의 값 기록
- [x] T020 [US2] `get_financial_stats.py` `scenario_table`: 현재가 대비 등락률(배수 A·B, 시나리오별, 확률가중), 밴드 최저 P/B 회귀 시 주가·등락률 기록
- [x] T021 [US2] `get_financial_stats.py` `metrics_table`·`trajectory_table`·`cycle_tables`·`peer_table`: PEG 등 남은 지표, 시계열 PER·EPS, 연간 순이익 증감률, 피어 평균 대비 % 기록
- [x] T022 [US2] `get_financial_stats.py` `signal_matrix`·`decision_matrix`: 판정에 쓰는 코드 상수를 `rules.{rule}.{threshold}`로 기록(`source="rules"`, `basis="derived"`, `status="final"`, `note`=규칙 원본 파일 이름). 상수 값은 바꾸지 않는다
- [x] T023 [US2] `FA/references/rules/data-snapshot.md`: §3에 `section4`, §6에 T018~T022에서 확정한 경로와 `rules.*` 추가
- [x] T024 [US2] 커버리지 테스트 보강(네트워크 없음): 표 함수(`overview_table`~`scenario_table`, `warnings_section`)를 합성 `results`·`HISTORY`로 호출해 Section 4를 만들고, 그 전체를 `check_section4`의 스냅샷 대조에 넣어 `section4_not_in_snapshot` 0건을 확인한다(SC-004 후반, FR-015). 합성 입력은 모든 표가 채워지도록(한국 종목 1, 미국 종목 1, 순환업종, 수급·서프라이즈·감사 항목 포함) 만든다. 실제 데이터로 같은 확인을 하는 테스트는 `@pytest.mark.network`로 두고 quickstart 4단계에서 로컬 실행한다. 남는 항목이 있으면 T018~T022로 돌아가 채운다
  - *(구현 메모)* 수급·시장 비교 표 함수가 안에서 직접 네트워크 조회를 해서 합성 입력으로 표를 다시 만들려면 조회를 여럿 흉내 내야 했다. 대신 실제 실행의 Section 4·스냅샷을 `tests/fixtures/002/coverage/`에 고정해 CI에서 0건을 확인하고, 표 코드 변경으로 생기는 새 누락은 `network` 표시 테스트(`test_section4_live_fully_in_snapshot`)가 로컬에서 잡는다. 측정: 누락 183 → 0, 판정 줄 변화 0, 스냅샷 269KB
- [x] T025 [US2] CI 네트워크 테스트 정리(헌법 기술 제약): `tests/conftest.py`에 `network` 표시를 등록하고, 001에서 들어온 실제 접속 테스트(`tests/test_snapshot.py`의 `test_snapshot_coverage`, `test_warnings_and_meta_match_report_section8`)에 `@pytest.mark.network`를 단다. `.github/workflows/ci.yml` 테스트 단계를 `pytest tests -q -m "not network"`로 바꾸고, `CLAUDE.md` 명령에 로컬 전체 실행(`-m network` 포함)을 적는다. 001 테스트가 하던 키 목록 확인은 T024의 네트워크 없는 테스트가 대신한다

**Checkpoint**: 새 보고서에서 Section 4 변경 0, 스냅샷 누락 0. Section 4를 고치면 감지된다.

---

## Phase 5: User Story 3 - 인용과 참고문헌 형식 점검 (Priority: P3)

**Goal**: 인용 번호와 참고문헌이 서로 맞고, 각 참고문헌이 찾아갈 수 있는 형식이며, 남은 문제는 보고서의 '숫자 점검 결과' 섹션에 사유와 함께 기록된다.

**Independent Test**: 검증 세트 보고서에서 홈페이지 주소 17건이 모두 지적되고(SC-005), 섹션 기록 흐름이 종료 코드 1 → 0으로 바뀐다.

- [x] T026 [US3] `TRN`에 테스트 작성(실패 확인): 참고문헌 두 형식(`[n] 제목 — 발행일 — URL`, `[n] [제목](URL) — 날짜`) 파싱, `homepage_url`(경로 없음·`/`·`/index.html`), `missing_date`, `missing_title`, `missing_url`, 없는 인용([18]), 미사용 참고문헌(`warning`, 종료 코드에 영향 없음), `[AI_TODO]` 위치, 검증 세트에서 `homepage_url` 17건
- [x] T027 [US3] `CHK` `check_references`, `find_ai_todo` 구현. 참고문헌 파싱은 '## 9.' 제목에서 끝난다. T026 통과
- [x] T028 [US3] `TRN`에 섹션 기록 흐름 테스트 작성(실패 확인): `--section` 출력 형식(contracts/cli.md: 머리 줄 개수, 표 `ID | 위치 | 숫자 | 문제 | 사유`, 남은 문제 없으면 "남은 문제 없음"), 섹션 없음 → `check_section_missing`, 개수 다름 → `check_section_stale`, 사유가 `[AI_TODO]` → `documented: false`, 모든 남은 문제에 사유 → 종료 코드 0. 섹션 자체는 숫자 대조에서 빠진다
- [x] T029 [US3] `CHK` `render_section`, `read_check_section`, 문제 ID(R9), `documented` 판정과 종료 코드 규칙(contracts/cli.md '종료 코드'). T028 통과
- [x] T030 [US3] `TRN`에 기사 대조 테스트(실패 확인, `requests.get`을 흉내 냄): 문서에 숫자 있음 → `found`, 없음 → `not_found`(`source_not_found` 문제), 시간 초과·홈페이지 주소·본문 500자 미만 → `unverifiable`(`source_unverifiable` 문제, 통과 아님). `--fetch-sources` 없이는 `requests.get`이 호출되지 않음
- [x] T031 [US3] `CHK` `fetch_and_verify`: 제한 시간 10초, 재시도 없음, `beautifulsoup4`로 본문 글자 추출, T006 숫자 해석·R4 단위 규칙으로 대조. T030 통과

**Checkpoint**: 검증 세트 보고서에 `--section` 블록을 붙이고 사유를 채우면 종료 코드 0.

---

## Phase 6: Polish & Cross-Cutting (스킬 연동·문서·검증)

- [x] T032 `IS/SKILL.md` Phase 3에 5~8단계 추가(contracts/cli.md 'investment-strategy 연동' 그대로, Claude Code·Antigravity 명령 병기). Best Practices의 'Enforce Referencing'에 점검 도구 연결과 "숫자를 지울 때는 그 주장도 함께 빼거나 출처를 찾는다" 추가. `IS/scripts/generate_strategy_report.py` 참고문헌 자리 안내에 "점검 결과 섹션은 이 목록 뒤에" 한 줄 추가
- [x] T033 [P] `FA/SKILL.md` Resources에 `check_report_numbers.py`와 `report-number-check.md` 추가. 버전: financial-analyst 3.3.0, investment-strategy 2.2.0
- [x] T034 [P] 결정 기록 `docs/decisions/0005-report-number-check.md`: 직접 계산 숫자 금지, 기사 대조 로컬 선택 실행, 남은 예외의 보고서 기록 방식, Section 4 기준본을 스냅샷에 저장한 이유, 판정 기준값을 스냅샷에 기록한 이유
- [x] T035 [P] `README.md`(디렉토리 구조, financial-analyst·investment-strategy 기능, 변경 이력), `ROADMAP.md`(2단계 상태), `CLAUDE.md`(명령에 점검 도구 실행 추가)
- [x] T036 quickstart.md 단계 1~5 실행, 결과(종료 코드·개수·실행 시간)를 PR 본문에 기록
  - *(결과 2026-10-14 18:3x KST)* 1: 오프라인 테스트 209 통과(검증 세트 1 건너뜀). 2: 검증 세트 종료 코드 1, 0.38초, 홈페이지 참고문헌 17, Section 4 누락 204(001 이전 스냅샷)·기준본 없음. 3: --section 블록(문제 276행) 붙임 → 1, 사유 기입 → 0. 4: 새 보고서 section4 저장, 변경 0·스냅샷 누락 0·경고 누락 0, 남은 문제는 [AI_TODO] 42뿐(틀 안내문 속 '0%'가 잡히던 문제를 고침), Section 4 현재가 수정 → 바뀐 줄과 원래 값 보고. 5: --fetch-sources 홈페이지 17건 요청 없이 unverifiable
- [ ] T037 판정 불변 확인(헌법 V): 같은 시각에 `main` 코드(별도 worktree)와 이 브랜치 코드로 `000660.KS,005930.KS,MU,TSM` Section 4를 만들어 판정(🟢🟡🔴)·종합 판단이 같은지 비교. T002 기준과도 비교하고, 다르면 원인을 PR에 적는다
- [ ] T038 CI 통과(문법 검사, 테스트, 위키 근거 대조) 확인. `pytest -rs` 출력에서 `test_validation_set`이 건너뛰어지지 않고 통과했는지 확인한다(건너뛰면 SC-001 미검증이므로 PR을 열지 않는다), `checklists/requirements.md`와 spec Status 갱신, PR 생성

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3(US1, MVP) → Phase 4·5 → Phase 6
- T001(승인) 전에는 구현 작업을 시작하지 않는다. T002·T003은 T001 이후 병렬 가능
- Phase 2: T004는 독립. T005 → T006 → T007 (같은 파일)
- US1: T008 → T009 → T010 → T011 → T012 → T013(사람). T013은 US1 완료 조건이지만 Phase 4·5 진행을 막지 않는다
- US2: T014 → T015(병렬 가능) → T016 → T017. T018~T022는 같은 파일이라 순서대로, T017과는 독립. T023은 T018~T022 이후, T024는 T017·T023 이후, T025는 T024 이후
- US3: T026 → T027 → T028 → T029 → T030 → T031. US2와 독립(같은 `CHK` 파일을 고치므로 동시에 하지 않고 번갈아 커밋)
- Phase 6: T032은 US1~US3 이후. T033~T035는 서로 병렬. T036·T037은 T032 이후, T038이 마지막

## Parallel Opportunities

- Setup: T002(네트워크 실행)와 T003(파일 복사)
- Foundational: T004(규칙 문서)와 T005~T007(코드)
- US2 안: T015(`snapshot.py`)와 T018~T022(`get_financial_stats.py`)는 다른 파일 → 동시에 가능
- US2 vs US3: 스냅샷 보완(T018~T023, `get_financial_stats.py`)과 참고문헌 점검(T026~T031, `CHK`)은 다른 파일 → 동시에 가능
- Polish: T033·T034·T035

```text
# 예: US1 MVP가 끝난 뒤 두 갈래로 동시에 진행
갈래 1: T014 → T015 → T018 → T019 → T020 → T021 → T022 → T023   (snapshot.py, get_financial_stats.py, data-snapshot.md)
갈래 2: T026 → T027 → T028 → T029                                 (check_report_numbers.py, test_report_numbers.py)
합류:   T016 → T017 → T024 → T025 → T030 → T031
```

## Implementation Strategy

1. **MVP (Phase 1~3)**: 점검 도구가 본문 숫자를 분류하고 근거 없는 목록을 낸다. 이것만으로 검토 대상이 약 200개에서 수십 개로 준다. 사람 검토(T013)로 정확도를 확정한다.
2. **US2**: 스냅샷 누락을 채우고 Section 4 변경을 감지한다. 새 보고서부터 본문 대조의 기준이 완전해진다.
3. **US3**: 참고문헌 형식과 남은 예외 기록 흐름을 더해, 스킬이 "고칠 때까지 반복 → 남은 것은 기록"을 스크립트로 확인할 수 있게 한다. 기사 대조는 마지막에 선택 기능으로 붙인다.
4. **Polish**: 스킬 절차·문서·결정 기록을 갱신하고, 판정 불변을 확인한 뒤 PR을 연다.
