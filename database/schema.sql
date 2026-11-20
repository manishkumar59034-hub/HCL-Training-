-- =====================================================================
-- Bank Branch Performance Analysis - SQLite schema
-- All tables use explicit primary keys, foreign keys and CHECK constraints.
-- Foreign keys are enforced by `PRAGMA foreign_keys = ON` in database/db.py.
-- =====================================================================

-- ---------------------------------------------------------------------
-- A. branches
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS branches (
    branch_id      TEXT PRIMARY KEY,                         -- e.g. BR001
    branch_name    TEXT NOT NULL UNIQUE,
    city           TEXT NOT NULL,
    state          TEXT NOT NULL,
    region         TEXT NOT NULL CHECK (region IN ('North','South','East','West','Central')),
    branch_type    TEXT NOT NULL CHECK (branch_type IN ('Metro','Urban','Semi-Urban','Rural')),
    opening_date   TEXT NOT NULL,                            -- ISO date YYYY-MM-DD
    status         TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Inactive','Under Review'))
);

-- ---------------------------------------------------------------------
-- B. customers  (synthetic identifiers only - no real personal data)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id    TEXT PRIMARY KEY,                         -- e.g. CU000001
    branch_id      TEXT NOT NULL REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    customer_name  TEXT NOT NULL,                            -- synthetic label e.g. "Customer 000001"
    customer_type  TEXT NOT NULL CHECK (customer_type IN ('Individual','Business','Corporate','NRI','Senior Citizen')),
    gender         TEXT CHECK (gender IN ('Male','Female','Other') OR gender IS NULL),
    age_group      TEXT CHECK (age_group IN ('18-25','26-35','36-45','46-60','60+') OR age_group IS NULL),
    join_date      TEXT NOT NULL,
    city           TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Active' CHECK (status IN ('Active','Inactive','Closed'))
);

-- ---------------------------------------------------------------------
-- C. transactions
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id   TEXT PRIMARY KEY,                       -- e.g. TX0000001
    customer_id      TEXT NOT NULL REFERENCES customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    branch_id        TEXT NOT NULL REFERENCES branches(branch_id)   ON UPDATE CASCADE ON DELETE RESTRICT,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Deposit','Withdrawal','Transfer','Bill Payment','Loan Repayment')),
    amount           REAL NOT NULL CHECK (amount > 0),
    channel          TEXT NOT NULL CHECK (channel IN ('Branch','ATM','Mobile Banking','Internet Banking','UPI')),
    status           TEXT NOT NULL DEFAULT 'Success' CHECK (status IN ('Success','Failed','Reversed'))
);

