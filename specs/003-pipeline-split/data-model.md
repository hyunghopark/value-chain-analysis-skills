# Data Model: 수집·정제·계산·출력 분리

**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

규칙 원본은 구현 때 `skills/financial-analyst/references/rules/data-snapshot.md`에 옮긴다(FR-012). 이 문서는 설계 기준이다.

## 1. 스냅샷 형식 2 (최상위)

```json
{
  "meta": {
    "format_version": 2,
    "generated_at": "2026-10-20 14:05 KST",
    "collected_at": "2026-10-20T14:05:12+09:00",
    "args": {"tickers": "...", "cyclical": "", "not_cyclical": "", "benchmarks": "", "weights": "0.2,0.5,0.3", "snapshot": "..."},
    "versions": {"python": "3.12.7", "yfinance": "1.4.1", "pandas": "3.0.3", "numpy": "2.3.1"},
    "repo_commit": "a1308f9",
    "repo_commit_error": null
  },
  "inputs": { "<심볼>": { "<항목>": { "...원자료 항목(§2)" } } },
  "values":   { "...001 형식 그대로" },
  "series":   { "...001 형식 그대로" },
  "warnings": [ "...001 형식 그대로" ],
  "section4": { "...002 형식 그대로 (generate_strategy_report.py가 덧붙임)" }
}
```

| 키 | 뜻 | 바뀐 점 |
|---|---|---|
| `meta.format_version` | `2`. 없으면 이전 형식(1) | 신규 |
| `meta.generated_at` | 사람이 읽는 수집 완료 시각. Section 4 데이터 기준 블록과 같은 글자 | 뜻 변경: 지금은 스냅샷 저장 직전 시각 → 수집 완료 시각 |
| `meta.collected_at` | 수집 완료 시각(초, 시간대 포함). 표 머리 생성 시각의 원본 | 신규 |
| `meta.args` | 실행 옵션(재현의 기본 옵션) | 그대로 |
| `meta.versions` | python·yfinance·pandas·numpy | python·numpy 추가 |
| `meta.repo_commit` / `repo_commit_error` | 코드 버전 / 알 수 없을 때 이유 | 버그 수정(R15), 이유 칸 신규 |
| `inputs` | 원자료(§2~3). 정제·계산·출력의 유일한 데이터 입력 | 신규 |
| `values`, `series`, `warnings` | 정제·계산 결과. 001·002가 읽는 값 | 형식 그대로. 이제 원자료에서 다시 만들 수 있다 |
| `section4` | 002 기준본 | 그대로 |

## 2. 원자료 항목

```json
{
  "source": "yahoo",
  "fetched_at": "2026-10-20T14:04:58+09:00",
  "status": "ok",
  "kind": "frame",
  "data": { "...kind에 따른 내용" },
  "error": null,
  "note": null
}
```

| 필드 | 값 | 규칙 |
|---|---|---|
| `source` | `yahoo`, `naver`, `wisereport`, `daum`, `pykrx` | 001 `source`와 같은 이름 |
| `fetched_at` | ISO 8601, 초, `+09:00` | 시각이 필요한 정제·계산은 이 값을 쓴다(R4) |
| `status` | `ok` / `empty` / `error` / `skipped` | `empty`: 받았지만 비어 있음. `error`: 예외(메시지는 `error`). `skipped`: 수집 조건이 맞지 않아 요청하지 않음(예: 당일 행이 이미 있어 다음 장중 조회 생략) |
| `kind` | `json` / `frame` / `table` | `ok`일 때만 `data`가 있다 |
| `error` | 예외 메시지 글자 | 경고 문장에 그대로 들어간다(R6) |
| `note` | 보조 설명 | 예: `info`를 `_quote._info`로 대신 받았을 때 그 사유 |

### 표 형식 (`kind: "frame"`)

```json
{
  "index":   {"kind": "datetime", "tz": "Asia/Seoul", "unit": "s", "name": "Date", "values": ["2021-10-20T00:00:00", "..."]},
  "columns": {"kind": "index", "dtype": "str", "name": null, "values": ["Open", "High", "Low", "Close", "Adj Close", "Volume", "Dividends", "Stock Splits"]},
  "dtypes":  ["float64", "float64", "float64", "float64", "float64", "int64", "float64", "float64"],
  "data":    [[1.0, 2.0, null, "..."], ["..."]]
}
```

- `index`·`columns`는 각각 `kind`가 `datetime`이면 `tz`(이름 또는 `null`), `unit`, `name`, 시간대를 뺀 현지 시각을 가진다. `index`이면 `dtype`, `name`, 글자 값을 가진다.
- `data`는 행 목록이다. 결측은 `null`이고, 읽을 때 `dtypes`로 되돌린다.
- 읽은 표는 원래 표와 `DataFrame.equals`, 인덱스·열 자료형, 이름까지 같아야 한다(R3, 테스트로 확인).

### WiseReport 표 (`kind: "table"`)

```json
{"headers": ["재무년월", "매출액(억원, %)", "..."], "rows": [["2025/12", "...", "..."], ["..."]]}
```

표 구조 검사(KI-004)와 셀 해석은 정제 단계가 한다.

## 3. 원자료 목록

경로는 `inputs.<심볼>.<항목>`이다. 지수는 `^KS11`처럼 지수 기호를 심볼로 쓴다.

