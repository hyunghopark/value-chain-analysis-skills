"""
Unit and integration tests for the unified 3-tier investment-strategy workflow:
Tests benchmark auto-detection, Section 4 baseline hashing, unified snapshot merging,
placeholder detection, number traceability (macro + financial), and check_strategy_report_numbers.py.
All tests run locally with 0 external network dependencies.
"""

import json
import os
import sys
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
STRATEGY_SCRIPTS = os.path.join(REPO_DIR, "skills", "investment-strategy", "scripts")
if STRATEGY_SCRIPTS not in sys.path:
    sys.path.insert(0, STRATEGY_SCRIPTS)

import generate_strategy_report as gsr
import check_strategy_report_numbers as csr


def test_auto_detect_market_benchmark():
    # 1. Semiconductor keywords
    assert gsr.detect_market_benchmark("AI 메모리 반도체", "005930.KS,000660.KS,MU,TSM") == "반도체"
    assert gsr.detect_market_benchmark("첨단 HBM 패키징", "000660.KS,TSM") == "반도체"
    assert gsr.detect_market_benchmark("Semiconductor Foundry", "TSM,INTC") == "반도체"

    # 2. Tech / Software keywords
    assert gsr.detect_market_benchmark("생성형 AI 소프트웨어", "MSFT,GOOGL") == "기술주식"
    assert gsr.detect_market_benchmark("클라우드 빅테크", "AMZN,MSFT") == "기술주식"

    # 3. Korean Ticker (.KS / .KQ)
    assert gsr.detect_market_benchmark("전기차 배터리", "051910.KS,006400.KS") == "한국증시"
    assert gsr.detect_market_benchmark("바이오 시밀러", "068270.KQ") == "한국증시"
    assert gsr.detect_market_benchmark("국내 제조", "005930") == "한국증시"

    # 4. US Ticker Default
    assert gsr.detect_market_benchmark("Aerospace Defense", "LMT,RTX") == "미국증시"

    # 5. Explicit Override Flag
    assert gsr.detect_market_benchmark("AI 메모리 반도체", "005930.KS", override_market="코스피") == "코스피"
    assert gsr.detect_market_benchmark("전기차", "TSLA", override_market="한국증시") == "한국증시"


def test_extract_target_verdict():
    sample_table = """
### 5. ⭐ 핵심 지표 의사결정 매트릭스
| 기업 (티커) | 유형 | 종합 판단 |
|---|---|---|
| **005930.KS** | 🔄 순환 | 🟢 **강력 매수 후보** |
| **000660.KS** | 🔄 순환 | 🟢 **매수 고려** |
| **MU** | 🔄 순환 | 🟡 **중립/관망** |
"""
    verdict = gsr.extract_target_verdict(sample_table, "005930.KS")
    assert "🟢" in verdict
    assert "강력 매수 후보" in verdict

    verdict_mu = gsr.extract_target_verdict(sample_table, "MU")
    assert "🟡" in verdict_mu
    assert "중립/관망" in verdict_mu

    verdict_missing = gsr.extract_target_verdict(sample_table, "NVDA")
    assert "[AI_TODO:" in verdict_missing


def test_placeholder_detection(tmp_path):
    report_text = """# 테스트 보고서
> **데이터 스냅샷**: `test_data.json`

## 1. 산업 개요
[AI_TODO: 산업 개요 작성 필요]
현재 시장 변동성은 [XX%] 수준입니다.
목표 달성 시 [수치] 억원 예상.
시그널은 [🟢/🟡/🔴] 입니다.

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)
데이터 표

## 8. 참고 문헌
[1] [출처](https://example.com) — 2026-10-01
"""
    rep_file = tmp_path / "test_report.md"
    rep_file.write_text(report_text, encoding="utf-8")

    report = csr.load_report(str(rep_file))
    placeholders = csr.find_placeholders(report)

    descs = [p["desc"] for p in placeholders]
    assert any("AI_TODO" in d for d in descs)
    assert any("XX%" in d for d in descs)
    assert any("수치" in d for d in descs)
    assert any("🟢/🟡/🔴" in d for d in descs)
    assert len(placeholders) >= 4


