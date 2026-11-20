"""
Reset ALL business data back to the original synthetic demo dataset.

    python scripts/reset_demo_data.py          # asks you to type RESET
    python scripts/reset_demo_data.py --yes    # no prompt (for scripts)

Manager accounts are kept. A backup is always created before anything is
deleted, and the delete + reload runs in ONE transaction: if the reload fails,
the original data is restored automatically.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402
from scripts.backup_database import backup_database  # noqa: E402
from scripts.generate_demo_data import generate_all  # noqa: E402
from scripts.seed_database import load_demo_data  # noqa: E402


def reset_demo_data(db_path=None, make_backup: bool = True) -> dict:
    db.init_db(db_path)
    backup_path = backup_database(db_path=db_path) if make_backup else None
    data = generate_all()
    with db.transaction(db_path) as conn:
        db.clear_business_data(conn)
        inserted = load_demo_data(conn, data)
    db.mark_data_refreshed(db_path)
    return {"inserted": inserted, "backup": str(backup_path) if backup_path else None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()
    if not args.yes:
        print("WARNING: this replaces ALL branch, customer, transaction, loan, financial and")
        print("feedback data with the demo dataset. Manager accounts are kept.")
        if input("Type RESET to continue: ").strip() != "RESET":
            print("Cancelled. No changes made.")
            raise SystemExit(0)
    result = reset_demo_data()
    print(f"Backup created first: {result['backup']}")
    for table, n in result["inserted"].items():
        print(f"  {table:<18} {n:>6} rows loaded")
