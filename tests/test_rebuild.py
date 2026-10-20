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


# --- Rebuild from the committed fixture (SC-001·003·006, FR-005·006·007·008·010·013) ---

import copy  # noqa: E402
import datetime as _real_datetime  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import socket  # noqa: E402
import time  # noqa: E402
import types  # noqa: E402

FX = os.path.join(CURRENT_DIR, "fixtures", "003", "snapshot_data.json")
LEGACY = os.path.join(CURRENT_DIR, "fixtures", "002", "report_data.json")
PINNED = os.path.join(CURRENT_DIR, "requirements-pinned.txt")


def _rb():
    import rebuild_section4
    return rebuild_section4


def _load_fx():
    with open(FX, encoding="utf-8") as f:
        return json.load(f)


def _write(tmp_path, snap, name="s_data.json"):
    path = tmp_path / name
    path.write_text(json.dumps(snap, ensure_ascii=False), encoding="utf-8")
    return str(path)


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def test_fixture_rebuilds_identically():
    before = _sha(FX)
    t0 = time.perf_counter()
    result, body = _rb().verify(FX)
    elapsed = time.perf_counter() - t0
    assert result["exit_code"] == 0, _rb().render_summary(result, verbose=True)
    assert result["section4"]["compared"] and result["section4"]["same"]
    assert result["values"]["same"] and result["values"]["count"] > 500
    assert result["warnings"]["same"] and result["warnings"]["count"] > 0
    assert elapsed < 10, elapsed                      # SC-006
    assert _sha(FX) == before                         # FR-010: read only
    assert "장중 잠정" in body                         # a provisional flow row is rebuilt as provisional