def test_validator_fails_on_unpopulated_placeholders(tmp_path):
    report_text = """# 테스트 보고서
> **데이터 스냅샷**: `test_data.json`

## 1. 산업 개요
[AI_TODO: 채우지 않은 영역]

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)
정량 표

## 5. 기업별 심층 분석
분석 내용

## 8. 참고 문헌
[1] [출처](https://example.com) — 2026-10-01
"""
    snap_data = {
        "meta": {"tickers": ["005930.KS"]},
        "values": {},
        "section4": {"text": "정량 표", "sha256": "dummy"}
    }
    rep_file = tmp_path / "test_report.md"
    snap_file = tmp_path / "test_data.json"
    rep_file.write_text(report_text, encoding="utf-8")
    snap_file.write_text(json.dumps(snap_data), encoding="utf-8")

    res = csr.verify_strategy_report(str(rep_file))
    assert res.exit_code == csr.EXIT_ISSUES
    assert any(i.kind == "placeholder_left" for i in res.issues)


def test_validator_fails_on_section4_tampering(tmp_path):
    original_sec4 = """### 4.1. 탑다운 거시 시장
지수 현황 표 5,000

### 4.2. 바텀업 기업 재무
삼성전자 주가 55,000원"""

    import hashlib
    sec4_sha = hashlib.sha256(original_sec4.encode('utf-8')).hexdigest()

    tampered_sec4 = """### 4.1. 탑다운 거시 시장
지수 현황 표 5,000 (임의로 숫자 바꿈 9,999)

### 4.2. 바텀업 기업 재무
삼성전자 주가 55,000원"""

    report_text = f"""# 테스트 보고서
> **데이터 스냅샷**: `test_data.json`

## 1. 산업 개요
완성된 산업 개요 문장.

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)
{tampered_sec4}

## 5. 기업별 심층 분석
완성된 분석 내용.

## 8. 참고 문헌
[1] [제목](https://example.com/test) — 2026-10-01
"""
    snap_data = {
        "meta": {"tickers": ["005930.KS"]},
        "values": {"005930.KS.price.close": {"value": 55000, "status": "final"}},
        "section4": {"text": original_sec4, "sha256": sec4_sha}
    }
    rep_file = tmp_path / "test_report.md"
    snap_file = tmp_path / "test_data.json"
    rep_file.write_text(report_text, encoding="utf-8")
    snap_file.write_text(json.dumps(snap_data), encoding="utf-8")

    res = csr.verify_strategy_report(str(rep_file))
    assert res.exit_code == csr.EXIT_ISSUES
    assert any(i.kind == "section4_changed" for i in res.issues)


def test_validator_fails_on_untraced_number(tmp_path):
    sec4 = "정량 데이터 내용"
    import hashlib
    sec4_sha = hashlib.sha256(sec4.encode('utf-8')).hexdigest()

    report_text = f"""# 테스트 보고서
> **데이터 스냅샷**: `test_data.json`

## 1. 산업 개요
아무 근거도 없고 스냅샷에도 없는 미확인 매출 88,888억원을 기록했습니다.

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)
{sec4}

## 5. 기업별 심층 분석
기업 분석 본문.

## 8. 참고 문헌
[1] [기사](https://example.com/article) — 2026-10-01
"""
    snap_data = {
        "meta": {"tickers": ["005930.KS"]},
        "values": {"005930.KS.price.close": {"value": 55000, "status": "final"}},
        "section4": {"text": sec4, "sha256": sec4_sha}
    }
    rep_file = tmp_path / "test_report.md"
    snap_file = tmp_path / "test_data.json"
    rep_file.write_text(report_text, encoding="utf-8")
    snap_file.write_text(json.dumps(snap_data), encoding="utf-8")

    res = csr.verify_strategy_report(str(rep_file))
    assert res.exit_code == csr.EXIT_ISSUES
    assert any(i.kind == "unsupported_number" for i in res.issues)


