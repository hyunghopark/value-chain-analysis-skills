# 001. 데이터 스냅샷과 출처 정보 — 설계

- 상태: 확정 (2026-10-14)
- 요구사항: [spec.md](spec.md)

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

문제는 값이 `info` 딕셔너리 안에서 **덮어써진다**는 점이다(예: 한국 종목 PER은 Yahoo 값 위에 네이버 값, TSM P/B는 역산 값). 덮어쓴 순간 출처 정보가 사라진다.

## 설계

### 1. 새 모듈 `skills/financial-analyst/scripts/snapshot.py`

```python
BASES = {'krx_regular_close', 'flow_feed_price', 'yahoo_close', 'quote',
         'statement', 'consensus', 'derived', 'index_close', 'reference'}
STATUSES = {'final', 'provisional', 'estimated', 'corrected'}

class Snapshot:
    def record(self, path, value, *, source, basis, as_of=None, status='final',
               note=None, ki=None, original=None, inputs=None): ...
    def series(self, path, series, *, source, basis, limit=260): ...   # 가격 이력 (날짜→값)
    def warning(self, msg): ...                                        # KI 번호 파싱
    def dump(self, file_path, meta): ...                               # JSON 저장, 실패 시 예외
```

- `path`는 점 표기(`000660.KS.valuation.trailingPE`)로 표의 위치와 맞춘다.
- `basis`·`status`가 어휘에 없으면 `ValueError` — 오타로 기준이 흐려지는 것을 막는다.
- 전역 하나(`SNAP`)를 `get_financial_stats.py`가 가진다. `warn()`이 `SNAP.warning()`도 호출한다.

### 2. 기록 지점 — "값을 넣는 바로 그 자리"에서 기록

| 기록 지점 (함수) | 기록할 값 | basis / status |
|---|---|---|
| `get_stats` (Yahoo info 직후) | 표에 쓰는 info 원값 | `quote` 또는 `statement`(기간 있는 값), source=yahoo |
| `enrich_korean_stock` | 네이버로 덮어쓴 PER·EPS·PBR·BPS 등, WiseReport FY0·FY1·NTM EPS | `statement`·`consensus`, `original`=Yahoo 값 |
| `sanitize_metrics` (ADR 보정) | 역산한 P/B·P/S·EV 배수·BPS | `derived`, status=`corrected`, ki=KI-008, `original` |
| `check_krx_history` / `check_krx_index` | 채우거나 바꾼 날짜의 값 | `krx_regular_close`/`index_close`, status=`corrected`, ki=KI-002/006, `original` |
| `fetch_investor_trends_table` | 날짜별 순매수 수량, 수급 데이터 가격, 정규장 종가, 금액 | 수량·가격=`flow_feed_price`, 정규장=`krx_regular_close`, 금액=`derived`·`estimated` |
| `fetch_estimates` | FY0·FY1 최저·평균·최고, 30일 상향·하향 건수, eps_trend | `consensus`, source=yahoo |
| `analyze_cycle` / `compute_pb_band` | 연간 영업이익률 목록(기간 포함), 시점별 BPS·P/B | `statement`, `derived`(inputs 기록) |
| `market_context_table` / `technical_table` | 계산에 쓴 기준일·기준 종가 | `derived`(inputs: 이력 경로) |
| `scenario_table` | EPS 3종, 배수 A·B, 결과 | `derived`(inputs) |
| `generate_report` 끝 | 가격 이력(종가·거래량 260일) | `yahoo_close`(교정 반영본), 교정일은 위 기록과 연결 |

### 3. 파일 저장

- `get_financial_stats.py`에 `--snapshot PATH` 인자를 추가한다. 주면 실행 끝에 저장하고, 실패하면 표준 오류와 데이터 품질 경고에 남긴다(R8).
- `generate_strategy_report.py`는 보고서 파일명을 정한 **뒤에** 스냅샷 경로(`<보고서>_data.json`)를 정해 하위 프로세스에 넘긴다. 지금은 데이터 수집이 파일명 결정보다 먼저라 순서를 바꿔야 한다.
- 보고서 상단 '분석 기준 시각' 아래에 스냅샷 파일명을 표시한다.

### 4. 형식 규칙 문서

`skills/financial-analyst/references/rules/data-snapshot.md`에 JSON 구조, `basis`·`status` 어휘와 뜻, 경로 규칙을 적는다. 어휘를 바꿀 때는 이 문서·`snapshot.py`·테스트를 함께 고친다.

```json
{
  "meta": {"generated_at": "2026-10-14 01:20 KST", "args": {...}, "versions": {"yfinance": "1.7.0"}, "repo_commit": "6c14de2"},
  "values": {
    "005930.KS.flows.2026-10-13.price": {"value": 234000, "source": "naver", "basis": "flow_feed_price", "as_of": "2026-10-13", "status": "final"},
    "005930.KS.flows.2026-10-13.krx_close": {"value": 232000, "source": "daum", "basis": "krx_regular_close", "as_of": "2026-10-13", "status": "final", "ki": "KI-001"},
    "^KS11.history.2026-10-13.close": {"value": 6035.35, "source": "daum", "basis": "index_close", "status": "corrected", "ki": "KI-002", "original": null}
  },
  "series": {"005930.KS.close": {"source": "yahoo+daum", "basis": "yahoo_close", "data": {"2026-10-13": 232000}}},
  "warnings": [{"ki": "KI-002", "msg": "..."}]
}
```

## 바꿀 파일

| 파일 | 변경 |
|---|---|
| `skills/financial-analyst/scripts/snapshot.py` | 신규 |
| `skills/financial-analyst/scripts/get_financial_stats.py` | 기록 지점 추가, `--snapshot` 인자, `warn()` 연결 |
| `skills/investment-strategy/scripts/generate_strategy_report.py` | 파일명 결정 순서 변경, 스냅샷 경로 전달, 상단 표시 |
| `skills/financial-analyst/references/rules/data-snapshot.md` | 신규 (형식 규칙) |
| `skills/*/SKILL.md`, `README.md` | 스냅샷 안내, Clean-Slate에 스냅샷 포함(R10) |
| `tests/test_snapshot.py` | 신규 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 기록 지점을 빠뜨려 출처 없는 값이 남음 | 테스트에서 Section 4 표 값 목록과 스냅샷 경로 목록을 대조(완료 기준 2번) |
| `info`를 덮어쓰는 곳이 많아 수정 범위가 큼 | 이번 단계는 '기록만' 추가하고 계산 흐름은 바꾸지 않는다. 구조 분리는 003 |
| 스냅샷 크기 증가 | 이력은 260일·종가·거래량만(R9) |
| 판정이 바뀌는 회귀 | 같은 입력으로 수정 전후 Section 4를 비교하는 확인을 tasks에 넣는다 |

## 결정 (2026-10-14)

- spec 열린 질문 1~3: spec.md '결정' 절 참고 (JSON 하나, 커밋 정보는 가능하면, Git 관리는 분석 프로젝트 선택)
- `path` 표기: **점 표기** (`005930.KS.flows.2026-10-13.price`). 2단계 자동 대조가 찾기 쉽다.
- 구현 브랜치: `main`에서 새로 분기 (`claude/001-data-snapshot` 등). 데이터 품질 작업은 PR로 먼저 반영한다.
