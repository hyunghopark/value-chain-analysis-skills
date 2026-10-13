"""Cross-source data checks for the financial-analyst scripts.

Rules: skills/financial-analyst/references/rules/data-quality.md
Incidents (KI-xxx): wiki/known-issues/ in the value-chain-analysis-skills repository.

Pure functions (no network) come first so tests can feed them fixtures; fetchers follow.
"""
import datetime
import math

import pandas as pd

KNOWN_ISSUES = {
    'KI-001': '네이버 종가 필드가 거래소 종가와 다름',
    'KI-002': 'Yahoo 한국 종목 최근 거래일 누락·빈값',
    'KI-003': 'Yahoo 재무제표 반영 지연',
    'KI-004': 'WiseReport 표 구조 변경 위험',
    'KI-005': 'Yahoo 거래량 이상치',
    'KI-006': 'Yahoo 한국 종목 산발적 종가 오류',
    'KI-007': 'Yahoo 재무상태표 주식수 이상치',
    'KI-008': 'ADR 통화 불일치',
}

# The first six header cells of WiseReport cF1002; EPS is read from cell index 5 of each row.
WISEREPORT_HEADER = ('재무년월', '매출액(억원, %)', '영업이익(억원, %)', '당기순이익(억원, %)', 'EPS(원)', 'PER(배)')

# Yahoo index ticker -> Daum market_index market code (KRX index closes).
DAUM_INDEX = {'^KS11': 'KOSPI', '^KQ11': 'KOSDAQ'}

BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'


def ki(code, msg):
    """Prefix a warning with its known-issue id so the report links to wiki/known-issues/."""
    return f"[{code}] {msg}"


