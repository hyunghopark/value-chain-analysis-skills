#!/usr/bin/env python3
"""Quantitative data collector for the financial-analyst / investment-strategy skills.

Prints markdown tables to stdout. Every data-quality warning goes to stderr and is also
collected into the final "데이터 품질 경고" section, so the agent writing the report sees
it instead of losing it in stderr.
"""
import argparse
import datetime
import math
import statistics
import sys

import pandas as pd
import yfinance as yf

import data_checks
from data_checks import ki

KST =datetime.timezone(datetime.timedelta(hours=9))
DEFAULT_WEIGHTS = (0.2, 0.5, 0.3)  # Bull, Base, Bear
GENERAL_PILLARS = ('fpe', 'peg', 'rg', 'ev', 'roe', 'de', 'rev')
CYCLICAL_PILLARS = ('band', 'cycle', 'rev', 'de')
MIN_VALID_PILLARS = 4
BENCHMARK_NAMES = {
    '^KS11': '코스피', '^KQ11': '코스닥', '^GSPC': 'S&P 500', '^IXIC': '나스닥 종합',
    '^SOX': '필라델피아 반도체', '^N225': '니케이 225', '^TWII': '대만 가권',
}
MARKET_STATE_KO = {
    'PREPRE': '개장 전', 'PRE': '프리마켓', 'REGULAR': '정규장 진행 중',
    'POST': '애프터마켓', 'POSTPOST': '장 마감', 'CLOSED': '장 마감',
}

WARNINGS = []
HISTORY = {}


def warn(msg):
    print(f"[Warn] {msg}", file=sys.stderr)
    WARNINGS.append(msg)


def num(val):
    """Return val as a finite float, or None."""
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def format_number(val, is_currency=False, currency="USD"):
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        if is_currency:
            if currency == "KRW":
                return f"₩{val:,.0f}"
            if currency in ("USD", None, ""):
                return f"${val:,.2f}"
            return f"{val:,.2f} {currency}"
        return f"{val:,.2f}"
    return str(val)


def format_percent(val):
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        return f"{val * 100:,.2f}%"
    return str(val)


def format_large_number(val, currency="USD"):
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        size = abs(val)
        if size >= 1e12:
            suffix, divisor = "T", 1e12
        elif size >= 1e9:
            suffix, divisor = "B", 1e9
        elif size >= 1e6:
            suffix, divisor = "M", 1e6
        else:
            suffix, divisor = "", 1

        formatted = f"{val / divisor:,.2f}{suffix}"
        if currency == "KRW":
            return f"₩{formatted}"
        if currency in ("USD", None, ""):
            return f"${formatted}"
        return f"{formatted} {currency}"
    return str(val)


def fmt_signed_pct(val, digits=1):
    return f"{val * 100:+.{digits}f}%" if isinstance(val, (int, float)) else "N/A"


def fmt_multiple(val):
    return f"{val:.2f}배" if isinstance(val, (int, float)) else "N/A"


def fmt_kst_date(epoch):
    v = num(epoch)
    if not v or v <= 0:
        return "N/A"
    return datetime.datetime.fromtimestamp(v, tz=KST).strftime('%Y-%m-%d')


def digits8(val):
    """First 8 digits of a date-like value (YYYYMMDD), or ''."""
    return ''.join(ch for ch in str(val or '') if ch.isdigit())[:8]


def parse_korean_number(text):
    if text is None:
        return None
    import re
    text = str(text).replace(',', '').strip()
    if not text or text in ('-', 'N/A'):
        return None
    if any(u in text for u in ('조', '억', '만')):
        total = 0.0
        matched = False
        for value, unit in re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*(조|억|만)', text):
            matched = True
            mult = {'조': 1e12, '억': 1e8, '만': 1e4}[unit]
            total += float(value) * mult
        return total if matched else None
    m = re.search(r'[-+]?[0-9]+(?:\.[0-9]+)?', text)
    return float(m.group(0)) if m else None


def sanitize_metrics(info, ticker_symbol=""):
    # 0. Fallback pegRatio -> trailingPegRatio & recommendationKey -> recommendationMean
    if info.get('pegRatio') is None and info.get('trailingPegRatio') is not None:
        info['pegRatio'] = info['trailingPegRatio']

    rec_key = str(info.get('recommendationKey') or '').lower()
    if not rec_key or rec_key in ('none', 'n/a'):
        rec_mean = info.get('recommendationMean')
        if isinstance(rec_mean, (int, float)) and rec_mean > 0:
            # Yahoo scale: 1.0 = Strong Buy, 2.0 = Buy, 3.0 = Hold, 4.0+ = Sell
            info['recommendationKey'] = (
                'strong_buy' if rec_mean <= 1.5 else
                ('buy' if rec_mean <= 2.5 else
                 ('hold' if rec_mean <= 3.5 else 'sell'))
            )

    # 1. Normalize dividendYield to percentage value (e.g., 0.72 means 0.72%)
    if not info.get('_div_is_pct'):
        raw_dy = info.get('dividendYield')
        div_rate = info.get('dividendRate')
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        t_dy = info.get('trailingAnnualDividendYield')
        ref_pct = None
        if div_rate and price and price > 0:
            ref_pct = (div_rate / price) * 100.0
        elif t_dy is not None:
            ref_pct = t_dy * 100.0 if t_dy < 0.25 else t_dy
        if isinstance(raw_dy, (int, float)):
            if ref_pct is not None and ref_pct > 0:
                if abs(raw_dy * 100.0 - ref_pct) < abs(raw_dy - ref_pct):
                    info['dividendYield'] = raw_dy * 100.0
                else:
                    info['dividendYield'] = raw_dy
        info['_div_is_pct'] = True

    # 2. ADR / Currency mismatch (currency != financialCurrency) distortion correction
    curr = info.get('currency')
    fin_curr = info.get('financialCurrency')
    if curr and fin_curr and curr != fin_curr:
        tag = f"[KI-008] {ticker_symbol}: 통화 불일치({curr}/{fin_curr}) 보정"
        pe = info.get('trailingPE')
        roe = info.get('returnOnEquity')
        pb = info.get('priceToBook')
        if pe and roe and pe > 0 and roe > 0:
            implied_pb = pe * roe
            if pb is None or pb <= 0 or pb > implied_pb * 2.5 or pb < implied_pb / 2.5:
                warn(f"{tag} — P/B {pb} → {implied_pb:.2f} (P/E × ROE로 역산)")
                info['priceToBook'] = implied_pb

        ps = info.get('priceToSalesTrailing12Months')
        ev_rev = info.get('enterpriseToRevenue')
        ev_ebitda = info.get('enterpriseToEbitda')
        ebitda_m = info.get('ebitdaMargins')
        npm = info.get('profitMargins')

        if pe and npm and pe > 0 and npm > 0:
            implied_ps = pe * npm
            if ps is None or ps <= 0 or ps > implied_ps * 2.5 or ps < implied_ps / 2.5:
                warn(f"{tag} — P/S {ps} → {implied_ps:.2f} (P/E × 순이익률로 역산)")
                ps = implied_ps
                info['priceToSalesTrailing12Months'] = ps

        if ps and ps > 0:
            if ev_rev is None or ev_rev <= 0 or ev_rev > ps * 2.5 or ev_rev < ps / 2.5:
                warn(f"{tag} — EV/Revenue {ev_rev} → {ps:.2f} (P/S로 대체)")
                ev_rev = ps
                info['enterpriseToRevenue'] = ev_rev
            if ebitda_m and ebitda_m > 0:
                implied_ev_ebitda = ev_rev / ebitda_m
                if ev_ebitda is None or ev_ebitda <= 0 or ev_ebitda > implied_ev_ebitda * 2.0 or ev_ebitda < implied_ev_ebitda / 2.0:
                    warn(f"{tag} — EV/EBITDA {ev_ebitda} → {implied_ev_ebitda:.2f} (EV/Revenue ÷ EBITDA 마진으로 역산)")
                    info['enterpriseToEbitda'] = implied_ev_ebitda

        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price and price > 0:
            if pe and pe > 0:
                implied_teps = price / pe
                t_eps = info.get('trailingEps')
                if t_eps is None or t_eps <= 0 or t_eps > implied_teps * 1.5 or t_eps < implied_teps / 1.5:
                    warn(f"{tag} — Trailing EPS {t_eps} → {implied_teps:.2f}")
                    info['trailingEps'] = implied_teps
            fpe = info.get('forwardPE')
            if fpe and fpe > 0:
                implied_feps = price / fpe
                f_eps = info.get('forwardEps')
                if f_eps is None or f_eps <= 0 or f_eps > implied_feps * 1.5 or f_eps < implied_feps / 1.5:
                    warn(f"{tag} — Forward EPS {f_eps} → {implied_feps:.2f}")
                    info['forwardEps'] = implied_feps
            pb_now = info.get('priceToBook')
            if pb_now and pb_now > 0:
                implied_bps = price / pb_now
                bv = info.get('bookValue')
                if bv is None or bv <= 0 or bv > implied_bps * 1.5 or bv < implied_bps / 1.5:
                    warn(f"{tag} — BPS {bv} → {implied_bps:.2f}")
                    info['bookValue'] = implied_bps

    # 3. Fill missing EPS / BPS if price and P/E or P/B are available
    price = info.get('currentPrice') or info.get('regularMarketPrice')
    if price and price > 0:
        if info.get('trailingEps') is None and info.get('trailingPE') and info['trailingPE'] > 0:
            info['trailingEps'] = price / info['trailingPE']
        if info.get('forwardEps') is None and info.get('forwardPE') and info['forwardPE'] > 0:
            info['forwardEps'] = price / info['forwardPE']
        if info.get('bookValue') is None and info.get('priceToBook') and info['priceToBook'] > 0:
            info['bookValue'] = price / info['priceToBook']

    # 4. Derived TTM-based arithmetic & Forward BPS / Forward P/B (12M, simple estimate)
    t_eps = info.get('trailingEps')
    f_eps = info.get('forwardEps')
    t_pe = info.get('trailingPE')
    if isinstance(t_eps, (int, float)) and t_eps > 0 and isinstance(f_eps, (int, float)) and f_eps > 0:
        info['forwardEpsGrowth'] = (f_eps - t_eps) / t_eps
    if isinstance(f_eps, (int, float)) and f_eps > 0 and isinstance(t_pe, (int, float)) and t_pe > 0:
        info['impliedRolloverPrice'] = f_eps * t_pe

    bv = info.get('bookValue')
    if isinstance(bv, (int, float)) and bv > 0 and isinstance(f_eps, (int, float)):
        dps = info.get('dividendRate')
        dy = info.get('dividendYield')
        if price and price > 0 and isinstance(dy, (int, float)) and dy >= 0:
            implied_dps = price * (dy / 100.0)
            if dps is None or (curr and fin_curr and curr != fin_curr and (dps > implied_dps * 1.5 or dps < implied_dps / 1.5)):
                dps = implied_dps
        dps_val = float(dps) if isinstance(dps, (int, float)) and dps >= 0 else 0.0
        fwd_bv = bv + (f_eps - dps_val)
        if fwd_bv > 0:
            info['forwardBookValue'] = fwd_bv
            if price and price > 0:
                info['forwardPriceToBook'] = price / fwd_bv

    # 5. DuPont Financial Leverage (총자산/자기자본 = ROE / ROA) & Dividend Payout Ratio (배당성향)
    roe = info.get('returnOnEquity')
    roa = info.get('returnOnAssets')
    if isinstance(roe, (int, float)) and isinstance(roa, (int, float)) and roa > 0:
        info['dupontLeverage'] = roe / roa

    payout = info.get('payoutRatio')
    dps = info.get('dividendRate')
    if (payout is None or not (0.0 <= payout <= 5.0)) and isinstance(dps, (int, float)) and dps > 0 and isinstance(t_eps, (int, float)) and t_eps > 0:
        info['payoutRatio'] = dps / t_eps


