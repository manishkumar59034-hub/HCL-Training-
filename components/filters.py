"""
Global filters (sidebar). Every option list cascades: choosing a Region narrows
States, which narrows Cities, which narrows Branches. The resulting Filters
object is passed to every query, so KPIs, charts, tables, rankings and insights
all respond to the same selection.
"""
from __future__ import annotations

import calendar
from datetime import date

import streamlit as st

from analytics.queries import Filters
from components.data_loader import data_version, filter_options

FILTER_KEYS = ["f_dates", "f_year", "f_month", "f_region", "f_state", "f_city", "f_branch", "f_status"]
MONTHS = ["All"] + [calendar.month_name[i] for i in range(1, 13)]


def reset_filters() -> None:
    for k in FILTER_KEYS:
        st.session_state.pop(k, None)


def _prune(key: str, options: list) -> None:
    """Drop stale selections that are no longer valid options (cascading filters)."""
    if key in st.session_state:
        st.session_state[key] = [v for v in st.session_state[key] if v in options]


def render_filters(manager=None) -> Filters:
    branches, (min_d, max_d) = filter_options(data_version())
    if branches.empty or min_d is None:
        st.sidebar.warning("No data loaded yet. Use Data Management to load demo data.")
        return Filters()

    sb = st.sidebar
    with sb.expander("🔎 Filters", expanded=True):
        picked = st.date_input("Reporting date range", value=(min_d, max_d), min_value=min_d,
                               max_value=max_d, key="f_dates", format="DD/MM/YYYY")
        start, end = (picked if isinstance(picked, (tuple, list)) and len(picked) == 2
                      else (min_d, max_d))

        years = ["All"] + [str(y) for y in range(min_d.year, max_d.year + 1)]
        c1, c2 = st.columns(2)
        year = c1.selectbox("Year", years, key="f_year")
        month_name = c2.selectbox("Month", MONTHS, key="f_month")

        scoped_branch = None
        if manager is not None and manager.role == "Branch Manager" and manager.assigned_branch_id:
            scoped_branch = manager.assigned_branch_id

        pool = branches if not scoped_branch else branches[branches["branch_id"] == scoped_branch]
        regions_opt = sorted(pool["region"].unique())
        _prune("f_region", regions_opt)
        regions = st.multiselect("Region", regions_opt, key="f_region", placeholder="All regions")
        p2 = pool[pool["region"].isin(regions)] if regions else pool

        states_opt = sorted(p2["state"].unique())
        _prune("f_state", states_opt)
        states = st.multiselect("State", states_opt, key="f_state", placeholder="All states")
        p3 = p2[p2["state"].isin(states)] if states else p2

        cities_opt = sorted(p3["city"].unique())
        _prune("f_city", cities_opt)
        cities = st.multiselect("City", cities_opt, key="f_city", placeholder="All cities")
        p4 = p3[p3["city"].isin(cities)] if cities else p3

        branch_labels = {f"{r.branch_name} ({r.branch_id})": r.branch_id for r in p4.itertuples()}
        if scoped_branch:
            st.caption(f"Your account is scoped to branch **{scoped_branch}**.")
            chosen_ids = [scoped_branch]
        else:
            _prune("f_branch", list(branch_labels))
            chosen = st.multiselect("Branch", list(branch_labels), key="f_branch", placeholder="All branches")
            chosen_ids = [branch_labels[c] for c in chosen]

        status_opt = sorted(branches["status"].unique())
        _prune("f_status", status_opt)
        statuses = st.multiselect("Branch status", status_opt, key="f_status", placeholder="All statuses")

        st.button("Reset filters", on_click=reset_filters, key="btn_reset_filters")

    if year != "All":
        y = int(year)
        start = max(start, date(y, 1, 1))
        end = min(end, date(y, 12, 31))
    month = MONTHS.index(month_name) if month_name != "All" else None

    return Filters(start_date=start, end_date=end, month=month, regions=list(regions),
                   states=list(states), cities=list(cities), branch_ids=chosen_ids,
                   branch_statuses=list(statuses))
