"""Check that every number in an investment-strategy report can be traced to its data snapshot or a citation.

Rules: skills/financial-analyst/references/rules/report-number-check.md
Spec:  specs/002-report-number-check/ in the value-chain-analysis-skills repository.

The checker only reads the report and its paired snapshot (Clean-Slate: no other reports or snapshots).
Network access happens only with --fetch-sources.

Exit codes: 0 no undocumented errors, 1 undocumented errors, 2 cannot run.
"""
import argparse
import datetime
import difflib
import hashlib
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
    section4_refs: List[str] = field(default_factory=list)
    approximate: bool = False
    classification: str = "unsupported"   # script | cited | unsupported
    weak: bool = False
    matched_path: Optional[str] = None
    match_count: int = 0
    snapshot_status: Optional[str] = None
    currency: Optional[str] = None


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
        if not unit:
            letters = re.match(r'[A-Za-z]+', text[end:])
            if letters:                      # a unit we do not compare (2.5W, 2.5Tbps): kept, never matched
                unit = letters.group(0)
                end += len(unit)
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
                                r'|\d+-?(?:Hi|bit)\b|\d+(?:nm|나노|세대)|\d+단(?!계|기|위|순)|\b\d[a-wyz]\b|\b\d+(?:\.\d+)?D\b')),
    ('duration', re.compile(r'\d+(?:\s?~\s?\d+)?\s?(?:거래일간?|영업일|개월간?|일간|일|년간|주간|시간|분(?!기))'
                            r'|(?<![\d,.])\d{1,3}주(?=\s?(?:최고|최저|고점|저점|범위|신고|신저|동안|이동))'
                            r'|(?<![\d,.$₩])\d{1,2}M\b'
                            r'|(?<![\d,.])\d{1,2}년(?![도대])')),
    ('year', re.compile(r'(?<![\d,.$₩])(?:19|20)\d{2}(?!\d|,\d|\.\d|%|조|억|만|배|건|주)(?:년)?')),
]


def mask_non_quantities(line, in_mermaid=False, found=None):
    """Blank out non-quantity notations (keeping positions) and count them by category.

    If a list is given as found, (category, text) of every blanked notation is appended to it.
    """
    counts = dict.fromkeys(EXCLUDE_CATEGORIES, 0)
    if in_mermaid and MERMAID_STYLE_LINE.match(line):
        counts['diagram_style'] += 1
        if found is not None:
            found.append(('diagram_style', line.strip()))
        return ' ' * len(line), counts

    def blank(category):
        def repl(m):
            counts[category] += 1
            if found is not None:
                found.append((category, m.group(0)))
            return ' ' * len(m.group(0))
        return repl

    for category, pattern in MASKS:
        line = pattern.sub(blank(category), line)
    return line, counts


def extract_numbers(line, in_mermaid=False, found=None):
    """Quantities in one line, plus counts of the non-quantities that were left out."""
    masked, counts = mask_non_quantities(line, in_mermaid, found)
    tokens = []
    for t in parse_numbers(masked):
        if not t.unit and not t.currency and not t.sign and t.decimals == 0 and abs(t.value) < 10:
            counts['numbering'] += 1      # bare one-digit integer: an ordinal or a count word
            if found is not None:
                found.append(('numbering', t.raw))
            continue
        tokens.append(t)
    return tokens, counts


# --- Matching against the snapshot (rules §4) -----------------------------------------------

# Snapshot path kinds: the first pattern that matches (re.search on the whole path) wins.
PATH_KINDS = [(kind, re.compile(pattern)) for kind, pattern in (
    ('volume', r'\.volume(\.|$)'),
    ('flow_amount', r'\.flows\.[^.]+\.\w+_amt$'),
    ('shares', r'_shares$'),
    ('count', r'(up|down)_30d$|_count$'),
    ('percent', r'\.(debt_to_equity|deviation_lower|deviation_upper|dividend_yield)$|_pct$'),
    ('fraction', r'\.(return_\w+|drawdown_52w|\w*margin|roe|roa|\w*growth|payout_ratio|held_percent_\w+'
                 r'|short_percent_\w+|foreign_hold_ratio|percentile|upside\w*|opm_ttm)$|\.cycle\.opm\.'),
    ('multiple', r'\.(beta|current_ratio|ev_to_\w+|forward_pe|trailing_pe|peg_ratio|price_to_\w+|multiple_[ab]|pe)$'
                 r'|\.pb_band\.(pb\.|high$|low$|median$|current_pb$)'),
    ('money', r'\.(market_cap\w*)$|\.audit\.'),
    ('price', r'(close|price|eps|_high|_low|bps|sma_20|bollinger_\w+|book_value|dividend_rate)(_[ab])?(\.|$)|\.history\.|\.target'),
    ('other', r'.'),
)]

