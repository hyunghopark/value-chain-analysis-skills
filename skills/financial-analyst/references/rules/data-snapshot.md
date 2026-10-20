# 데이터 스냅샷 및 출처 정보 규칙 (원본)

코드: `scripts/snapshot.py`, `scripts/raw_inputs.py`, `scripts/collect.py`, `scripts/get_financial_stats.py`, `scripts/rebuild_section4.py`, `generate_strategy_report.py`  
관련 스펙: `specs/001-data-snapshot/` (SC-004), `specs/003-pipeline-split/` (원자료·재현)  
최상위 헌법 원칙: II(출처 추적), III(조용한 오류 금지), IV(단일 원본), VI(Clean-Slate)

---

## 1. 개요 및 목적

보고서의 모든 정량 지표와 분석 수치는 출처와 기준을 사후 검증할 수 있어야 합니다.  
본 규칙은 보고서 생성 시점에 수집·가공된 모든 데이터의 원본 출처, 가격 기준, 시점, 보완·교정 이력을 단일 JSON 파일(`<보고서 파일명>_data.json`)로 보존하는 표준 형식을 규정합니다.

---

## 2. 파일 저장 및 명명 규칙

1. **파일 명명**: 보고서 마크다운 파일과 동일한 경로 및 이름에 `_data.json` 접미사를 붙입니다.
   - 예: `reports/반도체_20261014_Investment_Strategy_Report.md`  
     → `reports/반도체_20261014_Investment_Strategy_Report_data.json`
2. **덮어쓰기 금지**: 기존 스냅샷 파일이 존재하면 새 버전 접미사(`_v2_data.json` 등)를 생성하여 이전 스냅샷을 보존합니다.
3. **오류 격리 (조용한 실패 방지)**: 스냅샷 저장이 디스크/권한 등으로 실패하더라도 보고서 생성을 중단하지 않습니다. 대신 보고서 상단 메타 섹션 및 Section 4 › 8번 데이터 품질 경고에 저장 실패 사실을 명시합니다.

---

## 3. JSON 구조

스냅샷 파일은 최상위 4개 객체(`meta`, `values`, `series`, `warnings`)로 구성됩니다. 형식 2(spec 003)는 여기에 원자료 `inputs`가 더해지며, 자세한 규칙은 §9에 있습니다. 보고서 생성(`generate_strategy_report.py`)이 끝나면 5번째 객체 `section4`가 덧붙습니다(spec 002):

- `section4.text`: 보고서에 넣은 Section 4 본문 그대로(`## 4.` 제목 줄 제외) — 이후 수정 여부를 확인하는 기준본
- `section4.sha256`: `text`의 SHA-256, `section4.attached_at`: 덧붙인 시각(KST)
- 덧붙이기에 실패하면 보고서 머리의 '데이터 스냅샷' 줄 옆에 사유를 표시합니다. 기준본이 없으면 `check_report_numbers.py`가 `no_baseline` 오류를 냅니다.

```json
{
  "meta": {
    "generated_at": "2026-10-14 11:31 KST",
    "args": {
      "tickers": "000660.KS,005930.KS,MU,TSM",
      "cyclical": "",
      "weights": "0.2,0.5,0.3"
    },
    "versions": {
      "yfinance": "1.7.0",
      "pandas": "3.0.6"
    },
    "repo_commit": "e7dafb1"
  },
  "values": {
    "005930.KS.quote.current_price": {
      "value": 237500,
      "source": "yahoo",
      "basis": "quote",
      "as_of": "2026-10-14 11:11",
      "status": "provisional"
    },
    "005930.KS.flows.2026-10-13.price": {
      "value": 234000,
      "source": "naver",
      "basis": "flow_feed_price",
      "as_of": "2026-10-13",
      "status": "final"
    },
    "005930.KS.flows.2026-10-13.krx_close": {
      "value": 232000,
      "source": "daum",
      "basis": "krx_regular_close",
      "as_of": "2026-10-13",
      "status": "final",
      "ki": "KI-001"
    },
    "^KS11.history.2026-10-14.close": {
      "value": 6131.35,
      "source": "daum",
      "basis": "index_close",
      "as_of": "2026-10-14",
      "status": "corrected",
      "ki": "KI-006",
      "original": 6123.98
    }
  },
  "series": {
    "005930.KS.close": {
      "source": "yahoo+daum",
      "basis": "yahoo_close",
      "data": {
        "2026-10-13": 232000
      }
    }
  },
  "warnings": [
    {
      "ki": "KI-006",
      "msg": "005930.KS: Yahoo 종가가 거래소 종가(다음 금융)와 다른 1일을 거래소 종가로 바꿨습니다(10-14 Yahoo ₩237,750→₩238,250)."
    }
  ]
}
```

