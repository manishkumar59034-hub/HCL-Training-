"""
Display formatting helpers (Indian number system).

    fmt_inr(1245678)              -> '₹12,45,678'
    fmt_inr(1245678, short=True)  -> '₹12.46 L'
    fmt_inr(32_10_00_000, short=True) -> '₹32.10 Cr'
    fmt_pct(12.345)               -> '12.3%'
"""
from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd

NA = "N/A"


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value)) or (isinstance(value, float) and math.isinf(value))
    except (TypeError, ValueError):
        return False


def indian_grouping(n: int) -> str:
    """Group digits the Indian way: 1234567 -> '12,34,567'."""
    s = str(abs(int(n)))
    if len(s) <= 3:
        out = s
    else:
        last3, rest = s[-3:], s[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        out = ",".join(groups) + "," + last3
    return ("-" if n < 0 else "") + out


def fmt_inr(value, short: bool = False, decimals: int = 2) -> str:
    if _missing(value):
        return NA
    value = float(value)
    sign = "-" if value < 0 else ""
    a = abs(value)
    if short:
        if a >= 1e7:
            return f"{sign}₹{a / 1e7:,.{decimals}f} Cr"
        if a >= 1e5:
            return f"{sign}₹{a / 1e5:,.{decimals}f} L"
        if a >= 1e3:
            return f"{sign}₹{a / 1e3:,.1f} K"
    return f"{sign}₹{indian_grouping(round(a))}"


def fmt_number(value, decimals: int = 0) -> str:
    if _missing(value):
        return NA
    if decimals == 0:
        return indian_grouping(round(float(value)))
    whole, frac = f"{abs(float(value)):.{decimals}f}".split(".")
    return ("-" if float(value) < 0 else "") + indian_grouping(int(whole)) + "." + frac


def fmt_pct(value, decimals: int = 1, signed: bool = False) -> str:
    if _missing(value):
        return NA
    return f"{float(value):+.{decimals}f}%" if signed else f"{float(value):.{decimals}f}%"


def fmt_score(value) -> str:
    return NA if _missing(value) else f"{float(value):.2f} / 5"


def fmt_date(value, fmt: str = "%d %b %Y") -> str:
    if _missing(value):
        return NA
    if isinstance(value, str):
        value = pd.to_datetime(value, errors="coerce")
        if pd.isna(value):
            return NA
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime(fmt)
    return str(value)


def fmt_month(value) -> str:
    return fmt_date(value, "%b %Y")