-- ---------------------------------------------------------------------
-- D. loans
--   loan_status      : Pending | Approved | Rejected | Disbursed | Closed
--   repayment_status : Not Applicable | Current | Overdue | Defaulted | Repaid
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS loans (
    loan_id            TEXT PRIMARY KEY,                     -- e.g. LN000001
    customer_id        TEXT NOT NULL REFERENCES customers(customer_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    branch_id          TEXT NOT NULL REFERENCES branches(branch_id)   ON UPDATE CASCADE ON DELETE RESTRICT,
    application_date   TEXT NOT NULL,
    loan_type          TEXT NOT NULL CHECK (loan_type IN ('Home Loan','Personal Loan','Vehicle Loan','Business Loan','Education Loan','Gold Loan')),
    loan_amount        REAL NOT NULL CHECK (loan_amount > 0),
    interest_rate      REAL NOT NULL CHECK (interest_rate >= 0 AND interest_rate <= 40),
    loan_status        TEXT NOT NULL CHECK (loan_status IN ('Pending','Approved','Rejected','Disbursed','Closed')),
    outstanding_amount REAL NOT NULL DEFAULT 0 CHECK (outstanding_amount >= 0),
    repayment_status   TEXT NOT NULL DEFAULT 'Not Applicable'
                       CHECK (repayment_status IN ('Not Applicable','Current','Overdue','Defaulted','Repaid'))
);

-- ---------------------------------------------------------------------
-- E. branch_financials  (one row per branch per reporting month)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS branch_financials (
    financial_id      TEXT PRIMARY KEY,                      -- e.g. FN-BR001-2025-01
    branch_id         TEXT NOT NULL REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    reporting_month   TEXT NOT NULL,                         -- first day of month, YYYY-MM-01
    revenue           REAL NOT NULL CHECK (revenue >= 0),
    expenses          REAL NOT NULL CHECK (expenses >= 0),
    deposits          REAL NOT NULL CHECK (deposits >= 0),
    loan_disbursement REAL NOT NULL CHECK (loan_disbursement >= 0),
    revenue_target    REAL NOT NULL CHECK (revenue_target >= 0),
    UNIQUE (branch_id, reporting_month)
);

-- ---------------------------------------------------------------------
-- F. customer_feedback
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_feedback (
    feedback_id        TEXT PRIMARY KEY,                     -- e.g. FB000001
    branch_id          TEXT NOT NULL REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    feedback_date      TEXT NOT NULL,
    satisfaction_score INTEGER NOT NULL CHECK (satisfaction_score BETWEEN 1 AND 5),
    feedback_category  TEXT NOT NULL CHECK (feedback_category IN ('Service Quality','Waiting Time','Staff Behaviour','Digital Services','Loan Processing','Account Services','Other'))
);

-- ---------------------------------------------------------------------
-- G. managers  (password_hash only - plain-text passwords are never stored)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS managers (
    manager_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username           TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash      TEXT NOT NULL,
    manager_name       TEXT NOT NULL,
    role               TEXT NOT NULL DEFAULT 'Branch Manager'
                       CHECK (role IN ('Administrator','Regional Manager','Branch Manager','Analyst')),
    assigned_branch_id TEXT REFERENCES branches(branch_id) ON UPDATE CASCADE ON DELETE SET NULL,
    is_active          INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    failed_attempts    INTEGER NOT NULL DEFAULT 0,
    locked_until       TEXT,
    last_login         TEXT
);

-- ---------------------------------------------------------------------
-- Supporting table: import_log (prevents importing the same file twice)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS import_log (
    import_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name     TEXT NOT NULL,
    file_name      TEXT NOT NULL,
    file_hash      TEXT NOT NULL,
    rows_inserted  INTEGER NOT NULL DEFAULT 0,
    rows_skipped   INTEGER NOT NULL DEFAULT 0,
    imported_by    TEXT,
    imported_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (table_name, file_hash)
);

-- ---------------------------------------------------------------------
-- Supporting table: app_metadata (e.g. last data refresh timestamp)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_metadata (
    meta_key   TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL
);

-- ---------------------------------------------------------------------
-- Indexes on commonly filtered columns
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_customers_branch      ON customers(branch_id);
CREATE INDEX IF NOT EXISTS idx_customers_join_date   ON customers(join_date);
CREATE INDEX IF NOT EXISTS idx_tx_branch             ON transactions(branch_id);
CREATE INDEX IF NOT EXISTS idx_tx_customer           ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_tx_date               ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_loans_branch          ON loans(branch_id);
CREATE INDEX IF NOT EXISTS idx_loans_customer        ON loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_loans_status          ON loans(loan_status);
CREATE INDEX IF NOT EXISTS idx_loans_app_date        ON loans(application_date);
CREATE INDEX IF NOT EXISTS idx_fin_branch            ON branch_financials(branch_id);
CREATE INDEX IF NOT EXISTS idx_fin_month             ON branch_financials(reporting_month);
CREATE INDEX IF NOT EXISTS idx_feedback_branch       ON customer_feedback(branch_id);
CREATE INDEX IF NOT EXISTS idx_feedback_date         ON customer_feedback(feedback_date);