def test_validator_passes_on_clean_report_with_macro_and_financial_data(tmp_path):
    sec4 = """### 4.1. 탑다운 거시 시장 및 시장 국면 진단
CBOE 변동성 지수 VIX 16.54, 권장 현금 비중 25%

### 4.2. 바텀업 기업 재무 및 밸류에이션 매트릭스
삼성전자 종가 55,000원, Forward PER 10.5배"""

    import hashlib
    sec4_sha = hashlib.sha256(sec4.encode('utf-8')).hexdigest()

    # The body cites macro numbers (VIX 16.54, cash 25%) and financial numbers (55,000원, PER 10.5배)
    # plus an external news figure cited with [1].
    report_text = f"""# 테스트 보고서
> **데이터 스냅샷**: `clean_data.json`
> **종합 의사결정 신호**: [거시 시장 신호: 🟡 건전한 조정 국면 (권장 현금 25%)] vs [기업 밸류 신호: 🟢 강력 매수 후보]
> **한 줄 결론**: 거시 조정 국면(권장 현금 25%)이나 기업 밸류에이션 매력도가 높아 분할 매수합니다.

---

## 1. 산업 개요 및 최근 시장 동향

### 1.1. 중장기 산업 규모 및 구조적 성장 동인
해당 산업의 글로벌 시장 점유율은 52.0%로 집계되었습니다 [1].

### 1.2. 최근 시장 변동성 및 거시/업황 트리거 진단
거시 변동성 지표인 VIX는 16.54를 기록하며 안정적인 흐름을 유지하고 있습니다.

---

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)
{sec4}

---

## 5. 기업별 심층 분석 및 밸류에이션 판단
삼성전자 종가는 55,000원이며 Forward PER은 10.5배입니다.

---

## 6. 소크라테스식 변증법적 리스크 평가 및 가설 검증
비관론자의 핵심 반대 논리를 철저히 점검합니다.

---

## 7. 투자 전략 및 포트폴리오 배분 제안
거시 시장 국면에 따라 포트폴리오의 최소 권장 현금 비중 25%를 준수합니다.

---

## 8. 참고 문헌 (References)
[1] 글로벌 반도체 시장 점유율 보고서 — 2026-10-15 — https://example.com/reports/semi-share

---

*본 보고서는 공개 데이터와 컨센서스를 바탕으로 자동·반자동 생성된 참고 자료이며 투자 권유가 아닙니다.*
"""
    snap_data = {
        "meta": {"tickers": ["005930.KS"], "market": "반도체"},
        "values": {
            # Macro snapshot values
            "macro.vix.level": {"value": 16.54, "source": "yahoo", "status": "final"},
            "macro.regime.cash_pct": {"value": 25.0, "source": "derived", "status": "final"},
            # Financial snapshot values
            "005930.KS.price.close": {"value": 55000.0, "source": "krx", "status": "final"},
            "005930.KS.metrics.forward_pe": {"value": 10.5, "source": "yahoo", "status": "final"},
        },
        "section4": {"text": sec4, "sha256": sec4_sha}
    }

    rep_file = tmp_path / "clean_report.md"
    snap_file = tmp_path / "clean_data.json"
    rep_file.write_text(report_text, encoding="utf-8")
    snap_file.write_text(json.dumps(snap_data), encoding="utf-8")

    res = csr.verify_strategy_report(str(rep_file))
    if res.issues:
        print("\nUnexpected issues in clean test:", [(i.kind, i.location, i.message) for i in res.issues])
    assert res.exit_code == csr.EXIT_OK
    assert len(res.issues) == 0


