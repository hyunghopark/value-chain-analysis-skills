#!/usr/bin/env python3
"""Rebuild a report's Section 4 from its format-2 snapshot alone — no network, no clock — and compare it with
what the snapshot recorded: the Section 4 baseline, every computed value and the data-quality warnings.

Recompute mode (--weights / --cyclical / --not-cyclical with --out) builds Section 4 again under other assumptions
from the same data and writes it to a new file marked as not a report; nothing is collected and the snapshot is
never modified (spec 003 US3).

Spec: specs/003-pipeline-split/ (contracts/cli.md §2, data-model §5)
Rules: references/rules/data-snapshot.md §9

Exit codes: 0 all the same (or recomputed and saved) · 1 something differs · 2 cannot rebuild (legacy format,
missing or invalid input, unreadable file, rejected option, output exists).
"""
import argparse
import difflib
import hashlib
import json
import os
import platform
import sys
from importlib import metadata

import get_financial_stats as gfs
import raw_inputs as ri
import snapshot as snapmod

EXIT_SAME, EXIT_DIFF, EXIT_ERROR = 0, 1, 2
SHOW = 20  # differences printed without --verbose
RECOMPUTE_OPTIONS = (('weights', 'weights'), ('cyclical', 'cyclical'), ('not_cyclical', 'not_cyclical'))

LEGACY_MSG = ("이 스냅샷은 원자료가 없는 이전 형식(001·002)이라 다시 만들 수 없습니다. "
              "숫자 점검(check_report_numbers.py)은 그대로 쓸 수 있습니다.")


class OptionError(Exception):
    def __init__(self, code, message, detail=None):
        super().__init__(message)
        self.code, self.detail = code, detail


