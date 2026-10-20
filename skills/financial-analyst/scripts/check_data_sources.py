#!/usr/bin/env python3
"""Periodic cross-source health check; prints a markdown report.

Compares Yahoo with the KRX close (Daum) and Naver for KR stocks, Yahoo with Nasdaq.com for US stocks,
checks the WiseReport table layout and Yahoo statement freshness. Save the output under raw/data-checks/
in the skills repository and ingest it into wiki/ (see CLAUDE.md there).

Rule: references/rules/data-quality.md
"""
import argparse
import datetime
import sys

import pandas as pd
import yfinance as yf

import collect
import data_checks as dc

KST = datetime.timezone(datetime.timedelta(hours=9))


def won(v):
    return f"{v:,.0f}"


def kr_section(code, days):
    lines = [f"## 한국 종목 {code} — Yahoo · 거래소(다음 금융) · 네이버(차트)\n"]
    krx = collect.fetch_daum_days(code, per_page=100, pages=3).iloc[-days:]
    naver = collect.fetch_naver_fchart(code, count=days + 30)
    ya = yf.Ticker(f"{code}.KS").history(start=krx.index[0].strftime('%Y-%m-%d'),
                                          end=(krx.index[-1] + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), auto_adjust=False)
    start, end = krx.index[0], krx.index[-1]
    naver = naver[(naver.index >= start) & (naver.index <= end)]
    lines.append(f"- 비교 기간: {start:%Y-%m-%d} ~ {end:%Y-%m-%d}, 거래소 기준 거래일 {len(krx)}일")

    missing = dc.missing_closes(ya['Close'], krx['Close'])
    lines.append(f"- Yahoo 누락·빈 거래일: {len(missing)}일" + (f" ({', '.join(f'{d:%Y-%m-%d}' for d in missing)})" if missing else ""))

    ym = dc.close_mismatches(ya['Close'], krx['Close'])
    lines.append(f"- Yahoo 종가 ≠ 거래소 종가: {len(ym)}일")
    nm = dc.close_mismatches(naver['Close'], krx['Close'])
    lines.append(f"- 네이버 종가 ≠ 거래소 종가: {len(nm)}일" + (f" (첫 날 {min(d for d, _, _ in nm):%Y-%m-%d}, 마지막 날 {max(d for d, _, _ in nm):%Y-%m-%d})" if nm else ""))
    if ym:
        lines += ["\n| 날짜 | Yahoo 종가 | 거래소 종가 |", "|---|---|---|"]
        lines += [f"| {d:%Y-%m-%d} | {won(y)} | {won(r)} |" for d, y, r in ym]
    if nm:
        lines += ["\n| 날짜 | 네이버 종가 | 거래소 종가 | 차이 |", "|---|---|---|---|"]
        lines += [f"| {d:%Y-%m-%d} | {won(n)} | {won(r)} | {n - r:+,.0f} |" for d, n, r in sorted(nm)]

    vo = dc.volume_outliers(ya['Volume'].dropna())
    lines.append(f"\n- Yahoo 거래량 이상치(직전 20일 중앙값의 1% 미만): {len(vo)}일")
    if vo:
        lines += ["\n| 날짜 | Yahoo 거래량 | 직전 20일 중앙값 | 거래소 거래량 | 네이버 거래량 |", "|---|---|---|---|---|"]
        lines += [f"| {d:%Y-%m-%d} | {won(v)} | {won(m)} | {won(krx.at[d, 'Volume']) if d in krx.index else 'N/A'} | "
                  f"{won(naver.at[d, 'Volume']) if d in naver.index else 'N/A'} |" for d, v, m in vo]

    yv = pd.Series(ya['Volume'].values, index=dc.naive_dates(ya.index)).dropna()
    yv = yv[yv > 0]
    common = krx.index.intersection(yv.index)
    same_y = int(sum(1 for d in common if yv[d] == krx.at[d, 'Volume']))
    nv_common = krx.index.intersection(naver.index)
    same_n = int(sum(1 for d in nv_common if naver.at[d, 'Volume'] == krx.at[d, 'Volume']))
    yn_common = yv.index.intersection(naver.index)
    same_yn = int(sum(1 for d in yn_common if yv[d] == naver.at[d, 'Volume']))
    lines.append("")
    lines.append(f"- 거래량이 거래소(다음)와 같은 날: Yahoo {same_y}/{len(common)}일, 네이버 {same_n}/{len(nv_common)}일")
    lines.append(f"- 거래량이 Yahoo와 네이버 사이에 같은 날: {same_yn}/{len(yn_common)}일")
    return "\n".join(lines) + "\n"


