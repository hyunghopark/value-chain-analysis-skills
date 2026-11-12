# 시장 데이터 스냅샷 및 출처 정보 규칙 (원본)

이 문서는 `market-analyst` 스킬에서 생성되는 데이터 스냅샷(`<보고서명>_data.json`)의 표준 규격입니다.  
최상위 원칙: 출처 추적성, 조용한 오류 금지, 단일 원본 보존, 독립적 신규 분석(Clean-Slate).

---

## 1. 개요 및 목적

보고서에 포함된 모든 정량 데이터(지수 종가, 등락률, 200 SMA 이격도, 낙폭, 위기 지지선, VIX, 금리, 신용 스프레드, 섹터 상대강도 등)는 사후 감사 및 재현이 가능하도록 단일 JSON 파일로 기록·보존되어야 합니다.

---

## 2. 파일 저장 및 명명 규칙

1. **파일 명명**: 보고서 마크다운 파일과 동일한 디렉토리 및 파일명에 `_data.json` 접미사를 붙입니다.
   - 예: `reports/미국지수_20261105_Market_Analysis_Report.md`  
     → `reports/미국지수_20261105_Market_Analysis_Report_data.json`
2. **덮어쓰기 금지**: 기존 보고서 및 스냅샷이 존재하면 `_v2`, `_v3` 등으로 버전 접미사를 붙여 이전 기록을 보존합니다.
3. **독립적 신규 분석 (Clean-Slate Policy)**: 새로운 분석을 시작할 때 과거에 작성된 스냅샷 파일을 참조하거나 읽지 않으며, 실시간 API로부터 수집된 새로운 데이터만 사용합니다.

---

## 3. JSON 구조 규격

스냅샷 파일은 5개의 최상위 객체로 구성됩니다:

```json
{
  "meta": {
    "generated_at": "2026-11-05 16:45 KST",
    "market": "US",
    "versions": {
      "yfinance": "1.8.0",
      "pandas": "3.1.1"
    }
  },
  "values": {
    "^GSPC.quote.close": {
      "value": 5780.25,
      "source": "yahoo",
      "basis": "index_close",
      "as_of": "2026-11-05",
      "status": "final"
    },
    "^GSPC.diagnostics.drawdown_52w": {
      "value": -8.45,
      "source": "derived",
      "basis": "drawdown",
      "as_of": "2026-11-05",
      "status": "final"
    },
    "^GSPC.support.iran_war_20240419.breached": {
      "value": false,
      "source": "derived",
      "basis": "support_check",
      "as_of": "2026-11-05",
      "status": "final"
    },
    "macro.regime.verdict": {
      "value": "건전한 조정 국면",
      "source": "derived",
      "basis": "regime_matrix",
      "as_of": "2026-11-05",
      "status": "final"
    }
  },
  "series": {},
  "warnings": [],
  "inputs": {},
  "section4": {
    "text": "## 4. 정량 지표 데이터 분석 결과...",
    "sha256": "abcdef...",
    "attached_at": "2026-11-05 16:45 KST"
  }
}
```

---

## 4. 지원하는 Basis 및 Status 목록

- **`basis` 허용값**: `index_close`, `quote`, `moving_average`, `drawdown`, `support_check`, `relative_strength`, `spread`, `macro_indicator`, `regime_matrix`, `socratic_rule`, `derived`.
- **`status` 허용값**: `final`, `provisional`, `estimated`, `corrected`.
