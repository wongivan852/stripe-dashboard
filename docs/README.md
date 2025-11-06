# 🏦 Company Stripe Dashboard

A comprehensive Flask-based web application for analyzing Stripe transaction data across multiple companies with monthly statement consolidation, advanced reporting capabilities, and currency handling.

**📍 Repository**: [wongivan852/stripe-dashboard](https://github.com/wongivan852/stripe-dashboard)

## 🆕 Recent Updates (August 2025)

### ✅ Major Transaction Processing & Balance Reconciliation Fixes
- **Krystal Technology Transfer Date Correction**: Fixed 12 transactions from March 2023 onwards with incorrect transfer dates
- **Refund Processing Fix**: Corrected refunds to properly reduce account balance (appear as credits)
- **Monthly Balance Carry Forward**: Fixed opening balance calculation to properly carry closing balances between months
- **Transaction Format Restoration**: Restored gross amount + processing fee display format matching deployed version
- **Backup File Exclusion**: Prevented duplicate processing of backup CSV files

### ✅ Enhanced Balance Carry-Forward & Date Field Analysis
- **Fixed Balance Continuity**: Resolved November 2021 → December 2021 carry-forward issue (HK$45.95)
- **Date Field Optimization**: Analyzed Created vs Available On dates for optimal manual reconciliation
- **Cross-Month Transfer Logic**: Improved handling of transactions with distant transfer dates
- **July 2025 Balance Verification**: Maintains correct closing balance of HK$554.77

### 🔄 Two Reconciliation Methods
1. **Monthly Statements** (Created dates): For consistent monthly balance tracking
2. **Payout Reconciliation** (Transfer dates): Matches Stripe's official payout reports exactly

### 📊 Manual Reconciliation Improvements
- Both Created and Available On dates preserved for reference
- Payout reconciliation matches Stripe reports exactly (e.g., July 2025: HK$2636.78)
- Clear separation between transaction occurrence vs fund availability timing

**⚠️ Statement Reprint Recommendation**: Reprint statements from November 2021 onwards to ensure accurate balance carry-forward.

## ✨ Features

- **Monthly Statement Consolidation**: Generate detailed monthly statements with running balances and carry-forward functionality
- **CSV Import**: Automated import from complete_csv folder with transaction categorization
- **Multi-Company Analytics**: Support for multiple Stripe accounts (CGGE, Krystal Institute, Krystal Technology)  
- **Succeeded/Refunded Filtering**: Only processes real cash movement transactions (excludes cancelled transactions)
- **Interactive Dashboard**: Real-time charts and analytics with modern responsive design
- **Export Capabilities**: CSV export, print-optimized statements, and monthly statement downloads
- **Balance Tracking**: Automatic calculation of opening/closing balances with month-to-month carry-forward

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/wongivan852/company-cost-quotation-system.git
   cd company-cost-quotation-system
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the dashboard**
   - Open http://localhost:8081 in your browser

## 📊 Application Structure

```
stripe-dashboard/
├── app/                    # Main application package
│   ├── __init__.py        # Flask app factory
│   ├── models/            # Database models
│   │   ├── stripe_account.py
│   │   └── transaction.py
│   ├── routes/            # Application routes
│   │   ├── main.py        # Main routes
│   │   └── analytics.py   # Analytics routes
│   ├── services/          # Business logic
│   │   ├── stripe_service.py
│   │   └── multi_stripe_service.py
│   ├── static/            # Static assets (CSS, JS)
│   └── templates/         # HTML templates
├── config/                # Configuration files
├── instance/              # Instance-specific files
├── requirements.txt       # Python dependencies
└── run.py                # Application entry point
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/app.db
DEBUG=False
```

### Database Setup

The application uses SQLite by default. The database will be created automatically on first run.

## 📈 Usage

### Dashboard Features

1. **Analytics Dashboard** (`/analytics/dashboard`)
   - Overview of all companies
   - Revenue and transaction charts
   - Account-specific breakdowns

2. **Statement Generator** (`/analytics/statement-generator`)
   - Custom date range selection
   - Company-specific filtering
   - Multiple output formats

3. **Summary View** (`/analytics/summary`)
   - Quick overview of key metrics
   - Status-based filtering

### CSV Data Import

The application supports importing transaction data from CSV files with the following format:

```csv
Company,Transaction ID,Date,Amount,Currency,Status,Customer Email,Description,Type,Fee
```

## 🌍 Currency Support

- **Primary Currency**: HKD (Hong Kong Dollar)
- **Secondary Currency**: CNY (Chinese Yuan)
- **Automatic Conversion**: CNY to HKD with configurable exchange rates
- **Currency Breakdown**: Detailed reporting by currency type

## 🔒 Security Features

- Environment-based configuration
- Secure session management
- Input validation and sanitization
- SQL injection prevention via SQLAlchemy

## 📱 Responsive Design

- Mobile-friendly interface
- Print-optimized statement layouts
- Progressive enhancement for better accessibility

## 🧪 Testing

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=app tests/
```

## 🚀 Deployment

### Production Deployment

#### Quick Deployment
```bash
# Clone and deploy
git clone <repository-url>
cd stripe-dashboard
./deploy.sh
```

#### Manual Deployment

1. **Set production environment variables**
   ```bash
   cp .env.production .env
   # Edit .env with your production values
   ```

2. **Initialize database**
   ```bash
   python init_db.py
   ```

3. **Start application**
   ```bash
   python run.py
   ```

#### Production WSGI Server
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8081 run:app
```

### Docker Deployment

```bash
# Build image
docker build -t stripe-dashboard .

# Run container
docker run -d -p 8081:8081 \
  -v $(pwd)/instance:/app/instance \
  stripe-dashboard
```

**Database Persistence:** The `instance/` directory contains the SQLite database and is mounted as a volume for data persistence.

## 📝 API Endpoints

### Core Endpoints
- `GET /` - Main dashboard
- `GET /analytics/dashboard` - Analytics overview
- `GET /analytics/statement-generator` - Statement generator form
- `POST /analytics/statement-generator/generate` - Generate statements
- `GET /analytics/api/account-amounts` - API data endpoint

### Monthly Statement & Reconciliation APIs
- `GET /analytics/api/monthly-statement` - Generate monthly statements (Created dates)
  - Parameters: `company`, `year`, `month`, `previous_balance` (optional)
  - Returns: Monthly statement with balance carry-forward
- `GET /analytics/api/payout-reconciliation` - Stripe payout reconciliation (Transfer dates)
  - Parameters: `company`, `year`, `month`  
  - Returns: Reconciliation matching Stripe's official payout reports
- `GET /analytics/monthly-statement` - Interactive monthly statement web interface
- `GET /analytics/payout-reconciliation` - Interactive payout reconciliation web interface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Email: support@example.com

## 🔄 Changelog

### v2.2.0 (August 2025) - Transaction Processing & Balance Fixes
- ✅ **Krystal Technology Transfer Date Fix** - Corrected 12 transactions from March 2023 onwards with wrong transfer dates
- ✅ **Refund Logic Correction** - Fixed refunds to appear as credits (reducing balance) instead of debits
- ✅ **Monthly Carry Forward Fix** - Opening balances now properly inherit from previous month's closing balance
- ✅ **Transaction Display Format** - Restored gross charge + processing fee format matching deployed PDF
- ✅ **Backup File Prevention** - Excluded backup CSV files from duplicate processing
- ✅ **Balance Accuracy Verification** - September 2022: $1.47, April 2023: -$28.77 (correct deficit)

### v2.1.0 (December 2025) - Balance Reconciliation & Date Analysis
- ✅ **Fixed balance carry-forward between months** - November 2021 → December 2021 continuity restored
- ✅ **Enhanced date field handling** - Created vs Available On date analysis for optimal reconciliation
- ✅ **Dual reconciliation methods** - Monthly statements (Created dates) + Payout reconciliation (Transfer dates)
- ✅ **Cross-month transfer logic improvements** - Proper handling of transactions with distant transfer dates
- ✅ **Manual reconciliation optimization** - Perfect alignment with Stripe's official payout reports
- ✅ **July 2025 balance verification** - Maintains correct closing balance of HK$554.77

### v2.0.0 (Production Integration Release)
- ✅ **CGGE July 2025 Data Correction** - Matches exact Stripe dashboard figures
- ✅ **Root Cause Analysis** for data discrepancies identified and resolved
- ✅ **Production CRM Integration** with automated reconciliation
- ✅ **Enhanced Financial Reporting** with corrected calculations
- ✅ **Data Validation** for CSV imports with error handling

### v1.1.0 (Previous Updates)
- ✅ Complete CSV processing with transfer date support
- ✅ Payout reconciliation matching Stripe reports exactly
- ✅ Enhanced transaction categorization (gross, fees, payouts)
- ✅ Interactive web interfaces for statement generation

### v1.0.0 (Initial Production Release)
- ✅ Multi-company Stripe analytics
- ✅ Currency conversion support (CNY/HKD)
- ✅ Advanced filtering and reporting
- ✅ Interactive dashboard with Chart.js
- ✅ CSV import functionality
- ✅ Print-optimized statements
- ✅ Mobile-responsive design

---

**Built with ❤️ using Flask, SQLAlchemy, and Chart.js**

### 📊 **Two-Tier Transaction Display**
- **Primary Tier (Green)**: Succeeded and Refunded transactions (real money movement)
- **Secondary Tier (Gray)**: Failed and other status transactions (informational only)

### 📈 **Analytics & Reporting**
- Interactive Chart.js visualizations
- Monthly bank statement generation
- Company-specific filtering and reporting
- Fee calculation and tracking
- Export capabilities (CSV, PDF-style HTML)

### 🔧 **Technical Features**
- Directory-based CSV processing (`/new_csv/{company}/`)
- Automatic company detection and categorization
- Responsive web interface
- SQLAlchemy database integration
- Real-time transaction processing

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Flask and dependencies (see `requirements.txt`)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stripe-dashboard
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   # Option 1: Use the startup script (recommended)
   ./start.sh
   
   # Option 2: Manual activation
   source venv/bin/activate
   python run.py
   ```

6. **Access the dashboard**
   Open http://localhost:8081 in your browser

## 📁 Project Structure

```
stripe-dashboard/
├── app/                          # Main Flask application
│   ├── models/                   # Database models
│   │   ├── stripe_account.py
│   │   └── transaction.py
│   ├── routes/                   # URL routes
│   │   ├── analytics.py         # Analytics and reporting
│   │   └── main.py              # Main routes
│   ├── services/                 # Business logic
│   │   ├── csv_transaction_service.py  # CSV processing
│   │   ├── multi_stripe_service.py     # Multi-account handling
│   │   └── stripe_service.py           # Stripe API integration
│   ├── static/                   # CSS, JS, assets
│   └── templates/               # HTML templates
├── config/                       # Configuration files
├── new_csv/                      # CSV data organized by company
│   ├── cgge/                    # CGGE transaction files
│   ├── krystal_institute/       # Krystal Institute files
│   └── krystal_technology/      # Krystal Technology files
├── requirements.txt             # Python dependencies
└── run.py                      # Application entry point
```

## 💡 Usage

### 📊 **Analytics Dashboard**
1. Navigate to `/analytics`
2. Select company from dropdown
3. Choose date range for analysis
4. Generate reports with two-tier transaction display

### 🏦 **Bank Statement Generation**
1. Select month and year
2. Choose company filter
3. Generate detailed statement with:
   - Primary transactions (money movement)
   - Secondary transactions (informational)
   - Interactive charts and summaries

### 📈 **Data Processing**
- CSV files are automatically discovered from company directories
- Transactions are categorized by status (succeeded/refunded vs failed/other)
- Company identification based on directory structure
- Real-time processing and caching

## 🔧 Configuration

### Environment Variables
Create a `.env` file with:
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
FLASK_ENV=development
STRIPE_API_KEY=your-stripe-key (optional)
```

### CSV Data Structure
Place CSV files in the following structure:
```
new_csv/
├── cgge/
│   ├── Balance_Summary_HKD_2024-01-01_to_2024-01-31_Asia-Hong_Kong.csv
│   └── Itemised_balance_change_from_activity_HKD_2024-01-01_to_2024-01-31_Asia-Hong_Kong.csv
├── krystal_institute/
│   └── [similar CSV files]
└── krystal_technology/
    └── [similar CSV files]
```

## 🎯 Key Features

### **Two-Tier Transaction System**
- **Primary Tier**: Real money movement (succeeded, refunded)
  - Green color scheme
  - Included in financial totals
  - Priority display in reports

- **Secondary Tier**: Informational transactions (failed, pending, etc.)
  - Gray color scheme  
  - Tracking purposes only
  - Separate section in reports

### **Multi-Company Architecture**
- Automatic company detection from directory structure
- Independent processing per company
- Consolidated or filtered reporting
- Company-specific analytics

### **Advanced Analytics**
- Interactive Chart.js visualizations
- Time-series analysis
- Fee breakdown and tracking
- Export capabilities
- Mobile-responsive interface

## 🛠️ Development

### Running in Development Mode
```bash
export FLASK_ENV=development
python run.py
```

### Adding New Companies
1. Create new directory under `new_csv/`
2. Add CSV files with transaction data
3. Company will be automatically detected

### Customizing Transaction Categories
Edit `csv_transaction_service.py` to modify transaction categorization logic.

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

For questions and support, please open an issue in the GitHub repository.
