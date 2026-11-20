"""
Database utility layer.

Every other module talks to SQLite through these helpers, which guarantees:
  * foreign keys are always enforced,
  * every query is parameterised (no string-formatted user values),
  * writes happen inside transactions that roll back on error.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import pandas as pd

from config import settings

# Tables that hold business data, in parent -> child order (safe insert order).
DATA_TABLES = [
    "branches",
    "customers",
    "transactions",
    "loans",
    "branch_financials",
    "customer_feedback",
]
# "banks" ko DATA_TABLES me nahi rakha, taaki demo reset me banks delete na ho.
ALL_TABLES = ["banks"] + DATA_TABLES + ["managers", "import_log", "app_metadata"]


class DatabaseError(Exception):
    """Raised when a database operation fails in a way the UI should report."""


def get_db_path() -> Path:
    """Return the active database path (read at call time so tests can override it)."""
    return Path(settings.DB_PATH)


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with foreign keys enabled and dict-like rows."""
    path = Path(db_path) if db_path else get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def transaction(db_path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    """Context manager: commit on success, roll back everything on any error."""
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | str | None = None) -> Path:
    """Create the database file and all tables/indexes if they do not exist."""
    path = Path(db_path) if db_path else get_db_path()
    schema_sql = settings.SCHEMA_FILE.read_text(encoding="utf-8")
    conn = get_connection(path)
    try:
        conn.executescript(schema_sql)
        _seed_banks(conn)          # settings.BANKS ko banks table me daalo
        conn.commit()
    except sqlite3.Error as exc:
        raise DatabaseError(f"Could not initialise database: {exc}") from exc
    finally:
        conn.close()
    return path


def database_exists(db_path: Path | str | None = None) -> bool:
    path = Path(db_path) if db_path else get_db_path()
    return path.exists() and path.stat().st_size > 0


def execute(sql: str, params: Sequence[Any] | dict | None = None,
            db_path: Path | str | None = None) -> int:
    """Run a single write statement in a transaction. Returns affected row count."""
    try:
        with transaction(db_path) as conn:
            cur = conn.execute(sql, params or [])
            return cur.rowcount
    except sqlite3.Error as exc:
        raise DatabaseError(str(exc)) from exc


def fetch_all(sql: str, params: Sequence[Any] | dict | None = None,
              db_path: Path | str | None = None) -> list[sqlite3.Row]:
    conn = get_connection(db_path)
    try:
        return conn.execute(sql, params or []).fetchall()
    finally:
        conn.close()


def fetch_one(sql: str, params: Sequence[Any] | dict | None = None,
              db_path: Path | str | None = None) -> sqlite3.Row | None:
    conn = get_connection(db_path)
    try:
        return conn.execute(sql, params or []).fetchone()
    finally:
        conn.close()


def query_df(sql: str, params: Sequence[Any] | dict | None = None,
             db_path: Path | str | None = None) -> pd.DataFrame:
    """Run a SELECT and return a pandas DataFrame."""
    conn = get_connection(db_path)
    try:
        return pd.read_sql_query(sql, conn, params=params or [])
    except (sqlite3.Error, pd.errors.DatabaseError) as exc:
        raise DatabaseError(f"Query failed: {exc}") from exc
    finally:
        conn.close()


