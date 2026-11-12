"""
Collection stage: the only code that reaches external sources or reads the clock (spec 003).

It stores what each source returned, with the time it was received, as raw input items
(raw_inputs.py). Failures are recorded as status "error" with the exception text instead of
warnings: get_financial_stats.py turns them into the same warning sentences at the same place
in the pipeline, so a snapshot rebuilds the same Section 4 (research R1·R4·R6).

Rules: references/rules/data-snapshot.md §9
"""
import datetime
import os
import platform
import re
import subprocess
import sys

import pandas as pd
import requests
import yfinance as yf

import data_checks
import mcp_client
import raw_inputs as ri
from data_checks import BROWSER_UA

KST = datetime.timezone(datetime.timedelta(hours=9))
YAHOO_FRAMES = ('income_stmt', 'quarterly_income_stmt', 'balance_sheet', 'quarterly_balance_sheet',
                'earnings_estimate', 'eps_trend', 'eps_revisions', 'earnings_history')
NAVER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
DAUM_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://finance.daum.net'}


def now_kst():
    return datetime.datetime.now(KST).replace(microsecond=0)


def stamp():
    return now_kst().isoformat()


def is_kr(sym):
    return sym.endswith(('.KS', '.KQ'))


def digits8(val):
    """First 8 digits of a date-like value (YYYYMMDD) — the rule get_financial_stats.digits8 uses."""
    return ''.join(ch for ch in str(val or '') if ch.isdigit())[:8]


def ok(source, kind, data, note=None):
    return ri.make_item(source, stamp(), 'ok', kind, data=data, note=note)


def failed(source, e):
    return ri.make_item(source, stamp(), 'error', error=str(e))


def skipped(source, note=None):
    return ri.make_item(source, stamp(), 'skipped', note=note)