---

## 4. `values` 레코드 규격 및 어휘 규칙

각 데이터 포인트는 점 표기(dot-notation) 경로를 고유 키로 갖습니다.

### 필수 필드
- **`value`**: 실제 수치 (숫자, 문자열, 불리언 또는 null)
- **`source`**: 원천 출처 식별자 (`yahoo`, `naver`, `daum`, `wisereport`, `calculated` 등)
- **`basis`**: 수치의 산출 기준. 반드시 아래 **8종 화이트리스트 어휘** 중 하나여야 하며, 그 외의 값은 즉시 예외(`ValueError`)를 발생시킵니다.
- **`as_of`**: 기준 일시 (예: `2026-10-14` 또는 `2026-10-14 11:11`)
- **`status`**: 값의 신뢰 상태. 반드시 아래 **4종 화이트리스트 어휘** 중 하나여야 합니다.

### 선택 / 조건부 필드
- **`note`**: 부가 설명 (선택)
- **`ki`**: 관련 알려진 데이터 이슈 번호 (`KI-001` ~ `KI-008` 등). `status == "corrected"`인 경우 **필수**
- **`original`**: 보완 또는 교정되기 전 원본 값. `status == "corrected"`인 경우 **필수**
- **`inputs`**: 계산값(`basis == "derived"`)인 경우 계산에 사용된 입력 경로들의 리스트 (선택)

---

## 5. 화이트리스트 어휘집

### 1) 기준 어휘 (`basis`)
| 어휘 | 정의 및 용도 | 주요 출처 |
|---|---|---|
| `krx_regular_close` | 한국거래소(KRX) 정규장 공식 종가 (Yahoo 보완/교정 기준) | 다음 금융 |
| `flow_feed_price` | 수급 데이터 피드에 기록된 해당일 단일 체결 기준 종가 | 네이버 금융 |
| `yahoo_close` | Yahoo Finance 일별 가격 이력의 종가 | Yahoo Finance |
| `index_close` | 시장 벤치마크 지수의 일별 종가 (코스피, 코스닥, S&P500 등) | 다음/Yahoo |
| `quote` | 현재가, 52주 고저가, 실시간/지연 호가 시세 | Yahoo/네이버 |
| `statement` | 재무제표 공시 수치 (자본총계, 매출, 당기순이익, BPS 등) | Yahoo/네이버 |
| `consensus` | 애널리스트 및 시장 컨센서스 추정치 (목표가, EPS 컨센서스) | Yahoo/WiseReport |
| `derived` | 수집된 원본 지표를 기반으로 스크립트가 연산한 파생 지표 | 스크립트 자체 계산 |

### 2) 상태 어휘 (`status`)
| 어휘 | 정의 | 규칙 제약 |
|---|---|---|
| `final` | 확정된 공식 수치 | 기본값 |
| `provisional` | 장중 잠정 수치 (장중 체결가, 외국인 지분변동 추정 수급 등) | 장중 실행 시 사용 |
| `estimated` | 통계적 추정치 (컨센서스, 수급 추정 대금 등) | - |
| `corrected` | 원본의 결측·오류·단위 불일치를 보완·교정한 수치 | `original`과 `ki` 필드 **필수** |

---

## 6. 점 표기 경로 (Dot-notation Key) 규칙

Section 4의 표 및 계산식을 100% 역추적할 수 있도록 일관된 계층 키를 부여합니다:

