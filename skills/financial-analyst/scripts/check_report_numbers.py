"""Check that every number in an investment-strategy report can be traced to its data snapshot or a citation.

Rules: skills/financial-analyst/references/rules/report-number-check.md
Spec:  specs/002-report-number-check/ in the value-chain-analysis-skills repository.

The checker only reads the report and its paired snapshot (Clean-Slate: no other reports or snapshots).
Network access happens only with --fetch-sources.

Exit codes: 0 no undocumented errors, 1 undocumented errors, 2 cannot run.
"""
import argparse
import datetime
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from typing import List, Optional

KST = datetime.timezone(datetime.timedelta(hours=9))

EXIT_OK, EXIT_ISSUES, EXIT_CANNOT_RUN = 0, 1, 2


# --- Data model (specs/002-report-number-check/data-model.md §2) ----------------------------

@dataclass
class Section:
    kind: str              # head | body | section4 | references | check
    title: str             # heading text without the leading '## '
    start: int             # 1-based line number of lines[0]
    lines: List[str]


@dataclass
class Report:
    path: str
    lines: List[str]
    sections: List[Section]


@dataclass
class NumberMention:
    id: str
    raw: str
    value: float
    unit: str
    decimals: int
    explicit_sign: Optional[str]
    section: str
    line: int
    context: str
    ticker_context: Optional[str] = None
    scope_citations: List[int] = field(default_factory=list)
    classification: str = "unsupported"   # script | cited | unsupported
    weak: bool = False
    matched_path: Optional[str] = None
    match_count: int = 0
    snapshot_status: Optional[str] = None


@dataclass
class Reference:
    number: int
    title: Optional[str]
    date: Optional[str]
    url: Optional[str]
    line: int
    cited: bool = False
    problems: List[str] = field(default_factory=list)
    fetch: Optional[dict] = None


@dataclass
class Section4Check:
    baseline: str = "missing"             # present | missing
    changed_lines: List[dict] = field(default_factory=list)
    snapshot_missing: List[dict] = field(default_factory=list)
    warnings_missing: List[str] = field(default_factory=list)


@dataclass
class Issue:
    id: str
    kind: str
    severity: str                         # error | warning
    location: str
    message: str
    documented: bool = False


@dataclass
class CheckResult:
    report: str
    snapshot: Optional[str]
    checked_at: str
    counts: dict = field(default_factory=dict)
    mentions: List[NumberMention] = field(default_factory=list)
    section4: Section4Check = field(default_factory=Section4Check)
    references: List[Reference] = field(default_factory=list)
    ai_todo: List[dict] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    exit_code: int = EXIT_OK


# --- Reading the report ---------------------------------------------------------------------

def _section_kind(title):
    if re.match(r'4\.', title):
        return 'section4'
    if '참고 문헌' in title or 'References' in title:
        return 'references'
    if '숫자 점검 결과' in title:
        return 'check'
    return 'body'


def load_report(path):
    """Split the report into sections at '## ' headings (rules §1).

    The disclaimer after the last '---' line of the report is split off as its own body section,
    so it is checked like body text and never read as a reference entry.
    """
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    sections = []
    current = Section('head', '', 1, [])
    in_code = False
    for no, line in enumerate(lines, start=1):
        if line.startswith('```'):
            in_code = not in_code
        if not in_code and line.startswith('## '):
            sections.append(current)
            title = line[3:].strip()
            current = Section(_section_kind(title), title, no, [line])
        else:
            current.lines.append(line)
    sections.append(current)

    last = sections[-1]
    seps = [i for i, line in enumerate(last.lines) if line.strip() == '---']
    if last.kind != 'head' and seps and any(line.strip() for line in last.lines[seps[-1] + 1:]):
        cut = seps[-1]
        sections.append(Section('body', '(면책 문구)', last.start + cut, last.lines[cut:]))
        last.lines = last.lines[:cut]

    return Report(path, lines, [s for s in sections if s.kind != 'head' or any(x.strip() for x in s.lines)])


SNAPSHOT_LINE = re.compile(r'\*\*데이터 스냅샷\*\*\s*:\s*`([^`]+)`')


