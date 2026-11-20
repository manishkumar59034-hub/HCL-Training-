"""KPI formulas, division by zero, empty data, filters, consistency and exports."""
from datetime import date

import pandas as pd
import pytest

from analytics import branch_analysis as ba
from analytics import insights as ins
from analytics import kpi_calculations as kpi
from analytics import queries as q
from utils.formatting import fmt_inr, fmt_pct, indian_grouping


# ---------------- scalar formulas ----------------
def test_basic_formulas():
    assert kpi.net_profit(1000, 600) == 400
    assert kpi.profit_margin(1000, 600) == pytest.approx(40.0)
    assert kpi.target_achievement(900, 1000) == pytest.approx(90.0)
    assert kpi.growth_rate(110, 100) == pytest.approx(10.0)
    assert kpi.growth_rate(90, 100) == pytest.approx(-10.0)
    assert kpi.approval_rate(30, 40) == pytest.approx(75.0)
    assert kpi.default_rate(3, 60) == pytest.approx(5.0)
    assert kpi.avg_revenue_per_customer(1000, 4) == 250


def test_division_by_zero_and_nulls_return_none():
    assert kpi.profit_margin(0, 100) is None
    assert kpi.target_achievement(100, 0) is None
    assert kpi.growth_rate(100, 0) is None
    assert kpi.growth_rate(100, None) is None
    assert kpi.approval_rate(0, 0) is None
    assert kpi.safe_divide(float("nan"), 2) is None
    assert kpi.net_profit(None, 5) is None


def test_performance_category_thresholds():
    assert kpi.performance_category(100) == "High Performer"
    assert kpi.performance_category(99.9) == "Average Performer"
    assert kpi.performance_category(80) == "Average Performer"
    assert kpi.performance_category(79.9) == "Low Performer"
    assert kpi.performance_category(None) == "Not Rated"
    assert kpi.performance_category(95, high=90, average=70) == "High Performer"


def test_period_change_and_no_previous_month():
    assert kpi.period_change(pd.Series([100])) is None
    assert kpi.latest_vs_previous(pd.Series([100])) is None
    assert kpi.period_change(pd.Series([100, 120])) == pytest.approx(20)
    s = pd.Series([100, 100, 100, 130, 130, 130])
    assert kpi.period_change(s) == pytest.approx(30)


def test_empty_dataset_kpis():
    f = kpi.financial_kpis(pd.DataFrame())
    assert all(v is None for v in f.values())
    assert kpi.customer_kpis(pd.DataFrame())["total"] == 0
    assert kpi.loan_kpis(pd.DataFrame())["approval_rate"] is None
    assert ba.branch_summary(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()).empty
    assert ins.generate_insights(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()) == []


def test_loan_kpis_distinguish_statuses():
    loans = pd.DataFrame({
        "loan_id": list("ABCDEF"),
        "loan_status": ["Pending", "Approved", "Rejected", "Disbursed", "Disbursed", "Closed"],
        "repayment_status": ["Not Applicable", "Not Applicable", "Not Applicable", "Defaulted", "Current", "Repaid"],
        "loan_amount": [10, 20, 30, 40, 50, 60], "outstanding_amount": [0, 0, 0, 40, 25, 0],
        "interest_rate": [9] * 6})
    k = kpi.loan_kpis(loans)
    assert k["applications"] == 6 and k["approved"] == 4 and k["rejected"] == 1 and k["pending"] == 1
    assert k["disbursed_count"] == 3 and k["defaulted"] == 1
    assert k["disbursed_amount"] == 150 and k["outstanding"] == 65
    assert k["approval_rate"] == pytest.approx(4 / 6 * 100)
    assert k["default_rate"] == pytest.approx(100 / 3)


# ---------------- formatting ----------------
def test_indian_currency_format():
    assert indian_grouping(1245678) == "12,45,678"
    assert fmt_inr(1245678) == "₹12,45,678"
    assert fmt_inr(32_10_00_000, short=True) == "₹32.10 Cr"
    assert fmt_inr(None) == "N/A" and fmt_pct(None) == "N/A"


# ---------------- database-backed KPIs and filters ----------------
def test_kpis_match_direct_sql(seeded_db):
    fin = q.get_financials(q.Filters())
    k = kpi.financial_kpis(fin)
    from database import db
    rev, exp = db.fetch_one("SELECT SUM(revenue), SUM(expenses) FROM branch_financials")
    assert k["revenue"] == pytest.approx(rev)
    assert k["profit"] == pytest.approx(rev - exp)


