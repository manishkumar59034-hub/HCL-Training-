# Database Schema

Database file: `database/bank_performance.db` (SQLite 3). The full DDL is in `database/schema.sql`.
Foreign keys are enforced on every connection (`PRAGMA foreign_keys = ON`).

## Entity relationships
```
branches 1 ──< customers 1 ──< transactions >── 1 branches
    │               └──────< loans >──────────── 1 branches
    ├──< branch_financials   (UNIQUE branch_id + reporting_month)
    ├──< customer_feedback
    └──< managers.assigned_branch_id (nullable)
import_log, app_metadata  (supporting tables)
```

## Tables

| Table | Primary key | Foreign keys | Key constraints |
|---|---|---|---|
| branches | branch_id | – | region / branch_type / status from fixed lists; branch_name unique |
| customers | customer_id | branch_id → branches | customer_type, gender, age_group, status from fixed lists |
| transactions | transaction_id | customer_id → customers, branch_id → branches | amount > 0; type/channel/status lists |
| loans | loan_id | customer_id → customers, branch_id → branches | loan_amount > 0; 0 ≤ interest_rate ≤ 40; outstanding ≥ 0 |
| branch_financials | financial_id | branch_id → branches | all money ≥ 0; one row per branch per month |
| customer_feedback | feedback_id | branch_id → branches | satisfaction_score integer 1–5 |
| managers | manager_id (autoincrement) | assigned_branch_id → branches | username unique (case-insensitive); is_active 0/1 |
| import_log | import_id | – | UNIQUE(table_name, file_hash) blocks duplicate imports |
| app_metadata | meta_key | – | stores `last_data_refresh` |

`ON DELETE RESTRICT` prevents deleting a branch or customer that still has dependent records.

## Indexes
| Index | Column(s) | Why |
|---|---|---|
| idx_customers_branch, idx_customers_join_date | customers(branch_id), (join_date) | branch filter, growth over time |
| idx_tx_branch, idx_tx_customer, idx_tx_date | transactions | branch/customer joins, date filter |
| idx_loans_branch, idx_loans_customer, idx_loans_status, idx_loans_app_date | loans | branch, status and date filters |
| idx_fin_branch, idx_fin_month | branch_financials | branch and reporting-month filters |
| idx_feedback_branch, idx_feedback_date | customer_feedback | branch and date filters |

## Normalisation notes
- Branch attributes (city, state, region) are stored once in `branches` and joined when needed.
- `customers.city` is the customer's own city (here equal to the branch city for synthetic data).
- `transactions.branch_id` and `loans.branch_id` are stored deliberately (the branch where the
  transaction/loan was booked) — a data-quality check reports any row whose branch differs from the
  customer's home branch.

## Safe SQL
Every value from the user (filters, uploaded data, credentials) is passed as a `?` parameter.
Table and column names used in dynamic SQL are checked against a whitelist / the live schema first.
