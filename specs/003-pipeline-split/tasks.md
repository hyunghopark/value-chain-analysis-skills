# Tasks: 수집·정제·계산·출력 분리

**Input**: Design documents from `specs/003-pipeline-split/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md), [quickstart.md](quickstart.md)

**Tests**: 포함한다. 헌법 V와 SC-001~SC-008이 테스트를 요구한다. 각 시나리오는 테스트를 먼저 쓰고 실패를 확인한 뒤 구현한다.

**Organization**: 사용자 시나리오(US1~US3)별로 나눴다. 커밋 하나에 작업 하나를 담고, 각 작업은 테스트가 통과한 상태로 커밋한다. 실패를 확인하는 테스트 작업은 다음 구현 작업과 함께 커밋한다.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일을 고쳐 병렬로 할 수 있음
- **[Story]**: US1·US2·US3
- 경로 약어:

  | 약어 | 경로 |
  |---|---|
  | `FA` | `skills/financial-analyst` |
  | `GFS` | `FA/scripts/get_financial_stats.py` |
  | `COL` | `FA/scripts/collect.py` |
  | `RAW` | `FA/scripts/raw_inputs.py` |
  | `RB` | `FA/scripts/rebuild_section4.py` |
  | `TRI` | `tests/test_raw_inputs.py` |
  | `TRB` | `tests/test_rebuild.py` |
  | `TCO` | `tests/test_collect.py` |
  | `FX` | `tests/fixtures/003` |

---

## Phase 1: Setup

- [x] T001 spec·plan 검토와 승인(사용자, 2026-10-20 "003 구현 시작해줘"). 승인되면 `spec.md`·`plan.md`의 Status를 Approved(날짜)로 바꾼다
- [x] T002 회귀 기준 저장(plan 단계 A). 분리 전 코드(`main`, 별도 worktree)로 `get_financial_stats.py --tickers 000660.KS,005930.KS,MU,TSM`을 장중(15:40 이전) 한 번, 장 마감 후 한 번 실행한다. 결과를 `specs/003-pipeline-split/baseline-section4-intraday.md`, `baseline-section4-close.md`에 저장하고 실행 시각·커밋을 적는다. 판정 행 비교용(SC-004)
  - *(진행 2026-10-20)* 장 마감 후: 18:49 KST, `main` a82a5b7, `--cyclical 000660.KS,005930.KS,MU` 포함 → `baseline-section4-close.md` (종합: 000660.KS·005930.KS·MU 🟡 중립/관망(주의 1), TSM 🟢 강력 매수 후보). 장중 기준은 다음 장중에 실행
  - *(완료 2026-10-20)* 장중: KRX 정규장(15:30) 이후지만 넥스트레이드(NXT) 거래가 20:00까지 이어져 19:57에 실행 → `baseline-section4-intraday.md`. 같은 시각(19:57:14) 이 브랜치 코드와 Section 4 전체 같음(다른 줄 0, 판정 행 23줄). 코드의 "15:40 이전" 분기는 테스트로 확인. NXT 시간대 수급 표기 문제는 003 밖의 별도 작업으로 분리
- [x] T003 [P] `repo_commit` 조용한 실패 수정(research R15). `GFS` 최상위에 `import os`를 추가한다. `collect_meta`가 `git` 실패 사유를 `repo_commit_error`에 기록하게 한다(`except Exception: pass` 제거). `meta.versions`에 `python`·`numpy`를 추가한다(R16). 테스트는 `tests/test_snapshot.py`에 둔다: git 저장소 안이면 `repo_commit`이 짧은 해시, 실패를 흉내 내면 `repo_commit` `None`과 `repo_commit_error` 글자

---

## Phase 2: Foundational (모든 시나리오의 전제)

- [x] T004 `RAW` 표 형식 + `TRI` 테스트(research R3, data-model §2).
  - `encode_frame(df)` / `decode_frame(obj)`를 만든다. 인덱스·열마다 `kind`(`datetime`·`index`), `tz`(이름, 예 `Asia/Seoul`, 고정 오프셋 금지), `unit`, `name`, `dtype`, 시간대를 뺀 현지 시각 글자를 저장한다. 결측은 `null`로 쓰고 `dtypes`로 되돌린다.
  - 테스트 표 5종을 실제 Yahoo 모양대로 테스트 코드 안에서 만든다.
    - 시간대 있는 `datetime64[s]` 인덱스(이름 `Date`, 8열, `Volume` int64)
    - 서머타임이 섞인 `America/New_York` 인덱스
    - 열이 `datetime64[s]`인 재무제표(행 인덱스 `str`, NaN 포함)
    - 인덱스 이름이 `period`인 컨센서스 표(`str` 인덱스)
    - 빈 표
  - 각 표가 왕복 후 `DataFrame.equals`, 인덱스·열 자료형, 이름까지 같은지 확인한다
- [x] T005 `RAW` 원자료 접근 + `TRI` 테스트(data-model §2·§3·§5).
  - 항목 검사 규칙:
    - `source` ∈ {`yahoo`, `naver`, `wisereport`, `daum`, `pykrx`}
    - `status` ∈ {`ok`, `empty`, `error`, `skipped`}
    - `kind` ∈ {`json`, `frame`, `table`}이고 `ok`일 때만 `data`
    - `fetched_at`은 "ISO 8601, 초, `+09:00`"
    - `error`일 때 `error` 글자 필수
  - `RawInputs(snapshot_dict)`의 메서드는 `get(sym, item)`, `frame(sym, item)`, `json(sym, item)`, `table(sym, item)`, `fetched_at(sym, item)`이다.
  - 예외:
    - 항목이 없으면 `MissingInput("inputs.<sym>.<item>")`
    - 형식이 틀리면 `InvalidInput`
    - `meta.format_version`이 없거나 2가 아니거나 `inputs`가 없으면 `LegacyFormat`
  - `dumps(meta, inputs)` / `loads(text)`는 생성과 재현이 같이 쓴다. 테스트는 위 예외 4종과, `empty`·`error`·`skipped` 항목이 `None`과 항목 정보를 돌려주는지 확인한다
- [x] T006 [P] `FA/scripts/snapshot.py` 형식 2.
  - `to_dict`/`dump`가 `meta.format_version: 2`와 `inputs`를 함께 쓴다. `values`·`series`·`warnings`·`section4` 형식은 바꾸지 않는다.
  - Section 4 머리 줄 떼기 함수 `section4_body(stdout_text)`를 여기로 옮긴다(지금은 `generate_strategy_report.py`의 `FINANCIAL_HEADER` 처리). `generate_strategy_report.py`는 이 함수를 쓰고, 동작은 그대로다.
  - 테스트는 `tests/test_snapshot.py`에 둔다
- [x] T007 [P] 규칙 원본 `FA/references/rules/data-snapshot.md`에 형식 2 절을 추가한다.
  - data-model §1의 최상위 키 표, §2의 원자료 항목 필드 표와 표 형식, §3의 원자료 목록 표
  - 받은 시각 규칙: research R4의 표
  - 이전 형식 판별(R10)
  - `meta.generated_at`의 뜻 변경(수집 완료 시각)

**Checkpoint**: 원자료를 저장하고 다시 읽으면 표가 원래와 같고, 누락·형식 오류·이전 형식을 구분한다.

---

## Phase 3: User Story 1 - 스냅샷만으로 Section 4 다시 만들기 (Priority: P1) 🎯 MVP

**Goal**: 외부 접속과 시각 읽기를 수집으로 모으고, Section 4를 원자료에서 만들며, `RB`로 네트워크 없이 글자 단위로 같게 다시 만든다.

**Independent Test**: `FX`의 시험 스냅샷을 소켓·시각을 막은 상태에서 `RB`로 다시 만들어 종료 코드 0을 확인한다. 값 변조는 1, 원자료 삭제와 이전 형식은 2.

### 테스트 먼저

- [x] T008 [US1] `TRB` 코드 검사 테스트(SC-002, FR-001 확인 기준 (a), research R11). `GFS`·`RAW`·`RB`·`FA/scripts/data_checks.py`·`FA/scripts/snapshot.py`를 AST로 읽어 다음이 없는지 확인한다. `COL`과 각 파일의 `if __name__ == "__main__":` 블록은 예외다.
  - 네트워크 라이브러리 import: `requests`, `yfinance`, `bs4`, `pykrx`, `urllib`, `socket`. 함수 안의 지역 import도 잡는다.
  - 시각 호출: `datetime.now`, `datetime.today`, `date.today`, `time.time`
  - `snapshot.attach_section4`의 `datetime.now`는 Section 4 글자에 들어가지 않으므로 허용 목록에 이유와 함께 둔다. 이 테스트는 지금 실패해야 한다

### 수집 (`COL`)

- [x] T009 [US1] `COL` Yahoo 수집(research R1·R2·R4, data-model §2·§3).
  - `collect_ticker(sym)`은 `info`를 받는다. `t.info`가 실패해 `t._quote._info`로 대신 받으면 `status: ok`, `note`에 예외 글자를 남긴다. `info`가 없거나 `'symbol'`이 없으면 `status: error`다.
  - 그 밖의 항목: `history`(`period='5y'`, `auto_adjust=False`, 전체 열), `income_stmt`, `quarterly_income_stmt`, `balance_sheet`, `quarterly_balance_sheet`, `earnings_estimate`, `eps_trend`, `eps_revisions`, `earnings_history`.
  - 각 항목에 `source: yahoo`와 받은 직후의 `fetched_at`(KST, 초)을 단다. 예외는 `status: error`와 `error=str(e)`, 빈 표는 `status: empty`다.
  - `TCO`에 `network` 표시 테스트(로컬 전용) 1개를 둔다: MU 수집 결과의 항목 이름·상태·kind
- [x] T010 [US1] `COL` 국내 수집과 요청 함수 이동.
  - `collect_kr(sym)`이 받는 항목:
    - `naver_integration`: 응답 JSON 전체
    - `wisereport_eps`: `kind: table`, `{"headers": [...], "rows": [[...]]}`. HTML은 저장하지 않는다
    - `daum_days`: 응답 `data` 행 목록
    - `pykrx_fundamental`: `KRX_ID`·`KRX_PW`가 있을 때만 받는다. 해당 종목 행과 기준일을 저장하고, 없으면 `skipped`다
  - `FA/scripts/data_checks.py`의 `fetch_daum_days`, `fetch_daum_index_days`, `fetch_naver_fchart`, `fetch_nasdaq_history`를 `COL`로 옮긴다. 해석 함수 `daum_frame` 등은 `data_checks.py`에 남긴다.
  - `FA/scripts/check_data_sources.py`와 `tests/test_data_checks.py`의 import를 고친다. `TCO`에 `network` 테스트 1개(000660)를 둔다
- [x] T011 [US1] `COL` 수급·지수·전체 수집.
  - `collect_flows(sym)`은 `naver_trend`를 받는다. 그 `fetched_at` 기준으로 오늘 행이 없는 평일이면 `daum_quote`와 `daum_investor_days`도 받는다. 지금 `fetch_investor_trends_table`의 조건과 같다. 받지 않으면 두 항목은 `status: skipped`다.
  - `collect_indices`는 `GFS`의 `default_benchmarks`·`market_index_for`로 지수 목록을 정하고 다음을 받는다.
    - `history`: `period='1y'`
    - `daum_index_days`: `^KS11`·`^KQ11`만
  - `collect_all(args)`는 종목 순서대로 모두 부르고 `meta`를 만든다(data-model §1). `format_version: 2`, `collected_at`(수집 완료 시각, 초), `generated_at`(같은 시각의 `%Y-%m-%d %H:%M KST`), `args`, `versions`, `repo_commit`이 들어간다. T003에서 고친 `collect_meta`를 `GFS`에서 `COL`로 옮기고(`datetime.now`·`git` 호출이 수집에만 남도록, T008), `tests/test_snapshot.py`의 `from get_financial_stats import collect_meta`를 `collect`로 고친다. 수집 함수는 `warn`을 부르지 않는다(R6)

### 정제·계산·출력 (`GFS`)

- [x] T012 [US1] `GFS` 종목 정제를 원자료 기반으로 바꾼다(research R5·R6).
  - `get_stats(sym)`을 `refine_ticker(sym, raw)`로 바꾼다. `yf.Ticker`·`t.xxx`·`requests.get` 대신 `RAW`로 읽는다.
  - 처리 순서와 `warn` 위치·문장은 지금과 같아야 한다. `status: error` 항목은 지금 `except` 자리의 문장을 저장된 `error` 글자로 만든다. 예: `"{sym}: 네이버 API 오류 ({error})"`, `"{sym}: 가격 이력 조회 실패 ({error})"`.
  - 바꿀 함수:
    - `enrich_korean_stock`: `naver_integration`·`wisereport_eps`·`pykrx_fundamental` 항목을 읽는다
    - `fetch_wisereport_ntm_eps` → `parse_wisereport_eps(table, today)`: `today` = `wisereport_eps.fetched_at`의 날짜
    - `enrich_global_stock`: `compute_ntm_eps(today=info.fetched_at 날짜)`
    - `check_krx_history`: `daum_days` 항목을 `data_checks.daum_frame`으로 바꾼다
    - `check_statement_lag`, `fetch_estimates`, `analyze_cycle`, `compute_pb_band`, `audit_unusual_items`: 원자료 표를 읽는다
- [x] T013 [US1] `GFS` 표 생성 중 접속·시각 제거.
  - `fetch_investor_trends_table`은 `naver_trend`·`daum_quote`·`daum_investor_days` 항목을 읽는다. `now_kst`는 `naver_trend.fetched_at`이다.
  - `market_context_table`은 `yf.Ticker(b).history` 대신 지수 `history` 항목을 읽는다. `check_krx_index`는 `daum_index_days` 항목으로 하되, 지금과 같은 자리(시장 비교 표 안)에서 실행한다.
  - `earnings_dates(info, now)`: `now` = `info.fetched_at`
  - `data_basis_block`: 생성 시각 = `meta.collected_at`
- [x] T014 [US1] `GFS` 생성 경로(research R7, contracts §1).
  - `reset_state()`는 `WARNINGS`·`HISTORY`·`SNAP`을 비운다.
  - `build_section4(raw, meta, options)`는 지금 `generate_report`의 본문(종목 정제 → 순환 지정 → 표 → 경고 섹션)을 옮긴 순수 함수다. `options`는 `tickers`·`cyclical_add`·`cyclical_remove`·`benchmarks`·`weights`다.
  - `main`의 순서: `COL.collect_all`(함수 안 import) → `RAW.dumps`/`loads` 왕복 → `build_section4` → `--snapshot`이면 `meta`·`inputs`·`values`·`series`·`warnings`를 한 번에 저장. 저장 실패 시 경고하고 계속하는 동작은 그대로다.
  - *(결과 2026-10-20 19:02 KST)* 새 코드로 4개 종목 실제 수집(12.9초, 스냅샷 2.39MB) → 같은 스냅샷으로 `build_section4` 재실행: Section 4·values 646개·warnings 17개 모두 같음. 분리 전 코드(18:49) 기준과 판정 기호 행 23줄 같음(나머지 22줄은 13분 사이 데이터 변화: 시가총액, 장중 추정). 지수 목록은 `sorted()`로 순서를 고정(분리 전에는 집합 순서라 프로세스마다 경고 순서가 달라질 수 있었음)
  - `tests/test_snapshot.py`에서 `yf`·`requests`를 흉내 내던 테스트(`generate_report`, `check_krx_history`, `fetch_investor_trends_table`)를 합성 원자료 기반으로 바꾼다. 검사 내용(기록 경로·값·상태)은 유지한다. 이 작업 뒤 T008이 통과해야 한다
- [x] T015 [US1] 시험 스냅샷 `FX`(research R14, 로컬 실행).
  - 장중에 `get_financial_stats.py --tickers 000660.KS,005930.KS,MU,TSM --snapshot`으로 받는다. 표준 출력에 `snapshot.section4_body`를 적용하고 `attach_section4`로 기준본을 덧붙여 `FX/snapshot_data.json`을 만든다.
  - `FX/README.md`에 적을 내용: 수집 시각, 코드 커밋, 라이브러리 버전, 파일 크기, "테스트 자료 — 기업별 결론을 위키에 넣지 않음(헌법 VI)".
  - 크기가 SC-007(10MB 이하)을 넘으면 멈추고 보고한다
  - 버전 고정(plan 위험 표): `tests/requirements-pinned.txt`에 `FX` `meta.versions`의 pandas·numpy를 `==`로 적는다. `.github/workflows/ci.yml` 테스트 단계와 `CLAUDE.md`의 테스트 명령 두 줄에 `--with-requirements tests/requirements-pinned.txt`를 추가한다. `TRB`에 테스트를 둔다: 고정 파일의 버전이 `FX`의 `meta.versions`와 같다(다르면 "버전을 올렸다면 시험 스냅샷을 다시 만드세요" 메시지로 실패)
  - *(결과 2026-10-20)* 장 마감 후 19:02 수집본으로 만듦(계획의 "장중"과 다름): 네이버 수급에 당일 행이 없어 다음 금융 장중 조회가 실제로 들어 있어 '장중 잠정' 경로를 시험할 수 있다. 진짜 장중 수집본 확인은 T019에서. 1.15MB(들여쓰기 없는 JSON, 원본 2.39MB), 고정 버전 pandas 3.0.6·numpy 2.5.4

### 재현 도구 (`RB`)

- [x] T016 [US1] `RB` 확인 모드(contracts §2, data-model §5, research R8·R9).
  - 인자: `SNAPSHOT`, `--json`, `--print`, `--verbose`. Windows 콘솔 UTF-8 출력은 `GFS`와 같은 처리(`stream.reconfigure`)
  - `rebuilt_at`(실행 기록용 현재 시각)은 `if __name__ == "__main__":` 진입부에서 구해 넘긴다. 비교 함수는 시각을 읽지 않는다(T008)
  - 읽기 오류는 종료 코드 2: `unreadable`, `legacy_format`(안내 문구는 contracts 그대로), `missing_input`(경로 포함), `invalid_input`
  - `build_section4`를 `meta.args`의 옵션으로 실행하고 세 가지를 비교한다.
    - Section 4: 기준본이 있을 때 `section4_body` 결과와 줄 단위
    - `values`: 경로별로 정확히 같은지, 바뀜·새로 생김·없어짐
    - `warnings`: 순서 포함
  - `meta.versions`와 지금 버전이 다르면 `version_warnings`에 넣는다(비교는 계속한다).
  - 요약 출력 형식은 contracts §2 그대로다. 종료 코드는 0(모두 같음), 1(차이), 2(위 오류). 스냅샷 파일은 읽기만 한다
- [x] T017 [US1] `TRB` 재현 테스트(SC-001·002·003·006, FR-008·010). `FX`로 다음을 확인한다.
  - `RB`가 종료 코드 0을 내고, Section 4·values·warnings가 같다
  - 소켓 연결(`socket.socket.connect`)과 `GFS`의 `datetime` 시각 함수를 예외로 막아도 성공한다
  - `values`의 숫자 하나를 바꾸면 종료 코드 1이고, 출력에 경로·저장값·재계산값이 있다
  - `inputs.MU.quarterly_balance_sheet`를 지우면 종료 코드 2와 `missing_input`, 경로가 나온다
  - `tests/fixtures/002/report_data.json`이면 종료 코드 2와 `legacy_format`이 나온다
  - 실행 시간이 10초 미만이다
  - 실행 전후 스냅샷의 SHA-256이 같다
  - 장중 수집본이면 수급 표에 '잠정' 표시가 그대로 있다
  - 수집 실패 재현(US1 시나리오 5, FR-007 뒷부분): `FX` 복사본에서 `inputs.000660.KS.naver_trend`를 `{"status": "error", "error": "timeout"}`으로 바꾸고 `build_section4`를 두 번(생성 경로 왕복, 재현 경로) 실행하면 두 결과가 같고, 경고에 `"네이버 수급 API 오류 (timeout)"`이 들어 있으며 1-1 수급 표에서 해당 종목이 빠진다
  - 버전 경고(FR-013): `FX` 복사본의 `meta.versions.pandas`를 다른 값으로 바꾸면 `version_warnings`에 그 차이가 나오고, 종료 코드는 비교 결과(0)를 그대로 따른다

### 분리 전후 같음 (FR-014)

- [x] T018 [US1] 재생 비교 도구 `tests/tools/replay_main.py`(research R12, quickstart 6).
  - 인자: `--main <worktree>`, `--snapshot`, `--out`
  - 분리 전 코드의 `get_financial_stats.generate_report`를 같은 프로세스에서 실행한다. 이때 `yf.Ticker`는 스냅샷 `inputs`를 돌려주는 가짜로 바꾼다(`info`, `history`(기간 인자 무시), 재무제표·컨센서스 속성, `_quote._info`). `requests.get`은 URL 패턴별로 해당 항목 JSON 또는 WiseReport HTML을 재구성해 돌려준다. `datetime`은 원자료의 받은 시각으로 고정한다(재생용 스냅샷은 받은 시각을 하나로 맞춘다).
  - `--out`에 Section 4를 쓰고, `RB --print` 결과와 `diff`한다. 차이 줄 수와 각 원인을 이 작업 아래에 기록한다. 0줄이 목표이고, 남는 차이는 원인과 판정 영향 여부를 적는다
  - *(결과 2026-10-20)* `main` a82a5b7(별도 worktree)에 `tests/fixtures/003/snapshot_data.json`(받은 시각을 수집 완료 19:02:37로 통일)을 재생: 분리 전 305줄 · 분리 후 305줄 · **다른 줄 0**. 경고 17개의 문장·순서, 장중 잠정 행, 판정·종합 판단 모두 같음
- [x] T019 [US1] SC-001 로컬 확인. 장중 수집본과 장 마감 후 수집본을 각각 다른 날 네트워크를 끊고 `RB`로 다시 만들어 종료 코드 0인지 확인한다. 결과(수집·재현 시각, 종료 코드, 실행 시간, 스냅샷 크기)를 이 작업 아래에 기록한다
  - *(진행 2026-10-20)* S1(NXT 거래 중 19:57 수집, 2.39MB) → 거래 종료 후 20:05 재현: 종료 코드 0, Section 4 305줄·values 646·경고 17 같음, '장중 잠정' 행 유지. S2(거래 종료 후 20:05 수집)와 시험 스냅샷(19:02)은 다음 날 재현 예정. 보관: `~/.cache/value-chain-analysis/verify003/`
  - *(결과 2026-10-21 14:07 KST, 다음 날·정규장 중, 소켓 연결 차단)* S1(10-20 19:57 NXT 거래 중 수집)·S2(10-20 20:05 거래 종료 후)·시험 스냅샷(10-20 19:02) 모두 종료 코드 0 — Section 4 305줄이 수집 당일 출력과 같고, values 646·경고 17 같음. 시험 스냅샷 재현 1.05초
  - *(결과 2026-10-21)* S3(KRX 정규장 중 14:08 수집, "정규장 진행 중"·'장중 잠정') → 15:40 이후 15:47 재현(소켓 차단): 종료 코드 0, Section 4 307줄 같음, values 649·경고 19 같음, 시장 상태·잠정 표기 그대로

**Checkpoint**: 새 보고서의 Section 4를 언제든 네트워크 없이 같게 다시 만들고, 바뀐 계산값·빠진 원자료·이전 형식을 구분해 알린다. 분리 전 코드와의 재생 비교 결과가 기록되어 있다.

---

## Phase 4: User Story 2 - 같은 입력으로 규칙 변경 전후 비교 (Priority: P2)

**Goal**: 같은 스냅샷에서 코드가 바뀐 영향만 드러나고, 계산값 변화와 글자 변화를 구분한다.

**Independent Test**: 기준값 하나만 바꾼 코드로 `FX`를 다시 만들면, 차이가 그 기준값의 영향 범위 안에만 있다.

- [x] T020 [US2] `TRB` 영향 범위 테스트(SC-005, US2 시나리오 1·2).
  - 같은 코드로 두 번 만들면 차이가 0줄이다.
  - `GFS.THRESHOLDS['fpe']`를 바꿔 만들면, Section 4의 차이 줄이 모두 허용 목록 안에 있어야 한다.
    - 4·5번 매트릭스에서 해당 종목 행
    - 4·5번 표 아래 판정 기준 설명 줄
  - `values`의 차이 경로도 허용 목록 안에 있어야 한다: `rules.forward_pe.*`
  - 허용 목록 밖 차이가 하나라도 있으면 실패한다
  - *(결과 2026-10-20)* `fpe` (18,30)→(10,15): Section 4 4줄(TSM 4·5번 행, 기준 설명 2줄)·values 2개(`rules.forward_pe.*`)만 다름, TSM 4번 종합 🟢→🟡
- [x] T021 [US2] `RB` 차이 구분(US2 시나리오 3).
  - Section 4는 다르지만 `values`·`warnings`가 같으면 요약에 "계산 결과 같음, 글자만 다름"을 표시한다. JSON에서는 `section4.cause: "text_only"`다.
  - `values`가 다르면 `"values"`다.
  - `TRB` 테스트: 출력 형식 함수(예: `fmt_signed_pct`의 자릿수)만 바꾼 경우는 `text_only`, 계산을 바꾼 경우는 `values`로 나오는지 확인한다
- [x] T022 [P] [US2] 규칙 변경 전후 비교 방법을 문서에 적는다.
  - `FA/references/rules/data-snapshot.md`의 재현 절: 같은 스냅샷으로 `main` worktree와 작업 브랜치에서 `RB --print`를 실행해 `diff`하는 방법
  - `CLAUDE.md` 규칙 1(기준값 변경)에 "같은 스냅샷으로 전후 Section 4를 비교해 PR에 적는다"를 추가한다

**Checkpoint**: 판정 규칙을 바꾸는 PR이 시세 변동 없이 차이를 정확히 보여 준다.

---

## Phase 5: User Story 3 - 수집 없이 분석 옵션만 바꿔 다시 계산 (Priority: P3)

**Goal**: 시나리오 확률과 순환업종 지정만 바꿔 별도 파일로 다시 계산하고, 원본은 그대로 둔다.

**Independent Test**: `FX`에 `--weights 0.1,0.5,0.4 --out <새 파일>`을 실행한다. 결과 파일 머리와 시나리오 부분만 원래 Section 4와 다르고, 원본 SHA-256이 같으며, 같은 `--out`으로 다시 실행하면 거부된다.

- [x] T023 [US3] `TRB` 옵션 재계산 테스트(US3 시나리오 1~3, Clarifications Q1).
  - `--weights` 변경: 원래 Section 4와 다른 줄이 다음뿐이다.
    - 재계산 머리 2줄
    - 7번 시나리오 확률 설명 줄
    - 확률가중 기대값 행
  - 같은 경우 `values` 차이 경로가 다음 안에만 있다: `rules.scenario.weight_*`, `*.scenario.expected_price_*`, `*.scenario.return_expected_*`
  - `--cyclical`에 스냅샷에 없는 종목, 또는 `--tickers`·`--benchmarks` 같은 허용하지 않는 옵션 → 종료 코드 2와 `option_needs_data` / `option_rejected`
  - 이미 있는 `--out` → `output_exists`
  - `--out` 없이 옵션만 주면 → 인자 오류(2)
  - 모든 경우에 원본 스냅샷 SHA-256이 그대로다
- [x] T024 [US3] `RB` 재계산 모드(contracts §2).
  - `--weights`·`--cyclical`·`--not-cyclical`은 `--out`이 있을 때만 받는다. `--weights`는 `GFS.parse_weights` 규칙으로 검사한다.
  - `meta.args`에 옵션을 덮어써 `build_section4`를 실행한다.
  - `--out`에는 contracts의 "재계산 결과 파일 머리" 2줄(원본 경로, SHA-256 앞 8자리, 수집 시각, 바꾼 옵션 `이전 → 이후`, "데이터는 다시 받지 않았습니다")과 Section 4를 쓴다.
  - JSON에는 `mode: "recompute"`, `options_changed`, 바뀐 `values` 목록을 넣는다. 저장 성공 시 종료 코드 0이다

**Checkpoint**: 같은 데이터로 가정만 바꿔 본 결과가 '보고서 아님' 표시와 함께 별도 파일로 남는다.

---

## Phase 6: Polish & Cross-Cutting

- [x] T025 [P] 규칙 원본 `FA/references/rules/data-snapshot.md`에 재현 절을 마무리한다: `RB` 사용법, 종료 코드 0/1/2와 오류 코드 7종(data-model §5), 옵션 재계산 범위, 코드 검사 테스트가 금지하는 것(R11)
- [x] T026 [P] 스킬·저장소 문서.
  - `FA/SKILL.md`:
    - Resources에 `rebuild_section4.py`·`collect.py`·`raw_inputs.py`를 추가한다
    - `--snapshot` 설명을 고친다: 원자료와 받은 시각, 재현 가능
    - 버전을 3.4.0으로 올린다
  - `README.md`: 디렉토리 구조, financial-analyst 기능, 변경 이력
  - `ROADMAP.md`: 3단계 상태
  - `CLAUDE.md`:
    - 명령에 재현 확인 추가
    - `tests/` 설명에 `fixtures/003`·`tools/replay_main.py` 추가
- [x] T027 [P] 결정 기록 `docs/decisions/0006-pipeline-split.md`. 다룰 내용:
  - 원자료를 저장하고 정제를 다시 실행하는 이유(R5)
  - 원자료별 받은 시각(R4)
  - 표 형식에 자료형·시간대·정밀도를 넣은 이유(R3)
  - 계산·출력 모듈 분리를 미룬 이유와 다시 판단할 조건(plan Complexity Tracking)
  - `meta.generated_at`의 뜻 변경
- [x] T028 quickstart.md 단계 1~8을 실행하고, 결과(종료 코드·차이 줄 수·실행 시간·스냅샷 크기)를 이 작업 아래와 PR 본문에 기록한다
  - *(완료 2026-10-21)* 2: 다음 날 재현 — T019 결과(수집 다음 날 3개 스냅샷 모두 0). 그 밖의 단계는 아래 기록 그대로
  - *(진행 2026-10-20 장 마감 후)* 1: 오프라인 259 통과·건너뜀 0(Python 3.12·3.13), network 5 통과. 2: 같은 날 생성 직후 재현 0(다음 날·장중은 T019). 3·4: 테스트로 확인(변조 1, 원자료 삭제 2·경로, 이전 형식 2). 5: `--weights 0.1,0.5,0.4` → 0, 바뀐 값 18개 모두 시나리오 범위, 같은 `--out` 재실행 2. 6: 재생 비교 0줄. 7: 스냅샷 2.39MB(4종목, 들여쓰기 2칸), 재현 1.2초. 8: `generate_strategy_report.py`(000660.KS, MU) → 재현 0(기준본 244줄·values 357·경고 6), 숫자 점검 1(`[AI_TODO]` 32건뿐, Section 4 변경 0·스냅샷 누락 0·경고 누락 0)
- [x] T029 판정 불변 확인(헌법 V, SC-004).
  - 같은 시각에 `main`(별도 worktree)과 이 브랜치로 `000660.KS,005930.KS,MU,TSM` Section 4를 만들어, 판정 기호가 있는 행과 종목별 종합 판단이 100% 같은지 비교한다.
  - T002 기준과도 비교하고, T018 재생 비교 결과와 함께 PR에 적는다
  - *(결과 2026-10-20)* `main` 19:13:17 · 이 브랜치 19:13:29 실행(장 마감 후): Section 4 전체가 같음(다른 줄 0, 판정 기호 행 23줄 포함). T002 마감 후 기준(18:49)과도 판정 행 같음. 종합: 000660.KS·005930.KS·MU 🟡 중립/관망(주의 1), TSM 🟢 강력 매수 후보. T018 재생 비교도 0줄
- [x] T030 마무리.
  - CI 통과를 확인한다: 문법 검사, 테스트, 위키 근거 대조.
  - `pytest -rs` 출력에서 003 테스트와 002 `test_validation_set`이 건너뛰어지지 않았는지 확인한다. 건너뛰었으면 PR을 열지 않는다.
  - `checklists/requirements.md`와 spec·plan Status를 갱신하고 PR을 연다
  - *(결과 2026-10-22)* PR #9(구현)·#10(부동소수점 허용 오차)·#12(마감) 병합. #12 CI 성공, main CI 성공(d6fc32b). 오프라인 261 통과·건너뜀 0(macOS arm64, x86_64 Linux Docker), 위키 근거 대조 0건. 체크리스트 16/16, spec·plan Status Implemented

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3(US1, MVP) → Phase 4·5 → Phase 6
- T001(승인) 전에는 구현을 시작하지 않는다. T002(네트워크, 장중·마감 후)와 T003은 T001 이후 병렬로 할 수 있다
- Phase 2: T004 → T005(같은 `RAW`). T006·T007은 T004·T005와 병렬로 할 수 있다
- US1:
  - T008(실패 확인)
  - 수집: T009 → T010 → T011(같은 `COL`)
  - 정제: T012 → T013 → T014(같은 `GFS`, T005·T011 필요). T014 뒤 T008 통과
  - T015(T014 필요, 장중 실행)
  - T016 → T017(T015 필요)
  - T018(T002·T015·T016 필요)
  - T019(T016 필요, 다른 날 두 번)
- US2: T020·T021은 T017 이후(같은 `TRB`, 순서대로). T022는 병렬로 할 수 있다
- US3: T023 → T024. US2와 독립이지만 같은 `RB`·`TRB` 파일을 고치므로 번갈아 커밋한다
- Phase 6: T025~T027은 병렬로 할 수 있다. T028·T029는 US1~US3 이후, T030이 마지막

## Parallel Opportunities

- Setup: T002(분리 전 코드 실행)와 T003(`GFS` 메타 수정). T003은 T012~T014와 같은 파일이므로 T012 전에 끝낸다
- Foundational: `RAW`(T004·T005), `snapshot.py`(T006), 규칙 문서(T007)
- US1 안: 수집 갈래(T009~T011, `COL`)와 정제 갈래의 준비(T012의 원자료 읽기는 T005만 필요)는 다른 파일이다. 단, T012의 실행 확인에는 T011의 실제 수집 결과가 필요하다
- US2 vs US3: 테스트 파일이 같아 번갈아 진행한다. 문서 작업(T022)은 독립이다

```text
# 예: Foundational 이후 두 갈래
갈래 1: T009 → T010 → T011                (collect.py, test_collect.py)
갈래 2: T008 → T012 → T013 → T014         (test_rebuild.py, get_financial_stats.py, test_snapshot.py)
합류:   T015 → T016 → T017 → T018 → T019
```

## Implementation Strategy

1. **MVP (Phase 1~3)**: 외부 접속이 수집 한 곳으로 모이고, 스냅샷만으로 Section 4를 같게 다시 만든다. 이것만으로 로드맵 3단계의 완료 기준을 충족한다. 재생 비교(T018)로 분리 전후가 같은지 확인한다.
2. **US2**: 판정 규칙을 바꾸는 이후 작업(4단계 공식 출처 전환, 보류 중인 사이클 판정 개선)의 검증 방법이 된다.
3. **US3**: 같은 데이터로 가정만 바꿔 보는 부가 기능이다.
4. 각 단계가 끝날 때 CI를 통과시키고, 판정에 영향이 있으면 PR에 원인을 적는다.
