#!/usr/bin/env python3
"""Replay a format-2 snapshot through the pre-split code and compare its Section 4 with the new pipeline's
(spec 003 research R12, quickstart 6). Local, manual tool — not collected by pytest.

The pre-split get_financial_stats.py fetches everything itself and reads the clock. Here its yfinance and
requests calls return the snapshot's stored responses and its clock is frozen at the collection time, so both
codes see exactly the same inputs: every differing line is caused by code, not by the market moving.

    python tests/tools/replay_main.py --main /path/to/main-worktree --snapshot X_data.json --out /tmp/replay

Writes <out>/main.md (pre-split code), <out>/new.md (this branch) and <out>/replay_data.json (the snapshot with
every fetch time set to the collection time, since the old code reads one clock), then prints the diff.
"""
import argparse
import copy
import datetime as real_datetime
import difflib
import html
import json
import os
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
NEW_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "skills", "financial-analyst", "scripts")
HEADER = "## 📊 정량 데이터 분석 결과 (스크립트 자동 산출)"


def body(text):
    text = text.strip()
    return text[len(HEADER):].strip() if text.startswith(HEADER) else text


def uniform_time(snap):
    """One clock for every fetch: the old code reads the clock several times, the new one per raw input."""
    snap = copy.deepcopy(snap)
    t = snap["meta"]["collected_at"]
    for items in snap["inputs"].values():
        for item in items.values():
            item["fetched_at"] = t
    snap.pop("section4", None)
    return snap


# ---------------------------------------------------------------- worker: runs inside the old code's folder

