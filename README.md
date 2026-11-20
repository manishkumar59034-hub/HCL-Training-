# 🏦 Bank Branch Performance Analysis

A database-driven data-analytics application that lets bank managers monitor branch performance,
analyse financial results, customer growth and loan quality, identify under-performing branches and
act on automatically generated, explained insights.

Built with **Python · Streamlit · SQLite · Pandas · NumPy · Plotly**. Runs entirely on a local Windows
laptop — no cloud services, paid APIs or API keys.

> ⚠️ Academic / demonstration project. All data is synthetic. It is **not** production banking software
> (see [Limitations](#19-limitations)).

---

## Contents
1. [Introduction](#1-introduction) · 2. [Objectives](#2-objectives) · 3. [Features](#3-features) ·
4. [Technologies](#4-technologies-used) · 5. [Architecture](#5-application-architecture) ·
6. [Folder structure](#6-folder-structure) · 7. [Database design](#7-database-design) ·
8. [Dataset](#8-dataset-explanation) · 9. [KPIs](#9-kpi-definitions) · 10. [Installation](#10-installation) ·
11. [Environment setup](#11-environment-setup) · 12. [Manager account](#12-manager-account-setup) ·
13. [Run](#13-how-to-run-the-application) · 14. [Import data](#14-how-to-import-data) ·
15. [Refresh](#15-how-to-refresh-the-dashboard) · 16. [Reset demo data](#16-how-to-reset-demo-data) ·
17. [Backup](#17-how-to-back-up-the-database) · 18. [Troubleshooting](#18-troubleshooting) ·
19. [Limitations](#19-limitations) · 20. [Future improvements](#20-future-improvements) · [Testing](#testing)

---

## 1. Introduction
Branch data in a bank is spread across ledgers, loan registers and feedback systems. This application
loads that data into one relational database, validates it, calculates KPIs with a single shared set of
formulas, and presents interactive dashboards protected by a manager login. Every chart, KPI, ranking,
insight and export responds to the same global filters.

## 2. Objectives
- Design a normalised SQLite schema with keys, constraints and indexes.
- Build a validated import pipeline (CSV/Excel → clean → validate → transactional insert).
- Centralise KPI formulas so a KPI is never calculated two different ways.
- Provide descriptive, comparative, trend and basic diagnostic analytics with decision support.
- Implement secure-by-default authentication suitable for a student project.

## 3. Features
| Area | What you get |
|---|---|
| Login | Hashed passwords (PBKDF2-SHA256), lockout after 5 failures, inactive accounts, session timeout, logout clears session, first-time admin setup |
| Executive Overview | 8 KPIs, revenue vs target trend, revenue by branch, deposits vs disbursement, customer distribution, top/bottom 5 by any metric, highlights |
| Branch Performance | KPI cards, 14-column performance table, 5 chart tabs, configurable High/Average/Low thresholds, single-branch drill-down vs bank average |
| Financial Analysis | 8 KPIs incl. MoM growth, 6 charts, auto-written answers to 7 business questions, formula reference |
| Customer Analysis | 5 KPIs, 6 charts, acquisition & satisfaction answers (synthetic IDs only) |
| Loan Analysis | Applications / approvals / rejections / disbursement / outstanding / defaults kept distinct, 7 charts, answers |
| Reports & Insights | Rule-based positive insights, warnings and grouped recommendations — each with its evidence |
| Report Export | CSV / Excel per report or one multi-sheet workbook; always reflects current filters |
| Data Management | DB status & integrity, CSV/Excel import with preview, validation and duplicate protection, data-quality checks, backup & download, confirmed demo reset, import history, manager accounts |
| Filters | Date range, year, month, region → state → city → branch (cascading), branch status |

## 4. Technologies used
| Technology | Use |
|---|---|
| Python 3.11+ | Language (tested on 3.13) |
| Streamlit | Web interface |
| SQLite (`sqlite3`) | Persistent relational database |
| Pandas / NumPy | Data processing, synthetic data |
| Plotly | Interactive charts |
| openpyxl | Excel import/export |
| python-dotenv | Loads `.env` (optional — a fallback parser is built in) |
| hashlib / hmac / secrets | Password hashing (standard library) |
| pytest | Automated tests |

## 5. Application architecture
```
Data sources (CSV / Excel / synthetic generator)
        ↓  analytics/data_cleaning.py      (format fixes, logged)
        ↓  analytics/data_validation.py    (types, ranges, dates, references, duplicates)
        ↓  analytics/data_import.py        (single transaction, duplicate-file guard)
SQLite database  (database/schema.sql, database/db.py)
        ↓  analytics/queries.py            (Filters → parameterised SQL)
        ↓  analytics/*_analysis.py         (Pandas analysis)
        ↓  analytics/kpi_calculations.py   (ONE place for every formula)
        ↓  analytics/insights.py           (business rules → insights + actions)
Streamlit app  (app.py → login gate → components/sidebar.py → views/*.py)
```
UI, authentication, database, data processing, KPIs, insights, charts, utilities and configuration
are in separate modules. Details: [docs/project_overview.md](docs/project_overview.md).

## 6. Folder structure
```
Bank_Branch_Performance_Analysis/
├── app.py                     # Streamlit entry point (login gate + routing)
├── requirements.txt  README.md  .env.example  .gitignore
├── .streamlit/config.toml     # theme; hides automatic page links
├── config/settings.py         # paths, thresholds, colours, demo sizes
├── database/
│   ├── schema.sql             # tables, constraints, indexes
│   ├── db.py                  # connections, transactions, helpers
│   └── bank_performance.db    # demo database (synthetic data, no accounts)
├── auth/
│   ├── authentication.py      # hashing, login, lockout, sessions
│   └── setup_manager.py       # CLI: first manager, add, reset, (de)activate, list
├── analytics/
│   ├── data_cleaning.py  data_validation.py  data_import.py
│   ├── queries.py  kpi_calculations.py
│   ├── branch_analysis.py  financial_analysis.py  customer_analysis.py  loan_analysis.py
│   └── insights.py
├── views/                     # one module per page (named views/, not pages/, so Streamlit
│   ├── overview.py            #  cannot expose pages before login)
│   ├── branch_performance.py  financial_analysis.py  customer_analysis.py
│   ├── loan_analysis.py  reports_insights.py  report_export.py  data_management.py
│   └── common.py
├── components/
│   ├── sidebar.py  filters.py  kpi_cards.py  charts.py  tables.py
│   ├── login_ui.py  styling.py  data_loader.py
├── utils/formatting.py  utils/exports.py
├── scripts/
│   ├── initialize_project.py  # one-command setup
│   ├── generate_demo_data.py  seed_database.py  reset_demo_data.py
│   ├── backup_database.py     reset_manager_password.py
├── data/raw/ (generated CSVs)  data/samples/ (import demo files)  data/processed/  data/exports/
├── backups/                   # database backups are written here
├── tests/                     # pytest suite (56 tests)
└── docs/                      # overview, schema, data dictionary, KPIs, user guide
```

## 7. Database design
Seven core tables — `branches`, `customers`, `transactions`, `loans`, `branch_financials`,
`customer_feedback`, `managers` — plus `import_log` (duplicate-import protection) and `app_metadata`
(last refresh time). Primary keys, foreign keys (enforced), CHECK constraints and 13 indexes.
See [docs/database_schema.md](docs/database_schema.md) and [docs/data_dictionary.md](docs/data_dictionary.md).

## 8. Dataset explanation
Generated by `scripts/generate_demo_data.py` with seed **42** (identical on every machine):

| Table | Rows |
|---|---|
| branches | 20 (18 cities, 15 states, 5 regions) |
| customers | 2,400 |
| transactions | 12,000 |
| loans | 850 |
| branch_financials | 360 (20 branches × 18 months, May 2025 – Oct 2026) |
| customer_feedback | ≈3,300 |

Each branch has a designed profile, so results differ realistically: e.g. *Gurugram Cyber City* beats
target with fast customer growth, *Hyderabad Banjara Hills* has heavy lending with high defaults,
*Lucknow Hazratganj* and *Patna Fraser Road* under-perform with rising costs and low satisfaction.
Customers are labelled `Customer 000123` — no real personal or financial data is used.

## 9. KPI definitions
| KPI | Formula |
|---|---|
| Net Profit | Revenue − Expenses |
| Profit Margin % | Net Profit ÷ Revenue × 100 |
| Target Achievement % | Actual Revenue ÷ Revenue Target × 100 |
| Revenue Growth % (MoM) | (Latest month − Previous month) ÷ Previous month × 100 |
| Customer Growth % | (Customers at period end − at period start) ÷ at period start × 100 |
| Loan Approval Rate % | Approved Loans ÷ Total Applications × 100 |
| Loan Default Rate % | Defaulted Loans ÷ Disbursed Loans × 100 |
| Avg Revenue per Customer | Total Revenue ÷ Total Customers |

Performance categories: **High** ≥ 100%, **Average** 80–99.9%, **Low** < 80% target achievement
(configurable). Division by zero or a missing previous month shows **N/A**.
Full list and insight rules: [docs/kpi_definitions.md](docs/kpi_definitions.md).

## 10. Installation
Prerequisite: **Python 3.11 or newer** from python.org (tick *"Add python.exe to PATH"* during install).

1. Extract `Bank_Branch_Performance_Analysis.zip`.
2. Open the extracted folder in **VS Code** (*File → Open Folder…*).
3. Open a terminal (*Terminal → New Terminal*) and run:

```bat
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

> PowerShell says *"running scripts is disabled"*? Run once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` and then activate again.
> Or switch the VS Code terminal to **Command Prompt**.

## 11. Environment setup
```bat
copy .env.example .env
```
Open `.env` and set your own values:
```
MANAGER_USERNAME=bankadmin
MANAGER_PASSWORD=<choose a strong password>
MANAGER_NAME=Your Display Name
APP_SECRET_KEY=<random text>
```
Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
`.env` is in `.gitignore` and is **not** included in the ZIP. The example password is a placeholder and
is rejected by the setup script.

## 12. Manager account setup
**Option A — one command (recommended):**
```bat
python scripts\initialize_project.py
```
Creates/validates the database, loads demo data if empty, and creates the first **Administrator** from
`.env` (or prompts you, with hidden password entry). The password is stored only as a PBKDF2 hash.

**Option B — in the browser:** just run the app. If no manager exists, a one-time *First-time setup*
screen asks you to create the Administrator. It disappears permanently once an account exists.

Other account commands:
```bat
python -m auth.setup_manager --list              :: list managers (no hashes shown)
python -m auth.setup_manager --create            :: add a manager (any role)
python -m auth.setup_manager --reset-password    :: reset a password (also clears lockout)
python scripts\reset_manager_password.py bankadmin
python -m auth.setup_manager --deactivate USER   :: or --activate USER
```
Password rules: at least 8 characters with an uppercase letter, a lowercase letter and a digit.
Administrators can also add and (de)activate managers in **Data Management → Manager accounts**.

## 13. How to run the application
```bat
venv\Scripts\activate
streamlit run app.py
```
The browser opens at http://localhost:8501. Log in with the account from step 12.

**First login, step by step:** `copy .env.example .env` → edit username/password → 
`python scripts\initialize_project.py` → `streamlit run app.py` → enter the same username and password → **Login**.

## 14. How to import data
Data Management → **Import data** (Administrator role):
1. Choose the target table; check *Expected file format* (an empty CSV template can be downloaded).
2. Upload `.csv` or `.xlsx` → preview, cleaning log and validation summary appear.
3. Errors are listed by file row number with a plain-language reason (missing value, invalid date,
   negative amount, unknown branch, duplicate ID, out-of-range score…).
4. Any error blocks the import unless you tick *Import only the valid rows*.
5. **Import into database** — runs in one transaction; existing records are skipped; the same file
   cannot be imported twice.

Practice files in `data/samples/`: `sample_financials_next_month.csv` (valid),
`sample_financials_with_errors.csv` (5 deliberate errors), `sample_feedback_next_month.xlsx` (valid Excel).

## 15. How to refresh the dashboard
Imports and resets refresh automatically. To force a refresh (e.g. after editing the database
externally): Data Management → Database status → **Refresh dashboard data**. The sidebar shows the
last refresh time.

## 16. How to reset demo data
In the app: Data Management → Backup & reset → tick the confirmation box, type `RESET`, click
**Reset demo data**. From a terminal:
```bat
python scripts\reset_demo_data.py
```
(asks you to type `RESET`). A backup is always created first; manager accounts are kept; the reset
runs in a single transaction. `python scripts\seed_database.py` never overwrites existing data.

## 17. How to back up the database
In the app: Data Management → Backup & reset → **Create backup** → **Download backup file**.
From a terminal:
```bat
python scripts\backup_database.py
```
Backups go to `backups\bank_performance_YYYYMMDD_HHMMSS_mmm.db` (SQLite online-backup API, safe while
the app runs). To restore, stop the app and copy a backup over `database\bank_performance.db`.

## 18. Troubleshooting
| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python with *Add to PATH*, or use `py` instead of `python` |
| `streamlit` not recognized | Activate the venv first (`venv\Scripts\activate`) or use `python -m streamlit run app.py` |
| PowerShell blocks `activate` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` or use Command Prompt |
| `ModuleNotFoundError` | `pip install -r requirements.txt` inside the activated venv; run commands from the project folder |
| "Account temporarily locked" | Wait 15 minutes or `python -m auth.setup_manager --reset-password` |
| Forgot the only admin password | `python scripts\reset_manager_password.py bankadmin` |
| Port 8501 busy | `streamlit run app.py --server.port 8502` |
| Charts empty | Filters exclude all data — click **Reset filters** in the sidebar |
| Database corrupted / want a clean start | Stop the app, delete `database\bank_performance.db`, run `python scripts\initialize_project.py` (managers must be recreated) |
| Import says "already imported" | The exact file was imported before — this is the duplicate-import guard |

## 19. Limitations
- Synthetic data only; branch "profiles" are designed, so patterns are cleaner than real data.
- Security is appropriate for a local academic demo, **not** for production banking: no HTTPS, MFA,
  audit trail of every view, encryption at rest, or central identity provider. The lockout is per
  account, not per IP. Streamlit sessions live in server memory.
- SQLite suits a single user/laptop; a multi-user deployment would need PostgreSQL or similar.
- Customer `status` is current-state only, so historical active counts are not reconstructed.
- Imported loans do not automatically update `branch_financials.loan_disbursement`; the two are
  reconciled in demo data only.
- Insights are rule-based (descriptive/diagnostic). There is no forecasting or machine learning.

## 20. Future improvements
- Role-based page permissions beyond the current Administrator / Branch Manager scoping.
- Time-series forecasting of revenue and deposits (validated against hold-out months).
- Scheduled e-mail of the PDF/Excel management pack.
- Audit log of logins and data changes; password expiry; optional MFA.
- PostgreSQL backend and Docker packaging for multi-user use.
- Drill-through from charts to the underlying transactions.

---

## Testing
```bat
venv\Scripts\activate
python -m pytest -v
```
56 automated tests cover database creation, constraints and foreign keys, reproducible data
generation, seeding, reset and backup, password hashing, correct/incorrect/inactive login, lockout,
logout, every KPI formula, division by zero, empty datasets, date/month/branch/region filtering,
KPI consistency across pages, insights, cleaning, validation, duplicate detection, CSV and Excel import,
transaction rollback, report export, and Streamlit UI tests (login gate, every page, empty filter
results, filter changes KPIs, logout, first-time setup).

## Project documentation
- [docs/project_overview.md](docs/project_overview.md) — architecture and analytics approach
- [docs/database_schema.md](docs/database_schema.md) — tables, keys, indexes
- [docs/data_dictionary.md](docs/data_dictionary.md) — every column, cleaning rules, assumptions
- [docs/kpi_definitions.md](docs/kpi_definitions.md) — formulas and insight rules
- [docs/user_guide.md](docs/user_guide.md) — how to use each page
#   H C L - T r a i n i n g -  
 