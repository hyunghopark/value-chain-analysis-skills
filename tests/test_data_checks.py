"""Tests for skills/financial-analyst/scripts/data_checks.py (no network).

Cases mirror incidents recorded in wiki/known-issues/ (KI-001 ... KI-006).
Run: uv run --no-project --with-requirements skills/financial-analyst/requirements.txt --with pytest pytest tests
"""
import datetime
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'skills', 'financial-analyst', 'scripts'))
import data_checks as dc  # noqa: E402

TZ = 'Asia/Seoul'


def yahoo_hist(rows):
    """rows: [(YYYY-MM-DD, close, volume)] -> Yahoo-like tz-aware history."""
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d, _, _ in rows]).tz_localize(TZ)
    close = [c for _, c, _ in rows]
    return pd.DataFrame({'Open': close, 'High': close, 'Low': close, 'Close': close,
                         'Adj Close': close, 'Volume': [v for _, _, v in rows],
                         'Dividends': 0.0, 'Stock Splits': 0.0}, index=idx)


def daum_rows(rows):
    """rows: [(YYYY-MM-DD, close, volume)] -> Daum /days JSON rows."""
    return [{'date': f'{d} 00:00:00', 'tradePrice': c, 'openingPrice': c, 'highPrice': c,
             'lowPrice': c, 'accTradeVolume': v} for d, c, v in rows]


def test_daum_frame_parses_rows():
    df = dc.daum_frame(daum_rows([('2026-10-13', 232000, 24104354), ('2026-10-12', 250500, 17143787)]))
    assert list(df.index) == [pd.Timestamp('2026-10-12'), pd.Timestamp('2026-10-13')]
    assert df.loc['2026-10-13', 'Close'] == 232000


def test_reconcile_fills_missing_and_empty_days():
    # KI-002: Yahoo dropped 10/12 and left 10/13 empty.
    hist = yahoo_hist([('2026-10-07', 268500, 1), ('2026-10-08', 262000, 1), ('2026-10-13', float('nan'), 0)])
    ref = dc.daum_frame(daum_rows([('2026-10-07', 268500, 1), ('2026-10-08', 262000, 1),
                                   ('2026-10-12', 250500, 2), ('2026-10-13', 232000, 3)]))
    fixed, filled, replaced = dc.reconcile_history(hist, ref)
    closes = fixed['Close']
    closes.index = dc.naive_dates(closes.index)
    assert filled == [pd.Timestamp('2026-10-12'), pd.Timestamp('2026-10-13')]
    assert replaced == []
    assert closes[pd.Timestamp('2026-10-12')] == 250500
    assert closes[pd.Timestamp('2026-10-13')] == 232000
    assert fixed.index.tz is not None and fixed.index.is_monotonic_increasing


def test_reconcile_replaces_wrong_close():
    # KI-006: Yahoo 2026-06-24 close 2,621,000 vs KRX 2,580,000.
    hist = yahoo_hist([('2026-06-23', 2500000, 1), ('2026-06-24', 2621000, 1)])
    ref = dc.daum_frame(daum_rows([('2026-06-23', 2500000, 1), ('2026-06-24', 2580000, 1)]))
    fixed, filled, replaced = dc.reconcile_history(hist, ref)
    assert filled == []
    assert replaced == [(pd.Timestamp('2026-06-24'), 2621000.0, 2580000.0)]
    assert fixed['Close'].iloc[-1] == 2580000


def test_reconcile_does_not_prepend_before_history():
    hist = yahoo_hist([('2026-10-08', 262000, 1)])
    ref = dc.daum_frame(daum_rows([('2026-10-07', 268500, 1), ('2026-10-08', 262000, 1)]))
    fixed, filled, _ = dc.reconcile_history(hist, ref)
    assert filled == [] and len(fixed) == 1