| 항목 | 대상 | kind | 출처 | 읽는 정제·계산 |
|---|---|---|---|---|
| `info` | 모든 종목 | json | yahoo | 덮어쓰기·교정, 표 전부, 실적 발표일, 데이터 기준 블록 |
| `history` | 모든 종목(5년) | frame | yahoo | 거래소 대조, 거래량 이상, 기술 지표, 시장 비교, P/B 밴드, `series` |
| `income_stmt`, `quarterly_income_stmt` | 모든 종목 | frame | yahoo | 재무제표 지연(KI-003), 사이클, 감사 |
| `balance_sheet`, `quarterly_balance_sheet` | 모든 종목 | frame | yahoo | P/B 밴드, 감사 |
| `earnings_estimate`, `eps_trend`, `eps_revisions`, `earnings_history` | 모든 종목 | frame | yahoo | 추정치·서프라이즈·시나리오, 해외 NTM |
| `naver_integration` | 한국 종목 | json | naver | 국내 지표 덮어쓰기 |
| `wisereport_eps` | 한국 종목 | table | wisereport | KI-004 검사, FY0·FY1·NTM |
| `pykrx_fundamental` | 한국 종목(환경 변수 있을 때) | json(해당 종목 행과 기준일) | pykrx | 결측 보완 |
| `daum_days` | 한국 종목 | json(응답 `data` 행) | daum | 거래소 종가 대조, 수급 표의 거래소 종가 |
| `naver_trend` | 한국 종목 | json | naver | 수급 표 |
| `daum_quote`, `daum_investor_days` | 한국 종목(당일 네이버 행이 없는 평일만) | json | daum | 장중 외국인 수급 추정 |
| `history` | 지수(1년) | frame | yahoo | 시장 비교, 거래일 달력 |
| `daum_index_days` | `^KS11`, `^KQ11` | json | daum | 지수 대조 |

- 수집할 지수는 `default_benchmarks`와 `market_index_for`로 정한다. 정제·계산도 같은 함수를 쓰므로, 수집 결과와 계산이 요구하는 지수가 어긋나지 않는다.
- 수집 조건에 따라 요청하지 않은 항목은 `status: "skipped"`로 남긴다. 항목이 아예 없으면 형식 오류다(§5).

## 4. 실행 정보 (Run context)

정제·계산·출력에 넘기는 값이다. 전부 스냅샷에서 나온다.

| 필드 | 출처 |
|---|---|
| `tickers` | `meta.args.tickers` |
| `cyclical_add`, `cyclical_remove`, `weights` | `meta.args` 또는 재계산 옵션 |
| `benchmarks` | `meta.args.benchmarks`(비면 `default_benchmarks`) |
| `collected_at` | `meta.collected_at` |
| 원자료별 시각 | `inputs.*.*.fetched_at` |

## 5. 재현 결과 (Reproduction result)

`rebuild_section4.py --json`의 출력 구조다.

```json
{
  "snapshot": "path/X_data.json",
  "snapshot_sha256": "...",
  "rebuilt_at": "2026-10-21 09:00 KST",
  "mode": "verify",
  "options_changed": {},
  "format_version": 2,
  "version_warnings": ["pandas 3.0.3 → 3.0.5"],
  "section4": {"compared": true, "same": false, "diff": [{"line": 41, "baseline": "...", "rebuilt": "..."}]},
  "values":   {"same": false, "changed": [{"path": "MU.metrics.forward_pe", "stored": 9.81, "rebuilt": 9.83}], "added": [], "removed": [],
               "within_tolerance": ["MU.technical.bollinger_lower"]},
  "warnings": {"same": true, "diff": []},
  "errors":   [],
  "exit_code": 1
}
```

| 필드 | 뜻 |
|---|---|
| `mode` | `verify`(저장값과 비교) / `recompute`(옵션을 바꿔 다시 계산, 비교 대신 바뀐 값 목록) |
| `section4.compared` | 기준본이 있을 때만 `true`. 없으면 `false`이고 차이로 보지 않는다(값·경고 비교는 한다) |
| `errors` | 다시 만들 수 없는 이유. 예: `{"code": "missing_input", "path": "inputs.MU.quarterly_balance_sheet"}`, `{"code": "legacy_format"}`, `{"code": "option_needs_data", "detail": "--cyclical 000990.KS (스냅샷에 없는 종목)"}` |
| `rebuilt_at` | 재현 도구 자신의 실행 기록용. 재현 결과(Section 4·values)에는 들어가지 않는다 |
| `values.within_tolerance` | 숫자가 상대 1e-9(절대 1e-12) 안에서만 다른 경로 — 같은 값으로 보지만 나열한다(CPU 구조 차이, research R8 조정) |

**오류 코드**: `legacy_format`, `missing_input`, `invalid_input`(형식이 맞지 않음), `unreadable`(파일 읽기 실패), `option_rejected`(허용하지 않는 옵션), `option_needs_data`, `output_exists`. 모두 종료 코드 2다.

## 6. 상태 변화

```text
수집 (collect.py, 네트워크·시각)
  └─ inputs + meta  ──JSON 글자로 왕복──┐
                                        ▼
정제 (get_financial_stats.py: refine_*)  ← 원자료와 fetched_at만
  └─ 덮어쓰기·교정·대조·경고 → values / warnings 일부
계산·출력 (표 함수)                        ← 정제 결과만
  └─ 지표·판정·시나리오 → values / warnings, Section 4 글자
저장: meta + inputs + values + series + warnings   (generate_strategy_report.py가 section4 덧붙임)

재현 (rebuild_section4.py): 저장된 스냅샷 → 정제 → 계산·출력 → 비교
```

## 7. 이전 형식과의 관계

| 기능 | 형식 1 (001·002) | 형식 2 (003) |
|---|---|---|
| 002 숫자 점검 | 동작 | 동작 (`values`·`series`·`section4` 그대로) |
| Section 4 재현 | 불가(`legacy_format`, 종료 코드 2) | 가능 |
| 옵션 재계산 | 불가 | 가능 (확률·순환업종) |
