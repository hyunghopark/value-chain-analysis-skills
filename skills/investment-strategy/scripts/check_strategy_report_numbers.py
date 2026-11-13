"""Unified number and placeholder verification tool for 3-tier investment-strategy reports.

Validates that:
1. Section 4 hash and text match the unified data snapshot baseline.
2. Zero unpopulated placeholders ([AI_TODO], [수치], [XX%], [🟢/🟡/🔴], [출처], [방어 유지], etc.) remain.
3. Every number mentioned outside Section 4 traces to snapshot values (macro, sector, financial, Socratic)
   or valid citations.
4. References in Section 8 are correctly formatted and cited.

Exit codes:
0: All checks pass (no undocumented errors or leftover placeholders).
1: Undocumented errors, modified Section 4, unpopulated placeholders, or untraced numbers.
2: Execution failure (missing files or invalid arguments).
"""

import argparse
import datetime
import difflib
import hashlib
import io
import json
import os
import re
import sys
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

KST = datetime.timezone(datetime.timedelta(hours=9))

EXIT_OK = 0
EXIT_ISSUES = 1
EXIT_CANNOT_RUN = 2


# --- Data Models -----------------------------------------------------------------------------

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
class NumberToken:
    raw: str
    value: float
    unit: str
    decimals: int
    sign: Optional[str]
    currency: Optional[str]
    start: int
    end: int


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
class Candidate:
    path: str
    value: float
    status: Optional[str]
    kind: str = 'other'


@dataclass
class CheckResult:
    report: str
    snapshot: Optional[str]
    checked_at: str
    counts: dict = field(default_factory=dict)
    mentions: List[NumberMention] = field(default_factory=list)
    section4: Section4Check = field(default_factory=Section4Check)
    references: List[Reference] = field(default_factory=list)
    placeholders: List[dict] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    exit_code: int = EXIT_OK


# --- Reading & Parsing Report ----------------------------------------------------------------

def _section_kind(title: str) -> str:
    if re.match(r'4\.', title):
        return 'section4'
    if '참고 문헌' in title or 'References' in title:
        return 'references'
    if '숫자 점검 결과' in title:
        return 'check'
    return 'body'


def load_report(path: str) -> Report:
    """Split the report into sections at '## ' headings."""
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


def find_snapshot(report: Report, override: Optional[str] = None) -> Optional[str]:
    """Return the paired snapshot path named in the report header, or override if specified."""
    if override:
        return override if os.path.exists(override) else None
    head = next((s for s in report.sections if s.kind == 'head'), None)
    for line in (head.lines if head else report.lines[:20]):
        m = SNAPSHOT_LINE.search(line)
        if m:
            path = os.path.join(os.path.dirname(os.path.abspath(report.path)), os.path.basename(m.group(1)))
            if os.path.exists(path):
                return path
    # Fallback to report base name
    base_no_ext, _ = os.path.splitext(report.path)
    fallback = f"{base_no_ext}_data.json"
    if os.path.exists(fallback):
        return fallback
    return None


def load_snapshot(path: str) -> Dict[str, Any]:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# --- Number Extraction & Masks ---------------------------------------------------------------

NUMBER_PATTERN = re.compile(
    r'(?<![A-Za-z0-9_])'
    r'(?:(?P<cur>[₩$€¥£]|NT\$|₫)\s*)?'
    r'(?P<sign>[±+\-−])?'
    r'(?P<int>\d{1,3}(?:,\d{3})+|\d+)'
    r'(?:\.(?P<dec>\d+))?'
    r'(?P<unit>%p|%|조|억|만|T|B|M|K|배|x|건|주|bp|bps|pt)?'
    r'(?![A-Za-z0-9_])'
)

RANGE_SEP = re.compile(r'^\s*(?:~|–|—|-)\s*$')


def parse_numbers(text: str) -> List[NumberToken]:
    tokens = []
    pos = 0
    for m in NUMBER_PATTERN.finditer(text):
        start, end = m.start(), m.end()
        raw_int = m.group('int').replace(',', '')
        dec = m.group('dec') or ''
        val_str = f"{raw_int}.{dec}" if dec else raw_int
        try:
            value = float(val_str)
        except ValueError:
            continue
        sign = m.group('sign')
        if sign in ('-', '−'):
            value = -value
        unit = m.group('unit') or ''
        decimals = len(dec)
        tokens.append(NumberToken(text[start:end], value, unit, decimals, sign, m.group('cur'), start, end))
        pos = end

    for cur, nxt in zip(tokens, tokens[1:]):
        if not cur.unit and not cur.currency and nxt.unit and RANGE_SEP.match(text[cur.end:nxt.start]):
            cur.unit = nxt.unit
    return tokens


