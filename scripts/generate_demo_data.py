"""
Synthetic data generator.

Creates realistic but entirely FICTIONAL banking data with a fixed random seed,
so every run produces exactly the same numbers. No real customer data is used:
customers are labelled "Customer 000123" etc.

Each branch is given a deliberate "profile" so the dashboard has a story to tell:
some branches beat target, some are average, some underperform; some have
rising expenses, strong customer growth, heavy loan activity, high defaults
or poor satisfaction.

Run on its own to write CSVs into data/raw/ :
    python scripts/generate_demo_data.py
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402


@dataclass
class BranchProfile:
    name: str
    city: str
    state: str
    region: str
    branch_type: str
    opening_date: str
    size: float              # monthly revenue target scale (INR)
    achievement: float       # mean revenue / target ratio
    revenue_trend: float     # monthly revenue growth rate
    expense_ratio: float     # starting expenses / revenue
    expense_trend: float     # monthly growth of expense ratio
    customer_weight: float   # share of customers
    new_customer_share: float  # share of customers that join during the window
    loan_weight: float       # loan activity multiplier
    approval_rate: float     # share of decided applications approved
    default_rate: float      # share of disbursed loans that default
    satisfaction: float      # mean feedback score (1-5)
    satisfaction_trend: float  # change in mean score per month
    status: str = "Active"


# fmt: off
#                name                         city          state             region     type         opened        size        ach   rTrend  expR  eTrend  custW  newSh  loanW appr  dflt  sat   sTrend
PROFILES = [
    BranchProfile("Mumbai Fort Main",        "Mumbai",     "Maharashtra",    "West",    "Metro",      "1998-04-01", 9_500_000, 1.12,  0.012, 0.58, 0.000, 1.60, 0.22, 1.50, 0.78, 0.03, 4.3,  0.00),
    BranchProfile("Mumbai Andheri East",     "Mumbai",     "Maharashtra",    "West",    "Metro",      "2006-07-15", 7_200_000, 1.03,  0.008, 0.66, 0.002, 1.35, 0.25, 1.30, 0.74, 0.05, 4.0,  0.00),
    BranchProfile("Pune Shivajinagar",       "Pune",       "Maharashtra",    "West",    "Urban",      "2009-01-10", 5_000_000, 1.08,  0.015, 0.62, 0.000, 1.10, 0.38, 1.10, 0.76, 0.04, 4.2,  0.01),
    BranchProfile("Ahmedabad CG Road",       "Ahmedabad",  "Gujarat",        "West",    "Urban",      "2004-11-20", 4_600_000, 0.92,  0.004, 0.70, 0.003, 1.00, 0.20, 1.00, 0.70, 0.06, 3.9,  0.00),
    BranchProfile("Surat Ring Road",         "Surat",      "Gujarat",        "West",    "Urban",      "2012-03-05", 3_800_000, 0.86, -0.002, 0.74, 0.004, 0.85, 0.18, 0.90, 0.66, 0.07, 3.7, -0.01),
    BranchProfile("New Delhi Connaught Place","New Delhi", "Delhi",          "North",   "Metro",      "1995-08-01", 9_000_000, 1.06,  0.010, 0.60, 0.001, 1.50, 0.20, 1.40, 0.75, 0.04, 4.1,  0.00),
    BranchProfile("Gurugram Cyber City",     "Gurugram",   "Haryana",        "North",   "Metro",      "2014-02-14", 6_200_000, 1.15,  0.020, 0.55, 0.000, 1.20, 0.45, 1.60, 0.80, 0.03, 4.4,  0.01),
    BranchProfile("Lucknow Hazratganj",      "Lucknow",    "Uttar Pradesh",  "North",   "Urban",      "2001-06-18", 3_500_000, 0.72, -0.008, 0.82, 0.006, 0.90, 0.12, 0.80, 0.58, 0.12, 3.2, -0.02),
    BranchProfile("Jaipur MI Road",          "Jaipur",     "Rajasthan",      "North",   "Urban",      "2007-09-09", 3_900_000, 0.95,  0.006, 0.68, 0.000, 0.95, 0.24, 0.95, 0.72, 0.05, 3.9,  0.00),
    BranchProfile("Bengaluru MG Road",       "Bengaluru",  "Karnataka",      "South",   "Metro",      "2000-05-22", 8_400_000, 1.10,  0.014, 0.59, 0.000, 1.45, 0.30, 1.35, 0.77, 0.04, 4.3,  0.00),
    BranchProfile("Bengaluru Whitefield",    "Bengaluru",  "Karnataka",      "South",   "Metro",      "2016-10-03", 5_600_000, 1.01,  0.022, 0.64, 0.000, 1.25, 0.55, 1.20, 0.76, 0.05, 4.1,  0.01),
    BranchProfile("Chennai T Nagar",         "Chennai",    "Tamil Nadu",     "South",   "Metro",      "1997-12-12", 7_000_000, 0.97,  0.005, 0.67, 0.002, 1.30, 0.18, 1.10, 0.73, 0.05, 4.0,  0.00),
    BranchProfile("Hyderabad Banjara Hills", "Hyderabad",  "Telangana",      "South",   "Metro",      "2005-04-27", 6_800_000, 0.89,  0.003, 0.72, 0.005, 1.20, 0.22, 1.70, 0.79, 0.11, 3.8,  0.00),
    BranchProfile("Kochi Marine Drive",      "Kochi",      "Kerala",         "South",   "Urban",      "2010-08-30", 3_200_000, 1.04,  0.009, 0.63, 0.000, 0.75, 0.28, 0.70, 0.74, 0.03, 4.5,  0.00),
    BranchProfile("Kolkata Park Street",     "Kolkata",    "West Bengal",    "East",    "Metro",      "1996-03-15", 6_000_000, 0.83, -0.004, 0.78, 0.004, 1.15, 0.14, 1.00, 0.68, 0.08, 3.6, -0.01),
    BranchProfile("Bhubaneswar Saheed Nagar","Bhubaneswar","Odisha",         "East",    "Urban",      "2013-01-21", 2_600_000, 0.91,  0.010, 0.70, 0.000, 0.70, 0.35, 0.75, 0.71, 0.05, 4.0,  0.00),
    BranchProfile("Patna Fraser Road",       "Patna",      "Bihar",          "East",    "Semi-Urban", "2011-07-07", 2_200_000, 0.68, -0.010, 0.88, 0.007, 0.80, 0.10, 0.85, 0.55, 0.15, 3.0, -0.02, "Under Review"),
    BranchProfile("Guwahati GS Road",        "Guwahati",   "Assam",          "East",    "Semi-Urban", "2015-11-11", 1_900_000, 0.79,  0.002, 0.80, 0.003, 0.60, 0.26, 0.60, 0.64, 0.09, 3.5,  0.00),
    BranchProfile("Indore Vijay Nagar",      "Indore",     "Madhya Pradesh", "Central", "Urban",      "2012-09-19", 3_000_000, 1.02,  0.016, 0.64, 0.000, 0.85, 0.42, 1.00, 0.75, 0.04, 4.2,  0.01),
    BranchProfile("Nagpur Sitabuldi",        "Nagpur",     "Maharashtra",    "Central", "Rural",      "2003-02-02", 1_600_000, 0.84,  0.000, 0.76, 0.002, 0.55, 0.15, 0.65, 0.69, 0.07, 3.8,  0.00),
]
# fmt: on

CUSTOMER_TYPES = ["Individual", "Business", "Corporate", "NRI", "Senior Citizen"]
CUSTOMER_TYPE_P = [0.62, 0.16, 0.05, 0.05, 0.12]
GENDERS = ["Male", "Female", "Other"]
GENDER_P = [0.54, 0.44, 0.02]
AGE_GROUPS = ["18-25", "26-35", "36-45", "46-60", "60+"]
AGE_P = [0.14, 0.30, 0.26, 0.20, 0.10]

TX_TYPES = ["Deposit", "Withdrawal", "Transfer", "Bill Payment", "Loan Repayment"]
TX_TYPE_P = [0.34, 0.26, 0.20, 0.13, 0.07]
TX_MEAN_AMOUNT = {"Deposit": 42_000, "Withdrawal": 18_000, "Transfer": 30_000,
                  "Bill Payment": 4_500, "Loan Repayment": 22_000}
CHANNELS = ["Branch", "ATM", "Mobile Banking", "Internet Banking", "UPI"]
CHANNEL_P = [0.18, 0.17, 0.27, 0.13, 0.25]

LOAN_TYPES = ["Home Loan", "Personal Loan", "Vehicle Loan", "Business Loan", "Education Loan", "Gold Loan"]
LOAN_TYPE_P = [0.18, 0.28, 0.17, 0.14, 0.08, 0.15]
LOAN_RANGE = {  # (min, max) INR
    "Home Loan": (1_500_000, 6_000_000), "Personal Loan": (100_000, 800_000),
    "Vehicle Loan": (300_000, 1_500_000), "Business Loan": (500_000, 4_000_000),
    "Education Loan": (200_000, 1_500_000), "Gold Loan": (50_000, 300_000),
}
LOAN_RATE = {"Home Loan": 8.6, "Personal Loan": 12.5, "Vehicle Loan": 9.4,
             "Business Loan": 11.2, "Education Loan": 9.9, "Gold Loan": 9.0}
LOAN_TENURE_MONTHS = {"Home Loan": 240, "Personal Loan": 48, "Vehicle Loan": 60,
                      "Business Loan": 84, "Education Loan": 96, "Gold Loan": 12}

FEEDBACK_CATEGORIES = ["Service Quality", "Waiting Time", "Staff Behaviour",
                       "Digital Services", "Loan Processing", "Account Services", "Other"]
FEEDBACK_P = [0.24, 0.18, 0.14, 0.16, 0.10, 0.13, 0.05]


def month_starts(start: str, n: int) -> list[pd.Timestamp]:
    return list(pd.date_range(pd.Timestamp(start + "-01"), periods=n, freq="MS"))


def _random_dates(rng: np.random.Generator, start: pd.Timestamp, end: pd.Timestamp,
                  n: int) -> pd.Series:
    span = max((end - start).days, 1)
    offsets = rng.integers(0, span + 1, size=n)
    return pd.Series(start + pd.to_timedelta(offsets, unit="D"))


def generate_all(seed: int = settings.RANDOM_SEED,
                 n_customers: int = settings.DEMO_NUM_CUSTOMERS,
                 n_transactions: int = settings.DEMO_NUM_TRANSACTIONS,
                 n_loans: int = settings.DEMO_NUM_LOANS,
                 start_month: str = settings.DEMO_START_MONTH,
                 n_months: int = settings.DEMO_NUM_MONTHS) -> dict[str, pd.DataFrame]:
    """Generate every table as a DataFrame. Deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    months = month_starts(start_month, n_months)
    window_start = months[0]
    window_end = months[-1] + pd.offsets.MonthEnd(0)

    # ---------------- branches ----------------
    branches = pd.DataFrame([{
        "branch_id": f"BR{i + 1:03d}", "branch_name": p.name, "city": p.city, "state": p.state,
        "region": p.region, "branch_type": p.branch_type, "opening_date": p.opening_date,
        "status": p.status,
    } for i, p in enumerate(PROFILES)])
    profiles = {f"BR{i + 1:03d}": p for i, p in enumerate(PROFILES)}

    # ---------------- customers ----------------
    weights = np.array([p.customer_weight for p in PROFILES])
    branch_ids = rng.choice(branches["branch_id"], size=n_customers, p=weights / weights.sum())
    branch_ids = np.sort(branch_ids)
    join_dates = []
    for bid in branch_ids:
        p = profiles[bid]
        if rng.random() < p.new_customer_share:
            # joined during the analysis window, more often later for growing branches
            u = rng.random() ** (0.8 if p.new_customer_share > 0.3 else 1.1)
            day = int(u * (window_end - window_start).days)
            join_dates.append(window_start + pd.Timedelta(days=day))
        else:
            opened = max(pd.Timestamp(p.opening_date), pd.Timestamp("2015-01-01"))
            span = (window_start - pd.Timedelta(days=1) - opened).days
            join_dates.append(opened + pd.Timedelta(days=int(rng.integers(0, max(span, 1)))))
    customers = pd.DataFrame({
        "customer_id": [f"CU{i + 1:06d}" for i in range(n_customers)],
        "branch_id": branch_ids,
        "customer_type": rng.choice(CUSTOMER_TYPES, size=n_customers, p=CUSTOMER_TYPE_P),
        "gender": rng.choice(GENDERS, size=n_customers, p=GENDER_P),
        "age_group": rng.choice(AGE_GROUPS, size=n_customers, p=AGE_P),
        "join_date": pd.to_datetime(join_dates),
        "status": rng.choice(["Active", "Inactive", "Closed"], size=n_customers, p=[0.86, 0.10, 0.04]),
    })
    customers.insert(2, "customer_name", "Customer " + customers["customer_id"].str[2:])
    customers["city"] = customers["branch_id"].map(branches.set_index("branch_id")["city"])
    customers = customers[["customer_id", "branch_id", "customer_name", "customer_type", "gender",
                           "age_group", "join_date", "city", "status"]]

    # ---------------- transactions ----------------
    # Pick each transaction date uniformly in the window, then pick a customer who had
    # already joined by that date (weighted: business customers transact more).
    order = customers["join_date"].sort_values().index.to_numpy()
    sorted_join = customers.loc[order, "join_date"].to_numpy()
    window_days = (window_end - window_start).days

    def pick_customers(dates: pd.Series, weights: np.ndarray) -> np.ndarray:
        cum = np.cumsum(weights[order])
        eligible = np.searchsorted(sorted_join, dates.to_numpy(), side="right")
        eligible = np.maximum(eligible, 1)
        draws = rng.random(len(dates)) * cum[eligible - 1]
        return order[np.minimum(np.searchsorted(cum, draws, side="right"), eligible - 1)]

    tx_dates = pd.Series(window_start + pd.to_timedelta(rng.integers(0, window_days + 1, n_transactions), unit="D"))
    cust_weights = np.where(customers["customer_type"].isin(["Business", "Corporate"]), 3.0, 1.0)
    tx_cust = customers.loc[pick_customers(tx_dates, cust_weights)].reset_index(drop=True)
    tx_types = rng.choice(TX_TYPES, size=n_transactions, p=TX_TYPE_P)
    means = np.array([TX_MEAN_AMOUNT[t] for t in tx_types])
    amounts = np.round(rng.lognormal(np.log(means), 0.7), 2)
    transactions = pd.DataFrame({
        "transaction_id": [f"TX{i + 1:07d}" for i in range(n_transactions)],
        "customer_id": tx_cust["customer_id"],
        "branch_id": tx_cust["branch_id"],
        "transaction_date": tx_dates,
        "transaction_type": tx_types,
        "amount": np.maximum(amounts, 10.0),
        "channel": rng.choice(CHANNELS, size=n_transactions, p=CHANNEL_P),
        "status": rng.choice(["Success", "Failed", "Reversed"], size=n_transactions, p=[0.955, 0.035, 0.01]),
    }).sort_values("transaction_date").reset_index(drop=True)
    transactions["transaction_id"] = [f"TX{i + 1:07d}" for i in range(n_transactions)]

    # ---------------- loans ----------------
    loan_w = np.array([profiles[b].loan_weight for b in customers["branch_id"]])
    app_dates = pd.Series(window_start + pd.to_timedelta(rng.integers(0, window_days + 1, n_loans), unit="D"))
    loan_cust = customers.loc[pick_customers(app_dates, loan_w)].reset_index(drop=True)
    loan_rows = []
    for i in range(n_loans):
        bid = loan_cust.at[i, "branch_id"]
        p = profiles[bid]
        ltype = rng.choice(LOAN_TYPES, p=LOAN_TYPE_P)
        lo, hi = LOAN_RANGE[ltype]
        amount = float(round(rng.uniform(lo, hi) / 1000) * 1000)
        rate = round(LOAN_RATE[ltype] + rng.normal(0, 0.6), 2)
        app_date = app_dates.iloc[i]
        age_days = (window_end - app_date).days
        # recent applications may still be pending
        if age_days < 25 and rng.random() < 0.6:
            status = "Pending"
        elif rng.random() < p.approval_rate:
            status = "Approved" if age_days < 40 and rng.random() < 0.5 else "Disbursed"
        else:
            status = "Rejected"
        outstanding, repayment = 0.0, "Not Applicable"
        if status == "Disbursed":
            tenure = LOAN_TENURE_MONTHS[ltype]
            months_elapsed = max(age_days // 30, 0)
            if ltype == "Gold Loan" and months_elapsed >= tenure:
                status, repayment = "Closed", "Repaid"
            else:
                r = rng.random()
                if r < p.default_rate:
                    repayment = "Defaulted"
                    paid = min(months_elapsed, 4) / tenure
                elif r < p.default_rate * 2.2:
                    repayment = "Overdue"
                    paid = months_elapsed * 0.7 / tenure
                else:
                    repayment = "Current"
                    paid = months_elapsed / tenure
                outstanding = round(amount * max(0.0, 1 - paid), 2)
        loan_rows.append({
            "loan_id": f"LN{i + 1:06d}", "customer_id": loan_cust.at[i, "customer_id"],
            "branch_id": bid, "application_date": app_date, "loan_type": ltype,
            "loan_amount": amount, "interest_rate": rate, "loan_status": status,
            "outstanding_amount": outstanding, "repayment_status": repayment,
        })
    loans = pd.DataFrame(loan_rows).sort_values("application_date").reset_index(drop=True)
    loans["loan_id"] = [f"LN{i + 1:06d}" for i in range(len(loans))]

    # ---------------- branch_financials ----------------
    disb = loans[loans["loan_status"].isin(settings.DISBURSED_LOAN_STATUSES)].copy()
    disb["month"] = disb["application_date"].dt.to_period("M").dt.to_timestamp()
    disb_by = disb.groupby(["branch_id", "month"])["loan_amount"].sum()
    fin_rows = []
    for bid, p in profiles.items():
        for m_idx, month in enumerate(months):
            seasonal = 1 + 0.05 * np.sin(2 * np.pi * (month.month - 3) / 12)
            target = p.size * (1.008 ** m_idx)
            revenue = p.size * p.achievement * (1 + p.revenue_trend) ** m_idx * seasonal \
                * rng.normal(1.0, 0.045)
            exp_ratio = p.expense_ratio * (1 + p.expense_trend) ** m_idx * rng.normal(1.0, 0.03)
            expenses = revenue * exp_ratio
            deposits = revenue * rng.normal(32, 2.5) * (1 + p.revenue_trend * 0.8) ** m_idx
            fin_rows.append({
                "financial_id": f"FN-{bid}-{month:%Y-%m}", "branch_id": bid,
                "reporting_month": month, "revenue": round(max(revenue, 0), 2),
                "expenses": round(max(expenses, 0), 2), "deposits": round(max(deposits, 0), 2),
                "loan_disbursement": round(float(disb_by.get((bid, month), 0.0)), 2),
                "revenue_target": round(target, 2),
            })
    financials = pd.DataFrame(fin_rows)

    # ---------------- customer_feedback ----------------
    fb_rows = []
    fb_id = 1
    for bid, p in profiles.items():
        for m_idx, month in enumerate(months):
            n = int(rng.integers(6, 13) * p.customer_weight)
            mean = np.clip(p.satisfaction + p.satisfaction_trend * m_idx, 1.5, 4.9)
            scores = np.clip(np.rint(rng.normal(mean, 0.85, size=n)), 1, 5).astype(int)
            dates = _random_dates(rng, month, month + pd.offsets.MonthEnd(0), n)
            cats = rng.choice(FEEDBACK_CATEGORIES, size=n, p=FEEDBACK_P)
            for s, d, c in zip(scores, dates, cats):
                fb_rows.append({"feedback_id": f"FB{fb_id:06d}", "branch_id": bid,
                                "feedback_date": d, "satisfaction_score": int(s),
                                "feedback_category": c})
                fb_id += 1
    feedback = pd.DataFrame(fb_rows)

    data = {
        "branches": branches, "customers": customers, "transactions": transactions,
        "loans": loans, "branch_financials": financials, "customer_feedback": feedback,
    }
    for df in data.values():
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
    return data


def write_csvs(data: dict[str, pd.DataFrame], folder: Path = settings.RAW_DIR) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for table, df in data.items():
        path = folder / f"{table}.csv"
        df.to_csv(path, index=False)
        paths.append(path)
    return paths


def write_sample_import_files(data: dict[str, pd.DataFrame],
                              folder: Path = settings.SAMPLES_DIR) -> list[Path]:
    """Small files for demonstrating the Data Management import feature.

    * sample_financials_next_month.csv - one valid new month for every branch
    * sample_financials_with_errors.csv - same, with deliberate problems
    * sample_feedback_next_month.xlsx  - a valid Excel import
    """
    folder.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(settings.RANDOM_SEED + 1)
    fin = data["branch_financials"].copy()
    last_month = pd.Timestamp(fin["reporting_month"].max())
    next_month = last_month + pd.offsets.MonthBegin(1)
    latest = fin[fin["reporting_month"] == last_month.strftime("%Y-%m-%d")].copy()
    latest["reporting_month"] = next_month.strftime("%Y-%m-%d")
    latest["financial_id"] = "FN-" + latest["branch_id"] + f"-{next_month:%Y-%m}"
    for col in ("revenue", "expenses", "deposits"):
        latest[col] = (latest[col] * rng.normal(1.01, 0.03, len(latest))).round(2)
    latest["loan_disbursement"] = 0.0
    latest["revenue_target"] = (latest["revenue_target"] * 1.008).round(2)
    good = folder / "sample_financials_next_month.csv"
    latest.to_csv(good, index=False)

    bad = latest.copy().head(8).reset_index(drop=True)
    bad.loc[1, "revenue"] = -50000                    # negative value
    bad.loc[2, "reporting_month"] = "2026-13-45"     # invalid date
    bad.loc[3, "branch_id"] = "BR999"                # unknown branch
    bad.loc[4, "expenses"] = None                    # missing value
    bad.loc[5, "financial_id"] = bad.loc[0, "financial_id"]  # duplicate id
    bad_path = folder / "sample_financials_with_errors.csv"
    bad.to_csv(bad_path, index=False)

    fb_rows = []
    start_id = len(data["customer_feedback"]) + 1
    for i, bid in enumerate(data["branches"]["branch_id"]):
        for j in range(5):
            fb_rows.append({
                "feedback_id": f"FB{start_id + i * 5 + j:06d}", "branch_id": bid,
                "feedback_date": (next_month + pd.Timedelta(days=int(rng.integers(0, 28)))).strftime("%Y-%m-%d"),
                "satisfaction_score": int(rng.integers(2, 6)),
                "feedback_category": str(rng.choice(FEEDBACK_CATEGORIES)),
            })
    xlsx = folder / "sample_feedback_next_month.xlsx"
    pd.DataFrame(fb_rows).to_excel(xlsx, index=False)
    return [good, bad_path, xlsx]


if __name__ == "__main__":
    generated = generate_all()
    for path in write_csvs(generated):
        print(f"Wrote {path.relative_to(settings.BASE_DIR)}")
    for path in write_sample_import_files(generated):
        print(f"Wrote {path.relative_to(settings.BASE_DIR)}")
    for name, frame in generated.items():
        print(f"  {name:<18} {len(frame):>6} rows")
