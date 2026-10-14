"""
Tests for the report number checker (skills/financial-analyst/scripts/check_report_numbers.py).
Spec: specs/002-report-number-check/ — rules: skills/financial-analyst/references/rules/report-number-check.md
"""

import json
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(CURRENT_DIR)
SCRIPTS_DIR = os.path.join(REPO_DIR, "skills", "financial-analyst", "scripts")
RULES_DOC = os.path.join(REPO_DIR, "skills", "financial-analyst", "references", "rules", "report-number-check.md")
FIXTURE_DIR = os.path.join(CURRENT_DIR, "fixtures", "002")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_report_numbers as crn


def write_case(tmp_path, report_text, snapshot=None, report_name="r.md", snapshot_name="r_data.json"):
    """Write a synthetic report (and optional snapshot) and return the report path."""
    report = tmp_path / report_name
    report.write_text(report_text, encoding="utf-8")
    if snapshot is not None:
        (tmp_path / snapshot_name).write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
    return str(report)


MINI_REPORT = """# 테스트 보고서

> **데이터 스냅샷**: `r_data.json`
> **한 줄 결론**: 머리 문장

---

## 1. 산업 개요

본문 문장.

## 4. 정량 재무 지표 (스크립트 자동 산출 — 수치 수정 금지)

### 1. 주요 주가

| 기업 | 현재 주가 |
|---|---|
| A | ₩237,500 |

---

## 5. 기업별 분석

분석 문장.

## 8. 참고 문헌 (References)

[1] [제목](https://example.com/a/1) — 2026-10-01

---

*면책 문구*
"""


# --- T005: sections, snapshot discovery, exit code 2 ---------------------------------------

def test_load_report_sections(tmp_path):
    report = crn.load_report(write_case(tmp_path, MINI_REPORT))
    assert [s.kind for s in report.sections] == ["head", "body", "section4", "body", "references", "body"]
    s4 = next(s for s in report.sections if s.kind == "section4")
    assert s4.title.startswith("4. 정량 재무 지표")
    assert any("₩237,500" in line for line in s4.lines)
    refs = next(s for s in report.sections if s.kind == "references")
    # the disclaimer after the last '---' is body text, not part of the reference list
    assert not any("면책" in line for line in refs.lines)
    assert any("면책" in line for line in report.sections[-1].lines)


def test_load_report_check_section_kind(tmp_path):
    text = MINI_REPORT.replace("---\n\n*면책 문구*", "## 9. 숫자 점검 결과 (스크립트 자동 점검)\n\n남은 문제 없음\n\n---\n\n*면책 문구*")
    report = crn.load_report(write_case(tmp_path, text))
    assert [s.kind for s in report.sections][-2:] == ["check", "body"]


def test_line_numbers_are_one_based(tmp_path):
    report = crn.load_report(write_case(tmp_path, MINI_REPORT))
    s4 = next(s for s in report.sections if s.kind == "section4")
    assert report.lines[s4.start - 1].startswith("## 4.")
    assert s4.lines[0] == report.lines[s4.start - 1]


def test_find_snapshot_from_header(tmp_path):
    path = write_case(tmp_path, MINI_REPORT, snapshot={"meta": {}, "values": {}, "series": {}, "warnings": []})
    report = crn.load_report(path)
    assert crn.find_snapshot(report) == str(tmp_path / "r_data.json")


def test_find_snapshot_missing_file(tmp_path):
    report = crn.load_report(write_case(tmp_path, MINI_REPORT))
    assert crn.find_snapshot(report) is None


def test_find_snapshot_override(tmp_path):
    other = tmp_path / "other_data.json"
    other.write_text("{}", encoding="utf-8")
    report = crn.load_report(write_case(tmp_path, MINI_REPORT))
    assert crn.find_snapshot(report, override=str(other)) == str(other)


def test_exit_code_2_for_missing_report(tmp_path):
    assert crn.main([str(tmp_path / "nope.md")]) == 2


def test_exit_code_2_for_bad_arguments():
    assert crn.main(["--no-such-option"]) == 2


