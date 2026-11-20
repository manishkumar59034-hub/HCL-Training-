"""Page 4 - Customer Analysis (synthetic identifiers only; no personal data shown)."""
from __future__ import annotations

import streamlit as st

from analytics import customer_analysis as ca
from analytics import kpi_calculations as kpi
from components import charts
from components.kpi_cards import answer_cards, chart_note, kpi_row, page_header
from config import settings
from utils.formatting import fmt_number, fmt_pct, fmt_score
from views.common import no_data, show


def render(ds) -> None:
    page_header("Customer Analysis",
                "Understand the size, growth, mix and satisfaction of the customer base across branches.")
    if no_data(ds):
        return
    c = kpi.customer_kpis(ds.customers, ds.filters.start_date, ds.feedback, ds.filters.month)
    kpi_row([
        {"label": "Total Customers", "value": fmt_number(c["total"]),
         "help_text": "Customers who had joined by the end of the selected period"},
        {"label": "New Customers", "value": fmt_number(c["new"]),
         "help_text": "Joined within the selected period"},
        {"label": "Active Customers", "value": fmt_number(c["active"]),
         "delta_label": f"{fmt_pct(kpi.safe_pct(c['active'], c['total']))} of total"},
        {"label": "Customer Growth", "value": fmt_pct(c["growth"], signed=True),
         "help_text": "(Customers at period end − customers at period start) ÷ customers at period start × 100"},
        {"label": "Avg Satisfaction", "value": fmt_score(c["satisfaction"])},
    ], per_row=5)

    growth = ds.customer_growth
    acq = ca.acquisition_by_branch(ds.customers, ds.filters.start_date, ds.filters.month)
    c1, c2 = st.columns(2)
    with c1:
        show(charts.count_line(growth, "month", {"total_customers": "Customer base"},
                               "Customer growth trend", "Customers"), "ca_growth")
        show(charts.count_line(growth, "month", {"new_customers": "New customers"},
                               "New customers by month", "Customers", bars=True), "ca_new")
        nm = growth["new_customers"] if len(growth) else []
        if len(nm) >= 2:
            chart_note(f"Average **{nm.mean():.0f}** new customers per month; peak "
                       f"{int(nm.max())} in {growth.loc[nm.idxmax(), 'month']:%b %Y}.")
    with c2:
        show(charts.branch_bar(acq.assign(customers=acq["total"]), "customers", "Customers by branch",
                               money=False, value_label="Customers"), "ca_branch")
    c3, c4 = st.columns(2)
    with c3:
        reg = ca.customers_by(ds.customers, "region")
        show(charts.category_bar(reg, "region", "customers", "Customers by region", "Customers",
                                 color_map=settings.REGION_COLORS), "ca_region")
        types = ca.customers_by(ds.customers, "customer_type")
        show(charts.category_bar(types, "customer_type", "customers", "Customer type distribution",
                                 "Customers"), "ca_types")
    with c4:
        sat = ca.satisfaction_by_branch(ds.feedback)
        show(charts.branch_bar(sat, "satisfaction", "Customer satisfaction by branch (1–5)", money=False,
                               value_label="Avg score", ref=settings.LOW_SATISFACTION_THRESHOLD), "ca_sat")
        chart_note(f"Dotted line = low-satisfaction threshold ({settings.LOW_SATISFACTION_THRESHOLD}).")

    st.subheader("Business questions")
    answer_cards(ca.customer_answers(ds.customers, ds.feedback, acq, growth))

    with st.expander("Customer acquisition by branch (table)"):
        view = acq.rename(columns={"branch_name": "Branch", "region": "Region", "total": "Customers (period end)",
                                   "new": "New in period", "previous": "Customers (period start)",
                                   "growth": "Growth %"}).drop(columns=["branch_id"])
        view["Growth %"] = view["Growth %"].map(lambda v: fmt_pct(v, signed=True))
        st.dataframe(view, hide_index=True)
        st.caption("Only aggregate counts are shown. Customer records use synthetic IDs such as CU000123.")
