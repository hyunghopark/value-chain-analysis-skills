"""
Raw inputs saved in a format-2 snapshot, so Section 4 can be rebuilt from the snapshot alone.
Spec: specs/003-pipeline-split/ (research R3·R5·R10, data-model §2·§3)
Rules: references/rules/data-snapshot.md

Only collect.py fetches anything. Everything after it reads these items, and a table read back
here is identical to the one collected (dtype, timezone name, datetime unit and index names kept).
"""

import datetime
import json
import math
import re

import pandas as pd

FORMAT_VERSION = 2
SOURCES = {'yahoo', 'naver', 'wisereport', 'daum', 'pykrx'}
STATUSES = {'ok', 'empty', 'error', 'skipped'}
KINDS = {'json', 'frame', 'table'}
_FETCHED_AT = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00$')
_FRAME_KEYS = {'index', 'columns', 'dtypes', 'data'}


class RawInputError(BaseException):
    """A snapshot that cannot be rebuilt from. Derived from BaseException on purpose: the pipeline has many
    `except Exception` blocks that turn source failures into warnings, and a broken snapshot must stop the
    rebuild instead of becoming a data-quality warning (constitution III)."""
    code = 'invalid_input'

    def __init__(self, msg, path=None):
        super().__init__(msg)
        self.path = path


class MissingInput(RawInputError):
    """An input the pipeline needs is not in the snapshot (a damaged or foreign file)."""
    code = 'missing_input'

    def __init__(self, path):
        super().__init__(f"원자료 없음: {path}", path)


class InvalidInput(RawInputError):
    code = 'invalid_input'


class LegacyFormat(RawInputError):
    """A format-1 snapshot (spec 001·002): values only, no raw inputs to rebuild from."""
    code = 'legacy_format'


# --- Tables ---

def _plain(v):
    """A JSON-safe cell: NaN/NaT → None, ±inf → 'Infinity'/'-Infinity', timestamps → ISO text."""
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if hasattr(v, 'item'):
        v = v.item()
    if isinstance(v, float):
        if math.isnan(v):
            return None
        if math.isinf(v):
            return 'Infinity' if v > 0 else '-Infinity'
    return v


def _encode_index(ix):
    if isinstance(ix, pd.MultiIndex):
        raise ValueError("MultiIndex is not supported")
    if isinstance(ix, pd.DatetimeIndex):
        tz = str(ix.tz) if ix.tz is not None else None
        naive = ix.tz_localize(None) if ix.tz is not None else ix
        return {'kind': 'datetime', 'tz': tz, 'unit': ix.unit, 'name': ix.name,
                'values': [None if pd.isna(d) else d.isoformat() for d in naive]}
    return {'kind': 'index', 'dtype': str(ix.dtype), 'name': ix.name, 'values': [_plain(v) for v in ix]}


def _decode_index(e):
    if e['kind'] == 'datetime':
        ix = pd.DatetimeIndex(pd.to_datetime(pd.Series(e['values'], dtype=object))).as_unit(e['unit'])
        if e['tz']:
            ix = ix.tz_localize(e['tz'])
    else:
        ix = pd.Index(e['values'], dtype=e['dtype'])
    return ix.rename(e['name'])


def _restore_column(values, dtype):
    s = pd.Series(values, dtype=object)
    if dtype.startswith('datetime64'):
        tz = dtype[dtype.index(',') + 1:-1].strip() if ',' in dtype else None
        out = pd.to_datetime(s, utc=bool(tz))
        out = out.dt.tz_convert(tz) if tz else out
        return out.astype(dtype)
    if dtype.startswith(('float', 'Float')):
        s = s.map(lambda v: {'Infinity': math.inf, '-Infinity': -math.inf}.get(v, v) if isinstance(v, str) else v)
    return s.astype(dtype)


def encode_frame(df):
    """DataFrame → JSON-ready dict (data-model §2). Read back with decode_frame."""
    return {
        'index': _encode_index(df.index),
        'columns': _encode_index(df.columns),
        'dtypes': [str(t) for t in df.dtypes],
        'data': [[_plain(v) for v in row] for row in df.itertuples(index=False, name=None)],
    }


def decode_frame(obj):
    index, columns = _decode_index(obj['index']), _decode_index(obj['columns'])
    rows, dtypes = obj['data'], obj['dtypes']
    df = pd.DataFrame(index=index)
    for i, dt in enumerate(dtypes):
        df[i] = _restore_column([r[i] for r in rows], dt).set_axis(index)
    df.columns = columns
    return df