# --- T006: parse_numbers ------------------------------------------------------------------------

def _tok(text):
    return [(t.value, t.unit, t.decimals, t.sign, t.currency) for t in crn.parse_numbers(text)]


@pytest.mark.parametrize("text, expected", [
    ("₩237,500", [(237500.0, "", 0, None, "₩")]),
    ("+101.64%", [(101.64, "%", 2, "+", None)]),
    ("−3.2%", [(-3.2, "%", 1, "-", None)]),
    ("하방(-27.2%)", [(-27.2, "%", 1, "-", None)]),
    ("$54.23B", [(54.23, "B", 2, None, "$")]),
    ("₩1,076.75T (보통주)", [(1076.75, "T", 2, None, "₩")]),
    ("P/B 2.44배", [(2.44, "배", 2, None, None)]),
    ("6.63x로", [(6.63, "x", 2, None, None)]),
    ("-39,334억 원", [(-39334.0, "억", 0, "-", None)]),
    ("3조 9,334억 원", [(3.9334, "조", 4, None, None)]),
    ("약 -3조 9,334억 원(추정)", [(-3.9334, "조", 4, "-", None)]),
    ("1조 4,942억 TWD", [(1.4942, "조", 4, None, None)]),
    ("107.4조 원", [(107.4, "조", 1, None, None)]),
    ("35,601,106주", [(35601106.0, "주", 0, None, None)]),
    ("상향 7건", [(7.0, "건", 0, None, None)]),
    ("34.3% 하락", [(34.3, "%", 1, None, None)]),
    ("26.5%~31.2%", [(26.5, "%", 1, None, None), (31.2, "%", 1, None, None)]),
    ("50~60%", [(50.0, "%", 0, None, None), (60.0, "%", 0, None, None)]),
    ("₩404,500 ~ ₩3,002,000", [(404500.0, "", 0, None, "₩"), (3002000.0, "", 0, None, "₩")]),
    ("16GB~32GB", [(16.0, "GB", 0, None, None), (32.0, "GB", 0, None, None)]),
    ("1.24~10.89", [(1.24, "", 2, None, None), (10.89, "", 2, None, None)]),
    ("+2.4% 반등", [(2.4, "%", 1, "+", None)]),
    ("+12.5%p", [(12.5, "%p", 1, "+", None)]),
])
def test_parse_numbers(text, expected):
    assert _tok(text) == expected


def test_parse_numbers_hyphen_between_numbers_is_not_a_sign():
    # '1-1' or '10-14' must not produce negative numbers (they are masked later as numbering/date)
    assert [t.sign for t in crn.parse_numbers("1-1")] == [None, None]
    assert [t.value for t in crn.parse_numbers("2022→2023 -74%")] == [2022.0, 2023.0, -74.0]


def test_parse_numbers_positions_and_raw():
    text = "외국인 -3조 9,334억 원 순매도"
    (t,) = crn.parse_numbers(text)
    assert t.raw == "-3조 9,334억"
    assert text[t.start:t.end] == t.raw


# --- T007: exclusion categories (rules §2) ------------------------------------------------------