EXCLUDE_CATEGORIES = ('diagram_style', 'citation', 'date', 'ticker_code', 'period_label',
                      'product_spec', 'duration', 'year', 'numbering')

MERMAID_STYLE_LINE = re.compile(r'\s*(?:style|classDef|linkStyle|class)\b')

MASKS = [
    ('diagram_style', re.compile(r'#[0-9A-Fa-f]{3,8}\b')),
    ('citation', re.compile(r'https?://[^\s)\]>]+|`[^`]*`|\[\d+\]|KI-\d{3}')),
    ('numbering', re.compile(r'^\s*(?:>\s*)*#{1,6}\s*(?:[^\w\s]+\s*)?\d+(?:[.\-]\d+)*[.)]?'
                             r'|^\s*(?:>\s*)*(?:[-*]\s+)?\d+[.)](?=\s)'
                             r'|\(\d+\)'
                             r'|Section\s*\d+(?:\.\d+)*(?:\s*(?:및|·|,|/)\s*\d+(?:\.\d+)*)*(?:\s*›\s*\d+(?:-\d+)?번?)?'
                             r'|\d+(?:-\d+)?번째?'
                             r'|\b\d+차\s*(?:지지선|공습|저점|방어선)?\b'
                             r'|\b\d+대\s*(?:기둥|질문|편향|원칙)?\b'
                             r'|\b\d+가지\b'
                             r'|\b\d+(?:개|사|개사)(?:의|를|은|는|이|가|로|에)?\b'
                             r'|\b(?:Tier|tier|Phase|phase)\s*\d+(?:\.\d+)?\b'
                             r'|\b\d+-(?:Pillar|pillar|tier|Tier|티어|호라이즌)\b'
                             r'|\b[345]-티어\b'
                             r'|\b\d+단계\b')),
    ('date', re.compile(r'\d{4}[-.]\d{2}[-.]\d{2}'
                        r'|\d{4}-\d{2}(?!\d)'
                        r'|(?<![\d,.])\d{1,2}[-/]\d{1,2}(?![\d%.,])'
                        r'|\d{1,2}월\s?\d{1,2}(?:\s?~\s?\d{1,2})?일'
                        r'|\d{1,2}월(?:\s?(?:초|중순|상순|하순|말|중))?'
                        r'|\d{1,2}:\d{2}')),
    ('ticker_code', re.compile(r'\^[A-Z]{2,}\d*|S&P\s?500|KOSPI\s?200|NASDAQ\s?100|Nasdaq\s?100|(?<![\d,.₩$])\d{6}(?:\.K[SQ])?(?![\d,.])')),
    ('period_label', re.compile(r'\b(?:FY)?\d{1,2}[QH]\d{2}\b|\bFY\d{1,4}\b|\bQ[1-4]\b|\b[1-4]Q\b|\d분기')),
    ('product_spec', re.compile(r'[±+\-−]?\d+(?:\.\d+)?σ|\b[A-Za-z]+-?\d+[A-Za-z0-9]*(?:-[A-Za-z0-9]+)*'
                                r'|\d+-?(?:Hi|bit)\b|\d+(?:nm|나노|세대)|\d+단(?!계|기|위|순)|\b\d[a-wyz]\b|\b\d+(?:\.\d+)?D\b'
                                r'|\b\d+-(?:베타|알파|감마)\b')),
    ('duration', re.compile(r'\d+(?:\s?~\s?\d+)?\s?(?:거래일간?|영업일|개월간?|일간|일|년간|주간|시간|분(?!기))'
                            r'|(?<![\d,.])\d{1,3}주(?=\s?(?:최고|최저|고점|저점|범위|신고|신저|동안|이동))'
                            r'|(?<![\d,.$₩])\d{1,2}M\b'
                            r'|(?<![\d,.])\d{1,2}년(?![도대])'
                            r'|\b(?:20|50|200)\s*(?:SMA|EMA|선)\b')),
    ('year', re.compile(r'(?<![\d,.$₩])(?:19|20)\d{2}(?!\d|,\d|\.\d|%|조|억|만|배|건|주)(?:년)?')),
]