def us_section(symbol, days):
    lines = [f"## 미국 종목 {symbol} — Yahoo · Nasdaq.com\n"]
    end = datetime.date.today()
    start = end - datetime.timedelta(days=int(days * 1.5))
    nq = collect.fetch_nasdaq_history(symbol, start.isoformat(), end.isoformat())
    nq = nq.iloc[-days:]
    ya = yf.Ticker(symbol).history(start=nq.index[0].strftime('%Y-%m-%d'),
                                   end=(nq.index[-1] + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), auto_adjust=False)
    lines.append(f"- 비교 기간: {nq.index[0]:%Y-%m-%d} ~ {nq.index[-1]:%Y-%m-%d}, Nasdaq 기준 거래일 {len(nq)}일")
    missing = dc.missing_closes(ya['Close'], nq['Close'])
    lines.append(f"- Yahoo 누락·빈 거래일: {len(missing)}일")
    mm = dc.close_mismatches(ya['Close'], nq['Close'], tol=0.011)
    lines.append(f"- Yahoo 종가 ≠ Nasdaq 종가(1센트 초과): {len(mm)}일")
    yv = pd.Series(ya['Volume'].values, index=dc.naive_dates(ya.index))
    common = nq.index.intersection(yv.index)
    big = [d for d in common if nq.at[d, 'Volume'] and abs(yv[d] / nq.at[d, 'Volume'] - 1) > 0.05]
    lines.append(f"- 거래량 차이 5% 초과: {len(big)}일 / {len(common)}일")
    return "\n".join(lines) + "\n"


def statements_section(symbols):
    lines = ["## Yahoo 재무제표 반영 시점\n",
             "| 티커 | 연간 표 최신 | 최근 회계연도 말(lastFiscalYearEnd) | 분기 표 최신 | 최근 분기 말(mostRecentQuarter) | 판정 |",
             "|---|---|---|---|---|---|"]
    for sym in symbols:
        t = yf.Ticker(sym)
        info = t.info
        a = max(t.income_stmt.columns) if not t.income_stmt.empty else None
        q = max(t.quarterly_income_stmt.columns) if not t.quarterly_income_stmt.empty else None

        def d(epoch):
            v = dc._num(epoch)
            return datetime.datetime.fromtimestamp(v, tz=datetime.timezone.utc).date() if v else None
        lag_a = dc.statement_lag(a, info.get('lastFiscalYearEnd'))
        lag_q = dc.statement_lag(q, info.get('mostRecentQuarter'))
        verdict = '지연' if (lag_a or lag_q) else '정상'
        lines.append(f"| {sym} | {pd.Timestamp(a):%Y-%m-%d} | {d(info.get('lastFiscalYearEnd'))} | "
                     f"{pd.Timestamp(q):%Y-%m-%d} | {d(info.get('mostRecentQuarter'))} | {verdict} |")
    return "\n".join(lines) + "\n"


def wisereport_section(codes):
    import requests
    from bs4 import BeautifulSoup
    lines = ["## WiseReport 표 구조\n"]
    for code in codes:
        res = requests.get("https://navercomp.wisereport.co.kr/v2/company/cF1002.aspx",
                           params={'cmp_cd': code, 'finGubun': 'MAIN'}, headers={'User-Agent': dc.BROWSER_UA}, timeout=8)
        soup = BeautifulSoup(res.text, 'html.parser')
        head = [th.get_text(strip=True) for th in soup.select('table thead th')]
        try:
            dc.validate_wisereport_header(head)
            for tr in soup.select('table tbody tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all('td')]
                if len(cells) >= 6:
                    dc.check_wisereport_row(cells)
            lines.append(f"- {code}: 정상 (머리글 {head[:6]})")
        except ValueError as e:
            lines.append(f"- {code}: 이상 — {e}")
    return "\n".join(lines) + "\n"


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('--krx', default='005930,000660', help='KRX codes (6 digits), comma-separated')
    p.add_argument('--us', default='MU', help='US tickers, comma-separated')
    p.add_argument('--days', type=int, default=244, help='trading days to compare')
    a = p.parse_args()
    krx = [x.strip() for x in a.krx.split(',') if x.strip()]
    us = [x.strip() for x in a.us.split(',') if x.strip()]

    now = datetime.datetime.now(KST)
    out = [f"# 데이터 출처 교차 점검 — {now:%Y-%m-%d %H:%M} KST\n",
           f"> 생성: skills/financial-analyst/scripts/check_data_sources.py --krx {a.krx} --us {a.us} --days {a.days}\n"
           "> 기준: 한국 종목은 다음 금융 일별 시세를 거래소 종가로, 미국 종목은 Nasdaq.com을 기준으로 봅니다.\n"]
    for code in krx:
        out.append(kr_section(code, a.days))
    for sym in us:
        out.append(us_section(sym, a.days))
    out.append(statements_section([f"{c}.KS" for c in krx] + us))
    if krx:
        out.append(wisereport_section(krx))
    print("\n".join(out))


if __name__ == '__main__':
    main()