@pytest.mark.parametrize("text, category, in_mermaid", [
    ("    classDef x fill:#f9f9f9,stroke:#333,stroke-width:2px;", "diagram_style", True),
    ("색상 #512da8 사용", "diagram_style", False),
    ("확인했습니다 [7].", "citation", False),
    ("출처 [7], [8]", "citation", False),
    ("KI-001 경고", "citation", False),
    ("https://www.yna.co.kr/view/AKR20261010", "citation", False),
    ("`AI_20261014_data.json`", "citation", False),
    ("2026-10-28 발표", "date", False),
    ("2026-10 한국경제", "date", False),
    ("최종 체결 10-14 KST", "date", False),
    ("10월 27~28일 예정", "date", False),
    ("10월 말 발표", "date", False),
    ("한국 시각 15:00", "date", False),
    ("코드 005930", "ticker_code", False),
    ("005930.KS 분석", "ticker_code", False),
    ("^KS11 지수", "ticker_code", False),
    ("3Q26 잠정", "period_label", False),
    ("FY4Q26 매출", "period_label", False),
    ("1H26 실적", "period_label", False),
    ("FY1 EPS", "period_label", False),
    ("3분기 실적", "period_label", False),
    ("HBM4 전환", "product_spec", False),
    ("LPDDR5X 탑재", "product_spec", False),
    ("MI350 시리즈", "product_spec", False),
    ("16-Hi 적층", "product_spec", False),
    ("4나노 수율", "product_spec", False),
    ("3nm 공정", "product_spec", False),
    ("12단 제품", "product_spec", False),
    ("2048-bit 인터페이스", "product_spec", False),
    ("1c D램", "product_spec", False),
    ("6세대 제품", "product_spec", False),
    ("최근 30일 추정치", "duration", False),
    ("5거래일 기준", "duration", False),
    ("20일간 하락", "duration", False),
    ("최근 1~5거래일간", "duration", False),
    ("52주 최고가", "duration", False),
    ("PEG (12M, 단순 추정)", "duration", False),
    ("3개월 내", "duration", False),
    ("2027년 가이던스", "year", False),
    ("2034", "year", False),
    ("### 6.1. 시나리오 해석", "numbering", False),
    ("### 🎯 7.1. 판정별 실행 전략", "numbering", False),
    ("### 💰 7.2. 포트폴리오 배분 제안", "numbering", False),
    ("Section 4 › 1-1 표", "numbering", False),
    ("Section 4 › 5번 매트릭스", "numbering", False),
    ("5번 매트릭스", "numbering", False),
    ("주의 신호 2개", "numbering", False),
    ("1. **AI 가속기**", "numbering", False),
])
def test_excluded_categories(text, category, in_mermaid):
    tokens, counts = crn.extract_numbers(text, in_mermaid=in_mermaid)
    assert tokens == [], [t.raw for t in tokens]
    assert counts[category] >= 1, dict(counts)


def test_year_range_with_arrow_is_two_years():
    tokens, counts = crn.extract_numbers("(2022→2023 -74%)")
    assert [t.raw for t in tokens] == ["-74%"]
    assert counts["year"] == 2


def test_heading_with_ticker_is_excluded():
    tokens, counts = crn.extract_numbers("### 1) 005930.KS (Samsung Electronics)")
    assert tokens == []
    assert counts["numbering"] == 1 and counts["ticker_code"] == 1


@pytest.mark.parametrize("text", [
    "TTM 영업이익률 52.18%", "₩237,500", "-39,334억 원", "P/B 2.44배", "16GB", "상향 7건",
    "52주 최고가(₩380,000) 대비 -34.3%", "지분율 46.18%", "2,034억 원", "백분위 62%",
])
def test_quantities_are_kept(text):
    tokens, _ = crn.extract_numbers(text)
    assert tokens, f"no quantity read from {text!r}"