def mask_non_quantities(line: str, in_mermaid: bool = False, found: Optional[List] = None) -> Tuple[str, Dict[str, int]]:
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


def extract_numbers(line: str, in_mermaid: bool = False, found: Optional[List] = None) -> Tuple[List[NumberToken], Dict[str, int]]:
    masked, counts = mask_non_quantities(line, in_mermaid, found)
    tokens = parse_numbers(masked)
    return tokens, counts


INDEX_ALIASES = {
    '^KS11': ('KOSPI', '코스피'),
    '^KQ11': ('KOSDAQ', '코스닥'),
    '^SOX': ('SOX', '필라델피아 반도체', '필반'),
    '^GSPC': ('S&P 500', 'S&P500', 'SPX'),
    '^IXIC': ('NASDAQ', '나스닥'),
    '^NDX': ('나스닥 100', '나스닥100', 'NDX'),
    '^DJI': ('다우', '다우존스', 'DJI'),
    '^RUT': ('러셀 2000', '러셀2000', 'RUT'),
    '^VIX': ('VIX', '변동성 지수', '공포 지수'),
    'DX-Y.NYB': ('달러 인덱스', 'DXY'),
    'USDKRW=X': ('원/달러', 'USD/KRW', '원달러 환율', '환율'),
}

COMMON_STOCK_ALIASES = {
    '000660.KS': ('SK하이닉스', '하이닉스', 'SK hynix', 'SK Hynix'),
    '005930.KS': ('삼성전자', '삼전', 'Samsung Electronics'),
    'MU': ('마이크론', 'Micron', 'Micron Technology'),
    'TSM': ('TSMC', '티에스엠씨', 'Taiwan Semiconductor'),
}

ALIAS_STOPWORDS = {'지수', '기업', '종목', '티커', '코드'}


def build_aliases(lines: List[str], tickers: List[str]) -> Dict[str, str]:
    aliases = {}
    text = '\n'.join(lines)
    for t in tickers:
        for m in re.finditer(r'([A-Za-z가-힣][A-Za-z가-힣0-9&]*)\s?\(\s?' + re.escape(t) + r'\s?\)', text):
            name = m.group(1)
            if len(name) >= 2 and name not in ALIAS_STOPWORDS and name != t:
                aliases.setdefault(name, t)
        if t in COMMON_STOCK_ALIASES:
            for alias in COMMON_STOCK_ALIASES[t]:
                aliases.setdefault(alias, t)
    for index, names in INDEX_ALIASES.items():
        for name in names:
            aliases.setdefault(name, index)
    return aliases


def ticker_pattern(tickers: List[str], aliases: Optional[Dict[str, str]] = None) -> Tuple[Optional[re.Pattern], Dict[str, str]]:
    names = {t: t for t in tickers}
    names.update(aliases or {})
    if not names:
        return None, {}
    alts = '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True))
    return re.compile(r'(?<![A-Za-z0-9.^가-힣])(' + alts + r')(?![A-Za-z0-9])'), names


def _heading_title(line: str) -> str:
    return line.lstrip('#').strip()


CITATION_NUMBER = re.compile(r'\[(\d+)\]')
SECTION4_REF = re.compile(r'Section\s*4(?:\.([123]))?\s*›\s*(\d+(?:-\d+)?)')
SECTION4_TABLE = re.compile(r'^#{3,4}\s*(?:[^\w\s]+\s*)?(\d+(?:-\d+)?)\.')
APPROXIMATE_AFTER = re.compile(r'\s?(?:원\s?)?(?:부근|내외|안팎|가량|전후)')
SENTENCE_BREAK = re.compile(r'(?<=다\.)\s+|(?<=\.)\s+(?=\S)|<br\s*/?>')


def scopes(line: str) -> List[Tuple[int, int]]:
    if line.lstrip().startswith('|'):
        return [(0, len(line))]
    spans, start = [], 0
    for m in SENTENCE_BREAK.finditer(line):
        spans.append((start, m.start()))
        start = m.end()
    spans.append((start, len(line)))
    return spans