def find_snapshot(report, override=None):
    """Return the paired snapshot path named in the report header (same folder), or None if absent."""
    if override:
        return override if os.path.exists(override) else None
    head = next((s for s in report.sections if s.kind == 'head'), None)
    for line in (head.lines if head else report.lines[:20]):
        m = SNAPSHOT_LINE.search(line)
        if m:
            path = os.path.join(os.path.dirname(os.path.abspath(report.path)), os.path.basename(m.group(1)))
            return path if os.path.exists(path) else None
    return None


def load_snapshot(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# --- Reading numbers (rules §3) -------------------------------------------------------------

@dataclass
class NumberToken:
    raw: str
    value: float
    unit: str
    decimals: int
    sign: Optional[str]                   # '+', '-' or None
    currency: Optional[str]
    start: int
    end: int


NUMBER = re.compile(
    r'(?P<sign>[+\-−])?(?P<cur>[₩$])?'
    r'(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)'
    r'(?P<unit>%p|%|배|조|억|만|건|GB|TB|bp|주|(?:x|T|B|M|K)(?![A-Za-z]))?')
EOK_AFTER_JO = re.compile(r'\s?(\d{1,3}(?:,\d{3})+|\d+)억')
RANGE_SEP = re.compile(r'\s?[~∼]\s?$')


def parse_numbers(text):
    """Read every number in text as (value, unit, decimals, sign, currency) with its position.

    '3조 9,334억' is one amount (3.9334 조), '50~60%' lends '%' to 50, and a '-' glued to a preceding
    letter or digit ('1-1', '10-14') is a separator, not a sign.
    """
    tokens = []
    pos = 0
    while True:
        m = NUMBER.search(text, pos)
        if not m:
            break
        start, end = m.start(), m.end()
        sign = m.group('sign')
        if sign and start > 0 and text[start - 1].isalnum():
            sign = None
            start += 1
        num_start = m.start('num')
        if num_start > 0 and text[num_start - 1].isascii() and text[num_start - 1].isalpha():
            pos = end              # digits glued to a Latin word (HBM4): not a quantity
            continue
        num = m.group('num')
        value = float(num.replace(',', ''))
        decimals = len(num.split('.')[1]) if '.' in num else 0
        unit = m.group('unit') or ''
        if unit == '조' and decimals == 0:
            eok = EOK_AFTER_JO.match(text, end)
            if eok:
                value += float(eok.group(1).replace(',', '')) / 1e4
                decimals = 4
                end = eok.end()
        if sign in ('-', '−'):
            sign = '-'
            value = -value
        tokens.append(NumberToken(text[start:end], value, unit, decimals, sign, m.group('cur'), start, end))
        pos = end

    for cur, nxt in zip(tokens, tokens[1:]):
        if not cur.unit and not cur.currency and nxt.unit and RANGE_SEP.match(text[cur.end:nxt.start]):
            cur.unit = nxt.unit
    return tokens


# --- Entry point ----------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(description="Check that report numbers trace to the data snapshot or a citation.")
    parser.add_argument("report", help="Report markdown file")
    parser.add_argument("--snapshot", default="", help="Paired snapshot JSON (default: the file named in the report header)")
    parser.add_argument("--json", default="", help="Write the structured result to this JSON file")
    parser.add_argument("--section", action="store_true", help="Print only the '숫자 점검 결과' block to paste into the report")
    parser.add_argument("--fetch-sources", action="store_true", help="Download cited articles and look for the cited numbers (network, local only)")
    parser.add_argument("--verbose", action="store_true", help="Also list matched and excluded numbers")
    return parser


def run(args):
    report = load_report(args.report)
    snapshot_path = find_snapshot(report, args.snapshot or None)
    result = CheckResult(report=args.report, snapshot=snapshot_path,
                         checked_at=datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M KST'))
    return result


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return EXIT_CANNOT_RUN if e.code else EXIT_OK
    if not os.path.isfile(args.report):
        print(f"보고서를 찾을 수 없습니다: {args.report}", file=sys.stderr)
        return EXIT_CANNOT_RUN
    try:
        result = run(args)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"점검을 실행할 수 없습니다: {e}", file=sys.stderr)
        return EXIT_CANNOT_RUN
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, ensure_ascii=False, indent=2)
    return result.exit_code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
