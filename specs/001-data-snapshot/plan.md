# Implementation Plan: 데이터 스냅샷과 출처 정보

**Branch**: `claude/001-data-snapshot` | **Date**: 2026-10-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-data-snapshot/spec.md`

**Status**: Approved (2026-10-14)

## Summary

보고서를 만들 때 수집한 값을 출처 정보(출처·기준·시점·상태·교정 이력)와 함께 JSON 스냅샷으로 저장한다. 값을 `info` 딕셔너리에 넣거나 덮어쓰는 바로 그 자리에서 기록하고, 계산 흐름은 바꾸지 않는다(구조 분리는 003).

## Technical Context

**Language/Version**: Python 3.12 (uv가 관리, CI도 3.12)

**Primary Dependencies**: yfinance, pandas, requests, beautifulsoup4 (기존 그대로). 추가 의존성 없음 — JSON은 표준 라이브러리.

**Storage**: 보고서 옆 JSON 파일 1개 (`<보고서>_data.json`)

**Testing**: pytest (`tests/`), GitHub Actions CI

**Target Platform**: Windows(로컬), Ubuntu(CI)

**Project Type**: CLI 스크립트 묶음 (Claude Code 스킬)

**Performance Goals**: 보고서 생성 시간 증가 5% 이내 (네트워크 호출 추가 없음)

**Constraints**: 스냅샷 2MB 이하(종목 4개), 판정 결과 불변, 저장 실패가 보고서 생성을 막지 않음

**Scale/Scope**: 보고서 1건당 종목 4개 + 지수 2~3개

## Constitution Check

*GATE: 설계 전후 모두 확인.*

| 원칙 | 점검 | 결과 |
|---|---|---|
| I. 객관성 우선 | 판정 로직·기준값을 바꾸지 않는다. 기록만 추가한다. | ✅ 통과 |
| II. 출처 추적 | 이 기능의 목적 자체. `basis` 어휘로 정규장 종가와 수급 데이터 가격을 구분한다. | ✅ 통과 |
| III. 조용한 오류 금지 | 교정 값에 `original`·`ki` 필수(FR-004). 저장 실패는 경고(FR-008). 어휘 밖 값은 오류(FR-003). | ✅ 통과 |
| IV. 규칙 단일 원본 | 형식 규칙을 `references/rules/data-snapshot.md` 한 곳에 둔다. | ✅ 통과 |
| V. 검증 가능한 변경 | 수정 전 Section 4를 회귀 기준으로 저장하고 비교한다(T002, T016). | ✅ 통과 |
| VI. Clean-Slate | 과거 스냅샷을 입력으로 읽지 않는다(FR-010). SKILL.md에 명시. | ✅ 통과 |

## 현재 구조

```
generate_strategy_report.py
  └─ subprocess: get_financial_stats.py --tickers ...   → 표준 출력(마크다운 표)만 돌려줌
        ├─ get_stats(): Yahoo info → enrich_korean_stock / enrich_global_stock → sanitize_metrics
        │                → history → check_krx_history / check_volume / check_statement_lag
        │                → fetch_estimates / analyze_cycle / compute_pb_band / audit_unusual_items
        ├─ results[symbol] = info dict (원래 키 + '_' 내부 키 15종), HISTORY[symbol] = 가격 이력
        └─ 표 함수들이 results·HISTORY를 읽어 바로 마크다운으로 포맷
```

값이 `info` 안에서 덮어써지는 순간(한국 종목 PER ← 네이버, TSM P/B ← 역산) 출처 정보가 사라지는 것이 핵심 문제다.

## 설계

### 1. 새 모듈 `skills/financial-analyst/scripts/snapshot.py`

```python
BASES = {'krx_regular_close', 'flow_feed_price', 'yahoo_close', 'index_close',
         'quote', 'statement', 'consensus', 'derived'}
STATUSES = {'final', 'provisional', 'estimated', 'corrected'}

class Snapshot:
    def record(self, path, value, *, source, basis, as_of=None, status='final',
               note=None, ki=None, original=None, inputs=None): ...
    def series(self, path, series, *, source, basis, limit=260): ...
    def warning(self, msg): ...          # 메시지 앞의 [KI-xxx] 파싱
    def dump(self, file_path, meta): ...  # 실패 시 예외 → 호출자가 경고 처리
