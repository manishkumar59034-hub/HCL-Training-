"""
Central configuration for the Bank Branch Performance Analysis application.

All paths, thresholds and tunable business rules live here so that every
module (and every page) uses exactly the same values.

Secrets (manager credentials, secret key) are NEVER hardcoded here. They are
read from environment variables, which can be supplied through a local `.env`
file (see `.env.example`).
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
EXPORTS_DIR = DATA_DIR / "exports"
SAMPLES_DIR = DATA_DIR / "samples"
BACKUP_DIR = BASE_DIR / "backups"
SCHEMA_FILE = DATABASE_DIR / "schema.sql"
ENV_FILE = BASE_DIR / ".env"


def _load_env_file(path: Path) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Uses python-dotenv when available, otherwise a tiny built-in parser.
    Existing environment variables are never overwritten.
    """
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(path, override=False)
        return
    except ImportError:
        pass
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env_file(ENV_FILE)

# Database file (can be overridden, e.g. by tests)
DB_PATH = Path(os.environ.get("BANK_DB_PATH", DATABASE_DIR / "bank_performance.db"))

# --------------------------------------------------------------------------
# Application
# --------------------------------------------------------------------------
APP_TITLE = "Bank Branch Performance Analysis"
APP_SHORT_TITLE = "Branch Analytics"
APP_ICON = "🏦"
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
PBKDF2_ITERATIONS = 260_000          # PBKDF2-HMAC-SHA256 work factor
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_ATTEMPTS = 5              # lock account after this many failures
LOCKOUT_MINUTES = 15                 # lock duration
SESSION_TIMEOUT_MINUTES = 60         # idle timeout for a logged-in session

# --------------------------------------------------------------------------
# Business rules (configurable thresholds)
# --------------------------------------------------------------------------
HIGH_PERFORMER_THRESHOLD = 100.0     # target achievement % >= this -> High
AVERAGE_PERFORMER_THRESHOLD = 80.0   # >= this and < high -> Average, else Low
DEFAULT_RATE_THRESHOLD = 8.0         # loan default rate % considered high
LOW_SATISFACTION_THRESHOLD = 3.5     # average score (1-5) considered low
HIGH_EXPENSE_RATIO_THRESHOLD = 75.0  # expenses as % of revenue considered high
TOP_N = 5                            # top / bottom N branches

# Loan statuses (used consistently in every loan KPI)
LOAN_STATUS_APPROVED = "Approved"    # approved, awaiting disbursement
LOAN_STATUS_DISBURSED = "Disbursed"  # approved and money paid out
LOAN_STATUS_REJECTED = "Rejected"
LOAN_STATUS_PENDING = "Pending"
LOAN_STATUS_CLOSED = "Closed"        # disbursed and fully repaid
APPROVED_LOAN_STATUSES = (LOAN_STATUS_APPROVED, LOAN_STATUS_DISBURSED, LOAN_STATUS_CLOSED)
DISBURSED_LOAN_STATUSES = (LOAN_STATUS_DISBURSED, LOAN_STATUS_CLOSED)
REPAYMENT_DEFAULTED = "Defaulted"

# --------------------------------------------------------------------------
# Synthetic data generation
# --------------------------------------------------------------------------
RANDOM_SEED = 42
DEMO_NUM_BRANCHES = 20
DEMO_NUM_CUSTOMERS = 2400
DEMO_NUM_TRANSACTIONS = 12000
DEMO_NUM_LOANS = 850
DEMO_START_MONTH = "2025-05"         # first reporting month
DEMO_NUM_MONTHS = 18                 # number of reporting months

# --------------------------------------------------------------------------
# UI theme colours (navy / white / grey with blue accents)
# --------------------------------------------------------------------------
COLOR_NAVY = "#0B2545"
COLOR_BLUE = "#1F5FAE"
COLOR_LIGHT_BLUE = "#7DA7D9"
COLOR_GREY = "#8A94A6"
COLOR_LIGHT_GREY = "#F3F5F8"
COLOR_GREEN = "#2E7D5B"
COLOR_AMBER = "#C98A1B"
COLOR_RED = "#B23A48"
# Categorical chart palette - fixed order, validated for colour-blind separation
# (blue, orange, aqua, yellow, magenta, green, violet, red). Never cycled.
CHART_SEQUENCE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
CHART_PRIMARY = "#2a78d6"            # single-series charts
CHART_SECONDARY = "#eb6834"          # second series in two-series comparisons
CHART_GRID = "#e1e0d9"
CHART_AXIS = "#c3c2b7"
CHART_TEXT = "#3a4256"
# Fixed entity -> colour maps so a filter never repaints the survivors
REGION_COLORS = {"North": "#2a78d6", "South": "#eb6834", "East": "#1baf7a",
                 "West": "#eda100", "Central": "#6250d6"}
CATEGORY_COLORS = {
    "High Performer": COLOR_GREEN,      # status colours - always shown with a text label
    "Average Performer": COLOR_AMBER,
    "Low Performer": COLOR_RED,
    "Not Rated": COLOR_GREY,
}


def ensure_directories() -> None:
    """Create runtime folders if they do not yet exist."""
    for folder in (DATABASE_DIR, RAW_DIR, PROCESSED_DIR, EXPORTS_DIR, SAMPLES_DIR, BACKUP_DIR):
        folder.mkdir(parents=True, exist_ok=True)
