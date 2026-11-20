"""
Branch-level analysis: the branch performance table, rankings, regional view
and single-branch drill-down. All formulas come from kpi_calculations.
"""
from __future__ import annotations

import pandas as pd

from analytics import kpi_calculations as kpi
from config import settings

RANK_METRICS = {
    "Revenue": "revenue",
    "Net Profit": "profit",
    "Profit Margin %": "profit_margin",
    "Target Achievement %": "target_achievement",
    "Deposits": "deposits",
    "Customers": "customers",
    "Customer Satisfaction": "satisfaction",
}


def branch_summary(branches: pd.DataFrame, fin: pd.DataFrame, customers: pd.DataFrame,
                   feedback: pd.DataFrame, loans: pd.DataFrame | None = None,
                   high: float = settings.HIGH_PERFORMER_THRESHOLD,
                   average: float = settings.AVERAGE_PERFORMER_THRESHOLD) -> pd.DataFrame:
    """One row per (filtered) branch with every performance metric."""
    if branches is None or branches.empty:
        return pd.DataFrame()
    base = branches[["branch_id", "branch_name", "city", "state", "region", "branch_type", "status"]].copy()

    if fin is not None and not fin.empty:
        agg = fin.groupby("branch_id")[kpi.FIN_COLS].sum().reset_index()
        exp_trend = (fin.sort_values("reporting_month").groupby("branch_id")
                     .agg(revenue_change=("revenue", kpi.period_change),
                          expense_change=("expenses", kpi.period_change),
                          deposit_change=("deposits", kpi.period_change))
                     .reset_index())
        prof = fin.assign(profit=fin["revenue"] - fin["expenses"]).sort_values("reporting_month")
        prof_trend = prof.groupby("branch_id")["profit"].apply(kpi.period_change).rename("profit_change").reset_index()
        agg = agg.merge(exp_trend, on="branch_id", how="left").merge(prof_trend, on="branch_id", how="left")
    else:
        agg = pd.DataFrame(columns=["branch_id"] + kpi.FIN_COLS)
    out = base.merge(agg, on="branch_id", how="left")
    out["months_reported"] = (fin.groupby("branch_id")["reporting_month"].nunique()
                              .reindex(out["branch_id"]).fillna(0).astype(int).values
                              if fin is not None and not fin.empty else 0)
    for col in kpi.FIN_COLS:
        out[col] = out[col].fillna(0.0)

    cust = (customers.groupby("branch_id").size().rename("customers").reset_index()
            if customers is not None and not customers.empty else pd.DataFrame(columns=["branch_id", "customers"]))
    out = out.merge(cust, on="branch_id", how="left")
    out["customers"] = out["customers"].fillna(0).astype(int)

    sat = (feedback.groupby("branch_id")["satisfaction_score"].mean().rename("satisfaction").reset_index()
           if feedback is not None and not feedback.empty else pd.DataFrame(columns=["branch_id", "satisfaction"]))
    out = out.merge(sat, on="branch_id", how="left")

    if loans is not None and not loans.empty:
        rows = []
        for bid, grp in loans.groupby("branch_id"):
            k = kpi.loan_kpis(grp)
            rows.append({"branch_id": bid, "loan_applications": k["applications"],
                         "disbursed_loans": k["disbursed_count"],
                         "approval_rate": k["approval_rate"], "default_rate": k["default_rate"]})
        out = out.merge(pd.DataFrame(rows), on="branch_id", how="left")
    else:
        out["loan_applications"], out["disbursed_loans"] = 0, 0
        out["approval_rate"], out["default_rate"] = None, None

    out["profit"] = out["revenue"] - out["expenses"]
    out["profit_margin"] = [kpi.profit_margin(r, e) for r, e in zip(out["revenue"], out["expenses"])]
    out["target_achievement"] = [kpi.target_achievement(r, t) for r, t in zip(out["revenue"], out["revenue_target"])]
    out["expense_ratio"] = [kpi.expense_ratio(r, e) for r, e in zip(out["revenue"], out["expenses"])]
    out["performance_category"] = [kpi.performance_category(a, high, average) for a in out["target_achievement"]]
    out["revenue_per_customer"] = [kpi.avg_revenue_per_customer(r, c) for r, c in zip(out["revenue"], out["customers"])]
    for col in ("revenue_change", "expense_change", "deposit_change", "profit_change"):
        if col not in out.columns:
            out[col] = None
    return out.sort_values("revenue", ascending=False).reset_index(drop=True)