- **기본 시세/밸류에이션**: `{ticker}.quote.{metric}` (예: `005930.KS.quote.current_price`, `MU.quote.fifty_two_week_high`)
- **재무 및 지표**: `{ticker}.metrics.{metric}` (예: `000660.KS.metrics.forward_pe`, `TSM.metrics.roe`)
- **수급 데이터**: `{ticker}.flows.{date}.{metric}` (예: `000660.KS.flows.2026-10-13.foreign_net_shares`)
  - 외국인 지분율: `{ticker}.flows.{date}.foreign_hold_ratio` (비율은 소수로 저장, 46.18% → `0.4618`)
  - 최근 5일 누적(추정): `{ticker}.flows.total_5d.{foreign|organ|individual}_net_amt` (억 원, `basis=derived`, `inputs`에 일별 금액 경로. 당일 장중 추정 행이 있으면 기관·개인은 당일 제외이고 `note`에 표시)
- **컨센서스 및 추정치**: `{ticker}.estimates.{period}.{metric}` (예: `005930.KS.estimates.fy1.mean_eps`)
- **시나리오 분석**: `{ticker}.scenario.{case}.{metric}` (예: `MU.scenario.bear.target_price_a`)
- **사이클 및 P/B 밴드**: `{ticker}.cycle.{metric}`, `{ticker}.pb_band.{metric}`
- **기술적 지표/시장 비교**: `{ticker}.technical.{metric}`, `{ticker}.market_context.{period}`

**Section 4 표 표시값 (spec 002, FR-015)**: Section 4에 보이는 숫자는 모두 스냅샷에 있어야 합니다. 앞 단계에서 기록한 값과 표에 찍는 값이 같으면 그대로 두고, 이후 단계에서 바뀐 값이면 표시값을 기록하고 이전 값을 `original`에 남깁니다(`snap_display`). 비율은 소수로 저장합니다(52% → `0.52`). 경로 이름은 `check_report_numbers.py`의 경로 종류 규칙(`report-number-check.md` §4-2)과 맞춥니다.

| 표 | 경로 |
|---|---|
| 2 핵심 지표 | `{ticker}.metrics.{forward_price_to_book, forward_book_value, dupont_leverage, forward_eps_growth}` 등 표의 모든 지표 |
| 2-1 궤적 | `{ticker}.estimates.{fy0,fy1}.{selected_pe, selected_eps}`, `{ticker}.metrics.{implied_rollover_price, return_rollover}` |
| 2-2 경기순환·밴드 | `{ticker}.cycle.max_income_drop`, `{ticker}.pb_band.{position, points_count, return_floor}` |
| 2-3 피어 | `peers.avg.{forward_pe, ev_to_ebitda, profit_margin, roe}`, `{ticker}.peer.forward_pe_vs_avg` |
| 3 목표가 | `{ticker}.estimates.target.{mean, low, high, analysts_count, upside_mean, upside_naver}` |
| 3-1 추정치 | `{ticker}.estimates.{fy0,fy1}.change_30d`, `{ticker}.estimates.total.{up_30d, down_30d}` (FY0+FY1) |
| 3-2 서프라이즈 | `{ticker}.eps_surprise.{YYYY-MM}.{estimate_eps, actual_eps, surprise}` |
| 6 회계 감사 | `{ticker}.audit.{max_unusual, removed_income}`, `{ticker}.audit.{reported,normalized}.{roe, eps}` |
| 7 시나리오 | `{ticker}.scenario.{bear,base,bull}.return_{a,b}`, `{ticker}.scenario.return_expected_{a,b}`, `{ticker}.scenario.{up_down_ratio, eps_range_width}`, `{ticker}.estimates.fy1.analysts_count` |
| 판정 기준값·실행 설정 | `rules.{forward_pe,peg,ev_to_ebitda}.{green_below,yellow_below}`, `rules.{revenue_growth,roe}.{green_above_pct,yellow_above_pct}`, `rules.debt_to_equity.{green_below_pct,yellow_below_pct}`, `rules.revision.{green_above_pct, red_below_pct, min_count, fy1_change_pct}`, `rules.cyclical.income_drop_pct`, `rules.audit.min_share_pct`, `rules.technical.{rsi_oversold_below, rsi_overbought_above}`, `rules.scenario.weight_{bull,base,bear}` — `source="rules"`, `note`에 규칙 원본 파일. 값은 코드 상수(`THRESHOLDS` 등)에서 기록하며, 판정 코드와 Section 4 설명 문구도 같은 상수를 씁니다 |

