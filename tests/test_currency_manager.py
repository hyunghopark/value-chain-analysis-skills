"""
Unit tests for currency_manager.py.
Verifies ISO 4217 registry, decimal precisions, Money pattern type safety,
and deterministic currency formatting.
"""

import os
import sys
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "skills", "financial-analyst", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import currency_manager as cm
from currency_manager import Money, format_currency, get_currency_decimals, get_currency_info


def test_iso_4217_decimals():
    """Verify official decimal precisions across global currencies."""
    # 0 decimals (integer)
    assert get_currency_decimals("KRW") == 0
    assert get_currency_decimals("JPY") == 0
    assert get_currency_decimals("TWD") == 0
    assert get_currency_decimals("VND") == 0

    # 2 decimals (standard)
    assert get_currency_decimals("USD") == 2
    assert get_currency_decimals("EUR") == 2
    assert get_currency_decimals("GBP") == 2
    assert get_currency_decimals("CNY") == 2
    assert get_currency_decimals("HKD") == 2
    assert get_currency_decimals("CHF") == 2

    # 3 decimals (middle east)
    assert get_currency_decimals("BHD") == 3
    assert get_currency_decimals("KWD") == 3

    # Unknown fallback
    assert get_currency_decimals("XYZ") == 2


def test_format_currency_standard():
    """Verify standard string representation by currency."""
    assert format_currency(208000, "KRW") == "₩208,000"
    assert format_currency(155.8, "USD", code_wrap_usd=True) == "`$155.80`"
    assert format_currency(155.8, "USD", code_wrap_usd=False) == "$155.80"
    assert format_currency(750.5, "EUR") == "€750.50"
    assert format_currency(28500, "JPY") == "¥28,500"
    assert format_currency(1050, "TWD") == "NT$1,050"
    assert format_currency(2500000, "VND") == "2,500,000 ₫"
    assert format_currency(1234.567, "BHD") == "BD1,234.567"
    assert format_currency(13940, "GBp") == "13,940 p"
    assert format_currency(134.12, "CHF") == "CHF 134.12"


def test_format_currency_edge_cases():
    """Verify formatting edge cases like None, NaN, zero, and negatives."""
    assert format_currency(None) == "N/A"
    assert format_currency(float("nan")) == "N/A"
    assert format_currency(0, "KRW") == "₩0"
    assert format_currency(0, "USD", code_wrap_usd=False) == "$0.00"
    assert format_currency(-208000, "KRW") == "-₩208,000"
    assert format_currency(-155.8, "USD", code_wrap_usd=False) == "-$155.80"


def test_format_currency_dual():
    """Verify dual currency formatting when live FX rate is given."""
    formatted = format_currency(208000, "KRW", dual_fx_rate=1335.0, dual_target_ccy="USD")
    assert formatted == "₩208,000 (`$155.81`)"


def test_money_pattern_type_safety():
    """Verify Money value object type safety and arithmetic."""
    m1 = Money(100.50, "USD")
    m2 = Money(50.25, "USD")

    # Same currency operations
    added = m1 + m2
    assert added.amount == 150.75
    assert added.currency == "USD"

    subbed = m1 - m2
    assert subbed.amount == 50.25

    scaled = m1 * 2
    assert scaled.amount == 201.0

    divided = m1 / 2
    assert divided.amount == 50.25

    # Cross currency operation must raise TypeError
    krw_money = Money(208000, "KRW")
    with pytest.raises(TypeError):
        _ = m1 + krw_money

    with pytest.raises(TypeError):
        _ = m1 - krw_money


def test_money_conversion():
    """Verify deterministic conversion using explicit FX rate."""
    usd_money = Money(100.0, "USD")
    krw_money = usd_money.to_currency("KRW", fx_rate=1335.0)
    assert krw_money.currency == "KRW"
    assert krw_money.amount == 133500
