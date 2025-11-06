# Stripe Dashboard - Monthly Statement Generator

## 🎯 Project Overview

A complete Flask-based solution for generating professional monthly statements in traditional debit/credit accounting format. Creates statements that match the exact format of CGGE-MonthlyStatement_2025_07.pdf with customer transaction summaries.

## ✨ Key Features

- **Traditional Debit/Credit Format**: Proper accounting methodology with running balance
- **Customer Transaction Summary**: Separate section showing customer payments and details
- **Statement Management**: Create, edit, save, and generate PDF statements
- **Opening Balance Carryforward**: Auto-loads previous month's closing balance
- **Multi-Company Support**: CGGE, Krystal Institute, Krystal Technology
- **Professional PDF Generation**: Browser-based print-to-PDF functionality

## 🚀 Quick Start

### Start the Server
```bash
python monthly_statement_generator.py
```

### Access the Application
Open your browser and go to: **http://localhost:8081**

## 📁 Project Structure

```
stripe-dashboard/
├── monthly_statement_generator.py    # Main application server
├── manual_reconciliation_server.py   # Alternative reconciliation server
├── production_server.py              # Legacy CSV processing server
├── data/
│   ├── monthly_statement_data.json       # Statement data storage
│   └── manual_reconciliation_data.json   # Reconciliation data storage
├── docs/
│   ├── README.md                         # This file
│   ├── MONTHLY_STATEMENT_SOLUTION.md     # Complete solution guide
│   ├── CGGE-MonthlyStatement_2025_07.pdf # Reference format
│   └── [Other documentation files]
├── complete_csv/                     # Stripe CSV export files
├── payout_reconciliation_cgge/       # Historical Stripe payout PDFs
├── app/                              # Flask application components
├── config/                           # Configuration files
└── archive/                          # Archived old files
```

## 💼 Business Use Cases

### For CGGE, Krystal Institute, and Krystal Technology
- Generate monthly financial statements
- Track customer payments and transactions
- Maintain proper debit/credit accounting records
- Carry forward balances between months
- Export professional PDF reports for accounting

## 📊 Statement Format

### Main Report Table
- **Opening Balance**: Brought forward from previous month
- **Transaction Details**: Date, Nature, Party, Debit/Credit, Running Balance
- **Subtotals**: Summary of all debits and credits
- **Closing Balance**: Carry forward to next month

### Customer Transaction Summary
- **Customer List**: Names and email addresses
- **Transaction Amounts**: Individual payment details
- **Total Summary**: Sum of all customer payments

## 🛠️ Technical Stack

- **Backend**: Python Flask
- **Frontend**: HTML/CSS/JavaScript
- **Data Storage**: JSON files
- **PDF Generation**: Browser print-to-PDF
- **Styling**: CSS Grid and Flexbox

## 📋 How to Use

### 1. Create New Statement
1. Click "Create Monthly Statement"
2. Select company and period (YYYY-MM)
3. Load opening balance from previous month
4. Add individual transactions

### 2. Add Transactions
For each transaction specify:
- **Date**: Transaction date
- **Nature**: Gross Payment, Processing Fee, Payout, etc.
- **Party**: Customer name/email or "Stripe"
- **Amount Type**: Debit (increases) or Credit (decreases balance)
- **Amount**: HKD amount
- **Description**: Transaction details

### 3. Manage Statements
- **Save**: Persist data for future editing
- **Edit**: Modify existing saved statements
- **Generate PDF**: Create professional reports
- **Delete**: Remove unwanted statements

## 💾 Data Management

### Statement Data
- Stored in `data/monthly_statement_data.json`
- Preserves creation and update timestamps
- Maintains full transaction history
- Supports backup and restore

### Key Structure
```json
{
  "company_period": {
    "company": "cgge",
    "period": "2025-08",
    "opening_balance": 554.77,
    "closing_balance": 0.00,
    "transactions": [...]
  }
}
```

## 🎯 Current Status

### Active Data (August 2025)
- **CGGE**: 19 transactions, 5 customer payments (HK$480.99)
- **KI**: No transactions (HK$1,427.61 opening balance)
- **KT**: No transactions (HK$0.00 balance)

### Features Implemented
✅ Traditional debit/credit format  
✅ Running balance calculation  
✅ Opening balance carryforward  
✅ Customer transaction summary  
✅ Statement editing capability  
✅ Data persistence  
✅ Professional PDF generation  
✅ Multi-company support  

## 📚 Documentation

- **[Complete Solution Guide](docs/MONTHLY_STATEMENT_SOLUTION.md)**: Detailed feature documentation
- **[Reference Format](docs/CGGE-MonthlyStatement_2025_07.pdf)**: Original PDF format to match
- **[Deployment Guides](docs/)**: Various deployment documentation

## 🔧 Server Configuration

### Main Server
- **File**: `monthly_statement_generator.py`
- **Port**: 8081
- **Features**: Full statement management with edit capability

### Alternative Servers
- **Manual Reconciliation**: `manual_reconciliation_server.py` (Port 8081)
- **Legacy CSV Parser**: `production_server.py` (Various ports)

## 🔄 Development History

This project evolved from a CSV processing system to a complete manual statement generator:

1. **Phase 1**: CSV parsing and automated processing
2. **Phase 2**: Manual reconciliation input system  
3. **Phase 3**: Traditional debit/credit accounting format
4. **Phase 4**: Customer transaction summary integration
5. **Phase 5**: Statement editing and management features

## 📞 Support

For technical issues or feature requests:
- Review documentation in `docs/` directory
- Check existing statement data in `data/` directory
- Verify server logs for troubleshooting

---

**The Monthly Statement Generator provides a complete solution for professional accounting statement generation with traditional debit/credit format and customer transaction summaries.**

**Access the application at: http://localhost:8081**