"""
Collection stage for market data using yfinance.
Collects daily historical bars for indices, sector ETFs, and macro risk indicators.
"""

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import yfinance as yf

import market_raw_inputs as ri

KST = datetime.timezone(datetime.timedelta(hours=9))

DEFAULT_INDICES = ['^GSPC', '^NDX', '^DJI', '^RUT', '^SOX']
DEFAULT_SECTORS = ['XLK', 'XLC', 'XLY', 'XLI', 'XLF', 'XLV', 'XLE', 'XLP', 'XLU', 'XLRE', 'XLB']
BENCHMARK_ETF = 'SPY'
DEFAULT_MACRO = ['^VIX', '^TNX', '^IRX', 'DX-Y.NYB', 'CL=F', 'GC=F', 'HYG', 'LQD', 'USDKRW=X']
SUPPLEMENTARY_GLOBAL = ['^KS11', '^KQ11', '^N225']


def now_kst() -> datetime.datetime:
    return datetime.datetime.now(KST).replace(microsecond=0)


def stamp() -> str:
    return now_kst().isoformat()


def collect_market_data(
    indices: Optional[List[str]] = None,
    sectors: Optional[List[str]] = None,
    macro: Optional[List[str]] = None,
    include_global: bool = False,
    period: str = "3y",
) -> Dict[str, Dict[str, Any]]:
    """
    Download 3-year daily history for all target tickers and return raw input items.
    """
    tickers_to_fetch = list(indices or DEFAULT_INDICES)
    sector_tickers = list(sectors or DEFAULT_SECTORS)
    if BENCHMARK_ETF not in sector_tickers:
        sector_tickers.append(BENCHMARK_ETF)
    tickers_to_fetch.extend(sector_tickers)
    tickers_to_fetch.extend(macro or DEFAULT_MACRO)
    if include_global:
        tickers_to_fetch.extend(SUPPLEMENTARY_GLOBAL)

    seen = set()
    unique_tickers = [t for t in tickers_to_fetch if not (t in seen or seen.add(t))]

    raw_items: Dict[str, Dict[str, Any]] = {}
    fetched_time = stamp()

    try:
        data = yf.download(unique_tickers, period=period, interval="1d", progress=False, group_by="ticker")
    except Exception as e:
        for sym in unique_tickers:
            raw_items[sym] = ri.make_item("yahoo", fetched_time, "error", error=str(e))
        return raw_items

    for sym in unique_tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                if sym in data.columns.levels[0]:
                    df = data[sym].dropna(how="all")
                elif 'Ticker' in data.columns.names and sym in data.columns.get_level_values('Ticker'):
                    df = data.xs(sym, level='Ticker', axis=1).dropna(how="all")
                else:
                    df = pd.DataFrame()
            else:
                df = data.copy()

            if isinstance(df.columns, pd.MultiIndex):
                if 'Price' in df.columns.names:
                    df = df.droplevel([n for n in df.columns.names if n != 'Price'], axis=1)

            if df is not None and not df.empty:
                if "Close" in df.columns:
                    df = df.dropna(subset=["Close"]).copy()
                raw_items[sym] = ri.make_item("yahoo", fetched_time, "ok", kind="frame", data=df)
            else:
                # Retry individual fetch if batch download returned empty
                try:
                    single_df = yf.download(sym, period=period, interval="1d", progress=False)
                    if isinstance(single_df.columns, pd.MultiIndex):
                        if 'Price' in single_df.columns.names:
                            single_df = single_df.droplevel([n for n in single_df.columns.names if n != 'Price'], axis=1)
                        elif sym in single_df.columns.levels[0]:
                            single_df = single_df[sym]
                    if single_df is not None and not single_df.empty and "Close" in single_df.columns:
                        single_df = single_df.dropna(subset=["Close"]).copy()
                        raw_items[sym] = ri.make_item("yahoo", fetched_time, "ok", kind="frame", data=single_df)
                    else:
                        raw_items[sym] = ri.make_item("yahoo", fetched_time, "empty", note="No historical rows returned")
                except Exception:
                    raw_items[sym] = ri.make_item("yahoo", fetched_time, "empty", note="No historical rows returned")
        except Exception as e:
            raw_items[sym] = ri.make_item("yahoo", fetched_time, "error", error=str(e))

    # Official FRED macro bundles (rates & credit OAS spreads)
    try:
        import mcp_client
        rates_bundle = mcp_client.get_fred_bundle('rates')
        if rates_bundle:
            raw_items['FRED_RATES'] = ri.make_item("fred", fetched_time, "ok", kind="json", data=rates_bundle)
        else:
            raw_items['FRED_RATES'] = ri.make_item("fred", fetched_time, "empty", note="No FRED rates bundle returned")
    except Exception as e:
        raw_items['FRED_RATES'] = ri.make_item("fred", fetched_time, "error", error=str(e))

    try:
        import mcp_client
        credit_bundle = mcp_client.get_fred_bundle('credit')
        if credit_bundle:
            raw_items['FRED_CREDIT'] = ri.make_item("fred", fetched_time, "ok", kind="json", data=credit_bundle)
        else:
            raw_items['FRED_CREDIT'] = ri.make_item("fred", fetched_time, "empty", note="No FRED credit bundle returned")
    except Exception as e:
        raw_items['FRED_CREDIT'] = ri.make_item("fred", fetched_time, "error", error=str(e))

    return raw_items