# Written unit -> ((path kind, scale), ...) in priority order. Units not listed are never compared.
UNIT_KINDS = {
    '%': (('fraction', 100.0), ('percent', 1.0)),
    '%p': (('fraction', 100.0), ('percent', 1.0)),
    '조': (('money', 1e-12), ('flow_amount', 1e-4)),
    '억': (('money', 1e-8), ('flow_amount', 1.0)),
    '만': (('money', 1e-4), ('shares', 1e-4), ('volume', 1e-4)),
    'T': (('money', 1e-12),),
    'B': (('money', 1e-9),),
    'M': (('money', 1e-6), ('shares', 1e-6), ('volume', 1e-6)),
    'K': (('money', 1e-3),),
    '배': (('multiple', 1.0),),
    'x': (('multiple', 1.0),),
    '건': (('count', 1.0),),
    '주': (('shares', 1.0), ('volume', 1.0)),
    'bp': (('fraction', 1e4), ('percent', 100.0)),
    '(통화)': (('price', 1.0), ('money', 1.0)),
    '(없음)': (('multiple', 1.0), ('price', 1.0), ('count', 1.0), ('other', 1.0)),
}


def path_kind(path):
    return next(kind for kind, pattern in PATH_KINDS if pattern.search(path))


def unit_key(m):
    if m.unit:
        return m.unit
    return '(통화)' if m.currency else '(없음)'
FETCH_STATUSES = ('found', 'not_found', 'unverifiable')
LOW_INFO_LIMIT = 100      # integers below this, written without decimals, are 'low information' (rules §4-4)


# --- Body numbers with their citation scope and ticker context (rules §5) -------------------

CITATION_NUMBER = re.compile(r'\[(\d+)\]')
SECTION4_REF = re.compile(r'Section\s*4\s*›\s*(\d+(?:-\d+)?)')
SECTION4_TABLE = re.compile(r'^#{3,4}\s*(?:[^\w\s]+\s*)?(\d+(?:-\d+)?)\.')
APPROXIMATE_AFTER = re.compile(r'\s?(?:원\s?)?(?:부근|내외|안팎|가량|전후)')
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


INDEX_ALIASES = {
    '^KS11': ('KOSPI', '코스피'),
    '^KQ11': ('KOSDAQ', '코스닥'),
    '^SOX': ('SOX', '필라델피아 반도체'),
    '^GSPC': ('S&P 500', 'S&P500'),
    '^IXIC': ('NASDAQ', '나스닥'),
}
ALIAS_STOPWORDS = {'지수', '기업', '종목', '티커', '코드'}


def build_aliases(lines, tickers):
    """Names written as 'NAME(TICKER)' in the report, plus the fixed index aliases (rules §4-6)."""
    aliases = {}
    text = '\n'.join(lines)
    for t in tickers:
        for m in re.finditer(r'([A-Za-z가-힣][A-Za-z가-힣0-9&]*)\s?\(\s?' + re.escape(t) + r'\s?\)', text):
            name = m.group(1)
            if len(name) >= 2 and name not in ALIAS_STOPWORDS and name != t:
                aliases.setdefault(name, t)
    for index, names in INDEX_ALIASES.items():
        for name in names:
            aliases.setdefault(name, index)
    return aliases


