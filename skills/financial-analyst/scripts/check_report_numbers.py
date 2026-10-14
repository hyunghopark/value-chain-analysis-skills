"""Check that every number in an investment-strategy report can be traced to its data snapshot or a citation.

Rules: skills/financial-analyst/references/rules/report-number-check.md
Spec:  specs/002-report-number-check/ in the value-chain-analysis-skills repository.

The checker only reads the report and its paired snapshot (Clean-Slate: no other reports or snapshots).
Network access happens only with --fetch-sources.

Exit codes: 0 no undocumented errors, 1 undocumented errors, 2 cannot run.
"""
import argparse
import hashlib
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


# --- Non-quantities (rules §2) --------------------------------------------------------------

EXCLUDE_CATEGORIES = ('diagram_style', 'citation', 'date', 'ticker_code', 'period_label',
                      'product_spec', 'duration', 'year', 'numbering')
SPEC_UNITS = ('nm', '나노', '단', 'Hi', 'bit', '세대')

MERMAID_STYLE_LINE = re.compile(r'\s*(?:style|classDef|linkStyle|class)\b')
# (category, pattern) in the order they are masked. 'numbering' runs twice: line-head numbers and
# section references before dates, bare one-digit integers after the numbers are read.
MASKS = [
    ('diagram_style', re.compile(r'#[0-9A-Fa-f]{3,8}\b')),
    ('citation', re.compile(r'https?://[^\s)\]>]+|`[^`]*`|\[\d+\]|KI-\d{3}')),
    ('numbering', re.compile(r'^\s*#{1,6}\s*(?:[^\w\s]+\s*)?\d+(?:[.\-]\d+)*[.)]?'
                             r'|^\s*(?:[-*]\s+)?\d+[.)](?=\s)'
                             r'|Section\s*\d+(?:\.\d+)*(?:\s*›\s*\d+(?:-\d+)?번?)?'
                             r'|\d+(?:-\d+)?번째?')),
    ('date', re.compile(r'\d{4}[-.]\d{2}[-.]\d{2}'
                        r'|\d{4}-\d{2}(?!\d)'
                        r'|(?<![\d,.])\d{1,2}-\d{1,2}(?![\d%.,])'
                        r'|\d{1,2}월\s?\d{1,2}(?:\s?~\s?\d{1,2})?일'
                        r'|\d{1,2}월(?:\s?(?:초|중순|상순|하순|말|중))?'
                        r'|\d{1,2}:\d{2}')),
    ('ticker_code', re.compile(r'\^[A-Z]{2,}\d*|(?<![\d,.₩$])\d{6}(?:\.K[SQ])?(?![\d,.])')),
    ('period_label', re.compile(r'\b(?:FY)?\d{1,2}[QH]\d{2}\b|\bFY\d{1,4}\b|\bQ[1-4]\b|\b[1-4]Q\b|\d분기')),
    ('product_spec', re.compile(r'\b[A-Za-z]+-?\d+[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*'
                                r'|\d+-?(?:Hi|bit)\b|\d+(?:nm|나노|세대)|\d+단(?!계|기|위|순)|\b\d[a-wyz]\b')),
    ('duration', re.compile(r'\d+(?:\s?~\s?\d+)?\s?(?:거래일간?|영업일|개월간?|일간|일|년간|주간|시간)'
                            r'|(?<![\d,.])\d{1,3}주(?=\s?(?:최고|최저|고점|저점|범위|신고|신저|동안|이동))'
                            r'|(?<![\d,.$₩])\d{1,2}M\b'
                            r'|(?<![\d,.])\d{1,2}년(?![도대])')),
    ('year', re.compile(r'(?<![\d,.$₩])(?:19|20)\d{2}(?!\d|,\d|\.\d|%|조|억|만|배|건|주)(?:년)?')),
]


