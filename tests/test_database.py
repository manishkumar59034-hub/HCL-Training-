"""Database creation, schema, foreign keys, seeding, reset and backup."""
import sqlite3

import pytest

from database import db
from scripts.backup_database import backup_database
from scripts.generate_demo_data import generate_all
from scripts.reset_demo_data import reset_demo_data
from scripts.seed_database import seed

EXPECTED_TABLES = {"branches", "customers", "transactions", "loans", "branch_financials",
                   "customer_feedback", "managers", "import_log", "app_metadata"}


def test_database_and_tables_created(empty_db):
    assert empty_db.exists()
    names = {r[0] for r in db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")}
    assert EXPECTED_TABLES <= names


def test_indexes_created(empty_db):
    idx = {r[0] for r in db.fetch_all("SELECT name FROM sqlite_master WHERE type='index'")}
    for name in ("idx_tx_date", "idx_fin_month", "idx_loans_status", "idx_customers_branch", "idx_tx_customer"):
        assert name in idx


def test_init_is_idempotent(empty_db):
    db.init_db()
    db.init_db()
    assert db.table_counts()["branches"] == 0


def test_foreign_keys_enforced(empty_db):
    with pytest.raises(db.DatabaseError):
        db.execute("INSERT INTO customers (customer_id, branch_id, customer_name, customer_type, join_date, city, status)"
                   " VALUES ('CU1','NOPE','Customer 1','Individual','2025-01-01','X','Active')")


def test_check_constraints(empty_db):
    db.execute("INSERT INTO branches VALUES ('BR001','B','C','S','North','Urban','2010-01-01','Active')")
    with pytest.raises(db.DatabaseError):
        db.execute("INSERT INTO customer_feedback VALUES ('F1','BR001','2025-01-01',9,'Other')")


def test_transaction_rolls_back(empty_db):
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction() as conn:
            conn.execute("INSERT INTO branches VALUES ('BR001','B','C','S','North','Urban','2010-01-01','Active')")
            conn.execute("INSERT INTO branches VALUES ('BR001','B2','C','S','North','Urban','2010-01-01','Active')")
    assert db.table_counts()["branches"] == 0


def test_demo_data_generation_is_reproducible_and_in_range():
    a, b = generate_all(), generate_all()
    for t in a:
        assert a[t].equals(b[t]), f"{t} not reproducible"
    assert 15 <= len(a["branches"]) <= 25
    assert 1000 <= len(a["customers"]) <= 3000
    assert 5000 <= len(a["transactions"]) <= 15000
    assert 500 <= len(a["loans"]) <= 1000
    assert a["branch_financials"]["reporting_month"].nunique() >= 12
    assert len(a["customer_feedback"]) > 0


def test_demo_data_has_varied_performance():
    fin = generate_all()["branch_financials"]
    g = fin.groupby("branch_id")[["revenue", "revenue_target"]].sum()
    ach = g["revenue"] / g["revenue_target"] * 100
    assert (ach >= 100).any() and ((ach >= 80) & (ach < 100)).any() and (ach < 80).any()


def test_seed_populates_and_relations_valid(seeded_db):
    counts = db.table_counts()
    assert counts["branches"] == 20 and counts["customers"] > 0 and counts["transactions"] > 0
    rep = db.integrity_report()
    assert rep["integrity"] == "ok" and rep["foreign_key_violations"] == 0
    orphans = db.fetch_one("SELECT COUNT(*) FROM transactions t LEFT JOIN customers c "
                           "ON c.customer_id=t.customer_id WHERE c.customer_id IS NULL")[0]
    assert orphans == 0


def test_seed_does_not_overwrite_existing_data(seeded_db):
    db.execute("DELETE FROM customer_feedback WHERE feedback_id = 'FB000001'")
    before = db.table_counts()
    assert seed(verbose=False) == {}
    assert db.table_counts() == before


def test_reset_restores_demo_data_and_keeps_managers(seeded_db):
    from auth.authentication import create_manager
    create_manager("keepme", "Keep@Me123", "Keep")
    db.execute("DELETE FROM customer_feedback")
    result = reset_demo_data()
    assert db.table_counts()["customer_feedback"] > 0
    assert db.fetch_one("SELECT COUNT(*) FROM managers")[0] == 1
    assert result["backup"] and __import__("pathlib").Path(result["backup"]).exists()


def test_backup_creates_valid_copy(seeded_db, tmp_path):
    out = backup_database(dest_dir=tmp_path / "bk")
    assert out.exists() and out.stat().st_size > 0
    conn = sqlite3.connect(out)
    assert conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0] == 20
    conn.close()