def frame_item(source, df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return ri.make_item(source, stamp(), 'empty')
    return ok(source, 'frame', ri.encode_frame(df))


# ---------------------------------------------------------------- source requests

def daum_day_rows(code, per_page=100, pages=1):
    rows = []
    for p in range(1, pages + 1):
        r = requests.get(f"https://finance.daum.net/api/quote/A{code}/days",
                         params={'symbolCode': f'A{code}', 'page': p, 'perPage': per_page, 'pagination': 'true'},
                         headers={'User-Agent': BROWSER_UA, 'Referer': 'https://finance.daum.net'}, timeout=8)
        r.raise_for_status()
        rows += r.json().get('data') or []
    return rows


def daum_index_rows(market, per_page=100):
    r = requests.get("https://finance.daum.net/api/market_index/days",
                     params={'page': 1, 'perPage': per_page, 'market': market, 'pagination': 'true'},
                     headers={'User-Agent': BROWSER_UA, 'Referer': 'https://finance.daum.net'}, timeout=8)
    r.raise_for_status()
    return r.json().get('data') or []


def fetch_daum_days(code, per_page=100, pages=1):
    """Daily KRX OHLCV from Daum Finance (finance.daum.net) — the KRX-close reference for KR stocks."""
    return data_checks.daum_frame(daum_day_rows(code, per_page, pages))


def fetch_daum_index_days(market, per_page=100):
    """Daily KRX index closes (KOSPI/KOSDAQ) from Daum Finance; open/high/low may be absent."""
    return data_checks.daum_frame(daum_index_rows(market, per_page))


def fetch_naver_fchart(code, count=260):
    """Daily OHLCV from Naver's chart feed (same basis as the Naver mobile price API)."""
    xml = requests.get("https://fchart.stock.naver.com/sise.nhn",
                       params={'symbol': code, 'timeframe': 'day', 'count': count, 'requestType': 0},
                       headers={'User-Agent': BROWSER_UA}, timeout=8).text
    recs = {}
    for item in re.findall(r'data="([^"]+)"', xml):
        d, o, h, l, c, v = item.split('|')
        recs[pd.Timestamp(d)] = {'Open': float(o), 'High': float(h), 'Low': float(l), 'Close': float(c), 'Volume': float(v)}
    return pd.DataFrame.from_dict(recs, orient='index').sort_index()


# ---------------------------------------------------------------- per ticker

def collect_ticker(sym):
    """Yahoo items for one ticker, plus SEC EDGAR items for US tickers."""
    items = {}
    t = yf.Ticker(sym)
    try:
        items['info'] = ok('yahoo', 'json', dict(t.info))
    except Exception as inner_e:
        # yfinance can fail in _fetch_complementary() after the base quote arrived; the pipeline warns with this note
        q = getattr(t, '_quote', None)
        info = getattr(q, '_info', None) if q is not None else None
        items['info'] = ok('yahoo', 'json', dict(info), note=str(inner_e)) if info else failed('yahoo', inner_e)
    try:
        items['history'] = frame_item('yahoo', t.history(period='5y', auto_adjust=False))
    except Exception as e:
        items['history'] = failed('yahoo', e)
    for attr in YAHOO_FRAMES:
        try:
            items[attr] = frame_item('yahoo', getattr(t, attr))
        except Exception as e:
            items[attr] = failed('yahoo', e)

    # For US tickers, collect official SEC EDGAR financials and shares outstanding
    if not is_kr(sym):
        try:
            edgar_f = mcp_client.get_edgar_financials(sym, period='annual', limit=10)
            if edgar_f:
                items['edgar_financials'] = ok('edgar', 'json', edgar_f)
            else:
                items['edgar_financials'] = failed('edgar', 'EDGAR 재무 데이터 없음')
        except Exception as e:
            items['edgar_financials'] = failed('edgar', e)

        try:
            edgar_s = mcp_client.get_edgar_shares_outstanding(sym)
            if edgar_s:
                items['edgar_shares'] = ok('edgar', 'json', edgar_s)
            else:
                items['edgar_shares'] = failed('edgar', 'EDGAR 주식수 데이터 없음')
        except Exception as e:
            items['edgar_shares'] = failed('edgar', e)

    return items


def wisereport_table(code):
    from bs4 import BeautifulSoup
    url = f"https://navercomp.wisereport.co.kr/v2/company/cF1002.aspx?cmp_cd={code}&finGubun=MAIN"
    res = requests.get(url, headers={'User-Agent': NAVER_UA}, timeout=5)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    return {'headers': [th.get_text(strip=True) for th in soup.select('table thead th')],
            'rows': [[td.get_text(strip=True) for td in tr.find_all('td')] for tr in soup.select('table tbody tr')]}


def collect_kr(sym):
    """Collect official KRX, DART, and consensus items for a Korean ticker."""
    code = sym.split('.')[0]
    market_type = 'kospi' if sym.endswith('.KS') else 'kosdaq'
    items = {}

    # 1. Official KRX Stock Info & Quote
    try:
        krx_data = mcp_client.get_krx_ticker_info(code, market_type)
        if krx_data:
            items['krx_stock'] = ok('krx', 'json', krx_data)
        else:
            items['krx_stock'] = failed('krx', 'KRX 종목 데이터 없음')
    except Exception as e:
        items['krx_stock'] = failed('krx', e)

    # 2. Official DART 10-Year Financials
    try:
        corp_code = mcp_client.get_dart_corp_code(code)
        if corp_code:
            dart_data = mcp_client.get_dart_financials(corp_code)
            if dart_data:
                items['dart_financials'] = ok('dart', 'json', dart_data)
            else:
                items['dart_financials'] = skipped('dart', 'DART 재무제표 없음')
        else:
            items['dart_financials'] = skipped('dart', f'DART 고유번호 미확인 ({code})')
    except Exception as e:
        items['dart_financials'] = failed('dart', e)

    # 3. Consensus & Target Price (Naver & WiseReport)
    try:
        res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/integration", headers={'User-Agent': NAVER_UA}, timeout=5)
        res.raise_for_status()
        items['naver_integration'] = ok('naver', 'json', res.json())
    except Exception as e:
        items['naver_integration'] = failed('naver', e)

    try:
        items['wisereport_eps'] = ok('wisereport', 'table', wisereport_table(code))
    except Exception as e:
        items['wisereport_eps'] = failed('wisereport', e)

    # 4. Fallback Daily Closes (Daum)
    try:
        items['daum_days'] = ok('daum', 'json', daum_day_rows(code))
    except Exception as e:
        items['daum_days'] = failed('daum', e)

    return items


def collect_flows(sym):
    """Collect investor flows from Toss MCP (primary) and Naver trend."""
    code = sym.split('.')[0]
    market_name = 'KOSPI' if sym.endswith('.KS') else 'KOSDAQ'
    items = {}

    # 1. Toss Individual Stock Investor Flows (7-Institutional Sub-entities, 06:10 confirmed)
    try:
        toss_stock = mcp_client.get_toss_stock_flows(code)
        if toss_stock:
            items['toss_stock_flows'] = ok('toss', 'json', toss_stock)
        else:
            items['toss_stock_flows'] = failed('toss', '토스 종목 수급 응답 없음')
    except Exception as e:
        items['toss_stock_flows'] = failed('toss', e)

    # 2. Toss Market Investor Flows (20:06 confirmed)
    try:
        toss_market = mcp_client.get_toss_market_flows(market_name)
        if toss_market:
            items['toss_market_flows'] = ok('toss', 'json', toss_market)
        else:
            items['toss_market_flows'] = failed('toss', '토스 시장 수급 응답 없음')
    except Exception as e:
        items['toss_market_flows'] = failed('toss', e)

    # 3. Naver trend (historical trend series)
    try:
        res = requests.get(f'https://m.stock.naver.com/api/stock/{code}/trend', headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        items['naver_trend'] = ok('naver', 'json', res)
    except Exception as e:
        items['naver_trend'] = failed('naver', e)

    return items


def collect_index(bench):
    items = {}
    try:
        items['history'] = frame_item('yahoo', yf.Ticker(bench).history(period='1y', auto_adjust=False))
    except Exception as e:
        items['history'] = failed('yahoo', e)
    market = data_checks.DAUM_INDEX.get(bench)
    if market and items['history']['status'] == 'ok':
        try:
            items['daum_index_days'] = ok('daum', 'json', daum_index_rows(market))
        except Exception as e:
            items['daum_index_days'] = failed('daum', e)
    elif market:
        items['daum_index_days'] = skipped('daum', 'Yahoo 지수 이력 없음')
    return items


# ---------------------------------------------------------------- whole run

def collect_meta(args_dict, collected_at=None):
    import numpy as np
    collected_at = collected_at or now_kst()
    versions = {
        'python': platform.python_version(),
        'yfinance': getattr(yf, '__version__', 'unknown'),
        'pandas': getattr(pd, '__version__', 'unknown'),
        'numpy': getattr(np, '__version__', 'unknown'),
    }
    # An unknown commit is recorded with its reason, never silently dropped (spec 003 R15).
    repo_commit, repo_commit_error = None, None
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        res = subprocess.run(["git", "-C", script_dir, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            repo_commit = res.stdout.strip()
        else:
            repo_commit_error = (res.stderr or '').strip() or f"git exit {res.returncode}"
    except Exception as e:
        repo_commit_error = f"{type(e).__name__}: {e}"
    return {
        "format_version": ri.FORMAT_VERSION,
        "generated_at": collected_at.strftime("%Y-%m-%d %H:%M KST"),
        "collected_at": collected_at.isoformat(),
        "args": args_dict or {},
        "versions": versions,
        "repo_commit": repo_commit,
        "repo_commit_error": repo_commit_error,
    }


def collect_all(tickers, benchmarks=None, args_dict=None):
    """Fetch every raw input the Section 4 pipeline reads. Returns (meta, inputs)."""
    import get_financial_stats as gfs  # the index choice must match the pipeline's own functions
    inputs = {}

    # 1. Macro Rates & Spreads (ECOS & FRED)
    print("Fetching macro rates and credit spreads (ECOS & FRED)...", file=sys.stderr)
    macro_items = {}
    try:
        ecos_r = mcp_client.get_ecos_market_rates()
        if ecos_r:
            macro_items['ecos_market_rates'] = ok('ecos', 'json', ecos_r)
        else:
            macro_items['ecos_market_rates'] = failed('ecos', 'ECOS 시장금리 데이터 없음')
    except Exception as e:
        macro_items['ecos_market_rates'] = failed('ecos', e)

    try:
        fred_r = mcp_client.get_fred_bundle('rates')
        if fred_r:
            macro_items['fred_rates'] = ok('fred', 'json', fred_r)
        else:
            macro_items['fred_rates'] = failed('fred', 'FRED rates 데이터 없음')
    except Exception as e:
        macro_items['fred_rates'] = failed('fred', e)

    try:
        fred_c = mcp_client.get_fred_bundle('credit')
        if fred_c:
            macro_items['fred_credit'] = ok('fred', 'json', fred_c)
        else:
            macro_items['fred_credit'] = failed('fred', 'FRED credit 데이터 없음')
    except Exception as e:
        macro_items['fred_credit'] = failed('fred', e)

    inputs['macro'] = macro_items

    # 2. Per-Ticker Data
    for sym in tickers:
        print(f"Fetching data for {sym}...", file=sys.stderr)
        inputs[sym] = collect_ticker(sym)
        if is_kr(sym):
            inputs[sym].update(collect_kr(sym))
            inputs[sym].update(collect_flows(sym))

    # 3. Benchmark Indices
    usable = {s: it['info']['data'] for s, it in inputs.items()
              if isinstance(it, dict) and 'info' in it and it['info']['status'] == 'ok' and 'symbol' in (it['info']['data'] or {})}
    symbols = list(usable)
    marks = [b for b in (benchmarks or gfs.default_benchmarks(symbols, usable)) if b not in symbols]
    for b in sorted(set(marks) | {gfs.market_index_for(s) for s in symbols if gfs.market_index_for(s)}):
        inputs[b] = collect_index(b)

    return collect_meta(args_dict), inputs
