# Stripe Dashboard Revamp - Documentation

## Overview
This document outlines the comprehensive revamp of the Stripe Dashboard application to ensure monthly statements are consistent with Stripe's payout reconciliation reports.

## Key Improvements

### 1. Dynamic Data Processing
- **Before**: Hardcoded transaction data in production_server.py
- **After**: Dynamic processing of CSV files from `complete_csv/` directory
- **Impact**: Real-time data accuracy, no manual updates needed

### 2. Email Address Implementation
- **Before**: Self-explanatory text like "student1@cgge.edu" 
- **After**: Actual customer email addresses extracted from CSV metadata
- **Priority Order**:
  1. Customer Email field
  2. 2. User email (metadata) field
  3. Customer Description field
  4. Fallback to User ID if no email available

### 3. Stripe Reconciliation Format Consistency
- **Monthly Statements**: Now use transaction dates for proper monthly balance tracking
- **Payout Reconciliation**: Uses transfer dates to match Stripe's format exactly
- **Dual Reporting**: Supports both statement types for different accounting needs

### 4. Enhanced PDF Generation
- **Format**: Maintains CGGE-MonthlyStatement_YYYY_MM.pdf naming convention
- **Content**: 
  - Company header with month/year
  - Summary section with opening/closing balances
  - Individual transaction listing with email addresses
  - Professional formatting matching original requirements

### 5. CSV Service Enhancements
- **Location**: `app/services/complete_csv_service.py`
- **Features**:
  - Automatic CSV file discovery and parsing
  - Email extraction from multiple metadata fields
  - Proper debit/credit accounting
  - Fee calculation and reconciliation
  - Support for multiple companies (CGGE, KI, KT)

## File Structure Changes

### Removed/Archived Files
```
archive/
├── analyze_cgge_data.py
├── app_simple.py
├── calculate_adjustments.py
├── cgge_data_processor.py
├── cgge_july_final.py
├── corrected_statement_generator.py
├── debug_import.py
├── find_solution.py
├── fixed_server.py
├── stable_server.py
├── test_app.py
├── test_db.py
├── test_pdf_export.py
├── test_real_api.py
├── working_server.py
├── csv_production_server.py
└── server.py
```

### Active Files
```
production_server.py         # Main server file (revamped)
app/services/
├── complete_csv_service.py # Enhanced CSV processing with email extraction
└── ...other services
complete_csv/               # CSV data directory
├── cgge_2021_Nov-2025_Aug.csv
├── ki_2023_Jul-2025_Aug.csv
└── kt_2022_Sept-2025_Aug.csv
```

## API Endpoints

### Main Dashboard
- **URL**: `/`
- **Description**: Shows summary of all companies with latest month data

### Monthly Statement Generator
- **URL**: `/monthly-statement`
- **Features**:
  - Company selection
  - Month selection
  - Output format (HTML/PDF/CSV)
  - Email addresses in party field

### Payout Reconciliation
- **URL**: `/payout-reconciliation`
- **Features**:
  - Matches Stripe's payout reconciliation format
  - Uses transfer dates for accuracy
  - Shows charges, refunds, and payout reversals

### API Status
- **URL**: `/api/status`
- **Response**: JSON with system status and data integrity checks

## Data Consistency

### Pain Point Resolution
**Before**: Monthly statement data not consistent with Stripe reports
**After**: Complete consistency achieved through:
1. Proper date handling (transaction vs transfer dates)
2. Accurate fee calculation
3. Email address extraction from metadata
4. Dynamic data processing from CSV files

### Validation Points
- CGGE July 2025 reconciliation matches Stripe exactly
- Email addresses displayed instead of placeholder text
- Individual transactions properly listed
- Running balances accurately calculated

## Deployment Instructions

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Required packages:
   - Flask
   - pandas
   - reportlab (for PDF generation)

2. **Ensure CSV Files**:
   - Place updated CSV files in `complete_csv/` directory
   - Files should follow naming convention: `{company}_YYYY_MMM-YYYY_MMM.csv`

3. **Run Server**:
   ```bash
   python production_server.py
   ```
   Server runs on port 8081 by default

4. **Access Dashboard**:
   - Local: http://localhost:8081
   - Network: http://192.168.0.104:8081

## CSV Data Format Requirements

### Required Fields
- `id`: Transaction ID
- `Created date (UTC)` or `Created (UTC)`: Transaction date
- `Amount`: Transaction amount
- `Fee`: Processing fee
- `Currency`: Transaction currency
- `Customer Email`: Customer email address
- `2. User email (metadata)`: Alternative email field
- `Transfer Date (UTC)`: For payout reconciliation

### Company Identification
- Files starting with `cgge_`: CGGE transactions
- Files starting with `ki_`: Krystal Institute transactions
- Files starting with `kt_`: Krystal Technology transactions

## Testing Checklist

- [x] Dynamic CSV data loading
- [x] Email address extraction and display
- [x] Monthly statement generation (HTML/PDF/CSV)
- [x] Payout reconciliation report
- [x] Balance calculations
- [x] Fee rate calculations
- [x] PDF formatting and download
- [x] API status endpoint

## Maintenance Notes

### Adding New Companies
1. Add CSV file to `complete_csv/` with appropriate prefix
2. Update `company_names` dict in `complete_csv_service.py`
3. No code changes needed in production_server.py

### Updating Data
1. Replace CSV files in `complete_csv/` directory
2. Server automatically picks up new data
3. No restart required for data updates

### Troubleshooting
- Check logs for CSV parsing errors
- Verify email fields in CSV files
- Ensure date formats are consistent
- Validate currency and amount fields

## Security Considerations

- No hardcoded credentials
- CSV files should be access-controlled
- Email addresses handled as PII
- No sensitive data in logs

## Performance Optimizations

- CSV files cached in memory during processing
- Decimal arithmetic for financial accuracy
- Efficient pandas operations for large datasets
- Lazy loading of transaction details

---

*Last Updated: September 2024*
*Version: 2.0 (Revamped)*