def compute_ntm_eps(eps_fy0, eps_fy1, info=None, today=None):
    """Compute 12M Forward (NTM) EPS using remaining days (d/365) weighting between FY0 and FY1."""
    if eps_fy0 is None or eps_fy1 is None:
        return None
    import calendar
    today = today or datetime.date.today()
    fy0_end = datetime.date(today.year, 12, 31)
    if info:
        ts = info.get('nextFiscalYearEnd') or info.get('lastFiscalYearEnd')
        if isinstance(ts, (int, float)) and ts > 0:
            try:
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).date()
                year = today.year
                day = min(dt.day, calendar.monthrange(year, dt.month)[1])
                candidate = datetime.date(year, dt.month, day)
                if candidate < today:
                    year += 1
                    day = min(dt.day, calendar.monthrange(year, dt.month)[1])
                    candidate = datetime.date(year, dt.month, day)
                fy0_end = candidate
            except Exception:
                pass
    rem_days = max(0, min(365, (fy0_end - today).days))
    w0 = rem_days / 365.0
    w1 = 1.0 - w0
    return w0 * float(eps_fy0) + w1 * float(eps_fy1)


def fetch_wisereport_ntm_eps(code, headers, today=None):
    """Fetch FY0(E) and FY1(E) consensus EPS from WiseReport cF1002.aspx and return (eps_fy0, eps_fy1, ntm_eps)."""
    import requests
    import re
    from bs4 import BeautifulSoup

    today = today or datetime.date.today()
    url = f"https://navercomp.wisereport.co.kr/v2/company/cF1002.aspx?cmp_cd={code}&finGubun=MAIN"
    res = requests.get(url, headers=headers, timeout=5)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    # EPS is read by cell position, so refuse to parse a table whose layout moved (KI-004).
    data_checks.validate_wisereport_header([th.get_text(strip=True) for th in soup.select('table thead th')])

    eps_by_year = {}
    estimate_eps = []
    for tr in soup.select('table tbody tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all('td')]
        if len(cells) >= 6:
            data_checks.check_wisereport_row(cells)
            period_str = cells[0]
            eps_val = parse_korean_number(cells[5])
            if eps_val is None:
                continue
            m = re.search(r'(20\d{2})', period_str)
            if m:
                eps_by_year[int(m.group(1))] = eps_val
            if '(E)' in period_str:
                estimate_eps.append(eps_val)

    eps_fy0, eps_fy1 = None, None
    if today.year in eps_by_year and (today.year + 1) in eps_by_year:
        eps_fy0 = eps_by_year[today.year]
        eps_fy1 = eps_by_year[today.year + 1]
    elif len(estimate_eps) >= 2:
        eps_fy0, eps_fy1 = estimate_eps[0], estimate_eps[1]
    elif len(estimate_eps) == 1:
        eps_fy0 = estimate_eps[0]

    ntm_eps = compute_ntm_eps(eps_fy0, eps_fy1, today=today) if (eps_fy0 is not None and eps_fy1 is not None) else None
    return eps_fy0, eps_fy1, ntm_eps


def enrich_korean_stock(info, ticker_symbol, orig_fpe, orig_feps, orig_peg):
    """Overlay Naver / WiseReport consensus (and optional PyKrx) data on Yahoo data for KRX stocks."""
    import requests
    code = ticker_symbol.split('.')[0]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

    # Priority 1: Naver Mobile Stock Integration JSON API
    try:
        res = requests.get(f"https://m.stock.naver.com/api/stock/{code}/integration", headers=headers, timeout=5)
        res.raise_for_status()
        data = res.json()

        total_infos = data.get('totalInfos') or []
        kv = {item.get('code'): item.get('value') for item in total_infos if isinstance(item, dict)}
        cns = data.get('consensusInfo') or {}

        naver_close = parse_korean_number(data.get('closePrice'))
        if naver_close is not None and not (info.get('currentPrice') or info.get('regularMarketPrice')):
            info['currentPrice'] = naver_close

        naver_per = parse_korean_number(kv.get('per'))
        naver_eps = parse_korean_number(kv.get('eps'))
        naver_fwd_per = parse_korean_number(kv.get('cnsPer'))
        naver_fwd_eps = parse_korean_number(kv.get('cnsEps'))
        naver_pbr = parse_korean_number(kv.get('pbr'))
        naver_bps = parse_korean_number(kv.get('bps'))
        naver_div = parse_korean_number(kv.get('dividendYieldRatio'))
        naver_dps = parse_korean_number(kv.get('dividend'))
        naver_52w_high = parse_korean_number(kv.get('highPriceOf52Weeks'))
        naver_52w_low = parse_korean_number(kv.get('lowPriceOf52Weeks'))
        naver_mcap = parse_korean_number(kv.get('marketValue'))
        naver_target_mean = parse_korean_number(cns.get('priceTargetMean'))
        naver_recomm = parse_korean_number(cns.get('recommMean'))

        if naver_per is not None: info['trailingPE'] = naver_per
        if naver_eps is not None: info['trailingEps'] = naver_eps
        if naver_fwd_per is not None:
            # Naver's consensus P/E is for the current fiscal year (FY0), not NTM
            info['forwardPE'] = naver_fwd_per
            info['peFY0'] = naver_fwd_per
            info['_fwd_basis'] = 'FY0(네이버)'
        if naver_fwd_eps is not None:
            info['forwardEps'] = naver_fwd_eps
            info['epsFY0'] = naver_fwd_eps
            info['_naver_fy0_eps'] = naver_fwd_eps
        if orig_feps and orig_feps > 0:
            info['epsFY1'] = orig_feps
        if orig_fpe and orig_fpe > 0:
            info['peFY1'] = orig_fpe
        if naver_pbr is not None: info['priceToBook'] = naver_pbr
        if naver_bps is not None: info['bookValue'] = naver_bps
        if naver_div is not None:
            info['dividendYield'] = naver_div
            info['_div_is_pct'] = True
        if naver_dps is not None: info['dividendRate'] = naver_dps
        if naver_52w_high is not None: info['fiftyTwoWeekHigh'] = naver_52w_high
        if naver_52w_low is not None: info['fiftyTwoWeekLow'] = naver_52w_low
        # Naver's market value counts listed common shares only. Show it, but keep Yahoo's market cap
        # and EV untouched so EV-based multiples still include preferred equity.
        if naver_mcap is not None:
            info['marketCapCommon'] = naver_mcap
        if naver_target_mean is not None:
            info['targetMeanPriceNaver'] = naver_target_mean
            if not info.get('targetMeanPrice'):
                info['targetMeanPrice'] = naver_target_mean
                info['_target_source'] = '네이버'
        if naver_recomm is not None and (not info.get('recommendationKey') or str(info.get('recommendationKey')).lower() in ('none', 'n/a')):
            # Naver consensus scale: 5 강력매수 · 4 매수 · 3 중립 · 2 매도 · 1 강력매도
            info['recommendationKey'] = 'strong_buy' if naver_recomm >= 4.5 else ('buy' if naver_recomm >= 3.5 else ('hold' if naver_recomm >= 2.5 else 'sell'))

        if not total_infos:
            warn(f"{ticker_symbol}: 네이버 API가 빈 totalInfos를 반환했습니다.")
    except Exception as e:
        warn(f"{ticker_symbol}: 네이버 API 오류 ({e})")

    # Priority 1-B: WiseReport 12M Forward (NTM) EPS & P/E (blending FY0 and FY1 by remaining days d/365)
    try:
        wr_fy0, wr_fy1, ntm_eps = fetch_wisereport_ntm_eps(code, headers)
        info['_wr_fy0'], info['_wr_fy1'] = wr_fy0, wr_fy1
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if wr_fy0 is not None and wr_fy0 > 0:
            info['epsFY0'] = wr_fy0
            if price and price > 0:
                info['peFY0'] = price / wr_fy0
        if wr_fy1 is not None and wr_fy1 > 0:
            info['epsFY1'] = wr_fy1
            if price and price > 0:
                info['peFY1'] = price / wr_fy1
        if ntm_eps is not None and ntm_eps > 0 and price and price > 0:
            info['forwardEps'] = ntm_eps
            info['forwardPE'] = price / ntm_eps
            info['_fwd_basis'] = 'NTM'
    except Exception as e:
        warn(f"{ticker_symbol}: WiseReport NTM 수집 실패 ({e})")

    # Proportionally update PEG ratio if forwardPE changed
    new_fpe = info.get('forwardPE')
    if orig_peg and orig_peg > 0 and orig_fpe and orig_fpe > 0 and new_fpe and new_fpe > 0:
        info['pegRatio'] = orig_peg * (new_fpe / orig_fpe)

    # Priority 2: PyKrx Fallback (KRX Official Data) for anything still missing
    import os
    krx_id = os.environ.get('KRX_ID')
    krx_pw = os.environ.get('KRX_PW')
    if krx_id and krx_pw:
        try:
            from pykrx import stock

            df = None
            for i in range(10):
                date_str = (datetime.datetime.today() - datetime.timedelta(days=i)).strftime('%Y%m%d')
                temp_df = stock.get_market_fundamental(date_str, market="ALL")
                if not temp_df.empty:
                    df = temp_df
                    break

            if df is not None and code in df.index:
                row = df.loc[code]
                if not info.get('trailingPE') and 'PER' in row and row['PER'] > 0:
                    info['trailingPE'] = float(row['PER'])
                if not info.get('priceToBook') and 'PBR' in row and row['PBR'] > 0:
                    info['priceToBook'] = float(row['PBR'])
                if not info.get('bookValue') and 'BPS' in row and row['BPS'] > 0:
                    info['bookValue'] = float(row['BPS'])
                if not info.get('trailingEps') and 'EPS' in row and row['EPS'] > 0:
                    info['trailingEps'] = float(row['EPS'])
                if not info.get('dividendYield') and 'DIV' in row and row['DIV'] > 0:
                    info['dividendYield'] = float(row['DIV'])
                    info['_div_is_pct'] = True
        except Exception as e:
            warn(f"{ticker_symbol}: PyKrx 오류 ({e})")


def enrich_global_stock(info, t, orig_fpe, orig_peg):
    """Compute 12M Forward (NTM) EPS & P/E using d/365 day-weighting of FY0 and FY1."""
    eps_fy0 = info.get('epsCurrentYear')
    eps_fy1 = info.get('forwardEps') or info.get('epsForward')
    if eps_fy0 is None or eps_fy1 is None:
        try:
            ee = t.earnings_estimate
            if ee is not None and not ee.empty and 'avg' in ee.columns:
                if eps_fy0 is None and '0y' in ee.index and pd.notna(ee.loc['0y', 'avg']):
                    eps_fy0 = float(ee.loc['0y', 'avg'])
                if eps_fy1 is None and '+1y' in ee.index and pd.notna(ee.loc['+1y', 'avg']):
                    eps_fy1 = float(ee.loc['+1y', 'avg'])
        except Exception:
            pass
    ntm_eps = compute_ntm_eps(eps_fy0, eps_fy1, info=info)
    price = info.get('currentPrice') or info.get('regularMarketPrice')

    # Determine ADR / currency scale factor if EPS is in financialCurrency while price is in trading currency
    eps_scale = 1.0
    if orig_fpe and orig_fpe > 0 and eps_fy1 and eps_fy1 > 0 and price and price > 0:
        raw_fpe = price / float(eps_fy1)
        if raw_fpe > orig_fpe * 1.5 or raw_fpe < orig_fpe / 1.5:
            eps_scale = (price / orig_fpe) / float(eps_fy1)

    if eps_fy0 is not None and eps_fy0 > 0:
        scaled_fy0 = float(eps_fy0) * eps_scale
        info['epsFY0'] = scaled_fy0
        if price and price > 0:
            info['peFY0'] = price / scaled_fy0
    if eps_fy1 is not None and eps_fy1 > 0:
        scaled_fy1 = float(eps_fy1) * eps_scale
        info['epsFY1'] = scaled_fy1
        if price and price > 0:
            info['peFY1'] = price / scaled_fy1

    if ntm_eps is not None and ntm_eps > 0:
        scaled_ntm = float(ntm_eps) * eps_scale
        info['forwardEps'] = scaled_ntm
        if price and price > 0:
            new_fpe = price / scaled_ntm
            info['forwardPE'] = new_fpe
            info['_fwd_basis'] = 'NTM'
            if orig_peg and orig_peg > 0 and orig_fpe and orig_fpe > 0:
                info['pegRatio'] = orig_peg * (new_fpe / orig_fpe)


def check_krx_history(symbol, info):
    """Reconcile a KR stock's Yahoo history with KRX closes from Daum (KI-002, KI-006)."""
    try:
        ref = data_checks.fetch_daum_days(symbol.split('.')[0])
    except Exception as e:
        warn(ki('KI-002', f"{symbol}: 다음 금융 일별 시세 조회 실패({e}) — Yahoo 가격 이력을 거래소 종가와 대조하지 못했습니다."))
        return
    info['_krx_daily'] = ref
    hist = HISTORY.get(symbol)
    if hist is None or ref.empty:
        return
    fixed, filled, replaced = data_checks.reconcile_history(hist, ref)
    HISTORY[symbol] = fixed
    if filled:
        warn(ki('KI-002', f"{symbol}: Yahoo 가격 이력에 없거나 빈 거래일 {len(filled)}개"
                          f"({', '.join(f'{d:%m-%d}' for d in filled[-3:])})를 거래소 종가(다음 금융)로 채웠습니다."))
    if replaced:
        ex = ', '.join(f"{d:%m-%d} Yahoo ₩{y:,.0f}→₩{r:,.0f}" for d, y, r in replaced[:3])
        warn(ki('KI-006', f"{symbol}: Yahoo 종가가 거래소 종가(다음 금융)와 다른 {len(replaced)}일을 거래소 종가로 바꿨습니다({ex})."))


def check_volume(symbol):
    """Flag days whose Yahoo volume is under 1% of the trailing 20-day median (KI-005)."""
    hist = HISTORY.get(symbol)
    if hist is None or 'Volume' not in hist.columns:
        return
    outliers = data_checks.volume_outliers(hist['Volume'].iloc[-260:])
    if outliers:
        ex = ', '.join(f"{d:%Y-%m-%d} {v:,.0f}주(직전 중앙값 {m:,.0f}주)" for d, v, m in outliers[:3])
        warn(ki('KI-005', f"{symbol}: Yahoo 거래량 이상치 {len(outliers)}일 — {ex}. 거래량 관련 수치는 이 날짜를 제외하고 보세요."))


def check_statement_lag(t, info, symbol):
    """Warn when Yahoo's statement tables trail the periods its summary fields already report (KI-003)."""
    for attr, key, what, effect in (
            ('income_stmt', 'lastFiscalYearEnd', '연간', '사이클 위치·순환업종 판정은 그 이전 연도까지 기준이며, 갱신되면 판정이 바뀔 수 있습니다'),
            ('quarterly_income_stmt', 'mostRecentQuarter', '분기', '일회성 손익 감사·P/B 밴드는 이전 분기 기준입니다')):
        try:
            df = getattr(t, attr)
        except Exception:
            continue
        latest = max(df.columns) if df is not None and not df.empty else None
        lag = data_checks.statement_lag(latest, info.get(key))
        if lag:
            have = f"{pd.Timestamp(latest):%Y-%m-%d}" if latest is not None else '없음'
            warn(ki('KI-003', f"{symbol}: Yahoo {what} 재무제표가 최근 기간({lag:%Y-%m-%d} 마감)을 아직 반영하지 않았습니다"
                              f"(최신 {have}) — {effect}."))


def get_stats(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        try:
            info = t.info
        except Exception as inner_e:
            # Defend against yfinance _fetch_complementary() failure when base _info succeeded
            q = getattr(t, '_quote', None)
            info = getattr(q, '_info', None) if q is not None else None
            if info:
                warn(f"{ticker_symbol}: 보조 시세 조회 실패({inner_e}) — 기본 시세 정보만 사용")
            else:
                raise inner_e
        if not info or 'symbol' not in info:
            return None
        info = dict(info)

        # Ensure pegRatio fallback before overrides
        if info.get('pegRatio') is None and info.get('trailingPegRatio') is not None:
            info['pegRatio'] = info['trailingPegRatio']

        orig_fpe = info.get('forwardPE')
        orig_feps = info.get('forwardEps') or info.get('epsForward')
        orig_peg = info.get('pegRatio')
        # Yahoo's own values stay available: the scenario table and cross-checks need one consistent source.
        info['_yahoo_eps_fy1'] = orig_feps
        info['_yahoo_target_mean'] = info.get('targetMeanPrice')
        info['_target_source'] = 'Yahoo'
        info['_fwd_basis'] = 'FY1(Yahoo)' if orig_fpe else None

        if ticker_symbol.endswith('.KS') or ticker_symbol.endswith('.KQ'):
            enrich_korean_stock(info, ticker_symbol, orig_fpe, orig_feps, orig_peg)
        else:
            enrich_global_stock(info, t, orig_fpe, orig_peg)

        basis = info.get('_fwd_basis')
        if basis and basis != 'NTM':
            warn(f"{ticker_symbol}: Forward P/E가 12M(NTM)이 아니라 {basis} 기준입니다 — 표에 기준을 함께 표시합니다.")

        sanitize_metrics(info, ticker_symbol)
        try:
            hist = t.history(period='5y', auto_adjust=False)
            HISTORY[ticker_symbol] = hist if hist is not None and not hist.empty else None
        except Exception as e:
            HISTORY[ticker_symbol] = None
            warn(f"{ticker_symbol}: 가격 이력 조회 실패 ({e})")
        if ticker_symbol.endswith(('.KS', '.KQ')):
            check_krx_history(ticker_symbol, info)
        check_volume(ticker_symbol)
        check_statement_lag(t, info, ticker_symbol)
        info['_est'] = fetch_estimates(t, info, ticker_symbol)
        info['_cycle'] = analyze_cycle(t, info, ticker_symbol)
        info['_audit_result'] = audit_unusual_items(t, info, ticker_symbol)
        return info
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}", file=sys.stderr)
        return None


def fetch_estimates(t, info, symbol):
    """Yahoo consensus tables used by the revision, surprise and scenario sections."""
    est = {'scale': 1.0}
    for key, attr in (('ee', 'earnings_estimate'), ('trend', 'eps_trend'),
                      ('revisions', 'eps_revisions'), ('history', 'earnings_history')):
        try:
            df = getattr(t, attr)
            est[key] = df if isinstance(df, pd.DataFrame) and not df.empty else None
        except Exception as e:
            est[key] = None
            warn(f"{symbol}: Yahoo {attr} 조회 실패 ({e})")
    ee = est.get('ee')
    # ADRs can carry estimates per ordinary share in the reporting currency; rescale to the quoted unit.
    if ee is not None and '+1y' in ee.index and 'avg' in ee.columns:
        ee_fy1 = num(ee.loc['+1y', 'avg'])
        ref = num(info.get('_yahoo_eps_fy1'))
        if ee_fy1 and ref and ee_fy1 > 0 and ref > 0 and not (1 / 1.5 < ref / ee_fy1 < 1.5):
            est['scale'] = ref / ee_fy1
            warn(f"{symbol}: Yahoo 추정 EPS 단위를 x{est['scale']:.4f} 보정했습니다 (ADR·통화 단위 차이).")
    return est


def est_value(info, period, col):
    """Value from Yahoo earnings_estimate (rescaled to the quoted unit), or None."""
    est = info.get('_est') or {}
    ee = est.get('ee')
    if ee is None or period not in ee.index or col not in ee.columns:
        return None
    v = num(ee.loc[period, col])
    if v is None:
        return None
    return v if col == 'numberOfAnalysts' else v * est.get('scale', 1.0)


def analyze_cycle(t, info, symbol):
    """Earnings-cycle diagnostics: annual net income drawdown, margin position, and P/B band.

    Rule: references/rules/cycle-position.md (thresholds and known limits live there, not here).
    """
    out = {'auto': False, 'basis': None, 'opm_hist': []}
    try:
        inc = t.income_stmt
    except Exception as e:
        inc = None
        warn(f"{symbol}: 연간 손익계산서 조회 실패 ({e})")
    if inc is not None and not inc.empty:
        cols = sorted(inc.columns)
        ni_row = next((r for r in ('Net Income Common Stockholders', 'Net Income') if r in inc.index), None)
        if ni_row:
            ni = [(c, num(inc.loc[ni_row, c])) for c in cols]
            ni = [(c, v) for c, v in ni if v is not None]
            worst = None
            for i, (ci, vi) in enumerate(ni):
                if vi <= 0:
                    continue
                for cj, vj in ni[i + 1:]:
                    chg = (vj - vi) / vi
                    if worst is None or chg < worst[0]:
                        worst = (chg, ci, cj)
            if worst:
                out['auto'] = worst[0] <= -0.5
                out['basis'] = f"연간 순이익 최대 감소 {worst[1].year}→{worst[2].year} {worst[0] * 100:+.0f}%"
            elif ni:
                out['basis'] = f"연간 순이익 감소 이력 없음({ni[0][0].year}~{ni[-1][0].year})"
        if 'Operating Income' in inc.index and 'Total Revenue' in inc.index:
            for c in cols:
                oi, rev = num(inc.loc['Operating Income', c]), num(inc.loc['Total Revenue', c])
                if oi is not None and rev:
                    out['opm_hist'].append((c, oi / rev))

    opm_ttm = num(info.get('operatingMargins'))
    out['opm_ttm'] = opm_ttm
    hist_vals = [v for _, v in out['opm_hist']]
    if opm_ttm is not None and len(hist_vals) >= 3:
        top, mid = max(hist_vals), statistics.median(hist_vals)
        if opm_ttm > top:
            out['cycle_sig'], out['cycle_desc'] = '🔴', '이익률 과거 최고 초과 (정점 위험)'
        elif opm_ttm >= mid:
            out['cycle_sig'], out['cycle_desc'] = '🟡', '이익률 과거 중앙값~최고'
        else:
            out['cycle_sig'], out['cycle_desc'] = '🟢', '이익률 과거 중앙값 미만 (회복 구간)'
    out['band'] = compute_pb_band(t, info, symbol)
    return out


def compute_pb_band(t, info, symbol):
    """Historical P/B band from Yahoo balance sheets and same-day closes; the current P/B uses the same method.

    Rule: references/rules/verdict-matrix.md#pb-band
    """
    curr, fin = info.get('currency'), info.get('financialCurrency')
    if curr and fin and curr != fin:
        return {'skip': f'통화 불일치({curr}/{fin}) — ADR은 산출 생략'}
    raw = {}
    for attr in ('balance_sheet', 'quarterly_balance_sheet'):
        try:
            bs = getattr(t, attr)
        except Exception:
            bs = None
        if bs is None or bs.empty:
            continue
        eq_row = next((r for r in ('Common Stock Equity', 'Stockholders Equity') if r in bs.index), None)
        sh_row = next((r for r in ('Ordinary Shares Number', 'Share Issued') if r in bs.index), None)
        if not eq_row:
            continue
        for c in bs.columns:
            eq = num(bs.loc[eq_row, c])
            sh = num(bs.loc[sh_row, c]) if sh_row else None
            if eq and eq > 0:
                raw[pd.Timestamp(c).normalize()] = (eq, sh)
    shares = [sh for _, sh in raw.values() if sh and sh > 0]
    if len(raw) < 3 or not shares:
        return {'skip': f'재무상태표 시점 부족({len(raw)}개)'}
    med_sh = statistics.median(shares)
    fixed = 0
    bps = {}
    for d, (eq, sh) in raw.items():
        # Yahoo share counts occasionally jump (e.g. preferred shares mixed in); use the median for outliers
        if not sh or abs(sh / med_sh - 1) > 0.08:
            sh, fixed = med_sh, fixed + 1
        bps[d] = eq / sh
    if fixed:
        warn(ki('KI-007', f"{symbol}: 재무상태표 주식수 이상치 {fixed}건을 중앙값({med_sh:,.0f}주)으로 보정해 P/B 밴드를 계산했습니다."))

    hist = HISTORY.get(symbol)
    if hist is None or hist.empty:
        return {'skip': '가격 이력 없음'}
    close = hist['Close'].dropna()
    if close.index.tz is not None:
        close.index = close.index.tz_localize(None)
    close = close.sort_index()
    pbs = []
    for d in sorted(bps):
        if d < close.index[0]:
            continue
        p = num(close.asof(d))
        if p:
            pbs.append((d, p / bps[d]))
    if len(pbs) < 3:
        return {'skip': f'가격과 맞출 수 있는 시점 부족({len(pbs)}개)'}
    price = num(info.get('currentPrice') or info.get('regularMarketPrice'))
    if not price:
        return {'skip': '현재가 없음'}

    latest = max(bps)
    cur = price / bps[latest]
    vals = sorted(v for _, v in pbs)
    lo, mid, hi = vals[0], statistics.median(vals), vals[-1]
    if cur > hi:
        sig, desc = '🔴', '밴드 최고 초과'
    elif cur > mid:
        sig, desc = '🟡', '중앙값~최고'
    else:
        sig, desc = '🟢', '중앙값 이하'
    return {
        'n': len(pbs), 'start': pbs[0][0], 'end': pbs[-1][0], 'lo': lo, 'med': mid, 'hi': hi,
        'cur': cur, 'pos': (cur - lo) / (hi - lo) if hi > lo else None, 'sig': sig, 'desc': desc,
        'floor_price': lo * bps[latest], 'bps': bps[latest], 'bps_date': latest,
    }


def audit_unusual_items(t, info, ticker_symbol):
    """Detect large one-off items in the last 4 quarters and recompute nominal vs normalized
    ROE/EPS on the same denominators (average equity, median diluted shares)."""
    try:
        q = t.quarterly_income_stmt
        if q is None or q.empty:
            return None
        dates = [d for d in q.columns if q[d].notna().any()][:4]
        if len(dates) < 4:
            return None

        def ttm(row):
            if row not in q.index:
                return None
            vals = [num(q.loc[row, d]) for d in dates]
            vals = [v for v in vals if v is not None]
            return sum(vals) if vals else None

        pretax = ttm('Pretax Income')
        net_inc = ttm('Net Income Common Stockholders')
        if net_inc is None:
            net_inc = ttm('Net Income')
        norm_inc = ttm('Normalized Income')
        unusual = ttm('Total Unusual Items') or 0.0
        op_inc = ttm('Operating Income')

        # Trigger: unusual > 15% of pretax, or normalized income differs by > 15% of pretax, or NPM > OPM
        triggered = False
        if pretax and abs(unusual) > 0.15 * abs(pretax):
            triggered = True
        elif pretax and norm_inc is not None and net_inc is not None and abs(net_inc - norm_inc) > 0.15 * abs(pretax):
            triggered = True
        elif op_inc and op_inc > 0 and net_inc and net_inc > 0 and (net_inc / op_inc) > 1.05:
            triggered = True
        if not triggered or net_inc is None:
            return None

        max_q_date, max_q_val = None, 0.0
        if 'Total Unusual Items' in q.index:
            for d in dates:
                v = num(q.loc['Total Unusual Items', d])
                if v is not None and abs(v) > abs(max_q_val):
                    max_q_date, max_q_val = d.strftime('%Y-%m-%d'), v

        shares = None
        if 'Diluted Average Shares' in q.index:
            vals = [num(q.loc['Diluted Average Shares', d]) for d in dates]
            vals = [v for v in vals if v and v > 0]
            if vals:
                shares = statistics.median(vals)
        shares = shares or num(info.get('sharesOutstanding'))

        avg_eq = None
        bs = t.quarterly_balance_sheet
        if bs is not None and not bs.empty:
            eq_row = next((r for r in ('Common Stock Equity', 'Stockholders Equity') if r in bs.index), None)
            if eq_row:
                eqs = [num(bs.loc[eq_row, c]) for c in bs.columns]
                latest = eqs[0] if eqs else None
                year_ago = eqs[4] if len(eqs) > 4 else None
                if latest and latest > 0:
                    avg_eq = (latest + year_ago) / 2 if year_ago and year_ago > 0 else latest

        return {
            'symbol': ticker_symbol,
            'label': '일회성 이익' if unusual >= 0 else '일회성 손실',
            'max_date': max_q_date,
            'max_val': max_q_val,
            'removed': (net_inc - norm_inc) if norm_inc is not None else None,
            'rep_roe': net_inc / avg_eq if avg_eq else None,
            'norm_roe': norm_inc / avg_eq if (avg_eq and norm_inc is not None) else None,
            'rep_eps': net_inc / shares if shares else None,
            'norm_eps': norm_inc / shares if (shares and norm_inc is not None) else None,
            'currency': info.get('financialCurrency') or info.get('currency', 'USD'),
        }
    except Exception as e:
        warn(f"{ticker_symbol}: 일회성 손익 감사 실패 ({e})")
        return None


def cross_check(info, symbol):
    """financial-analyst 5% rule: flag gaps above 5% between data sources.

    Rule: references/rules/data-quality.md#cross-source-5
    """
    def check(label, a, a_src, b, b_src, note=''):
        a, b = num(a), num(b)
        if a and b and a > 0 and b > 0 and abs(a - b) / b > 0.05:
            warn(f"{symbol}: {label} 출처 간 차이 {abs(a - b) / b * 100:.1f}% — {a_src} {a:,.2f} vs {b_src} {b:,.2f}{note}")

    if symbol.endswith(('.KS', '.KQ')):
        check('올해(FY0) EPS', info.get('_wr_fy0'), 'WiseReport', est_value(info, '0y', 'avg'), 'Yahoo')
        check('내년(FY1) EPS', info.get('_wr_fy1'), 'WiseReport', est_value(info, '+1y', 'avg'), 'Yahoo', ' (시나리오 표는 Yahoo 기준)')
        check('올해(FY0) EPS', info.get('_wr_fy0'), 'WiseReport', info.get('_naver_fy0_eps'), '네이버', ' (WiseReport 표 구조가 바뀌었을 수 있음)')
        check('평균 목표가', info.get('targetMeanPriceNaver'), '네이버', info.get('_yahoo_target_mean'), 'Yahoo')
        check('시가총액', info.get('marketCapCommon'), '네이버(보통주)', info.get('marketCap'), 'Yahoo',
              ' (우선주 포함 여부 차이 — EV 배수는 Yahoo 기준 유지)')


def revision_summary(info):
    """30-day EPS revision breadth for FY0+FY1 and the change in the average estimate.

    Rule: references/rules/verdict-matrix.md#estimate-revisions
    """
    est = info.get('_est') or {}
    rev, trend = est.get('revisions'), est.get('trend')
    up = down = 0.0
    have = False
    if rev is not None:
        for h in ('0y', '+1y'):
            if h in rev.index:
                u = num(rev.loc[h, 'upLast30days']) if 'upLast30days' in rev.columns else None
                d = num(rev.loc[h, 'downLast30days']) if 'downLast30days' in rev.columns else None
                if u is not None or d is not None:
                    have = True
                    up += u or 0
                    down += d or 0
    chg = {}
    if trend is not None and {'current', '30daysAgo'} <= set(trend.columns):
        for h in ('0y', '+1y'):
            if h in trend.index:
                cur, ago = num(trend.loc[h, 'current']), num(trend.loc[h, '30daysAgo'])
                if cur and ago:
                    chg[h] = cur / ago - 1
    total = up + down
    breadth = (up - down) / total if have and total else None
    if breadth is not None and total >= 3:
        sig = '🟢' if breadth >= 0.3 else ('🔴' if breadth <= -0.3 else '🟡')
    elif '+1y' in chg:
        sig = '🟢' if chg['+1y'] > 0.01 else ('🔴' if chg['+1y'] < -0.01 else '🟡')
    else:
        sig = '⚪'
    text = f"상향 {up:.0f} / 하향 {down:.0f}" if have else 'N/A'
    return {'up': up, 'down': down, 'have': have, 'breadth': breadth, 'chg': chg, 'sig': sig, 'text': text}


def earnings_dates(info):
    """(last, next) earnings dates in KST from Yahoo's earnings timestamps."""
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    stamps = [num(info.get(k)) for k in ('earningsTimestamp', 'earningsTimestampStart', 'earningsTimestampEnd')]
    stamps = [s for s in stamps if s]
    past = [s for s in stamps if s <= now]
    future = [s for s in stamps if s > now]
    last = fmt_kst_date(max(past)) if past else 'N/A'
    nxt = fmt_kst_date(min(future)) if future else 'N/A'
    if future and info.get('isEarningsDateEstimate'):
        nxt += ' (예상)'
    return last, nxt


def fetch_investor_trends_table(ticker_code, company_name, info):
    import requests
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://finance.daum.net'}
    try:
        res = requests.get(f'https://m.stock.naver.com/api/stock/{ticker_code}/trend',
                           headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
    except Exception as e:
        warn(f"{company_name}({ticker_code}): 네이버 수급 API 오류 ({e})")
        return ''
    if not isinstance(res, list) or not res:
        return ''

    now_kst = datetime.datetime.now(KST)
    today_str = now_kst.strftime('%Y%m%d')
    naver_dates = [digits8(r.get('bizdate')) for r in res]
    has_today = today_str in naver_dates

    # A row dated today is only an intraday snapshot until its price/volume match the official close.
    status_note = ''
    today_label = ''
    if has_today:
        row = res[naver_dates.index(today_str)]
        reasons = []
        if (now_kst.hour, now_kst.minute) < (15, 40):
            reasons.append('장 마감(15:30) 전 실행')
        actual_close = num(info.get('regularMarketPrice') or info.get('currentPrice'))
        actual_vol = num(info.get('regularMarketVolume'))
        row_close = parse_korean_number(row.get('closePrice'))
        row_vol = parse_korean_number(row.get('accumulatedTradingVolume'))
        if actual_close and row_close and abs(row_close - actual_close) / actual_close > 0.001:
            # Since 2026-09-14 Naver's close field also differs from the KRX close after the session (KI-001).
            reasons.append(f'행 종가 ₩{row_close:,.0f} ≠ 실제 종가 ₩{actual_close:,.0f}(네이버 종가 기준 차이일 수 있음, KI-001)')
        if actual_vol and row_vol and abs(row_vol - actual_vol) / actual_vol > 0.03:
            reasons.append(f'행 거래량 {row_vol:,.0f}주 ≠ 실제 {actual_vol:,.0f}주')
        if reasons:
            today_label = '잠정'
            status_note = f"> ⚠️ 당일 행은 **잠정치(장중 스냅샷)**입니다 — {', '.join(reasons)}.\n\n"
            warn(f"{company_name}({ticker_code}): 당일 수급 행은 잠정치입니다 — {', '.join(reasons)}")
        else:
            today_label = '마감 후 집계'
            status_note = "> 당일 행은 장 마감 후 집계입니다(거래소 확정 거래대금과는 소폭 다를 수 있음).\n\n"

    rows = []
    tot_frgn_amt = tot_org_amt = tot_ind_amt = 0.0
    daum_row_used = False

    # Today has no Naver row yet: estimate today's foreign flow from the foreign-ownership change (intraday only)
    if not has_today and now_kst.weekday() < 5:
        try:
            dq = requests.get(f'https://finance.daum.net/api/quotes/A{ticker_code}', headers=headers, timeout=5).json()
            trade_date = digits8(dq.get('date') or dq.get('tradeDate'))
            if trade_date == today_str:
                ddays = requests.get(f'https://finance.daum.net/api/investor/days?page=1&perPage=5&symbolCode=A{ticker_code}',
                                     headers=headers, timeout=5).json()
                prev = next((d for d in (ddays.get('data') or [])
                             if digits8(d.get('date') or d.get('tradeDate')) not in ('', today_str)
                             and d.get('foreignOwnShares')), None)
                curr_shares = num(dq.get('foreignOwnShares'))
                prev_shares = num(prev.get('foreignOwnShares')) if prev else None
                curr_price = num(dq.get('tradePrice'))
                if curr_shares and prev_shares and curr_price:
                    diff_amt = (curr_shares - prev_shares) * curr_price / 1e8
                    tot_frgn_amt += diff_amt
                    ratio = num(dq.get('foreignRatio'))
                    ratio_str = f"{ratio * 100:.2f}%" if ratio is not None else 'N/A'
                    date_str = f"{today_str[:4]}-{today_str[4:6]}-{today_str[6:]}"
                    rows.append(f'| **{date_str} (장중 잠정)** | ₩{curr_price:,.0f} | **{diff_amt:+,.0f}억 (지분 변동 추정)** | (집계 전) | (집계 전) | {ratio_str} |')
                    daum_row_used = True
                    status_note = "> ⚠️ 당일 행은 외국인 지분 변동으로 추정한 **장중 잠정치**이며, 기관·개인은 아직 집계되지 않았습니다.\n\n"
        except Exception as e:
            warn(f"{company_name}({ticker_code}): 다음 금융 장중 수급 조회 실패 ({e})")

    krx = info.get('_krx_daily')
    basis_diffs = []
    for row in res[:4 if daum_row_used else 5]:
        bdate = digits8(row.get('bizdate'))
        date_str = f'{bdate[:4]}-{bdate[4:6]}-{bdate[6:]}' if len(bdate) == 8 else str(row.get('bizdate', ''))
        naver_close = float(str(row.get('closePrice', '0')).replace(',', ''))
        # Amounts use the KRX close; Naver's close field can follow a different basis (KI-001).
        krx_close = data_checks.ref_close_on(krx, bdate)
        close_p = krx_close or naver_close
        if krx_close and abs(krx_close - naver_close) > 0.5:
            basis_diffs.append((date_str, naver_close, krx_close))
        frgn_q = float(str(row.get('foreignerPureBuyQuant', '0')).replace(',', '').replace('+', ''))
        org_q = float(str(row.get('organPureBuyQuant', '0')).replace(',', '').replace('+', ''))
        ind_q = float(str(row.get('individualPureBuyQuant', '0')).replace(',', '').replace('+', ''))
        frgn_ratio = row.get('foreignerHoldRatio', 'N/A')

        frgn_amt = (frgn_q * close_p) / 1e8
        org_amt = (org_q * close_p) / 1e8
        ind_amt = (ind_q * close_p) / 1e8
        tot_frgn_amt += frgn_amt
        tot_org_amt += org_amt
        tot_ind_amt += ind_amt

        label = f"**{date_str} ({today_label})**" if (bdate == today_str and today_label) else date_str
        rows.append(f'| {label} | ₩{close_p:,.0f} | {frgn_amt:+,.0f}억 | {org_amt:+,.0f}억 | {ind_amt:+,.0f}억 | {frgn_ratio} |')

    if basis_diffs:
        ex = ', '.join(f"{d[5:]} 네이버 ₩{n:,.0f}/거래소 ₩{k:,.0f}" for d, n, k in basis_diffs[:3])
        warn(ki('KI-001', f"{company_name}({ticker_code}): 네이버 수급 표의 종가가 거래소 종가와 {len(basis_diffs)}일 다릅니다({ex}) "
                          "— 표의 종가와 금액은 거래소 종가(다음 금융)로 계산했습니다."))

    excl = " (당일 제외)" if daum_row_used else ""
    title = f'**{company_name} ({ticker_code}) 최근 5거래일 투자자별 순매매 추정**'
    header = '| 거래일자 | 종가 | 외국인 순매매 | 기관 순매매 | 개인 순매매 | 외국인 지분율 |\n|---|---|---|---|---|---|'
    summary = f'| **최근 5일 누적(추정)** | - | **{tot_frgn_amt:+,.0f}억 원** | **{tot_org_amt:+,.0f}억 원{excl}** | **{tot_ind_amt:+,.0f}억 원{excl}** | - |'
    return f'{title}\n\n{status_note}{header}\n' + '\n'.join(rows) + f'\n{summary}\n'


def data_basis_block(results):
    now = datetime.datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')
    parts = []
    for sym, info in results.items():
        state = str(info.get('marketState') or '')
        state_ko = MARKET_STATE_KO.get(state, state or 'N/A')
        ts = num(info.get('regularMarketTime'))
        last = datetime.datetime.fromtimestamp(ts, tz=KST).strftime('%m-%d %H:%M KST') if ts else 'N/A'
        delay = info.get('exchangeDataDelayedBy')
        parts.append(f"{sym} {state_ko}(최종 체결 {last}" + (f", {delay}분 지연" if delay else "") + ")")
    return (f"> 🕒 **데이터 기준**: {now} 생성 · " + " · ".join(parts) + "\n"
            "> 출처: Yahoo Finance(시세·재무·컨센서스), 네이버 금융(국내 지표·수급), WiseReport(국내 컨센서스 EPS), "
            "다음 금융(국내 거래소 종가 — Yahoo 이력 대조·보완, 수급 금액). 장중에 실행하면 시세·수급은 잠정치입니다. "
            "경고의 [KI-xxx]는 스킬 저장소 wiki/known-issues/의 사건 번호입니다.\n")


def overview_table(results):
    lines = ["### 1. 주요 주가 및 시가총액 현황\n",
             "| 기업명 (티커) | 현재 주가 | 52주 범위 | 시가총액 | 통화 |",
             "|---|---|---|---|---|"]
    for symbol, info in results.items():
        name = info.get('longName') or info.get('shortName') or symbol
        curr = info.get('currency', 'USD')
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        mcap_common = info.get('marketCapCommon')
        mcap = (format_large_number(mcap_common, curr) + " (보통주)") if mcap_common else format_large_number(info.get('marketCap'), curr)
        lines.append(f"| **{name} ({symbol})** | {format_number(price, True, curr)} | "
                     f"{format_number(info.get('fiftyTwoWeekLow'), True, curr)} ~ {format_number(info.get('fiftyTwoWeekHigh'), True, curr)} | {mcap} | {curr} |")
    return "\n".join(lines) + "\n"


def investor_section(tickers_list, results):
    tables = []
    for symbol in tickers_list:
        if symbol in results and symbol.endswith(('.KS', '.KQ')):
            info = results[symbol]
            name = info.get('shortName') or info.get('longName') or symbol
            tbl = fetch_investor_trends_table(symbol.split('.')[0], name, info)
            if tbl:
                tables.append(tbl)
    if not tables:
        return ''
    return ("### 1-1. 📉 최근 5거래일 투자자별 순매매 (추정)\n\n"
            "> 💡 금액은 네이버 금융의 투자자별 순매수 **수량 × 해당일 거래소 종가(다음 금융)**로 추정한 값이라 거래소 확정 거래대금과 다를 수 있습니다"
            "(거래소 종가를 못 받은 날은 네이버 종가 사용, KI-001). 보고서에서는 '추정'으로 표기하세요.\n\n"
            + "\n\n".join(tables) + "\n")


def technical_table(tickers_list, results):
    rows = []
    for symbol in tickers_list:
        info = results.get(symbol)
        hist = HISTORY.get(symbol)
        if info is None or hist is None:
            continue
        close = hist['Close'].dropna().iloc[-260:]
        if len(close) < 20:
            continue
        delta = close.diff()
        # Wilder's smoothing (alpha = 1/14): the standard RSI used by most charting tools
        avg_gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        avg_loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        rsi = 100 - 100 / (1 + avg_gain / avg_loss)
        sma20 = close.rolling(window=20).mean()
        lower = sma20 - 2 * close.rolling(window=20).std(ddof=0)

        curr, c_rsi, c_sma, c_lower = close.iloc[-1], rsi.iloc[-1], sma20.iloc[-1], lower.iloc[-1]
        dev_lower = ((curr - c_lower) / c_lower) * 100

        status = "정상 밴드 내"
        if c_rsi < 30 and dev_lower < 0:
            status = "🚨 극단적 과매도 & 밴드 하단 이탈"
        elif c_rsi < 30:
            status = "⚠️ RSI 과매도 구간 (<30)"
        elif dev_lower < 0:
            status = "⚠️ 볼린저 하단 이탈 (-2σ 하회)"
        elif c_rsi > 70:
            status = "🔥 RSI 과열 구간 (>70)"

        name = info.get('shortName') or info.get('longName') or symbol
        ccy = info.get('currency', 'USD')
        rows.append(f"| **{name} ({symbol})** | {format_number(float(curr), True, ccy)} | **{c_rsi:.1f}** | "
                    f"{format_number(float(c_sma), True, ccy)} | {format_number(float(c_lower), True, ccy)} | **{dev_lower:+.1f}%** | {status} |")

    if not rows:
        return ""
    return ("### 1-2. 📈 기술적 지표 (RSI · 볼린저밴드) — 진입 시점 보조용\n\n"
            "> 💡 14일 RSI(와일더 방식)와 20일 볼린저밴드(±2σ)입니다. 과매도는 '싸다'는 뜻이 아니므로 투자 판정에는 쓰지 않고, "
            "판정이 나온 뒤 진입 시점을 고르는 보조 지표로만 씁니다.\n\n"
            "| 기업명 (티커) | 현재 주가 | 14일 RSI | 20일 이평선 (SMA) | 볼린저 하단 (-2σ) | 하단 밴드 이탈도 | 기술적 국면 진단 |\n"
            "|---|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")


def default_benchmarks(symbols, results):
    marks = []
    if any(s.endswith(('.KS', '.KQ')) for s in symbols):
        marks.append('^KS11')
    if any('.' not in s for s in symbols):
        marks.append('^GSPC')
    if any('semiconductor' in str(results[s].get('industry', '')).lower() for s in symbols):
        marks.append('^SOX')
    return marks


def daily_closes(hist):
    """Close series indexed by tz-naive trading dates."""
    close = hist['Close'].dropna()
    idx = close.index.tz_localize(None) if close.index.tz is not None else close.index
    close.index = idx.normalize()
    return close[~close.index.duplicated(keep='last')].sort_index()


def market_index_for(sym):
    if sym.endswith('.KQ'):
        return '^KQ11'
    if sym.endswith('.KS'):
        return '^KS11'
    return '^GSPC' if '.' not in sym else None


def market_context_table(symbols, results, benchmarks):
    benchmarks = [b for b in benchmarks if b not in symbols]
    # Index histories double as each market's trading calendar, so they are loaded even when not listed.
    for b in set(benchmarks) | {market_index_for(s) for s in symbols if market_index_for(s)}:
        if b not in HISTORY:
            try:
                h = yf.Ticker(b).history(period='1y', auto_adjust=False)
                HISTORY[b] = h if h is not None and not h.empty else None
            except Exception as e:
                warn(f"{b}: 지수 시세 조회 실패 ({e})")
                HISTORY[b] = None

    rows = []
    for sym in list(symbols) + benchmarks:
        is_bench = sym not in results
        hist = HISTORY.get(sym)
        if hist is None or hist.empty:
            continue
        close = daily_closes(hist)
        if len(close) < 2:
            continue
        cal = list(close.index)
        if not is_bench and HISTORY.get(market_index_for(sym)) is not None:
            ref = daily_closes(HISTORY[market_index_for(sym)])
            cal = [d for d in ref.index if d <= close.index[-1]] or cal
            missing = [d for d in cal[-30:] if d not in close.index]
            if missing:
                warn(ki('KI-002', f"{sym}: Yahoo 가격 이력에 최근 거래일 {len(missing)}개가 빠져 있습니다"
                     f"({', '.join(f'{d:%m-%d}' for d in missing[:3])}) — 1일 등락은 전일 종가로, 5·20일 등락은 지수 거래일 기준으로 계산했고, "
                     "RSI·볼린저밴드는 누락분의 영향을 받을 수 있습니다."))

        def ret(n):
            if n == 1 and not is_bench:
                price = num(results[sym].get('regularMarketPrice') or results[sym].get('currentPrice'))
                prev = num(results[sym].get('regularMarketPreviousClose'))
                if price and prev:
                    return price / prev - 1
            if len(cal) <= n:
                return None
            base = num(close.asof(cal[-1 - n]))
            return float(close.iloc[-1] / base - 1) if base else None

        drawdown = float(close.iloc[-1] / close.iloc[-252:].max() - 1)
        name = BENCHMARK_NAMES.get(sym, sym) if is_bench else (results[sym].get('shortName') or sym)
        kind = '지수' if is_bench else '분석 기업'
        rows.append(f"| {name} ({sym}) | {kind} | {close.index[-1]:%Y-%m-%d} | {fmt_signed_pct(ret(1))} | "
                    f"{fmt_signed_pct(ret(5))} | {fmt_signed_pct(ret(20))} | {fmt_signed_pct(drawdown)} |")
    if not rows:
        return ''
    return ("### 1-3. 🌐 시장 비교 (지수·피어 동반 등락) — 급락·급등 원인 판별용\n\n"
            "> 💡 같은 기간 지수와 해외 피어도 함께 움직였다면 '기업 고유'나 '국내 수급'보다 '업종·시장 전반' 요인일 가능성이 큽니다. "
            "기준일이 다르면(한국 당일 마감 vs 미국 전일 종가) 시차를 감안하세요. 52주 고점 대비는 종가 기준입니다.\n\n"
            "| 대상 | 구분 | 기준일 | 1일 | 5일 | 20일 | 52주 고점 대비 |\n|---|---|---|---|---|---|---|\n"
            + "\n".join(rows) + "\n")


METRIC_ROWS = [
    ("**[밸류에이션]**", None, None),
    ("Trailing P/E (LTM)", 'trailingPE', format_number),
    ("⭐⭐⭐ Forward P/E (12M)", 'forwardPE', format_number),
    ("Trailing EPS (LTM)", 'trailingEps', format_number),
    ("Forward EPS (12M)", 'forwardEps', format_number),
    ("⭐⭐⭐ PEG Ratio", 'pegRatio', format_number),
    ("⭐⭐ EV/EBITDA", 'enterpriseToEbitda', format_number),
    ("EV/Revenue", 'enterpriseToRevenue', format_number),
    ("Price to Sales (P/S)", 'priceToSalesTrailing12Months', format_number),
    ("Price to Book (P/B)", 'priceToBook', format_number),
    ("Forward P/B (12M, 단순 추정)", 'forwardPriceToBook', format_number),
    ("BPS (주당순자산)", 'bookValue', format_number),
    ("Forward BPS (12M, 단순 추정)", 'forwardBookValue', format_number),
    ("**[수익성]**", None, None),
    ("⭐⭐ ROE (자기자본이익률)", 'returnOnEquity', format_percent),
    ("ROA (총자산이익률)", 'returnOnAssets', format_percent),
    ("듀퐁 재무레버리지 (자산/자본)", 'dupontLeverage', lambda v: f"{v:,.2f}배" if isinstance(v, (int, float)) else "N/A"),
    ("영업이익률 (OPM)", 'operatingMargins', format_percent),
    ("순이익률 (NPM)", 'profitMargins', format_percent),
    ("매출총이익률 (GPM)", 'grossMargins', format_percent),
    ("EBITDA 마진", 'ebitdaMargins', format_percent),
    ("**[성장성]**", None, None),
    ("⭐⭐⭐ 매출 성장률 (YoY)", 'revenueGrowth', format_percent),
    ("이익 성장률 (YoY)", 'earningsGrowth', format_percent),
    ("선행 EPS 성장률 (12M vs TTM)", 'forwardEpsGrowth', format_percent),
    ("**[재무 건전성]**", None, None),
    ("⭐⭐ 부채비율 (Debt/Equity)", 'debtToEquity', lambda v: f"{v:,.2f}%" if isinstance(v, (int, float)) else "N/A"),
    ("유동비율 (Current Ratio)", 'currentRatio', format_number),
    ("**[주주환원·수급·리스크]**", None, None),
    ("배당수익률 (Div Yield)", 'dividendYield', lambda v: f"{v:,.2f}%" if isinstance(v, (int, float)) else "N/A"),
    ("배당성향 (Payout Ratio)", 'payoutRatio', format_percent),
    ("베타 (β)", 'beta', format_number),
    ("공매도 잔고율 (Short % of Float)", 'shortPercentOfFloat', format_percent),
    ("기관 보유율 (Inst. Ownership)", 'heldPercentInstitutions', format_percent),
]


def metrics_table(results):
    syms = list(results.keys())
    lines = ["### 2. 핵심 재무 및 밸류에이션 지표\n",
             "> ⭐⭐⭐ 최우선 지표 | ⭐⭐ 확신 강화 지표 | 무표시 = 보조 지표 · Forward P/E 옆 괄호는 NTM이 아닌 기준일 때만 표시\n",
             "| 지표 항목 | " + " | ".join(syms) + " |",
             "|---| " + " | ".join("---" for _ in syms) + " |"]
    for label, key, formatter in METRIC_ROWS:
        if key is None:
            lines.append(f"| {label} | " + " | ".join("" for _ in syms) + " |")
            continue
        vals = []
        for info in results.values():
            if key in ('trailingEps', 'forwardEps', 'bookValue', 'forwardBookValue'):
                vals.append(format_number(info.get(key), True, info.get('currency', 'USD')))
            elif key == 'forwardPE':
                basis = info.get('_fwd_basis')
                vals.append(format_number(info.get(key)) + ('' if basis in (None, 'NTM') else f" ({basis})"))
            else:
                vals.append(formatter(info.get(key)))
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def trajectory_table(results):
    def ccy(info):
        return info.get('currency', 'USD')

    def rollover(info):
        if info.get('_is_cyclical'):
            return "N/A (순환업종)"
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        val = info.get('impliedRolloverPrice')
        if isinstance(val, (int, float)) and price:
            return f"{format_number(val, True, ccy(info))} ({(val - price) / price * 100:+.1f}%)"
        return "N/A"

    rows = [
        ("**[시계열별 PER 추이]**", None),
        ("① TTM PER (과거 12M 확정)", lambda i: format_number(i.get('trailingPE'))),
        ("② 올해 PER (FY0 컨센서스)", lambda i: format_number(i.get('peFY0'))),
        ("③ 내년 PER (FY1 컨센서스)", lambda i: format_number(i.get('peFY1'))),
        ("④ **12M Forward PER (NTM 가중)**", lambda i: f"**{format_number(i.get('forwardPE'))}**" + ('' if i.get('_fwd_basis') in (None, 'NTM') else f" ({i.get('_fwd_basis')})")),
        ("**[시계열별 EPS 추이]**", None),
        ("① TTM EPS (과거 12M 확정)", lambda i: format_number(i.get('trailingEps'), True, ccy(i))),
        ("② 올해 EPS (FY0 컨센서스)", lambda i: format_number(i.get('epsFY0'), True, ccy(i))),
        ("③ 내년 EPS (FY1 컨센서스)", lambda i: format_number(i.get('epsFY1'), True, ccy(i))),
        ("④ **12M Forward EPS (NTM 가중)**", lambda i: f"**{format_number(i.get('forwardEps'), True, ccy(i))}**"),
        ("**[PBR · BPS — Forward 값은 단순 추정]**", None),
        ("Trailing P/B (현재 장부 기준)", lambda i: format_number(i.get('priceToBook'))),
        ("12M Forward P/B (BPS + 선행 EPS − DPS)", lambda i: format_number(i.get('forwardPriceToBook'))),
        ("Trailing BPS (현재 주당순자산)", lambda i: format_number(i.get('bookValue'), True, ccy(i))),
        ("12M Forward BPS (BPS + 선행 EPS − DPS)", lambda i: format_number(i.get('forwardBookValue'), True, ccy(i))),
        ("**[참고: 단순 산술치]**", None),
        ("선행 EPS 성장률 (12M NTM vs TTM)", lambda i: f"{i['forwardEpsGrowth'] * 100:+.2f}%" if isinstance(i.get('forwardEpsGrowth'), (int, float)) else "N/A"),
        ("(참고) TTM PER × 선행 EPS", rollover),
    ]
    syms = list(results.keys())
    lines = ["### 2-1. 시계열별 PER · EPS 궤적 (보조 자료)\n",
             "> 💡 실적 궤적을 보는 보조 표입니다. Forward P/B·BPS는 자사주 매입·평가손익을 반영하지 않은 단순 추정이라 **과거 P/B와 비교하면 안 됩니다**(과거 비교는 2-2 표 사용). "
             "'TTM PER × 선행 EPS'는 목표가나 내재가치가 아닌 단순 산술치이며, 이익 정점에 과거 배수를 곱하는 오류가 생기므로 순환업종에는 표시하지 않습니다.\n",
             "| 시계열 / 항목 | " + " | ".join(syms) + " |",
             "|---| " + " | ".join("---" for _ in syms) + " |"]
    for label, fn in rows:
        if fn is None:
            lines.append(f"| {label} | " + " | ".join("" for _ in syms) + " |")
        else:
            lines.append(f"| {label} | " + " | ".join(fn(info) for info in results.values()) + " |")
    return "\n".join(lines) + "\n"


def cycle_tables(results):
    lines = ["### 2-2. 🔄 경기순환 진단 및 과거 밸류에이션 밴드\n",
             "> 💡 경기순환 업종은 이익 정점에서 PER·PEG가 가장 낮아 보입니다. 순환업종으로 분류된 기업은 5번 매트릭스에서 "
             "Forward PER·PEG·매출성장·EV/EBITDA·ROE 대신 **P/B 밴드 위치 · 사이클 위치(이익률) · 추정치 방향**으로 판정합니다. "
             "과거 비교는 아래 표의 기간 안에서만 유효합니다.\n",
             "| 기업 | 업종 유형 | 분류 근거 | 연간 영업이익률 범위 (회계연도) | TTM 영업이익률 | 사이클 위치 |",
             "|---|---|---|---|---|---|"]
    for sym, info in results.items():
        cyc = info.get('_cycle') or {}
        opms = cyc.get('opm_hist') or []
        if opms:
            rng = f"{min(v for _, v in opms) * 100:.1f}% ~ {max(v for _, v in opms) * 100:.1f}% ({opms[0][0].year}~{opms[-1][0].year})"
        else:
            rng = 'N/A'
        pos = f"{cyc['cycle_sig']} {cyc['cycle_desc']}" if cyc.get('cycle_sig') else '⚪ 데이터 부족'
        kind = '🔄 경기순환' if info.get('_is_cyclical') else '일반'
        lines.append(f"| **{sym}** | {kind} | {info.get('_cyc_basis', 'N/A')} | {rng} | {format_percent(cyc.get('opm_ttm'))} | {pos} |")

    lines += ["",
              "| 기업 | P/B 밴드 최저 · 중앙 · 최고 | 기간 (시점 수) | 현재 P/B (같은 방식) | 밴드 내 위치 | 밴드 최저 P/B 회귀 시 주가 (참고) |",
              "|---|---|---|---|---|---|"]
    for sym, info in results.items():
        band = (info.get('_cycle') or {}).get('band') or {}
        if not band.get('sig'):
            lines.append(f"| **{sym}** | N/A | {band.get('skip', 'N/A')} | - | - | - |")
            continue
        curr = info.get('currency', 'USD')
        price = num(info.get('currentPrice') or info.get('regularMarketPrice'))
        pos = f"{band['sig']} {band['desc']}" + (f" ({band['pos'] * 100:.0f}%)" if band.get('pos') is not None else '')
        floor = band['floor_price']
        floor_str = format_number(floor, True, curr) + (f" ({(floor / price - 1) * 100:+.1f}%)" if price else '')
        lines.append(f"| **{sym}** | {band['lo']:.2f} · {band['med']:.2f} · {band['hi']:.2f} | "
                     f"{band['start']:%Y-%m}~{band['end']:%Y-%m} ({band['n']}개) | {band['cur']:.2f} | {pos} | {floor_str} |")
    lines.append("\n> 밴드는 Yahoo 재무상태표(연말·분기말)의 자본÷주식수와 해당일 종가로 계산했고, 현재 P/B도 같은 방식이라 서로 비교할 수 있습니다"
                 "(네이버 P/B와는 다를 수 있음). 가용 기간이 짧고 구조적 변화(예: 새로운 수요)가 있으면 밴드 상단이 높아질 수 있으니 반대 논리에서 함께 다루세요.\n")
    return "\n".join(lines) + "\n"


def peer_table(results):
    if len(results) < 2:
        return ''
    syms = list(results.keys())
    specs = [
        ('Forward P/E', 'forwardPE', lambda v: f"{v:.2f}", True),
        ('EV/EBITDA', 'enterpriseToEbitda', lambda v: f"{v:.2f}", True),
        ('순이익률', 'profitMargins', lambda v: f"{v * 100:.1f}%", False),
        ('ROE', 'returnOnEquity', lambda v: f"{v * 100:.1f}%", False),
    ]
    lines = ["### 2-3. 피어 평균 대비 상대가치\n",
             "> 💡 분석 대상끼리의 단순 평균입니다. 순환업종과 일반 기업이 섞이면 평균의 의미가 약하니 참고용으로만 씁니다.\n",
             "| 지표 | " + " | ".join(syms) + " | 피어 평균 |",
             "|---|" + "---|" * (len(syms) + 1)]
    for label, key, fmt, positive_only in specs:
        vals = [num(results[s].get(key)) for s in syms]
        valid = [v for v in vals if v is not None and (v > 0 or not positive_only)]
        avg = sum(valid) / len(valid) if valid else None
        cells = [fmt(v) if v is not None else 'N/A' for v in vals]
        lines.append(f"| {label} | " + " | ".join(cells) + f" | **{fmt(avg) if avg is not None else 'N/A'}** |")
        if key == 'forwardPE' and avg:
            prem = [fmt_signed_pct(v / avg - 1, 0) if v and v > 0 else 'N/A' for v in vals]
            lines.append("| Forward P/E 평균 대비 | " + " | ".join(prem) + " | - |")
    return "\n".join(lines) + "\n"


def consensus_tables(results):
    lines = ["### 3. 애널리스트 투자의견·목표가 및 추정치 동향\n",
             "| 기업 (티커) | 투자의견 | 평균 목표가 | 최저 / 최고 | 애널리스트 수 | 상승 여력 | 국내 컨센서스 평균 목표가 (네이버) |",
             "|---|---|---|---|---|---|---|"]
    for sym, info in results.items():
        curr = info.get('currency', 'USD')
        price = num(info.get('currentPrice') or info.get('regularMarketPrice'))
        rec = str(info.get('recommendationKey') or 'N/A').upper()
        mean = num(info.get('targetMeanPrice'))
        n = info.get('numberOfAnalystOpinions')
        upside = fmt_signed_pct(mean / price - 1, 2) if (mean and price) else 'N/A'
        naver = num(info.get('targetMeanPriceNaver'))
        naver_str = f"{format_number(naver, True, curr)} ({(naver / price - 1) * 100:+.1f}%)" if (naver and price) else '-'
        lines.append(f"| **{sym}** | {rec} | {format_number(mean, True, curr)} ({info.get('_target_source', 'Yahoo')}) | "
                     f"{format_number(info.get('targetLowPrice'), True, curr)} / {format_number(info.get('targetHighPrice'), True, curr)} | "
                     f"{n if n else 'N/A'} | **{upside}** | {naver_str} |")
    lines.append("\n> 평균·최저·최고 목표가는 같은 출처(Yahoo)라 한 줄 안의 기준이 같습니다. 국내 컨센서스(네이버)는 별도 열로 비교합니다.\n")

    lines += ["#### 3-1. 이익 추정치 동향 (최근 30일) 및 실적 일정\n",
              "| 기업 | 올해(FY0) 평균 EPS 30일 변화 | 내년(FY1) 평균 EPS 30일 변화 | 30일 상향 / 하향 건수 (FY0+FY1) | 추정치 방향 | 최근 실적 발표 | 다음 실적 발표 |",
              "|---|---|---|---|---|---|---|"]
    for sym, info in results.items():
        r = info.get('_rev') or {}
        chg = r.get('chg') or {}
        last, nxt = earnings_dates(info)
        lines.append(f"| **{sym}** | {fmt_signed_pct(chg.get('0y'))} | {fmt_signed_pct(chg.get('+1y'))} | {r.get('text', 'N/A')} | "
                     f"{r.get('sig', '⚪')} | {last} | {nxt} |")
    lines.append("\n> 추정치 방향: 30일간 (상향 − 하향) ÷ 전체 건수가 +30% 이상이면 🟢, −30% 이하면 🔴, 건수가 3건 미만이면 내년 평균 EPS 변화(±1%)로 판단합니다. "
                 "Yahoo의 실적 발표일은 확정 실적 기준이라 한국 기업의 **잠정실적**은 빠질 수 있으니 웹 검색으로 확인하세요.\n")

    lines += ["#### 3-2. 최근 4분기 EPS 서프라이즈 (Yahoo)\n",
              "| 기업 | 분기 | 예상 EPS | 실제 EPS | 서프라이즈 |",
              "|---|---|---|---|---|"]
    for sym, info in results.items():
        hist = (info.get('_est') or {}).get('history')
        if hist is None:
            lines.append(f"| **{sym}** | N/A | - | - | - |")
            continue
        curr = info.get('currency', 'USD')
        for i, (idx, row) in enumerate(hist.tail(4).iterrows()):
            quarter = idx.strftime('%Y-%m') if hasattr(idx, 'strftime') else str(idx)
            lines.append(f"| {'**' + sym + '**' if i == 0 else ''} | {quarter} | {format_number(num(row.get('epsEstimate')), True, curr)} | "
                         f"{format_number(num(row.get('epsActual')), True, curr)} | {fmt_signed_pct(num(row.get('surprisePercent')))} |")
    lines.append("\n> 매출 서프라이즈와 잠정실적은 Yahoo에 없으므로 공시·IR 웹 검색으로 보완하세요.\n")
    return "\n".join(lines) + "\n"


def sig_lt(v, green, yellow):
    return '🟢' if v < green else ('🟡' if v < yellow else '🔴')


def sig_gt(v, green, yellow):
    return '🟢' if v > green else ('🟡' if v > yellow else '🔴')


def build_signals(info):
    """(display text, signal) for every pillar; the matrices pick the general or cyclical set.

    Rule: references/rules/verdict-matrix.md — change thresholds there and here in the same commit.
    """
    s = {}
    basis = info.get('_fwd_basis')
    fpe = num(info.get('forwardPE'))
    tag = '' if basis in (None, 'NTM') else f" ({basis})"
    s['fpe'] = (f"{fpe:.1f}{tag}", sig_lt(fpe, 18, 30)) if fpe and fpe > 0 else ('N/A', '⚪')
    peg = num(info.get('pegRatio'))
    s['peg'] = (f"{peg:.2f}", sig_lt(peg, 1, 2)) if peg and peg > 0 else ('N/A', '⚪')
    rg = num(info.get('revenueGrowth'))
    s['rg'] = (f"{rg * 100:+.1f}%", sig_gt(rg * 100, 20, 5)) if rg is not None else ('N/A', '⚪')
    ev = num(info.get('enterpriseToEbitda'))
    s['ev'] = (f"{ev:.1f}", sig_lt(ev, 12, 20)) if ev and ev > 0 else ('N/A', '⚪')
    audit = info.get('_audit_result') or {}
    roe, roe_tag = num(audit.get('norm_roe')), ' (정규화)'
    if roe is None:
        roe, roe_tag = num(info.get('returnOnEquity')), ''
    s['roe'] = (f"{roe * 100:.1f}%{roe_tag}", sig_gt(roe * 100, 20, 10)) if roe is not None else ('N/A', '⚪')
    de = num(info.get('debtToEquity'))
    s['de'] = (f"{de:.1f}%", sig_lt(de, 50, 100)) if de is not None else ('N/A', '⚪')
    rev = info.get('_rev') or {}
    s['rev'] = (rev.get('text', 'N/A'), rev.get('sig', '⚪'))
    cyc = info.get('_cycle') or {}
    band = cyc.get('band') or {}
    s['band'] = (f"P/B {band['cur']:.2f} (밴드 {band['lo']:.2f}~{band['hi']:.2f})", band['sig']) if band.get('sig') else ('N/A', '⚪')
    s['cycle'] = (cyc.get('cycle_desc', 'N/A'), cyc.get('cycle_sig', '⚪'))
    return s


def decision_verdict(sigs):
    """Rule: references/rules/verdict-matrix.md#aggregation"""
    g, r = sigs.count('🟢'), sigs.count('🔴')
    valid = len([x for x in sigs if x != '⚪'])
    if r >= 2:
        return "🔴 **신중 접근 (주의 신호 2개 이상)**"
    if valid < MIN_VALID_PILLARS:
        return "⚪ **판단 보류 (데이터 부족)**"
    if g >= 4 and r == 0:
        return "🟢 **강력 매수 후보**"
    if g >= 3 and r <= 1:
        return "🟢 **매수 고려**"
    return "🟡 **중립/관망**" + (" (주의 신호 1개)" if r == 1 else "")


def signal_matrix(results):
    lines = ["### 4. 투자 판단 신호등 매트릭스\n",
             "| 기업 (티커) | 유형 | 밸류에이션 | 수익성 | 성장성 | 재무건전성 | 종합 |",
             "|---|---|---|---|---|---|---|"]
    for sym, info in results.items():
        s = build_signals(info)
        cyclical = info.get('_is_cyclical')
        keys = ('band', 'cycle', 'rev', 'de') if cyclical else ('fpe', 'roe', 'rg', 'de')
        sigs = [s[k][1] for k in keys]
        g, r = sigs.count('🟢'), sigs.count('🔴')
        valid = len([x for x in sigs if x != '⚪'])
        overall = '🔴' if r >= 2 else ('⚪' if valid < 3 else ('🟢' if (g >= 3 and r == 0) else '🟡'))
        lines.append(f"| **{sym}** | {'🔄 순환' if cyclical else '일반'} | " + " | ".join(sigs) + f" | {overall} |")
    lines.append("\n> 🟢 양호 | 🟡 보통 | 🔴 주의 | ⚪ 데이터 없음 · **일반**: 밸류에이션=Forward PE(<18 🟢 <30 🟡) · 수익성=ROE(>20% 🟢 >10% 🟡, 일회성 감지 시 정규화 ROE) · "
                 "성장성=매출성장(>20% 🟢 >5% 🟡) · 재무건전성=D/E(<50% 🟢 <100% 🟡) · **🔄 순환**: 밸류에이션=P/B 밴드 위치 · 수익성=사이클 위치(이익률) · "
                 "성장성=이익 추정치 방향(30일) · 재무건전성=D/E · 종합: 🔴 2개 이상 🔴, 유효 3개 미만 ⚪, 🟢 3개 이상·🔴 0개 🟢, 그 외 🟡\n")
    return "\n".join(lines) + "\n"


DECISION_COLUMNS = [('fpe', 'Forward PE'), ('peg', 'PEG'), ('rg', '매출성장'), ('ev', 'EV/EBITDA'), ('roe', 'ROE'),
                    ('de', '부채비율'), ('rev', '추정치 방향(30일)'), ('band', 'P/B 밴드'), ('cycle', '사이클 위치')]


def decision_matrix(results):
    lines = ["### 5. ⭐ 핵심 지표 의사결정 매트릭스\n",
             "> 일반 기업은 Forward PE·PEG·매출성장·EV/EBITDA·ROE·부채비율·추정치 방향 7개로, 🔄 순환업종은 P/B 밴드·사이클 위치·추정치 방향·부채비율 4개로 판정합니다. "
             "순환업종은 이익 정점에서 PER·PEG·EV/EBITDA·ROE·매출성장이 모두 좋아 보이므로 '제외'로 표시하고 판정에 쓰지 않습니다.\n",
             "| 기업 (티커) | 유형 | " + " | ".join(lbl for _, lbl in DECISION_COLUMNS) + " | 종합 판단 |",
             "|---|---|" + "---|" * (len(DECISION_COLUMNS) + 1)]
    for sym, info in results.items():
        s = build_signals(info)
        cyclical = info.get('_is_cyclical')
        active = CYCLICAL_PILLARS if cyclical else GENERAL_PILLARS
        cells = [f"{s[k][0]} {s[k][1]}" if k in active else f"{s[k][0]} · 제외" for k, _ in DECISION_COLUMNS]
        verdict = decision_verdict([s[k][1] for k in active])
        lines.append(f"| **{sym}** | {'🔄 순환' if cyclical else '일반'} | " + " | ".join(cells) + f" | {verdict} |")
    lines.append("")
    lines.append("> **판정 기준**: Forward PE(<18 🟢 <30 🟡) · PEG(<1 🟢 <2 🟡) · 매출성장(>20% 🟢 >5% 🟡) · EV/EBITDA(<12 🟢 <20 🟡) · "
                 "ROE(>20% 🟢 >10% 🟡, 일회성 감지 시 정규화 ROE) · D/E(<50% 🟢 <100% 🟡) · 추정치 방향(30일 상향·하향 비율 ≥+30% 🟢, ≤−30% 🔴) · "
                 "P/B 밴드(중앙값 이하 🟢, 최고 이하 🟡, 최고 초과 🔴) · 사이클 위치(TTM 영업이익률이 과거 중앙값 미만 🟢, 최고 이하 🟡, 최고 초과 🔴)")
    lines.append("> **종합 판정 규칙**: 🔴 2개 이상 → 🔴 신중 접근 | 유효 신호 4개 미만 → ⚪ 판단 보류 | 🟢 4개 이상 & 🔴 0개 → 🟢 강력 매수 후보 | "
                 "🟢 3개 이상 & 🔴 1개 이하 → 🟢 매수 고려 | 그 외 → 🟡 중립/관망\n")
    return "\n".join(lines) + "\n"


def audit_table(results):
    lines = ["### 6. 🔍 [회계 감사] 일회성 손익(Unusual Items) 감지 및 정규화 지표 비교\n"]
    audits = [i['_audit_result'] for i in results.values() if i.get('_audit_result')]
    if not audits:
        lines.append("> 💡 분석 대상 전 종목에서 세전이익 대비 15% 이상의 일회성 손익 왜곡이 감지되지 않았습니다(Yahoo 분류 기준).\n")
        return "\n".join(lines) + "\n"
    lines += ["> ⚠️ 최근 4분기(TTM)에 큰 일회성 손익이 감지된 기업입니다. 명목·정규화 수치를 **같은 분모**(평균 자기자본, 희석주식수 중앙값)로 다시 계산해 "
              "서로 비교할 수 있게 맞췄습니다(2번 표의 ROE·EPS와는 기준이 다름). 비경상 항목 분류는 Yahoo 기준이라 회사 공시(DART·IR)와 다를 수 있으니, "
              "큰 항목은 공시로 확인하세요.\n",
              "| 기업 | 진단 | 최대 분기 비경상 항목 | TTM 제거 금액 (명목 − 정규화 순이익) | 명목 ROE → 정규화 ROE | 명목 EPS → 정규화 EPS |",
              "|---|---|---|---|---|---|"]
    for a in audits:
        ccy = a['currency']
        lines.append(f"| **{a['symbol']}** | ⚠️ **{a['label']} 감지** | {a['max_date'] or 'N/A'}: {format_large_number(a['max_val'], ccy)} | "
                     f"{format_large_number(a['removed'], ccy)} | {format_percent(a['rep_roe'])} → **{format_percent(a['norm_roe'])}** | "
                     f"{format_number(a['rep_eps'], True, ccy)} → **{format_number(a['norm_eps'], True, ccy)}** |")
    lines.append("\n> 💡 일반 기업 판정(5번)의 ROE는 정규화 값을 씁니다. 평가이익은 이후 분기에 평가손실로 되돌려질 수 있으니 관련 자산의 최근 가격 변동도 함께 확인하세요.\n")
    return "\n".join(lines) + "\n"


def scenario_table(results, weights):
    w_bull, w_base, w_bear = weights
    lines = ["### 7. 🧪 시나리오 스트레스 테스트 (스크립트 자동 산출 — 수치 임의 수정 금지)\n",
             "> - **EPS 시나리오**: 내년(FY1) 컨센서스 EPS의 최저(Bear) · 평균(Base) · 최고(Bull) — Yahoo Finance",
             "> - **배수 A (현재 배수 유지)**: 현재가 ÷ Yahoo 12M 선행 EPS — 리레이팅이 없다는 가정",
             "> - **배수 B (목표가 내재 배수)**: Yahoo 평균 목표가 ÷ FY1 평균 EPS — 애널리스트들이 가정한 배수",
             f"> - **확률 가중**: Bull {w_bull:.0%} · Base {w_base:.0%} · Bear {w_bear:.0%} (`--weights`로 변경)",
             "> - 하방이 음수(-)로 나오면 그대로 보고합니다. 결론에 맞추려고 배수·확률을 바꾸지 않습니다. 순환업종은 2-2 표의 '밴드 최저 P/B 회귀 시 주가'도 함께 보세요.\n",
             "| 기업 | 시나리오 | FY1 EPS | 배수 A 적용 주가 | 현재가 대비 | 배수 B 적용 주가 | 현재가 대비 |",
             "|---|---|---|---|---|---|---|"]
    summary = []
    for sym, info in results.items():
        ccy = info.get('currency', 'USD')
        price = num(info.get('currentPrice') or info.get('regularMarketPrice'))
        lo, avg, hi = (est_value(info, '+1y', c) for c in ('low', 'avg', 'high'))
        fy0 = est_value(info, '0y', 'avg')
        n = est_value(info, '+1y', 'numberOfAnalysts')
        if not price or avg is None:
            lines.append(f"| **{sym}** | Yahoo 추정치 없음 | - | - | - | - | - |")
            continue
        ntm = compute_ntm_eps(fy0, avg, info=info) if fy0 is not None else avg
        mult_a = price / ntm if ntm and ntm > 0 else None
        tgt = num(info.get('_yahoo_target_mean'))
        mult_b = tgt / avg if (tgt and avg > 0) else None

        prices = []
        for idx, (name, eps) in enumerate((('🐻 Bear (최저)', lo), ('⚖️ Base (평균)', avg), ('🐂 Bull (최고)', hi))):
            pa = eps * mult_a if (eps is not None and eps > 0 and mult_a) else None
            pb = eps * mult_b if (eps is not None and eps > 0 and mult_b) else None
            prices.append((pa, pb))
            head = f"**{sym}** (A {fmt_multiple(mult_a)} · B {fmt_multiple(mult_b)})" if idx == 0 else ""
            eps_str = format_number(eps, True, ccy)
            if eps is not None and eps <= 0:
                eps_str += " (적자 — P/E 적용 불가)"
            lines.append(f"| {head} | {name} | {eps_str} | {format_number(pa, True, ccy)} | {fmt_signed_pct(pa / price - 1) if pa else 'N/A'} | "
                         f"{format_number(pb, True, ccy)} | {fmt_signed_pct(pb / price - 1) if pb else 'N/A'} |")

        def expected(col):
            bear, base, bull = (p[col] for p in prices)
            if None in (bear, base, bull):
                return None
            return w_bull * bull + w_base * base + w_bear * bear

        ea, eb = expected(0), expected(1)
        lines.append(f"|  | **확률가중 기대값** | - | **{format_number(ea, True, ccy)}** | **{fmt_signed_pct(ea / price - 1) if ea else 'N/A'}** | "
                     f"**{format_number(eb, True, ccy)}** | **{fmt_signed_pct(eb / price - 1) if eb else 'N/A'}** |")

        down = prices[0][0] / price - 1 if prices[0][0] else None
        up = prices[2][0] / price - 1 if prices[2][0] else None
        parts = [f"하방(Bear·배수 A) {fmt_signed_pct(down)}", f"상방(Bull·배수 A) {fmt_signed_pct(up)}"]
        if down is not None and up is not None and down < 0 < up:
            parts.append(f"상방/하방 비율 {up / -down:.1f} : 1")
        if lo is not None and hi is not None and avg:
            parts.append(f"추정치 범위 폭 {(hi - lo) / avg:.0%}" + (f" (애널리스트 {n:.0f}명)" if n else ""))
        summary.append(f"- **{sym}**: " + " · ".join(parts))
    lines.append("")
    lines += summary
    return "\n".join(lines) + "\n"


def warnings_section():
    lines = ["### 8. ⚠️ 데이터 품질 경고 (스크립트 자동 점검)\n"]
    if WARNINGS:
        lines.append("> 아래 항목에 해당하는 수치를 본문에서 인용할 때는 경고 내용을 함께 밝히세요.\n")
        lines += [f"- {w}" for w in dict.fromkeys(WARNINGS)]
    else:
        lines.append("> 자동 점검에서 발견된 경고가 없습니다.")
    return "\n".join(lines) + "\n"


def generate_report(tickers_list, cyclical_add=frozenset(), cyclical_remove=frozenset(), benchmarks=None, weights=DEFAULT_WEIGHTS):
    results = {}
    for symbol in tickers_list:
        print(f"Fetching data for {symbol}...", file=sys.stderr)
        info = get_stats(symbol)
        if info:
            results[symbol] = info
        else:
            warn(f"{symbol}: 데이터를 가져오지 못해 표에서 제외했습니다.")

    if not results:
        print("No data retrieved.", file=sys.stderr)
        sys.exit(1)

    for symbol, info in results.items():
        cyc = info.get('_cycle') or {}
        basis = cyc.get('basis') or '연간 순이익 데이터 없음'
        if symbol in cyclical_remove:
            info['_is_cyclical'], info['_cyc_basis'] = False, f"사용자 지정(일반) · {basis}"
        elif symbol in cyclical_add:
            info['_is_cyclical'], info['_cyc_basis'] = True, f"사용자 지정(순환) · {basis}"
        else:
            info['_is_cyclical'] = bool(cyc.get('auto'))
            info['_cyc_basis'] = f"자동 · {basis}" + (" (−50% 이하 → 순환)" if cyc.get('auto') else "")
        info['_rev'] = revision_summary(info)
        cross_check(info, symbol)

    symbols = list(results.keys())
    sections = [
        "## 📊 정량 데이터 분석 결과 (스크립트 자동 산출)\n",
        data_basis_block(results),
        overview_table(results),
        investor_section(tickers_list, results),
        technical_table(tickers_list, results),
        market_context_table(symbols, results, benchmarks if benchmarks else default_benchmarks(symbols, results)),
        metrics_table(results),
        trajectory_table(results),
        cycle_tables(results),
        peer_table(results),
        consensus_tables(results),
        signal_matrix(results),
        decision_matrix(results),
        audit_table(results),
        scenario_table(results, weights),
    ]
    sections.append(warnings_section())
    return "\n".join(s for s in sections if s)


def parse_weights(text):
    try:
        vals = tuple(float(x) for x in text.split(','))
    except ValueError:
        return None
    if len(vals) != 3 or any(v < 0 for v in vals) or abs(sum(vals) - 1.0) > 1e-6:
        return None
    return vals


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Fetch stock financials (Yahoo Finance + Naver/WiseReport for KRX) as markdown tables.")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of stock tickers")
    parser.add_argument("--cyclical", type=str, default="", help="Comma-separated tickers to treat as cyclical (memory, chemicals, steel, shipping, refining ...)")
    parser.add_argument("--not-cyclical", type=str, default="", help="Comma-separated tickers to exclude from automatic cyclical detection")
    parser.add_argument("--benchmarks", type=str, default="", help="Comma-separated index tickers for the market comparison table (default: auto)")
    parser.add_argument("--weights", type=str, default="0.2,0.5,0.3", help="Scenario probabilities Bull,Base,Bear (must sum to 1)")
    args = parser.parse_args()

    weights = parse_weights(args.weights)
    if weights is None:
        parser.error("--weights must be three non-negative numbers (Bull,Base,Bear) that sum to 1, e.g. 0.2,0.5,0.3")

    def split(text):
        return [x.strip() for x in text.split(',') if x.strip()]

    markdown_report = generate_report(split(args.tickers), set(split(args.cyclical)), set(split(args.not_cyclical)),
                                      split(args.benchmarks) or None, weights)
    print(markdown_report)