# --- Items ---

def validate_item(path, item):
    def bad(why):
        raise InvalidInput(f"원자료 형식 오류: {path} — {why}", path)
    if not isinstance(item, dict):
        bad("항목이 객체가 아님")
    if item.get('source') not in SOURCES:
        bad(f"source {item.get('source')!r}")
    if item.get('status') not in STATUSES:
        bad(f"status {item.get('status')!r}")
    if not isinstance(item.get('fetched_at'), str) or not _FETCHED_AT.match(item['fetched_at']):
        bad(f"fetched_at {item.get('fetched_at')!r} (ISO 8601, 초, +09:00)")
    status = item['status']
    if status == 'ok':
        if item.get('kind') not in KINDS:
            bad(f"kind {item.get('kind')!r}")
        if item.get('data') is None:
            bad("status ok인데 data 없음")
        if item['kind'] == 'frame' and not (isinstance(item['data'], dict) and _FRAME_KEYS <= set(item['data'])):
            bad("frame 형식이 아님")
        if item['kind'] == 'table' and not (isinstance(item['data'], dict) and {'headers', 'rows'} <= set(item['data'])):
            bad("table 형식이 아님")
    else:
        if item.get('data') is not None:
            bad(f"status {status}인데 data 있음")
        if status == 'error' and not isinstance(item.get('error'), str):
            bad("status error인데 error 글자 없음")


def make_item(source, fetched_at, status, kind=None, data=None, error=None, note=None):
    item = {'source': source, 'fetched_at': fetched_at, 'status': status,
            'kind': kind if status == 'ok' else None, 'data': data if status == 'ok' else None,
            'error': error, 'note': note}
    validate_item(f"({source})", item)
    return item


class RawInputs:
    """Read access to inputs.<symbol>.<item>. A missing item raises MissingInput with its path."""

    def __init__(self, inputs):
        if not isinstance(inputs, dict):
            raise InvalidInput("inputs가 객체가 아님", "inputs")
        for sym, items in inputs.items():
            if not isinstance(items, dict):
                raise InvalidInput(f"원자료 형식 오류: inputs.{sym}", f"inputs.{sym}")
            for name, item in items.items():
                validate_item(f"inputs.{sym}.{name}", item)
        self._inputs = inputs
        self._frames = {}

    def symbols(self):
        return list(self._inputs)

    def has(self, sym, name):
        return name in self._inputs.get(sym, {})

    def get(self, sym, name):
        try:
            return self._inputs[sym][name]
        except KeyError:
            raise MissingInput(f"inputs.{sym}.{name}") from None

    def _data(self, sym, name, kind):
        item = self.get(sym, name)
        if item['status'] != 'ok':
            return None
        if item['kind'] != kind:
            raise InvalidInput(f"원자료 형식 오류: inputs.{sym}.{name} — kind {item['kind']} (기대 {kind})", f"inputs.{sym}.{name}")
        return item['data']

    def frame(self, sym, name):
        data = self._data(sym, name, 'frame')
        if data is None:
            return None
        key = (sym, name)
        if key not in self._frames:
            self._frames[key] = decode_frame(data)
        return self._frames[key].copy(deep=True)

    def json(self, sym, name):
        return self._data(sym, name, 'json')

    def table(self, sym, name):
        return self._data(sym, name, 'table')

    def fetched_at(self, sym, name):
        return datetime.datetime.fromisoformat(self.get(sym, name)['fetched_at'])


# --- Snapshot text (generation and rebuild share these, research R7) ---

def check_format(snapshot):
    meta = snapshot.get('meta') if isinstance(snapshot, dict) else None
    if not isinstance(meta, dict) or meta.get('format_version') != FORMAT_VERSION or not isinstance(snapshot.get('inputs'), dict):
        raise LegacyFormat("원자료가 없는 이전 형식(001·002) 스냅샷", "meta.format_version")


def dumps(meta, inputs):
    # json items keep Yahoo's NaN as is (like Snapshot.dump); frames never contain NaN tokens (see _plain)
    return json.dumps({'meta': meta, 'inputs': inputs}, ensure_ascii=False)


def loads(text):
    snap = json.loads(text)
    check_format(snap)
    return snap