---

## 7. 가격 이력 (`series`) 제한 규격

- **260거래일 제한**: 종목 및 지수의 일별 가격 이력은 최근 260거래일(약 1년)의 종가(`close`) 및 거래량(`volume`)만 포함합니다.
- **용량 제한**: 4개 종목 기준 스냅샷 파일의 전체 용량은 형식 1 **2MB 이하**, 원자료를 포함하는 형식 2 **10MB 이하**입니다(spec 003 SC-007, 측정 약 2MB — 결정 0006).
- `series`는 사람이 보는 요약입니다. 계산은 `inputs`의 전체 가격 이력(5년)을 읽습니다(§9).

---

## 8. Clean-Slate 원칙 준수

- **과거 스냅샷 참조 금지**: 새로운 분석 세션은 이전에 생성된 스냅샷 파일이나 과거 결론을 입력값으로 사용하지 않습니다. 모든 분석은 독립적으로 최신 데이터를 조회하여 수행합니다.
- 스냅샷은 사후 감사, 회귀 검증, 인간 검토자의 출처 확인 목적으로만 열람됩니다.

---

## 9. 원자료(`inputs`)와 형식 2 (spec 003)

같은 스냅샷이면 같은 Section 4가 나오도록, 정제·계산·출력이 읽는 **원자료 전부**를 받은 시각과 함께 저장합니다. 외부 접속과 현재 시각 읽기는 `collect.py`에서만 합니다.

### 9-1. 최상위 키

| 키 | 뜻 |
|---|---|
| `meta.format_version` | `2`. 없으면 형식 1(001·002) — 원자료가 없어 Section 4를 다시 만들 수 없습니다 |
| `meta.collected_at` | 수집 완료 시각(ISO 8601, 초, `+09:00`). Section 4 데이터 기준 블록의 '생성' 시각 |
| `meta.generated_at` | `collected_at`과 같은 시각의 `YYYY-MM-DD HH:MM KST` 글자. **형식 2부터 뜻이 '수집 완료 시각'** (형식 1은 저장 직전 시각) |
| `meta.versions` | `python`, `yfinance`, `pandas`, `numpy` |
| `meta.repo_commit` / `meta.repo_commit_error` | 코드 버전 / 알 수 없을 때 이유(빈 값을 조용히 남기지 않음) |
| `inputs.<심볼>.<항목>` | 원자료 항목(§9-2). 지수는 `^KS11`처럼 지수 기호가 심볼 |
| `values`, `series`, `warnings`, `section4` | 형식 1과 같은 형식·뜻. 형식 2에서는 원자료로부터 다시 만들 수 있습니다 |

### 9-2. 원자료 항목

```json
{"source": "yahoo", "fetched_at": "2026-10-20T14:04:58+09:00", "status": "ok", "kind": "frame", "data": {}, "error": null, "note": null}
```

| 필드 | 값 |
|---|---|
| `source` | `yahoo`, `naver`, `wisereport`, `daum`, `pykrx` |
| `fetched_at` | 받은 직후 시각(ISO 8601, 초, `+09:00`) |
| `status` | `ok` 받음 · `empty` 받았지만 비어 있음 · `error` 예외(메시지는 `error`, 경고 문장에 그대로 들어감) · `skipped` 수집 조건이 맞지 않아 요청하지 않음 |
| `kind` | `json`(응답 그대로) · `frame`(표) · `table`(WiseReport 표 머리 `headers`와 셀 `rows`). `ok`일 때만 `data`가 있습니다 |
| `note` | 보조 설명(예: Yahoo `info`를 대체 경로로 받은 사유) |