def extract_mentions(report: Report, tickers: List[str] = (), excluded_items: Optional[List] = None) -> Tuple[List[NumberMention], Dict[str, int]]:
    mentions = []
    excluded = dict.fromkeys(EXCLUDE_CATEGORIES, 0)
    aliases = build_aliases(report.lines, list(tickers))
    find_ticker, ticker_of = ticker_pattern(list(tickers), aliases)
    seen: Dict[Tuple[str, str], int] = {}

    for section in report.sections:
        if section.kind in ('section4', 'references', 'check'):
            continue
        in_mermaid, in_code = False, False
        heading = section.title
        heading_ticker = None
        for offset, line in enumerate(section.lines):
            line_no = section.start + offset
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
                refs = []
                for sub_num, tbl_num in SECTION4_REF.findall(line[lo:hi]):
                    if sub_num:
                        refs.append(f"4.{sub_num}-{tbl_num}")
                        refs.append(f"4.{sub_num} › {tbl_num}")
                    refs.append(tbl_num)
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


# --- Placeholder Detection -------------------------------------------------------------------

PLACEHOLDER_PATTERNS = [
    (re.compile(r'\[[A-Za-z0-9_]*TODO[^\]]*\]', re.IGNORECASE), 'unpopulated [AI_TODO]'),
    (re.compile(r'\[(?:XX|OO|00)[^\]]*\]'), 'unpopulated [XX%]'),
    (re.compile(r'\[수치[^\]]*\]'), 'unpopulated [수치]'),
    (re.compile(r'\[출처[^\]]*\]'), 'unpopulated [출처]'),
    (re.compile(r'\[(?:금액|비율|판단|의견|작성|확인|내용)[^\]]*\]'), 'unpopulated placeholder'),
    (re.compile(r'\[🟢/🟡/🔴\]'), 'unpopulated [🟢/🟡/🔴]'),
    (re.compile(r'\[방어 유지[^\]]*\]'), 'unpopulated [방어 유지]'),
    (re.compile(r'\[진단[^\]]*\]'), 'unpopulated [진단]'),
    (re.compile(r'<!--\s*스크립트.*?-->'), 'unpopulated script template comment'),
    (re.compile(r'\[\s*(?:YYYY|MM|DD)[^\]]*\]'), 'unpopulated date placeholder'),
]


def find_placeholders(report: Report) -> List[Dict[str, Any]]:
    """Find any remaining unfilled template placeholders across the whole report."""
    results = []
    for line_no, line in enumerate(report.lines, start=1):
        for pat, desc in PLACEHOLDER_PATTERNS:
            for m in pat.finditer(line):
                results.append({
                    'line': line_no,
                    'desc': desc,
                    'text': m.group(0),
                    'context': line.strip()[:100],
                })
    return results


# --- Candidates & Matching -------------------------------------------------------------------

PATH_KINDS = [
    ('percent', re.compile(r'\.(debt_to_equity|dividend_yield|cash_pct|equity_pct|safe_pct'
                           r'|ret[_\.]\w+|dist_50|dist_200|dist_52w_low|buffer_pct|drawdown_pct|rs[_\.]\w+|spread[_\.]\w+|chg[_\.]\w+_pct'
                           r'|diagnostics\.drawdown_52w)$')),
    ('fraction', re.compile(r'\.(return_\w+|drawdown_52w|\w*margin|roe|roa|\w*growth|payout_ratio|held_percent_\w+'
                            r'|short_percent_\w+|foreign_hold_ratio|percentile|position|upside\w*|opm_ttm|change_30d|surprise'
                            r'|max_income_drop|\w*vs_avg|weight_\w+|eps_range_width|export_ratio|\w*op_impact\w*|\w*shift\w*|mean_\w+)$|\.cycle\.opm\.')),
    ('multiple', re.compile(r'\.(beta|beta_parent|current_ratio|dupont_leverage|ev_to_\w+|\w*_pe|peg_ratio|price_to_\w+|multiple_[ab]|pe|ratio)$'
                            r'|\.pb_band\.(pb\.|high$|low$|median$|current_pb$)')),
    ('money', re.compile(r'\.(market_cap\w*)$|\.audit\.')),
    ('price', re.compile(r'(close|price|eps|_high|_low|bps|sma_20|sma_50|sma_200|bollinger_\w+|book_value|dividend_rate|rate|level|trough_price)(_[ab])?(\.|$)|\.history\.|\.target|\.crisis\.|\.tier2\.')),
    ('other', re.compile(r'.')),
]

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
    'bp': (('fraction', 1e4), ('percent', 100.0), ('other', 1.0)),
    'bps': (('fraction', 1e4), ('percent', 100.0), ('other', 1.0)),
    'pt': (('other', 1.0), ('price', 1.0)),
    '(통화)': (('price', 1.0), ('money', 1.0)),
    '(없음)': (('multiple', 1.0), ('price', 1.0), ('count', 1.0), ('other', 1.0), ('percent', 1.0)),
}


