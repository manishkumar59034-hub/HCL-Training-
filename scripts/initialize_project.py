"""
One-command setup for a new computer:

    python scripts/initialize_project.py

1. Creates folders and the SQLite database with all tables.
2. Loads the synthetic demo data (only if the database is empty).
3. Creates the first manager account from .env (or asks you), if none exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth.setup_manager import create_first_manager  # noqa: E402
from scripts.seed_database import seed  # noqa: E402

if __name__ == "__main__":
    print("Step 1/2: database and demo data")
    seed()
    print("\nStep 2/2: manager account")
    code = create_first_manager()
    if code == 0:
        print("\nSetup complete. Start the app with:  streamlit run app.py")
    raise SystemExit(code)