```

- `basis`·`status`가 어휘 밖이거나 `corrected`인데 `original`·`ki`가 없으면 `ValueError`.
- 전역 `SNAP` 하나를 `get_financial_stats.py`가 가진다. `warn()`이 `SNAP.warning()`도 호출한다.

### 2. 기록 지점 — "값을 넣는 바로 그 자리"

| 함수 | 기록할 값 | basis / status |
|---|---|---|
| `get_stats` (Yahoo info 직후) | 표에 쓰는 info 원값 | `quote`·`statement`, source=yahoo |
| `enrich_korean_stock` | 네이버로 덮어쓴 PER·EPS·PBR·BPS 등, WiseReport FY0·FY1·NTM EPS | `statement`·`consensus`, `original`=Yahoo 값 |
| `sanitize_metrics` | 역산한 P/B·P/S·EV 배수·BPS | `derived`, `corrected`, KI-008, `original` |
| `check_krx_history` / `check_krx_index` | 채우거나 바꾼 날짜의 값 | `krx_regular_close`·`index_close`, `corrected`, KI-002·006, `original` |
| `fetch_investor_trends_table` | 날짜별 순매수 수량, 수급 데이터 가격, 정규장 종가, 추정 금액 | 수량·가격 `flow_feed_price`, 정규장 `krx_regular_close`, 금액 `derived`·`estimated` |
| `fetch_estimates` | FY0·FY1 최저·평균·최고, 30일 상향·하향, eps_trend | `consensus`, source=yahoo |
| `analyze_cycle` / `compute_pb_band` | 연간 영업이익률(기간 포함), 시점별 BPS·P/B | `statement`, `derived`(inputs) |
| `market_context_table` / `technical_table` | 기준일·기준 종가 | `derived`(inputs) |
| `scenario_table` | EPS 3종, 배수 A·B, 결과 | `derived`(inputs) |
| `generate_report` 끝 | 종목·지수 가격 이력 260일 | `yahoo_close`·`index_close`(교정 반영본) |

### 3. 파일 저장과 연결

- `get_financial_stats.py`에 `--snapshot PATH` 추가. 실행 끝에 저장, 실패하면 경고(FR-008).
- `generate_strategy_report.py`는 보고서 파일명을 **먼저** 정한 뒤 `<보고서>_data.json` 경로를 하위 프로세스에 넘긴다(현재는 데이터 수집이 파일명 결정보다 먼저라 순서를 바꾼다).
- 보고서 상단 '분석 기준 시각' 아래에 스냅샷 파일명을 표시한다.

### 4. 형식 예시

```json
{
  "meta": {"generated_at": "2026-10-14 01:20 KST", "args": {}, "versions": {"yfinance": "1.7.0"}, "repo_commit": "e7dafb1"},
  "values": {
    "005930.KS.flows.2026-10-13.price": {"value": 234000, "source": "naver", "basis": "flow_feed_price", "as_of": "2026-10-13", "status": "final"},
    "005930.KS.flows.2026-10-13.krx_close": {"value": 232000, "source": "daum", "basis": "krx_regular_close", "as_of": "2026-10-13", "status": "final", "ki": "KI-001"},
    "^KS11.history.2026-10-13.close": {"value": 6035.35, "source": "daum", "basis": "index_close", "status": "corrected", "ki": "KI-002", "original": null}
  },
  "series": {"005930.KS.close": {"source": "yahoo+daum", "basis": "yahoo_close", "data": {"2026-10-13": 232000}}},
  "warnings": [{"ki": "KI-002", "msg": "..."}]
}
```

## Project Structure

### Documentation (this feature)

```text
specs/001-data-snapshot/
├── spec.md      # 요구사항 (승인됨)
├── plan.md      # 이 문서
└── tasks.md     # 작업 목록
```

### Source Code (repository root)

```text
skills/financial-analyst/
├── references/rules/data-snapshot.md   # 신규: 형식 규칙
└── scripts/
    ├── snapshot.py                     # 신규
    └── get_financial_stats.py          # 기록 지점, --snapshot
skills/investment-strategy/scripts/generate_strategy_report.py   # 파일명 순서, 경로 전달, 상단 표시
tests/test_snapshot.py                  # 신규
```

**Structure Decision**: 기존 스킬 구조를 유지하고 `financial-analyst/scripts`에 모듈 하나를 더한다. 스킬 폴더 안에서 자기완결적이어야 한다(헌법 기술 제약).

## Complexity Tracking

| 복잡도 | 필요한 이유 | 더 단순한 대안을 버린 이유 |
|---|---|---|
| 기록 지점이 10곳 이상으로 흩어짐 | 값이 덮어써지는 자리에서만 원래 출처를 알 수 있다 | 끝에서 `info`를 통째로 저장하면 덮어쓰기 전 출처를 잃는다. 근본 해결(구조 분리)은 003 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 기록 지점을 빠뜨려 출처 없는 값이 남음 | Section 4 표 값 목록과 스냅샷 경로를 대조하는 테스트(SC-002) |
| `info`를 덮어쓰는 곳이 많아 수정 범위가 큼 | 이번에는 기록만 추가, 계산 흐름 불변 |
| 판정이 바뀌는 회귀 | 수정 전 Section 4를 저장해 비교(T002, T016) |
