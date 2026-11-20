# User Guide

## 1. Logging in
Open the app (`streamlit run app.py`), enter your manager username and password, click **Login**.
- Wrong credentials show *"Invalid username or password."*
- After 5 failed attempts the account is locked for 15 minutes (an administrator can reset the password to unlock it).
- Inactive accounts cannot log in. Sessions end after 60 minutes of inactivity.
- If no manager exists yet, a one-time **First-time setup** screen lets you create the Administrator.

## 2. Navigation and filters (sidebar)
Pages: Executive Overview · Branch Performance · Financial Analysis · Customer Analysis · Loan Analysis ·
Reports & Insights · Report Export · Data Management · Logout.

Filters apply to **every** page, KPI, chart, ranking, insight and export:
| Filter | Effect |
|---|---|
| Reporting date range | Limits months, transactions, loans and feedback |
| Year | Narrows the date range to that calendar year |
| Month | Keeps only that calendar month (in every selected year) |
| Region → State → City → Branch | Cascading — each choice narrows the next list |
| Branch status | Active / Under Review / Inactive |

**Reset filters** clears all of them. "Active filters" shows what is applied; the last data-refresh time is under it.
Branch Managers with an assigned branch only see their own branch.

## 3. Pages
- **Executive Overview** — 8 KPIs, revenue trend vs target, revenue by branch (coloured by category), deposits vs disbursement, customers by region, top/bottom 5 by a metric you choose, and highlights.
- **Branch Performance** — branch KPIs, full performance table (sortable), revenue/profit/target/ranking/regional tabs, adjustable category thresholds, and a **Branch details** drill-down comparing one branch with the bank average.
- **Financial Analysis** — revenue, expenses, profit, margin, deposits, disbursement, MoM growth; trend charts; written answers to the key financial questions; formula reference.
- **Customer Analysis** — base, new, active, growth, satisfaction; growth and acquisition charts; answers to customer questions. Only aggregate counts and synthetic IDs are shown.
- **Loan Analysis** — applications, approvals, rejections, disbursement, outstanding and defaults kept clearly separate; trend, type, status and branch charts; definitions table.
- **Reports & Insights** — positive insights, warnings (filterable by branch), grouped recommendations, and a full table. Every item says *why* it was raised.
- **Report Export** — pick a report, preview, download CSV or Excel; or build one complete workbook. File names include a timestamp, and a *Filters* sheet records the selection used.
- **Data Management** — database status and integrity, import, data-quality checks, backup & download, demo reset, import history, manager accounts (Administrator only).

## 4. Importing data (Administrator)
1. Data Management → **Import data**.
2. Choose the **target table**; open *Expected file format* (download an empty template if needed).
3. Upload a `.csv` or `.xlsx` file. A preview, the cleaning steps and a validation summary appear.
4. Problems are listed with the file row number and a plain-language reason.
5. If there are errors the import is blocked; you may tick *Import only the valid rows* to skip them.
6. Click **Import into database**. Records already in the database are skipped; the same file can't be imported twice.
7. The dashboard refreshes automatically.

Try it with the files in `data/samples/`:
- `sample_financials_next_month.csv` → table `branch_financials` (valid, 20 rows)
- `sample_financials_with_errors.csv` → table `branch_financials` (shows 5 types of error)
- `sample_feedback_next_month.xlsx` → table `customer_feedback` (valid Excel, 100 rows)

## 5. Backup and reset
- **Create backup** writes `backups/bank_performance_<timestamp>.db` and offers a download.
- **Reset demo data** requires ticking the confirmation box *and* typing `RESET`. A backup is made first,
  and the reset runs in one transaction. Manager accounts are kept.
