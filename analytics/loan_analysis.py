"""
Loan analysis.

Terminology (kept strictly separate):
  Application  - every row in the loans table (any status)
  Approved     - loan_status in Approved, Disbursed, Closed
  Rejected     - loan_status = Rejected
  Disbursed    - loan_status in Disbursed, Closed (money actually paid out)
  Outstanding  - outstanding_amount still owed on disbursed loans
  Default      - disbursed loan with repayment_status = Defaulted
"""
from __future__ import annotations

import pandas as pd

from analytics import kpi_calculations as kpi
from config import settings
from utils.formatting import fmt_inr, fmt_number, fmt_pct


def loan_branch_table(loans: pd.DataFrame) -> pd.DataFrame:
    if loans is None or loans.empty:
        return pd.DataFrame()
    rows = []
    for (bid, name, region), grp in loans.groupby(["branch_id", "branch_name", "region"]):
        k = kpi.loan_kpis(grp)
        rows.append({"branch_id": bid, "branch_name": name, "region": region,
                     "applications": k["applications"], "approved": k["approved"],
                     "rejected": k["rejected"], "approval_rate": k["approval_rate"],
                     "applied_amount": k["applied_amount"], "disbursed_amount": k["disbursed_amount"],
                     "outstanding": k["outstanding"], "defaulted": k["defaulted"],
                     "disbursed_count": k["disbursed_count"], "default_rate": k["default_rate"]})
    return pd.DataFrame(rows).sort_values("applications", ascending=False).reset_index(drop=True)


def monthly_applications(loans: pd.DataFrame) -> pd.DataFrame:
    if loans is None or loans.empty:
        return pd.DataFrame(columns=["month", "applications", "approved", "rejected"])
    l = loans.assign(month=loans["application_date"].dt.to_period("M").dt.to_timestamp())
    g = l.groupby("month").agg(
        applications=("loan_id", "count"),
        approved=("loan_status", lambda s: int(s.isin(settings.APPROVED_LOAN_STATUSES).sum())),
        rejected=("loan_status", lambda s: int((s == settings.LOAN_STATUS_REJECTED).sum())),
    ).reset_index()
    return g


def distribution(loans: pd.DataFrame, column: str) -> pd.DataFrame:
    if loans is None or loans.empty:
        return pd.DataFrame(columns=[column, "count", "amount"])
    return (loans.groupby(column).agg(count=("loan_id", "count"), amount=("loan_amount", "sum"))
            .reset_index().sort_values("count", ascending=False))


def loan_answers(loans: pd.DataFrame, table: pd.DataFrame) -> list[dict]:
    if loans is None or loans.empty:
        return [{"question": "Loan analysis", "answer": "No loan applications for the selected filters.",
                 "status": "info"}]
    k = kpi.loan_kpis(loans)
    out = []
    most = table.sort_values("approved", ascending=False).head(3)
    out.append({"question": "Which branches approve the most loans?",
                "answer": ", ".join(f"**{r.branch_name}** ({fmt_number(r.approved)} approved)" for r in most.itertuples()),
                "status": "info"})
    eligible = table[table["applications"] >= 5].dropna(subset=["approval_rate"])
    low = eligible.sort_values("approval_rate").head(3)
    out.append({"question": "Which branches have lower approval rates?",
                "answer": (", ".join(f"**{r.branch_name}** ({fmt_pct(r.approval_rate)})" for r in low.itertuples())
                           + f" — bank average {fmt_pct(k['approval_rate'])}.") if len(low) else
                "Too few applications per branch to compare (minimum 5).",
                "status": "warn" if len(low) else "info"})
    types = distribution(loans, "loan_type")
    out.append({"question": "Which loan types are most common?",
                "answer": ", ".join(f"**{r.loan_type}** ({fmt_number(r.count)})" for r in types.head(3).itertuples()),
                "status": "info"})
    out.append({"question": "How much loan amount has been disbursed?",
                "answer": (f"**{fmt_inr(k['disbursed_amount'], short=True)}** across "
                           f"{fmt_number(k['disbursed_count'])} disbursed loans "
                           f"(out of {fmt_inr(k['applied_amount'], short=True)} applied for)."),
                "status": "info"})
    risky = table[(table["disbursed_count"] >= 5) & (table["default_rate"] > settings.DEFAULT_RATE_THRESHOLD)] \
        .sort_values("default_rate", ascending=False)
    out.append({"question": "Which branches have higher default rates?",
                "answer": (", ".join(f"**{r.branch_name}** ({fmt_pct(r.default_rate)})" for r in risky.itertuples())
                           + f" exceed the {settings.DEFAULT_RATE_THRESHOLD:.0f}% threshold.")
                if len(risky) else f"No branch exceeds the {settings.DEFAULT_RATE_THRESHOLD:.0f}% default-rate threshold.",
                "status": "warn" if len(risky) else "good"})
    out.append({"question": "How much loan amount remains outstanding?",
                "answer": f"**{fmt_inr(k['outstanding'], short=True)}** is still outstanding on disbursed loans.",
                "status": "info"})
    return out