def _rules_tables():
    """Tables in the rules document whose first header cell is '키', keyed by the nearest heading."""
    tables, heading, current = [], "", None
    with open(RULES_DOC, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            if line.startswith("| 키 |"):
                current = {"heading": heading, "header": [c.strip() for c in line.strip("|").split("|")], "rows": []}
                tables.append(current)
            elif current is not None and line.startswith("|") and not line.startswith("|---"):
                current["rows"].append([c.strip() for c in line.strip("|").split("|")])
            elif not line.startswith("|"):
                current = None
    return tables


def _keys(table):
    return {row[0].strip("`") for row in table["rows"]}


def test_rules_document_matches_constants():
    tables = _rules_tables()
    by = lambda heading_prefix, col: next(t for t in tables if t["heading"].startswith(heading_prefix) and t["header"][1] == col)
    assert _keys(by("2.", "범주")) == set(crn.EXCLUDE_CATEGORIES)
    assert _keys(by("2.", "뜻")) == set(crn.SPEC_UNITS)
    scales = by("4-2.", "배율")
    doc_scales = {("" if row[0] == "(없음)" else row[0].strip("`")): [float(x) for x in row[1].split(",")] for row in scales["rows"]}
    assert doc_scales == {k: list(v) for k, v in crn.UNIT_SCALES.items()}
    assert _keys(by("7.", "뜻")) == set(crn.FETCH_STATUSES)
    assert _keys(by("8.", "뜻")) == {str(crn.EXIT_OK), str(crn.EXIT_ISSUES), str(crn.EXIT_CANNOT_RUN)}


# --- T008: US1 classification (spec US1 acceptance scenarios 1-8) -------------------------------

US1_SNAPSHOT = {
    "meta": {"args": {"tickers": "005930.KS,000660.KS"}},
    "values": {
        "005930.KS.cycle.opm_ttm": {"value": 0.52183, "source": "calculated", "basis": "derived", "status": "final"},
        "005930.KS.pb_band.current_pb": {"value": 2.4417, "source": "calculated", "basis": "derived", "status": "final"},
        "005930.KS.flows.total_5d.foreign_net_amt": {"value": -39334.2, "source": "calculated", "basis": "derived", "status": "estimated"},
        "005930.KS.quote.current_price": {"value": 237500, "source": "yahoo", "basis": "quote", "status": "provisional"},
        "005930.KS.market_context.drawdown_52w": {"value": -0.3430, "source": "calculated", "basis": "derived", "status": "final"},
        "005930.KS.estimates.revisions.down_30d": {"value": 25, "source": "yahoo", "basis": "consensus", "status": "final"},
        "000660.KS.estimates.revisions.down_30d": {"value": 11, "source": "yahoo", "basis": "consensus", "status": "final"},
        "005930.KS.metrics.part_a": {"value": 120.5, "source": "yahoo", "basis": "statement", "status": "final"},
        "005930.KS.metrics.part_b": {"value": 30.25, "source": "yahoo", "basis": "statement", "status": "final"},
        "000660.KS.metrics.roe": {"value": 0.4567, "source": "yahoo", "basis": "statement", "status": "final"},
        "^KS11.market_context.return_5d": {"value": -0.119, "source": "calculated", "basis": "derived", "status": "final"},
    },
    "series": {"005930.KS.close": {"source": "yahoo", "basis": "yahoo_close", "data": {"2026-10-13": 232000}}},
    "warnings": [],
}

US1_REPORT = """# 테스트 보고서

> **데이터 스냅샷**: `r_data.json`

## 1. 산업 개요

TTM 영업이익률 52.18%를 기록했다. P/B 2.44배 수준이다.
3분기 잠정 영업이익 107.4조 원을 발표했다 [7].
근거 없는 숫자 12.34%가 문장에 있다.
외국인은 -3조 9,334억 원(추정) 순매도했다.
두 지표의 합은 150.75이다.
005930.KS 하락 속에 지수는 -11.9% 내렸고 000660.KS는 하향 11건이다.
고점 대비 34.3% 하락했다. 다른 문장에서는 고점 대비 +34.3% 올랐다고 썼다.
2027년 HBM4 출하가 예정되어 있다.
하향 11건이 나왔다.
현재가 ₩237,500이고 전일 종가는 ₩232,000이다.

| 항목 | 결과 | 출처 |
|---|---|---|
| 실적 | 매출 195조 원 | [연합뉴스](https://example.com/news/1) [7] |

## 5. 기업별 분석

### 1) 005930.KS (Samsung Electronics)

추정치는 하향 25건이다. 상향 11건은 이 종목 값이 아니다. ROE 45.67%는 다른 종목 값이다.

## 8. 참고 문헌 (References)

[7] [기사 제목](https://example.com/news/1) — 2026-10-10
"""


@pytest.fixture
def us1(tmp_path):
    path = write_case(tmp_path, US1_REPORT, snapshot=US1_SNAPSHOT)
    result = crn.check(path)
    return result


def _mention(result, raw, nth=0):
    found = [m for m in result.mentions if m.raw == raw]
    assert len(found) > nth, f"{raw!r} not found in {[m.raw for m in result.mentions]}"
    return found[nth]


def test_us1_ratio_matches_with_path(us1):                       # scenario 1
    m = _mention(us1, "52.18%")
    assert m.classification == "script"
    assert m.matched_path == "005930.KS.cycle.opm_ttm"


def test_us1_display_precision(us1):                              # scenario 2
    assert _mention(us1, "2.44배").classification == "script"


def test_us1_citation_in_sentence(us1):                           # scenario 3
    m = _mention(us1, "107.4조")
    assert m.classification == "cited"
    assert m.scope_citations == [7]


def test_us1_citation_in_table_row(us1):                          # scenario 4
    m = _mention(us1, "195조")
    assert m.classification == "cited"
    assert m.scope_citations == [7]


def test_us1_unsupported_has_location_and_context(us1):           # scenario 5
    m = _mention(us1, "12.34%")
    assert m.classification == "unsupported"
    assert m.section == "1. 산업 개요"
    assert m.line == 9
    assert "근거 없는 숫자" in m.context


def test_us1_unit_conversion_korean_amount(us1):                  # scenario 6
    m = _mention(us1, "-3조 9,334억")
    assert m.classification == "script"
    assert m.matched_path == "005930.KS.flows.total_5d.foreign_net_amt"


def test_us1_derived_sum_is_unsupported(us1):                     # scenario 7
    assert _mention(us1, "150.75").classification == "unsupported"


def test_us1_non_quantities_excluded(us1):                        # scenario 8
    raws = {m.raw for m in us1.mentions}
    assert not raws & {"2027", "2027년", "4", "7", "3"}
    assert us1.counts["excluded"]["year"] >= 1
    assert us1.counts["excluded"]["product_spec"] >= 1


def test_us1_sign(us1):
    assert _mention(us1, "34.3%").classification == "script"     # direction in words → absolute value
    assert _mention(us1, "+34.3%").classification == "unsupported"  # explicit sign must agree


def test_us1_low_information_numbers(us1):
    no_context = _mention(us1, "11건", 1)                            # no ticker context → not matched at all
    assert no_context.classification == "unsupported" and no_context.matched_path is None
    strong = _mention(us1, "25건")                                   # ticker context 005930.KS
    assert strong.classification == "script" and not strong.weak
    assert strong.ticker_context == "005930.KS"
    assert strong.matched_path == "005930.KS.estimates.revisions.down_30d"
    other = _mention(us1, "11건", 2)                                 # only 000660.KS has 11 → not this ticker's value
    assert other.classification == "unsupported"


def test_us1_weak_match_from_other_ticker(us1):
    m = _mention(us1, "45.67%")                                     # 005930.KS section, value only under 000660.KS
    assert m.classification == "unsupported" and m.weak             # not a pass: another company's value
    assert m.matched_path == "000660.KS.metrics.roe"
    assert not _mention(us1, "52.18%").weak


def test_us1_line_with_several_tickers_and_index(us1):
    idx = _mention(us1, "-11.9%")                                   # index values may be cited in any sentence
    assert idx.classification == "script" and not idx.weak
    assert set(idx.ticker_context.split(",")) == {"005930.KS", "000660.KS"}
    second = _mention(us1, "11건", 0)                                # 000660.KS is also in this line's context
    assert second.classification == "script"
    assert second.matched_path == "000660.KS.estimates.revisions.down_30d"


def test_us1_series_and_status(us1):
    assert _mention(us1, "₩237,500").snapshot_status == "provisional"
    assert _mention(us1, "₩232,000").matched_path == "005930.KS.close.2026-10-13"


def test_us1_mention_ids_are_stable(us1):
    ids = [m.id for m in us1.mentions]
    assert len(ids) == len(set(ids))
    assert _mention(us1, "11건", 1).id.endswith("-11건-2")             # second in '1. 산업 개요'
    m = _mention(us1, "11건", 2)                                     # first in the 005930.KS subsection
    assert m.id.endswith("-11건-1") and len(m.id.split("-")[0]) == 4
