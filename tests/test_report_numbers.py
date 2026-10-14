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
