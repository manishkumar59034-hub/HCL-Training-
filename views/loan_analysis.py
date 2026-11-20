"""Page 5 - Loan Analysis."""
from __future__ import annotations

import streamlit as st

from analytics import kpi_calculations as kpi
from analytics import loan_analysis as la
from components import charts
from components.kpi_cards import answer_cards, chart_note, kpi_row, page_header
from config import settings
from utils.formatting import fmt_inr, fmt_number, fmt_pct
from views.common import show

DEFINITIONS = """
| Term | Meaning in this application |
|---|---|
| **Loan application** | Every record in the loan register, whatever its status |
| **Approved loan** | Status *Approved*, *Disbursed* or *Closed* |
| **Rejected loan** | Status *Rejected* |
| **Disbursed loan** | Status *Disbursed* or *Closed* — the money was actually paid out |
| **Outstanding** | Amount still owed on disbursed loans |
| **Default** | A disbursed loan whose repayment status is *Defaulted* |
| **Approval rate** | Approved ÷ total applications × 100 (pending applications are in the denominator) |
| **Default rate** | Defaulted ÷ disbursed loans × 100 |

*Total Loan Disbursement* on this page uses the same source as the Overview and Financial pages
(the monthly `branch_financials.loan_disbursement` figure), so the KPI matches everywhere.
The register-based disbursed amount is shown alongside for reconciliation.
"""

STATUS_COLORS = {"Disbursed": "#2a78d6", "Approved": "#1baf7a", "Pending": "#eda100",
                 "Rejected": "#eb6834", "Closed": "#6250d6"}


def render(ds) -> None:
    page_header("Loan Analysis",
                "Follow loans from application to approval, disbursement, repayment and default.")
    if ds.loans.empty:
        st.warning("No loan applications match the selected filters.")
        return
    k = kpi.loan_kpis(ds.loans)
    fin = kpi.financial_kpis(ds.financials)
    kpi_row([
        {"label": "Loan Applications", "value": fmt_number(k["applications"]),
         "delta_label": f"{k['pending']} pending decision"},
        {"label": "Approved Loans", "value": fmt_number(k["approved"])},
        {"label": "Rejected Loans", "value": fmt_number(k["rejected"])},
        {"label": "Approval Rate", "value": fmt_pct(k["approval_rate"])},
        {"label": "Total Loan Disbursement", "value": fmt_inr(fin["loan_disbursement"], short=True),
         "delta_label": f"Register: {fmt_inr(k['disbursed_amount'], short=True)} · {k['disbursed_count']} loans"},
        {"label": "Outstanding Loans", "value": fmt_inr(k["outstanding"], short=True)},
        {"label": "Default Rate", "value": fmt_pct(k["default_rate"]),
         "delta_label": f"{k['defaulted']} of {k['disbursed_count']} disbursed"},
        {"label": "Avg Interest (approved)", "value": fmt_pct(k["avg_interest"], decimals=2)},
    ])

    table = la.loan_branch_table(ds.loans)
    monthly = la.monthly_applications(ds.loans)
    c1, c2 = st.columns(2)
    with c1:
        show(charts.count_line(monthly, "month", {"applications": "Applications", "approved": "Approved",
                                                  "rejected": "Rejected"},
                               "Loan applications trend", "Loans"), "la_trend")
        types = la.distribution(ds.loans, "loan_type")
        show(charts.category_bar(types, "loan_type", "count", "Loan type distribution", "Applications"),
             "la_types")
        status = la.distribution(ds.loans, "loan_status")
        show(charts.category_bar(status, "loan_status", "count", "Loan status distribution", "Loans",
                                 color_map=STATUS_COLORS), "la_status")
    with c2:
        show(charts.grouped_branch_bar(table.sort_values("applications", ascending=False),
                                       {"applied_amount": "Applied", "disbursed_amount": "Disbursed"},
                                       "Loan amount by branch"), "la_amount")
        show(charts.branch_bar(table.assign(approved_n=table["approved"]), "approved_n",
                               "Approved loans by branch", money=False, value_label="Approved"), "la_approved")
        risky = table[table["disbursed_count"] >= 1]
        show(charts.branch_bar(risky, "default_rate", "Default rate by branch (%)", money=False,
                               value_label="Default rate", suffix="%", ref=settings.DEFAULT_RATE_THRESHOLD),
             "la_default")
        chart_note(f"Dotted line = {settings.DEFAULT_RATE_THRESHOLD:.0f}% risk threshold. Branches with very few "
                   "disbursed loans can show extreme rates — check the counts in the table below.")

    st.subheader("Approved vs rejected by branch")
    show(charts.grouped_branch_bar(table, {"approved": "Approved", "rejected": "Rejected"}, ""), "la_appr_rej")
    st.caption("Counts of loans (not amounts).")

    st.subheader("Business questions")
    answer_cards(la.loan_answers(ds.loans, table))
    with st.expander("Branch loan table"):
        view = table.drop(columns=["branch_id"]).rename(columns={
            "branch_name": "Branch", "region": "Region", "applications": "Applications", "approved": "Approved",
            "rejected": "Rejected", "approval_rate": "Approval %", "applied_amount": "Applied (₹)",
            "disbursed_amount": "Disbursed (₹)", "outstanding": "Outstanding (₹)", "defaulted": "Defaulted",
            "disbursed_count": "Disbursed loans", "default_rate": "Default %"})
        for c in ("Applied (₹)", "Disbursed (₹)", "Outstanding (₹)"):
            view[c] = view[c].map(lambda v: fmt_inr(v, short=True))
        for c in ("Approval %", "Default %"):
            view[c] = view[c].map(fmt_pct)
        st.dataframe(view, hide_index=True)
    with st.expander("📐 Loan definitions"):
        st.markdown(DEFINITIONS)
