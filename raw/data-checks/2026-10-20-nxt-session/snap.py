"""Evidence snapshot across KRX/NXT close: collect.collect_flows + always-on Daum quote + Yahoo info subset."""
import json, sys, os
sys.path.insert(0, sys.argv[1])
import requests, yfinance as yf
import collect
out_dir = sys.argv[2]
syms = sys.argv[3:] or ['000660.KS', '005930.KS']
res = {'snapshot_at': collect.stamp(), 'tickers': {}}
YKEYS = ['regularMarketPrice', 'regularMarketTime', 'marketState', 'regularMarketPreviousClose', 'exchange',
         'fullExchangeName', 'exchangeTimezoneName', 'postMarketPrice', 'preMarketPrice', 'currentPrice', 'regularMarketVolume', 'volume']
for sym in syms:
    code = sym.split('.')[0]
    t = {}
    t['collect_flows'] = collect.collect_flows(sym)
    try:
        dq = requests.get(f'https://finance.daum.net/api/quotes/A{code}', headers=collect.DAUM_HEADERS, timeout=5).json()
        t['daum_quote_always'] = collect.ok('daum', 'json', dq)
    except Exception as e:
        t['daum_quote_always'] = collect.failed('daum', e)
    try:
        dd = requests.get(f'https://finance.daum.net/api/investor/days?page=1&perPage=5&symbolCode=A{code}', headers=collect.DAUM_HEADERS, timeout=5).json()
        t['daum_investor_days_always'] = collect.ok('daum', 'json', dd)
    except Exception as e:
        t['daum_investor_days_always'] = collect.failed('daum', e)
    try:
        t['daum_days_top5'] = collect.ok('daum', 'json', collect.daum_day_rows(code, per_page=5))
    except Exception as e:
        t['daum_days_top5'] = collect.failed('daum', e)
    try:
        info = dict(yf.Ticker(sym).info)
        t['yahoo_info_subset'] = collect.ok('yahoo', 'json', {k: info.get(k) for k in YKEYS})
    except Exception as e:
        t['yahoo_info_subset'] = collect.failed('yahoo', e)
    res['tickers'][sym] = t
fn = os.path.join(out_dir, 'snap-' + res['snapshot_at'].replace(':', '').replace('+0900', '') + '.json')
with open(fn, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(fn)