def _num(val):
    try:
        f = float(str(val).replace(',', '').replace('+', ''))
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def naive_dates(index):
    """DatetimeIndex -> tz-naive midnight dates (Yahoo histories are tz-aware)."""
    idx = pd.DatetimeIndex(index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()


def daum_frame(rows):
    """Daum /api/quote/{code}/days rows -> OHLCV frame indexed by tz-naive date (KRX session basis)."""
    recs = {}
    for x in rows or []:
        d = pd.Timestamp(str(x.get('date', ''))[:10])
        recs[d] = {
            'Open': _num(x.get('openingPrice')), 'High': _num(x.get('highPrice')),
            'Low': _num(x.get('lowPrice')), 'Close': _num(x.get('tradePrice')),
            'Volume': _num(x.get('accTradeVolume')),
        }
    if not recs:
        return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'], dtype=float)
    return pd.DataFrame.from_dict(recs, orient='index').sort_index().astype(float)


def close_mismatches(close, ref_close, tol=0.5):
    """[(date, value, ref)] where both series have a value and they differ by more than tol."""
    s = pd.Series(close.values, index=naive_dates(close.index)).dropna()
    s = s[~s.index.duplicated(keep='last')]
    out = []
    for d, r in ref_close.dropna().items():
        if d in s.index and abs(float(s[d]) - float(r)) > tol:
            out.append((d, float(s[d]), float(r)))
    return out


def missing_closes(close, ref_close):
    """Reference dates that are absent from close or whose close is NaN."""
    s = pd.Series(close.values, index=naive_dates(close.index))
    s = s[~s.index.duplicated(keep='last')]
    return [d for d in ref_close.dropna().index if d not in s.index or pd.isna(s[d])]


def reconcile_history(hist, ref, window=100):
    """Fill missing/empty days and replace mismatched closes in a Yahoo history from a KRX reference.

    Only the last `window` reference rows are used. Returns (fixed_hist, filled_dates, replaced) where
    replaced is [(date, yahoo_close, ref_close)]. Volume of filled rows comes from the reference
    (KRX-only volume, which can differ from Yahoo's basis); replaced rows keep Yahoo's volume.
    """
    ref = ref.dropna(subset=['Close']).iloc[-window:]
    if hist is None or hist.empty or ref.empty:
        return hist, [], []
    tz = hist.index.tz
    fixed = hist.copy()
    pos = {d: i for i, d in enumerate(naive_dates(fixed.index))}
    first = min(pos)
    filled, replaced = [], []
    new_rows = {}
    for d, row in ref.iterrows():
        if d in pos:
            label = fixed.index[pos[d]]
            y = fixed.at[label, 'Close']
            if pd.isna(y):
                for col in ('Open', 'High', 'Low', 'Close', 'Volume'):
                    if col in fixed.columns:
                        fixed.at[label, col] = row[col]
                if 'Adj Close' in fixed.columns:
                    fixed.at[label, 'Adj Close'] = row['Close']
                filled.append(d)
            elif abs(float(y) - float(row['Close'])) > 0.5:
                replaced.append((d, float(y), float(row['Close'])))
                fixed.at[label, 'Close'] = row['Close']
                if 'Adj Close' in fixed.columns:
                    fixed.at[label, 'Adj Close'] = row['Close']
        elif d > first:
            label = d.tz_localize(tz) if tz is not None else d
            rec = {c: float('nan') for c in fixed.columns}
            rec.update({c: row[c] for c in ('Open', 'High', 'Low', 'Close', 'Volume') if c in fixed.columns})
            if 'Adj Close' in fixed.columns:
                rec['Adj Close'] = row['Close']
            for c in ('Dividends', 'Stock Splits'):
                if c in fixed.columns:
                    rec[c] = 0.0
            new_rows[label] = rec
            filled.append(d)
    if new_rows:
        fixed = pd.concat([fixed, pd.DataFrame.from_dict(new_rows, orient='index')[fixed.columns]]).sort_index()
    return fixed, sorted(filled), replaced


def volume_outliers(volume, ratio=0.01, window=20):
    """[(date, volume, trailing median)] where volume is below ratio x the trailing median."""
    v = pd.Series(volume.values, index=naive_dates(volume.index)).astype(float)
    med = v.rolling(window, min_periods=10).median().shift(1)
    mask = (v < ratio * med) & med.notna()
    return [(d, float(v[d]), float(med[d])) for d in v.index[mask]]


def statement_lag(latest_column, reported_epoch, grace_days=7):
    """Reported period end (date) when Yahoo's statement tables stop before it, else None.

    latest_column: newest column date of an income statement table (or None).
    reported_epoch: Yahoo info epoch such as lastFiscalYearEnd / mostRecentQuarter.
    """
    rep = _num(reported_epoch)
    if not rep or rep <= 0:
        return None
    reported = datetime.datetime.fromtimestamp(rep, tz=datetime.timezone.utc).date()
    if latest_column is None:
        return reported
    latest = pd.Timestamp(latest_column).date()
    return reported if reported > latest + datetime.timedelta(days=grace_days) else None


def validate_wisereport_header(headers):
    """Raise ValueError when the cF1002 header no longer matches the layout the EPS parser assumes."""
    got = tuple(headers[:len(WISEREPORT_HEADER)])
    if got != WISEREPORT_HEADER:
        raise ValueError(ki('KI-004', f"WiseReport 표 머리글이 예상과 다릅니다 — 예상 {list(WISEREPORT_HEADER)}, 실제 {list(got)}"))


def check_wisereport_row(cells):
    """Raise ValueError when net income (cell 4) and EPS (cell 5) disagree in sign — a sign of shifted columns."""
    ni, eps = _num(cells[4]), _num(cells[5])
    if ni and eps and (ni > 0) != (eps > 0):
        raise ValueError(ki('KI-004', f"WiseReport {cells[0]} 행의 순이익({cells[4]})과 EPS({cells[5]}) 부호가 달라 열이 밀렸을 수 있습니다"))


def ref_close_on(ref, date8):
    """Reference close for a YYYYMMDD string, or None."""
    if ref is None or ref.empty or len(date8) != 8:
        return None
    d = pd.Timestamp(f"{date8[:4]}-{date8[4:6]}-{date8[6:]}")
    return float(ref.at[d, 'Close']) if d in ref.index and pd.notna(ref.at[d, 'Close']) else None


# ---------------------------------------------------------------- fetchers (network)

def fetch_daum_days(code, per_page=100, pages=1):
    """Daily KRX OHLCV from Daum Finance (finance.daum.net) — the KRX-close reference for KR stocks."""
    import requests
    headers = {'User-Agent': BROWSER_UA, 'Referer': 'https://finance.daum.net'}
    rows = []
    for p in range(1, pages + 1):
        r = requests.get(f"https://finance.daum.net/api/quote/A{code}/days",
                         params={'symbolCode': f'A{code}', 'page': p, 'perPage': per_page, 'pagination': 'true'},
                         headers=headers, timeout=8)
        r.raise_for_status()
        rows += r.json().get('data') or []
    return daum_frame(rows)


def fetch_daum_index_days(market, per_page=100):
    """Daily KRX index closes (KOSPI/KOSDAQ) from Daum Finance; open/high/low may be absent."""
    import requests
    r = requests.get("https://finance.daum.net/api/market_index/days",
                     params={'page': 1, 'perPage': per_page, 'market': market, 'pagination': 'true'},
                     headers={'User-Agent': BROWSER_UA, 'Referer': 'https://finance.daum.net'}, timeout=8)
    r.raise_for_status()
    return daum_frame(r.json().get('data') or [])


def fetch_naver_fchart(code, count=260):
    """Daily OHLCV from Naver's chart feed (same basis as the Naver mobile price API)."""
    import re
    import requests
    xml = requests.get("https://fchart.stock.naver.com/sise.nhn",
                       params={'symbol': code, 'timeframe': 'day', 'count': count, 'requestType': 0},
                       headers={'User-Agent': BROWSER_UA}, timeout=8).text
    recs = {}
    for item in re.findall(r'data="([^"]+)"', xml):
        d, o, h, l, c, v = item.split('|')
        recs[pd.Timestamp(d)] = {'Open': float(o), 'High': float(h), 'Low': float(l), 'Close': float(c), 'Volume': float(v)}
    return pd.DataFrame.from_dict(recs, orient='index').sort_index()


def fetch_nasdaq_history(symbol, start, end, limit=400):
    """Daily close/volume from Nasdaq.com for US listings."""
    import requests
    r = requests.get(f"https://api.nasdaq.com/api/quote/{symbol}/historical",
                     params={'assetclass': 'stocks', 'fromdate': start, 'todate': end, 'limit': limit},
                     headers={'User-Agent': BROWSER_UA, 'Accept': 'application/json, text/plain, */*'}, timeout=20)
    r.raise_for_status()
    rows = ((r.json().get('data') or {}).get('tradesTable') or {}).get('rows') or []
    recs = {pd.Timestamp(datetime.datetime.strptime(x['date'], '%m/%d/%Y')):
            {'Close': _num(x['close'].replace('$', '')), 'Volume': _num(x['volume'])} for x in rows}
    return pd.DataFrame.from_dict(recs, orient='index').sort_index()
