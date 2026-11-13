"""
ISO 4217 Currency Management & FX Normalization Module.
Provides global currency metadata, decimals precision, type-safe Money pattern,
and zero-hallucination currency conversion for financial analysis reports.
Spec: Pure Python Standard Library (Spec 003 Pure Determinism).
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union


@dataclass(frozen=True)
class CurrencyInfo:
    code: str
    symbol: str
    decimals: int
    name: str
    symbol_prefix: bool = True  # True: $100, False: 100 ₫


# ISO 4217 Global Currency Registry
CURRENCY_REGISTRY: Dict[str, CurrencyInfo] = {
    # 0 Decimal Currencies (Integer only)
    "KRW": CurrencyInfo("KRW", "₩", 0, "South Korean Won", symbol_prefix=True),
    "JPY": CurrencyInfo("JPY", "¥", 0, "Japanese Yen", symbol_prefix=True),
    "TWD": CurrencyInfo("TWD", "NT$", 0, "New Taiwan Dollar", symbol_prefix=True),
    "VND": CurrencyInfo("VND", "₫", 0, "Vietnamese Dong", symbol_prefix=False),
    "CLP": CurrencyInfo("CLP", "$", 0, "Chilean Peso", symbol_prefix=True),
    "HUF": CurrencyInfo("HUF", "Ft", 0, "Hungarian Forint", symbol_prefix=False),
    "IDR": CurrencyInfo("IDR", "Rp", 0, "Indonesian Rupiah", symbol_prefix=True),
    "ISV": CurrencyInfo("ISK", "kr", 0, "Icelandic Krona", symbol_prefix=False),

    # 2 Decimal Currencies (Standard global)
    "USD": CurrencyInfo("USD", "$", 2, "US Dollar", symbol_prefix=True),
    "EUR": CurrencyInfo("EUR", "€", 2, "Euro", symbol_prefix=True),
    "GBP": CurrencyInfo("GBP", "£", 2, "British Pound", symbol_prefix=True),
    "GBp": CurrencyInfo("GBp", "p", 0, "British Pence", symbol_prefix=False),
    "GBX": CurrencyInfo("GBX", "p", 0, "British Pence", symbol_prefix=False),
    "CNY": CurrencyInfo("CNY", "¥", 2, "Chinese Yuan", symbol_prefix=True),
    "HKD": CurrencyInfo("HKD", "HK$", 2, "Hong Kong Dollar", symbol_prefix=True),
    "CHF": CurrencyInfo("CHF", "CHF ", 2, "Swiss Franc", symbol_prefix=True),
    "SGD": CurrencyInfo("SGD", "S$", 2, "Singapore Dollar", symbol_prefix=True),
    "CAD": CurrencyInfo("CAD", "CA$", 2, "Canadian Dollar", symbol_prefix=True),
    "AUD": CurrencyInfo("AUD", "A$", 2, "Australian Dollar", symbol_prefix=True),
    "INR": CurrencyInfo("INR", "₹", 2, "Indian Rupee", symbol_prefix=True),
    "BRL": CurrencyInfo("BRL", "R$", 2, "Brazilian Real", symbol_prefix=True),
    "MXN": CurrencyInfo("MXN", "$", 2, "Mexican Peso", symbol_prefix=True),
    "SEK": CurrencyInfo("SEK", "kr", 2, "Swedish Krona", symbol_prefix=False),
    "NOK": CurrencyInfo("NOK", "kr", 2, "Norwegian Krone", symbol_prefix=False),
    "DKK": CurrencyInfo("DKK", "kr", 2, "Danish Krone", symbol_prefix=False),

    # 3 Decimal Currencies (Middle East)
    "BHD": CurrencyInfo("BHD", "BD", 3, "Bahraini Dinar", symbol_prefix=True),
    "KWD": CurrencyInfo("KWD", "KD", 3, "Kuwaiti Dinar", symbol_prefix=True),
    "OMR": CurrencyInfo("OMR", "OMR", 3, "Omani Rial", symbol_prefix=True),
    "JOD": CurrencyInfo("JOD", "JD", 3, "Jordanian Dinar", symbol_prefix=True),
}

DEFAULT_CURRENCY = "USD"


def get_currency_info(currency: Optional[str]) -> CurrencyInfo:
    """Look up ISO 4217 CurrencyInfo or return default fallback."""
    if not currency or not isinstance(currency, str):
        return CURRENCY_REGISTRY["USD"]
    clean_ccy = currency.strip()
    if clean_ccy in CURRENCY_REGISTRY:
        return CURRENCY_REGISTRY[clean_ccy]
    upper_ccy = clean_ccy.upper()
    if upper_ccy in CURRENCY_REGISTRY:
        return CURRENCY_REGISTRY[upper_ccy]
    # Generic fallback
    return CurrencyInfo(upper_ccy, upper_ccy, 2, f"{upper_ccy} Currency", symbol_prefix=False)


def get_currency_decimals(currency: Optional[str]) -> int:
    """Return standard decimals precision for currency (e.g. KRW: 0, USD: 2)."""
    return get_currency_info(currency).decimals


def format_currency(
    val: Any,
    currency: Optional[str] = "USD",
    *,
    code_wrap_usd: bool = True,
    dual_fx_rate: Optional[float] = None,
    dual_target_ccy: str = "USD",
) -> str:
    """
    Format monetary amount according to ISO 4217 standards.
    - KRW: ₩208,000 (0 decimals)
    - USD: `$155.80` (2 decimals, markdown backtick wrapped by default)
    - EUR: €750.50 (2 decimals)
    - JPY: ¥28,500 (0 decimals)
    - TWD: NT$1,050 (0 decimals)
    - Dual style if dual_fx_rate is provided: e.g. ₩208,000 ($155.80)
    """
    if val is None:
        return "N/A"
    try:
        f_val = float(val)
    except (TypeError, ValueError):
        return str(val)

    if not math.isfinite(f_val):
        return "N/A"

    info = get_currency_info(currency)
    decimals = info.decimals
    sign = "-" if f_val < 0 else ""
    abs_val = abs(f_val)

    if decimals == 0:
        num_str = f"{abs_val:,.0f}"
    elif decimals == 2:
        num_str = f"{abs_val:,.2f}"
    elif decimals == 3:
        num_str = f"{abs_val:,.3f}"
    else:
        num_str = f"{abs_val:,.{decimals}f}"

    if info.symbol_prefix:
        formatted_primary = f"{sign}{info.symbol}{num_str}"
    else:
        formatted_primary = f"{sign}{num_str} {info.symbol}"

    # Markdown protection for USD to prevent KaTeX inline math collision
    if info.code == "USD" and code_wrap_usd:
        formatted_primary = f"`{formatted_primary}`"

    # Dual conversion formatting if live exchange rate is supplied
    if dual_fx_rate and dual_fx_rate > 0 and info.code != dual_target_ccy:
        if info.code == "KRW" and dual_target_ccy == "USD":
            target_amount = f_val / dual_fx_rate
            dual_str = format_currency(target_amount, "USD", code_wrap_usd=True)
            return f"{formatted_primary} ({dual_str})"
        elif info.code != "USD" and dual_target_ccy == "USD":
            target_amount = f_val / dual_fx_rate
            dual_str = format_currency(target_amount, "USD", code_wrap_usd=True)
            return f"{formatted_primary} ({dual_str})"

    return formatted_primary


@dataclass(frozen=True)
class Money:
    """
    Type-Safe Monetary Value Object (Martin Fowler's Money Pattern).
    Guards against accidental cross-currency operations.
    """
    amount: float
    currency: str = "USD"

    def __post_init__(self):
        info = get_currency_info(self.currency)
        # Canonicalize currency code
        object.__setattr__(self, "currency", info.code)
        # Canonicalize amount rounding according to currency decimals
        rounded = round(float(self.amount), info.decimals) if info.decimals > 0 else round(float(self.amount))
        object.__setattr__(self, "amount", rounded)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot add different currencies: {self.currency} and {other.currency}. "
                "Convert them to the same currency using .to_currency() first."
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError(
                f"Cannot subtract different currencies: {self.currency} and {other.currency}. "
                "Convert them to the same currency using .to_currency() first."
            )
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: Union[int, float]) -> "Money":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Money(self.amount * scalar, self.currency)

    def __truediv__(self, scalar: Union[int, float]) -> "Money":
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Money by zero.")
        return Money(self.amount / scalar, self.currency)

    def to_currency(self, target_currency: str, fx_rate: float) -> "Money":
        """
        Convert Money to target currency using the given fx_rate.
        fx_rate = target_currency / current_currency
        (e.g. from USD to KRW: fx_rate = 1335.0; from KRW to USD: fx_rate = 1/1335.0)
        """
        if target_currency.upper() == self.currency:
            return self
        converted_amount = self.amount * fx_rate
        return Money(converted_amount, target_currency)

    def format(self, style: str = "standard", dual_fx_rate: Optional[float] = None) -> str:
        """Render formatted monetary string."""
        return format_currency(self.amount, self.currency, dual_fx_rate=dual_fx_rate)

    def __str__(self) -> str:
        return self.format()
