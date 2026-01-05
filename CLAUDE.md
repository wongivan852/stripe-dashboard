# CLAUDE.md - Stripe Dashboard Project Context

> This file provides essential context for Claude Code and other AI assistants working on this project.
> **Last Updated:** 2026-01-05

---

## Project Overview

**Stripe Dashboard** - A Flask-based analytics and reporting tool for Stripe payment data. Provides monthly statements, balance summaries, payout reconciliation, and transaction analysis.

### Key Facts
- **Framework:** Flask with Python 3.12
- **Port:** 8006
- **Data Source:** CSV files from Stripe exports (balance_history, payments)
- **Database:** SQLite (optional, CSV files are primary data source)

---

## Directory Structure

```
/home/user/stripe-dashboard/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── routes/
│   │   ├── analytics.py      # Main analytics routes (statements, reports)
│   │   └── health.py         # Health check endpoint
│   └── models/               # SQLAlchemy models (optional)
├── data/                     # CSV data files
│   ├── cgge_balance_history.csv      # CGGE transaction history
│   ├── CGGE_Balance_Summary_*.csv    # Balance summaries
│   ├── stripe_cgge_payments.csv      # Payment details
│   └── ...                           # Other company data
├── venv/                     # Python virtual environment
├── CLAUDE.md                 # This file
└── requirements.txt
```

---

## Running the Application

### Start Flask Server
```bash
cd /home/user/stripe-dashboard
./venv/bin/python -m flask --app app:create_app run --host=0.0.0.0 --port=8006
```

### Background Start
```bash
./venv/bin/python -m flask --app app:create_app run --host=0.0.0.0 --port=8006 > /tmp/stripe_dashboard.log 2>&1 &
```

### Restart Server
```bash
lsof -i:8006 | awk 'NR>1 {print $2}' | xargs kill -9 2>/dev/null
sleep 2
./venv/bin/python -m flask --app app:create_app run --host=0.0.0.0 --port=8006 > /tmp/stripe_dashboard.log 2>&1 &
```

---

## Key URLs

| URL | Description |
|-----|-------------|
| http://localhost:8006/health | Health check endpoint |
| http://localhost:8006/analytics/statement-generator | Statement generator form |
| http://localhost:8006/analytics/statement-generator/generate?company=1&format=detailed&from_date=2025-12-01&to_date=2025-12-31 | Bank Statement |
| http://localhost:8006/analytics/monthly-statement-v2?company=1&from_date=2025-12-01&to_date=2025-12-31 | Monthly Statement V2 |
| http://localhost:8006/analytics/simple | Simple analytics view |

---

## Company Mapping

| Company ID | Code | Name |
|------------|------|------|
| 1 | cgge | CG Global Entertainment |
| 2 | ki | Krystal Institute |
| 3 | kt | Krystal Technology |
| 4 | cgge_sz | CGGE Shenzhen |

---

## Key Functions in analytics.py

### `get_balance_summary(company_id, from_date, to_date)`
Calculates balance summary from balance_history.csv.

**Returns:**
- `starting_balance`: Sum of all transactions before period start
- `ending_balance`: Starting balance + period activity
- `total_payouts`: Sum of payouts in period (by Created Date)
- `activity_gross`: Payments + refunds (using Amount, not Net)
- `activity_fee`: Total processing fees
- `activity_net`: Activity gross - fees

**Date Logic:**
- Uses **Created Date** for ALL transactions (accountant's method)
- Refund fees are included in total fees, not in activity gross

### `generate_statement()` (Route: /analytics/statement-generator/generate)
Generates detailed bank statement HTML.

### `monthly_statement_v2()` (Route: /analytics/monthly-statement-v2)
Generates monthly statement with Debit/Credit columns.

### `generate_detailed_statement()`
Helper function that generates the HTML for detailed statements.

---

## Balance Calculation Logic

### Activity Calculation (Matching Stripe Balance Summary)
```
Activity Gross = Payments Amount + Charges Amount + Refunds Amount (gross, not net)
Activity Fee = Payment Fees + Charge Fees + Refund Fees
Activity Net = Activity Gross - Activity Fee
```

### Payout Date Attribution
- **Current Setting:** Uses **Created Date** (accountant's method)
- Payouts are attributed to the month when initiated, not when transferred
- This affects which payouts appear in a given period's Total Payouts

### Ending Balance Verification
```
Ending Balance = Starting Balance + Activity Net - Total Payouts
```

---

## Data Files

### cgge_balance_history.csv
Main transaction history with columns:
- `id`: Transaction ID (txn_xxx)
- `Type`: payment, payout, payment_refund, refund, charge
- `Source`: Source ID (py_xxx for payments, po_xxx for payouts)
- `Amount`: Gross amount
- `Fee`: Processing fee
- `Net`: Net amount (Amount - Fee)
- `Currency`: hkd, cny, etc.
- `Created (UTC)`: When transaction was created
- `Transfer Date (UTC)`: When payout was transferred to bank
- `2. User email (metadata)`: Customer email
- `3. User name (metadata)`: Customer name

### Balance Summary CSV
Pre-calculated summary with:
- starting_balance
- activity_gross (before fees)
- activity_fee
- activity (net)
- payouts_gross
- payouts_fee
- payouts (total)
- ending_balance

---

## Recent Changes (January 2026)

### 2026-01-05
- Fixed 35.26 HKD discrepancy in activity calculation
  - Now uses refund Amount (gross) instead of Net for Activity Gross
  - Refund fees correctly included in total fees
- Changed payout date logic to use Created Date (accountant's method)
  - Total Payouts: 69,884.34 (was 71,516.68 with Transfer Date)
  - Starting Balance adjusted accordingly
- Added Total Payouts card to Bank Statement summary
- Updated all statement pages to use `get_balance_summary()` values
- Fixed f-string formatting issues in generate_detailed_statement()

---

## Integration with Krystal Platform

This dashboard integrates with the Integrated Business Platform at port 8080:
- Links from `/home/user/integrated_business_platform/stripe_integration/templates/stripe_integration/dashboard.html`
- Statement Generator and Monthly Statement buttons link to this Flask app

---

## Troubleshooting

### Server Won't Start
```bash
# Check if port is in use
lsof -i:8006

# Kill existing process
kill -9 $(lsof -t -i:8006)
```

### Health Check Shows Unhealthy Database
- This is expected - the app uses CSV files as primary data source
- SQLAlchemy database connection errors can be ignored

### Values Don't Match Balance Summary CSV
- Check date logic (Created vs Transfer Date for payouts)
- Verify refund amounts use gross (Amount) not net
- Ensure all functions use `get_balance_summary()` values

---

## Git Repository

```bash
# Push to GitHub
git add .
git commit -m "Description of changes"
git push origin main

# Remote
git@github.com:wongivan852/stripe-dashboard.git
```

---

## For Claude Code Sessions

When starting a new session:
1. Read this file for context
2. Check if Flask server is running: `lsof -i:8006`
3. View recent logs: `tail -20 /tmp/stripe_dashboard.log`
4. Test endpoints before making changes
