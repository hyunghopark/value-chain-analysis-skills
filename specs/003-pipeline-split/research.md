# Research: 수집·정제·계산·출력 분리

**Date**: 2026-10-19 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

측정은 2026-10-19 로컬(macOS, yfinance 1.4.x, pandas 3.0.x)에서 했다. 측정 스크립트는 세션 임시 폴더에서 실행했고 저장소에 넣지 않았다(결과 수치만 기록).

## R1. 외부 접속과 현재 시각을 읽는 곳 (전수 조사)

`get_financial_stats.py`(2,207줄)·`data_checks.py`·`snapshot.py`를 전부 읽어 외부 접속과 시각 읽기를 모두 찾았다.

| 위치 | 하는 일 | 지금 단계 | 바뀐 뒤 |
|---|---|---|---|
| `get_stats` → `yf.Ticker(s).info` (실패 시 `_quote._info`) | Yahoo 요약 정보 | 수집 | 수집: `info` |
| `get_stats` → `t.history(period='5y')` | 5년 일별 시세 | 수집 | 수집: `history` |
| `check_statement_lag` → `t.income_stmt`, `t.quarterly_income_stmt` | 재무제표 지연 경고(KI-003) | 수집+정제 섞임 | 수집: 표 저장 / 정제: 경고 |
| `fetch_estimates` → `t.earnings_estimate`, `eps_trend`, `eps_revisions`, `earnings_history` | 컨센서스 표 | 수집+정제 | 수집 / 정제: ADR 단위 보정 |
| `enrich_global_stock` → `t.earnings_estimate` | 해외 NTM EPS | 수집+계산 | 수집(같은 표 재사용) / 계산 |
| `analyze_cycle` → `t.income_stmt` | 사이클 진단 | 수집+계산 | 계산 |
| `compute_pb_band` → `t.balance_sheet`, `t.quarterly_balance_sheet` | P/B 밴드 | 수집+계산 | 계산 |
| `audit_unusual_items` → `t.quarterly_income_stmt`, `t.quarterly_balance_sheet` | 일회성 손익 감사 | 수집+계산 | 계산 |
| `enrich_korean_stock` → 네이버 `integration` | 국내 지표 덮어쓰기 | 수집+정제 | 수집: 응답 JSON / 정제: 덮어쓰기 |
| `fetch_wisereport_ntm_eps` → WiseReport HTML | 국내 FY0·FY1 EPS | 수집+정제+계산 | 수집: 표 머리·셀 / 정제: 표 구조 검사(KI-004) / 계산: NTM |
| `enrich_korean_stock` → `pykrx` (환경 변수 있을 때만) | KRX 지표 보완 | 수집+정제 | 수집: 해당 종목 행 / 정제 |
| `check_krx_history` → 다음 `quote/A{code}/days` | 거래소 종가 대조(KI-002·006) | 수집+정제 | 수집: 응답 행 / 정제 |
| **`fetch_investor_trends_table`** → 네이버 `trend`, 다음 `quotes`, 다음 `investor/days` | 수급 표 | **표 생성 중 수집** | 수집: 응답 JSON / 정제·계산·출력 |
| **`market_context_table`** → `yf.Ticker(b).history('1y')`, 다음 `market_index/days` | 지수 시세, 지수 대조 | **표 생성 중 수집** | 수집 / 정제 |
| `compute_ntm_eps`, `fetch_wisereport_ntm_eps` → `date.today()` | NTM 가중, FY 연도 | 계산 | 원자료의 받은 시각 |
| `enrich_korean_stock` → `datetime.today()` (pykrx 날짜 역산) | 최근 영업일 찾기 | 수집 | 수집에 남음(수집 단계는 시각을 읽어도 된다) |
| `earnings_dates` → `datetime.now()` | 지난·다음 실적 발표일 | 계산 | `info`의 받은 시각 |
| `fetch_investor_trends_table` → `datetime.now(KST)` | 당일 행 판단, 15:40 장 마감, 평일 여부 | 수집+정제 | 네이버 `trend`의 받은 시각 |
| `data_basis_block` → `datetime.now(KST)` | "데이터 기준 … 생성" 시각 | 출력 | 수집 완료 시각(`meta.collected_at`) |
| `collect_meta` → `datetime.now(KST)`, `git rev-parse` | 메타 | 수집 | 수집 |
| `snapshot.attach_section4` → `datetime.now` | 기준본 덧붙인 시각 | 보고서 생성 | 그대로(Section 4 글자에 들어가지 않음) |

