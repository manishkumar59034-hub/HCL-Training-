# KPI Definitions and Business Rules

All formulas live in `analytics/kpi_calculations.py`; every page imports them from there.
If a denominator is zero or missing, or a previous period does not exist, the KPI shows **N/A**.

## Financial
| KPI | Formula | Notes |
|---|---|---|
| Total Revenue / Expenses / Deposits / Loan Disbursement | Sum of monthly values in the filter | From `branch_financials` |
| Net Profit | Revenue − Expenses | |
| Profit Margin % | Net Profit ÷ Revenue × 100 | |
| Target Achievement % | Actual Revenue ÷ Revenue Target × 100 | Bank/region level uses total ÷ total (not an average of %) |
| Expense Ratio % | Expenses ÷ Revenue × 100 | |
| Revenue / Expense / Deposit Growth % (MoM) | (Latest month − previous month) ÷ previous month × 100 | Within the selected months; N/A for one month |
| Period trend % | (Avg of last 3 months − avg of first 3 months) ÷ avg of first 3 × 100 | Last vs first month when fewer than 6 months; used for "increasing/decreasing" statements and insight rules |
| Avg Revenue per Customer | Total Revenue ÷ Total Customers | |

## Customers
| KPI | Formula |
|---|---|
| Total Customers | Customers with join_date ≤ period end |
| New Customers | Customers with join_date inside the period |
| Active Customers | Total customers whose current status is Active |
| Customer Growth % | (Customers at period end − customers at period start) ÷ customers at period start × 100 |
| Average Satisfaction | Mean of satisfaction_score (1–5) for feedback in the period |

## Loans
| KPI | Formula |
|---|---|
| Loan Applications | Count of loans applied for in the period (any status) |
| Approved Loans | Status Approved + Disbursed + Closed |
| Rejected Loans | Status Rejected |
| Approval Rate % | Approved ÷ Total Applications × 100 (pending included in denominator) |
| Disbursed Loans | Status Disbursed + Closed |
| Total Loan Disbursement | Sum of `branch_financials.loan_disbursement` (same value on every page) |
| Outstanding | Sum of outstanding_amount on disbursed loans |
| Default Rate % | Disbursed loans with repayment_status Defaulted ÷ disbursed loans × 100 |

## Performance categories (configurable)
| Category | Rule (default) |
|---|---|
| High Performer | Target achievement ≥ 100% |
| Average Performer | 80% ≤ achievement < 100% |
| Low Performer | Achievement < 80% |

Defaults: `config/settings.py`. They can also be changed for the session on the Branch Performance page.

## Insight rules (`analytics/insights.py`)
| Insight | Type | Trigger | Recommended action |
|---|---|---|---|
| Highest revenue / profit branch | Positive | Top branch in filter | – |
| Branches exceeding target | Positive | Achievement ≥ 100% | – |
| Revenue growing / deposits increasing | Positive | Period trend > 0 | – |
| Customer base growing | Positive | Customer growth > 0 | – |
| Highest satisfaction | Positive | Top branch with score ≥ 4.0 | – |
| Branch below target | Warning (high) | Achievement < 80% | Review sales strategy, customer acquisition and local opportunities |
| Expenses rising faster than revenue | Warning | Expense trend > revenue trend + 3 pts and > 0 | Investigate operating expenses; cost optimisation |
| Profit declining | Warning | Profit trend < −5% | Analyse revenue mix and cost base |
| Deposit growth negative | Warning | Deposit trend < 0 | Investigate customer retention and deposit acquisition |
| Unusually high expenses | Warning | Expense ratio > 75% | Benchmark cost structure with peers |
| Low satisfaction | Warning | Avg score < 3.5 | Review service quality, waiting time, complaints |
| Satisfaction decreasing | Warning | Monthly avg fell ≥ 0.25 points | Service-quality audit |
| High default rate | Warning (high) | Default rate > 8% with ≥ 5 disbursed loans | Review loan monitoring and risk management |
| Customer growth slowing | Warning | New customers/month in 2nd half < 90% of 1st half | Strengthen acquisition campaigns |
| Bank-wide expenses outpacing revenue | Warning | Bank expense trend > revenue trend + 1 pt | Cost optimisation |

All thresholds are constants in `config/settings.py` so they are easy to explain and change.
