"""
MCP Python Client Bridge
Enables Python data collection scripts to call Node.js MCP servers via stdio JSON-RPC.
Servers supported: krx, dart, toss, ecos, fred, edgar.
"""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

CONFIG_PATH = os.path.expanduser("~/.gemini/config/mcp_config.json")


def _load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("mcpServers", {})
        except Exception:
            pass
    return {}


MCP_CONFIG = _load_config()


def call_mcp(
    server: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Optional[Dict[str, Any]]:
    """
    Execute a tool call against an MCP server via stdio JSON-RPC.
    Returns the parsed JSON data dict from content[0].text, or raw result dict.
    """
    global MCP_CONFIG
    if server not in MCP_CONFIG:
        # Reload config in case it was updated
        MCP_CONFIG = _load_config()
        if server not in MCP_CONFIG:
            raise ValueError(f"MCP server '{server}' not configured in {CONFIG_PATH}")

    sc = MCP_CONFIG[server]
    cmd = [sc.get("command", "node")] + sc.get("args", [])
    env = {**os.environ, **sc.get("env", {})}

    try:
        p = subprocess.Popen(
            cmd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to spawn MCP server '{server}': {e}")

    try:
        # 1. Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-mcp-client", "version": "1.0"},
            },
        }
        p.stdin.write(json.dumps(init_req) + "\n")

        # 2. Call Tool
        call_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments or {}},
        }
        p.stdin.write(json.dumps(call_req) + "\n")
        p.stdin.flush()

        # 3. Read stdout line by line until id==1 or timeout
        start_time = time.time()
        res = None

        while True:
            if time.time() - start_time > timeout:
                p.kill()
                raise TimeoutError(f"MCP call {server}.{tool} timed out after {timeout}s")

            # Check if process died
            if p.poll() is not None:
                break

            line = p.stdout.readline()
            if not line:
                time.sleep(0.01)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                msg = json.loads(line)
                if msg.get("id") == 1:
                    if "error" in msg:
                        raise RuntimeError(f"MCP error from {server}.{tool}: {msg['error']}")
                    res = msg.get("result")
                    break
            except json.JSONDecodeError:
                pass

        p.terminate()
        try:
            p.wait(timeout=1)
        except subprocess.TimeoutExpired:
            p.kill()

        if not res:
            return None

        # Parse text content if present
        if "content" in res and isinstance(res["content"], list) and len(res["content"]) > 0:
            txt = res["content"][0].get("text")
            if txt:
                try:
                    return json.loads(txt)
                except json.JSONDecodeError:
                    return {"text": txt}

        return res

    except Exception:
        try:
            p.kill()
        except Exception:
            pass
        raise


# --- Domain Helper APIs ---

def get_ecos_market_rates() -> Optional[Dict[str, Any]]:
    """Fetch Bank of Korea market interest rates (817Y002)."""
    return call_mcp("ecos", "ecos_market_rates", {})


def get_toss_exchange_rate(base: str = "USD", quote: str = "KRW") -> Optional[Dict[str, Any]]:
    """Fetch Toss real-time exchange rate (e.g. USD/KRW)."""
    return call_mcp("toss", "toss_exchange_rate", {"base": base, "quote": quote})


def get_live_usd_krw_rate() -> float:
    """Fetch live USD/KRW rate: 1st Toss MCP, 2nd Yahoo USDKRW=X, 3rd Fallback 1335.0."""
    try:
        t_res = get_toss_exchange_rate("USD", "KRW")
        if t_res and "rate" in t_res:
            return float(t_res["rate"])
    except Exception:
        pass

    try:
        import yfinance as yf
        tk = yf.Ticker("USDKRW=X")
        p = tk.fast_info.get("last_price") or tk.info.get("regularMarketPrice")
        if p and float(p) > 500:
            return float(p)
    except Exception:
        pass

    return 1335.0


def get_toss_market_flows(market: str = "KOSPI") -> Optional[Dict[str, Any]]:
    """Fetch Toss market investor trading flows (updatedAt 20:06:03 finalized)."""
    return call_mcp("toss", "toss_market_investor_trading", {"market": market})


def get_toss_stock_flows(symbol: str) -> Optional[Dict[str, Any]]:
    """Fetch Toss individual stock investor trading flows (7 institutional sub-entities)."""
    clean_sym = symbol.split(".")[0]
    return call_mcp("toss", "toss_stock_investor_trading", {"symbol": clean_sym})


def get_krx_stock_summary(market_type: str = "kospi") -> Optional[Dict[str, Any]]:
    """Fetch KRX daily market summary (상승/하락/보합, 거래대금, 시총)."""
    return call_mcp("krx", "krx_stock", {"type": market_type, "limit": 1})


def get_krx_ticker_info(symbol: str, market_type: str = "kospi") -> Optional[Dict[str, Any]]:
    """Fetch KRX specific stock quote, market cap, and shares."""
    clean_sym = symbol.split(".")[0]
    res = call_mcp("krx", "krx_stock", {"type": market_type, "code": clean_sym})
    if res and "rows" in res and len(res["rows"]) > 0:
        return res["rows"][0]
    return None


def get_fred_bundle(bundle_name: str) -> Optional[Dict[str, Any]]:
    """Fetch FRED macro bundle: 'rates', 'credit', or 'liquidity'."""
    return call_mcp("fred", "fred_bundle", {"bundle": bundle_name}, timeout=15)


def get_edgar_financials(ticker: str, period: str = "annual", limit: int = 10) -> Optional[Dict[str, Any]]:
    """Fetch SEC EDGAR 10-K/10-Q audited financials (10+ years, Q4 derived)."""
    clean_ticker = ticker.split(".")[0].upper()
    return call_mcp("edgar", "sec_financials", {"company": clean_ticker, "period": period, "limit": limit})


def get_edgar_shares_outstanding(ticker: str) -> Optional[Dict[str, Any]]:
    """Fetch SEC EDGAR exact shares outstanding via DEI concept."""
    clean_ticker = ticker.split(".")[0].upper()
    return call_mcp(
        "edgar",
        "sec_concept",
        {"company": clean_ticker, "taxonomy": "dei", "tag": "EntityCommonStockSharesOutstanding"},
    )


def get_dart_corp_code(corp_name_or_stock_code: str) -> Optional[str]:
    """Find DART 8-digit corp_code by stock code or company name."""
    clean_code = corp_name_or_stock_code.split(".")[0]
    res = call_mcp("dart", "dart_find_corp", {"query": clean_code})
    if res and "corps" in res and len(res["corps"]) > 0:
        return res["corps"][0].get("corp_code")
    return None


def get_dart_financials(corp_code: str, year: int = None, reprt_code: str = "11011") -> Optional[Dict[str, Any]]:
    """Fetch DART 10-year K-IFRS financial statements."""
    args = {"corp_code": corp_code, "reprt_code": reprt_code}
    if year:
        args["bsns_year"] = str(year)
    return call_mcp("dart", "dart_financials", args)
