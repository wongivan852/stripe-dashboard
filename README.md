# 🏦 Stripe Dashboard Analytics

A comprehensive Flask-based web application for analyzing Stripe transaction data across multiple companies with advanced reporting capabilities and currency handling.

**📍 Repository**: [wongivan852/stripe-dashboard](https://github.com/wongivan852/stripe-dashboard)

## ✨ Features

- **Multi-Company Analytics**: Support for multiple Stripe accounts (CGGE, Krystal Institute, Krystal Technology)
- **Advanced Reporting**: Generate detailed bank statements with customizable filters
- **Currency Support**: Proper handling of multiple currencies (HKD, CNY) with conversion
- **Interactive Dashboard**: Real-time charts and analytics using Chart.js
- **Export Capabilities**: CSV export and print-optimized statements
- **Period Filtering**: Custom date ranges, preset periods, and comprehensive status filters

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

1. **Set production environment variables**
   ```env
   FLASK_ENV=production
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   ```

2. **Use a production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8081 run:app
   ```

3. **Set up reverse proxy** (nginx/Apache)
4. **Configure SSL certificates**
5. **Set up database backups**

### Docker Deployment

```dockerfile
FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8081
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8081", "run:app"]
```

## 📝 API Endpoints

- `GET /` - Main dashboard
- `GET /analytics/dashboard` - Analytics overview
- `GET /analytics/statement-generator` - Statement generator form
- `POST /analytics/statement-generator/generate` - Generate statements
- `GET /analytics/api/account-amounts` - API data endpoint

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

### v1.0.0 (Production Release)
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
