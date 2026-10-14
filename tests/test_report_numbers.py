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


def _cells(line):
    import re as _re
    return [c.strip() for c in _re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _rules_tables():
    """Tables in the rules document whose first header cell is '키', keyed by the nearest heading."""
    tables, heading, current = [], "", None
    with open(RULES_DOC, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("#"):
                heading = line.lstrip("#").strip()
            if line.startswith("| 키 |"):
                current = {"heading": heading, "header": _cells(line), "rows": []}
                tables.append(current)
            elif current is not None and line.startswith("|") and not line.startswith("|---"):
                current["rows"].append(_cells(line))
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
    import re as _re
    kinds = by("4-2.", "경로 패턴")
    doc_kinds = [(row[0].strip("`"), row[1].strip("`").replace("\\|", "|")) for row in kinds["rows"]]
    assert doc_kinds == [(k, p.pattern) for k, p in crn.PATH_KINDS]
    units = by("4-3.", "대조할 경로 종류(배율)")
    doc_units = {row[0].strip("`"): [(k, float(x)) for k, x in _re.findall(r"`(\w+)` ×([\d.e\-]+)", row[1])]
                 for row in units["rows"]}
    assert doc_units == {k: list(v) for k, v in crn.UNIT_KINDS.items()}
    aliases = by("4-6.", "별칭")
    assert {row[0].strip("`"): tuple(x.strip() for x in row[1].split(",")) for row in aliases["rows"]} == crn.INDEX_ALIASES
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

## 4. 정량 재무 지표 (스크립트 자동 산출 — 수치 수정 금지)

### 3-1. 이익 추정치 동향

| 기업 | 상향 | 하향 |
|---|---|---|
| 005930.KS | 7건 | 25건 |

## 5. 기업별 분석

### 1) 005930.KS (Samsung Electronics)

추정치는 하향 25건이다(Section 4 › 3-1 표). 상향 11건은 이 종목 값이 아니다(Section 4 › 3-1). ROE 45.67%는 다른 종목 값이다.
비중은 0%로 둔다. 하향 25건은 출처 표시 없이 다시 쓴다.

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
    # small integers are never compared with snapshot values (rules §4-5) ...
    no_ref = _mention(us1, "11건", 1)
    assert no_ref.classification == "unsupported" and no_ref.matched_path is None
    # ... but count when the same sentence points at a Section 4 table that shows the same notation
    in_table = _mention(us1, "25건", 0)
    assert in_table.section4_refs == ["3-1"]
    assert in_table.classification == "script" and in_table.matched_path == "section4 › 3-1"
    assert in_table.ticker_context == "005930.KS"
    not_in_table = _mention(us1, "11건", 2)                          # the 3-1 table has no '11건'
    assert not_in_table.classification == "unsupported"
    assert _mention(us1, "25건", 1).classification == "unsupported"  # same number, no table reference
    assert _mention(us1, "0%").classification == "unsupported"       # zero carries no information


def test_us1_weak_match_from_other_ticker(us1):
    m = _mention(us1, "45.67%")                                     # 005930.KS section, value only under 000660.KS
    assert m.classification == "unsupported" and m.weak             # not a pass: another company's value
    assert m.matched_path == "000660.KS.metrics.roe"
    assert not _mention(us1, "52.18%").weak


def test_us1_line_with_several_tickers_and_index(us1):
    idx = _mention(us1, "-11.9%")                                   # index values may be cited in any sentence
    assert idx.classification == "script" and not idx.weak
    assert set(idx.ticker_context.split(",")) == {"005930.KS", "000660.KS"}
    assert _mention(us1, "11건", 0).ticker_context == "005930.KS,000660.KS"


def test_us1_series_and_status(us1):
    assert _mention(us1, "₩237,500").snapshot_status == "provisional"
    assert _mention(us1, "₩232,000").matched_path == "005930.KS.close.2026-10-13"


def test_us1_mention_ids_are_stable(us1):
    ids = [m.id for m in us1.mentions]
    assert len(ids) == len(set(ids))
    assert _mention(us1, "11건", 1).id.endswith("-11건-2")             # second in '1. 산업 개요'
    m = _mention(us1, "11건", 2)                                     # first in the 005930.KS subsection
    assert m.id.endswith("-11건-1") and len(m.id.split("-")[0]) == 4


# --- T011: issues, output, exit codes, read-only ------------------------------------------------

def test_unsupported_numbers_become_issues(us1):
    m = _mention(us1, "12.34%")
    issue = next(i for i in us1.issues if i.id == m.id)
    assert issue.kind == "unsupported_number" and issue.severity == "error" and not issue.documented
    assert "1. 산업 개요" in issue.location and "9" in issue.location
    assert "12.34%" in issue.message
    weak = next(i for i in us1.issues if i.id == _mention(us1, "45.67%").id)
    assert "000660.KS.metrics.roe" in weak.message                  # the hint is shown to the reviewer
    assert us1.exit_code == 1


def test_no_snapshot_is_not_a_silent_pass(tmp_path):
    result = crn.check(write_case(tmp_path, US1_REPORT))             # header names r_data.json, file absent
    assert result.snapshot is None
    assert any(i.kind == "no_snapshot" and i.severity == "error" for i in result.issues)
    assert all(m.classification != "script" for m in result.mentions)
    assert result.exit_code == 1


CLEAN_REPORT = """# 깨끗한 보고서

> **데이터 스냅샷**: `r_data.json`

## 1. 산업 개요

TTM 영업이익률 52.18%를 기록했고 P/B 2.44배이다. 매출 195조 원을 발표했다 [7].

## 8. 참고 문헌 (References)

[7] [기사 제목](https://example.com/news/1) — 2026-10-10
"""


def test_clean_report_exit_0(tmp_path):
    snapshot = dict(US1_SNAPSHOT, section4={"text": "", "sha256": "", "attached_at": ""})  # report has no Section 4
    result = crn.check(write_case(tmp_path, CLEAN_REPORT, snapshot=snapshot))
    assert [i for i in result.issues if i.severity == "error"] == []
    assert result.exit_code == 0


def test_main_json_and_exit_code(tmp_path, capsys):
    path = write_case(tmp_path, US1_REPORT, snapshot=US1_SNAPSHOT)
    out_json = tmp_path / "check.json"
    assert crn.main([path, "--json", str(out_json)]) == 1
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert list(data) == ["report", "snapshot", "checked_at", "counts", "mentions", "section4",
                          "references", "ai_todo", "issues", "exit_code"]
    assert data["exit_code"] == 1
    out = capsys.readouterr().out
    assert "| 스크립트 값 일치 |" in out and "| 근거 없음 |" in out
    assert "12.34%" in out                                           # unsupported numbers are listed
    assert "45.67%" in out and "다른 종목 값" in out


def test_verbose_lists_matches(tmp_path, capsys):
    path = write_case(tmp_path, US1_REPORT, snapshot=US1_SNAPSHOT)
    crn.main([path])
    assert "005930.KS.cycle.opm_ttm" not in capsys.readouterr().out
    crn.main([path, "--verbose"])
    out = capsys.readouterr().out
    assert "005930.KS.cycle.opm_ttm" in out and "제외" in out


def test_checker_is_read_only(tmp_path, monkeypatch):                 # FR-014, constitution VI
    import builtins
    import hashlib
    path = write_case(tmp_path, US1_REPORT, snapshot=US1_SNAPSHOT)
    (tmp_path / "other_report_data.json").write_text("{}", encoding="utf-8")
    (tmp_path / "other_report.md").write_text("# other", encoding="utf-8")
    digest = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
    before = {p: digest(p) for p in (path, str(tmp_path / "r_data.json"))}

    opened = []
    real_open = builtins.open
    def spy(file, mode="r", *args, **kwargs):
        opened.append((os.path.abspath(str(file)), mode))
        return real_open(file, mode, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", spy)
    crn.main([path])
    monkeypatch.undo()

    assert {p: digest(p) for p in before} == before
    assert all("w" not in mode and "a" not in mode for _, mode in opened)
    names = {os.path.basename(p) for p, _ in opened}
    assert names <= {"r.md", "r_data.json", "report-number-check.md"}, names


# --- T012: validation set (SC-001, SC-002, SC-003, SC-006) --------------------------------------

def test_validation_set():
    """SC-001/002/003/006 against human labels (tests/fixtures/002/labels.json).

    expected: script | script_gap | cited | unsupported | excluded. script_gap = shown in Section 4 but missing
    from this (pre-001-fix) snapshot: the checker cannot see it, so 'unsupported' is the right output for it,
    and it is left out of the reviewer-burden ratio because US2 fills those snapshot gaps.
    """
    import time
    labels_path = os.path.join(FIXTURE_DIR, "labels.json")
    with open(labels_path, encoding="utf-8") as f:
        labels = json.load(f)
    if not labels.get("reviewed"):
        pytest.skip("tests/fixtures/002/labels.json 사람 검토 전 (tasks T013) — SC-001~SC-003 미검증")

    started = time.time()
    result = crn.check(os.path.join(FIXTURE_DIR, labels["report"]), os.path.join(FIXTURE_DIR, labels["snapshot"]))
    elapsed = time.time() - started
    actual = {m.id: m.classification for m in result.mentions}

    mention_labels = labels["labels"]
    assert set(actual) == {l["id"] for l in mention_labels}, "labels.json is out of date with the checker's mentions"
    correct = lambda l: actual[l["id"]] == l["expected"] or (l["expected"] == "script_gap" and actual[l["id"]] == "unsupported")
    agree = sum(correct(l) for l in mention_labels) + sum(x["expected"] == "excluded" for x in labels["excluded"])
    total = len(mention_labels) + len(labels["excluded"])
    false_pass = [l["raw"] for l in mention_labels if l["expected"] == "unsupported" and actual[l["id"]] != "unsupported"]
    # quantities the checker left out are never checked: also a silent pass
    false_pass += [x["text"] for x in labels["excluded"] if x["expected"] == "unsupported"]

    assert agree / total >= 0.95, f"SC-001 agreement {agree}/{total}: {[l['raw'] for l in mention_labels if not correct(l)]}"
    assert false_pass == [], f"SC-001 false pass: {false_pass}"

    burden = [l for l in mention_labels if l["expected"] not in ("excluded", "script_gap")]
    unsupported = [l for l in burden if actual[l["id"]] == "unsupported"]
    assert len(unsupported) <= 0.25 * len(burden), f"SC-002 {len(unsupported)}/{len(burden)}"
    flagged = [l for l in mention_labels if actual[l["id"]] == "unsupported" and l["expected"] != "script_gap"]
    noise = [l for l in flagged if l["expected"] == "excluded"]
    assert len(noise) <= 0.05 * max(len(flagged), 1), f"SC-003 {[l['raw'] for l in noise]}"
    assert elapsed <= 10, f"SC-006 {elapsed:.1f}s"


# --- Path kinds and unit compatibility (rules §4-2, §4-3) — false passes found in the validation set

@pytest.mark.parametrize("path, kind", [
    ("^KS11.volume.2026-03-16", "volume"),
    ("005930.KS.flows.2026-10-13.foreign_net_amt", "flow_amount"),
    ("005930.KS.flows.total_5d.foreign_net_amt", "flow_amount"),
    ("005930.KS.flows.2026-10-13.foreign_net_shares", "shares"),
    ("005930.KS.estimates.fy1.down_30d", "count"),
    ("MU.estimates.fy1.analysts_count", "count"),
    ("005930.KS.metrics.debt_to_equity", "percent"),
    ("005930.KS.metrics.dividend_yield", "percent"),
    ("005930.KS.market_context.return_1d", "fraction"),
    ("000660.KS.cycle.opm.2025-12-31", "fraction"),
    ("005930.KS.flows.2026-10-13.foreign_hold_ratio", "fraction"),
    ("005930.KS.pb_band.current_pb", "multiple"),
    ("MU.pb_band.pb.2025-08-31", "multiple"),
    ("005930.KS.scenario.multiple_b", "multiple"),
    ("005930.KS.estimates.fy0.pe", "multiple"),
    ("005930.KS.quote.market_cap", "money"),
    ("000660.KS.close.2026-02-24", "price"),
    ("005930.KS.history.2026-10-14.close", "price"),
    ("005930.KS.quote.fifty_two_week_high", "price"),
    ("005930.KS.estimates.fy1.mean_eps", "price"),
    ("005930.KS.pb_band.floor_price", "price"),
    ("005930.KS.scenario.expected_price_a", "price"),
    ("005930.KS.technical.rsi_14", "other"),
])
def test_path_kind(path, kind):
    assert crn.path_kind(path) == kind


KIND_SNAPSHOT = {
    "meta": {"args": {"tickers": "005930.KS"}},
    "values": {
        "005930.KS.metrics.dividend_yield": {"value": 0.7, "status": "final"},           # percent value: 0.7%
        "005930.KS.scenario.multiple_b": {"value": 6.63, "status": "final"},
        "005930.KS.pb_band.current_pb": {"value": 2.4352, "status": "final"},
        "005930.KS.market_context.return_1d": {"value": 0.0237, "status": "final"},
        "MU.pb_band.pb.2025-08-31": {"value": 2.5, "status": "final"},
        "005930.KS.metrics.beta": {"value": 1.52, "status": "final"},
        "005930.KS.pb_band.low": {"value": 0.807, "status": "final"},
        "005930.KS.flows.2026-10-08.krx_close": {"value": 262000, "status": "final"},
    },
    "series": {"^KS11.volume": {"data": {"2026-03-16": 1.074e14}}},
    "warnings": [],
}

KIND_REPORT = """# 종류 테스트

> **데이터 스냅샷**: `r_data.json`

## 1. 산업 개요

사상 최대 영업이익 107.4조 원을 냈다.
전력 효율 2.5W를 절감했다.
업종 고베타(1.5~2.4)를 감안한다.

## 5. 기업별 분석

### 1) 005930.KS (Samsung Electronics)

순이익 변동성이 70%를 넘는다. 최근 상향 7건이다. 장중 +2.4% 반등했다.
P/B 밴드 최저는 0.81이고, 중심선 ₩262,000 부근에서 저항을 받는다.
"""


def test_unit_kind_compatibility_prevents_false_passes(tmp_path):
    result = crn.check(write_case(tmp_path, KIND_REPORT, snapshot=KIND_SNAPSHOT))
    m = {x.raw: x for x in result.mentions}
    assert m["107.4조"].classification == "unsupported"              # not an index volume ×1e-12
    assert m["2.5W"].classification == "unsupported" and m["2.5W"].unit == "W"   # unknown unit: never compared
    assert m["70%"].classification == "unsupported"                 # dividend_yield is a percent value (0.7%)
    assert m["7건"].classification == "unsupported"                  # counts only match count paths
    plus = m["+2.4%"]
    assert plus.classification == "script"
    assert plus.matched_path == "005930.KS.market_context.return_1d"  # fraction ×100 ranks before other kinds
    assert m["1.5"].classification == "unsupported"                 # two significant digits, no ticker context
    assert m["2.4"].classification == "unsupported"
    assert m["0.81"].classification == "script"                     # same precision, but in 005930.KS context
    assert m["₩262,000"].approximate and m["₩262,000"].classification == "unsupported"   # '부근': approximation


def test_only_latest_series_value_is_a_candidate():
    snap = {"values": {}, "series": {"005930.KS.close": {"data": {"2026-10-08": 262000, "2026-10-13": 232000}}}}
    paths = {c.path for c in crn.snapshot_candidates(snap)}
    assert paths == {"005930.KS.close.2026-10-13"}


# --- Ticker aliases and Section 4 count tables (rules §4-5, §4-6) -------------------------------

ALIAS_SNAPSHOT = {
    "meta": {"args": {"tickers": "005930.KS,MU", "benchmarks": "^KS11,^SOX"}},
    "values": {
        "MU.market_context.return_5d": {"value": -0.0878, "status": "final"},
        "^SOX.market_context.return_5d": {"value": -0.0763, "status": "final"},
        "005930.KS.market_context.return_5d": {"value": -0.124, "status": "final"},
    },
    "series": {}, "warnings": [],
}

ALIAS_REPORT = """# 별칭 테스트

> **데이터 스냅샷**: `r_data.json`

## 1. 산업 개요

삼성전자(005930.KS)와 마이크론(MU)을 비교한다. 필라델피아 반도체 지수(^SOX)도 본다.

| 확인 항목 | 결과 | 출처 |
|---|---|---|
| 동반 등락 | 5거래일 기준 마이크론 -8.8%, SOX -7.6% | 스크립트 산출 |
| 추정치 방향 | **삼성전자**: 상향 7건 / 하향 25건 | 스크립트 산출 (Section 4 › 3-1 표) |

## 4. 정량 재무 지표 (스크립트 자동 산출 — 수치 수정 금지)

#### 3-1. 이익 추정치 동향

| 기업 | 30일 상향 / 하향 건수 |
|---|---|
| **005930.KS** | 상향 7 / 하향 25 |
"""


def test_aliases_from_report_and_index_table(tmp_path):
    result = crn.check(write_case(tmp_path, ALIAS_REPORT, snapshot=ALIAS_SNAPSHOT))
    m = {x.raw: x for x in result.mentions}
    assert m["-8.8%"].classification == "script" and m["-8.8%"].matched_path == "MU.market_context.return_5d"
    assert m["-7.6%"].classification == "script"                    # 'SOX' is a fixed index alias
    assert "MU" in m["-8.8%"].ticker_context.split(",")


def test_counts_in_section4_table_without_unit(tmp_path):
    result = crn.check(write_case(tmp_path, ALIAS_REPORT, snapshot=ALIAS_SNAPSHOT))
    m = {x.raw: x for x in result.mentions}
    assert m["7건"].classification == "script" and m["7건"].matched_path == "section4 › 3-1"
    assert m["25건"].classification == "script"


def test_build_aliases():
    lines = ["삼성전자(005930.KS)는", "**마이크론 (MU)**", "SK하이닉스(000660.KS)", "반도체 지수(^SOX)"]
    aliases = crn.build_aliases(lines, ["005930.KS", "MU", "000660.KS", "^SOX"])
    assert aliases["삼성전자"] == "005930.KS" and aliases["마이크론"] == "MU" and aliases["SK하이닉스"] == "000660.KS"
    assert "지수" not in aliases
    assert aliases["SOX"] == "^SOX" and aliases["코스피"] == "^KS11"


# --- T014: Section 4 baseline and snapshot coverage (US2) ----------------------------------------

S4_BODY = """### 1. 주요 주가

| 기업 | 현재 주가 | 판정 |
|---|---|---|
| **005930.KS** | ₩237,500 | 🟢 매수 고려 |

### 8. ⚠️ 데이터 품질 경고 (스크립트 자동 점검)

- [KI-001] 005930.KS: 수급 표 종가 차이"""

S4_REPORT = """# 섹션 4 테스트

> **데이터 스냅샷**: `r_data.json`

## 1. 산업 개요

본문.

## 4. 정량 재무 지표 및 투자 시그널 매트릭스 (스크립트 자동 산출 — 수치 수정 금지)

{body}

---

## 5. 기업별 분석

분석.
"""


def s4_snapshot(baseline=S4_BODY, warnings=("[KI-001] 005930.KS: 수급 표 종가 차이",), extra_values=None):
    import hashlib
    snap = {
        "meta": {"args": {"tickers": "005930.KS"}},
        "values": {"005930.KS.quote.current_price": {"value": 237500, "status": "final"}},
        "series": {},
        "warnings": [{"ki": "KI-001", "msg": w} for w in warnings],
    }
    snap["values"].update(extra_values or {})
    if baseline is not None:
        snap["section4"] = {"text": baseline, "sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                            "attached_at": "2026-10-14 12:00 KST"}
    return snap


def _s4(tmp_path, body=S4_BODY, **kw):
    return crn.check(write_case(tmp_path, S4_REPORT.format(body=body), snapshot=s4_snapshot(**kw)))


def _kinds(result):
    return {i.kind for i in result.issues}


def test_section4_unchanged(tmp_path):
    r = _s4(tmp_path)
    assert r.section4.baseline == "present"
    assert r.section4.changed_lines == [] and r.section4.snapshot_missing == [] and r.section4.warnings_missing == []
    assert not _kinds(r) & {"section4_changed", "section4_not_in_snapshot", "warning_not_in_snapshot", "no_baseline"}


def test_section4_number_change_detected(tmp_path):
    r = _s4(tmp_path, body=S4_BODY.replace("₩237,500", "₩238,000"))
    (c,) = r.section4.changed_lines
    assert "₩238,000" in c["current"] and "₩237,500" in c["original"]
    assert c["line"] > 0
    assert "section4_changed" in _kinds(r)


def test_section4_verdict_change_detected(tmp_path):
    r = _s4(tmp_path, body=S4_BODY.replace("🟢 매수 고려", "🔴 신중 접근"))
    assert len(r.section4.changed_lines) == 1
    assert "section4_changed" in _kinds(r)


def test_section4_missing_baseline(tmp_path):
    r = _s4(tmp_path, baseline=None)
    assert r.section4.baseline == "missing"
    assert "no_baseline" in _kinds(r)


def test_section4_warning_not_in_snapshot(tmp_path):
    r = _s4(tmp_path, warnings=())
    assert r.section4.warnings_missing == ["[KI-001] 005930.KS: 수급 표 종가 차이"]
    assert "warning_not_in_snapshot" in _kinds(r)


def test_section4_number_not_in_snapshot(tmp_path):
    body = S4_BODY.replace("| **005930.KS** | ₩237,500 | 🟢 매수 고려 |",
                           "| **005930.KS** | ₩237,500 | 🟢 매수 고려 |\n| **005930.KS** | ₩999,999 | 🟡 |")
    r = _s4(tmp_path, body=body, baseline=body)
    assert [m["raw"] for m in r.section4.snapshot_missing] == ["₩999,999"]
    assert "section4_not_in_snapshot" in _kinds(r)
