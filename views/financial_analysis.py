"""Page 3 - Financial Analysis."""
from __future__ import annotations

import streamlit as st

from analytics import financial_analysis as fa
from analytics import kpi_calculations as kpi
from components import charts
from components.kpi_cards import answer_cards, chart_note, kpi_row, page_header
from config import settings
from utils.formatting import fmt_inr, fmt_pct
from views.common import no_data, show

FORMULAS = """
| KPI | Formula |
|---|---|
| Net Profit | Revenue − Expenses |
| Profit Margin % | (Net Profit ÷ Revenue) × 100 |
| Target Achievement % | (Actual Revenue ÷ Revenue Target) × 100 |
| Revenue / Expense Growth % (MoM) | ((Latest month − Previous month) ÷ Previous month) × 100 |
| Period trend % | (Average of last 3 months − Average of first 3 months) ÷ Average of first 3 months × 100 |
| Expense Ratio % | (Expenses ÷ Revenue) × 100 |

Divisions by zero, or a missing previous month, are shown as **N/A** rather than an error or a misleading 0.
"""


def render(ds) -> None:
    page_header("Financial Analysis",
                "Track revenue, expenses, profitability, deposits and loan disbursement over time and by branch.")
    if no_data(ds):
        return
    f = kpi.financial_kpis(ds.financials)
    m = ds.monthly
    kpi_row([
        {"label": "Total Revenue", "value": fmt_inr(f["revenue"], short=True)},
        {"label": "Total Expenses", "value": fmt_inr(f["expenses"], short=True)},
        {"label": "Net Profit", "value": fmt_inr(f["profit"], short=True)},
        {"label": "Profit Margin", "value": fmt_pct(f["profit_margin"])},
        {"label": "Total Deposits", "value": fmt_inr(f["deposits"], short=True)},
        {"label": "Loan Disbursement", "value": fmt_inr(f["loan_disbursement"], short=True)},
        {"label": "Revenue Growth (MoM)", "value": fmt_pct(f["revenue_growth"], signed=True),
         "help_text": "Latest month vs previous month in the selection"},
        {"label": "Expense Growth (MoM)", "value": fmt_pct(f["expense_growth"], signed=True),
         "help_text": "Latest month vs previous month in the selection"},
    ])
    if f["months"] and f["months"] < 2:
        st.info("Only one month is selected, so month-over-month growth is shown as N/A.")

    c1, c2 = st.columns(2)
    with c1:
        show(charts.money_lines(m, "reporting_month", {"revenue": "Revenue", "expenses": "Expenses"},
                                "Revenue vs expenses trend"), "fa_rev_exp")
        rc, ec = kpi.period_change(m["revenue"]), kpi.period_change(m["expenses"])
        if rc is not None and ec is not None:
            chart_note(f"Revenue {fmt_pct(rc, signed=True)} vs expenses {fmt_pct(ec, signed=True)} across the period — "
                       + ("**expenses are growing faster**." if ec > rc else "**revenue is growing faster**."))
        show(charts.money_lines(m, "reporting_month", {"deposits": "Deposits"}, "Deposits trend"), "fa_dep")
    with c2:
        show(charts.money_lines(m, "reporting_month", {"profit": "Net profit"}, "Profit trend"), "fa_profit")
        if len(m):
            best = m.loc[m["profit"].idxmax()]
            chart_note(f"Best month: **{best['reporting_month']:%b %Y}** with {fmt_inr(best['profit'], short=True)} profit.")
        show(charts.money_lines(m, "reporting_month", {"loan_disbursement": "Loan disbursement"},
                                "Loan disbursement trend"), "fa_loan")

    c3, c4 = st.columns(2)
    with c3:
        show(charts.branch_bar(ds.summary, "profit", "Profit by branch", value_label="Net profit"), "fa_prof_branch")
    with c4:
        show(charts.branch_bar(ds.summary, "target_achievement", "Revenue vs target (achievement %)",
                               money=False, value_label="Achievement", suffix="%",
                               color_col="performance_category", color_map=settings.CATEGORY_COLORS,
                               ref=settings.HIGH_PERFORMER_THRESHOLD), "fa_rev_target")

    st.subheader("Analysis")
    answer_cards(fa.financial_answers(ds.financials, ds.summary))
    with st.expander("📐 KPI formulas used on this page"):
        st.markdown(FORMULAS)