def ticker_pattern(tickers, aliases=None):
    """Regex for ticker codes and aliases, and the map from matched text to ticker."""
    names = {t: t for t in tickers}
    names.update(aliases or {})
    if not names:
        return None, {}
    alts = '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    # Korean particles may follow a name; a Latin letter or digit may not.
    return re.compile(r'(?<![A-Za-z0-9.^가-힣])(' + alts + r')(?![A-Za-z0-9])'), names


def _heading_title(line):
    return line.lstrip('#').strip()


def extract_mentions(report, tickers=(), excluded_items=None):
    """Every quantity in the head and body sections, with section, line, context, citations and ticker.

    Returns (mentions, excluded counts by category). If a list is given as excluded_items,
    {'line', 'category', 'text', 'context'} of every left-out notation is appended to it.
    """
    find_ticker, ticker_of = ticker_pattern(tickers, build_aliases(report.lines, tickers))
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
            heading_ticker = ticker_of[m.group(1)] if m else None
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
                heading_ticker = ticker_of[m.group(1)] if m else None
            found = [] if excluded_items is not None else None
            tokens, counts = extract_numbers(line, in_mermaid, found)
            for category, text in found or []:
                excluded_items.append({'line': line_no, 'category': category, 'text': text,
                                       'context': line.strip()[:120]})
            for k, v in counts.items():
                excluded[k] += v
            if not tokens:
                continue
            line_tickers = list(dict.fromkeys(ticker_of[n] for n in find_ticker.findall(line))) if find_ticker else []
            context_tickers = line_tickers or ([heading_ticker] if heading_ticker else [])
            spans = scopes(line)
            for t in tokens:
                lo, hi = next(((a, b) for a, b in spans if a <= t.start < b), (0, len(line)))
                cites = [int(n) for n in CITATION_NUMBER.findall(line[lo:hi])]
                refs = SECTION4_REF.findall(line[lo:hi])
                key = (heading, t.raw)
                seen[key] = seen.get(key, 0) + 1
                mid = f"{hashlib.sha1(heading.encode('utf-8')).hexdigest()[:4]}-{t.raw}-{seen[key]}"
                context = line[max(0, t.start - 40):t.end + 40].strip()
                mentions.append(NumberMention(
                    id=mid, raw=t.raw, value=t.value, unit=t.unit, decimals=t.decimals,
                    explicit_sign=t.sign, section=heading, line=line_no, context=context, currency=t.currency,
                    ticker_context=','.join(context_tickers) or None, scope_citations=cites, section4_refs=refs,
                    approximate=bool(APPROXIMATE_AFTER.match(line, t.end))))
    return mentions, excluded


# --- Classification (rules §4, §5) ----------------------------------------------------------

@dataclass
class Candidate:
    path: str
    value: float
    status: Optional[str]
    kind: str = 'other'


