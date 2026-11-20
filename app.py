"""
Bank Branch Performance Analysis - Streamlit entry point.

    streamlit run app.py

Flow:  login gate  ->  sidebar (navigation + filters)  ->  cached filtered dataset  ->  selected page.
No dashboard content is rendered until a manager has authenticated.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import authentication as auth  # noqa: E402
from components.data_loader import load_dataset  # noqa: E402
from components.login_ui import render_first_time_setup, render_login  # noqa: E402
from components.sidebar import PAGES, render_sidebar  # noqa: E402
from components.styling import apply_styling  # noqa: E402
from config import settings  # noqa: E402
from database import db  # noqa: E402
from views import (branch_performance, customer_analysis, data_management, financial_analysis,  # noqa: E402
                   loan_analysis, overview, report_export, reports_insights)

st.set_page_config(page_title=settings.APP_TITLE, page_icon=settings.APP_ICON, layout="wide",
                   initial_sidebar_state="expanded")


@st.cache_resource
def _bootstrap() -> bool:
    """Create folders, database and tables once per server process.
    Demo data is loaded automatically only if the database has no business data."""
    settings.ensure_directories()
    db.init_db()
    from scripts.seed_database import has_business_data, seed
    if not has_business_data():
        seed(verbose=False)
    return True


def main() -> None:
    apply_styling()
    try:
        _bootstrap()
    except Exception as exc:  # noqa: BLE001
        st.error(f"The database could not be initialised: {exc}")
        st.stop()

    if not auth.is_authenticated(st.session_state):
        st.markdown("<style>section[data-testid='stSidebar']{display:none;}</style>", unsafe_allow_html=True)
        if auth.manager_count() == 0:
            render_first_time_setup()
        else:
            render_login()
        st.stop()

    if not auth.is_still_active(st.session_state):
        auth.logout_session(st.session_state)
        st.warning("Your account has been deactivated. Please contact the administrator.")
        st.stop()

    manager = st.session_state["manager"]
    page, filters = render_sidebar(manager)
    try:
        ds = load_dataset(filters)
    except db.DatabaseError as exc:
        st.error(f"Could not load data: {exc}")
        st.stop()

    pages = dict(zip(PAGES, [overview.render, branch_performance.render, financial_analysis.render,
                             customer_analysis.render, loan_analysis.render, reports_insights.render,
                             report_export.render, None]))
    try:
        if page == PAGES[-1]:
            data_management.render(ds, manager)
        else:
            pages[page](ds)
    except Exception as exc:  # noqa: BLE001 - never show a raw traceback to managers
        st.error("Something went wrong while building this page. Try widening the filters or "
                 "refreshing data from Data Management.")
        with st.expander("Technical details"):
            st.exception(exc)


main()
