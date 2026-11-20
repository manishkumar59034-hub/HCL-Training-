"""Cleaning, validation, duplicate detection, import and data-quality checks."""
import pandas as pd

from analytics import data_import as di
from analytics.data_cleaning import clean_dataframe
from analytics.data_validation import data_quality_summary, validate_dataframe
from database import db


def _fin_rows(month="2026-11-01"):
    return pd.DataFrame({
        "financial_id": [f"FN-BR00{i}-2026-11" for i in range(1, 4)],
        "branch_id": ["BR001", "BR002", "BR003"],
        "reporting_month": [month] * 3,
        "revenue": ["1,00,000", "200000", "₹300000"],
        "expenses": [50000, 60000, 70000], "deposits": [1e6, 2e6, 3e6],
        "loan_disbursement": [0, 0, 0], "revenue_target": [100000, 200000, 300000]})


def test_cleaning_normalises_columns_numbers_dates():
    df = pd.DataFrame({" Branch ID ": ["  BR001 "], "Feedback-Date": ["15/03/2026"], "satisfaction_score": [" 4 "],
                       "feedback_id": ["X1"], "feedback_category": ["service quality"]})
    cleaned, log = clean_dataframe("customer_feedback", df)
    assert "branch_id" in cleaned.columns and "feedback_date" in cleaned.columns
    assert cleaned.loc[0, "branch_id"] == "BR001"
    assert cleaned.loc[0, "feedback_date"] == "2026-03-15"
    assert cleaned.loc[0, "satisfaction_score"] == 4
    assert cleaned.loc[0, "feedback_category"] == "Service Quality"
    assert log


def test_reporting_month_normalised_to_first_day():
    cleaned, _ = clean_dataframe("branch_financials", _fin_rows("2026-11-17"))
    assert set(cleaned["reporting_month"]) == {"2026-11-01"}


def test_validation_detects_every_problem(seeded_db):
    df = _fin_rows()
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)       # duplicate id (row 3)
    df.loc[1, "expenses"] = -5                                   # negative
    df.loc[2, "reporting_month"] = "2026-13-40"                  # invalid date
    df.loc[0, "branch_id"] = "BR999"                             # unknown branch
    cleaned, _ = clean_dataframe("branch_financials", df)
    cleaned.loc[3, "deposits"] = None                            # missing
    rep = validate_dataframe("branch_financials", cleaned)
    problems = rep.issues_df()["Problem"].str.cat(sep=" | ")
    assert "Negative value" in problems
    assert "Invalid date" in problems
    assert "Unknown reference" in problems
    assert "Duplicate ID" in problems
    assert "Missing value" in problems
    assert rep.duplicate_in_file == 1 and rep.has_errors


def test_missing_columns_detected(seeded_db):
    rep = validate_dataframe("loans", pd.DataFrame({"loan_id": ["L1"]}))
    assert "loan_amount" in rep.missing_columns and not rep.is_structurally_valid


def test_out_of_range_score(seeded_db):
    df = pd.DataFrame({"feedback_id": ["Z1"], "branch_id": ["BR001"], "feedback_date": ["2026-01-05"],
                       "satisfaction_score": [7], "feedback_category": ["Other"]})
    cleaned, _ = clean_dataframe("customer_feedback", df)
    assert "Out of range" in validate_dataframe("customer_feedback", cleaned).issues_df()["Problem"].iloc[0]


def test_valid_import_and_duplicate_prevention(seeded_db):
    content = _fin_rows().to_csv(index=False).encode()
    raw = di.read_upload("fin.csv", content)
    cleaned, _, rep = di.prepare("branch_financials", raw)
    assert not rep.has_errors and rep.valid_new_rows == 3
    before = db.table_counts()["branch_financials"]
    res = di.import_data("branch_financials", cleaned, rep, file_name="fin.csv", digest=di.file_hash(content))
    assert res.success and res.inserted == 3
    assert db.table_counts()["branch_financials"] == before + 3
    # same file again -> blocked
    res2 = di.import_data("branch_financials", cleaned, rep, file_name="fin.csv", digest=di.file_hash(content))
    assert not res2.success and "already been imported" in res2.message
    # same rows in a different file -> recognised as existing, nothing duplicated
    content2 = content + b"\n"
    cleaned2, _, rep2 = di.prepare("branch_financials", di.read_upload("fin2.csv", content2))
    assert len(rep2.existing_rows) == 3
    res3 = di.import_data("branch_financials", cleaned2, rep2, file_name="fin2.csv", digest=di.file_hash(content2))
    assert not res3.success
    assert db.table_counts()["branch_financials"] == before + 3


def test_invalid_rows_block_import_unless_partial(seeded_db):
    df = _fin_rows()
    df.loc[1, "revenue"] = "-1"
    content = df.to_csv(index=False).encode()
    cleaned, _, rep = di.prepare("branch_financials", di.read_upload("bad.csv", content))
    before = db.table_counts()["branch_financials"]
    blocked = di.import_data("branch_financials", cleaned, rep, file_name="bad.csv", digest=di.file_hash(content))
    assert not blocked.success and db.table_counts()["branch_financials"] == before
    partial = di.import_data("branch_financials", cleaned, rep, file_name="bad.csv",
                             digest=di.file_hash(content), allow_partial=True)
    assert partial.success and partial.inserted == 2 and partial.skipped_invalid == 1


def test_failed_import_rolls_back_completely(seeded_db, monkeypatch):
    content = _fin_rows().to_csv(index=False).encode()
    cleaned, _, rep = di.prepare("branch_financials", di.read_upload("f.csv", content))
    before = db.table_counts()

    real_insert = db.insert_dataframe

    def failing_insert(conn, table, df, on_conflict="ABORT"):
        real_insert(conn, table, df, on_conflict)   # rows written inside the transaction...
        raise RuntimeError("simulated failure")      # ...then something breaks

    monkeypatch.setattr(db, "insert_dataframe", failing_insert)
    res = di.import_data("branch_financials", cleaned, rep, file_name="f.csv", digest=di.file_hash(content))
    assert not res.success and "rolled back" in res.message
    assert db.table_counts() == before


def test_excel_import(seeded_db, tmp_path):
    path = tmp_path / "fb.xlsx"
    pd.DataFrame({"feedback_id": ["FBX001"], "branch_id": ["BR002"], "feedback_date": ["2026-10-02"],
                  "satisfaction_score": [5], "feedback_category": ["Digital Services"]}).to_excel(path, index=False)
    content = path.read_bytes()
    cleaned, _, rep = di.prepare("customer_feedback", di.read_upload("fb.xlsx", content))
    res = di.import_data("customer_feedback", cleaned, rep, file_name="fb.xlsx", digest=di.file_hash(content))
    assert res.success and res.inserted == 1


def test_unsupported_file_type():
    try:
        di.read_upload("data.txt", b"abc")
        assert False
    except di.ImportErrorMessage:
        pass


def test_data_quality_summary_clean_on_demo(seeded_db):
    q = data_quality_summary()
    assert int(q["Issues"].sum()) == 0
    assert {"Duplicate IDs", "Satisfaction scores outside 1-5"} <= set(q["Check"])
