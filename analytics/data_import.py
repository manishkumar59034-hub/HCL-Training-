"""
Import pipeline:  read file -> clean -> validate -> insert (single transaction).

Guarantees
----------
* The same file (by SHA-256 content hash) cannot be imported twice into a table.
* Rows already present in the database (same ID) are skipped, never duplicated.
* By default, ANY validation error blocks the whole import. The manager may
  choose to import only the valid rows; invalid rows are then skipped and listed.
* All inserts happen inside one transaction - if anything fails, nothing is saved.
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

import pandas as pd

from analytics.data_cleaning import clean_dataframe
from analytics.data_validation import TABLE_SPECS, ValidationReport, validate_dataframe
from database import db


class ImportErrorMessage(Exception):
    """Raised with a manager-friendly message when an import cannot proceed."""


@dataclass
class ImportResult:
    success: bool
    message: str
    inserted: int = 0
    skipped_existing: int = 0
    skipped_invalid: int = 0
    details: list[str] = field(default_factory=list)


def file_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def read_upload(file_name: str, content: bytes) -> pd.DataFrame:
    """Read CSV or Excel bytes into a DataFrame of strings/numbers."""
    name = file_name.lower()
    try:
        if name.endswith(".csv"):
            return pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=True,
                               encoding_errors="replace")
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(io.BytesIO(content), dtype=str)
    except Exception as exc:  # noqa: BLE001 - convert to friendly message
        raise ImportErrorMessage(f"The file could not be read: {exc}") from exc
    raise ImportErrorMessage("Unsupported file type. Please upload a .csv or .xlsx file.")


def prepare(table: str, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], ValidationReport]:
    """Clean + validate. Returns (clean_df, cleaning_log, report)."""
    cleaned, log = clean_dataframe(table, df)
    report = validate_dataframe(table, cleaned)
    return cleaned, log, report


def already_imported(table: str, digest: str) -> bool:
    return db.fetch_one("SELECT 1 FROM import_log WHERE table_name = ? AND file_hash = ?",
                        [table, digest]) is not None


def import_data(table: str, cleaned: pd.DataFrame, report: ValidationReport, *,
                file_name: str, digest: str, imported_by: str | None = None,
                allow_partial: bool = False) -> ImportResult:
    if table not in TABLE_SPECS:
        raise ImportErrorMessage(f"Unknown table '{table}'.")
    if not report.is_structurally_valid:
        return ImportResult(False, "Import blocked: required columns are missing ("
                            + ", ".join(report.missing_columns) + ").")
    if already_imported(table, digest):
        return ImportResult(False, "This exact file has already been imported into "
                                   f"'{table}'. Duplicate import prevented.")
    if report.invalid_rows and not allow_partial:
        return ImportResult(False, f"Import blocked: {len(report.invalid_rows)} row(s) have "
                                   "validation errors. Fix the file or choose to import valid rows only.",
                            skipped_invalid=len(report.invalid_rows))

    skip = report.invalid_rows | report.existing_rows
    to_insert = cleaned.loc[~cleaned.index.isin(list(skip))]
    allowed = TABLE_SPECS[table]["required"] + TABLE_SPECS[table]["optional"]
    to_insert = to_insert[[c for c in allowed if c in to_insert.columns]].copy()
    for col in TABLE_SPECS[table]["numeric"]:
        to_insert[col] = pd.to_numeric(to_insert[col])
        if col == "satisfaction_score":
            to_insert[col] = to_insert[col].astype(int)

    skipped_existing = len(report.existing_rows - report.invalid_rows)
    if to_insert.empty:
        return ImportResult(False, "Nothing to import - every row is either invalid or already "
                                   "in the database.", 0, skipped_existing, len(report.invalid_rows))
    try:
        with db.transaction() as conn:
            inserted = db.insert_dataframe(conn, table, to_insert, on_conflict="ABORT")
            conn.execute(
                "INSERT INTO import_log (table_name, file_name, file_hash, rows_inserted, "
                "rows_skipped, imported_by) VALUES (?, ?, ?, ?, ?, ?)",
                [table, file_name, digest, inserted, len(skip), imported_by],
            )
    except Exception as exc:  # noqa: BLE001
        return ImportResult(False, f"Import failed and was fully rolled back - no records were "
                                   f"saved. Database message: {exc}")
    db.mark_data_refreshed()
    return ImportResult(True, f"Import successful: {inserted} record(s) inserted into '{table}'.",
                        inserted, skipped_existing, len(report.invalid_rows))


def import_history() -> pd.DataFrame:
    return db.query_df(
        "SELECT imported_at AS 'Imported At', table_name AS 'Table', file_name AS 'File', "
        "rows_inserted AS 'Inserted', rows_skipped AS 'Skipped', imported_by AS 'By' "
        "FROM import_log ORDER BY import_id DESC")


def template_dataframe(table: str) -> pd.DataFrame:
    """Empty frame with the expected columns - offered as a download template."""
    spec = TABLE_SPECS[table]
    return pd.DataFrame(columns=spec["required"] + spec["optional"])
