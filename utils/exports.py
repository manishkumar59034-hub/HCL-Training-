"""Build export files (CSV / multi-sheet Excel) that reflect the current filters."""
from __future__ import annotations

import io
import re
from datetime import datetime

import pandas as pd

from analytics import insights as ins
from analytics import kpi_calculations as kpi
from analytics import loan_analysis as la
from analytics.queries import Filters, get_transactions
from components.tables import branch_table_export


def safe_filename(name: str, ext: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return f"{stem}_{datetime.now():%Y%m%d_%H%M}.{ext}"


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")  # BOM so Excel shows ₹ correctly


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.sheets[name[:31]]
            for col_cells in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col_cells[:200])
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(10, width + 2), 60)
    return buf.getvalue()


def filters_sheet(filters: Filters) -> pd.DataFrame:
    return pd.DataFrame({"Filter applied": filters.describe(),
                         "Generated at": datetime.now().strftime("%Y-%m-%d %H:%M")})


def financial_summary(ds) -> pd.DataFrame:
    f = kpi.financial_kpis(ds.financials)
    rows = [("Total Revenue (₹)", f["revenue"]), ("Total Expenses (₹)", f["expenses"]),
            ("Net Profit (₹)", f["profit"]), ("Profit Margin %", f["profit_margin"]),
            ("Revenue Target (₹)", f["revenue_target"]), ("Target Achievement %", f["target_achievement"]),
            ("Total Deposits (₹)", f["deposits"]), ("Loan Disbursement (₹)", f["loan_disbursement"]),
            ("Revenue Growth % (MoM)", f["revenue_growth"]), ("Expense Growth % (MoM)", f["expense_growth"]),
            ("Months in selection", f["months"])]
    summary = pd.DataFrame(rows, columns=["Metric", "Value"])
    summary["Value"] = summary["Value"].map(lambda v: round(v, 2) if isinstance(v, float) else v)
    return summary


def monthly_financials_export(ds) -> pd.DataFrame:
    m = ds.monthly.copy()
    if m.empty:
        return m
    m["reporting_month"] = m["reporting_month"].dt.strftime("%b %Y")
    return m.rename(columns={"reporting_month": "Month", "revenue": "Revenue (₹)", "expenses": "Expenses (₹)",
                             "deposits": "Deposits (₹)", "loan_disbursement": "Loan Disbursement (₹)",
                             "revenue_target": "Revenue Target (₹)", "profit": "Net Profit (₹)",
                             "profit_margin": "Profit Margin %", "target_achievement": "Target Achievement %"}).round(2)


def loan_summary(ds) -> pd.DataFrame:
    t = la.loan_branch_table(ds.loans)
    if t.empty:
        return t
    return t.rename(columns={"branch_id": "Branch ID", "branch_name": "Branch", "region": "Region",
                             "applications": "Applications", "approved": "Approved", "rejected": "Rejected",
                             "approval_rate": "Approval Rate %", "applied_amount": "Applied Amount (₹)",
                             "disbursed_amount": "Disbursed Amount (₹)", "outstanding": "Outstanding (₹)",
                             "defaulted": "Defaulted Loans", "disbursed_count": "Disbursed Loans",
                             "default_rate": "Default Rate %"}).round(2)


def transactions_export(ds) -> pd.DataFrame:
    t = get_transactions(ds.filters)
    if t.empty:
        return t
    t["transaction_date"] = t["transaction_date"].dt.strftime("%Y-%m-%d")
    return t.rename(columns={"transaction_id": "Transaction ID", "transaction_date": "Date",
                             "branch_id": "Branch ID", "branch_name": "Branch", "city": "City", "region": "Region",
                             "customer_id": "Customer ID", "transaction_type": "Type", "amount": "Amount (₹)",
                             "channel": "Channel", "status": "Status"})


def insights_export(ds) -> pd.DataFrame:
    return ins.insights_frame(ins.generate_insights(ds.summary, ds.financials, ds.feedback, ds.customer_growth))


REPORTS = {
    "Branch performance report": lambda ds: branch_table_export(ds.summary),
    "Financial summary": financial_summary,
    "Monthly financials": monthly_financials_export,
    "Loan analysis summary": loan_summary,
    "Filtered transaction data": transactions_export,
    "Summary of insights": insights_export,
}


def full_report(ds) -> bytes:
    sheets = {"Filters": filters_sheet(ds.filters)}
    for name, fn in REPORTS.items():
        sheets[name.replace("Filtered ", "").title()[:31]] = fn(ds)
    return excel_bytes(sheets)
