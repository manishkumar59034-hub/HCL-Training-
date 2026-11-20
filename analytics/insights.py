"""
Rule-based business insight engine.

Every insight is computed from the CURRENT FILTERED data and carries:
  category   : Positive | Warning
  title      : short headline
  branch     : branch concerned (or "Bank-wide")
  evidence   : the numbers that triggered the rule (why it was generated)
  action     : recommended next step (for warnings)

Rules and thresholds come from config/settings.py, so they are easy to explain
and to change. This is descriptive / diagnostic analytics - no predictions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from analytics import kpi_calculations as kpi
from config import settings
from utils.formatting import fmt_inr, fmt_pct, fmt_score

RECOMMENDATIONS = {
    "low_target": "Review the branch's sales strategy, customer acquisition activity, and local business opportunities.",
    "expense_growth": "Investigate operating expenses and identify opportunities for cost optimization.",
    "low_satisfaction": "Review service quality, customer waiting time, and unresolved customer complaints.",
    "satisfaction_drop": "Review recent service changes and complaint categories; schedule a service-quality audit.",
    "high_default": "Review loan monitoring and risk management practices.",
    "deposit_decline": "Investigate customer retention and deposit acquisition.",
    "profit_decline": "Analyse revenue mix and cost base to identify what is eroding profit.",
    "high_expense_ratio": "Benchmark the branch's cost structure against peers of the same type and region.",
    "customer_slowdown": "Strengthen customer acquisition campaigns and referral programmes.",
}


@dataclass
class Insight:
    category: str          # "Positive" | "Warning"
    title: str
    branch: str
    evidence: str
    action: str = ""
    severity: int = 1      # 1 = info, 2 = moderate, 3 = high (for sorting)
    rule: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _feedback_change(feedback: pd.DataFrame) -> pd.DataFrame:
    """Per branch: change in average monthly score (points), last 3 vs first 3 months."""
    if feedback is None or feedback.empty:
        return pd.DataFrame(columns=["branch_id", "score_change"])
    fb = feedback.assign(month=feedback["feedback_date"].dt.to_period("M").dt.to_timestamp())
    monthly = fb.groupby(["branch_id", "month"])["satisfaction_score"].mean().reset_index()
    rows = []
    for bid, grp in monthly.groupby("branch_id"):
        s = grp.sort_values("month")["satisfaction_score"]
        if len(s) >= 6:
            rows.append({"branch_id": bid, "score_change": s.iloc[-3:].mean() - s.iloc[:3].mean()})
        elif len(s) >= 2:
            rows.append({"branch_id": bid, "score_change": s.iloc[-1] - s.iloc[0]})
    return pd.DataFrame(rows, columns=["branch_id", "score_change"])


def generate_insights(summary: pd.DataFrame, fin: pd.DataFrame, feedback: pd.DataFrame,
                      customer_growth: pd.DataFrame | None = None) -> list[Insight]:
    insights: list[Insight] = []
    if summary is None or summary.empty:
        return insights
    monthly = kpi.monthly_financials(fin)
    n_months = len(monthly)

    # ------------------------------------------------------------ positive
    top_rev = summary.sort_values("revenue", ascending=False).iloc[0]
    if top_rev["revenue"] > 0:
        insights.append(Insight("Positive", "Highest revenue branch", top_rev["branch_name"],
                                f"Revenue of {fmt_inr(top_rev['revenue'], short=True)} "
                                f"({fmt_pct(kpi.safe_pct(top_rev['revenue'], summary['revenue'].sum()))} of selected total).",
                                rule="top_revenue"))
    top_profit = summary.sort_values("profit", ascending=False).iloc[0]
    if top_profit["profit"] > 0:
        insights.append(Insight("Positive", "Highest profit branch", top_profit["branch_name"],
                                f"Net profit of {fmt_inr(top_profit['profit'], short=True)} at a "
                                f"{fmt_pct(top_profit['profit_margin'])} margin.", rule="top_profit"))
    exceeding = summary[summary["target_achievement"] >= settings.HIGH_PERFORMER_THRESHOLD]
    if len(exceeding):
        names = ", ".join(exceeding.sort_values("target_achievement", ascending=False)["branch_name"].head(5))
        insights.append(Insight("Positive", f"{len(exceeding)} branch(es) exceeding target", "Multiple",
                                f"At or above {settings.HIGH_PERFORMER_THRESHOLD:.0f}% of revenue target: {names}"
                                + (" …" if len(exceeding) > 5 else "."), rule="exceeding_target"))
    if n_months >= 2:
        rev_change = kpi.period_change(monthly["revenue"])
        if rev_change is not None and rev_change > 0:
            insights.append(Insight("Positive", "Revenue is growing", "Bank-wide",
                                    f"Monthly revenue up {fmt_pct(rev_change, signed=True)} across the period "
                                    f"({fmt_inr(monthly['revenue'].iloc[0], short=True)} → "
                                    f"{fmt_inr(monthly['revenue'].iloc[-1], short=True)}).", rule="revenue_growth"))
        dep_change = kpi.period_change(monthly["deposits"])
        if dep_change is not None and dep_change > 0:
            insights.append(Insight("Positive", "Deposits are increasing", "Bank-wide",
                                    f"Monthly deposit mobilisation up {fmt_pct(dep_change, signed=True)} across the period.",
                                    rule="deposit_growth"))
    if customer_growth is not None and len(customer_growth) >= 2:
        start_base = int(customer_growth["total_customers"].iloc[0] - customer_growth["new_customers"].iloc[0])
        g = kpi.growth_rate(customer_growth["total_customers"].iloc[-1], start_base) if start_base else None
        if g is not None and g > 0:
            insights.append(Insight("Positive", "Customer base is growing", "Bank-wide",
                                    f"Customers grew {fmt_pct(g, signed=True)} from "
                                    f"{start_base:,} at the start of the period to "
                                    f"{customer_growth['total_customers'].iloc[-1]:,} over the selected months.",
                                    rule="customer_growth"))
    best_sat = summary.dropna(subset=["satisfaction"]).sort_values("satisfaction", ascending=False)
    if len(best_sat) and best_sat.iloc[0]["satisfaction"] >= 4.0:
        insights.append(Insight("Positive", "Highest customer satisfaction", best_sat.iloc[0]["branch_name"],
                                f"Average score {fmt_score(best_sat.iloc[0]['satisfaction'])}.", rule="top_satisfaction"))

    # ------------------------------------------------------------ warnings (per branch)
    sat_change = _feedback_change(feedback).set_index("branch_id")["score_change"].to_dict()
    for r in summary.itertuples():
        name = r.branch_name
        ach = r.target_achievement
        if ach is not None and not pd.isna(ach) and ach < settings.AVERAGE_PERFORMER_THRESHOLD:
            insights.append(Insight("Warning", "Branch below target", name,
                                    f"Target achievement is {fmt_pct(ach)} (below the "
                                    f"{settings.AVERAGE_PERFORMER_THRESHOLD:.0f}% low-performer threshold); "
                                    f"revenue {fmt_inr(r.revenue, short=True)} vs target {fmt_inr(r.revenue_target, short=True)}.",
                                    RECOMMENDATIONS["low_target"], 3, "low_target"))
        rc, ec = r.revenue_change, r.expense_change
        if rc is not None and ec is not None and not pd.isna(rc) and not pd.isna(ec) and ec > rc + 3 and ec > 0:
            insights.append(Insight("Warning", "Expenses rising faster than revenue", name,
                                    f"Expenses changed {fmt_pct(ec, signed=True)} vs revenue {fmt_pct(rc, signed=True)} "
                                    "(last 3 months vs first 3 months of the period).",
                                    RECOMMENDATIONS["expense_growth"], 2, "expense_growth"))
        pc = r.profit_change
        if pc is not None and not pd.isna(pc) and pc < -5:
            insights.append(Insight("Warning", "Profit declining", name,
                                    f"Monthly profit changed {fmt_pct(pc, signed=True)} across the period.",
                                    RECOMMENDATIONS["profit_decline"], 2, "profit_decline"))
        dc = r.deposit_change
        if dc is not None and not pd.isna(dc) and dc < 0:
            insights.append(Insight("Warning", "Deposit growth is negative", name,
                                    f"Monthly deposits changed {fmt_pct(dc, signed=True)} across the period.",
                                    RECOMMENDATIONS["deposit_decline"], 2, "deposit_decline"))
        er = r.expense_ratio
        if er is not None and not pd.isna(er) and er > settings.HIGH_EXPENSE_RATIO_THRESHOLD:
            insights.append(Insight("Warning", "Unusually high expenses", name,
                                    f"Expenses are {fmt_pct(er)} of revenue (threshold "
                                    f"{settings.HIGH_EXPENSE_RATIO_THRESHOLD:.0f}%).",
                                    RECOMMENDATIONS["high_expense_ratio"], 2, "high_expense_ratio"))
        sat = r.satisfaction
        if sat is not None and not pd.isna(sat) and sat < settings.LOW_SATISFACTION_THRESHOLD:
            insights.append(Insight("Warning", "Low customer satisfaction", name,
                                    f"Average score {fmt_score(sat)} is below the "
                                    f"{settings.LOW_SATISFACTION_THRESHOLD} threshold.",
                                    RECOMMENDATIONS["low_satisfaction"], 2, "low_satisfaction"))
        chg = sat_change.get(r.branch_id)
        if chg is not None and chg <= -0.25:
            insights.append(Insight("Warning", "Customer satisfaction decreasing", name,
                                    f"Average monthly score fell by {abs(chg):.2f} points across the period.",
                                    RECOMMENDATIONS["satisfaction_drop"], 2, "satisfaction_drop"))
        dr = getattr(r, "default_rate", None)
        n_disb = getattr(r, "disbursed_loans", 0) or 0
        if dr is not None and not pd.isna(dr) and n_disb >= 5 and dr > settings.DEFAULT_RATE_THRESHOLD:
            insights.append(Insight("Warning", "High loan default rate", name,
                                    f"{fmt_pct(dr)} of disbursed loans have defaulted "
                                    f"({int(n_disb)} disbursed; threshold {settings.DEFAULT_RATE_THRESHOLD:.0f}%).",
                                    RECOMMENDATIONS["high_default"], 3, "high_default"))

    # ------------------------------------------------------------ warnings (bank-wide)
    if customer_growth is not None and len(customer_growth) >= 4:
        nm = customer_growth["new_customers"]
        half = len(nm) // 2
        first, second = nm.iloc[:half].mean(), nm.iloc[half:].mean()
        if first > 0 and second < first * 0.9:
            insights.append(Insight("Warning", "Customer growth slowing", "Bank-wide",
                                    f"Average new customers per month fell from {first:.0f} to {second:.0f} "
                                    "between the first and second half of the period.",
                                    RECOMMENDATIONS["customer_slowdown"], 2, "customer_slowdown"))
    if n_months >= 2:
        rc, ec = kpi.period_change(monthly["revenue"]), kpi.period_change(monthly["expenses"])
        if rc is not None and ec is not None and ec > rc + 1:
            insights.append(Insight("Warning", "Bank-wide expenses rising faster than revenue", "Bank-wide",
                                    f"Expenses {fmt_pct(ec, signed=True)} vs revenue {fmt_pct(rc, signed=True)}.",
                                    RECOMMENDATIONS["expense_growth"], 2, "expense_growth"))
    return insights


def insights_frame(insights: list[Insight]) -> pd.DataFrame:
    if not insights:
        return pd.DataFrame(columns=["Category", "Insight", "Branch", "Why (evidence)", "Recommended action"])
    df = pd.DataFrame([i.to_dict() for i in insights])
    df = df.sort_values(["category", "severity"], ascending=[False, False])
    return df.rename(columns={"category": "Category", "title": "Insight", "branch": "Branch",
                              "evidence": "Why (evidence)", "action": "Recommended action"})[
        ["Category", "Insight", "Branch", "Why (evidence)", "Recommended action"]]


def recommendations(insights: list[Insight]) -> list[dict]:
    """Group warning insights by recommended action."""
    groups: dict[str, dict] = {}
    for i in insights:
        if i.category != "Warning" or not i.action:
            continue
        g = groups.setdefault(i.rule, {"action": i.action, "issue": i.title, "branches": [], "severity": i.severity})
        if i.branch not in g["branches"]:
            g["branches"].append(i.branch)
    return sorted(groups.values(), key=lambda g: (-g["severity"], -len(g["branches"])))


def overview_highlights(summary: pd.DataFrame, fin: pd.DataFrame) -> dict:
    """Short facts for the Executive Overview page."""
    if summary is None or summary.empty:
        return {}
    monthly = kpi.monthly_financials(fin)
    lowest = summary.dropna(subset=["target_achievement"]).sort_values("target_achievement")
    rising_exp = summary[(summary["expense_change"].astype(float) > 0)
                         & (summary["expense_change"].astype(float) > summary["revenue_change"].astype(float))] \
        if "expense_change" in summary else pd.DataFrame()
    return {
        "highest_revenue": summary.sort_values("revenue", ascending=False).iloc[0],
        "highest_profit": summary.sort_values("profit", ascending=False).iloc[0],
        "lowest_achievement": lowest.iloc[0] if len(lowest) else None,
        "revenue_growth": kpi.period_change(monthly["revenue"]) if len(monthly) else None,
        "first_month": monthly["reporting_month"].iloc[0] if len(monthly) else None,
        "last_month": monthly["reporting_month"].iloc[-1] if len(monthly) else None,
        "below_target": summary[summary["target_achievement"] < settings.HIGH_PERFORMER_THRESHOLD],
        "rising_expenses": rising_exp,
    }
