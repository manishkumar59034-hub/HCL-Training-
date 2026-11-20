"""
Data validation rules for imports, plus a data-quality report for the database.

`validate_dataframe` checks an (already cleaned) upload against the table
specification and returns a ValidationReport describing every problem in
plain language, row by row.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from database import db

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Specification for every importable table.
#   numeric: column -> "positive" | "non_negative" | (min, max)
TABLE_SPECS: dict[str, dict] = {
    "branches": {
        "id": "branch_id",
        "required": ["branch_id", "branch_name", "city", "state", "region", "branch_type",
                     "opening_date", "status"],
        "optional": [],
        "dates": ["opening_date"],
        "numeric": {},
        "categories": {
            "region": ["North", "South", "East", "West", "Central"],
            "branch_type": ["Metro", "Urban", "Semi-Urban", "Rural"],
            "status": ["Active", "Inactive", "Under Review"],
        },
        "foreign_keys": {},
        "unique_together": [["branch_name"]],
    },
    "customers": {
        "id": "customer_id",
        "required": ["customer_id", "branch_id", "customer_name", "customer_type", "join_date",
                     "city", "status"],
        "optional": ["gender", "age_group"],
        "dates": ["join_date"],
        "numeric": {},
        "categories": {
            "customer_type": ["Individual", "Business", "Corporate", "NRI", "Senior Citizen"],
            "gender": ["Male", "Female", "Other"],
            "age_group": ["18-25", "26-35", "36-45", "46-60", "60+"],
            "status": ["Active", "Inactive", "Closed"],
        },
        "foreign_keys": {"branch_id": "branches"},
        "unique_together": [],
    },
    "transactions": {
        "id": "transaction_id",
        "required": ["transaction_id", "customer_id", "branch_id", "transaction_date",
                     "transaction_type", "amount", "channel", "status"],
        "optional": [],
        "dates": ["transaction_date"],
        "numeric": {"amount": "positive"},
        "categories": {
            "transaction_type": ["Deposit", "Withdrawal", "Transfer", "Bill Payment", "Loan Repayment"],
            "channel": ["Branch", "ATM", "Mobile Banking", "Internet Banking", "UPI"],
            "status": ["Success", "Failed", "Reversed"],
        },
        "foreign_keys": {"customer_id": "customers", "branch_id": "branches"},
        "unique_together": [],
    },
    "loans": {
        "id": "loan_id",
        "required": ["loan_id", "customer_id", "branch_id", "application_date", "loan_type",
                     "loan_amount", "interest_rate", "loan_status", "outstanding_amount",
                     "repayment_status"],
        "optional": [],
        "dates": ["application_date"],
        "numeric": {"loan_amount": "positive", "interest_rate": (0, 40),
                    "outstanding_amount": "non_negative"},
        "categories": {
            "loan_type": ["Home Loan", "Personal Loan", "Vehicle Loan", "Business Loan",
                          "Education Loan", "Gold Loan"],
            "loan_status": ["Pending", "Approved", "Rejected", "Disbursed", "Closed"],
            "repayment_status": ["Not Applicable", "Current", "Overdue", "Defaulted", "Repaid"],
        },
        "foreign_keys": {"customer_id": "customers", "branch_id": "branches"},
        "unique_together": [],
    },
    "branch_financials": {
        "id": "financial_id",
        "required": ["financial_id", "branch_id", "reporting_month", "revenue", "expenses",
                     "deposits", "loan_disbursement", "revenue_target"],
        "optional": [],
        "dates": ["reporting_month"],
        "numeric": {"revenue": "non_negative", "expenses": "non_negative",
                    "deposits": "non_negative", "loan_disbursement": "non_negative",
                    "revenue_target": "non_negative"},
        "categories": {},
        "foreign_keys": {"branch_id": "branches"},
        "unique_together": [["branch_id", "reporting_month"]],
    },
    "customer_feedback": {
        "id": "feedback_id",
        "required": ["feedback_id", "branch_id", "feedback_date", "satisfaction_score",
                     "feedback_category"],
        "optional": [],
        "dates": ["feedback_date"],
        "numeric": {"satisfaction_score": (1, 5)},
        "categories": {
            "feedback_category": ["Service Quality", "Waiting Time", "Staff Behaviour",
                                  "Digital Services", "Loan Processing", "Account Services", "Other"],
        },
        "foreign_keys": {"branch_id": "branches"},
        "unique_together": [],
    },
}

IMPORTABLE_TABLES = list(TABLE_SPECS.keys())


@dataclass
class ValidationReport:
    table: str
    total_rows: int = 0
    missing_columns: list[str] = field(default_factory=list)
    unexpected_columns: list[str] = field(default_factory=list)
    issues: list[dict] = field(default_factory=list)        # {row, column, problem}
    invalid_rows: set[int] = field(default_factory=set)     # file row indexes with errors
    existing_rows: set[int] = field(default_factory=set)    # already in database -> skip
    duplicate_in_file: int = 0

    @property
    def is_structurally_valid(self) -> bool:
        return not self.missing_columns

    @property
    def has_errors(self) -> bool:
        return bool(self.missing_columns or self.invalid_rows)

    @property
    def valid_new_rows(self) -> int:
        return self.total_rows - len(self.invalid_rows | self.existing_rows)

    def add(self, rows, column: str, problem: str) -> None:
        for r in rows:
            self.issues.append({"Row": int(r) + 2, "Column": column, "Problem": problem})
            self.invalid_rows.add(int(r))

    def issues_df(self) -> pd.DataFrame:
        if not self.issues:
            return pd.DataFrame(columns=["Row", "Column", "Problem"])
        return pd.DataFrame(self.issues).sort_values(["Row", "Column"]).reset_index(drop=True)

    def summary(self) -> dict:
        return {
            "Rows in file": self.total_rows,
            "Rows with errors": len(self.invalid_rows),
            "Already in database (will be skipped)": len(self.existing_rows - self.invalid_rows),
            "Duplicate rows inside file": self.duplicate_in_file,
            "Valid new rows ready to import": self.valid_new_rows,
        }


def _existing_values(table: str, column: str) -> set:
    rows = db.fetch_all(f'SELECT DISTINCT "{column}" FROM "{table}"')
    return {r[0] for r in rows}


def validate_dataframe(table: str, df: pd.DataFrame) -> ValidationReport:
    """Validate a cleaned DataFrame for import into `table`."""
    if table not in TABLE_SPECS:
        raise ValueError(f"Unknown table: {table}")
    spec = TABLE_SPECS[table]
    report = ValidationReport(table=table, total_rows=len(df))

    allowed_cols = set(spec["required"]) | set(spec["optional"])
    report.missing_columns = [c for c in spec["required"] if c not in df.columns]
    report.unexpected_columns = [c for c in df.columns if c not in allowed_cols]
    if report.missing_columns or df.empty:
        return report

    # 1. Missing values in required columns
    for col in spec["required"]:
        missing = df.index[df[col].isna()]
        if len(missing):
            report.add(missing, col, "Missing value (required field)")

    # 2. Dates
    for col in spec["dates"]:
        vals = df[col]
        bad = vals.notna() & ~vals.astype(str).str.match(ISO_DATE_RE)
        parsed = pd.to_datetime(vals.where(~bad), format="%Y-%m-%d", errors="coerce")
        bad = bad | (vals.notna() & parsed.isna())
        if bad.any():
            report.add(df.index[bad], col, "Invalid date (expected YYYY-MM-DD)")
        future = parsed > pd.Timestamp.today() + pd.Timedelta(days=62)
        if future.any():
            report.add(df.index[future], col, "Date is too far in the future")

    # 3. Numbers
    for col, rule in spec["numeric"].items():
        num = pd.to_numeric(df[col], errors="coerce")
        not_num = df[col].notna() & num.isna()
        if not_num.any():
            report.add(df.index[not_num], col, "Not a valid number")
        if rule == "positive":
            bad = num.notna() & (num <= 0)
            if bad.any():
                report.add(df.index[bad], col, "Must be greater than zero")
        elif rule == "non_negative":
            bad = num.notna() & (num < 0)
            if bad.any():
                report.add(df.index[bad], col, "Negative value is not allowed")
        elif isinstance(rule, tuple):
            lo, hi = rule
            bad = num.notna() & ((num < lo) | (num > hi))
            if bad.any():
                report.add(df.index[bad], col, f"Out of range (must be {lo}–{hi})")
            if col == "satisfaction_score":
                frac = num.notna() & (num % 1 != 0)
                if frac.any():
                    report.add(df.index[frac], col, "Score must be a whole number")

    # 4. Categories
    for col, allowed in spec["categories"].items():
        if col in df.columns:
            bad = df[col].notna() & ~df[col].isin(allowed)
            if bad.any():
                report.add(df.index[bad], col, "Invalid value (allowed: " + ", ".join(allowed) + ")")

    # 5. Duplicate IDs within the file
    id_col = spec["id"]
    dup = df[id_col].notna() & df.duplicated(subset=[id_col], keep="first")
    report.duplicate_in_file = int(dup.sum())
    if dup.any():
        report.add(df.index[dup], id_col, "Duplicate ID inside the uploaded file")
    for cols in spec["unique_together"]:
        d2 = df.duplicated(subset=cols, keep="first") & df[cols].notna().all(axis=1)
        if d2.any():
            report.add(df.index[d2], "+".join(cols), "Duplicate combination inside the file")

    # 6. Foreign keys (references must exist in DB or in the same file for branches)
    for col, parent in spec["foreign_keys"].items():
        parent_ids = _existing_values(parent, TABLE_SPECS[parent]["id"])
        bad = df[col].notna() & ~df[col].isin(parent_ids)
        if bad.any():
            report.add(df.index[bad], col, f"Unknown reference - not found in '{parent}'")

    # 7. Records already in the database (skipped, not errors)
    existing_ids = _existing_values(table, id_col)
    report.existing_rows |= set(df.index[df[id_col].isin(existing_ids)].tolist())
    for cols in spec["unique_together"]:
        rows = db.fetch_all(f'SELECT {", ".join(chr(34) + c + chr(34) for c in cols)} FROM "{table}"')
        existing = {tuple(r) for r in rows}
        keys = df[cols].astype(object).apply(tuple, axis=1)
        clash = keys.isin(existing) & ~df.index.isin(list(report.existing_rows))
        if clash.any():
            report.add(df.index[clash], "+".join(cols),
                       "A record with this combination already exists in the database")
    return report


# ---------------------------------------------------------------------------
# Data quality report for the live database
# ---------------------------------------------------------------------------
QUALITY_SQL = [
    ("Customers referencing unknown branch", "customers",
     "SELECT COUNT(*) FROM customers c LEFT JOIN branches b ON c.branch_id=b.branch_id WHERE b.branch_id IS NULL"),
    ("Transactions referencing unknown customer", "transactions",
     "SELECT COUNT(*) FROM transactions t LEFT JOIN customers c ON t.customer_id=c.customer_id WHERE c.customer_id IS NULL"),
    ("Transactions with branch different from customer's branch", "transactions",
     "SELECT COUNT(*) FROM transactions t JOIN customers c ON t.customer_id=c.customer_id WHERE t.branch_id<>c.branch_id"),
    ("Loans referencing unknown customer", "loans",
     "SELECT COUNT(*) FROM loans l LEFT JOIN customers c ON l.customer_id=c.customer_id WHERE c.customer_id IS NULL"),
    ("Non-positive transaction amounts", "transactions",
     "SELECT COUNT(*) FROM transactions WHERE amount <= 0 OR amount IS NULL"),
    ("Negative financial values", "branch_financials",
     "SELECT COUNT(*) FROM branch_financials WHERE revenue<0 OR expenses<0 OR deposits<0 OR loan_disbursement<0 OR revenue_target<0"),
    ("Zero revenue targets (achievement cannot be computed)", "branch_financials",
     "SELECT COUNT(*) FROM branch_financials WHERE revenue_target = 0"),
    ("Satisfaction scores outside 1-5", "customer_feedback",
     "SELECT COUNT(*) FROM customer_feedback WHERE satisfaction_score NOT BETWEEN 1 AND 5"),
    ("Outstanding amount greater than loan amount", "loans",
     "SELECT COUNT(*) FROM loans WHERE outstanding_amount > loan_amount"),
    ("Rejected/pending loans with outstanding balance", "loans",
     "SELECT COUNT(*) FROM loans WHERE loan_status IN ('Rejected','Pending') AND outstanding_amount > 0"),
]

DATE_COLUMNS = {
    "branches": "opening_date", "customers": "join_date", "transactions": "transaction_date",
    "loans": "application_date", "branch_financials": "reporting_month",
    "customer_feedback": "feedback_date",
}


def data_quality_summary() -> pd.DataFrame:
    """Run every quality check against the database and return a tidy table."""
    rows = []
    for table, spec in TABLE_SPECS.items():
        total = db.fetch_one(f'SELECT COUNT(*) FROM "{table}"')[0]
        missing = 0
        for col in spec["required"]:
            missing += db.fetch_one(f'SELECT COUNT(*) FROM "{table}" WHERE "{col}" IS NULL OR "{col}" = \'\'')[0]
        rows.append({"Table": table, "Check": "Missing values in required fields",
                     "Issues": missing, "Records": total})
        dup = db.fetch_one(f'SELECT COUNT(*) - COUNT(DISTINCT "{spec["id"]}") FROM "{table}"')[0]
        rows.append({"Table": table, "Check": "Duplicate IDs", "Issues": dup, "Records": total})
        dcol = DATE_COLUMNS[table]
        bad_dates = db.fetch_one(
            f'SELECT COUNT(*) FROM "{table}" WHERE date("{dcol}") IS NULL OR date("{dcol}") <> "{dcol}"')[0]
        rows.append({"Table": table, "Check": f"Invalid dates in {dcol}", "Issues": bad_dates,
                     "Records": total})
    for label, table, sql in QUALITY_SQL:
        total = db.fetch_one(f'SELECT COUNT(*) FROM "{table}"')[0]
        rows.append({"Table": table, "Check": label, "Issues": db.fetch_one(sql)[0], "Records": total})
    out = pd.DataFrame(rows)
    out["Status"] = out["Issues"].map(lambda n: "✅ OK" if n == 0 else "⚠️ Review")
    return out
