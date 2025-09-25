# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a Flask-based Stripe Dashboard application for analyzing transaction data across multiple companies (CGGE, Krystal Institute, Krystal Technology). It processes CSV data from Stripe exports and provides comprehensive financial reporting with monthly statements, payout reconciliation, and interactive analytics.

### Key Components

- **Flask Web Application**: Main server on port 8081 with SQLAlchemy ORM
- **CSV Processing Pipeline**: Imports Stripe CSV exports from `complete_csv/` directory
- **Multi-Company Support**: Handles transactions for three separate Stripe accounts
- **Two Reconciliation Methods**:
  - Monthly statements (by Created dates) for balance tracking
  - Payout reconciliation (by Transfer dates) matching Stripe reports

### Service Architecture

- `app/services/complete_csv_service.py`: Primary CSV import and processing
- `app/services/csv_transaction_service.py`: Legacy CSV format support
- `app/services/multi_stripe_service.py`: Multi-account transaction handling
- `app/routes/analytics.py`: API endpoints for statements and reconciliation

## Development Commands

### Start Development Server
```bash
# Activate virtual environment and run
source venv/bin/activate
python3 run.py

# Or use the startup script
./start.sh
```

### Production Deployment
```bash
# Quick deploy with database initialization
./deploy.sh

# Manual production server with gunicorn
gunicorn -w 4 -b 0.0.0.0:8081 run:app
```

### Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment configuration
cp .env.example .env
```

## Key API Endpoints

### Monthly Statements & Reconciliation
- `GET /analytics/api/monthly-statement` - Generate monthly statements (Created dates)
  - Parameters: `company`, `year`, `month`, `previous_balance`
- `GET /analytics/api/payout-reconciliation` - Payout reconciliation (Transfer dates)  
  - Parameters: `company`, `year`, `month`
- `GET /analytics/api/csv-health` - CSV import status and diagnostics
- `GET /analytics/api/account-amounts` - Account balance summaries

### Web Interfaces
- `/analytics/dashboard` - Main analytics dashboard
- `/analytics/statement-generator` - Interactive statement generator
- `/analytics/monthly-statement` - Monthly statement interface
- `/analytics/payout-reconciliation` - Payout reconciliation interface

## Data Processing

### CSV Import Structure
Place CSV files in:
```
complete_csv/
├── cgge_unified_payments_YYYYMMDD.csv
├── ki_unified_payments_YYYYMMDD.csv
└── kt_unified_payments_YYYYMMDD.csv
```

### Transaction Processing Rules
- **Succeeded/Refunded**: Real money movement (included in balances)
- **Failed/Cancelled**: Informational only (excluded from totals)
- **Refunds**: Appear as credits reducing account balance
- **Fees**: Automatically calculated and tracked

### Balance Tracking
- Opening balance carries forward from previous month's closing
- Dual date tracking: Created (transaction date) vs Transfer (payout date)
- Currency conversion: CNY to HKD at configurable rate

## Testing Approach

Currently no automated test framework is configured. For testing:
- Manual testing via web interface
- CSV health check endpoint for validation
- Database queries for reconciliation verification

## Important Notes

- Port 8081 is the default for both development and production
- SQLite database stored in `instance/app.db`
- CSV directory path resolution tries multiple locations (env var, cwd, Docker paths)
- Complete CSV format is preferred over legacy formats
- August 2025 data should be in `complete_csv/` directory