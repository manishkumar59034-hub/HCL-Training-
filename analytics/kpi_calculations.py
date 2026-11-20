"""
Centralised KPI calculations.

EVERY page imports its formulas from here, so a KPI is calculated exactly the
same way everywhere in the application.

Formulas
--------
Net Profit             = Revenue - Expenses
Profit Margin %        = Net Profit / Revenue * 100
Target Achievement %   = Actual Revenue / Revenue Target * 100
Growth %               = (Current - Previous) / Previous * 100
Customer Growth %      = (Customers at period end - Customers at period start) / Customers at period start * 100
Loan Approval Rate %   = Approved Loans / Total Loan Applications * 100
Loan Default Rate %    = Defaulted Loans / Disbursed Loans * 100
Avg Revenue / Customer = Total Revenue / Total Customers
Expense Ratio %        = Expenses / Revenue * 100

Any division by zero, missing value or missing previous period returns None,
which the UI displays as "N/A".
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

from config import settings


# ---------------------------------------------------------------------------
# Scalar formulas
# ---------------------------------------------------------------------------
def _is_missing(x: Any) -> bool:
    if x is None:
        return True
    try:
        return bool(pd.isna(x))
    except (TypeError, ValueError):
        return False


def safe_divide(numerator, denominator) -> float | None:
    if _is_missing(numerator) or _is_missing(denominator):
        return None
    try:
        denominator = float(denominator)
        if denominator == 0 or math.isinf(denominator):
            return None
        return float(numerator) / denominator
    except (TypeError, ValueError):
        return None


def safe_pct(numerator, denominator) -> float | None:
    ratio = safe_divide(numerator, denominator)
    return None if ratio is None else ratio * 100


def net_profit(revenue, expenses) -> float | None:
    if _is_missing(revenue) or _is_missing(expenses):
        return None
    return float(revenue) - float(expenses)


def profit_margin(revenue, expenses) -> float | None:
    return safe_pct(net_profit(revenue, expenses), revenue)


def target_achievement(revenue, target) -> float | None:
    return safe_pct(revenue, target)


def growth_rate(current, previous) -> float | None:
    if _is_missing(current) or _is_missing(previous):
        return None
    return safe_pct(float(current) - float(previous), abs(float(previous)))


def expense_ratio(revenue, expenses) -> float | None:
    return safe_pct(expenses, revenue)


def approval_rate(approved, total_applications) -> float | None:
    return safe_pct(approved, total_applications)


def default_rate(defaulted, disbursed) -> float | None:
    return safe_pct(defaulted, disbursed)


def avg_revenue_per_customer(revenue, customers) -> float | None:
    return safe_divide(revenue, customers)


def performance_category(achievement_pct,
                         high: float = settings.HIGH_PERFORMER_THRESHOLD,
                         average: float = settings.AVERAGE_PERFORMER_THRESHOLD) -> str:
    if _is_missing(achievement_pct):
        return "Not Rated"
    if achievement_pct >= high:
        return "High Performer"
    if achievement_pct >= average:
        return "Average Performer"
    return "Low Performer"


def period_change(series: pd.Series) -> float | None:
    """% change across a period for a monthly series (sorted by month).

    6+ months : average of last 3 vs average of first 3 (smooths noise)
    2-5 months: last month vs first month
    <2 months : None (not enough history)
    """
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return None
    if len(s) >= 6:
        return growth_rate(s.iloc[-3:].mean(), s.iloc[:3].mean())
    return growth_rate(s.iloc[-1], s.iloc[0])


def latest_vs_previous(series: pd.Series) -> float | None:
    """Month-over-month growth % of the last value vs the one before it."""
    s = pd.Series(series).dropna()
    if len(s) < 2:
        return None
    return growth_rate(s.iloc[-1], s.iloc[-2])


# ---------------------------------------------------------------------------
# DataFrame-level KPIs
# ---------------------------------------------------------------------------
FIN_COLS = ["revenue", "expenses", "deposits", "loan_disbursement", "revenue_target"]


def monthly_financials(fin: pd.DataFrame) -> pd.DataFrame:
    """Bank-wide monthly totals with derived KPI columns."""
    if fin is None or fin.empty:
        return pd.DataFrame(columns=["reporting_month"] + FIN_COLS + ["profit", "profit_margin",
                                                                       "target_achievement"])
    m = fin.groupby("reporting_month", as_index=False)[FIN_COLS].sum().sort_values("reporting_month")
    m["profit"] = m["revenue"] - m["expenses"]
    m["profit_margin"] = [profit_margin(r, e) for r, e in zip(m["revenue"], m["expenses"])]
    m["target_achievement"] = [target_achievement(r, t) for r, t in zip(m["revenue"], m["revenue_target"])]
    return m.reset_index(drop=True)


def financial_kpis(fin: pd.DataFrame) -> dict[str, float | None]:
    if fin is None or fin.empty:
        return {k: None for k in ("revenue", "expenses", "profit", "profit_margin", "deposits",
                                  "loan_disbursement", "revenue_target", "target_achievement",
                                  "revenue_growth", "expense_growth", "profit_growth",
                                  "deposit_growth", "months")}
    totals = fin[FIN_COLS].sum()
    m = monthly_financials(fin)
    return {
        "revenue": float(totals["revenue"]),
        "expenses": float(totals["expenses"]),
        "profit": net_profit(totals["revenue"], totals["expenses"]),
        "profit_margin": profit_margin(totals["revenue"], totals["expenses"]),
        "deposits": float(totals["deposits"]),
        "loan_disbursement": float(totals["loan_disbursement"]),
        "revenue_target": float(totals["revenue_target"]),
        "target_achievement": target_achievement(totals["revenue"], totals["revenue_target"]),
        "revenue_growth": latest_vs_previous(m["revenue"]),
        "expense_growth": latest_vs_previous(m["expenses"]),
        "profit_growth": latest_vs_previous(m["profit"]),
        "deposit_growth": latest_vs_previous(m["deposits"]),
        "months": int(m["reporting_month"].nunique()),
    }


def customer_kpis(customers: pd.DataFrame, period_start=None, feedback: pd.DataFrame | None = None,
                  month: int | None = None) -> dict[str, float | None]:
    """Customer KPIs. `customers` must already be limited to join_date <= period end."""
    sat = None
    if feedback is not None and not feedback.empty:
        sat = float(feedback["satisfaction_score"].mean())
    if customers is None or customers.empty:
        return {"total": 0, "active": 0, "new": 0, "previous": 0, "growth": None, "satisfaction": sat}
    total = len(customers)
    active = int((customers["status"] == "Active").sum())
    if period_start is not None:
        start = pd.Timestamp(period_start)
        in_period = customers["join_date"] >= start
        if month:
            in_period &= customers["join_date"].dt.month == month
        new = int(in_period.sum())
        previous = int((customers["join_date"] < start).sum())
    else:
        new, previous = total, 0
    return {"total": total, "active": active, "new": new, "previous": previous,
            "growth": growth_rate(total, previous) if previous else None, "satisfaction": sat}


def loan_kpis(loans: pd.DataFrame) -> dict[str, float | None]:
    empty = {"applications": 0, "approved": 0, "rejected": 0, "pending": 0, "disbursed_count": 0,
             "defaulted": 0, "approval_rate": None, "default_rate": None, "applied_amount": 0.0,
             "disbursed_amount": 0.0, "outstanding": 0.0, "avg_interest": None}
    if loans is None or loans.empty:
        return empty
    status = loans["loan_status"]
    approved_mask = status.isin(settings.APPROVED_LOAN_STATUSES)
    disbursed_mask = status.isin(settings.DISBURSED_LOAN_STATUSES)
    defaulted = int((disbursed_mask & (loans["repayment_status"] == settings.REPAYMENT_DEFAULTED)).sum())
    applications = len(loans)
    approved = int(approved_mask.sum())
    disbursed = int(disbursed_mask.sum())
    return {
        "applications": applications,
        "approved": approved,
        "rejected": int((status == settings.LOAN_STATUS_REJECTED).sum()),
        "pending": int((status == settings.LOAN_STATUS_PENDING).sum()),
        "disbursed_count": disbursed,
        "defaulted": defaulted,
        "approval_rate": approval_rate(approved, applications),
        "default_rate": default_rate(defaulted, disbursed),
        "applied_amount": float(loans["loan_amount"].sum()),
        "disbursed_amount": float(loans.loc[disbursed_mask, "loan_amount"].sum()),
        "outstanding": float(loans.loc[disbursed_mask, "outstanding_amount"].sum()),
        "avg_interest": float(loans.loc[approved_mask, "interest_rate"].mean()) if approved else None,
    }