def path_kind(path: str) -> str:
    for kind, pat in PATH_KINDS:
        if pat.search(path):
            return kind
    return 'other'


def unit_key(m: NumberMention) -> str:
    if m.unit:
        return m.unit
    return '(통화)' if m.currency else '(없음)'


LOW_INFO_LIMIT = 100


def is_low_information(m: NumberMention) -> bool:
    """Bare integers or counts below 100 without decimals can match randomly."""
    if m.value == 0:
        return True
    if m.unit in ('건', '') and not m.currency and m.decimals == 0 and abs(m.value) < LOW_INFO_LIMIT:
        return True
    return False


def snapshot_candidates(snapshot: Dict[str, Any]) -> List[Candidate]:
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
                cands.append(Candidate(f"{path}.{day}", float(v), 'final', path_kind(path)))
    return cands


def section4_tables(report: Report) -> Dict[str, List[NumberToken]]:
    tables: Dict[str, List[NumberToken]] = {}
    current = None
    sub = ""
    for section in report.sections:
        if section.kind != 'section4':
            continue
        for line in section.lines[1:]:
            m_sub = re.match(r'^###\s*4\.([12])\b', line)
            if m_sub:
                sub = f"4.{m_sub.group(1)}"
                current = None
                continue
            m = SECTION4_TABLE.match(line)
            if m:
                current = m.group(1)
                continue
            if current:
                toks = parse_numbers(mask_non_quantities(line)[0])
                if toks:
                    tables.setdefault(current, []).extend(toks)
                    if sub:
                        tables.setdefault(f"{sub}-{current}", []).extend(toks)
                        tables.setdefault(f"{sub} › {current}", []).extend(toks)
    return tables


def match_rank(m: NumberMention, cand: Candidate) -> Optional[int]:
    tol = 0.5 * 10 ** (-m.decimals) + 1e-9
    for rank, (kind, scale) in enumerate(UNIT_KINDS.get(unit_key(m), ())):
        if cand.kind != kind and cand.kind != 'other':
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


def context_filter(ticker_context: Optional[str]):
    if not ticker_context:
        return lambda c: True
    prefixes = tuple(t + '.' for t in ticker_context.split(',')) + ('rules.', '^', 'macro.', 'sector.', 'sectors.', 'socratic.')
    return lambda c: c.path.startswith(prefixes)


def in_section4_table(m: NumberMention, tables: Dict[str, List[NumberToken]]) -> Optional[str]:
    for ref in m.section4_refs:
        for t in tables.get(ref, []):
            same_sign = not m.explicit_sign or (t.value < 0) == (m.value < 0)
            same_unit = t.unit == m.unit or (m.unit == '건' and not t.unit)
            if same_unit and t.currency == m.currency and abs(t.value) == abs(m.value) and same_sign:
                return ref
    return None


def classify(mentions: List[NumberMention], candidates: List[Candidate], section4: Dict[str, Any] = None) -> List[NumberMention]:
    for m in mentions:
        own = context_filter(m.ticker_context)
        if m.section4_refs:
            ref = in_section4_table(m, section4 or {})
            if ref:
                m.classification, m.matched_path = 'script', f"section4 › {ref}"
                continue
        if is_low_information(m):
            m.classification = 'cited' if m.scope_citations else 'unsupported'
            continue
        if m.approximate:
            m.classification = 'cited' if m.scope_citations else 'unsupported'
            continue
        ranked = [(c, match_rank(m, c)) for c in candidates]
        ranked = sorted(((c, r) for c, r in ranked if r is not None), key=lambda cr: (not own(cr[0]), cr[1]))
        matches = [c for c, _ in ranked]
        if matches:
            m.matched_path = matches[0].path
            m.snapshot_status = matches[0].status
            m.match_count = len(matches)
        if matches and own(matches[0]):
            m.classification = 'script'
            continue
        m.weak = bool(matches)
        if m.scope_citations:
            m.classification = 'cited'
        else:
            m.classification = 'unsupported'
    return mentions


# --- Section 4 Verification ------------------------------------------------------------------

