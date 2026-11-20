"""
Customer analysis: distributions, acquisition speed and satisfaction.
Only synthetic customer IDs are ever shown - no personal names.
"""
from __future__ import annotations

import pandas as pd

from analytics import kpi_calculations as kpi
from config import settings
from utils.formatting import fmt_number, fmt_pct, fmt_score


def customers_by(customers: pd.DataFrame, column: str) -> pd.DataFrame:
    if customers is None or customers.empty:
        return pd.DataFrame(columns=[column, "customers"])
    return (customers.groupby(column).size().rename("customers").reset_index()
            .sort_values("customers", ascending=False))


def acquisition_by_branch(customers: pd.DataFrame, period_start, month: int | None = None) -> pd.DataFrame:
    """Per branch: base at period start, new customers in period, growth %."""
    if customers is None or customers.empty:
        return pd.DataFrame(columns=["branch_id", "branch_name", "region", "total", "new",
                                     "previous", "growth"])
    start = pd.Timestamp(period_start) if period_start is not None else customers["join_date"].min()
    rows = []
    for (bid, name, region), grp in customers.groupby(["branch_id", "branch_name", "region"]):
        k = kpi.customer_kpis(grp, start, month=month)
        rows.append({"branch_id": bid, "branch_name": name, "region": region, "total": k["total"],
                     "new": k["new"], "previous": k["previous"], "growth": k["growth"]})
    return pd.DataFrame(rows).sort_values("total", ascending=False).reset_index(drop=True)


def acquisition_by_region(acq: pd.DataFrame) -> pd.DataFrame:
    if acq is None or acq.empty:
        return pd.DataFrame(columns=["region", "total", "new", "previous", "growth"])
    reg = acq.groupby("region")[["total", "new", "previous"]].sum().reset_index()
    reg["growth"] = [kpi.growth_rate(t, p) if p else None for t, p in zip(reg["total"], reg["previous"])]
    return reg.sort_values("growth", ascending=False, na_position="last").reset_index(drop=True)


def satisfaction_by_branch(feedback: pd.DataFrame) -> pd.DataFrame:
    if feedback is None or feedback.empty:
        return pd.DataFrame(columns=["branch_id", "branch_name", "satisfaction", "responses"])
    return (feedback.groupby(["branch_id", "branch_name"])["satisfaction_score"]
            .agg(satisfaction="mean", responses="count").reset_index()
            .sort_values("satisfaction"))


def satisfaction_trend(feedback: pd.DataFrame) -> pd.DataFrame:
    if feedback is None or feedback.empty:
        return pd.DataFrame(columns=["month", "satisfaction"])
    fb = feedback.assign(month=feedback["feedback_date"].dt.to_period("M").dt.to_timestamp())
    return fb.groupby("month")["satisfaction_score"].mean().rename("satisfaction").reset_index()


def customer_answers(customers: pd.DataFrame, feedback: pd.DataFrame, acq: pd.DataFrame,
                     growth_monthly: pd.DataFrame) -> list[dict]:
    if customers is None or customers.empty:
        return [{"question": "Customer analysis", "answer": "No customers for the selected filters.",
                 "status": "info"}]
    out = []
    top = acq.head(3)
    out.append({"question": "Which branches have the largest customer base?",
                "answer": ", ".join(f"**{r.branch_name}** ({fmt_number(r.total)})" for r in top.itertuples()),
                "status": "info"})
    fast = acq.dropna(subset=["growth"]).sort_values("growth", ascending=False).head(3)
    out.append({"question": "Which branches are acquiring customers faster?",
                "answer": (", ".join(f"**{r.branch_name}** ({fmt_pct(r.growth, signed=True)}, "
                                     f"{fmt_number(r.new)} new)" for r in fast.itertuples())
                           if len(fast) else "Growth cannot be calculated (no customer base before the period)."),
                "status": "good"})
    reg = acquisition_by_region(acq).dropna(subset=["growth"])
    if len(reg):
        best = reg.iloc[0]
        out.append({"question": "Which regions have the highest customer growth?",
                    "answer": f"**{best['region']}** leads with {fmt_pct(best['growth'], signed=True)}; "
                              + ", ".join(f"{r.region} {fmt_pct(r.growth, signed=True)}"
                                          for r in reg.iloc[1:].itertuples()),
                    "status": "good"})
    sat = satisfaction_by_branch(feedback)
    if len(sat):
        low = sat.head(3)
        out.append({"question": "Where is customer satisfaction lowest?",
                    "answer": ", ".join(f"**{r.branch_name}** ({fmt_score(r.satisfaction)})" for r in low.itertuples()),
                    "status": "warn" if low.iloc[0]["satisfaction"] < settings.LOW_SATISFACTION_THRESHOLD else "info"})
    if growth_monthly is not None and len(growth_monthly) >= 2:
        start_base = growth_monthly["total_customers"].iloc[0] - growth_monthly["new_customers"].iloc[0]
        g = kpi.growth_rate(growth_monthly["total_customers"].iloc[-1], start_base) if start_base else None
        nm = growth_monthly["new_customers"]
        half = len(nm) // 2
        slowing = half >= 1 and nm.iloc[half:].mean() < nm.iloc[:half].mean() * 0.9
        out.append({"question": "Are customer numbers increasing or decreasing?",
                    "answer": (f"The customer base grew {fmt_pct(g, signed=True)} over the selected months. "
                               + ("New-customer acquisition is **slowing** in the second half of the period."
                                  if slowing else "New-customer acquisition is steady or improving.")),
                    "status": "warn" if slowing else "good"})
    return out
