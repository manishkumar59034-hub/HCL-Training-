"""
Data cleaning rules applied to uploaded files BEFORE validation.

Cleaning is deliberately conservative: it only fixes formatting, never invents
values. Every change is recorded in a cleaning log that is shown to the manager.

Rules
-----
1. Column names: trimmed, lower-cased, spaces/hyphens -> underscores.
2. Text values: leading/trailing whitespace removed; empty strings -> missing.
3. Category values: matched case-insensitively to the allowed list
   (e.g. "approved" -> "Approved").
4. Numbers: thousands separators, currency symbols (₹, Rs, INR) removed,
   then converted to numbers. Values that cannot be converted become missing
   and are reported by validation (not silently replaced).
5. Dates: parsed and re-written as ISO YYYY-MM-DD. Unparseable dates are left
   as the original text so validation can report them.
6. reporting_month: normalised to the first day of the month (2025-03-17 -> 2025-03-01).
7. Exact duplicate rows inside the file are reported by validation, not dropped here.
"""
from __future__ import annotations

import re

import pandas as pd

from analytics.data_validation import TABLE_SPECS

CURRENCY_RE = re.compile(r"(₹|rs\.?|inr|,|\s)", re.IGNORECASE)


def normalise_column_name(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(name).strip().lower())


def _parse_date_value(value):
    if value is None or (isinstance(value, float) and pd.isna(value)) or value == "":
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", text):
        parsed = pd.to_datetime(text if len(text) == 10 else text + "-01",
                                format="%Y-%m-%d", errors="coerce")
    else:
        parsed = pd.to_datetime(text, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return text  # leave as-is; validation will flag it
    return parsed.strftime("%Y-%m-%d")


def clean_dataframe(table: str, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return (cleaned_df, cleaning_log)."""
    spec = TABLE_SPECS[table]
    log: list[str] = []
    df = df.copy()

    renamed = {c: normalise_column_name(c) for c in df.columns}
    changed = {k: v for k, v in renamed.items() if k != v}
    if changed:
        log.append(f"Standardised {len(changed)} column name(s): "
                   + ", ".join(f"'{k}'→'{v}'" for k, v in changed.items()))
    df = df.rename(columns=renamed)

    # Drop completely empty rows (e.g. trailing blank lines in Excel)
    empty = df.isna().all(axis=1)
    if empty.any():
        log.append(f"Removed {int(empty.sum())} completely empty row(s).")
        df = df[~empty].reset_index(drop=True)

    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            stripped = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
            stripped = stripped.replace({"": None})
            df[col] = stripped

    for col, allowed in spec.get("categories", {}).items():
        if col in df.columns:
            lookup = {a.lower(): a for a in allowed}
            before = df[col].copy()
            df[col] = df[col].map(lambda v: lookup.get(str(v).lower(), v) if pd.notna(v) else v)
            fixed = int((before.astype(str) != df[col].astype(str)).sum())
            if fixed:
                log.append(f"Corrected letter case in {fixed} '{col}' value(s).")

    for col in spec.get("numeric", {}):
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            raw = df[col]
            cleaned = raw.map(lambda v: CURRENCY_RE.sub("", str(v)) if pd.notna(v) else v)
            df[col] = pd.to_numeric(cleaned, errors="coerce")
            lost = int((raw.notna() & df[col].isna()).sum())
            log.append(f"Converted '{col}' to numbers (any ₹ symbols/commas removed)."
                       + (f" {lost} value(s) were not numeric." if lost else ""))

    for col in spec.get("dates", []):
        if col in df.columns:
            df[col] = df[col].map(_parse_date_value)
    if table == "branch_financials" and "reporting_month" in df.columns:
        def _first(v):
            if (isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)
                    and pd.notna(pd.to_datetime(v, format="%Y-%m-%d", errors="coerce"))):
                return v[:8] + "01"
            return v
        before = df["reporting_month"].copy()
        df["reporting_month"] = df["reporting_month"].map(_first)
        n = int((before.astype(str) != df["reporting_month"].astype(str)).sum())
        if n:
            log.append(f"Normalised {n} reporting_month value(s) to the first day of the month.")

    if not log:
        log.append("No cleaning changes were needed.")
    return df, log