def test_close_mismatches_and_missing():
    # KI-001: Naver close field 251,000 vs KRX 250,500 on 2026-10-12.
    naver = pd.Series([251000.0, 263000.0], index=pd.to_datetime(['2026-10-12', '2026-10-08']))
    krx = pd.Series([250500.0, 262000.0], index=pd.to_datetime(['2026-10-12', '2026-10-08']))
    assert dc.close_mismatches(naver, krx) == [(pd.Timestamp('2026-10-12'), 251000.0, 250500.0),
                                               (pd.Timestamp('2026-10-08'), 263000.0, 262000.0)]
    yahoo = pd.Series([262000.0], index=pd.to_datetime(['2026-10-08']).tz_localize(TZ))
    assert dc.missing_closes(yahoo, krx) == [pd.Timestamp('2026-10-12')]


def test_volume_outliers_flags_broken_day():
    # KI-005: Yahoo volume 151 shares on 2026-06-10 among ~4.9M-share days.
    days = pd.bdate_range('2026-05-11', periods=22)
    vol = pd.Series([4_900_000.0] * 22, index=days)
    vol.iloc[-1] = 151
    out = dc.volume_outliers(vol)
    assert [d for d, _, _ in out] == [days[-1]]


def test_statement_lag():
    # KI-003: Micron fiscal year ended 2026-09-03 (epoch 1788393600) but annual table stops at 2025-08-31.
    assert dc.statement_lag(pd.Timestamp('2025-08-31'), 1788393600) == datetime.date(2026, 9, 3)
    assert dc.statement_lag(pd.Timestamp('2026-09-03'), 1788393600) is None
    assert dc.statement_lag(None, 1788393600) == datetime.date(2026, 9, 3)
    assert dc.statement_lag(pd.Timestamp('2025-12-31'), None) is None


def test_wisereport_header_guard():
    good = ['재무년월', '매출액(억원, %)', '영업이익(억원, %)', '당기순이익(억원, %)', 'EPS(원)', 'PER(배)', 'PBR(배)']
    dc.validate_wisereport_header(good)
    with pytest.raises(ValueError, match='KI-004'):
        dc.validate_wisereport_header(['재무년월', '매출액(억원, %)', 'EPS(원)', '영업이익(억원, %)', '당기순이익(억원, %)', 'PER(배)'])


def test_wisereport_row_guard():
    dc.check_wisereport_row(['2023(A)', '327,657', '-26.57', '-77,303', '-91,124', '-12,517', 'N/A', '1.82'])
    dc.check_wisereport_row(['2027(E)', '5,128,005', '49.82', '4,034,723', '3,315,501', '453,872', '3.54', '1.64'])
    with pytest.raises(ValueError, match='KI-004'):
        dc.check_wisereport_row(['2025(A)', '971,467', '46.76', '472,063', '429,193', '-58,955', '11.04', '3.79'])


def test_ref_close_on():
    ref = dc.daum_frame(daum_rows([('2026-10-12', 250500, 1)]))
    assert dc.ref_close_on(ref, '20261012') == 250500
    assert dc.ref_close_on(ref, '20261013') is None
    assert dc.ref_close_on(None, '20261012') is None


def test_ki_prefix():
    assert dc.ki('KI-001', 'msg') == '[KI-001] msg'
    assert set(dc.KNOWN_ISSUES) == {f'KI-00{i}' for i in range(1, 9)}
    assert dc.DAUM_INDEX == {'^KS11': 'KOSPI', '^KQ11': 'KOSDAQ'}


def test_reconcile_index_without_ohlc():
    # KI-002 (index): Yahoo ^KS11 2026-10-13 close was NaN; Daum KOSPI index rows carry only tradePrice.
    hist = yahoo_hist([('2026-10-08', 6625.930176, 1), ('2026-10-12', 6384.240234, 1), ('2026-10-13', float('nan'), 0)])
    ref = dc.daum_frame([{'date': '2026-10-12 00:00:00', 'tradePrice': 6384.24},
                         {'date': '2026-10-13 00:00:00', 'tradePrice': 6035.35}])
    fixed, filled, replaced = dc.reconcile_history(hist, ref)
    assert filled == [pd.Timestamp('2026-10-13')]
    assert replaced == []  # 6384.240234 vs 6384.24 is the same close
    assert fixed['Close'].iloc[-1] == 6035.35