def test_extract_target_verdict_with_cyclical_and_table5():
    """Verify that extract_target_verdict extracts from Table 5, even when Table 2-2 has ticker rows."""
    sample_financial = """
### 2-2. 🔄 경기순환 진단 및 과거 밸류에이션 밴드
| 기업 | 업종 유형 | 분류 근거 | 연간 영업이익률 범위 | TTM 영업이익률 | 사이클 위치 |
|---|---|---|---|---|---|
| **005930.KS** | 🔄 경기순환 | 순환 | 2.5% ~ 14.4% | 55.04% | 🔴 이익률 과거 최고 초과 (정점 위험) |
| **000660.KS** | 🔄 경기순환 | 순환 | -23.6% ~ 48.6% | 79.66% | 🔴 이익률 과거 최고 초과 (정점 위험) |

### 5. ⭐ 핵심 지표 의사결정 매트릭스
| 기업 (티커) | 유형 | Forward PE | PEG | 매출성장 | EV/EBITDA | ROE | 부채비율 | 추정치 방향 | P/B 밴드 | 사이클 위치 | 종합 판단 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **005930.KS** | 🔄 순환 | 2.6 · 제외 | 0.11 · 제외 | +126.8% | 3.5 | 41.6% | 2.8% 🟢 | 상향 20 / 하향 15 🟡 | P/B 1.86 🟡 | 🔴 | 🟡 **중립/관망** (주의 신호 1개) |
| **000660.KS** | 🔄 순환 | 2.2 · 제외 | 0.13 · 제외 | +327.9% | 3.8 | 72.0% | 5.1% 🟢 | 상향 13 / 하향 7 🟢 | P/B 3.02 🟡 | 🔴 | 🟡 **중립/관망** (주의 신호 1개) |
"""
    verdict = gsr.extract_target_verdict(sample_financial, "005930.KS")
    assert "🟡" in verdict
    assert "중립/관망" in verdict
    assert "🔴" not in verdict  # Must NOT be Table 2-2's cycle position!


def test_detect_market_benchmark_case_insensitivity_and_whitespace():
    # Lowercase ticker with whitespace
    assert gsr.detect_market_benchmark("전기차 배터리", "  005930.ks , 000660.ks ") == "한국증시"
    assert gsr.detect_market_benchmark("AI 반도체", " nvda , msft ") == "반도체"


def test_find_reports_root():
    root = gsr.find_reports_root()
    assert os.path.isdir(os.path.join(root, "reports"))
    assert not root.endswith(".agents")
    assert not root.endswith("ki009-nxt")


def test_section4_tables_parsing_ignores_subsection_headings(tmp_path):
    report_text = """# 테스트 보고서
> **데이터 스냅샷**: `test_data.json`

## 4. 정량 데이터 분석 결과 (스크립트 자동 산출 — 수치 수정 금지)

### 4.1. 탑다운 거시 시장 및 시장 국면 진단
산출 시점 2026-11-06 09:41 KST

### 1. 주요 시장 지수 및 핵심 벤치마크 현황
| 지수명 | 현재 종가 | 5일 등락률 |
|---|---|---|
| S&P 500 | 5,500.00 | -2.5% |

### 4. 거시 리스크 및 스트레스 바로미터
| 지표 항목 | 수치 |
|---|---|
| CBOE 변동성 지수 (VIX) | 22.50 |

### 4.2. 바텀업 기업 재무 및 밸류에이션 매트릭스
데이터 기준 2026-11-06 09:41 KST

### 4. 투자 판단 신호등 매트릭스
| 기업 | 종합 |
|---|---|
| 005930.KS | 🟡 |
"""
    rep_file = tmp_path / "test_sec4_tables.md"
    rep_file.write_text(report_text, encoding="utf-8")
    report = csr.load_report(str(rep_file))
    tables = csr.section4_tables(report)

    # 4.1 and 4.2 subsection headings should NOT be parsed as Table 4
    # Table 4 should contain VIX (22.50) from Table 4, but not 2026 from ### 4.1.
    table4_raws = [t.raw for t in tables.get("4", [])]
    assert "22.50" in table4_raws
    assert "2026" not in table4_raws


def test_verify_real_generated_report():
    project_root = gsr.find_reports_root()
    real_report = os.path.join(project_root, "reports", "AI_메모리_반도체_20261106_Investment_Strategy_Report.md")
    assert os.path.isfile(real_report), f"Report not found at {real_report}"

    res = csr.verify_strategy_report(real_report)
    if res.issues:
        print("\nReport issues:", [(i.kind, i.location, i.message) for i in res.issues])
    assert res.exit_code == csr.EXIT_OK
    assert len([i for i in res.issues if not i.documented]) == 0
