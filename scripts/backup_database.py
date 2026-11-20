"""
Create a consistent backup copy of the SQLite database.

    python scripts/backup_database.py

Uses SQLite's online backup API, so it is safe even while the app is running.
Backups are written to backups/bank_performance_YYYYMMDD_HHMMSS.db
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database import db  # noqa: E402


def backup_database(dest_dir: Path | None = None, db_path: Path | None = None) -> Path:
    source_path = Path(db_path) if db_path else db.get_db_path()
    if not source_path.exists():
        raise FileNotFoundError(f"Database not found: {source_path}")
    dest_dir = Path(dest_dir) if dest_dir else settings.BACKUP_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    dest = dest_dir / f"bank_performance_{stamp}.db"
    src = sqlite3.connect(source_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    return dest


def backup_bytes(db_path: Path | None = None) -> bytes:
    """Return a consistent snapshot of the database as bytes (for download)."""
    path = backup_database(db_path=db_path)
    return path.read_bytes()


if __name__ == "__main__":
    out = backup_database()
    print(f"Backup created: {out}")