def old_worker(main_scripts, snap_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("raw_inputs_new", os.path.join(NEW_SCRIPTS, "raw_inputs.py"))
    ri = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ri)          # only the frame decoder of this branch
    sys.path.insert(0, main_scripts)     # every other module comes from the pre-split code
    import pandas as pd
    import requests
    import get_financial_stats as old

    snap = json.load(open(snap_path, encoding="utf-8"))
    inputs, meta = snap["inputs"], snap["meta"]

    def item(sym, name):
        it = inputs.get(sym, {}).get(name)
        if it is None:
            raise AssertionError(f"replay: no stored input {sym}.{name}")
        if it["status"] == "error":
            raise Exception(it["error"])
        if it["status"] == "skipped":
            raise AssertionError(f"replay: the old code asked for {sym}.{name}, which collection skipped")
        return it

    def frame(sym, name):
        it = item(sym, name)
        return pd.DataFrame() if it["status"] == "empty" else ri.decode_frame(it["data"])

    class FakeTicker:
        def __init__(self, sym):
            self.sym = sym
            self._quote = None

        @property
        def info(self):
            it = item(self.sym, "info")
            if it.get("note"):  # collect.py fell back to the base quote after this error
                self._quote = types.SimpleNamespace(_info=copy.deepcopy(it["data"]))
                raise Exception(it["note"])
            return copy.deepcopy(it["data"])

        def history(self, period=None, auto_adjust=None):
            return frame(self.sym, "history")

    for name in ("income_stmt", "quarterly_income_stmt", "balance_sheet", "quarterly_balance_sheet",
                 "earnings_estimate", "eps_trend", "eps_revisions", "earnings_history"):
        setattr(FakeTicker, name, property(lambda self, n=name: frame(self.sym, n)))

    class Resp:
        def __init__(self, payload=None, text=None):
            self.payload, self.text = payload, text

        def json(self):
            return copy.deepcopy(self.payload)

        def raise_for_status(self):
            pass

    index_by_market = {"KOSPI": "^KS11", "KOSDAQ": "^KQ11"}

    def sym_of(code):
        return next(s for s in inputs if s.split(".")[0] == code)

    def fake_get(url, params=None, headers=None, timeout=None):
        params = params or {}
        if "m.stock.naver.com/api/stock/" in url:
            code, kind = url.split("/api/stock/")[1].split("/")[:2]
            return Resp(item(sym_of(code), "naver_integration" if kind == "integration" else "naver_trend")["data"])
        if "wisereport" in url:
            t = item(sym_of(url.split("cmp_cd=")[1].split("&")[0]), "wisereport_eps")["data"]
            th = "".join(f"<th>{html.escape(h)}</th>" for h in t["headers"])
            trs = "".join("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in r) + "</tr>" for r in t["rows"])
            return Resp(text=f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>")
        if "/api/quote/A" in url and url.endswith("/days"):
            return Resp({"data": item(sym_of(url.split("/api/quote/A")[1].split("/")[0]), "daum_days")["data"]})
        if "/api/market_index/days" in url:
            return Resp({"data": item(index_by_market[params["market"]], "daum_index_days")["data"]})
        if "/api/quotes/A" in url:
            return Resp(item(sym_of(url.split("/api/quotes/A")[1]), "daum_quote")["data"])
        if "/api/investor/days" in url:
            return Resp(item(sym_of(url.split("symbolCode=A")[1]), "daum_investor_days")["data"])
        raise AssertionError(f"replay: unexpected request {url}")

    requests.get = fake_get
    T = real_datetime.datetime.fromisoformat(meta["collected_at"])

    class FrozenDatetime(real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return T.astimezone(tz) if tz else T.replace(tzinfo=None)

        @classmethod
        def today(cls):
            return T.replace(tzinfo=None)

    class FrozenDate(real_datetime.date):
        @classmethod
        def today(cls):
            return T.date()

    shim = types.SimpleNamespace(**{k: getattr(real_datetime, k) for k in dir(real_datetime) if not k.startswith("__")})
    shim.datetime, shim.date = FrozenDatetime, FrozenDate
    old.datetime = shim
    old.yf = types.SimpleNamespace(Ticker=FakeTicker, __version__="replay")

    def split(text):
        return [x.strip() for x in (text or "").split(",") if x.strip()]
    args = meta.get("args") or {}
    out = old.generate_report(split(args.get("tickers")), set(split(args.get("cyclical"))), set(split(args.get("not_cyclical"))),
                              split(args.get("benchmarks")) or None, old.parse_weights(args.get("weights") or "0.2,0.5,0.3"))
    sys.stdout.write(out)


# ---------------------------------------------------------------- driver

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--main", required=True, help="worktree of the pre-split code (e.g. git worktree add /tmp/main main)")
    ap.add_argument("--snapshot", required=True, help="format-2 snapshot")
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--_old-worker", dest="old_worker", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.old_worker:
        old_worker(os.path.join(a.main, "skills", "financial-analyst", "scripts"), a.old_worker)
        return 0

    os.makedirs(a.out, exist_ok=True)
    snap = uniform_time(json.load(open(a.snapshot, encoding="utf-8")))
    replay_path = os.path.join(a.out, "replay_data.json")
    json.dump(snap, open(replay_path, "w", encoding="utf-8"), ensure_ascii=False)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    old = subprocess.run([sys.executable, os.path.abspath(__file__), "--main", a.main, "--snapshot", a.snapshot,
                          "--out", a.out, "--_old-worker", replay_path], capture_output=True, text=True, encoding="utf-8", env=env)
    if old.returncode != 0:
        sys.stderr.write(old.stderr)
        return 2
    new = subprocess.run([sys.executable, os.path.join(NEW_SCRIPTS, "rebuild_section4.py"), replay_path, "--print"],
                         capture_output=True, text=True, encoding="utf-8", env=env)
    old_body, new_body = body(old.stdout), body(new.stdout)
    open(os.path.join(a.out, "main.md"), "w", encoding="utf-8").write(old_body + "\n")
    open(os.path.join(a.out, "new.md"), "w", encoding="utf-8").write(new_body + "\n")
    diff = list(difflib.unified_diff(old_body.splitlines(), new_body.splitlines(), "main", "new", lineterm=""))
    changed = sum(1 for line in diff if line[:1] in "+-" and not line.startswith(("+++", "---")))
    print("\n".join(diff) if diff else "(차이 없음)")
    print(f"\n재생 비교: 분리 전 {len(old_body.splitlines())}줄 · 분리 후 {len(new_body.splitlines())}줄 · 다른 줄 {changed}")
    return 0 if not diff else 1


if __name__ == "__main__":
    sys.exit(main())
