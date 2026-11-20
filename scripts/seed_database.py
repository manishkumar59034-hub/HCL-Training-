"""
Initialise the SQLite database and load the synthetic demo data (multi-bank).

    python scripts/seed_database.py

Har bank (settings.BANKS) ke liye alag demo data banta hai. IDs par bank code
ka prefix lagta hai (INDB-BR001, SBIN-BR001 ...), taaki alag banks ki IDs
kabhi na takraen.

Safe by design: jis bank ki branches pehle se hain, uska data overwrite nahi hota.
Naya bank add karke ye script dobara chalao - sirf naye bank ka data banega.
To replace existing data use scripts/reset_demo_data.py, which
asks for confirmation and makes a backup first.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import settings  # noqa: E402
from database import db  # noqa: E402
from scripts.generate_demo_data import generate_all, write_csvs, write_sample_import_files  # noqa: E402

# Kin tables ke kaun se columns ID hain (inpe bank code prefix lagega)
ID_COLUMNS = {
    "branches": ["branch_id"],
    "customers": ["customer_id", "branch_id"],
    "transactions": ["transaction_id", "customer_id", "branch_id"],
    "loans": ["loan_id", "customer_id", "branch_id"],
    "branch_financials": ["financial_id", "branch_id"],
    "customer_feedback": ["feedback_id", "branch_id"],
}


def has_business_data(db_path=None) -> bool:
    counts = db.table_counts(db_path)
    return any(counts.get(t, 0) > 0 for t in db.DATA_TABLES)


def banks_without_data(db_path=None) -> list:
    """Wo banks jinki abhi tak koi branch nahi hai."""
    return db.fetch_all(
        "SELECT b.bank_id, b.bank_code, b.bank_name FROM banks b "
        "WHERE b.is_active = 1 AND NOT EXISTS "
        "(SELECT 1 FROM branches br WHERE br.bank_id = b.bank_id) "
        "ORDER BY b.bank_id",
        db_path=db_path,
    )


def _generate_for_bank(bank_id: int) -> dict:
    """Generator ko chalao. Seed thoda badalte hain, taaki har bank ka data alag aaye
    (agar generator settings.RANDOM_SEED call ke waqt padhta hai)."""
    original = settings.RANDOM_SEED
    settings.RANDOM_SEED = original + int(bank_id)
    try:
        return generate_all()
    finally:
        settings.RANDOM_SEED = original


def _prefix_ids(data: dict, bank_code: str, bank_id: int) -> dict:
    """Saari IDs par bank code lagao aur branches me bank_id jodo."""
    out = {}
    for table in db.DATA_TABLES:
        df = data[table].copy()
        for col in ID_COLUMNS[table]:
            if col in df.columns:
                df[col] = f"{bank_code}-" + df[col].astype(str)
        if table == "branches":
            df["bank_id"] = bank_id
        out[table] = df
    return out


def load_demo_data(conn, banks) -> dict[str, int]:
    """Diye gaye banks ke liye data generate karke insert karo (open transaction me)."""
    inserted = {t: 0 for t in db.DATA_TABLES}
    for bank in banks:
        raw = _generate_for_bank(bank["bank_id"])
        data = _prefix_ids(raw, bank["bank_code"], bank["bank_id"])
        for table in db.DATA_TABLES:  # parent tables first (foreign keys)
            inserted[table] += db.insert_dataframe(conn, table, data[table], on_conflict="ABORT")
    return inserted


def seed(db_path=None, verbose: bool = True) -> dict[str, int]:
    settings.ensure_directories()
    db.init_db(db_path)
    banks = banks_without_data(db_path)
    if not banks:
        if verbose:
            print("Har bank ka data pehle se maujood hai - seeding skipped (nothing overwritten).")
            print("Naya bank add karna ho: config/settings.py me BANKS me add karo, "
                  "phir ye script dobara chalao.")
            print("To reload demo data run: python scripts/reset_demo_data.py")
        return {}

    with db.transaction(db_path) as conn:
        inserted = load_demo_data(conn, banks)
    db.mark_data_refreshed(db_path)

    # CSV / sample import files (purane format me, pehle bank ke data se)
    try:
        sample = _generate_for_bank(banks[0]["bank_id"])
        write_csvs(sample)
        write_sample_import_files(sample)
    except Exception as exc:  # noqa: BLE001 - files optional hain, seeding fail nahi honi chahiye
        if verbose:
            print(f"(Sample CSV files skip hue: {exc})")

    if verbose:
        print(f"Database ready: {db.get_db_path() if db_path is None else db_path}")
        print("Banks seeded: " + ", ".join(b["bank_name"] for b in banks))
        for table, n in inserted.items():
            print(f"  {table:<18} {n:>6} rows inserted")
    return inserted


if __name__ == "__main__":
    seed()