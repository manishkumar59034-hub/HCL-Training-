"""
Loads every dataset needed by the pages for the current filters, with caching.

The cache key includes a 'data version' (last refresh timestamp stored in the
database), so after an import or reset the dashboard immediately shows new data.
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


@st.cache_data(show_spinner="Crunching branch data…", max_entries=64)
def _load(filters: q.Filters, version: str, high: float, average: float) -> Dataset:
    branches = q.get_branches(filters)
    fin = q.get_financials(filters)
    customers = q.get_customers(filters)
    feedback = q.get_feedback(filters)
    loans = q.get_loans(filters)
    summary = ba.branch_summary(branches, fin, customers, feedback, loans, high=high, average=average)
    monthly = kpi.monthly_financials(fin)
    growth = ba.customer_growth_monthly(customers, monthly["reporting_month"]) if not monthly.empty \
        else pd.DataFrame(columns=["month", "total_customers", "new_customers"])
    return Dataset(filters, branches, fin, customers, feedback, loans, summary, monthly, growth)


def load_dataset(filters: q.Filters) -> Dataset:
    from config import settings
    high = st.session_state.get("threshold_high", settings.HIGH_PERFORMER_THRESHOLD)
    avg = st.session_state.get("threshold_avg", settings.AVERAGE_PERFORMER_THRESHOLD)
    return _load(filters, data_version(), float(high), float(avg))


@st.cache_data(max_entries=8)
def filter_options(version: str) -> tuple[pd.DataFrame, tuple]:
    return q.all_branches(), q.data_date_bounds()


def clear_caches() -> None:
    st.cache_data.clear()
