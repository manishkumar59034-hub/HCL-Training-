"""
SQL query layer.

Every function takes a `Filters` object and returns a DataFrame. Filters are
converted into a parameterised WHERE clause (values are passed as `?`
parameters - never formatted into the SQL string).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from database import db


@dataclass
class Filters:
    start_date: date | None = None
    end_date: date | None = None
    month: int | None = None                 # 1-12, applies across years
    regions: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)
    branch_ids: list[str] = field(default_factory=list)
    branch_statuses: list[str] = field(default_factory=list)

    def describe(self) -> list[str]:
        """Human-readable list of active filters (shown in the sidebar/exports)."""
        parts = []
        if self.start_date or self.end_date:
            parts.append(f"Period: {self.start_date:%d %b %Y} – {self.end_date:%d %b %Y}"
                         if self.start_date and self.end_date else "Period: custom")
        if self.month:
            parts.append(f"Month: {date(2000, self.month, 1):%B}")
        for label, values in (("Region", self.regions), ("State", self.states),
                              ("City", self.cities), ("Branch", self.branch_ids),
                              ("Status", self.branch_statuses)):
            if values:
                parts.append(f"{label}: {', '.join(values)}")
        return parts or ["No filters (all data)"]


def _in_clause(column: str, values: list) -> tuple[str, list]:
    placeholders = ",".join("?" for _ in values)
    return f"{column} IN ({placeholders})", list(values)


def branch_where(f: Filters, alias: str = "b") -> tuple[list[str], list]:
    clauses, params = [], []
    for col, values in (("region", f.regions), ("state", f.states), ("city", f.cities),
                        ("branch_id", f.branch_ids), ("status", f.branch_statuses)):
        if values:
            sql, p = _in_clause(f"{alias}.{col}", values)
            clauses.append(sql)
            params += p
    return clauses, params


def date_where(f: Filters, column: str, apply_start: bool = True) -> tuple[list[str], list]:
    clauses, params = [], []
    if f.start_date and apply_start:
        clauses.append(f"date({column}) >= date(?)")
        params.append(f.start_date.isoformat())
    if f.end_date:
        clauses.append(f"date({column}) <= date(?)")
        params.append(f.end_date.isoformat())
    if f.month and apply_start:
        clauses.append(f"CAST(strftime('%m', {column}) AS INTEGER) = ?")
        params.append(int(f.month))
    return clauses, params


def _run(base_sql: str, clauses: list[str], params: list, order_by: str = "") -> pd.DataFrame:
    sql = base_sql
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    if order_by:
        sql += " ORDER BY " + order_by
    return db.query_df(sql, params)


# ---------------------------------------------------------------------------
# Lookup / filter option queries
# ---------------------------------------------------------------------------
def all_branches() -> pd.DataFrame:
    return db.query_df("SELECT * FROM branches ORDER BY branch_id")


def data_date_bounds() -> tuple[date | None, date | None]:
    row = db.fetch_one("SELECT MIN(d), MAX(d) FROM ("
                       "SELECT MIN(reporting_month) d FROM branch_financials UNION ALL "
                       "SELECT date(MAX(reporting_month), '+1 month', '-1 day') FROM branch_financials UNION ALL "
                       "SELECT MIN(transaction_date) FROM transactions UNION ALL "
                       "SELECT MAX(transaction_date) FROM transactions)")
    if not row or row[0] is None:
        return None, None
    return date.fromisoformat(row[0]), date.fromisoformat(row[1])


# ---------------------------------------------------------------------------
# Business data queries
# ---------------------------------------------------------------------------
BRANCH_COLS = "b.branch_name, b.city, b.state, b.region, b.branch_type, b.status AS branch_status"


def get_branches(f: Filters) -> pd.DataFrame:
    clauses, params = branch_where(f)
    return _run("SELECT b.* FROM branches b", clauses, params, "b.branch_id")


def get_financials(f: Filters) -> pd.DataFrame:
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "fn.reporting_month")
    if f.start_date:
        # a month counts if its first day falls in range (reporting_month = YYYY-MM-01)
        dc[0] = "date(fn.reporting_month) >= date(?, 'start of month')"
    df = _run(f"SELECT fn.*, {BRANCH_COLS} FROM branch_financials fn "
              "JOIN branches b ON b.branch_id = fn.branch_id",
              bc + dc, bp + dp, "fn.reporting_month, fn.branch_id")
    if not df.empty:
        df["reporting_month"] = pd.to_datetime(df["reporting_month"])
    return df


def get_customers(f: Filters) -> pd.DataFrame:
    """Customers of the filtered branches who had joined by the period end.

    Join-date start is NOT applied, because "Total Customers" means the
    customer base at the end of the period. New customers are derived later.
    """
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "c.join_date", apply_start=False)
    df = _run(f"SELECT c.customer_id, c.branch_id, c.customer_type, c.gender, c.age_group, "
              f"c.join_date, c.city AS customer_city, c.status, {BRANCH_COLS} "
              "FROM customers c JOIN branches b ON b.branch_id = c.branch_id",
              bc + dc, bp + dp, "c.join_date")
    if not df.empty:
        df["join_date"] = pd.to_datetime(df["join_date"])
    return df


def get_transactions(f: Filters, limit: int | None = None) -> pd.DataFrame:
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "t.transaction_date")
    sql = ("SELECT t.transaction_id, t.transaction_date, t.branch_id, b.branch_name, b.city, "
           "b.region, t.customer_id, t.transaction_type, t.amount, t.channel, t.status "
           "FROM transactions t JOIN branches b ON b.branch_id = t.branch_id")
    df = _run(sql, bc + dc, bp + dp, "t.transaction_date DESC" + (f" LIMIT {int(limit)}" if limit else ""))
    if not df.empty:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    return df


def get_loans(f: Filters) -> pd.DataFrame:
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "l.application_date")
    df = _run(f"SELECT l.*, {BRANCH_COLS} FROM loans l JOIN branches b ON b.branch_id = l.branch_id",
              bc + dc, bp + dp, "l.application_date")
    if not df.empty:
        df["application_date"] = pd.to_datetime(df["application_date"])
    return df


def get_feedback(f: Filters) -> pd.DataFrame:
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "fb.feedback_date")
    df = _run(f"SELECT fb.*, {BRANCH_COLS} FROM customer_feedback fb "
              "JOIN branches b ON b.branch_id = fb.branch_id",
              bc + dc, bp + dp, "fb.feedback_date")
    if not df.empty:
        df["feedback_date"] = pd.to_datetime(df["feedback_date"])
    return df


def regional_financials_sql(f: Filters) -> pd.DataFrame:
    """Example of aggregation done directly in SQL (GROUP BY region)."""
    bc, bp = branch_where(f)
    dc, dp = date_where(f, "fn.reporting_month")
    if f.start_date:
        dc[0] = "date(fn.reporting_month) >= date(?, 'start of month')"
    sql = ("SELECT b.region, COUNT(DISTINCT b.branch_id) AS branches, SUM(fn.revenue) AS revenue, "
           "SUM(fn.expenses) AS expenses, SUM(fn.revenue) - SUM(fn.expenses) AS profit, "
           "SUM(fn.revenue_target) AS revenue_target, SUM(fn.deposits) AS deposits "
           "FROM branch_financials fn JOIN branches b ON b.branch_id = fn.branch_id")
    where = (" WHERE " + " AND ".join(bc + dc)) if (bc + dc) else ""
    return db.query_df(sql + where + " GROUP BY b.region ORDER BY revenue DESC", bp + dp)
