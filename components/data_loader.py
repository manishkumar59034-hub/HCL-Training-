"""
Loads every dataset needed by the pages for the current filters, with caching.

The cache key includes a 'data version' (last refresh timestamp stored in the
database) and the bank_id, so after an import or reset the dashboard shows new
data, and one bank's cached data is never shown to another bank.

Multi-bank: sirf logged-in manager ki bank ki branches (aur unka data) rakha jata hai.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from analytics import branch_analysis as ba
from analytics import kpi_calculations as kpi
from analytics import queries as q
from database import db


@dataclass
class Dataset:
    filters: q.Filters
    branches: pd.DataFrame
    financials: pd.DataFrame
    customers: pd.DataFrame
    feedback: pd.DataFrame
    loans: pd.DataFrame
    summary: pd.DataFrame
    monthly: pd.DataFrame
    customer_growth: pd.DataFrame

    @property
    def is_empty(self) -> bool:
        return self.branches.empty or self.financials.empty


def data_version() -> str:
    return db.get_metadata("last_data_refresh", "never") or "never"


def _bank_branch_ids(bank_id: int) -> set:
    rows = db.fetch_all("SELECT branch_id FROM branches WHERE bank_id = ?", [bank_id])
    return {r["branch_id"] for r in rows}


def _only_bank(df: pd.DataFrame, branch_ids: set) -> pd.DataFrame:
    """DataFrame me sirf is bank ki branches ki rows rakho."""
    if df is None or df.empty or "branch_id" not in df.columns:
        return df
    return df[df["branch_id"].isin(branch_ids)].reset_index(drop=True)


@st.cache_data(show_spinner="Crunching branch data…", max_entries=64)
def _load(filters: q.Filters, version: str, high: float, average: float,
          bank_id: int) -> Dataset:
    ids = _bank_branch_ids(bank_id)
    branches = _only_bank(q.get_branches(filters), ids)
    fin = _only_bank(q.get_financials(filters), ids)
    customers = _only_bank(q.get_customers(filters), ids)
    feedback = _only_bank(q.get_feedback(filters), ids)
    loans = _only_bank(q.get_loans(filters), ids)
    summary = ba.branch_summary(branches, fin, customers, feedback, loans, high=high, average=average)
    monthly = kpi.monthly_financials(fin)
    growth = ba.customer_growth_monthly(customers, monthly["reporting_month"]) if not monthly.empty \
        else pd.DataFrame(columns=["month", "total_customers", "new_customers"])
    return Dataset(filters, branches, fin, customers, feedback, loans, summary, monthly, growth)


def load_dataset(filters: q.Filters, bank_id: int | None = None) -> Dataset:
    from config import settings
    if bank_id is None:
        bank_id = st.session_state.get("bank_id", 0)
    high = st.session_state.get("threshold_high", settings.HIGH_PERFORMER_THRESHOLD)
    avg = st.session_state.get("threshold_avg", settings.AVERAGE_PERFORMER_THRESHOLD)
    return _load(filters, data_version(), float(high), float(avg), int(bank_id))


@st.cache_data(max_entries=8)
def _filter_options_cached(version: str, bank_id: int) -> tuple[pd.DataFrame, tuple]:
    ids = _bank_branch_ids(bank_id)
    return _only_bank(q.all_branches(), ids), q.data_date_bounds()


def filter_options(version: str) -> tuple[pd.DataFrame, tuple]:
    """Sidebar ke dropdowns: sirf logged-in bank ki branches dikhao.
    Signature same rakha hai, taaki sidebar.py ko badalna na pade."""
    return _filter_options_cached(version, int(st.session_state.get("bank_id", 0)))


def clear_caches() -> None:
    st.cache_data.clear()