def mask_non_quantities(line, in_mermaid=False):
    """Blank out non-quantity notations (keeping positions) and count them by category."""
    counts = dict.fromkeys(EXCLUDE_CATEGORIES, 0)
    if in_mermaid and MERMAID_STYLE_LINE.match(line):
        counts['diagram_style'] += 1
        return ' ' * len(line), counts

    def blank(category):
        def repl(m):
            counts[category] += 1
            return ' ' * len(m.group(0))
        return repl

    for category, pattern in MASKS:
        line = pattern.sub(blank(category), line)
    return line, counts


def extract_numbers(line, in_mermaid=False):
    """Quantities in one line, plus counts of the non-quantities that were left out."""
    masked, counts = mask_non_quantities(line, in_mermaid)
    tokens = []
    for t in parse_numbers(masked):
        if not t.unit and not t.currency and not t.sign and t.decimals == 0 and abs(t.value) < 10:
            counts['numbering'] += 1      # bare one-digit integer: an ordinal or a count word
            continue
        tokens.append(t)
    return tokens, counts


# --- Matching against the snapshot (rules §4) -----------------------------------------------

UNIT_SCALES = {
    '%': (100.0, 1.0), '%p': (100.0, 1.0),
    '조': (1e-12, 1e-4), '억': (1e-8, 1.0), '만': (1e-4,),
    'T': (1e-12,), 'B': (1e-9,), 'M': (1e-6,), 'K': (1e-3,),
    '배': (1.0,), 'x': (1.0,), '건': (1.0,), '주': (1.0,), 'GB': (1.0,), 'TB': (1.0,),
    'bp': (1.0, 1e4), '': (1.0,),
}
FETCH_STATUSES = ('found', 'not_found', 'unverifiable')
LOW_INFO_LIMIT = 100      # integers below this, written without decimals, are 'low information' (rules §4-4)


# --- Body numbers with their citation scope and ticker context (rules §5) -------------------

CITATION_NUMBER = re.compile(r'\[(\d+)\]')
SENTENCE_BREAK = re.compile(r'(?<=다\.)\s+|(?<=\.)\s+(?=\S)|<br\s*/?>')


def scopes(line):
    """Citation scopes in one line: the whole line for a table row, otherwise each sentence."""
    if line.lstrip().startswith('|'):
        return [(0, len(line))]
    spans, start = [], 0
    for m in SENTENCE_BREAK.finditer(line):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(line)))
    return spans


def ticker_pattern(tickers):
    if not tickers:
        return None
    alts = '|'.join(re.escape(t) for t in sorted(tickers, key=len, reverse=True))
    return re.compile(r'(?<![A-Za-z0-9.^])(' + alts + r')(?![A-Za-z0-9])')  # Korean particles may follow


def _heading_title(line):
    return line.lstrip('#').strip()


def extract_mentions(report, tickers=()):
    """Every quantity in the head and body sections, with section, line, context, citations and ticker.

    Returns (mentions, excluded counts by category).
    """
    find_ticker = ticker_pattern(tickers)
    excluded = dict.fromkeys(EXCLUDE_CATEGORIES, 0)
    mentions = []
    seen = {}
    for section in report.sections:
        if section.kind not in ('head', 'body'):
            continue
        heading = section.title or '(머리)'
        heading_ticker = None
        if find_ticker and section.title:
            m = find_ticker.search(section.title)
            heading_ticker = m.group(1) if m else None
        in_code = in_mermaid = False
        for offset, line in enumerate(section.lines):
            line_no = section.start + offset
            if offset == 0 and section.title:
                continue                               # the '## ' heading itself
            if line.startswith('```'):
                in_mermaid = (not in_code) and line.strip().startswith('```mermaid')
                in_code = not in_code
                continue
            if line.startswith('###'):
                heading = _heading_title(line)
                m = find_ticker.search(line) if find_ticker else None
                heading_ticker = m.group(1) if m else None
            tokens, counts = extract_numbers(line, in_mermaid)
            for k, v in counts.items():
                excluded[k] += v
            if not tokens:
                continue
            line_tickers = list(dict.fromkeys(find_ticker.findall(line))) if find_ticker else []
            context_tickers = line_tickers or ([heading_ticker] if heading_ticker else [])
            spans = scopes(line)
            for t in tokens:
                lo, hi = next(((a, b) for a, b in spans if a <= t.start < b), (0, len(line)))
                cites = [int(n) for n in CITATION_NUMBER.findall(line[lo:hi])]
                key = (heading, t.raw)
                seen[key] = seen.get(key, 0) + 1
                mid = f"{hashlib.sha1(heading.encode('utf-8')).hexdigest()[:4]}-{t.raw}-{seen[key]}"
                context = line[max(0, t.start - 40):t.end + 40].strip()
                mentions.append(NumberMention(
                    id=mid, raw=t.raw, value=t.value, unit=t.unit, decimals=t.decimals,
                    explicit_sign=t.sign, section=heading, line=line_no, context=context,
                    ticker_context=','.join(context_tickers) or None, scope_citations=cites))
    return mentions, excluded


