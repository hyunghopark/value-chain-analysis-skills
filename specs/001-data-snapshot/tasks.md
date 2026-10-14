# Tasks: 데이터 스냅샷과 출처 정보

**Input**: Design documents from `specs/001-data-snapshot/`

**Prerequisites**: plan.md (승인됨), spec.md (승인됨)

**Tests**: 포함 — 헌법 V(검증 가능한 변경)와 SC-002·SC-005가 테스트를 요구한다.

**Organization**: 사용자 시나리오(US1~US3)별로 나눴다. 커밋 하나에 작업 하나, 각 작업은 테스트가 통과한 상태로 커밋한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일을 고쳐 병렬로 할 수 있음
- **[Story]**: US1·US2·US3

---

## Phase 1: Setup

- [x] T001 spec 열린 질문과 plan 결정 확인 → spec·plan 승인 (2026-10-14)
- [x] T002 회귀 기준 저장: 수정 전 코드로 `000660.KS,005930.KS,MU,TSM` 보고서의 Section 4를 `specs/001-data-snapshot/baseline-section4.md`에 저장 (판정·주요 수치 비교용, 실행 시각 기록) (2026-10-14 11:31 KST)

---

## Phase 2: Foundational (모든 시나리오의 전제)

- [x] T003 [P] 형식 규칙 `skills/financial-analyst/references/rules/data-snapshot.md` 작성 (JSON 구조, basis·status 어휘와 뜻, 점 표기 경로 규칙, Clean-Slate)
- [x] T004 [P] `skills/financial-analyst/scripts/snapshot.py` + `tests/test_snapshot.py` (어휘 검증, corrected 필수 필드, series 260일 제한, 경고 KI 파싱, 저장 실패 예외)
- [x] T005 `get_financial_stats.py`: 전역 `SNAP`, `warn()` → `SNAP.warning()`, `--snapshot` 인자와 저장·실패 경고, 메타(시각·인자·버전·커밋) (T004 이후)

**Checkpoint**: `--snapshot`으로 빈 값 + 경고 + 메타가 담긴 파일이 생긴다.

---

## Phase 3: User Story 1 - 보고서 숫자의 출처 확인 (Priority: P1) 🎯 MVP

**Goal**: Section 4 표의 모든 값을 출처 정보와 함께 스냅샷에서 찾을 수 있다.

**Independent Test**: 보고서를 만들고 Section 4 임의 값의 경로를 스냅샷에서 찾는다.

- [x] T006 [US1] Yahoo info 원값(가격·52주 범위·핵심 지표)과 한국 종목 덮어쓰기(네이버 지표, WiseReport FY0·FY1·NTM EPS) 기록 — `original` 포함 (`get_stats`, `enrich_korean_stock`)
- [x] T007 [US1] 수급 표: 날짜별 순매수 수량·수급 데이터 가격(`flow_feed_price`)·정규장 종가(`krx_regular_close`)·추정 금액 기록 (`fetch_investor_trends_table`)
- [x] T008 [US1] 컨센서스·추정치 방향(`fetch_estimates`), 사이클 입력(연간 영업이익률·기간), P/B 밴드 입력(시점별 BPS·P/B) 기록
- [x] T009 [US1] 시장 비교·기술적 지표·시나리오의 계산 입력(`inputs`)과 종목·지수 가격 이력 series(260일) 기록
- [x] T010 [US1] `generate_strategy_report.py`: 파일명 결정 → 스냅샷 경로 전달 → 보고서 상단에 파일명 표시
- [x] T011 [US1] 커버리지 테스트: 샘플 보고서의 Section 4 표 값이 모두 스냅샷에 있는지 대조 (SC-002)

**Checkpoint**: US1만으로 보고서 검토자가 출처를 확인할 수 있다.

---

## Phase 4: User Story 2 - 보완·교정 이력 추적 (Priority: P2)

**Goal**: 스크립트가 고친 값마다 원래 값과 KI 번호가 남는다.

**Independent Test**: Yahoo 결측일이 포함된 보고서의 스냅샷에서 그 날짜가 `corrected`·`ki`·`original`을 갖는지 확인.

- [x] T012 [P] [US2] ADR 통화 보정(KI-008) 기록 (`sanitize_metrics`)
- [x] T013 [P] [US2] 종목·지수 이력 보완·교정(KI-002·006) 기록 (`check_krx_history`, `check_krx_index`) + `tests/test_snapshot.py`에 재현 사례 추가

---

## Phase 5: User Story 3 - 나중에 재검증·재현 (Priority: P3)

**Goal**: 스냅샷만으로 당시 실행 조건과 경고를 확인할 수 있다.

- [x] T014 [US3] 경고 목록이 보고서 Section 4 › 8번과 일치하는지, 메타 필드가 채워지는지 테스트

---

## Phase 6: Polish & Cross-Cutting

- [x] T015 [P] SKILL.md(스냅샷 안내, Clean-Slate에 스냅샷 포함)·README·ROADMAP 상태 갱신
- [x] T016 전체 실행 검증: T002 회귀 기준과 판정·주요 수치 비교, 스냅샷 크기 2MB 이하 확인(SC-006), CI 통과
- [x] T017 SC-002 보완 (002 스펙 작성 중 발견): 수급 표 '최근 5일 누적(추정)' 행과 외국인 지분율 칸이 스냅샷에 없던 것을 기록 (`flows.total_5d.*`, `flows.{date}.foreign_hold_ratio`) + 네트워크 없는 재현 테스트

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3(US1, MVP) → Phase 4·5(서로 독립) → Phase 6
- T003·T004는 병렬 가능, T005는 T004 이후
- T010은 T005 이후 아무 때나 가능, T011은 T006~T010 이후
