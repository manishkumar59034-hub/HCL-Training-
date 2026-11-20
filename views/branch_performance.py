"""Page 2 - Branch Performance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from analytics import branch_analysis as ba
from analytics import kpi_calculations as kpi
from components import charts
from components.kpi_cards import chart_note, kpi_row, page_header
from components.tables import show_branch_table
from config import settings
from utils.formatting import fmt_inr, fmt_number, fmt_pct, fmt_score
from views.common import no_data, show


def _thresholds() -> None:
    with st.expander("⚙️ Performance category thresholds"):
        c1, c2 = st.columns(2)
        high = c1.number_input("High Performer: achievement ≥ (%)", 50.0, 200.0,
                               float(st.session_state.get("threshold_high", settings.HIGH_PERFORMER_THRESHOLD)), 5.0)
        avg = c2.number_input("Average Performer: achievement ≥ (%)", 10.0, 199.0,
                              float(st.session_state.get("threshold_avg", settings.AVERAGE_PERFORMER_THRESHOLD)), 5.0)
        if avg >= high:
            st.error("The Average threshold must be lower than the High threshold.")
        elif (high, avg) != (st.session_state.get("threshold_high", settings.HIGH_PERFORMER_THRESHOLD),
                             st.session_state.get("threshold_avg", settings.AVERAGE_PERFORMER_THRESHOLD)):
            st.session_state["threshold_high"], st.session_state["threshold_avg"] = high, avg
            st.rerun()
        st.caption(f"Current rule: High ≥ {high:.0f}% · Average {avg:.0f}–{high:.0f}% · Low < {avg:.0f}% "
                   "(Target Achievement % = Actual Revenue ÷ Revenue Target × 100). Defaults are set in config/settings.py.")


def render(ds) -> None:
    page_header("Branch Performance",
                "Compare branches on revenue, profit, targets and customer metrics, then drill into any branch.")
    _thresholds()
    if no_data(ds):
        return
    s = ds.summary
    k = ba.branch_kpis(s)
    kpi_row([
        {"label": "Total Branches", "value": fmt_number(k["branches"])},
        {"label": "Avg Revenue / Branch", "value": fmt_inr(k["avg_revenue"], short=True)},
        {"label": "Avg Profit / Branch", "value": fmt_inr(k["avg_profit"], short=True)},
        {"label": "Avg Target Achievement", "value": fmt_pct(k["avg_achievement"]),
         "help_text": "Total revenue ÷ total target for the selected branches"},
        {"label": "Underperforming Branches", "value": fmt_number(k["underperforming"]),
         "delta_label": f"{k['high_performers']} high performers"},
    ], per_row=5)

    st.subheader("Branch performance table")
    show_branch_table(s)

    tabs = st.tabs(["Revenue by branch", "Profit by branch", "Revenue vs target", "Branch ranking",
                    "Regional performance"])
    with tabs[0]:
        show(charts.branch_bar(s, "revenue", "Revenue by branch", value_label="Revenue"), "bp_rev")
    with tabs[1]:
        show(charts.branch_bar(s, "profit", "Net profit by branch", value_label="Net profit"), "bp_profit")
        neg = s[s["profit"] < 0]
        chart_note(f"**{len(neg)}** branch(es) made a loss in the period." if len(neg)
                   else "Every selected branch was profitable in the period.")
    with tabs[2]:
        show(charts.grouped_branch_bar(s.sort_values("target_achievement", ascending=False),
                                       {"revenue": "Actual revenue", "revenue_target": "Revenue target"},
                                       "Actual revenue vs target (sorted by achievement)"), "bp_rev_target")
        show(charts.branch_bar(s, "target_achievement", "Target achievement %", money=False,
                               color_col="performance_category", color_map=settings.CATEGORY_COLORS,
                               value_label="Achievement", suffix="%",
                               ref=st.session_state.get("threshold_high", settings.HIGH_PERFORMER_THRESHOLD)),
             "bp_ach")
    with tabs[3]:
        metric_label = st.selectbox("Ranking metric", list(ba.RANK_METRICS), key="bp_rank_metric")
        metric = ba.RANK_METRICS[metric_label]
        ranked = ba.rank_branches(s, metric, n=len(s)).reset_index(drop=True)
        ranked.insert(0, "Rank", range(1, len(ranked) + 1))
        fmt = (lambda v: fmt_inr(v)) if metric in ("revenue", "profit", "deposits") else (
            (lambda v: fmt_pct(v)) if metric in ("profit_margin", "target_achievement") else (
                (lambda v: fmt_score(v)) if metric == "satisfaction" else (lambda v: fmt_number(v))))
        view = ranked[["Rank", "branch_name", "city", "region", metric, "performance_category"]].copy()
        view[metric] = view[metric].map(fmt)
        st.dataframe(view.rename(columns={"branch_name": "Branch", "city": "City", "region": "Region",
                                          metric: metric_label, "performance_category": "Category"}),
                     hide_index=True, height=min(740, 36 * len(view) + 40))
    with tabs[4]:
        reg = ba.regional_summary(s)
        c1, c2 = st.columns(2)
        with c1:
            show(charts.category_bar(reg, "region", "revenue", "Revenue by region", "Revenue",
                                     color_map=settings.REGION_COLORS, money=True), "bp_reg_rev")
        with c2:
            show(charts.category_bar(reg, "region", "target_achievement", "Target achievement % by region",
                                     "Achievement %", color_map=settings.REGION_COLORS), "bp_reg_ach")
        st.dataframe(pd.DataFrame({
            "Region": reg["region"], "Branches": reg["branches"],
            "Revenue": reg["revenue"].map(lambda v: fmt_inr(v, short=True)),
            "Profit": reg["profit"].map(lambda v: fmt_inr(v, short=True)),
            "Profit Margin": reg["profit_margin"].map(fmt_pct),
            "Target Achievement": reg["target_achievement"].map(fmt_pct),
            "Customers": reg["customers"].map(fmt_number)}), hide_index=True)
        if len(reg) >= 2:
            chart_note(f"**{reg.iloc[0]['region']}** generates the most revenue; "
                       f"best achievement: **{reg.sort_values('target_achievement').iloc[-1]['region']}**, "
                       f"weakest: **{reg.sort_values('target_achievement').iloc[0]['region']}**.")

    _branch_details(ds)


def _branch_details(ds) -> None:
    st.subheader("Branch details")
    s = ds.summary
    labels = {f"{r.branch_name} ({r.branch_id})": r.branch_id for r in s.sort_values("branch_name").itertuples()}
    choice = st.selectbox("Select a branch", list(labels), key="bp_detail_branch")
    bid = labels[choice]
    row = s[s["branch_id"] == bid].iloc[0]
    st.markdown(f"**{row['branch_name']}** · {row['city']}, {row['state']} · {row['region']} region · "
                f"{row['branch_type']} · Status: {row['status']} · Category: **{row['performance_category']}**")
    kpi_row([
        {"label": "Revenue", "value": fmt_inr(row["revenue"], short=True)},
        {"label": "Net Profit", "value": fmt_inr(row["profit"], short=True),
         "delta_label": f"Margin {fmt_pct(row['profit_margin'])}"},
        {"label": "Target Achievement", "value": fmt_pct(row["target_achievement"])},
        {"label": "Customers", "value": fmt_number(row["customers"])},
        {"label": "Satisfaction", "value": fmt_score(row["satisfaction"])},
    ], per_row=5)

    bm = ba.branch_monthly(ds.financials, bid)
    c1, c2 = st.columns(2)
    with c1:
        show(charts.money_lines(bm, "reporting_month", {"revenue": "Revenue", "revenue_target": "Target"},
                                "Revenue trend"), "bd_rev")
        show(charts.money_lines(bm, "reporting_month", {"deposits": "Deposits"}, "Deposit trend"), "bd_dep")
        show(charts.pct_line(bm, "reporting_month", "target_achievement", "Monthly target achievement",
                             "Achievement", ref=100), "bd_ach")
    with c2:
        show(charts.money_lines(bm, "reporting_month", {"profit": "Net profit"}, "Profit trend"), "bd_profit")
        cust = ds.customers[ds.customers["branch_id"] == bid]
        growth = ba.customer_growth_monthly(cust, bm["reporting_month"])
        show(charts.count_line(growth, "month", {"total_customers": "Customer base"}, "Customer growth",
                               "Customers"), "bd_cust")
        loans = ds.loans[ds.loans["branch_id"] == bid]
        lk = kpi.loan_kpis(loans)
        st.markdown("**Loan performance**")
        kpi_row([
            {"label": "Applications", "value": fmt_number(lk["applications"])},
            {"label": "Approval rate", "value": fmt_pct(lk["approval_rate"])},
            {"label": "Default rate", "value": fmt_pct(lk["default_rate"])},
        ], per_row=3)
        st.caption(f"Disbursed {fmt_inr(lk['disbursed_amount'], short=True)} · "
                   f"Outstanding {fmt_inr(lk['outstanding'], short=True)} · "
                   f"{lk['defaulted']} defaulted of {lk['disbursed_count']} disbursed.")

    st.markdown("**Comparison with bank-wide average** (average across the selected branches)")
    comp = ba.compare_with_bank(s, bid)
    if not comp.empty:
        def f(v, kind):
            return {"currency": lambda x: fmt_inr(x, short=True), "pct": fmt_pct,
                    "number": fmt_number, "score": fmt_score}[kind](v)
        view = pd.DataFrame({
            "Metric": comp["Metric"],
            "This branch": [f(v, k) for v, k in zip(comp["Branch"], comp["kind"])],
            "Bank average": [f(v, k) for v, k in zip(comp["Bank Average"], comp["kind"])],
            "Difference": [fmt_pct(d, signed=True) if k in ("currency", "number") else
                           (f"{d:+.1f} pts" if k == "pct" and d is not None and not pd.isna(d) else
                            (f"{d:+.2f}" if d is not None and not pd.isna(d) else "N/A"))
                           for d, k in zip(comp["Difference"], comp["kind"])],
        })
        st.dataframe(view, hide_index=True)
        st.caption("Difference: % above/below average for amounts and counts; percentage points for rates; "
                   "score points for satisfaction. For default rate, lower is better.")