# --- Classification (rules §4, §5) ----------------------------------------------------------

@dataclass
class Candidate:
    path: str
    value: float
    status: Optional[str]


def snapshot_candidates(snapshot):
    """Every numeric value in the snapshot (values and series) as a matching candidate."""
    cands = []
    for path, rec in (snapshot.get('values') or {}).items():
        v = rec.get('value') if isinstance(rec, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cands.append(Candidate(path, float(v), rec.get('status')))
    for path, s in (snapshot.get('series') or {}).items():
        for day, v in ((s or {}).get('data') or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cands.append(Candidate(f"{path}.{day}", float(v), None))
    return cands


def snapshot_tickers(snapshot):
    raw = ((snapshot.get('meta') or {}).get('args') or {}).get('tickers') or ''
    return [t.strip() for t in str(raw).split(',') if t.strip()]


def value_matches(m, value):
    """Does snapshot value v, under any scale for the mention's unit, read as the written number?"""
    tol = 0.5 * 10 ** (-m.decimals) + 1e-9
    for scale in UNIT_SCALES.get(m.unit, (1.0,)):
        c = value * scale
        if m.explicit_sign == '-' and c > 0 or m.explicit_sign == '+' and c < 0:
            continue
        if m.explicit_sign:
            if abs(c - m.value) <= tol:
                return True
        elif abs(abs(c) - abs(m.value)) <= tol:
            return True
    return False


def context_filter(ticker_context):
    """Paths a mention may match: its tickers, rule thresholds and indices (rules §4-4)."""
    if not ticker_context:
        return lambda c: True
    prefixes = tuple(t + '.' for t in ticker_context.split(',')) + ('rules.', '^')
    return lambda c: c.path.startswith(prefixes)


def is_low_information(m):
    return m.decimals == 0 and abs(m.value) < LOW_INFO_LIMIT


def classify(mentions, candidates):
    """script (snapshot match) → cited (citation in scope) → unsupported, per rules §5."""
    for m in mentions:
        own = context_filter(m.ticker_context)
        if is_low_information(m):
            # Small integers match by chance: only the context ticker's values count, and without a
            # ticker context they are not compared at all (rules §4-4).
            pool = [c for c in candidates if own(c)] if m.ticker_context else []
        else:
            pool = candidates
        matches = [c for c in pool if value_matches(m, c.value)]
        matches.sort(key=lambda c: not own(c))
        if matches:
            m.matched_path = matches[0].path
            m.snapshot_status = matches[0].status
            m.match_count = len(matches)
        if matches and own(matches[0]):
            m.classification = 'script'
            continue
        m.weak = bool(matches)        # only another company's value matched: a hint, not a pass (rules §4-5)
        if m.scope_citations:
            m.classification = 'cited'
        else:
            m.classification = 'unsupported'
    return mentions


def count_classes(mentions, excluded):
    return {
        'script': sum(m.classification == 'script' for m in mentions),
        'weak': sum(m.weak for m in mentions),
        'cited': sum(m.classification == 'cited' for m in mentions),
        'unsupported': sum(m.classification == 'unsupported' for m in mentions),
        'excluded': dict(excluded),
    }


def check(report_path, snapshot_path=None, fetch_sources=False):
    """Run every check on one report and return a CheckResult."""
    report = load_report(report_path)
    snap_path = find_snapshot(report, snapshot_path)
    snapshot = load_snapshot(snap_path) if snap_path else None
    tickers = snapshot_tickers(snapshot) if snapshot else []
    result = CheckResult(report=report_path, snapshot=snap_path,
                         checked_at=datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M KST'))
    mentions, excluded = extract_mentions(report, tickers)
    classify(mentions, snapshot_candidates(snapshot) if snapshot else [])
    result.mentions = mentions
    result.counts = count_classes(mentions, excluded)
    if not snap_path:
        result.issues.append(Issue('no_snapshot-report', 'no_snapshot', 'error', '머리',
                                   '짝 스냅샷을 찾을 수 없어 스크립트 값 대조를 하지 못했습니다(대조 불가).'))
    result.issues += mention_issues(mentions)
    result.exit_code = exit_code(result.issues)
    return result


def mention_issues(mentions):
    issues = []
    for m in mentions:
        if m.classification != 'unsupported':
            continue
        hint = f" (다른 종목 값 {m.matched_path}와 같음 — 이 문맥의 값이 아님)" if m.weak else ''
        issues.append(Issue(m.id, 'unsupported_number', 'error', f"{m.section} › 줄 {m.line}",
                            f'"{m.raw}" — {m.context}{hint}'))
    return issues


def exit_code(issues):
    return EXIT_ISSUES if any(i.severity == 'error' and not i.documented for i in issues) else EXIT_OK


# --- Output (contracts/cli.md) --------------------------------------------------------------

EXCLUDED_LABELS = {
    'diagram_style': '다이어그램 서식', 'citation': '인용·출처 표기', 'date': '날짜·시각', 'ticker_code': '종목 코드',
    'period_label': '분기·회계 표기', 'product_spec': '제품·규격', 'duration': '기간', 'year': '연도', 'numbering': '번호·개수',
}


def render_summary(result, verbose=False):
    c = result.counts
    excluded = sum((c.get('excluded') or {}).values())
    open_issues = [i for i in result.issues if not i.documented]
    lines = [
        f"## 숫자 점검 — {os.path.basename(result.report)}",
        f"점검 시각: {result.checked_at} · 스냅샷: {os.path.basename(result.snapshot) if result.snapshot else '없음(대조 불가)'}",
        "",
        "| 분류 | 개수 |",
        "|---|---|",
        f"| 스크립트 값 일치 | {c.get('script', 0)} |",
        f"| 인용 출처 있음 | {c.get('cited', 0)} |",
        f"| 근거 없음 | {c.get('unsupported', 0)} |",
        f"| 제외(수량 아님) | {excluded} |",
        "",
        f"### 문제 (기록 안 됨 {len(open_issues)} / 기록됨 {len(result.issues) - len(open_issues)})",
    ]
    lines += [f"- [{i.kind}] {i.location} — {i.message}" for i in open_issues] or ["- 없음"]
    if verbose:
        lines += ["", "### 스크립트 값 일치"]
        lines += [f"- {m.section} › 줄 {m.line} › \"{m.raw}\" → {m.matched_path}"
                  + (f" ({m.snapshot_status})" if m.snapshot_status and m.snapshot_status != 'final' else '')
                  + (f" 외 {m.match_count - 1}곳" if m.match_count > 1 else '')
                  for m in result.mentions if m.classification == 'script']
        lines += ["", "### 인용 출처 있음"]
        lines += [f"- {m.section} › 줄 {m.line} › \"{m.raw}\" → [{', '.join(map(str, m.scope_citations))}]"
                  for m in result.mentions if m.classification == 'cited']
        lines += ["", "### 제외(수량 아님)"]
        lines += [f"- {EXCLUDED_LABELS[k]}: {v}" for k, v in (c.get('excluded') or {}).items() if v]
    return '\n'.join(lines)


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
    return check(args.report, args.snapshot or None, fetch_sources=args.fetch_sources)


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
    print(render_summary(result, verbose=args.verbose))
    return result.exit_code


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