def current_versions():
    out = {'python': platform.python_version()}
    for pkg in ('yfinance', 'pandas', 'numpy'):
        try:
            out[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def version_warnings(meta):
    recorded, now = meta.get('versions') or {}, current_versions()
    return [f"{k} {recorded[k]} → {now.get(k)}" for k in sorted(recorded) if now.get(k) and recorded[k] != now.get(k)]


def _canon(record):
    """Text form for exact comparison (NaN equals NaN, key order ignored)."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False)


def compare_values(stored, rebuilt):
    changed = [{'path': p, 'stored': stored[p].get('value'), 'rebuilt': rebuilt[p].get('value'),
                'fields': sorted(k for k in set(stored[p]) | set(rebuilt[p]) if _canon(stored[p].get(k)) != _canon(rebuilt[p].get(k)))}
               for p in stored if p in rebuilt and _canon(stored[p]) != _canon(rebuilt[p])]
    added = sorted(p for p in rebuilt if p not in stored)
    removed = sorted(p for p in stored if p not in rebuilt)
    return {'same': not (changed or added or removed), 'count': len(stored), 'changed': changed, 'added': added, 'removed': removed}


def compare_lines(baseline, rebuilt):
    a, b = baseline.splitlines(), rebuilt.splitlines()
    diff = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        for k in range(max(i2 - i1, j2 - j1)):
            diff.append({'line': i1 + k + 1,
                         'baseline': a[i1 + k] if i1 + k < i2 else None,
                         'rebuilt': b[j1 + k] if j1 + k < j2 else None})
    return diff


def rebuild(snapshot, overrides=None):
    """Section 4 body plus the values and warnings the rebuild recorded (JSON-normalized like a saved snapshot)."""
    gfs.ECHO_WARNINGS = False
    text = gfs.build_section4(snapshot, overrides)
    values = json.loads(json.dumps(gfs.SNAP.values, ensure_ascii=False))
    warnings = json.loads(json.dumps(gfs.SNAP.warnings, ensure_ascii=False))
    return snapmod.section4_body(text), values, warnings


def error_result(path, code, message, detail=None, mode='verify'):
    return {'snapshot': path, 'mode': mode, 'errors': [{'code': code, 'message': message, 'detail': detail}],
            'exit_code': EXIT_ERROR}


def load(path, mode, rebuilt_at):
    """(snapshot, result skeleton). Raises what `guarded` maps to exit code 2."""
    with open(path, 'rb') as f:
        raw_bytes = f.read()
    snap = json.loads(raw_bytes.decode('utf-8'))
    ri.check_format(snap)
    meta = snap['meta']
    return snap, {'snapshot': path, 'snapshot_sha256': hashlib.sha256(raw_bytes).hexdigest(), 'rebuilt_at': rebuilt_at,
                  'mode': mode, 'options_changed': {}, 'format_version': meta.get('format_version'),
                  'collected_at': meta.get('generated_at'), 'version_warnings': version_warnings(meta), 'errors': []}


def guarded(path, mode, fn):
    """Run fn(); a snapshot or option that cannot be used becomes an exit-2 result (data-model §5 error codes)."""
    try:
        return fn()
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return error_result(path, 'unreadable', f"스냅샷을 읽을 수 없습니다: {e}", mode=mode), None
    except ri.LegacyFormat:
        return error_result(path, 'legacy_format', LEGACY_MSG, mode=mode), None
    except ri.MissingInput as e:
        return error_result(path, 'missing_input', f"원자료 없음: {e.path} — 스냅샷이 손상됐거나 다른 도구로 만든 파일입니다.", e.path, mode), None
    except ri.InvalidInput as e:
        return error_result(path, 'invalid_input', str(e), e.path, mode), None
    except OptionError as e:
        return error_result(path, e.code, str(e), e.detail, mode), None
    except (gfs.NoData, ValueError, KeyError, TypeError) as e:
        return error_result(path, 'invalid_input', f"스냅샷으로 Section 4를 만들 수 없습니다: {type(e).__name__}: {e}", mode=mode), None


# ---------------------------------------------------------------- verify

def verify(path, rebuilt_at=None):
    return guarded(path, 'verify', lambda: _verify(path, rebuilt_at))


def _verify(path, rebuilt_at):
    snap, result = load(path, 'verify', rebuilt_at)
    body, values, warnings = rebuild(snap)
    baseline = (snap.get('section4') or {}).get('text')
    s4 = {'compared': baseline is not None, 'lines': len(body.splitlines())}
    if baseline is not None:
        s4['diff'] = compare_lines(baseline, body)
        s4['same'] = not s4['diff']
    result['section4'] = s4
    result['values'] = compare_values(snap.get('values') or {}, values)
    stored_w = snap.get('warnings') or []
    result['warnings'] = {'same': warnings == stored_w, 'count': len(stored_w),
                          'diff': [] if warnings == stored_w else
                          [{'stored': [w['msg'] for w in stored_w], 'rebuilt': [w['msg'] for w in warnings]}]}
    if baseline is not None and not s4['same']:
        s4['cause'] = 'text_only' if (result['values']['same'] and result['warnings']['same']) else 'values'
    same = result['values']['same'] and result['warnings']['same'] and s4.get('same', True)
    result['exit_code'] = EXIT_SAME if same else EXIT_DIFF
    return result, body


# ---------------------------------------------------------------- recompute (US3)

def recompute(path, changes, out_path, rebuilt_at=None):
    """changes: {'weights' | 'cyclical' | 'not_cyclical': command-line text}. Writes out_path; never touches the snapshot."""
    return guarded(path, 'recompute', lambda: _recompute(path, changes, out_path, rebuilt_at))


def _recompute(path, changes, out_path, rebuilt_at):
    snap, result = load(path, 'recompute', rebuilt_at)
    if os.path.exists(out_path):
        raise OptionError('output_exists', f"출력 파일이 이미 있습니다: {out_path} — 덮어쓰지 않습니다.", out_path)
    args = snap['meta'].get('args') or {}
    tickers = gfs.split_list(args.get('tickers'))
    overrides = {}
    if 'weights' in changes:
        weights = gfs.parse_weights(changes['weights'])
        if weights is None:
            raise OptionError('option_rejected', "--weights는 Bull,Base,Bear 세 숫자(음수 아님, 합 1)여야 합니다.", changes['weights'])
        overrides['weights'] = weights
    for opt, key in (('cyclical', 'cyclical_add'), ('not_cyclical', 'cyclical_remove')):
        if opt in changes:
            chosen = gfs.split_list(changes[opt])
            unknown = [s for s in chosen if s not in tickers]
            if unknown:
                raise OptionError('option_needs_data', "스냅샷에 없는 종목이라 다시 받지 않고는 계산할 수 없습니다.",
                                  f"--{opt.replace('_', '-')} {','.join(unknown)} (스냅샷에 없는 종목)")
            overrides[key] = set(chosen)
    result['options_changed'] = {opt: [args.get(opt) or '', changes[opt]] for opt, _ in RECOMPUTE_OPTIONS if opt in changes}
    body, values, _ = rebuild(snap, overrides)
    result['values'] = compare_values(snap.get('values') or {}, values)
    changed = "; ".join(f"{opt} {before or '(없음)'} → {after or '(없음)'}" for opt, (before, after) in result['options_changed'].items())
    header = (f"> 🔁 **재계산 결과 — 보고서가 아닙니다.** 원본 스냅샷: `{os.path.basename(path)}` "
              f"(sha256 {result['snapshot_sha256'][:8]}), 수집 {result['collected_at']}.\n"
              f"> 바꾼 옵션: {changed}. 데이터는 다시 받지 않았습니다.")
    with open(out_path, 'x', encoding='utf-8') as f:
        f.write(header + "\n\n" + body + "\n")
    result['out'] = out_path
    result['exit_code'] = EXIT_SAME
    return result, body


# ---------------------------------------------------------------- output

def _short(v):
    s = str(v)
    return s if len(s) <= 60 else s[:57] + '...'


def _value_lines(v, limit):
    out = []
    for c in v['changed'][:limit]:
        extra = "" if c['fields'] == ['value'] else f" (다른 항목: {', '.join(c['fields'])})"
        out.append(f"  {c['path']}: {_short(c['stored'])} → {_short(c['rebuilt'])}{extra}")
    out += [f"  + {p}" for p in v['added'][:limit]]
    out += [f"  - {p}" for p in v['removed'][:limit]]
    return out


def render_summary(r, verbose=False):
    title = "재계산" if r['mode'] == 'recompute' else "재현 확인"
    if r['exit_code'] == EXIT_ERROR:
        e = r['errors'][0]
        detail = f" ({e['detail']})" if e.get('detail') and e['detail'] not in e['message'] else ""
        return f"{title}: {r['snapshot']}\n{e['message']}{detail}\n결과: 다시 만들 수 없음 (종료 코드 2)"
    limit = None if verbose else SHOW
    out = [f"{title}: {r['snapshot']} (형식 {r['format_version']}, 수집 {r.get('collected_at')})"]
    vw = r.get('version_warnings') or []
    out.append("버전: 같음" if not vw else "버전: " + ", ".join(vw) + " — 결과가 다르면 아래에 나타납니다")
    if r['mode'] == 'recompute':
        v = r['values']
        out.append("바꾼 옵션: " + "; ".join(f"{k} {a or '(없음)'} → {b or '(없음)'}" for k, (a, b) in r['options_changed'].items()))
        out.append(f"바뀐 계산값: {len(v['changed'])}개 · 새로 생김 {len(v['added'])} · 없어짐 {len(v['removed'])}")
        out += _value_lines(v, limit)
        out.append(f"저장: {r['out']} (원본 스냅샷은 바꾸지 않음) — 종료 코드 0")
        return "\n".join(out)
    s4 = r['section4']
    if not s4['compared']:
        out.append(f"Section 4: 기준본 없음 (다시 만든 {s4['lines']}줄, --print로 확인)")
    elif s4['same']:
        out.append(f"Section 4: 같음 (기준본 {s4['lines']}줄)")
    else:
        cause = " — 계산 결과 같음, 글자만 다름" if s4.get('cause') == 'text_only' else ""
        out.append(f"Section 4: 다름 {len(s4['diff'])}줄{cause}")
        for d in s4['diff'][:limit]:
            out.append(f"  {d['line']}행: {_short(d['baseline'])} → {_short(d['rebuilt'])}")
    v = r['values']
    if v['same']:
        out.append(f"계산 결과(values): 같음 ({v['count']:,}개)")
    else:
        out.append(f"계산 결과(values): 다름 — 바뀜 {len(v['changed'])} · 새로 생김 {len(v['added'])} · 없어짐 {len(v['removed'])}")
        out += _value_lines(v, limit)
    w = r['warnings']
    out.append(f"데이터 품질 경고: 같음 ({w['count']}개)" if w['same'] else "데이터 품질 경고: 다름 (--json으로 전체 비교)")
    out.append("결과: 같음 (종료 코드 0)" if r['exit_code'] == EXIT_SAME else "결과: 다름 (종료 코드 1)")
    return "\n".join(out)


def main(argv=None, rebuilt_at=None):
    parser = argparse.ArgumentParser(description="스냅샷 하나로 Section 4를 네트워크 없이 다시 만들고 저장된 값과 비교합니다 (spec 003).")
    parser.add_argument("snapshot", help="형식 2 스냅샷(*_data.json)")
    parser.add_argument("--json", dest="json_path", help="결과를 JSON으로 저장")
    parser.add_argument("--print", dest="print_body", action="store_true", help="다시 만든 Section 4를 출력")
    parser.add_argument("--verbose", action="store_true", help="차이를 모두 출력")
    parser.add_argument("--weights", help="재계산: 시나리오 확률 Bull,Base,Bear (--out 필요)")
    parser.add_argument("--cyclical", help="재계산: 순환업종으로 볼 종목 (--out 필요)")
    parser.add_argument("--not-cyclical", dest="not_cyclical", help="재계산: 순환업종 자동 감지에서 뺄 종목 (--out 필요)")
    parser.add_argument("--out", help="재계산 결과를 쓸 새 파일 (이미 있으면 거부)")
    args, extra = parser.parse_known_args(argv)
    changes = {opt: getattr(args, opt) for opt, _ in RECOMPUTE_OPTIONS if getattr(args, opt) is not None}

    if extra:
        result, body = error_result(args.snapshot, 'option_rejected',
                                    f"받지 않는 옵션: {' '.join(extra)} — 재계산은 --weights·--cyclical·--not-cyclical만 바꿀 수 있습니다.",
                                    ' '.join(extra), 'recompute' if changes else 'verify'), None
    elif changes:
        if not args.out:
            parser.error("--weights·--cyclical·--not-cyclical은 --out과 함께 씁니다")
        result, body = recompute(args.snapshot, changes, args.out, rebuilt_at)
    else:
        if args.out:
            parser.error("--out은 재계산 옵션(--weights·--cyclical·--not-cyclical)과 함께 씁니다")
        result, body = verify(args.snapshot, rebuilt_at)

    if args.json_path:
        with open(args.json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if args.print_body and body is not None:
        print(body)
    else:
        print(render_summary(result, args.verbose))
    return result['exit_code']


if __name__ == "__main__":
    import datetime
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    when = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
    sys.exit(main(rebuilt_at=when))
