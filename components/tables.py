"""Formatted table display for the branch / loan / insight tables."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.formatting import fmt_inr, fmt_number, fmt_pct

BRANCH_TABLE_COLUMNS = {
    "branch_name": "Branch Name", "city": "City", "region": "Region", "customers": "Customers",
    "revenue": "Revenue (₹)", "expenses": "Expenses (₹)", "profit": "Profit (₹)",
    "profit_margin": "Profit Margin %", "revenue_target": "Revenue Target (₹)",
    "target_achievement": "Target Achievement %", "deposits": "Deposits (₹)",
    "loan_disbursement": "Loan Disbursement (₹)", "satisfaction": "Customer Satisfaction",
    "performance_category": "Performance Category",
}


def branch_table_export(summary: pd.DataFrame) -> pd.DataFrame:
    """Raw-number version with friendly headings (for CSV/Excel export)."""
    if summary is None or summary.empty:
        return pd.DataFrame(columns=list(BRANCH_TABLE_COLUMNS.values()))
    out = summary[list(BRANCH_TABLE_COLUMNS)].rename(columns=BRANCH_TABLE_COLUMNS).copy()
    for c in ("Profit Margin %", "Target Achievement %"):
        out[c] = out[c].astype(float).round(2)
    out["Customer Satisfaction"] = out["Customer Satisfaction"].astype(float).round(2)
    for c in [c for c in out.columns if "(₹)" in c]:
        out[c] = out[c].round(2)
    return out


def show_branch_table(summary: pd.DataFrame, height: int = 520) -> None:
    if summary is None or summary.empty:
        st.info("No branches match the selected filters.")
        return
    df = branch_table_export(summary)
    # Show money in ₹ Lakh (Indian convention) while keeping columns numeric & sortable
    money = {}
    for c in [c for c in df.columns if "(₹)" in c]:
        new = c.replace("(₹)", "(₹ Lakh)")
        df[new] = (df.pop(c) / 1e5).round(2)
        money[new] = st.column_config.NumberColumn(new, format="%.2f")
    df = df[[c.replace("(₹)", "(₹ Lakh)") for c in BRANCH_TABLE_COLUMNS.values()]]
    st.dataframe(
        df, hide_index=True, height=height,
        column_config={
            **money,
            "Customers": st.column_config.NumberColumn(format="%,d"),
            "Profit Margin %": st.column_config.NumberColumn(format="%.1f%%"),
            "Target Achievement %": st.column_config.ProgressColumn(
                format="%.1f%%", min_value=0, max_value=max(150.0, float(df["Target Achievement %"].max() or 0))),
            "Customer Satisfaction": st.column_config.NumberColumn(format="%.2f"),
        },
    )


def display_frame(df: pd.DataFrame, money_cols=(), pct_cols=(), int_cols=(), rename=None) -> pd.DataFrame:
    """String-formatted copy of a frame for read-only display (Indian formatting)."""
    out = df.copy()
    for c in money_cols:
        if c in out:
            out[c] = out[c].map(lambda v: fmt_inr(v))
    for c in pct_cols:
        if c in out:
            out[c] = out[c].map(lambda v: fmt_pct(v))
    for c in int_cols:
        if c in out:
            out[c] = out[c].map(lambda v: fmt_number(v))
    return out.rename(columns=rename or {})
