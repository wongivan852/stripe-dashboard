# 🏦 Stripe Dashboard - Three Company Analytics

A comprehensive Flask-based analytics dashboard for processing Stripe payment data across three companies with advanced two-tier transaction display.

## ✨ Features

### 🏢 **Three Company Support**
- **CGGE** - Complete transaction processing and analytics
- **Krystal Institute** - Educational institution payment tracking  
- **Krystal Technology** - Technology services transaction management

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
   Open http://localhost:5001 in your browser

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
