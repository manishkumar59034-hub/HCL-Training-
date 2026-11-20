# Data Dictionary

Dates use ISO format `YYYY-MM-DD`. Money is in Indian Rupees (₹). All records are synthetic.

## branches
| Column | Type | Description | Allowed values / example |
|---|---|---|---|
| branch_id | TEXT (PK) | Branch code | `BR001` |
| branch_name | TEXT | Unique branch name | `Mumbai Fort Main` |
| city / state | TEXT | Location | `Mumbai` / `Maharashtra` |
| region | TEXT | Sales region | North, South, East, West, Central |
| branch_type | TEXT | Market type | Metro, Urban, Semi-Urban, Rural |
| opening_date | TEXT | Date opened | `1998-04-01` |
| status | TEXT | Operating status | Active, Inactive, Under Review |

## customers
| Column | Type | Description | Allowed values / example |
|---|---|---|---|
| customer_id | TEXT (PK) | Synthetic ID | `CU000123` |
| branch_id | TEXT (FK) | Home branch | `BR004` |
| customer_name | TEXT | Synthetic label only — never a real name | `Customer 000123` |
| customer_type | TEXT | Segment | Individual, Business, Corporate, NRI, Senior Citizen |
| gender | TEXT, optional | Synthetic | Male, Female, Other |
| age_group | TEXT, optional | Synthetic | 18-25, 26-35, 36-45, 46-60, 60+ |
| join_date | TEXT | Account opening date | `2025-08-14` |
| city | TEXT | Customer city | `Pune` |
| status | TEXT | **Current** status (not historical) | Active, Inactive, Closed |

## transactions
| Column | Type | Description | Allowed values |
|---|---|---|---|
| transaction_id | TEXT (PK) | ID | `TX0000001` |
| customer_id, branch_id | TEXT (FK) | Who / where | must exist |
| transaction_date | TEXT | Date | within data window |
| transaction_type | TEXT | Kind | Deposit, Withdrawal, Transfer, Bill Payment, Loan Repayment |
| amount | REAL | Amount, > 0 | `42000.50` |
| channel | TEXT | Channel | Branch, ATM, Mobile Banking, Internet Banking, UPI |
| status | TEXT | Outcome | Success, Failed, Reversed |

## loans
| Column | Type | Description | Allowed values |
|---|---|---|---|
| loan_id | TEXT (PK) | ID | `LN000001` |
| customer_id, branch_id | TEXT (FK) | Borrower / booking branch | must exist |
| application_date | TEXT | Date applied | |
| loan_type | TEXT | Product | Home, Personal, Vehicle, Business, Education, Gold Loan |
| loan_amount | REAL | Amount applied/sanctioned, > 0 | |
| interest_rate | REAL | Annual %, 0–40 | `9.4` |
| loan_status | TEXT | Lifecycle stage | Pending, Approved, Rejected, Disbursed, Closed |
| outstanding_amount | REAL | Still owed (0 unless disbursed) | |
| repayment_status | TEXT | Repayment health | Not Applicable, Current, Overdue, Defaulted, Repaid |

Lifecycle: *Pending → Approved → Disbursed → Closed*, or *Pending → Rejected*.
Only Disbursed/Closed loans can be Current, Overdue, Defaulted or Repaid.

## branch_financials
| Column | Type | Description |
|---|---|---|
| financial_id | TEXT (PK) | `FN-BR001-2025-05` |
| branch_id | TEXT (FK) | Branch |
| reporting_month | TEXT | First day of month, `2025-05-01` (one row per branch per month) |
| revenue | REAL | Total income for the month (interest, fees, commissions) |
| expenses | REAL | Operating costs for the month |
| deposits | REAL | **New deposits mobilised in the month** (a flow, so monthly values can be summed) |
| loan_disbursement | REAL | Loan money paid out in the month. In demo data this equals the sum of Disbursed/Closed loans in the loan register for that branch-month |
| revenue_target | REAL | Revenue target for the month |

## customer_feedback
| Column | Type | Description |
|---|---|---|
| feedback_id | TEXT (PK) | `FB000001` |
| branch_id | TEXT (FK) | Branch rated |
| feedback_date | TEXT | Date |
| satisfaction_score | INTEGER | 1 (very poor) – 5 (excellent) |
| feedback_category | TEXT | Service Quality, Waiting Time, Staff Behaviour, Digital Services, Loan Processing, Account Services, Other |

## managers
| Column | Type | Description |
|---|---|---|
| manager_id | INTEGER (PK) | Auto ID |
| username | TEXT | Unique, case-insensitive |
| password_hash | TEXT | `pbkdf2_sha256$iterations$salt$hash` — never the password |
| manager_name | TEXT | Display name |
| role | TEXT | Administrator, Regional Manager, Branch Manager, Analyst |
| assigned_branch_id | TEXT, nullable | If set for a Branch Manager, their dashboard is limited to that branch |
| is_active | INTEGER | 1 active, 0 inactive (cannot log in) |
| created_at, last_login | TEXT | Timestamps |
| failed_attempts, locked_until | INTEGER, TEXT | Login lockout tracking |

## Cleaning rules (applied to uploads, logged on screen)
1. Column names trimmed, lower-cased, spaces/hyphens → underscores.
2. Text trimmed; empty strings treated as missing.
3. Category values matched case-insensitively (`approved` → `Approved`).
4. ₹ symbols, "Rs", "INR" and thousands separators removed from numbers.
5. Dates parsed (day-first for ambiguous formats) and rewritten as `YYYY-MM-DD`.
6. `reporting_month` normalised to the first day of its month.
7. Fully empty rows removed.

Nothing else is changed. Missing or invalid values are **reported, not filled in**.

## Assumptions
- Monthly `deposits` is new deposit mobilisation, not closing balance.
- Customer `status` is the current status; historical status changes are not tracked.
- "Total Customers" for a period = customers who had joined by the period end.
- Satisfaction is averaged over individual responses (each response weighs equally).
