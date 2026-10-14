# 데이터 스냅샷 및 출처 정보 규칙 (원본)

코드: `scripts/snapshot.py`, `scripts/get_financial_stats.py`, `generate_strategy_report.py`  
관련 스펙: `specs/001-data-snapshot/` (SC-004)  
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

스냅샷 파일은 최상위 4개 객체(`meta`, `values`, `series`, `warnings`)로 구성됩니다:

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
- **컨센서스 및 추정치**: `{ticker}.estimates.{period}.{metric}` (예: `005930.KS.estimates.fy1.mean_eps`)
- **시나리오 분석**: `{ticker}.scenario.{case}.{metric}` (예: `MU.scenario.bear.target_price_a`)
- **사이클 및 P/B 밴드**: `{ticker}.cycle.{metric}`, `{ticker}.pb_band.{metric}`
- **기술적 지표/시장 비교**: `{ticker}.technical.{metric}`, `{ticker}.market_context.{period}`

---

## 7. 가격 이력 (`series`) 제한 규격

- **260거래일 제한**: 종목 및 지수의 일별 가격 이력은 최근 260거래일(약 1년)의 종가(`close`) 및 거래량(`volume`)만 포함합니다.
- **용량 제한**: 4개 종목 기준 스냅샷 파일의 전체 용량은 **2MB 이하**여야 합니다.

---

## 8. Clean-Slate 원칙 준수

- **과거 스냅샷 참조 금지**: 새로운 분석 세션은 이전에 생성된 스냅샷 파일이나 과거 결론을 입력값으로 사용하지 않습니다. 모든 분석은 독립적으로 최신 데이터를 조회하여 수행합니다.
- 스냅샷은 사후 감사, 회귀 검증, 인간 검토자의 출처 확인 목적으로만 열람됩니다.