- **Decision**: 외부 접속과 시각 읽기는 모두 새 수집 모듈로 옮긴다. 정제·계산·출력은 스냅샷에서 읽은 원자료와 그 원자료의 받은 시각만 쓴다.
- **Rationale**: 표 생성 중 접속 2곳과 시각 읽기 5곳이 "같은 스냅샷 → 같은 Section 4"를 막는 원인 전부다.

## R2. 원자료 저장 범위와 크기

4개 종목(000660.KS, 005930.KS, MU, TSM)과 지수 3개(^KS11, ^GSPC, ^SOX)의 원자료를 실제로 받아 JSON 크기를 쟀다(수집 9.6초).

| 항목 | 종목당 크기(KB, 들여쓰기 없음) |
|---|---|
| Yahoo `info` | 7.5~8.3 |
| 5년 일별 시세(8열) | 한국 127~129, 미국 182 |
| 재무제표 4종(연간·분기 손익, 연간·분기 재무상태) | 26~34 |
| 컨센서스 표 4종 | 1.4~1.5 |
| 네이버 `integration` / `trend` | 10.1 / 3.7 (한국만) |
| 다음 일별 시세 100행 | 8 (한국만) |
| 지수 1년 시세 | 33~35, 다음 지수 6.3 |
| **합계** | **들여쓰기 없음 0.86MB, 들여쓰기 2칸 1.66MB** |

- **Decision**: 계산이 읽는 원자료는 **통째로** 저장한다. Yahoo `info` 전체, 시세 이력 전체 열, 재무제표·컨센서스 표 전체, 네이버·다음 응답 JSON 전체다. WiseReport는 HTML 대신 표 머리와 셀 글자를 저장한다. 기존 `values`·`series`(약 0.27MB)는 그대로 둔다. 예상 스냅샷 크기는 4개 종목 기준 약 2MB이고, SC-007의 10MB 이하를 충족한다.
- **Rationale**: 필요한 키만 골라 저장하면, 계산 코드가 새 키를 읽기 시작할 때 다시 누락이 생긴다(001의 '정해진 키 목록' 누락과 같은 실패). 표 전체를 저장해도 크기가 작다. 시세 이력의 Open·High·Low도 저장한다. `reconcile_history`가 빈 날을 채울 때 다섯 열을 모두 쓰기 때문이다.
- **Alternatives**: 계산에 쓰는 열·키만 저장 → 크기를 약 40% 줄이지만 누락 위험이 커 버렸다. HTML 원문 저장 → WiseReport 한 쪽에 수백 KB이고 파싱 결과와 차이가 없어 버렸다.

## R3. DataFrame 저장 형식 (값이 바뀌지 않게)

JSON으로 썼다 읽은 DataFrame이 원래와 같은지 실제 자료 28개 표(4종목 × 시세·재무제표 4종·컨센서스 4종, 지수 1개)로 확인했다.