def test_date_filtering(seeded_db):
    f = q.Filters(start_date=date(2026, 1, 1), end_date=date(2026, 3, 31))
    fin = q.get_financials(f)
    assert set(fin["reporting_month"].dt.strftime("%Y-%m")) == {"2026-01", "2026-02", "2026-03"}
    tx = q.get_transactions(f)
    assert tx["transaction_date"].min() >= pd.Timestamp("2026-01-01")
    assert tx["transaction_date"].max() <= pd.Timestamp("2026-03-31")
    all_rev = kpi.financial_kpis(q.get_financials(q.Filters()))["revenue"]
    assert kpi.financial_kpis(fin)["revenue"] < all_rev


def test_month_filter(seeded_db):
    fin = q.get_financials(q.Filters(month=6))
    assert set(fin["reporting_month"].dt.month) == {6}


def test_branch_and_region_filtering(seeded_db):
    one = q.get_financials(q.Filters(branch_ids=["BR001"]))
    assert set(one["branch_id"]) == {"BR001"}
    south = q.get_branches(q.Filters(regions=["South"]))
    assert set(south["region"]) == {"South"}
    cust = q.get_customers(q.Filters(cities=["Mumbai"]))
    assert set(cust["city"]) == {"Mumbai"}


def test_filter_with_no_matching_data(seeded_db):
    f = q.Filters(start_date=date(2001, 1, 1), end_date=date(2001, 12, 31))
    fin = q.get_financials(f)
    assert fin.empty
    assert kpi.financial_kpis(fin)["revenue"] is None


def test_kpi_consistent_across_modules(seeded_db):
    """Total Loan Disbursement and revenue must be identical whichever page computes them."""
    f = q.Filters()
    fin, loans = q.get_financials(f), q.get_loans(f)
    branches, cust, fb = q.get_branches(f), q.get_customers(f), q.get_feedback(f)
    summary = ba.branch_summary(branches, fin, cust, fb, loans)
    assert summary["revenue"].sum() == pytest.approx(kpi.financial_kpis(fin)["revenue"])
    # Demo financials loan_disbursement are built from the loan register -> must reconcile
    assert kpi.financial_kpis(fin)["loan_disbursement"] == pytest.approx(kpi.loan_kpis(loans)["disbursed_amount"])
    bk = ba.branch_kpis(summary)
    assert bk["avg_achievement"] == pytest.approx(kpi.financial_kpis(fin)["target_achievement"])


def test_insights_generated_and_respect_filters(seeded_db):
    def run(f):
        fin = q.get_financials(f)
        s = ba.branch_summary(q.get_branches(f), fin, q.get_customers(f), q.get_feedback(f), q.get_loans(f))
        return ins.generate_insights(s, fin, q.get_feedback(f))
    all_items = run(q.Filters())
    assert any(i.category == "Positive" for i in all_items)
    assert any(i.category == "Warning" and i.action for i in all_items)
    one = run(q.Filters(branch_ids=["BR017"]))   # Patna - designed to underperform
    branches = {i.branch for i in one} - {"Bank-wide", "Multiple"}
    assert branches == {"Patna Fraser Road"}
    assert any(i.rule == "low_target" for i in one)


def test_report_export(seeded_db):
    from components.data_loader import _load
    from utils import exports
    f = q.Filters(regions=["West"])
    ds = _load.__wrapped__(f, "test", 100.0, 80.0) if hasattr(_load, "__wrapped__") else _load(f, "test", 100.0, 80.0)
    branch_report = exports.REPORTS["Branch performance report"](ds)
    assert set(branch_report["Region"]) == {"West"}
    assert "Target Achievement %" in branch_report.columns
    tx = exports.transactions_export(ds)
    assert set(tx["Region"]) == {"West"}
    xlsx = exports.full_report(ds)
    assert xlsx[:2] == b"PK" and len(xlsx) > 5000
    xl = pd.ExcelFile(__import__("io").BytesIO(xlsx))
    assert "Filters" in xl.sheet_names and len(xl.sheet_names) == 7
    assert exports.csv_bytes(branch_report).startswith(b"\xef\xbb\xbf")