def _trimmed(lines: List[str]) -> List[str]:
    lines = [l.rstrip() for l in lines]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def section4_region(section: Optional[Section]) -> List[Tuple[int, str]]:
    if not section:
        return []
    lines = []
    for offset, line in enumerate(section.lines[1:], start=1):
        if line.strip() == '---':
            break
        lines.append((section.start + offset, line))
    while lines and not lines[-1][1].strip():
        lines.pop()
    return lines


def check_section4(report: Report, snapshot: Dict[str, Any], candidates: List[Candidate]) -> Section4Check:
    chk = Section4Check()
    sec = next((s for s in report.sections if s.kind == 'section4'), None)
    raw_current = section4_region(sec) if sec else []

    # Strip leading and trailing empty lines from current
    start_idx = 0
    while start_idx < len(raw_current) and not raw_current[start_idx][1].strip():
        start_idx += 1
    end_idx = len(raw_current)
    while end_idx > start_idx and not raw_current[end_idx - 1][1].strip():
        end_idx -= 1
    current = raw_current[start_idx:end_idx]
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

    for line_no, text in lines:
        for t in extract_numbers(text)[0]:
            probe = NumberMention(id='', raw=t.raw, value=t.value, unit=t.unit, decimals=t.decimals,
                                  explicit_sign=t.sign, section='4', line=line_no, context='', currency=t.currency)
            if not any(match_rank(probe, c) is not None for c in candidates):
                chk.snapshot_missing.append({'line': line_no, 'raw': t.raw,
                                             'context': text[max(0, t.start - 40):t.end + 40].strip()})
    return chk


# --- References Verification -----------------------------------------------------------------

REFERENCE_LINE = re.compile(r'^\s*\[(\d+)\]\s*(.*)$')
MARKDOWN_LINK = re.compile(r'\[([^\]]+)\]\((https?://[^)\s]+)\)')
BARE_URL = re.compile(r'https?://[^\s)>\]]+')
ISO_DATE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
HOMEPAGE_PATHS = {'', '/', '/index.html', '/index.htm', '/main', '/home'}