def insert_dataframe(conn: sqlite3.Connection, table: str, df: pd.DataFrame,
                     on_conflict: str = "ABORT") -> int:
    """Insert a DataFrame into `table` using parameterised executemany.

    `conn` must come from `transaction()` so the caller controls commit/rollback.
    `on_conflict` is one of ABORT / IGNORE (validated against a whitelist).
    Table and column names are validated against the live schema, so they are
    never taken blindly from user input.
    """
    if table not in ALL_TABLES:
        raise DatabaseError(f"Unknown table: {table}")
    if on_conflict not in ("ABORT", "IGNORE"):
        raise DatabaseError("on_conflict must be ABORT or IGNORE")
    if df.empty:
        return 0
    valid_cols = set(get_table_columns(table, conn=conn))
    bad = [c for c in df.columns if c not in valid_cols]
    if bad:
        raise DatabaseError(f"Columns not in table '{table}': {', '.join(bad)}")
    cols = list(df.columns)
    placeholders = ",".join("?" for _ in cols)
    col_sql = ",".join(f'"{c}"' for c in cols)
    sql = f'INSERT OR {on_conflict} INTO "{table}" ({col_sql}) VALUES ({placeholders})'
    records = [tuple(_to_sql_value(v) for v in row)
               for row in df.itertuples(index=False, name=None)]
    before = conn.total_changes
    conn.executemany(sql, records)
    return conn.total_changes - before


def _to_sql_value(value: Any) -> Any:
    """Convert pandas/numpy scalars to plain Python values SQLite understands."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    return value


def get_table_columns(table: str, conn: sqlite3.Connection | None = None) -> list[str]:
    if table not in ALL_TABLES:
        raise DatabaseError(f"Unknown table: {table}")
    own = conn is None
    conn = conn or get_connection()
    try:
        rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return [r[1] for r in rows]
    finally:
        if own:
            conn.close()


def table_counts(db_path: Path | str | None = None) -> dict[str, int]:
    """Row count for every table (used by the Data Management page)."""
    conn = get_connection(db_path)
    try:
        counts = {}
        for table in ALL_TABLES:
            try:
                counts[table] = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            except sqlite3.Error:
                counts[table] = 0
        return counts
    finally:
        conn.close()


def integrity_report(db_path: Path | str | None = None) -> dict[str, Any]:
    """Run SQLite integrity and foreign-key checks."""
    conn = get_connection(db_path)
    try:
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
        return {"integrity": integrity, "foreign_key_violations": len(fk_violations)}
    finally:
        conn.close()


def set_metadata(key: str, value: str, db_path: Path | str | None = None) -> None:
    execute(
        "INSERT INTO app_metadata(meta_key, meta_value) VALUES (?, ?) "
        "ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value",
        [key, value], db_path,
    )


def get_metadata(key: str, default: str | None = None,
                 db_path: Path | str | None = None) -> str | None:
    try:
        row = fetch_one("SELECT meta_value FROM app_metadata WHERE meta_key = ?", [key], db_path)
    except sqlite3.Error:
        return default
    return row[0] if row else default


def mark_data_refreshed(db_path: Path | str | None = None) -> str:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_metadata("last_data_refresh", stamp, db_path)
    return stamp


def clear_business_data(conn: sqlite3.Connection) -> None:
    """Delete all business data (children first). Managers are kept.

    Only called from the explicit, confirmed demo-reset flow.
    """
    for table in reversed(DATA_TABLES):
        conn.execute(f'DELETE FROM "{table}"')
    conn.execute("DELETE FROM import_log")


def iter_chunks(items: Iterable, size: int) -> Iterator[list]:
    chunk: list = []
    for item in items:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


# --------------------------------------------------------------------------
# Multi-bank helpers
# --------------------------------------------------------------------------
def _seed_banks(conn: sqlite3.Connection) -> None:
    """settings.BANKS ki list ko banks table me daalta hai (duplicate nahi banta)."""
    for bank in settings.BANKS:
        conn.execute(
            "INSERT OR IGNORE INTO banks (bank_code, bank_name) VALUES (?, ?)",
            (bank["code"], bank["name"]),
        )


def get_banks() -> list[sqlite3.Row]:
    """Login dropdown ke liye saari active banks."""
    return fetch_all(
        "SELECT bank_id, bank_code, bank_name FROM banks "
        "WHERE is_active = 1 ORDER BY bank_name"
    )


def get_bank_id(bank_code: str) -> int | None:
    row = fetch_one("SELECT bank_id FROM banks WHERE bank_code = ?", [bank_code])
    return row["bank_id"] if row else None