- 1차 시도(인덱스를 문자열로만 저장): 값·열 자료형은 모두 같았지만 9개 표가 달랐다. 원인은 세 가지였다. 날짜 정밀도(`datetime64[s]` → `[us]`), 문자열 인덱스 자료형(`str` → `object`), 인덱스 이름(`Date`, `period`)이 빠졌다. RSI 계산(`ewm`) 결과는 그래도 같았다.
- 2차 시도(인덱스·열마다 종류, 시간대 이름, 날짜 정밀도, 자료형, 이름을 함께 저장): **28개 중 28개가 같았다**. `DataFrame.equals`, 인덱스·열 자료형, 이름까지 모두 일치했다.
- **Decision**: 표는 `{"index": 인덱스 정보, "columns": 열 정보, "dtypes": [...], "data": [[...]]}`로 저장한다([data-model.md §2](data-model.md#2-원자료-표-형식)). 시간대는 `+09:00` 같은 고정 오프셋이 아니라 `Asia/Seoul`처럼 **이름**으로 저장한다. 날짜는 시간대를 뺀 현지 시각으로 저장한다. 결측(NaN)은 `null`로 쓰고 읽을 때 자료형으로 되돌린다.
- **Rationale**: 고정 오프셋으로 저장하면 미국 서머타임 앞뒤의 오프셋이 섞여 시간대 정보가 망가진다. UTC로 바꾸면 한국 자정이 전날 15:00이 되어 날짜가 하루 밀린다. Python `json`의 실수 표기는 왕복해도 값이 정확히 같다.

## R4. 시각: 원자료마다 받은 시각

- **Decision**: 원자료 항목마다 받은 시각 `fetched_at`(초 단위, KST, 시간대 포함 ISO 형식)을 둔다. 시각이 필요한 계산은 **그 원자료의** 받은 시각을 쓴다.

  | 계산 | 쓰는 시각 |
  |---|---|
  | 수급 표의 '오늘' 판단, 15:40 장 마감, 평일 여부 | 네이버 `trend` |
  | 실적 발표일 | Yahoo `info` |
  | NTM 가중 | 국내는 WiseReport 표, 해외는 Yahoo `info` |

  표 머리의 생성 시각은 수집 완료 시각 `meta.collected_at`이다.
- **Rationale**: 지금 코드도 각 값을 받은 직후의 시각으로 판단한다. 시각을 하나로 통일하면 15:39에 시작해 15:41에 수급을 받은 실행의 판정이 지금과 달라진다. 원자료별 시각이 지금 동작과 가장 가깝다.
- **Alternatives**: 수집 시작 시각 하나 → 위 경계 사례에서 판정이 달라져 버렸다.

## R5. 정제를 다시 실행할 것인가, 정제 결과를 저장할 것인가

- **Decision**: 스냅샷에는 **원자료**를 저장한다. 다시 만들 때 정제(덮어쓰기, KI 교정, 출처 간 대조, 경고)도 원자료에서 같은 규칙으로 다시 실행한다. 정제 결과(교정 값과 `original`·`ki`)는 지금처럼 `values`에 남는다. 다시 만들 때 나온 정제 결과는 저장값과 비교한다(FR-006).
- **Rationale**:
  - 정제 함수는 모두 원자료와 받은 시각만으로 결과가 정해진다(R1).
  - 원자료를 남기면 교정 전 값까지 그대로 보존된다(헌법 II).
  - 데이터 품질 규칙(KI) 변경도 같은 스냅샷으로 전후를 비교할 수 있다(US2의 범위가 넓어진다).
  - 정제가 끝난 `info`를 따로 직렬화하는 두 번째 형식이 필요 없다.
- **Alternatives**: 정제 결과만 저장하고 다시 만들 때 정제를 건너뜀 → 원래 값이 사라지고, 정제 코드가 바뀌어도 알 수 없어 버렸다.
- **Spec 조정**: 이 결정에 맞춰 spec의 FR-002와 Edge Case '교정·보완 값'을 "원자료를 저장하고, 정제는 다시 실행해 저장된 교정 기록과 같아야 한다"로 고쳤다.

## R6. 경고 문장과 순서까지 같게

- 지금 경고는 실행 순서대로 쌓인다. 종목별 수집·정제·사이클·감사가 먼저 오고, 그다음 표 함수 순서(수급 → 기술 → 시장 비교 → …)다. 수집 실패 경고에는 예외 메시지(`{e}`)가 들어간다.
- **Decision**:
  - 수집 단계는 경고를 내지 않는다. 대신 실패를 원자료 항목에 `status: "error"`와 `error`(예외 메시지 글자)로 기록한다.
  - 지금 경고를 내는 바로 그 자리에서 정제 단계가 저장된 `error`로 같은 문장을 만든다.
  - 정제·계산·출력은 지금과 같은 순서로 실행한다.
- **Rationale**: 경고 순서가 수집 순서가 아니라 코드 순서로 정해지므로, 같은 원자료면 문장과 순서가 같다. 지금 코드와 같은 순서를 지키면 분리 전후 Section 8도 같게 나와야 한다(R12에서 확인).

## R7. 생성과 재현이 같은 길을 쓰게 (FR-009)

- **Decision**: `get_financial_stats.py`의 처리 순서는 다음과 같다.
  1. 수집해 원자료를 만든다.
  2. 원자료를 JSON 글자로 바꿨다가 다시 읽는다. 파일에서 읽는 것과 같은 함수를 쓴다.
  3. 다시 읽은 원자료로 정제·계산·출력을 실행한다.
  4. `values`·`warnings`를 채워 스냅샷을 한 번 저장한다.

  `--snapshot`이 없어도 2번 왕복은 한다.
- **Rationale**: 생성할 때 메모리의 DataFrame을 그대로 쓰면, 저장 형식 오류(R3)가 생성 때는 숨고 재현 때만 드러난다. 같은 길이면 SC-001이 구조적으로 보장된다.

## R8. 계산 결과 비교 (FR-006)

- **Decision**: 다시 만들면서 생긴 `values`를 저장된 `values`와 경로 단위로 비교한다.
  - 값이 다른 경로, 새로 생긴 경로, 없어진 경로를 보고한다.
  - 숫자는 **정확히 같아야** 한다. 같은 코드에 같은 입력이면 결과가 같다(R3).
  - `warnings`는 순서를 포함해 비교하고, Section 4는 줄 단위로 비교한다.
- **Rationale**: 허용 오차를 두면 계산 방식 변경(US2)을 놓친다. 표시 반올림이 같아 Section 4 글자는 같지만 값이 다른 경우도 보고되어야 한다(US2 시나리오 3: 계산값과 글자를 구분).
- **구현 후 조정 (2026-10-20, PR #9 병합 후 CI)**: x86_64 CI에서 시험 스냅샷(arm64에서 생성)을 재현하니 기술 지표 7개(RSI, 볼린저 하단, 하단 이탈도)가 마지막 자리에서 달랐다(최대 상대 약 5e-15, Section 4 글자는 같음). Docker로 같은 pandas 3.0.6·numpy 2.5.4를 x86_64·arm64 Linux에서 돌려 원인이 CPU 구조(이동 표준편차·지수이동평균 계산)임을 확인했다. 보고서를 만든 PC와 다시 만드는 PC가 다를 수 있으므로 버전 고정으로는 해결되지 않는다. → 숫자 값은 **상대 1e-9·절대 1e-12** 안이면 같은 값으로 보고, 그런 경로는 `within_tolerance`로 따로 나열한다. 1e-9는 관측 차이보다 약 10⁶배 크고, 표시 자릿수(최대 소수 둘째 자리)나 계산 방식 변경이 만드는 차이보다는 훨씬 작다. Section 4 글자 비교는 그대로 정확히 한다.

## R9. 재현 도구와 옵션 재계산

- **Decision**: 새 스크립트 `rebuild_section4.py`를 만든다. 스냅샷 하나를 받아 Section 4를 다시 만들고, 기준본(`section4.text`)·`values`·`warnings`와 비교한다.
  - **종료 코드**: 0(모두 같음), 1(차이 있음), 2(다시 만들 수 없음: 이전 형식, 입력 누락, 파일 오류, 거부된 옵션).
  - **옵션 재계산**: `--weights`·`--cyclical`·`--not-cyclical`만 받는다(Clarifications Q1). 결과는 `--out`에 지정한 새 파일로 쓰고, 그 파일이 이미 있으면 거부한다. 원본 스냅샷은 읽기만 한다.
  - **기록**: 결과 파일 머리에 원본 스냅샷 경로·SHA-256과 바꾼 옵션을 적고, 보고서가 아니라 재계산 결과라고 표시한다.
- **Rationale**: 002의 `check_report_numbers.py`와 같은 형식(요약, `--json`, 종료 코드)이라 CI와 AI가 같은 방식으로 쓸 수 있다. 수집용 `get_financial_stats.py`에 재현 모드를 넣으면, 한 명령이 네트워크를 쓰기도 하고 안 쓰기도 해서 경계가 흐려진다.
- **Alternatives**: `get_financial_stats.py --from-snapshot` → 위 이유로 버렸다.

## R10. 이전 형식 판별과 002 호환

- **Decision**: 새 스냅샷은 `meta.format_version: 2`와 최상위 `inputs`를 가진다. 버전 표시가 없거나 `inputs`가 없으면 이전 형식이다. 이전 형식이면 재현 도구는 종료 코드 2와 "원자료가 없는 이전 형식"이라는 안내를 낸다. 001·002의 `values`·`series`·`warnings`·`section4`는 형식과 뜻을 바꾸지 않는다.
- **Rationale**: 002 점검 도구는 `values`·`series`·`section4`만 읽으므로, 새 최상위 키가 늘어나도 그대로 동작한다. 002 검증 세트 픽스처(이전 형식)로 계속 확인한다(SC-008).

## R11. "외부 접속 0회, 시각 읽기 0회" 확인 방법 (SC-002)

- **Decision**: 두 가지로 확인한다.
  - **코드 검사 테스트**: 정제·계산·출력 코드에 다음이 없는지 확인한다. 함수 단위로 보고, 수집 모듈과 명령 실행 진입부는 예외로 둔다.
    - 네트워크 라이브러리 import: `requests`, `yfinance`, `bs4`, `pykrx`, `urllib`, `socket`
    - 시각 호출: `datetime.now`, `date.today`, `datetime.today`, `time.time`
  - **실행 테스트**: 소켓 연결과 현재 시각 함수를 막은 상태에서 시험용 스냅샷으로 재현을 실행해 성공하는지 본다.
- **Rationale**: 실행 테스트는 시험 자료가 지나가는 길만 확인한다. 장중 분기처럼 실행되지 않은 코드는 코드 검사가 잡는다.

## R12. 분리 전후 결과 같음 확인 (FR-014, SC-004)

- 002 T037은 `main`과 브랜치를 22초 간격으로 실행해 비교했고, 그 사이 시세 변동으로 2행이 달랐다.
- **Decision**: '재생' 방식으로 확인한다.
  1. 새 수집으로 원자료를 받는다.
  2. 분리 전 코드(`main`, 별도 worktree)를 실행하되, Yahoo·네이버·다음 호출은 같은 원자료를 돌려주는 가짜로 바꾸고, 현재 시각은 원자료의 받은 시각으로 고정한다.
  3. 새 코드의 재현 결과와 Section 4를 글자 단위로 비교한다.

  보조 스크립트는 `tests/tools/replay_main.py`에 둔다. 테스트 수집 대상이 아니며, 로컬에서 수동으로 실행한다. 이에 더해 002와 같은 방식의 같은 시각 실행 비교도 한다.
- **Rationale**: 같은 입력을 양쪽에 넣을 수 있어 차이가 0줄이어야 하고, 차이가 나면 모두 코드 원인이다. SC-004(판정 행 100% 같음)보다 강한 확인이다.
- **재생할 때 받은 시각을 하나로 맞춘다**: 분리 전 코드는 시각을 여러 번 읽으므로, 재생용 원자료는 받은 시각을 모두 같은 값으로 맞춰 만든다.

## R13. 코드 배치

- **Decision**:
  - **새 `collect.py`**: 외부 접속과 시각 읽기를 모두 맡는다. Yahoo·네이버·WiseReport·다음·pykrx를 호출해 원자료와 받은 시각, 실패 기록을 만든다. 다음 금융 요청 함수(`fetch_daum_days` 등)도 `data_checks.py`에서 이쪽으로 옮긴다. 응답을 해석하는 함수(`daum_frame`, `reconcile_history` 등)는 `data_checks.py`에 남긴다.
  - **새 `raw_inputs.py`**: 원자료 저장·읽기와 표 형식 변환(R3)을 맡는다. 원자료가 없으면 빠진 경로를 담은 오류를 낸다.
  - **`get_financial_stats.py`**: 정제·계산·출력 함수를 둔다. `t`(yfinance 객체)와 `requests` 대신 원자료 객체를 받는다. 명령 실행부는 '수집 → 왕복 → Section 4 만들기 → 저장' 순서로 부르고, 기존 명령 인자는 그대로다.
  - **새 `rebuild_section4.py`**: 재현 도구(R9).
  - **전역 상태**: `WARNINGS`·`HISTORY`·`SNAP`은 유지하되, 실행마다 비우는 초기화 함수를 둔다. 재현 도구와 테스트가 한 프로세스에서 여러 번 실행할 수 있게 하기 위해서다.
- **Rationale**: 외부 접속 경계는 모듈 경계로 강제하고 테스트로 확인할 수 있다(R11). 정제→계산은 실행 순서로 나뉜다. 계산→출력의 구분은 계산 결과가 `values`에 전부 기록되므로 값 비교(R8)로 확인한다.
- **Alternatives**: 계산과 출력을 별도 모듈로 나누기(표 함수 15개를 '값 계산'과 '글자 만들기'로 쪼개기) → [plan.md Complexity Tracking](plan.md#complexity-tracking) 참조.

## R14. CI용 시험 스냅샷

- **Decision**: 4개 종목(한국 2, 미국 2)으로 실제 수집한 새 형식 스냅샷을 `tests/fixtures/003/`에 넣는다. 예상 크기는 약 2MB이고, 생성 당시 Section 4 기준본을 포함한다. CI는 이것으로 재현 동일성, 외부 접속·시각 차단, 계산값 변조와 원자료 누락 감지, 옵션 재계산을 시험한다. 장중·마감 후 두 시나리오(SC-001)는 각각의 시각에 수집한 두 벌로 시험한다. 두 벌을 커밋하기 어려우면 장중 한 벌을 커밋하고, 마감 후 한 벌은 로컬에서 확인한다.
- **Rationale**: 합성 자료로는 실제 Yahoo 표의 결측·자료형·시간대 문제(R3)를 재현할 수 없다. 테스트 자료일 뿐이며 기업별 결론은 위키에 넣지 않는다(헌법 VI, 002 검증 세트와 같음).

## R15. 조사 중 발견한 조용한 오류

- `collect_meta`는 `os.path`를 쓰지만 `get_financial_stats.py` 최상위에 `import os`가 없다. 지역 import는 `enrich_korean_stock` 안에만 있다. 그래서 `NameError`가 `except Exception: pass`에 삼켜져 `meta.repo_commit`이 항상 `None`이다. 002 검증 세트 스냅샷도 `None`이다.
- **Decision**: 003에서 고친다(FR-013이 코드 버전 기록을 요구한다). `repo_commit`을 알 수 없을 때는 이유를 함께 기록한다. 고친 뒤 테스트로 확인한다(헌법 III).

## R16. 라이브러리 버전

- **Decision**: `meta.versions`에 python·yfinance·pandas·numpy를 기록한다(지금은 yfinance·pandas만). 재현할 때 버전이 다르면 경고만 하고 비교는 그대로 한다. 결과가 다르면 R8의 보고로 드러난다.
- **Rationale**: 버전이 다르다고 재현을 거부하면 오래된 스냅샷을 쓸 수 없다. 차이가 있으면 비교가 보여 준다.