def is_homepage(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    return parts.path.rstrip('/') in HOMEPAGE_PATHS and not parts.query


def parse_reference(number: int, text: str, line_no: int) -> Reference:
    link = MARKDOWN_LINK.search(text)
    if link:
        title, url = link.group(1).strip(), link.group(2)
    else:
        bare = BARE_URL.search(text)
        url = bare.group(0) if bare else None
        head = text[:bare.start()] if bare else text
        title = next((p.strip() for p in re.split(r'\s*[—–]\s*', head) if p.strip() and not ISO_DATE.fullmatch(p.strip())), None)
    date = ISO_DATE.search(text)
    ref = Reference(number=number, title=title or None, date=date.group(1) if date else None, url=url, line=line_no)
    if not ref.title:
        ref.problems.append('missing_title')
    if not ref.date:
        ref.problems.append('missing_date')
    if not ref.url:
        ref.problems.append('missing_url')
    elif is_homepage(ref.url):
        ref.problems.append('homepage_url')
    return ref


def body_citations(report: Report) -> Dict[int, int]:
    used = {}
    for section in report.sections:
        if section.kind in ('head', 'section4', 'references', 'check'):
            continue
        for offset, line in enumerate(section.lines):
            for n in CITATION_NUMBER.findall(MARKDOWN_LINK.sub('', line)):
                used.setdefault(int(n), section.start + offset)
    return used


def check_references(report: Report) -> Tuple[List[Reference], List[Issue]]:
    refs = []
    for section in report.sections:
        if section.kind != 'references':
            continue
        for offset, line in enumerate(section.lines[1:], start=1):
            m = REFERENCE_LINE.match(line)
            if m:
                refs.append(parse_reference(int(m.group(1)), m.group(2), section.start + offset))
    used = body_citations(report)
    numbers = {r.number for r in refs}
    issues = []
    labels = {'missing_title': '제목 없음', 'missing_date': '발행일(YYYY-MM-DD) 없음', 'missing_url': '주소 없음',
              'homepage_url': '홈페이지 주소(기사·문서 주소가 아님)'}
    for r in refs:
        r.cited = r.number in used
        if not r.cited:
            r.problems.append('unused')
            issues.append(Issue(f"unused_reference-{r.number}", 'unused_reference', 'warning', f"참고문헌 › 줄 {r.line}",
                                f"[{r.number}]이 본문에서 인용되지 않았습니다"))
        bad = [labels[p] for p in r.problems if p in labels]
        if bad:
            issues.append(Issue(f"reference_format-{r.number}", 'reference_format', 'error', f"참고문헌 › 줄 {r.line}",
                                f"[{r.number}] {', '.join(bad)}" + (f" ({r.url})" if r.url else '')))
    for n, line_no in sorted(used.items()):
        if n not in numbers:
            issues.append(Issue(f"missing_citation_target-{n}", 'missing_citation_target', 'error', f"줄 {line_no}",
                                f"본문의 [{n}]에 해당하는 참고문헌이 없습니다"))
    return refs, issues


# --- Section 9 Check Results Documentation ---------------------------------------------------

CHECK_SECTION_TITLE = "## 9. 숫자 점검 결과 (스크립트 자동 점검)"
REASON_TODO = "[AI_TODO: 남긴 이유]"
UNDOCUMENTABLE = {'ai_todo_left', 'placeholder_left', 'check_section_missing', 'check_section_stale', 'section4_changed'}
KIND_LABELS = {
    'unsupported_number': '근거 없음', 'section4_changed': 'Section 4 수정됨',
    'section4_not_in_snapshot': 'Section 4 값이 스냅샷에 없음',
    'reference_format': '참고문헌 형식', 'missing_citation_target': '없는 인용 번호',
    'no_snapshot': '짝 스냅샷 없음', 'no_baseline': 'Section 4 기준본 없음',
    'placeholder_left': '채우지 않은 자리', 'ai_todo_left': '채우지 않은 자리',
}


def render_check_section(result: CheckResult) -> str:
    lines = [CHECK_SECTION_TITLE, ""]
    c = result.counts
    total_exc = sum((c.get('excluded') or {}).values())
    lines.append(f"> 스크립트 값 일치 {c.get('script', 0)} · 인용 {c.get('cited', 0)} · 근거 없음 {c.get('unsupported', 0)} · 제외 {total_exc} · "
                 f"Section 4 변경 {len(result.section4.changed_lines)} · 참고문헌 문제 {sum(i.kind == 'reference_format' for i in result.issues)}")
    lines.append("")
    if not result.issues:
        lines.append("모든 숫자가 스냅샷 또는 참고문헌과 일치하며, 채우지 않은 자리가 없습니다.")
        return '\n'.join(lines) + '\n'

    lines.append("| 항목 | 구분 | 위치 | 내용 | 사유 |")
    lines.append("|---|---|---|---|---|")
    for n, iss in enumerate(result.issues, start=1):
        lbl = KIND_LABELS.get(iss.kind, iss.kind)
        lines.append(f"| {n} | {lbl} | {iss.location} | {iss.message} | {REASON_TODO} |")
    return '\n'.join(lines) + '\n'


def read_check_section(report: Report) -> Optional[List[Dict[str, str]]]:
    sec = next((s for s in report.sections if s.kind == 'check'), None)
    if not sec:
        return None
    rows = []
    for line in sec.lines:
        if line.strip().startswith('|') and not line.strip().startswith('|--') and not line.strip().startswith('| 항목'):
            cols = [c.strip() for c in line.split('|')[1:-1]]
            if len(cols) >= 5:
                rows.append({'n': cols[0], 'kind': cols[1], 'loc': cols[2], 'msg': cols[3], 'reason': cols[4]})
    return rows


def apply_check_section(result: CheckResult, recorded_rows: Optional[List[Dict[str, str]]]) -> None:
    if recorded_rows is None:
        return
    for iss in result.issues:
        if iss.kind in UNDOCUMENTABLE:
            continue
        # Find matching row
        for r in recorded_rows:
            if iss.location in r.get('loc', '') and r.get('reason') and r.get('reason') != REASON_TODO:
                iss.documented = True
                break


def exit_code(issues: List[Issue]) -> int:
    return EXIT_ISSUES if any(not i.documented for i in issues) else EXIT_OK


# --- Master Verification Pipeline ------------------------------------------------------------

def verify_strategy_report(report_path: str, snapshot_path: Optional[str] = None) -> CheckResult:
    if not os.path.isfile(report_path):
        res = CheckResult(report=report_path, snapshot=None, checked_at="")
        res.exit_code = EXIT_CANNOT_RUN
        print(f"❌ Error: Report file not found: {report_path}", file=sys.stderr)
        return res

    report = load_report(report_path)
    snap_path = find_snapshot(report, snapshot_path)
    if not snap_path or not os.path.isfile(snap_path):
        res = CheckResult(report=report_path, snapshot=snap_path, checked_at="")
        res.exit_code = EXIT_CANNOT_RUN
        print(f"❌ Error: Companion data snapshot not found: {snap_path}", file=sys.stderr)
        return res

    snapshot = load_snapshot(snap_path)
    tickers_list = (snapshot.get('meta') or {}).get('tickers') or []

    result = CheckResult(
        report=report_path,
        snapshot=snap_path,
        checked_at=datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')
    )

    # 1. Check placeholders across the whole report
    placeholders = find_placeholders(report)
    result.placeholders = placeholders
    for p in placeholders:
        result.issues.append(Issue(
            id=f"placeholder_left-{p['line']}",
            kind='placeholder_left',
            severity='error',
            location=f"줄 {p['line']}",
            message=f"{p['desc']}: '{p['text']}'"
        ))

    # 2. Check Section 4 integrity against baseline
    candidates = snapshot_candidates(snapshot)
    result.section4 = check_section4(report, snapshot, candidates)
    if result.section4.baseline == 'missing':
        result.issues.append(Issue('no_baseline-section4', 'no_baseline', 'error', 'Section 4',
                                   '스냅샷에 Section 4 기준본이 없어 생성 후 수정 여부를 확인하지 못했습니다.'))
    for c in result.section4.changed_lines:
        result.issues.append(Issue(
            id=f"section4_changed-{c['line']}",
            kind='section4_changed',
            severity='error',
            location=f"Section 4 › 줄 {c['line']}",
            message=f'현재 "{c["current"] or "(삭제됨)"}" / 기준본 "{c["original"] or "(없음)"}"'
        ))

    # 3. Extract mentions and trace to candidates
    mentions, excluded = extract_mentions(report, tickers_list)
    classify(mentions, candidates, section4_tables(report))
    result.mentions = mentions
    result.counts = {
        'script': sum(m.classification == 'script' for m in mentions),
        'weak': sum(m.weak for m in mentions),
        'cited': sum(m.classification == 'cited' for m in mentions),
        'unsupported': sum(m.classification == 'unsupported' for m in mentions),
        'excluded': excluded,
    }

    for m in mentions:
        if m.classification == 'unsupported':
            hint = f" (다른 종목/지표 값 {m.matched_path}와 일치함 — 문맥 불일치)" if m.weak else ""
            result.issues.append(Issue(
                id=m.id,
                kind='unsupported_number',
                severity='error',
                location=f"{m.section} › 줄 {m.line}",
                message=f'"{m.raw}" — {m.context}{hint}'
            ))

    # 4. Check References
    result.references, ref_issues = check_references(report)
    result.issues += ref_issues

    # 5. Check Documentation Section
    apply_check_section(result, read_check_section(report))
    result.exit_code = exit_code(result.issues)

    return result


def main():
    parser = argparse.ArgumentParser(description="Check unified 3-tier investment strategy report numbers and placeholders against snapshot")
    parser.add_argument("report_file", type=str, help="Path to markdown report file")
    parser.add_argument("--snapshot", type=str, default="", help="Optional snapshot JSON path override")
    parser.add_argument("--section", action="store_true", help="Print ## 9. 숫자 점검 결과 Markdown section")

    args = parser.parse_args()

    result = verify_strategy_report(args.report_file, args.snapshot or None)

    if args.section:
        print(render_check_section(result))
        sys.exit(result.exit_code)

    print(f"📋 Unified Investment Strategy Report Number Check: {os.path.basename(result.report)}")
    if result.snapshot:
        print(f"   - Snapshot: {os.path.basename(result.snapshot)} ({result.counts.get('script', 0)} script matches)")

    if result.exit_code == EXIT_CANNOT_RUN:
        sys.exit(EXIT_CANNOT_RUN)

    if result.exit_code != EXIT_OK:
        undocumented = [i for i in result.issues if not i.documented]
        print(f"\n❌ Issues identified ({len(undocumented)} undocumented):")
        for iss in undocumented:
            print(f"   [{iss.severity.upper()}] {iss.location}: {iss.message}")
        sys.exit(EXIT_ISSUES)

    if result.issues:
        print(f"\n⚠️ {len(result.issues)} issue(s) identified and documented in Section 9.")

    print("\n✅ All checks passed! Section 4 hash matches, zero unpopulated placeholders, and all numbers traced.")
    sys.exit(EXIT_OK)


if __name__ == "__main__":
    main()