**표(`frame`) 형식**: `{"index": …, "columns": …, "dtypes": […], "data": [[…]]}`. 인덱스·열마다 `kind`(`datetime`/`index`), `tz`(시간대 **이름**, 예 `Asia/Seoul` — 고정 오프셋 금지), `unit`(날짜 정밀도), `name`, `dtype`, 값을 저장합니다. 날짜는 시간대를 뺀 현지 시각 글자, 결측은 `null`, 무한대는 `"Infinity"`/`"-Infinity"`입니다. 다시 읽은 표는 원래 표와 값·자료형·인덱스 이름까지 같아야 합니다(`raw_inputs.py`, 테스트 `test_raw_inputs.py`).

### 9-3. 원자료 목록

| 항목 | 대상 | kind | 출처 |
|---|---|---|---|
| `info` | 모든 종목 | json | yahoo |
| `history` | 종목 5년 / 지수 1년, 모든 열 | frame | yahoo |
| `income_stmt`, `quarterly_income_stmt`, `balance_sheet`, `quarterly_balance_sheet` | 모든 종목 | frame | yahoo |
| `earnings_estimate`, `eps_trend`, `eps_revisions`, `earnings_history` | 모든 종목 | frame | yahoo |
| `naver_integration`, `naver_trend` | 한국 종목 | json | naver |
| `wisereport_eps` | 한국 종목 | table | wisereport |
| `daum_days` | 한국 종목(응답 `data` 행) | json | daum |
| `daum_quote`, `daum_investor_days` | 한국 종목, 당일 네이버 수급 행이 없는 평일만(아니면 `skipped`) | json | daum |
| `pykrx_fundamental` | 한국 종목, `KRX_ID`·`KRX_PW`가 있을 때만(아니면 `skipped`) | json | pykrx |
| `daum_index_days` | `^KS11`, `^KQ11` | json | daum |

수집할 지수는 계산과 같은 함수(`default_benchmarks`, `market_index_for`)로 정합니다. 필요한 항목이 아예 없으면 형식 오류(`missing_input`)이고, `error`·`empty`·`skipped`로 기록된 항목은 생성 때와 같은 경고·빈 표를 냅니다.

### 9-4. 시각 규칙

시각이 필요한 정제·계산은 현재 시각이 아니라 **그 원자료의 받은 시각**을 씁니다.

| 계산 | 쓰는 시각 |
|---|---|
| 수급 표의 '오늘' 판단, 장 마감(15:40) 전후, 평일 여부 | `naver_trend.fetched_at` |
| 지난·다음 실적 발표일 | `info.fetched_at` |
| NTM EPS 가중(올해·내년 비율) | 국내 `wisereport_eps.fetched_at`, 해외 `info.fetched_at` |
| Section 4 데이터 기준 블록의 생성 시각 | `meta.collected_at` |

### 9-5. 정제는 다시 실행한다

스냅샷에는 원자료를 저장하고, 덮어쓰기·KI 교정·출처 간 대조·경고는 Section 4를 만들 때마다 원자료에서 같은 규칙으로 다시 실행합니다. 교정 기록(`original`·`ki`)은 지금처럼 `values`에 남고, 다시 만들 때 저장된 기록과 같아야 합니다. 생성할 때도 원자료를 JSON 글자로 바꿨다 다시 읽은 뒤 Section 4를 만들어, 생성과 재현이 같은 길을 씁니다.

### 9-6. 규칙 변경 전후 비교 (spec 003 US2)

판정 기준값·계산 방식을 바꾸는 PR은 **같은 스냅샷**으로 바꾸기 전과 후의 Section 4를 비교해, 달라진 줄과 계산값을 PR에 적습니다. 실시간 데이터로 비교하면 실행 사이의 시세 변동이 섞이므로 쓰지 않습니다.

```bash
git worktree add /tmp/before main                # 바꾸기 전 코드
python /tmp/before/skills/financial-analyst/scripts/rebuild_section4.py X_data.json --print > before.md
python skills/financial-analyst/scripts/rebuild_section4.py X_data.json --json after.json   # 바꾼 코드: 저장값과 차이 보고
```

`rebuild_section4.py`는 Section 4 차이가 계산값 변화 때문인지(`cause: values`) 글자만 바뀐 것인지(`cause: text_only`) 구분합니다. 바꾸기 전 코드에 재현 도구가 없으면(003 이전) `tests/tools/replay_main.py`로 같은 원자료를 재생해 비교합니다.

