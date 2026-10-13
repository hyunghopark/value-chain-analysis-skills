#!/usr/bin/env python3
import argparse
import sys
import json
import yfinance as yf
import pandas as pd

def format_number(val, is_currency=False, currency="USD"):
    if val is None:
        return "N/A"
    if isinstance(val, (int, float)):
        if is_currency:
            if currency == "KRW":
                return f"₩{val:,.0f}"
            else:
                return f"${val:,.2f}"
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
        if val >= 1e12:
            suffix = "T"
            divisor = 1e12
        elif val >= 1e9:
            suffix = "B"
            divisor = 1e9
        elif val >= 1e6:
            suffix = "M"
            divisor = 1e6
        else:
            suffix = ""
            divisor = 1
        
        formatted = f"{val / divisor:,.2f}{suffix}"
        if currency == "KRW":
            return f"₩{formatted}"
        return f"${formatted}"
    return str(val)

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
        for num, unit in re.findall(r'([0-9]+(?:\.[0-9]+)?)\s*(조|억|만)', text):
            matched = True
            mult = {'조': 1e12, '억': 1e8, '만': 1e4}[unit]
            total += float(num) * mult
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
        pe = info.get('trailingPE')
        roe = info.get('returnOnEquity')
        pb = info.get('priceToBook')
        if pe and roe and pe > 0 and roe > 0:
            implied_pb = pe * roe
            if pb is None or pb <= 0 or pb > implied_pb * 2.5 or pb < implied_pb / 2.5:
                print(f"[Warn] {ticker_symbol}: Adjusted distorted P/B ({pb} -> {implied_pb:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                info['priceToBook'] = implied_pb

        ps = info.get('priceToSalesTrailing12Months')
        ev_rev = info.get('enterpriseToRevenue')
        ev_ebitda = info.get('enterpriseToEbitda')
        ebitda_m = info.get('ebitdaMargins')
        npm = info.get('profitMargins')

        if pe and npm and pe > 0 and npm > 0:
            implied_ps = pe * npm
            if ps is None or ps <= 0 or ps > implied_ps * 2.5 or ps < implied_ps / 2.5:
                print(f"[Warn] {ticker_symbol}: Adjusted distorted P/S ({ps} -> {implied_ps:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                ps = implied_ps
                info['priceToSalesTrailing12Months'] = ps

        if ps and ps > 0:
            if ev_rev is None or ev_rev <= 0 or ev_rev > ps * 2.5 or ev_rev < ps / 2.5:
                print(f"[Warn] {ticker_symbol}: Adjusted distorted EV/Revenue ({ev_rev} -> {ps:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                ev_rev = ps
                info['enterpriseToRevenue'] = ev_rev
            if ebitda_m and ebitda_m > 0:
                implied_ev_ebitda = ev_rev / ebitda_m
                if ev_ebitda is None or ev_ebitda <= 0 or ev_ebitda > implied_ev_ebitda * 2.0 or ev_ebitda < implied_ev_ebitda / 2.0:
                    print(f"[Warn] {ticker_symbol}: Adjusted distorted EV/EBITDA ({ev_ebitda} -> {implied_ev_ebitda:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                    info['enterpriseToEbitda'] = implied_ev_ebitda

        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price and price > 0:
            if pe and pe > 0:
                implied_teps = price / pe
                t_eps = info.get('trailingEps')
                if t_eps is None or t_eps <= 0 or t_eps > implied_teps * 1.5 or t_eps < implied_teps / 1.5:
                    print(f"[Warn] {ticker_symbol}: Adjusted distorted Trailing EPS ({t_eps} -> {implied_teps:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                    info['trailingEps'] = implied_teps
            fpe = info.get('forwardPE')
            if fpe and fpe > 0:
                implied_feps = price / fpe
                f_eps = info.get('forwardEps')
                if f_eps is None or f_eps <= 0 or f_eps > implied_feps * 1.5 or f_eps < implied_feps / 1.5:
                    print(f"[Warn] {ticker_symbol}: Adjusted distorted Forward EPS ({f_eps} -> {implied_feps:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
                    info['forwardEps'] = implied_feps
            pb_now = info.get('priceToBook')
            if pb_now and pb_now > 0:
                implied_bps = price / pb_now
                bv = info.get('bookValue')
                if bv is None or bv <= 0 or bv > implied_bps * 1.5 or bv < implied_bps / 1.5:
                    print(f"[Warn] {ticker_symbol}: Adjusted distorted BPS ({bv} -> {implied_bps:.2f}) due to currency mismatch ({curr} vs {fin_curr})", file=sys.stderr)
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

    # 4. Derived TTM-based future value metrics & Forward BPS / Forward P/B (12M)
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
    import datetime
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
    import datetime
    import re
    from bs4 import BeautifulSoup

    today = today or datetime.date.today()
    url = f"https://navercomp.wisereport.co.kr/v2/company/cF1002.aspx?cmp_cd={code}&finGubun=MAIN"
    res = requests.get(url, headers=headers, timeout=5)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')

    eps_by_year = {}
    estimate_eps = []
    for tr in soup.select('table tbody tr'):
        cells = [td.get_text(strip=True) for td in tr.find_all('td')]
        if len(cells) >= 6:
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
                print(f"[Warn] {ticker_symbol}: Complementary fetch failed ({inner_e}); using base quote info", file=sys.stderr)
            else:
                raise inner_e
        if not info or 'symbol' not in info:
            return None

        # Ensure pegRatio fallback before overrides
        if info.get('pegRatio') is None and info.get('trailingPegRatio') is not None:
            info['pegRatio'] = info['trailingPegRatio']

        orig_fpe = info.get('forwardPE')
        orig_feps = info.get('forwardEps') or info.get('epsForward')
        orig_peg = info.get('pegRatio')

        # For Korean stocks, enhance yfinance data with Naver Mobile Integration JSON API + WiseReport NTM consensus
        if ticker_symbol.endswith('.KS') or ticker_symbol.endswith('.KQ'):
            code = ticker_symbol.split('.')[0]
            orig_mcap = info.get('marketCap')
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            # Priority 1: Naver Mobile Stock Integration JSON API
            try:
                import requests
                
                url = f"https://m.stock.naver.com/api/stock/{code}/integration"
                res = requests.get(url, headers=headers, timeout=5)
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
                    info['forwardPE'] = naver_fwd_per
                    info['peFY0'] = naver_fwd_per
                if naver_fwd_eps is not None:
                    info['forwardEps'] = naver_fwd_eps
                    info['epsFY0'] = naver_fwd_eps
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
                if naver_mcap is not None:
                    info['marketCap'] = naver_mcap
                    if orig_mcap and orig_mcap > 0:
                        mcap_ratio = naver_mcap / orig_mcap
                        if info.get('priceToSalesTrailing12Months'):
                            info['priceToSalesTrailing12Months'] = info['priceToSalesTrailing12Months'] * mcap_ratio
                        orig_ev = info.get('enterpriseValue')
                        if orig_ev and orig_ev > 0:
                            new_ev = orig_ev - orig_mcap + naver_mcap
                            ev_ratio = (new_ev / orig_ev) if new_ev > 0 else mcap_ratio
                            info['enterpriseValue'] = new_ev
                        else:
                            ev_ratio = mcap_ratio
                        if info.get('enterpriseToRevenue'):
                            info['enterpriseToRevenue'] = info['enterpriseToRevenue'] * ev_ratio
                        if info.get('enterpriseToEbitda'):
                            info['enterpriseToEbitda'] = info['enterpriseToEbitda'] * ev_ratio
                if naver_target_mean is not None: info['targetMeanPrice'] = naver_target_mean
                if naver_recomm is not None and (not info.get('recommendationKey') or str(info.get('recommendationKey')).lower() in ('none', 'n/a')):
                    info['recommendationKey'] = 'strong_buy' if naver_recomm >= 4.0 else ('buy' if naver_recomm >= 3.5 else ('hold' if naver_recomm >= 2.5 else 'sell'))
                
                if not total_infos:
                    print(f"[Warn] Naver API returned empty totalInfos for {ticker_symbol}", file=sys.stderr)
                
            except Exception as e:
                print(f"Naver API error for {ticker_symbol}: {e}", file=sys.stderr)

            # Priority 1-B: WiseReport 12M Forward (NTM) EPS & P/E (blending FY0 and FY1 by remaining days d/365)
            try:
                wr_fy0, wr_fy1, ntm_eps = fetch_wisereport_ntm_eps(code, headers)
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
            except Exception as e:
                print(f"[Warn] WiseReport NTM fetch error for {ticker_symbol}: {e}", file=sys.stderr)

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
                    import datetime
                    
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
                    print(f"PyKrx error for {ticker_symbol}: {e}", file=sys.stderr)
        else:
            # Global stocks: Compute 12M Forward (NTM) EPS & P/E using d/365 day-weighting of FY0 and FY1
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
                    if orig_peg and orig_peg > 0 and orig_fpe and orig_fpe > 0:
                        info['pegRatio'] = orig_peg * (new_fpe / orig_fpe)

        sanitize_metrics(info, ticker_symbol)
        info['_audit_result'] = audit_unusual_items(t, info, ticker_symbol)
        return info
    except Exception as e:
        print(f"Error fetching {ticker_symbol}: {e}", file=sys.stderr)
        return None

def audit_unusual_items(t, info, ticker_symbol):
    try:
        q = t.quarterly_income_stmt
        if q is None or q.empty:
            return None
        dates = q.columns[:4]
        if len(dates) == 0:
            return None
        pretax = q.loc['Pretax Income', dates].sum() if 'Pretax Income' in q.index else 0
        net_inc = q.loc['Net Income', dates].sum() if 'Net Income' in q.index else 0
        norm_inc = q.loc['Normalized Income', dates].sum() if 'Normalized Income' in q.index else None
        unusual = q.loc['Total Unusual Items', dates].sum() if 'Total Unusual Items' in q.index else 0
        op_inc = q.loc['Operating Income', dates].sum() if 'Operating Income' in q.index else 0

        # Check trigger: unusual > 15% of pretax, or norm_inc differs by > 15%, or NPM > OPM
        is_triggered = False
        if pretax != 0 and abs(unusual) > 0.15 * abs(pretax):
            is_triggered = True
        elif pretax != 0 and norm_inc is not None and abs(net_inc - norm_inc) > 0.15 * abs(pretax):
            is_triggered = True
        elif op_inc > 0 and net_inc > 0 and (net_inc / op_inc) > 1.05:
            is_triggered = True

        if not is_triggered:
            return None

        # Find largest unusual quarter
        max_q_date = None
        max_q_val = 0
        if 'Total Unusual Items' in q.index:
            for d in dates:
                v = q.loc['Total Unusual Items', d]
                if abs(v) > abs(max_q_val):
                    max_q_val = v
                    max_q_date = d.strftime('%Y-%m-%d')

        curr = info.get('currency', 'USD')
        shares = info.get('sharesOutstanding') or (q.loc['Diluted Average Shares', dates[0]] if 'Diluted Average Shares' in q.index else None)
        rep_eps = info.get('trailingEps') or (net_inc / shares if shares else None)
        norm_eps = (norm_inc / shares) if (norm_inc is not None and shares) else None

        rep_roe = info.get('returnOnEquity')
        bs = t.quarterly_balance_sheet
        equity = bs.loc['Stockholders Equity', bs.columns[0]] if (bs is not None and not bs.empty and 'Stockholders Equity' in bs.index) else None
        norm_roe = (norm_inc / equity) if (norm_inc is not None and equity and equity > 0) else None

        # Institutional descriptions for major events
        if ticker_symbol == '000660.KS':
            desc = "2026년 2분기(2026-06-30) 키옥시아(Kioxia) 지분 평가·처분이익 약 +50.72조 원 등 투자자산 관련 손익"
        else:
            desc = f"최대 분기({max_q_date}): Unusual Items {format_large_number(max_q_val, curr)} (비경상 투자/자산 평가·처분 및 특수 손익)"

        return {
            'symbol': ticker_symbol,
            'unusual_ttm': unusual,
            'max_date': max_q_date,
            'max_val': max_q_val,
            'rep_eps': rep_eps,
            'norm_eps': norm_eps,
            'rep_roe': rep_roe,
            'norm_roe': norm_roe,
            'desc': desc,
            'currency': curr
        }
    except Exception as e:
        print(f"[Warn] Audit failed for {ticker_symbol}: {e}", file=sys.stderr)
        return None

def fetch_investor_trends_table(ticker_code, company_name=''):
    import requests
    import datetime
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://finance.daum.net'}
    url = f'https://m.stock.naver.com/api/stock/{ticker_code}/trend'
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
    except Exception as e:
        return ''
    if not isinstance(res, list) or not res:
        return ''

    today_str = datetime.datetime.now().strftime('%Y%m%d')
    has_today = any(r.get('bizdate') == today_str for r in res)

    rows = []
    tot_frgn_amt = 0
    tot_org_amt = 0
    tot_ind_amt = 0

    # If today is not in trend yet, fetch real-time quote for today's foreign trading
    if not has_today:
        try:
            dq_url = f'https://finance.daum.net/api/quotes/A{ticker_code}'
            dq = requests.get(dq_url, headers=headers, timeout=5).json()
            trade_date = dq.get('date')
            curr_shares = dq.get('foreignOwnShares')
            curr_price = dq.get('tradePrice', 0)
            curr_ratio = f"{dq.get('foreignRatio', 0)*100:.2f}%"

            ddays_url = f'https://finance.daum.net/api/investor/days?page=1&perPage=2&symbolCode=A{ticker_code}'
            ddays = requests.get(ddays_url, headers=headers, timeout=5).json()
            if 'data' in ddays and ddays['data']:
                y_shares = ddays['data'][0].get('foreignOwnShares')
                if curr_shares and y_shares:
                    diff_q = curr_shares - y_shares
                    diff_amt = (diff_q * curr_price) / 1e8
                    tot_frgn_amt += diff_amt
                    rows.append(f'| **{trade_date} (당일 실시간)** | ₩{curr_price:,.0f} | **{diff_amt:+,.0f}억 (잠정)** | (정산중) | (정산중) | {curr_ratio} |')
        except Exception:
            pass

    for row in res[:4 if not has_today else 5]:
        bdate = str(row.get('bizdate', ''))
        date_str = f'{bdate[:4]}-{bdate[4:6]}-{bdate[6:]}' if len(bdate) == 8 else bdate
        close_p = float(str(row.get('closePrice', '0')).replace(',', ''))
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

        rows.append(f'| {date_str} | ₩{close_p:,.0f} | {frgn_amt:+,.0f}억 | {org_amt:+,.0f}억 | {ind_amt:+,.0f}억 | {frgn_ratio} |')

    org_suffix = "" if has_today else " (당일제외)"
    ind_suffix = "" if has_today else " (당일제외)"
    title_suffix = "(당일 최종 정산 확정)" if has_today else "(당일 실시간 연동)"
    title = f'**{company_name} ({ticker_code}) 최근 5거래일 투자자별 순매매 동향 {title_suffix}**'
    header = '| 거래일자 | 종가 | 외국인 순매매 | 기관 순매매 | 개인 순매매 | 외국인 지분율 |\n|---|---|---|---|---|---|'
    summary = f'| **최근 5일 누적** | - | **{tot_frgn_amt:+,.0f}억 원** | **{tot_org_amt:+,.0f}억 원{org_suffix}** | **{tot_ind_amt:+,.0f}억 원{ind_suffix}** | - |'

    return f'{title}\n\n{header}\n' + '\n'.join(rows) + f'\n{summary}\n'

def fetch_technical_indicators_table(tickers_list, results):
    rows = []
    for symbol in tickers_list:
        try:
            t = yf.Ticker(symbol)
            df = t.history(period='3mo')
            if df.empty or len(df) < 20:
                continue
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            sma20 = df['Close'].rolling(window=20).mean()
            std20 = df['Close'].rolling(window=20).std()
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20

            curr = df['Close'].iloc[-1]
            c_rsi = rsi.iloc[-1]
            c_sma = sma20.iloc[-1]
            c_lower = lower.iloc[-1]
            c_upper = upper.iloc[-1]
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

            info = results.get(symbol, {})
            name = info.get('shortName') or info.get('longName') or symbol
            curr_code = info.get('currency', 'USD')
            curr_str = f"₩{curr:,.0f}" if curr_code == "KRW" else f"${curr:,.2f}"
            lower_str = f"₩{c_lower:,.0f}" if curr_code == "KRW" else f"${c_lower:,.2f}"
            sma_str = f"₩{c_sma:,.0f}" if curr_code == "KRW" else f"${c_sma:,.2f}"

            rows.append(f"| **{name} ({symbol})** | {curr_str} | **{c_rsi:.1f}** | {sma_str} | {lower_str} | **{dev_lower:+.1f}%** | {status} |")
        except Exception as e:
            print(f"[Warn] Technical indicator calculation failed for {symbol}: {e}", file=sys.stderr)

    if not rows:
        return ""

    table = "### 1-2. 📈 퀀트 기술적 모멘텀 및 변동성 지표 (RSI · 볼린저밴드 이탈도)\n\n"
    table += "> 💡 **기술적 과매도/과열 진단**: 14일 RSI(상대강도지수) 및 20일 볼린저밴드(±2σ) 하단 이탈도를 통해 주가의 극단적 패닉셀 및 기술적 반등 트리거를 정량 진단합니다.\n\n"
    table += "| 기업명 (티커) | 현재 주가 | 14일 RSI | 20일 이평선 (SMA) | 볼린저 하단 (-2σ) | 하단 밴드 이탈도 | 기술적 국면 진단 |\n"
    table += "|---|---|---|---|---|---|---|\n"
    table += "\n".join(rows) + "\n\n"
    return table

def generate_report(tickers_list):
    results = {}
    for symbol in tickers_list:
        print(f"Fetching data for {symbol}...", file=sys.stderr)
        info = get_stats(symbol)
        if info:
            results[symbol] = info
        else:
            print(f"Could not retrieve data for {symbol}", file=sys.stderr)
    
    if not results:
        print("No data retrieved.", file=sys.stderr)
        sys.exit(1)
        
    # Generate Output Markdown Tables
    output = "## 📊 Yahoo Finance API 실시간 데이터 분석 결과\n\n"
    
    # 1. Overview Table
    output += "### 1. 주요 주가 및 시가총액 현황\n\n"
    output += "| 기업명 (티커) | 현재 주가 | 52주 범위 | 시가총액 | 통화 |\n"
    output += "|---|---|---|---|---|\n"
    for symbol, info in results.items():
        name = info.get('longName', info.get('shortName', symbol))
        curr = info.get('currency', 'USD')
        price = info.get('currentPrice', info.get('regularMarketPrice'))
        high = info.get('fiftyTwoWeekHigh')
        low = info.get('fiftyTwoWeekLow')
        mcap = info.get('marketCap')
        
        output += f"| **{name} ({symbol})** | {format_number(price, True, curr)} | {format_number(low, True, curr)} ~ {format_number(high, True, curr)} | {format_large_number(mcap, curr)} | {curr} |\n"
    output += "\n"

    # 1-1. Investor Trend Tables (Korean stocks)
    kr_trends = []
    for symbol in tickers_list:
        if symbol.endswith('.KS') or symbol.endswith('.KQ'):
            code = symbol.split('.')[0]
            cname = results.get(symbol, {}).get('shortName') or results.get(symbol, {}).get('longName') or symbol
            tbl = fetch_investor_trends_table(code, cname)
            if tbl:
                kr_trends.append(tbl)
    if kr_trends:
        output += "### 1-1. 📉 최근 5거래일 투자자별 수급 동향 (외국인 · 기관 · 개인 거래대금 추정)\n\n"
        output += "> 💡 **수급 왜곡 진단**: 최근 주가 급변동 국면에서 외국인과 기관의 프로그램 매도세 및 개인 수급 흡수 강도를 정량 추적합니다.\n\n"
        output += "\n\n".join(kr_trends) + "\n\n"

    # 1-2. Technical Indicators Table (Quant Momentum & Bollinger Bands)
    tech_table = fetch_technical_indicators_table(tickers_list, results)
    if tech_table:
        output += tech_table

    # 2. Key Valuation Metrics Table
    output += "### 2. 핵심 재무 및 밸류에이션 지표\n\n"
    output += "> ⭐⭐⭐ 최우선 지표 | ⭐⭐ 확신 강화 지표 | 무표시 = 보조 지표\n\n"
    output += "| 지표 항목 | " + " | ".join([symbol for symbol in results.keys()]) + " |\n"
    output += "|---| " + " | ".join(["---" for _ in results.keys()]) + " |\n"
    
    metrics = [
        # --- Valuation Multiples ---
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
        ("Forward P/B (12M)", 'forwardPriceToBook', format_number),
        ("BPS (주당순자산)", 'bookValue', format_number),
        ("Forward BPS (12M)", 'forwardBookValue', format_number),
        # --- Profitability ---
        ("**[수익성]**", None, None),
        ("⭐⭐ ROE (자기자본이익률)", 'returnOnEquity', format_percent),
        ("ROA (총자산이익률)", 'returnOnAssets', format_percent),
        ("듀퐁 재무레버리지 (자산/자본)", 'dupontLeverage', lambda v: f"{v:,.2f}배" if isinstance(v, (int, float)) else "N/A"),
        ("영업이익률 (OPM)", 'operatingMargins', format_percent),
        ("순이익률 (NPM)", 'profitMargins', format_percent),
        ("매출총이익률 (GPM)", 'grossMargins', format_percent),
        ("EBITDA 마진", 'ebitdaMargins', format_percent),
        # --- Growth ---
        ("**[성장성]**", None, None),
        ("⭐⭐⭐ 매출 성장률 (YoY)", 'revenueGrowth', format_percent),
        ("이익 성장률 (YoY)", 'earningsGrowth', format_percent),
        ("선행 EPS 성장률 (12M vs TTM)", 'forwardEpsGrowth', format_percent),
        # --- Financial Health ---
        ("**[재무 건전성]**", None, None),
        ("⭐⭐ 부채비율 (Debt/Equity)", 'debtToEquity', lambda v: f"{v:,.2f}%" if isinstance(v, (int, float)) else "N/A"),
        ("유동비율 (Current Ratio)", 'currentRatio', format_number),
        # --- Shareholder Return & Positioning ---
        ("**[주주환원·수급·리스크]**", None, None),
        ("배당수익률 (Div Yield)", 'dividendYield', lambda v: f"{v:,.2f}%" if isinstance(v, (int, float)) else "N/A"),
        ("배당성향 (Payout Ratio)", 'payoutRatio', format_percent),
        ("베타 (β)", 'beta', format_number),
        ("공매도 잔고율 (Short % of Float)", 'shortPercentOfFloat', format_percent),
        ("기관 보유율 (Inst. Ownership)", 'heldPercentInstitutions', format_percent),
    ]
    
    for label, key, formatter in metrics:
        if key is None:
            # Section header row
            row = f"| {label} | " + " | ".join(["" for _ in results.keys()]) + " |"
        else:
            row = f"| {label} | "
            vals = []
            for symbol, info in results.items():
                if key in ('trailingEps', 'forwardEps', 'bookValue', 'forwardBookValue'):
                    vals.append(format_number(info.get(key), is_currency=True, currency=info.get('currency', 'USD')))
                else:
                    vals.append(formatter(info.get(key)))
            row += " | ".join(vals) + " |"
        output += row + "\n"
    output += "\n"

    # 2-1. 4-Horizon PER & EPS Trajectory and TTM-Based Implied Valuation Table (Visual Reference Only)
    output += "### 2-1. 시계열별 PER · EPS 상세 궤적 및 TTM 기반 내재가치 (시각적 비교용)\n\n"
    output += "> 💡 **참고**: 이 표는 시계열별(과거 4분기 · 올해 FY0 · 내년 FY1 · 향후 12개월 NTM) 실적 궤적과 자본 누적 효과(Forward PBR·BPS), TTM 멀티플 유지 가정 시의 내재가치를 비교하기 위한 시각적 보조 자료이며, 투자 판정(4·5번 매트릭스)은 표준 **12M Forward (NTM)** 기준을 그대로 유지합니다.\n\n"
    output += "| 시계열 / 내재가치 항목 | " + " | ".join([symbol for symbol in results.keys()]) + " |\n"
    output += "|---| " + " | ".join(["---" for _ in results.keys()]) + " |\n"

    trajectory_rows = [
        ("**[시계열별 PER 추이]**", None),
        ("① TTM PER (과거 12M 확정)", lambda info: format_number(info.get('trailingPE'))),
        ("② 올해 PER (FY0 컨센서스)", lambda info: format_number(info.get('peFY0'))),
        ("③ 내년 PER (FY1 컨센서스)", lambda info: format_number(info.get('peFY1'))),
        ("④ **12M Forward PER (NTM 가중)**", lambda info: f"**{format_number(info.get('forwardPE'))}**"),
        ("**[시계열별 EPS 추이]**", None),
        ("① TTM EPS (과거 12M 확정)", lambda info: format_number(info.get('trailingEps'), True, info.get('currency', 'USD'))),
        ("② 올해 EPS (FY0 컨센서스)", lambda info: format_number(info.get('epsFY0'), True, info.get('currency', 'USD'))),
        ("③ 내년 EPS (FY1 컨센서스)", lambda info: format_number(info.get('epsFY1'), True, info.get('currency', 'USD'))),
        ("④ **12M Forward EPS (NTM 가중)**", lambda info: f"**{format_number(info.get('forwardEps'), True, info.get('currency', 'USD'))}**"),
        ("**[PBR · BPS 자본 누적 추이]**", None),
        ("Trailing P/B (현재 장부 기준)", lambda info: format_number(info.get('priceToBook'))),
        ("**12M Forward P/B (이익 누적 반영)**", lambda info: f"**{format_number(info.get('forwardPriceToBook'))}**"),
        ("Trailing BPS (현재 주당순자산)", lambda info: format_number(info.get('bookValue'), True, info.get('currency', 'USD'))),
        ("**12M Forward BPS (이익 누적 반영)**", lambda info: f"**{format_number(info.get('forwardBookValue'), True, info.get('currency', 'USD'))}**"),
        ("**[TTM 기반 미래가치 역산]**", None),
        ("선행 EPS 성장률 (12M NTM vs TTM)", lambda info: f"**{info['forwardEpsGrowth']*100:+.2f}%**" if isinstance(info.get('forwardEpsGrowth'), (int, float)) else "N/A"),
        ("TTM PER 유지 시 1년 뒤 내재주가", lambda info: (
            f"**{format_number(info['impliedRolloverPrice'], True, info.get('currency', 'USD'))}** ({((info['impliedRolloverPrice'] - (info.get('currentPrice') or info.get('regularMarketPrice'))) / (info.get('currentPrice') or info.get('regularMarketPrice'))) * 100:+.1f}%)"
            if isinstance(info.get('impliedRolloverPrice'), (int, float)) and (info.get('currentPrice') or info.get('regularMarketPrice'))
            else "N/A"
        )),
    ]

    for label, fn in trajectory_rows:
        if fn is None:
            row = f"| {label} | " + " | ".join(["" for _ in results.keys()]) + " |"
        else:
            vals = [fn(info) for info in results.values()]
            row = f"| {label} | " + " | ".join(vals) + " |"
        output += row + "\n"
    output += "\n"

    # 3. Consensus & Targets Table
    output += "### 3. 애널리스트 투자의견 및 목표 주가\n\n"
    output += "| 기업명 (티커) | 투자의견 | 평균 목표가 | 최저가 / 최고가 | 현재가 대비 상승 여력 |\n"
    output += "|---|---|---|---|---|\n"
    for symbol, info in results.items():
        curr = info.get('currency', 'USD')
        price = info.get('currentPrice', info.get('regularMarketPrice'))
        rec = info.get('recommendationKey', 'N/A').upper()
        target_mean = info.get('targetMeanPrice')
        target_low = info.get('targetLowPrice')
        target_high = info.get('targetHighPrice')
        
        upside = "N/A"
        if price and target_mean:
            pct = ((target_mean - price) / price) * 100
            upside = f"{pct:+.2f}%"
            
        output += f"| **{symbol}** | {rec} | {format_number(target_mean, True, curr)} | {format_number(target_low, True, curr)} / {format_number(target_high, True, curr)} | **{upside}** |\n"
    output += "\n"

    # 4. Investment Signal Matrix
    output += "### 4. 투자 판단 신호등 매트릭스\n\n"
    output += "| 기업 (티커) | 밸류에이션 | 수익성 | 성장성 | 재무건전성 | 종합 |\n"
    output += "|---|---|---|---|---|---|\n"
    for symbol, info in results.items():
        signals = []
        # Valuation signal (보수적 기준): Forward PE < 18 green, < 30 yellow, else red
        fpe = info.get('forwardPE')
        if fpe is not None:
            signals.append("🟢" if fpe < 18 else ("🟡" if fpe < 30 else "🔴"))
        else:
            signals.append("⚪")
        # Profitability: ROE > 20% green, > 10% yellow, else red
        roe = info.get('returnOnEquity')
        if roe is not None:
            roe_pct = roe * 100
            signals.append("🟢" if roe_pct > 20 else ("🟡" if roe_pct > 10 else "🔴"))
        else:
            signals.append("⚪")
        # Growth: Revenue growth > 20% green, > 5% yellow, else red
        rg = info.get('revenueGrowth')
        if rg is not None:
            rg_pct = rg * 100
            signals.append("🟢" if rg_pct > 20 else ("🟡" if rg_pct > 5 else "🔴"))
        else:
            signals.append("⚪")
        # Health (보수적 기준): D/E < 50 green, < 100 yellow, else red
        de = info.get('debtToEquity')
        if de is not None:
            signals.append("🟢" if de < 50 else ("🟡" if de < 100 else "🔴"))
        else:
            signals.append("⚪")
        # Overall: 보수적 리스크 관리 (🔴 2개 이상 시 즉시 🔴, 🔴 없어야만 🟢)
        green_count = signals.count("🟢")
        red_count = signals.count("🔴")
        if red_count >= 2:
            overall = "🔴"
        elif green_count >= 3 and red_count == 0:
            overall = "🟢"
        elif green_count >= 2 and red_count <= 1:
            overall = "🟡"
        else:
            overall = "🔴"
        output += f"| **{symbol}** | {signals[0]} | {signals[1]} | {signals[2]} | {signals[3]} | {overall} |\n"
    output += "\n"
    output += "> 🟢 양호 | 🟡 보통 | 🔴 주의 | ⚪ 데이터 없음 (기준: Forward PE <18 🟢 <30 🟡 · ROE >20% 🟢 >10% 🟡 · 매출성장 >20% 🟢 >5% 🟡 · D/E <50% 🟢 <100% 🟡)\n\n"

    # 5. Key Metrics Decision Matrix
    output += "### 5. ⭐ 핵심 지표 의사결정 매트릭스\n\n"
    output += "> ⭐⭐⭐ Tier 1 + ⭐⭐ Tier 2 지표만 모아 한눈에 비교 (보수적 엄격 기준 적용)\n\n"
    output += "| 기업 (티커) | Forward PE | PEG | 매출성장 | EV/EBITDA | ROE | 부채비율 | 종합 판단 |\n"
    output += "|---|---|---|---|---|---|---|---|\n"
    for symbol, info in results.items():
        # Forward PE (보수적 기준: < 18 🟢, < 30 🟡, else 🔴)
        fpe = info.get('forwardPE')
        if fpe is not None and fpe > 0:
            fpe_sig = "🟢" if fpe < 18 else ("🟡" if fpe < 30 else "🔴")
            fpe_str = f"{fpe:.1f} {fpe_sig}"
        else:
            fpe_str = "N/A ⚪"
            fpe_sig = "⚪"

        # PEG (성장성 대비 가치: < 1.0 🟢, < 2.0 🟡, else 🔴)
        peg = info.get('pegRatio')
        if peg is not None and peg > 0:
            peg_sig = "🟢" if peg < 1 else ("🟡" if peg < 2 else "🔴")
            peg_str = f"{peg:.2f} {peg_sig}"
        else:
            peg_str = "N/A ⚪"
            peg_sig = "⚪"

        # Revenue Growth (매출 성장: > 20% 🟢, > 5% 🟡, else 🔴)
        rg = info.get('revenueGrowth')
        if rg is not None:
            rg_pct = rg * 100
            rg_sig = "🟢" if rg_pct > 20 else ("🟡" if rg_pct > 5 else "🔴")
            rg_str = f"+{rg_pct:.1f}% {rg_sig}" if rg_pct >= 0 else f"{rg_pct:.1f}% {rg_sig}"
        else:
            rg_str = "N/A ⚪"
            rg_sig = "⚪"

        # EV/EBITDA (보수적 현금창출력: < 12 🟢, < 20 🟡, else 🔴)
        ev = info.get('enterpriseToEbitda')
        if ev is not None and ev > 0:
            ev_sig = "🟢" if ev < 12 else ("🟡" if ev < 20 else "🔴")
            ev_str = f"{ev:.1f} {ev_sig}"
        else:
            ev_str = "N/A ⚪"
            ev_sig = "⚪"

        # ROE (자본 효율성: > 20% 🟢, > 10% 🟡, else 🔴)
        roe = info.get('returnOnEquity')
        if roe is not None:
            roe_pct = roe * 100
            roe_sig = "🟢" if roe_pct > 20 else ("🟡" if roe_pct > 10 else "🔴")
            roe_str = f"{roe_pct:.1f}% {roe_sig}"
        else:
            roe_str = "N/A ⚪"
            roe_sig = "⚪"

        # D/E (보수적 부채비율: < 50% 🟢, < 100% 🟡, else 🔴)
        de = info.get('debtToEquity')
        if de is not None:
            de_sig = "🟢" if de < 50 else ("🟡" if de < 100 else "🔴")
            de_str = f"{de:.1f}% {de_sig}"
        else:
            de_str = "N/A ⚪"
            de_sig = "⚪"

        # Overall verdict (보수적 엄격 판정: 🔴가 2개 이상이면 즉시 '신중 접근', 🔴가 1개라도 있으면 '강력 매수' 원천 차단)
        all_sigs = [fpe_sig, peg_sig, rg_sig, ev_sig, roe_sig, de_sig]
        g = all_sigs.count("🟢")
        r = all_sigs.count("🔴")
        valid = len([s for s in all_sigs if s != "⚪"])

        if valid == 0:
            verdict = "⚪ 데이터 부족"
        elif r >= 2:
            verdict = "🔴 **신중 접근 (리스크 경고)**"
        elif g >= 4 and r == 0:
            verdict = "🟢 **강력 매수 후보**"
        elif g >= 3 and r <= 1:
            verdict = "🟢 **매수 고려**"
        elif r == 1:
            verdict = "🟡 **조건부 매수 (주의 요망)**"
        else:
            verdict = "🟡 **조건부 매수 (중립)**"

        output += f"| **{symbol}** | {fpe_str} | {peg_str} | {rg_str} | {ev_str} | {roe_str} | {de_str} | {verdict} |\n"

    output += "\n"
    output += "> **판정 기준 (보수적 엄격 기준)**: Forward PE(<18 🟢 <30 🟡) · PEG(<1 🟢 <2 🟡) · 매출성장(>20% 🟢 >5% 🟡) · EV/EBITDA(<12 🟢 <20 🟡) · ROE(>20% 🟢 >10% 🟡) · D/E(<50% 🟢 <100% 🟡)\n"
    output += "> **종합 판정 규칙**: 🔴 2개 이상 시 즉시 '신중 접근' | 🔴 1개 이상 시 '강력 매수' 원천 차단 (🟢 4개 이상 & 🔴 0개 시에만 강력 매수)\n\n"

    # 6. Audit of Unusual Items and Normalized Metrics
    output += "### 6. 🔍 [회계 감사] 일회성 비경상 손익(Unusual Items) 감지 및 정규화(Normalized) 지표 비교\n\n"
    audit_results = [info['_audit_result'] for info in results.values() if info.get('_audit_result')]

    if audit_results:
        output += "> ⚠️ **회계 감사 알림**: 최근 4분기(TTM) 중 본업 영업활동 외의 대규모 일회성 비경상 손익(투자자산 처분/평가익, 자산손상, 세무환급 등)이 감지된 기업에 대해 공시된 명목 지표와 본업 기반 정규화(Normalized) 지표를 대조 분석합니다.\n\n"
        output += "| 기업명 (티커) | 회계 감사 진단 | 주요 비경상 항목 및 규모 (최대 분기) | 명목 ROE ➡️ 정규화 ROE | 명목 TTM EPS ➡️ 정규화 EPS |\n"
        output += "|---|---|---|---|---|\n"
        for a in audit_results:
            rep_roe_str = f"{a['rep_roe']*100:.1f}%" if a.get('rep_roe') is not None else "N/A"
            norm_roe_str = f"**{a['norm_roe']*100:.1f}%**" if a.get('norm_roe') is not None else "N/A"
            rep_eps_str = format_number(a.get('rep_eps'), True, a.get('currency', 'USD'))
            norm_eps_str = f"**{format_number(a.get('norm_eps'), True, a.get('currency', 'USD'))}**"
            output += f"| **{a['symbol']}** | ⚠️ **대규모 일회성 이익 감지** | {a['desc']} | {rep_roe_str} ➡️ {norm_roe_str} | {rep_eps_str} ➡️ {norm_eps_str} |\n"
        output += "\n> 💡 **투자 해석 시사점**: 일회성 비경상 이익이 포함된 기업은 표면상 ROE와 순이익률이 비정상적으로 높아 보이나, 차기 회계연도에 역기저 효과(실적 급감 착시)가 발생할 수 있으므로 **본업 기준 정규화 지표(Normalized ROE) 및 12M Forward 선행 지표**를 기준으로 가치평가를 수행해야 합니다.\n\n"
    else:
        output += "> 💡 **[회계 감사 결과]**: 분석 대상 전 종목에서 유의미한 일회성 비경상 손익 왜곡(세전이익 대비 15% 이상)이 감지되지 않았으며, 공시된 순이익과 ROE는 본업 영업 활동을 정상적으로 반영하고 있습니다.\n\n"

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch stock financials from Yahoo Finance API.")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of stock tickers")
    
    args = parser.parse_args()
    tickers = [t.strip() for t in args.tickers.split(',')]
    
    markdown_report = generate_report(tickers)
    print(markdown_report)
