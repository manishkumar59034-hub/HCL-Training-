"""Page 6 - Reports & Insights (all insights generated from current filtered data)."""
from __future__ import annotations

import streamlit as st

from analytics import insights as ins
from components.kpi_cards import insight_card, kpi_row, page_header
from views.common import no_data


def render(ds) -> None:
    page_header("Reports & Insights",
                "Automatically generated findings and recommendations, based on business rules applied to the filtered data.")
    if no_data(ds):
        return
    items = ins.generate_insights(ds.summary, ds.financials, ds.feedback, ds.customer_growth)
    positives = [i for i in items if i.category == "Positive"]
    warnings = sorted([i for i in items if i.category == "Warning"], key=lambda i: -i.severity)
    recs = ins.recommendations(items)
    kpi_row([
        {"label": "Positive insights", "value": str(len(positives))},
        {"label": "Warnings", "value": str(len(warnings)),
         "delta_label": f"{sum(1 for w in warnings if w.severity >= 3)} high priority"},
        {"label": "Branches needing attention",
         "value": str(len({w.branch for w in warnings if w.branch not in ('Bank-wide', 'Multiple')}))},
        {"label": "Recommended actions", "value": str(len(recs))},
    ])
    st.caption("Insights recalculate whenever filters change. Each one states the evidence that triggered it. "
               "Rules and thresholds are documented in docs/kpi_definitions.md.")

    t1, t2, t3, t4 = st.tabs(["✅ Positive", "⚠️ Warnings", "🧭 Recommendations", "📋 All insights (table)"])
    with t1:
        if not positives:
            st.info("No positive insights for the current selection.")
        for i in positives:
            insight_card(i.category, i.title, i.branch, i.evidence)
    with t2:
        if not warnings:
            st.success("No warnings — all selected branches are within the defined thresholds.")
        else:
            branches = sorted({w.branch for w in warnings})
            pick = st.selectbox("Show warnings for", ["All branches"] + branches, key="ri_branch")
            for i in warnings:
                if pick in ("All branches", i.branch):
                    insight_card(i.category, i.title, i.branch, i.evidence, i.action)
    with t3:
        if not recs:
            st.info("No recommendations — nothing crossed a warning threshold.")
        for r in recs:
            st.markdown(f"**{r['issue']}** — {len(r['branches'])} affected: {', '.join(r['branches'])}")
            st.markdown(f"> {r['action']}")
    with t4:
        st.dataframe(ins.insights_frame(items), hide_index=True, height=520)
