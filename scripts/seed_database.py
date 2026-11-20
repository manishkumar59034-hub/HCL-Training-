"""
Initialise the SQLite database and load the synthetic demo data.

    python scripts/seed_database.py

Safe by design: if the database already contains business data, nothing is
overwritten. To replace existing data use scripts/reset_demo_data.py, which
asks for confirmation and makes a backup first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database import db  # noqa: E402
from scripts.generate_demo_data import generate_all, write_csvs, write_sample_import_files  # noqa: E402


def has_business_data(db_path=None) -> bool:
    counts = db.table_counts(db_path)
    return any(counts.get(t, 0) > 0 for t in db.DATA_TABLES)


def load_demo_data(conn, data=None) -> dict[str, int]:
    """Insert generated data using an open transaction connection."""
    data = data or generate_all()
    inserted = {}
    for table in db.DATA_TABLES:  # parent tables first (foreign keys)
        inserted[table] = db.insert_dataframe(conn, table, data[table], on_conflict="ABORT")
    return inserted


def seed(db_path=None, verbose: bool = True) -> dict[str, int]:
    settings.ensure_directories()
    db.init_db(db_path)
    if has_business_data(db_path):
        if verbose:
            print("Database already contains data - seeding skipped (nothing overwritten).")
            print("To reload demo data run: python scripts/reset_demo_data.py")
        return {}
    data = generate_all()
    with db.transaction(db_path) as conn:
        inserted = load_demo_data(conn, data)
    db.mark_data_refreshed(db_path)
    write_csvs(data)
    write_sample_import_files(data)
    if verbose:
        print(f"Database ready: {db.get_db_path() if db_path is None else db_path}")
        for table, n in inserted.items():
            print(f"  {table:<18} {n:>6} rows inserted")
    return inserted


if __name__ == "__main__":
    seed()