def test_rebuild_with_network_and_clock_blocked(monkeypatch):
    """SC-002: the rebuild works with sockets refused and every clock call raising."""
    import data_checks
    import get_financial_stats as gfs

    def no_network(*args, **kwargs):
        raise AssertionError("network access during rebuild")
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)

    class NoClockDatetime(_real_datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            raise AssertionError("clock read during rebuild")

        @classmethod
        def today(cls):
            raise AssertionError("clock read during rebuild")

        utcnow = today

    class NoClockDate(_real_datetime.date):
        @classmethod
        def today(cls):
            raise AssertionError("clock read during rebuild")

    shim = types.SimpleNamespace(**{k: getattr(_real_datetime, k) for k in dir(_real_datetime) if not k.startswith("__")})
    shim.datetime, shim.date = NoClockDatetime, NoClockDate
    monkeypatch.setattr(gfs, "datetime", shim)
    monkeypatch.setattr(data_checks, "datetime", shim)
    monkeypatch.setattr(time, "time", no_network)
    result, _ = _rb().verify(FX)
    assert result["exit_code"] == 0, _rb().render_summary(result, verbose=True)


def test_tampered_value_is_reported(tmp_path):
    snap = _load_fx()
    path_key = next(k for k, v in snap["values"].items() if k.endswith(".metrics.forward_pe") and isinstance(v["value"], float))
    stored = snap["values"][path_key]["value"]
    snap["values"][path_key]["value"] = stored + 1
    result, _ = _rb().verify(_write(tmp_path, snap))
    assert result["exit_code"] == 1
    changed = {c["path"]: c for c in result["values"]["changed"]}
    assert changed[path_key]["stored"] == stored + 1 and changed[path_key]["rebuilt"] == stored
    assert path_key in _rb().render_summary(result)


def test_missing_raw_input_names_path(tmp_path):
    snap = _load_fx()
    del snap["inputs"]["MU"]["quarterly_balance_sheet"]
    result, body = _rb().verify(_write(tmp_path, snap))
    assert result["exit_code"] == 2 and body is None
    err = result["errors"][0]
    assert err["code"] == "missing_input" and err["detail"] == "inputs.MU.quarterly_balance_sheet"
    assert "inputs.MU.quarterly_balance_sheet" in _rb().render_summary(result)


def test_legacy_snapshot_is_refused():
    result, _ = _rb().verify(LEGACY)
    assert result["exit_code"] == 2 and result["errors"][0]["code"] == "legacy_format"
    assert "이전 형식" in _rb().render_summary(result)


def test_recorded_failure_rebuilds_same_warning():
    """US1 scenario 5 / FR-007: a source that failed at collection gives the same warning and empty table again."""
    import get_financial_stats as gfs
    import raw_inputs as ri
    snap = _load_fx()
    snap["inputs"]["000660.KS"]["naver_trend"] = {"source": "naver", "fetched_at": "2026-10-20T19:02:29+09:00",
                                                  "status": "error", "kind": None, "data": None, "error": "timeout", "note": None}
    snap.pop("section4")
    gfs.ECHO_WARNINGS = False
    direct = gfs.build_section4(copy.deepcopy(snap))
    warns = list(gfs.WARNINGS)
    round_trip = gfs.build_section4(ri.loads(ri.dumps(snap["meta"], snap["inputs"])))
    assert direct == round_trip and warns == gfs.WARNINGS
    assert any(w.endswith("(000660): 네이버 수급 API 오류 (timeout)") for w in warns)
    assert "(000660) 최근 5거래일 투자자별 순매매 추정" not in direct
    assert "(005930) 최근 5거래일 투자자별 순매매 추정" in direct


def test_version_difference_is_warned_not_failed(tmp_path):
    snap = _load_fx()
    snap["meta"]["versions"]["pandas"] = "0.0.0"
    result, _ = _rb().verify(_write(tmp_path, snap))
    assert any(w.startswith("pandas 0.0.0 →") for w in result["version_warnings"])
    assert result["exit_code"] == 0
    assert "pandas 0.0.0" in _rb().render_summary(result)


def test_pinned_versions_match_fixture():
    pins = dict(line.strip().split("==") for line in open(PINNED, encoding="utf-8") if "==" in line and not line.startswith("#"))
    versions = _load_fx()["meta"]["versions"]
    for pkg in ("pandas", "numpy"):
        assert pins.get(pkg) == versions[pkg], f"{pkg}: 버전을 올렸다면 시험 스냅샷을 다시 만드세요 (tests/fixtures/003/README.md)"


def test_cli_exit_codes(tmp_path, capsys):
    rb = _rb()
    assert rb.main([FX]) == 0
    assert "결과: 같음" in capsys.readouterr().out
    out_json = tmp_path / "r.json"
    assert rb.main([LEGACY, "--json", str(out_json)]) == 2
    assert json.loads(out_json.read_text(encoding="utf-8"))["errors"][0]["code"] == "legacy_format"
    assert rb.main([str(tmp_path / "missing_data.json")]) == 2


# --- US2: the same snapshot shows exactly what a code change did (SC-005, US2 scenarios 1–3) ---

def test_same_code_twice_is_identical():
    import get_financial_stats as gfs
    gfs.ECHO_WARNINGS = False
    snap = _load_fx()
    first = gfs.build_section4(copy.deepcopy(snap))
    first_values = json.dumps(gfs.SNAP.values, sort_keys=True)
    assert gfs.build_section4(copy.deepcopy(snap)) == first
    assert json.dumps(gfs.SNAP.values, sort_keys=True) == first_values


def test_threshold_change_stays_in_its_scope(monkeypatch):
    """Changing the Forward P/E thresholds may only change general-company matrix rows, the criteria notes and rules.forward_pe.*."""
    import get_financial_stats as gfs
    monkeypatch.setitem(gfs.THRESHOLDS, "fpe", (10, 15))
    result, _ = _rb().verify(FX)
    diff = result["section4"]["diff"]
    assert diff, "the change must show up (TSM, a general company, is judged on Forward P/E)"

    def allowed_line(line):
        if line is None:
            return True
        matrix_row = line.startswith("| **") and "| 일반 |" in line          # tables 4 and 5, general companies
        criteria = "Forward PE(<" in line                                   # notes under tables 4 and 5
        return matrix_row or criteria
    outside = [d for d in diff if not (allowed_line(d["baseline"]) and allowed_line(d["rebuilt"]))]
    assert not outside, outside
    v = result["values"]
    assert not v["added"] and not v["removed"]
    assert v["changed"] and all(c["path"].startswith("rules.forward_pe.") for c in v["changed"]), v["changed"]
    assert result["section4"]["cause"] == "values"


def test_text_only_change_is_told_apart(monkeypatch):
    """US2 scenario 3: a formatting change alters Section 4 text while every computed value stays the same."""
    import get_financial_stats as gfs
    monkeypatch.setattr(gfs, "fmt_signed_pct", lambda val, digits=1: f"{val * 100:+.{digits + 1}f}%" if isinstance(val, (int, float)) else "N/A")
    result, _ = _rb().verify(FX)
    assert result["exit_code"] == 1
    assert result["values"]["same"] and result["warnings"]["same"]
    assert result["section4"]["cause"] == "text_only"
    assert "글자만 다름" in _rb().render_summary(result)


# --- US3: recompute with other assumptions, without collecting (Clarifications Q1) ---

def test_recompute_weights_changes_only_the_scenario(tmp_path):
    rb = _rb()
    before = _sha(FX)
    out = tmp_path / "w.md"
    out_json = tmp_path / "w.json"
    assert rb.main([FX, "--weights", "0.1,0.5,0.4", "--out", str(out), "--json", str(out_json)]) == 0
    text = out.read_text(encoding="utf-8")
    head, rest = text.split("\n", 2)[:2], text.split("\n", 2)[2]
    assert head[0].startswith("> 🔁 **재계산 결과 — 보고서가 아닙니다.**") and "sha256 " + before[:8] in head[0]
    assert "weights 0.2,0.5,0.3 → 0.1,0.5,0.4" in head[1] and "데이터는 다시 받지 않았습니다" in head[1]
    baseline = _load_fx()["section4"]["text"]
    diff = rb.compare_lines(baseline, rest.strip())
    assert diff
    for d in diff:
        for line in (d["baseline"], d["rebuilt"]):
            assert line is None or "**확률 가중**" in line or line.startswith("|  | **확률가중 기대값**"), line
    r = json.loads(out_json.read_text(encoding="utf-8"))
    assert r["mode"] == "recompute" and r["options_changed"] == {"weights": ["0.2,0.5,0.3", "0.1,0.5,0.4"]}
    paths = [c["path"] for c in r["values"]["changed"]]
    assert paths and all(p.startswith("rules.scenario.weight_") or ".scenario.expected_price_" in p
                         or ".scenario.return_expected_" in p for p in paths), paths
    assert _sha(FX) == before


def test_recompute_cyclical_unknown_ticker_needs_data(tmp_path):
    rb = _rb()
    out_json = tmp_path / "c.json"
    assert rb.main([FX, "--cyclical", "000990.KS", "--out", str(tmp_path / "c.md"), "--json", str(out_json)]) == 2
    err = json.loads(out_json.read_text(encoding="utf-8"))["errors"][0]
    assert err["code"] == "option_needs_data" and "000990.KS" in err["detail"]
    assert not (tmp_path / "c.md").exists()


def test_recompute_rejects_other_options_and_existing_output(tmp_path):
    rb = _rb()
    before = _sha(FX)
    out_json = tmp_path / "r.json"
    assert rb.main([FX, "--tickers", "MU", "--out", str(tmp_path / "t.md"), "--json", str(out_json)]) == 2
    assert json.loads(out_json.read_text(encoding="utf-8"))["errors"][0]["code"] == "option_rejected"
    existing = tmp_path / "exists.md"
    existing.write_text("keep", encoding="utf-8")
    assert rb.main([FX, "--weights", "0.1,0.5,0.4", "--out", str(existing), "--json", str(out_json)]) == 2
    assert json.loads(out_json.read_text(encoding="utf-8"))["errors"][0]["code"] == "output_exists"
    assert existing.read_text(encoding="utf-8") == "keep"
    with pytest.raises(SystemExit) as e:
        rb.main([FX, "--weights", "0.1,0.5,0.4"])          # recompute needs --out
    assert e.value.code == 2
    assert _sha(FX) == before


# --- Floating-point differences between CPU architectures (CI x86_64 vs local arm64, research R8) ---

def test_compare_values_tolerates_last_bit_differences():
    rb = _rb()
    stored = {"a": {"value": 888.3901777977313, "basis": "derived"}, "b": {"value": 1.8584003998398702},
              "c": {"value": 1.0}, "d": {"value": "🟢"}, "e": {"value": None}, "f": {"value": 0.0}}
    rebuilt = {"a": {"value": 888.3901777977314, "basis": "derived"}, "b": {"value": 1.8584003998398573},
               "c": {"value": 1.000001}, "d": {"value": "🟡"}, "e": {"value": 0.0}, "f": {"value": 1e-13}}
    v = rb.compare_values(stored, rebuilt)
    assert sorted(c["path"] for c in v["changed"]) == ["c", "d", "e"]
    assert v["within_tolerance"] == ["a", "b", "f"]


def test_rebuild_same_across_architectures(tmp_path):
    """The x86_64 CI recomputes rolling/EWM values that differ from arm64 in the last bits; that is still the same rebuild."""
    snap = _load_fx()
    shaken = ("MU.technical.deviation_lower", "TSM.technical.rsi_14", "005930.KS.technical.bollinger_lower")
    for path in shaken:
        snap["values"][path]["value"] *= 1 + 5e-15
    result, _ = _rb().verify(_write(tmp_path, snap))
    assert result["exit_code"] == 0, _rb().render_summary(result, verbose=True)
    # on x86_64 the fixture's own arm64 values already differ in the last bits for a few more paths
    assert set(shaken) <= set(result["values"]["within_tolerance"])
    assert "허용 오차" in _rb().render_summary(result)
