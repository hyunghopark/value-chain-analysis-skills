"""
Tests for rebuilding Section 4 from a snapshot alone (spec 003).
Covers SC-001·002·003·005·006, FR-001(a)·003·004·006·007·008·010·011·013, research R8·R11.
"""

import ast
import os
import sys

import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


# --- SC-002 / FR-001 (a): only collect.py reaches the network or reads the clock (research R11) ---

PURE_MODULES = ["get_financial_stats.py", "raw_inputs.py", "data_checks.py", "snapshot.py", "rebuild_section4.py"]
NETWORK_MODULES = {"requests", "yfinance", "bs4", "pykrx", "urllib", "socket", "http"}
# (file, function) allowed to read the clock, with the reason
CLOCK_ALLOWED = {
    ("snapshot.py", "attach_section4"): "records when the baseline was attached; never part of Section 4 text",
}


def _is_main_guard(node):
    return (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__")


def _clock_call(node):
    """datetime.now(), datetime.today(), date.today(), datetime.datetime.now(), time.time() ..."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    attr, base = node.func.attr, node.func.value
    names = []
    while isinstance(base, ast.Attribute):
        names.append(base.attr)
        base = base.value
    if isinstance(base, ast.Name):
        names.append(base.id)
    if attr in ("now", "today", "utcnow") and {"datetime", "date"} & set(names):
        return ".".join(reversed(names)) + "." + attr
    if attr == "time" and names == ["time"]:
        return "time.time"
    return None


def _violations(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    fname = os.path.basename(path)
    found = []

    def visit(node, func):
        if _is_main_guard(node):
            return  # the command entry point may collect and read the clock
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = node.name
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in NETWORK_MODULES:
                    found.append(f"{fname}:{node.lineno} {func or '<module>'} import {a.name}")
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in NETWORK_MODULES:
            found.append(f"{fname}:{node.lineno} {func or '<module>'} from {node.module} import")
        call = _clock_call(node)
        if call and (fname, func) not in CLOCK_ALLOWED:
            found.append(f"{fname}:{node.lineno} {func or '<module>'} {call}()")
        for child in ast.iter_child_nodes(node):
            visit(child, func)

    visit(tree, None)
    return found


def test_pure_stages_do_not_fetch_or_read_clock():
    checked, problems = [], []
    for name in PURE_MODULES:
        path = os.path.join(SCRIPTS_DIR, name)
        if not os.path.exists(path):
            continue  # rebuild_section4.py arrives with T016; its existence is tested with the rebuild tests
        checked.append(name)
        problems += _violations(path)
    assert "get_financial_stats.py" in checked and "data_checks.py" in checked
    assert not problems, "정제·계산·출력 코드에서 외부 접속·현재 시각 읽기 발견:\n" + "\n".join(problems)


def test_clock_detector_catches_known_forms():
    src = ("import datetime, time\nfrom datetime import date\n"
           "def f():\n    a = datetime.datetime.now()\n    b = date.today()\n    c = time.time()\n"
           "    d = datetime.datetime.fromtimestamp(1)\n")
    calls = [c for n in ast.walk(ast.parse(src)) if (c := _clock_call(n))]
    assert calls == ["datetime.datetime.now", "date.today", "time.time"]