def branch_kpis(summary: pd.DataFrame) -> dict:
    if summary is None or summary.empty:
        return {"branches": 0, "avg_revenue": None, "avg_profit": None,
                "avg_achievement": None, "underperforming": 0, "high_performers": 0}
    return {
        "branches": len(summary),
        "avg_revenue": float(summary["revenue"].mean()),
        "avg_profit": float(summary["profit"].mean()),
        # Bank-level achievement = total revenue / total target (not a mean of %),
        # so large and small branches are weighted correctly.
        "avg_achievement": kpi.target_achievement(summary["revenue"].sum(), summary["revenue_target"].sum()),
        "underperforming": int((summary["performance_category"] == "Low Performer").sum()),
        "high_performers": int((summary["performance_category"] == "High Performer").sum()),
    }


def rank_branches(summary: pd.DataFrame, metric: str, n: int = settings.TOP_N,
                  ascending: bool = False) -> pd.DataFrame:
    if summary is None or summary.empty or metric not in summary.columns:
        return pd.DataFrame()
    ranked = summary.dropna(subset=[metric]).sort_values(metric, ascending=ascending)
    return ranked.head(n).reset_index(drop=True)


def regional_summary(summary: pd.DataFrame) -> pd.DataFrame:
    if summary is None or summary.empty:
        return pd.DataFrame()
    reg = summary.groupby("region").agg(
        branches=("branch_id", "count"), revenue=("revenue", "sum"), expenses=("expenses", "sum"),
        revenue_target=("revenue_target", "sum"), deposits=("deposits", "sum"),
        customers=("customers", "sum")).reset_index()
    reg["profit"] = reg["revenue"] - reg["expenses"]
    reg["profit_margin"] = [kpi.profit_margin(r, e) for r, e in zip(reg["revenue"], reg["expenses"])]
    reg["target_achievement"] = [kpi.target_achievement(r, t) for r, t in zip(reg["revenue"], reg["revenue_target"])]
    return reg.sort_values("revenue", ascending=False).reset_index(drop=True)


def branch_monthly(fin: pd.DataFrame, branch_id: str) -> pd.DataFrame:
    return kpi.monthly_financials(fin[fin["branch_id"] == branch_id]) if fin is not None and not fin.empty \
        else kpi.monthly_financials(pd.DataFrame())


def customer_growth_monthly(customers: pd.DataFrame, months: pd.Series) -> pd.DataFrame:
    """Cumulative customer base at each month end + new customers that month."""
    if customers is None or customers.empty or months is None or len(months) == 0:
        return pd.DataFrame(columns=["month", "total_customers", "new_customers"])
    months = pd.Series(sorted(pd.to_datetime(pd.Series(months).unique())))
    month_ends = months + pd.offsets.MonthEnd(0)
    joins = customers["join_date"].sort_values().values
    totals = [int((joins <= me.to_datetime64()).sum()) for me in month_ends]
    jm = customers["join_date"].dt.to_period("M").dt.to_timestamp()
    new = [int((jm == m).sum()) for m in months]
    return pd.DataFrame({"month": months, "total_customers": totals, "new_customers": new})


def compare_with_bank(summary: pd.DataFrame, branch_id: str) -> pd.DataFrame:
    """Branch value vs bank-wide average for the key metrics."""
    if summary is None or summary.empty or branch_id not in set(summary["branch_id"]):
        return pd.DataFrame()
    row = summary[summary["branch_id"] == branch_id].iloc[0]
    metrics = [("Revenue", "revenue", "currency"), ("Net Profit", "profit", "currency"),
               ("Profit Margin %", "profit_margin", "pct"), ("Target Achievement %", "target_achievement", "pct"),
               ("Deposits", "deposits", "currency"), ("Customers", "customers", "number"),
               ("Customer Satisfaction", "satisfaction", "score"), ("Loan Default Rate %", "default_rate", "pct")]
    data = []
    for label, col, kind in metrics:
        if col not in summary.columns:
            continue
        bank_avg = summary[col].mean() if col not in ("profit_margin", "target_achievement") else (
            kpi.profit_margin(summary["revenue"].sum(), summary["expenses"].sum()) if col == "profit_margin"
            else kpi.target_achievement(summary["revenue"].sum(), summary["revenue_target"].sum()))
        value = row[col]
        diff = kpi.growth_rate(value, bank_avg) if kind in ("currency", "number") else (
            None if pd.isna(value) or bank_avg is None or pd.isna(bank_avg) else float(value) - float(bank_avg))
        data.append({"Metric": label, "kind": kind, "Branch": value, "Bank Average": bank_avg,
                     "Difference": diff})
    return pd.DataFrame(data)