def snapshot_candidates(snapshot):
    """Numeric snapshot values as matching candidates: every value, and the latest day of each series.

    Older series days are left out: reports cite current prices, and the dated values that Section 4
    shows are recorded under values (rules §4-2).
    """
    cands = []
    for path, rec in (snapshot.get('values') or {}).items():
        v = rec.get('value') if isinstance(rec, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            cands.append(Candidate(path, float(v), rec.get('status'), path_kind(path)))
    for path, s in (snapshot.get('series') or {}).items():
        data = (s or {}).get('data') or {}
        if data:
            day = max(data)
            v = data[day]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                full = f"{path}.{day}"
                cands.append(Candidate(full, float(v), None, path_kind(full)))
    return cands


def section4_tables(report):
    """Numbers shown in each Section 4 table, keyed by the table number ('1-1', '3-1', '7')."""
    tables, current = {}, None
    for section in report.sections:
        if section.kind != 'section4':
            continue
        for line in section.lines[1:]:
            m = SECTION4_TABLE.match(line)
            if m:
                current = m.group(1)
                continue
            if current:
                # keep one-digit counts ('상향 7 / 하향 25'): they are table values here, not ordinals
                tables.setdefault(current, []).extend(parse_numbers(mask_non_quantities(line)[0]))
    return tables


def snapshot_tickers(snapshot):
    """Analysed tickers and benchmark indices named in the snapshot's run arguments."""
    args = (snapshot.get('meta') or {}).get('args') or {}
    raw = f"{args.get('tickers') or ''},{args.get('benchmarks') or ''}"
    return list(dict.fromkeys(t.strip() for t in raw.split(',') if t.strip()))


def match_rank(m, cand):
    """Priority (0 = best) at which a candidate reads as the written number, or None (rules §4-1 to §4-4)."""
    tol = 0.5 * 10 ** (-m.decimals) + 1e-9
    for rank, (kind, scale) in enumerate(UNIT_KINDS.get(unit_key(m), ())):
        if cand.kind != kind:
            continue
        c = cand.value * scale
        if m.explicit_sign == '-' and c > 0 or m.explicit_sign == '+' and c < 0:
            continue
        if m.explicit_sign:
            if abs(c - m.value) <= tol:
                return rank
        elif abs(abs(c) - abs(m.value)) <= tol:
            return rank
    return None


def context_filter(ticker_context):
    """Paths a mention may match: its tickers, rule thresholds and indices (rules §4-4)."""
    if not ticker_context:
        return lambda c: True
    prefixes = tuple(t + '.' for t in ticker_context.split(',')) + ('rules.', '^')
    return lambda c: c.path.startswith(prefixes)


def is_low_information(m):
    return m.value == 0 or (m.decimals == 0 and abs(m.value) < LOW_INFO_LIMIT)


def significant_digits(m):
    digits = f"{abs(m.value):.{m.decimals}f}".replace('.', '').lstrip('0')
    return len(digits if m.decimals else digits.rstrip('0'))


def in_section4_table(m, tables):
    """The referenced Section 4 table that shows the same notation (unit, currency, value), or None."""
    for ref in m.section4_refs:
        for t in tables.get(ref, []):
            same_sign = not m.explicit_sign or (t.value < 0) == (m.value < 0)
            same_unit = t.unit == m.unit or (m.unit == '건' and not t.unit)    # tables show counts bare
            if same_unit and t.currency == m.currency and abs(t.value) == abs(m.value) and same_sign:
                return ref
    return None


def classify(mentions, candidates, section4=None):
    """script (snapshot match) → cited (citation in scope) → unsupported, per rules §5."""
    for m in mentions:
        own = context_filter(m.ticker_context)
        if is_low_information(m):
            # Small integers and zero match some snapshot value by chance: they count only when the
            # sentence points at a Section 4 table that shows the same notation (rules §4-5).
            ref = in_section4_table(m, section4 or {})
            if ref:
                m.classification, m.matched_path = 'script', f"section4 › {ref}"
            else:
                m.classification = 'cited' if m.scope_citations else 'unsupported'
            continue
        if m.approximate:
            # '₩262,000 부근': an approximation is not the script value itself (rules §4-8)
            m.classification = 'cited' if m.scope_citations else 'unsupported'
            continue
        pool = candidates
        if significant_digits(m) <= 2:
            # Two significant digits (2.4, 0.81, ₩380,000) still collide: only the context's own paths,
            # and nothing without a ticker context (rules §4-5).
            pool = [c for c in candidates if own(c)] if m.ticker_context else []
        ranked = [(c, match_rank(m, c)) for c in pool]
        ranked = sorted(((c, r) for c, r in ranked if r is not None), key=lambda cr: (not own(cr[0]), cr[1]))
        matches = [c for c, _ in ranked]
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
    # Without the snapshot nothing is verifiable, not even Section 4 (its baseline lives in the snapshot).
    classify(mentions, snapshot_candidates(snapshot) if snapshot else [], section4_tables(report) if snapshot else {})
    result.mentions = mentions
    result.counts = count_classes(mentions, excluded)
    if not snap_path:
        result.issues.append(Issue('no_snapshot-report', 'no_snapshot', 'error', '머리',
                                   '짝 스냅샷을 찾을 수 없어 스크립트 값 대조를 하지 못했습니다(대조 불가).'))
    if snapshot:
        result.section4 = check_section4(report, snapshot, snapshot_candidates(snapshot))
        result.issues += section4_issues(result.section4)
    result.issues += mention_issues(mentions)
    result.exit_code = exit_code(result.issues)
    return result


WARNINGS_TABLE = re.compile(r'^#{3,4}\s*(?:[^\w\s]+\s*)?8\.')


def section4_region(section):
    """(line number, text) of Section 4 from the line after its heading to the next '---', trimmed."""
    pairs = []
    for offset, line in enumerate(section.lines[1:], start=1):
        if line.strip() == '---':
            break
        pairs.append((section.start + offset, line.rstrip()))
    while pairs and not pairs[0][1].strip():
        pairs.pop(0)
    while pairs and not pairs[-1][1].strip():
        pairs.pop()
    return pairs


def _trimmed(lines):
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def check_section4(report, snapshot, candidates):
    """Edits since generation (against the snapshot's baseline) and Section 4 numbers missing from it."""
    chk = Section4Check()
    sec = next((s for s in report.sections if s.kind == 'section4'), None)
    current = section4_region(sec) if sec else []
    first = current[0][0] if current else (sec.start + 1 if sec else 0)
    baseline = (snapshot.get('section4') or {}).get('text')
    if baseline is not None:
        chk.baseline = 'present'
        original = _trimmed(baseline.split('\n'))
        now = [text for _, text in current]
        ops = difflib.SequenceMatcher(a=original, b=now, autojunk=False).get_opcodes()
        for tag, i1, i2, j1, j2 in ops:
            if tag == 'equal':
                continue
            for k in range(max(i2 - i1, j2 - j1)):
                cur = current[j1 + k] if j1 + k < j2 else None
                chk.changed_lines.append({
                    'line': cur[0] if cur else (current[j1 - 1][0] if j1 > 0 else first),
                    'current': cur[1] if cur else None,
                    'original': original[i1 + k] if i1 + k < i2 else None,
                })
        lines = [(first + i, text) for i, text in enumerate(original)]
    else:
        lines = current

    # Section 4 is script output: every number in it should be a snapshot value (FR-015). The
    # information-content rules of the body check do not apply; only presence is asked.
    warning_msgs = {(w or {}).get('msg', '').strip() for w in (snapshot.get('warnings') or [])}
    in_warnings = False
    for line_no, text in lines:
        if text.startswith('#'):
            in_warnings = bool(WARNINGS_TABLE.match(text))
            continue
        if in_warnings:
            if text.startswith('- ') and text[2:].strip() not in warning_msgs:
                chk.warnings_missing.append(text[2:].strip())
            continue
        for t in extract_numbers(text)[0]:
            probe = NumberMention(id='', raw=t.raw, value=t.value, unit=t.unit, decimals=t.decimals,
                                  explicit_sign=t.sign, section='4', line=line_no, context='', currency=t.currency)
            if not any(match_rank(probe, c) is not None for c in candidates):
                chk.snapshot_missing.append({'line': line_no, 'raw': t.raw,
                                             'context': text[max(0, t.start - 40):t.end + 40].strip()})
    return chk


def section4_issues(chk):
    issues = []
    if chk.baseline == 'missing':
        issues.append(Issue('no_baseline-section4', 'no_baseline', 'error', 'Section 4',
                            '스냅샷에 Section 4 기준본이 없어 생성 후 수정 여부를 확인하지 못했습니다.'))
    for c in chk.changed_lines:
        issues.append(Issue(f"section4_changed-{c['line']}", 'section4_changed', 'error', f"Section 4 › 줄 {c['line']}",
                            f'현재 "{c["current"] or "(삭제됨)"}" / 기준본 "{c["original"] or "(없음)"}"'))
    for m in chk.snapshot_missing:
        issues.append(Issue(f"section4_not_in_snapshot-{m['line']}-{m['raw']}", 'section4_not_in_snapshot', 'error',
                            f"Section 4 › 줄 {m['line']}", f'"{m["raw"]}"가 스냅샷에 없습니다 — {m["context"]}'))
    for n, w in enumerate(chk.warnings_missing, start=1):
        issues.append(Issue(f"warning_not_in_snapshot-{n}", 'warning_not_in_snapshot', 'error', 'Section 4 › 8번',
                            f'데이터 품질 경고가 스냅샷 warnings에 없습니다: {w}'))
    return issues


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
