"""Page 1 - Executive Overview."""
from __future__ import annotations

import streamlit as st

from analytics import branch_analysis as ba
from analytics import customer_analysis as ca
from analytics import insights as ins
from analytics import kpi_calculations as kpi
from components import charts
from components.kpi_cards import chart_note, kpi_row, page_header
from config import settings
from utils.formatting import fmt_inr, fmt_month, fmt_number, fmt_pct, fmt_score
from views.common import no_data, show


def render(ds) -> None:
    page_header("Executive Overview",
                "An at-a-glance view of overall bank performance for the selected period and branches.")
    if no_data(ds):
        return
    f = kpi.financial_kpis(ds.financials)
    c = kpi.customer_kpis(ds.customers, ds.filters.start_date, ds.feedback, ds.filters.month)

    kpi_row([
        {"label": "Total Branches", "value": fmt_number(len(ds.summary)),
         "delta_label": f"{int((ds.summary['performance_category'] == 'High Performer').sum())} on/above target"},
        {"label": "Total Customers", "value": fmt_number(c["total"]),
         "delta": c["growth"], "delta_label": "vs period start"},
        {"label": "Total Deposits", "value": fmt_inr(f["deposits"], short=True),
         "delta": f["deposit_growth"], "delta_label": "MoM"},
        {"label": "Total Loan Disbursement", "value": fmt_inr(f["loan_disbursement"], short=True),
         "delta_label": f"{f['months']} month(s)"},
        {"label": "Total Revenue", "value": fmt_inr(f["revenue"], short=True),
         "delta": f["revenue_growth"], "delta_label": "MoM"},
        {"label": "Total Expenses", "value": fmt_inr(f["expenses"], short=True),
         "delta": f["expense_growth"], "delta_label": "MoM", "good_when_up": False},
        {"label": "Net Profit", "value": fmt_inr(f["profit"], short=True),
         "delta_label": f"Margin {fmt_pct(f['profit_margin'])}"},
        {"label": "Avg Customer Satisfaction", "value": fmt_score(c["satisfaction"]),
         "delta_label": f"{fmt_number(len(ds.feedback))} responses"},
    ])

    col1, col2 = st.columns(2)
    with col1:
        show(charts.money_lines(ds.monthly, "reporting_month",
                                {"revenue": "Revenue", "revenue_target": "Revenue target"},
                                "A. Monthly revenue trend"), "ov_rev_trend")
        rc = kpi.period_change(ds.monthly["revenue"])
        chart_note(f"Revenue moved **{fmt_pct(rc, signed=True)}** from the start to the end of the period; "
                   f"overall target achievement is **{fmt_pct(f['target_achievement'])}**." if rc is not None
                   else "Select at least two months to see a trend.")
    with col2:
        show(charts.branch_bar(ds.summary, "revenue", "B. Revenue by branch", color_col="performance_category",
                               color_map=settings.CATEGORY_COLORS, value_label="Revenue", height=420),
             "ov_branch_rev")
        chart_note("Bar colour = performance category (High ≥100%, Average 80–99%, Low <80% of target).")

    show(charts.small_multiples(ds.monthly, "reporting_month",
                                {"deposits": "Deposits mobilised", "loan_disbursement": "Loans disbursed"},
                                "C. Deposits vs loan disbursement (monthly)"), "ov_dep_loan")
    ratio = kpi.safe_pct(f["loan_disbursement"], f["deposits"])
    chart_note(f"Panels use separate scales because deposits are far larger. For every ₹100 of deposits "
               f"mobilised, **₹{ratio:.2f}** was disbursed as loans." if ratio is not None else "")

    col3, col4 = st.columns(2)
    with col3:
        reg = ca.customers_by(ds.customers, "region")
        show(charts.category_bar(reg, "region", "customers", "D. Customer distribution by region",
                                 "Customers", color_map=settings.REGION_COLORS), "ov_cust_region")
        if len(reg):
            chart_note(f"**{reg.iloc[0]['region']}** has the largest customer base "
                       f"({fmt_pct(kpi.safe_pct(reg.iloc[0]['customers'], reg['customers'].sum()))} of customers).")
    with col4:
        metric_label = st.selectbox("Rank branches by", list(ba.RANK_METRICS), key="ov_rank_metric")
        metric = ba.RANK_METRICS[metric_label]
        money = metric in ("revenue", "profit", "deposits")
        top = ba.rank_branches(ds.summary, metric, settings.TOP_N)
        bottom = ba.rank_branches(ds.summary, metric, settings.TOP_N, ascending=True)
        t1, t2 = st.tabs([f"E. Top {settings.TOP_N}", f"F. Bottom {settings.TOP_N}"])
        with t1:
            show(charts.branch_bar(top, metric, "", money=money, value_label=metric_label, height=280),
                 "ov_top5")
        with t2:
            show(charts.branch_bar(bottom, metric, "", money=money, value_label=metric_label, height=280),
                 "ov_bottom5")

    st.subheader("Overview insights")
    h = ins.overview_highlights(ds.summary, ds.financials)
    if not h:
        return
    low = h["lowest_achievement"]
    below, rising = h["below_target"], h["rising_expenses"]
    kpi_row([
        {"label": "Highest revenue branch", "value": h["highest_revenue"]["branch_name"],
         "delta_label": fmt_inr(h["highest_revenue"]["revenue"], short=True)},
        {"label": "Highest profit branch", "value": h["highest_profit"]["branch_name"],
         "delta_label": fmt_inr(h["highest_profit"]["profit"], short=True)},
        {"label": "Lowest target achievement", "value": low["branch_name"] if low is not None else "N/A",
         "delta_label": fmt_pct(low["target_achievement"]) if low is not None else ""},
    ], per_row=3)
    kpi_row([
        {"label": "Total revenue growth", "value": fmt_pct(h["revenue_growth"], signed=True),
         "delta_label": f"{fmt_month(h['first_month'])} → {fmt_month(h['last_month'])} (last 3 vs first 3 months)"},
        {"label": "Branches below target", "value": f"{len(below)} of {len(ds.summary)}",
         "delta_label": ", ".join(below.sort_values("target_achievement")["branch_name"].head(3))
         + (" …" if len(below) > 3 else "")},
        {"label": "Branches with increasing expenses", "value": f"{len(rising)}",
         "delta_label": ("Expenses outpacing revenue: " + ", ".join(rising["branch_name"].head(3))
                         + (" …" if len(rising) > 3 else "")) if len(rising) else "None"},
    ], per_row=3)
