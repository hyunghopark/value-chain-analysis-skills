#!/usr/bin/env python3
"""Rebuild a report's Section 4 from its format-2 snapshot alone — no network, no clock — and compare it with
what the snapshot recorded: the Section 4 baseline, every computed value and the data-quality warnings.

Spec: specs/003-pipeline-split/ (contracts/cli.md §2, data-model §5)
Rules: references/rules/data-snapshot.md §9

Exit codes: 0 all the same · 1 something differs · 2 cannot rebuild (legacy format, missing or invalid input,
unreadable file).
"""
import argparse
import difflib
import hashlib
import json
import platform
import sys
from importlib import metadata

import get_financial_stats as gfs
import raw_inputs as ri
import snapshot as snapmod

EXIT_SAME, EXIT_DIFF, EXIT_ERROR = 0, 1, 2
SHOW = 20  # differences printed without --verbose

LEGACY_MSG = ("이 스냅샷은 원자료가 없는 이전 형식(001·002)이라 다시 만들 수 없습니다. "
              "숫자 점검(check_report_numbers.py)은 그대로 쓸 수 있습니다.")


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


def rebuild(snapshot):
    """Section 4 body plus the values and warnings the rebuild recorded (JSON-normalized like a saved snapshot)."""
    gfs.ECHO_WARNINGS = False
    text = gfs.build_section4(snapshot)
    values = json.loads(json.dumps(gfs.SNAP.values, ensure_ascii=False))
    warnings = json.loads(json.dumps(gfs.SNAP.warnings, ensure_ascii=False))
    return snapmod.section4_body(text), values, warnings


def error_result(path, code, message, detail=None):
    return {'snapshot': path, 'mode': 'verify', 'errors': [{'code': code, 'message': message, 'detail': detail}],
            'exit_code': EXIT_ERROR}


def verify(path, rebuilt_at=None):
    try:
        with open(path, 'rb') as f:
            raw_bytes = f.read()
        snap = json.loads(raw_bytes.decode('utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        return error_result(path, 'unreadable', f"스냅샷을 읽을 수 없습니다: {e}"), None
    result = {'snapshot': path, 'snapshot_sha256': hashlib.sha256(raw_bytes).hexdigest(), 'rebuilt_at': rebuilt_at,
              'mode': 'verify', 'options_changed': {}, 'errors': []}
    try:
        ri.check_format(snap)
        meta = snap['meta']
        result['format_version'] = meta.get('format_version')
        result['collected_at'] = meta.get('generated_at')
        result['version_warnings'] = version_warnings(meta)
        body, values, warnings = rebuild(snap)
    except ri.LegacyFormat:
        return error_result(path, 'legacy_format', LEGACY_MSG), None
    except ri.MissingInput as e:
        return error_result(path, 'missing_input', f"원자료 없음: {e.path} — 스냅샷이 손상됐거나 다른 도구로 만든 파일입니다.", e.path), None
    except ri.InvalidInput as e:
        return error_result(path, 'invalid_input', str(e), e.path), None
    except (gfs.NoData, ValueError, KeyError, TypeError) as e:
        return error_result(path, 'invalid_input', f"스냅샷으로 Section 4를 만들 수 없습니다: {type(e).__name__}: {e}"), None

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


def _short(v):
    s = str(v)
    return s if len(s) <= 60 else s[:57] + '...'


def render_summary(r, verbose=False):
    if r['exit_code'] == EXIT_ERROR:
        e = r['errors'][0]
        return f"재현 확인: {r['snapshot']}\n{e['message']}\n결과: 다시 만들 수 없음 (종료 코드 2)"
    limit = None if verbose else SHOW
    out = [f"재현 확인: {r['snapshot']} (형식 {r['format_version']}, 수집 {r.get('collected_at')})"]
    vw = r.get('version_warnings') or []
    out.append("버전: 같음" if not vw else "버전: " + ", ".join(vw) + " — 결과가 다르면 아래에 나타납니다")
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
        for c in v['changed'][:limit]:
            extra = "" if c['fields'] == ['value'] else f" (다른 항목: {', '.join(c['fields'])})"
            out.append(f"  {c['path']}: {_short(c['stored'])} → {_short(c['rebuilt'])}{extra}")
        for p in v['added'][:limit]:
            out.append(f"  + {p}")
        for p in v['removed'][:limit]:
            out.append(f"  - {p}")
    w = r['warnings']
    out.append(f"데이터 품질 경고: 같음 ({w['count']}개)" if w['same'] else "데이터 품질 경고: 다름 (--json으로 전체 비교)")
    out.append("결과: 같음 (종료 코드 0)" if r['exit_code'] == EXIT_SAME else "결과: 다름 (종료 코드 1)")
    return "\n".join(out)


def main(argv=None, rebuilt_at=None):
    parser = argparse.ArgumentParser(description="스냅샷 하나로 Section 4를 네트워크 없이 다시 만들고 저장된 값과 비교합니다 (spec 003).")
    parser.add_argument("snapshot", help="형식 2 스냅샷(*_data.json)")
    parser.add_argument("--json", dest="json_path", help="재현 결과를 JSON으로 저장")
    parser.add_argument("--print", dest="print_body", action="store_true", help="다시 만든 Section 4를 출력")
    parser.add_argument("--verbose", action="store_true", help="차이를 모두 출력")
    args = parser.parse_args(argv)

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
