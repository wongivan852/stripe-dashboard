#!/usr/bin/env python3
"""
Monthly Statement Generator - Debit/Credit Format
Matches the exact format of CGGE-MonthlyStatement_2025_07.pdf
Traditional accounting format with running balance
"""

from flask import Flask, request, jsonify, render_template_string, Response
from datetime import datetime, timedelta
import json
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False

# Storage for monthly statement data
STATEMENT_DATA_FILE = 'data/monthly_statement_data.json'

def load_statement_data():
    """Load saved statement data"""
    if os.path.exists(STATEMENT_DATA_FILE):
        try:
            with open(STATEMENT_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_statement_data(data):
    """Save statement data"""
    try:
        with open(STATEMENT_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

def get_previous_month_closing_balance(company, period):
    """Get the closing balance from the previous month"""
    try:
        year, month = period.split('-')
        year = int(year)
        month = int(month)
        
        # Calculate previous month
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
            
        prev_period = f"{prev_year}-{prev_month:02d}"
        prev_key = f"{company}_{prev_period}"
        
        saved_data = load_statement_data()
        if prev_key in saved_data:
            return saved_data[prev_key].get('closing_balance', 0)
        
        return 0
    except:
        return 0

@app.route('/')
def home():
    """Main dashboard"""
    saved_data = load_statement_data()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monthly Statement Generator</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: #f8fafc; 
                margin: 0; 
                padding: 20px; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
            }
            .header { 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); 
                color: white; 
                padding: 40px; 
                text-align: center; 
                border-radius: 12px; 
                margin-bottom: 30px; 
            }
            .badge { 
                background: rgba(255,255,255,0.2); 
                padding: 8px 16px; 
                border-radius: 20px; 
                font-size: 0.9rem; 
                margin-top: 15px; 
                display: inline-block; 
            }
            .actions { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
                gap: 20px; 
                margin-bottom: 30px;
            }
            .action-card { 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
                transition: transform 0.2s; 
                cursor: pointer; 
                text-decoration: none; 
                color: inherit; 
            }
            .action-card:hover { 
                transform: translateY(-2px); 
            }
            .action-icon { 
                font-size: 2.5rem; 
                margin-bottom: 15px; 
            }
            .action-title { 
                font-size: 1.2rem; 
                font-weight: bold; 
                margin-bottom: 10px; 
                color: #1e293b; 
            }
            .action-desc { 
                color: #64748b; 
                line-height: 1.5; 
            }
            .saved-data { 
                background: #ecfdf5; 
                border-left: 4px solid #10b981; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 30px; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📄 Monthly Statement Generator</h1>
                <div class="badge">Traditional Debit/Credit Format</div>
                <p>Generate consolidated monthly statements with running balance</p>
                <p style="font-size: 0.9rem; opacity: 0.9;">Matches CGGE-MonthlyStatement format exactly</p>
            </div>
    '''
    
    # Show saved data if available
    if saved_data:
        html += f'''
            <div class="saved-data">
                <h3>💾 Saved Monthly Statements: {len(saved_data)}</h3>
                <p>Ready to generate PDFs from your saved statement data.</p>
            </div>
        '''
    
    html += '''
            <div class="actions">
                <a href="/create-statement" class="action-card">
                    <div class="action-icon">✏️</div>
                    <div class="action-title">Create Monthly Statement</div>
                    <div class="action-desc">Enter transactions manually in debit/credit format with running balance calculation</div>
                </a>
                
                <a href="/saved-statements" class="action-card">
                    <div class="action-icon">📁</div>
                    <div class="action-title">Saved Statements</div>
                    <div class="action-desc">View, edit, and generate PDFs from previously created monthly statements</div>
                </a>
                
                <a href="/api/status" class="action-card">
                    <div class="action-icon">🔧</div>
                    <div class="action-title">System Status</div>
                    <div class="action-desc">Check system health and view statement data summary</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/create-statement')
def create_statement_form():
    """Create monthly statement form"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Monthly Statement</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .header { 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                padding: 25px; 
                border-radius: 10px; 
                margin-bottom: 30px; 
                text-align: center; 
            }
            .section { 
                margin-bottom: 30px; 
                padding: 25px; 
                border: 2px solid #e5e7eb; 
                border-radius: 10px; 
            }
            .section-title { 
                font-size: 1.3rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 20px; 
                padding-bottom: 10px; 
                border-bottom: 2px solid #6366f1; 
            }
            .form-row { 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 20px; 
                margin-bottom: 20px; 
            }
            .form-group { 
                margin-bottom: 20px; 
            }
            label { 
                display: block; 
                margin-bottom: 8px; 
                font-weight: bold; 
                color: #374151; 
            }
            input, select { 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #e5e7eb; 
                border-radius: 8px; 
                font-size: 16px; 
                transition: border-color 0.2s; 
            }
            input:focus, select:focus { 
                outline: none; 
                border-color: #6366f1; 
            }
            .btn { 
                background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: 600; 
                transition: all 0.2s; 
            }
            .btn:hover { 
                transform: translateY(-1px); 
                box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
            }
            .btn-secondary {
                background: #6b7280;
                margin-left: 15px;
            }
            .btn-secondary:hover {
                background: #4b5563;
            }
            .info-box {
                background: #eff6ff;
                border-left: 4px solid #3b82f6;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 0.95rem;
            }
            .transactions-section {
                margin-top: 30px;
            }
            .transaction-item {
                background: #f8fafc;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            .add-transaction {
                background: #10b981;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                margin-bottom: 20px;
                font-size: 16px;
            }
            .transaction-header {
                font-weight: bold;
                margin-bottom: 15px;
                color: #1e293b;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📄 Create Monthly Statement</h2>
                <p>Traditional debit/credit format with running balance</p>
            </div>
            
            <div class="info-box">
                <strong>💡 Format:</strong> This creates statements exactly like CGGE-MonthlyStatement_2025_07.pdf with 
                debit/credit columns, running balance, and proper accounting format.
            </div>
            
            <form id="statementForm" action="/save-statement" method="POST">
                <!-- Basic Information -->
                <div class="section">
                    <div class="section-title">📋 Statement Information</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="company">Company:</label>
                            <select name="company" id="company" required>
                                <option value="cgge">CGGE</option>
                                <option value="ki">Krystal Institute</option>
                                <option value="kt">Krystal Technology</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="period">Month & Year:</label>
                            <input type="month" name="period" id="period" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="opening_balance">Opening Balance (HKD):</label>
                            <input type="number" name="opening_balance" id="opening_balance" step="0.01" required>
                            <button type="button" onclick="loadPreviousBalance()" style="margin-top: 10px; padding: 8px 16px; background: #6366f1; color: white; border: none; border-radius: 6px; cursor: pointer;">Load from Previous Month</button>
                        </div>
                        <div class="form-group">
                            <label for="closing_balance">Closing Balance (HKD):</label>
                            <input type="number" name="closing_balance" id="closing_balance" step="0.01" readonly style="background: #f3f4f6;">
                        </div>
                    </div>
                </div>
                
                <!-- Transactions Section -->
                <div class="section transactions-section">
                    <div class="section-title">📝 Individual Transactions</div>
                    <div id="transactions-container"></div>
                    <button type="button" class="add-transaction" onclick="addTransaction()">+ Add Transaction</button>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn">💾 Save Monthly Statement</button>
                    <a href="/" class="btn btn-secondary">← Back to Dashboard</a>
                </div>
            </form>
        </div>
        
        <script>
            let transactionCount = 0;
            
            function addTransaction() {
                transactionCount++;
                const container = document.getElementById('transactions-container');
                const transactionHtml = `
                    <div class="transaction-item" id="transaction-${transactionCount}">
                        <div class="transaction-header">Transaction ${transactionCount}</div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Date:</label>
                                <input type="date" name="transactions[${transactionCount}][date]" required>
                            </div>
                            <div class="form-group">
                                <label>Nature:</label>
                                <select name="transactions[${transactionCount}][nature]" required>
                                    <option value="">-- Select --</option>
                                    <option value="Gross Payment">Gross Payment</option>
                                    <option value="Gross Charge">Gross Charge</option>
                                    <option value="Processing Fee">Processing Fee</option>
                                    <option value="Payout">Payout</option>
                                    <option value="Refund">Refund</option>
                                    <option value="Adjustment">Adjustment</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Party:</label>
                                <input type="text" name="transactions[${transactionCount}][party]" placeholder="e.g., User 1234, Stripe, customer@email.com" required>
                            </div>
                            <div class="form-group">
                                <label>Amount Type:</label>
                                <select name="transactions[${transactionCount}][amount_type]" onchange="toggleAmountFields(${transactionCount})" required>
                                    <option value="">-- Select --</option>
                                    <option value="debit">Debit (Increases Balance)</option>
                                    <option value="credit">Credit (Decreases Balance)</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Amount (HKD):</label>
                                <input type="number" name="transactions[${transactionCount}][amount]" step="0.01" min="0" required onchange="calculateBalance()">
                            </div>
                            <div class="form-group">
                                <label>Description:</label>
                                <input type="text" name="transactions[${transactionCount}][description]" placeholder="Transaction description">
                            </div>
                        </div>
                        <button type="button" onclick="removeTransaction(${transactionCount})" 
                                style="background: #dc2626; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            Remove Transaction
                        </button>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', transactionHtml);
            }
            
            function removeTransaction(id) {
                document.getElementById(`transaction-${id}`).remove();
                calculateBalance();
            }
            
            function toggleAmountFields(id) {
                // This can be used for additional logic if needed
            }
            
            function calculateBalance() {
                const openingBalance = parseFloat(document.getElementById('opening_balance').value) || 0;
                let runningBalance = openingBalance;
                
                // Get all transaction amounts and types
                const container = document.getElementById('transactions-container');
                const transactions = container.querySelectorAll('.transaction-item');
                
                transactions.forEach(transaction => {
                    const amountInput = transaction.querySelector('input[name*="[amount]"]');
                    const typeSelect = transaction.querySelector('select[name*="[amount_type]"]');
                    
                    if (amountInput && typeSelect) {
                        const amount = parseFloat(amountInput.value) || 0;
                        const type = typeSelect.value;
                        
                        if (type === 'debit') {
                            runningBalance += amount;
                        } else if (type === 'credit') {
                            runningBalance -= amount;
                        }
                    }
                });
                
                document.getElementById('closing_balance').value = runningBalance.toFixed(2);
            }
            
            function loadPreviousBalance() {
                const company = document.getElementById('company').value;
                const period = document.getElementById('period').value;
                
                if (!company || !period) {
                    alert('Please select company and period first');
                    return;
                }
                
                fetch(`/api/previous-balance/${company}/${period}`)
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('opening_balance').value = data.previous_balance.toFixed(2);
                        if (data.previous_balance > 0) {
                            alert(`Loaded ${data.previous_period} closing balance: HK$${data.previous_balance.toFixed(2)}`);
                        } else {
                            alert('No previous month data found. Opening balance set to 0.');
                        }
                        calculateBalance();
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error loading previous balance');
                    });
            }
            
            // Add event listener to opening balance
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('opening_balance').addEventListener('input', calculateBalance);
            });
        </script>
    </body>
    </html>
    '''
    
    return html

@app.route('/save-statement', methods=['POST'])
def save_statement():
    """Save monthly statement data"""
    try:
        # Extract form data
        company = request.form.get('company')
        period = request.form.get('period')
        opening_balance = float(request.form.get('opening_balance', 0))
        closing_balance = float(request.form.get('closing_balance', 0))
        
        # Parse transactions
        transactions = []
        form_data = request.form.to_dict()
        
        # Extract individual transactions
        transaction_ids = set()
        for key in form_data:
            if key.startswith('transactions[') and key.endswith('][date]'):
                tx_id = key.split('[')[1].split(']')[0]
                transaction_ids.add(tx_id)
        
        for tx_id in sorted(transaction_ids, key=int):
            date = form_data.get(f'transactions[{tx_id}][date]')
            nature = form_data.get(f'transactions[{tx_id}][nature]')
            party = form_data.get(f'transactions[{tx_id}][party]')
            amount_type = form_data.get(f'transactions[{tx_id}][amount_type]')
            amount = form_data.get(f'transactions[{tx_id}][amount]')
            description = form_data.get(f'transactions[{tx_id}][description]')
            
            if date and nature and party and amount_type and amount:
                transactions.append({
                    'date': date,
                    'nature': nature,
                    'party': party,
                    'debit': float(amount) if amount_type == 'debit' else 0,
                    'credit': float(amount) if amount_type == 'credit' else 0,
                    'description': description or nature,
                    'acknowledged': 'No'
                })
        
        # Sort transactions by date
        transactions.sort(key=lambda x: x['date'])
        
        # Calculate running balance for each transaction
        running_balance = opening_balance
        for tx in transactions:
            running_balance += tx['debit'] - tx['credit']
            tx['balance'] = running_balance
        
        # Build statement data
        statement_data = {
            'company': company,
            'period': period,
            'created_at': datetime.now().isoformat(),
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_transactions': len(transactions),
            'total_debit': sum(tx['debit'] for tx in transactions),
            'total_credit': sum(tx['credit'] for tx in transactions),
            'transactions': transactions
        }
        
        # Save to file
        saved_data = load_statement_data()
        statement_key = f"{company}_{period}"
        saved_data[statement_key] = statement_data
        
        if save_statement_data(saved_data):
            # Redirect to success page with option to generate PDF
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Statement Saved Successfully</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f0fdf4; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .success-icon {{ font-size: 4rem; color: #10b981; margin-bottom: 20px; }}
                    h1 {{ color: #1e293b; }}
                    .summary {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
                    .btn {{ display: inline-block; background: #6366f1; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 10px; }}
                    .btn:hover {{ background: #5338d8; }}
                    .btn-secondary {{ background: #6b7280; }}
                    .btn-secondary:hover {{ background: #4b5563; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1>Monthly Statement Saved Successfully!</h1>
                    <div class="summary">
                        <strong>Company:</strong> {statement_data['company'].upper()}<br>
                        <strong>Period:</strong> {statement_data['period']}<br>
                        <strong>Opening Balance:</strong> HK${statement_data['opening_balance']:,.2f}<br>
                        <strong>Closing Balance:</strong> HK${statement_data['closing_balance']:,.2f}<br>
                        <strong>Total Transactions:</strong> {len(transactions)}<br>
                        <strong>Total Debit:</strong> HK${statement_data['total_debit']:,.2f}<br>
                        <strong>Total Credit:</strong> HK${statement_data['total_credit']:,.2f}
                    </div>
                    <a href="/generate-statement-pdf/{statement_key}" class="btn">📄 Generate PDF Statement</a>
                    <a href="/saved-statements" class="btn btn-secondary">📁 View All Statements</a>
                    <a href="/" class="btn btn-secondary">🏠 Dashboard</a>
                </div>
            </body>
            </html>
            '''
        else:
            return "Error saving statement", 500
            
    except Exception as e:
        logger.error(f"Error saving statement: {e}")
        return f"Error: {e}", 500

@app.route('/generate-statement-pdf/<statement_key>')
def generate_statement_pdf(statement_key):
    """Generate PDF-ready HTML for monthly statement"""
    saved_data = load_statement_data()
    
    if statement_key not in saved_data:
        return "Statement not found", 404
    
    statement_data = saved_data[statement_key]
    
    # Company name mapping
    company_names = {'cgge': 'CGGE', 'ki': 'Krystal Institute', 'kt': 'Krystal Technology'}
    company_name = company_names.get(statement_data['company'], 'Unknown Company')
    
    # Period formatting
    period = statement_data['period']
    try:
        date_obj = datetime.strptime(period, '%Y-%m')
        period_formatted = date_obj.strftime('%B %Y')
    except:
        period_formatted = period
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monthly Statement - {company_name} {period_formatted}</title>
        <meta charset="UTF-8">
        <style>
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: white;
                color: #1e293b;
                line-height: 1.4;
            }}
            .header {{ 
                text-align: center; 
                margin-bottom: 30px;
                border-bottom: 3px solid #6366f1;
                padding-bottom: 20px;
            }}
            .company-name {{ 
                font-size: 2.5rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 10px;
            }}
            .statement-title {{ 
                font-size: 1.8rem; 
                color: #64748b; 
                margin-bottom: 20px;
            }}
            .summary-box {{
                background: #f8fafc;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 30px;
            }}
            .summary-title {{
                font-size: 1.3rem;
                font-weight: bold;
                color: #1e293b;
                margin-bottom: 15px;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
            }}
            .summary-item {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
            }}
            .summary-label {{
                color: #64748b;
                font-weight: 500;
            }}
            .summary-value {{
                font-weight: bold;
                color: #1e293b;
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 20px;
                font-size: 0.9rem;
            }}
            th {{ 
                background: #f8fafc; 
                padding: 12px 8px; 
                text-align: left; 
                font-weight: bold; 
                color: #374151; 
                border: 1px solid #d1d5db;
            }}
            td {{ 
                padding: 8px; 
                border: 1px solid #e5e7eb;
                vertical-align: top;
            }}
            .amount {{ 
                text-align: right; 
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }}
            .debit {{ 
                color: #dc2626; 
            }}
            .credit {{ 
                color: #059669; 
            }}
            .balance {{ 
                font-weight: bold;
                color: #1e293b;
            }}
            .opening-row, .closing-row {{ 
                background: #fef3c7; 
                font-weight: bold;
            }}
            .subtotal-row {{ 
                background: #f3f4f6; 
                font-weight: bold;
                border-top: 2px solid #9ca3af;
            }}
            .print-btn {{
                background: #6366f1;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
            }}
            .print-btn:hover {{
                background: #5338d8;
            }}
        </style>
    </head>
    <body>
        <div class="no-print" style="text-align: center; margin-bottom: 20px;">
            <button class="print-btn" onclick="window.print()">🖨️ Print to PDF</button>
            <button class="print-btn" onclick="window.close()">← Close</button>
        </div>
        
        <div class="header">
            <div class="company-name">{company_name}</div>
            <div class="statement-title">Monthly Statement - {period_formatted}</div>
        </div>
        
        <div class="summary-box">
            <div class="summary-title">Statement Summary for {period_formatted}</div>
            <div class="summary-grid">
                <div class="summary-item">
                    <span class="summary-label">Company:</span>
                    <span class="summary-value">{statement_data['company']}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Opening Balance:</span>
                    <span class="summary-value">HK${statement_data['opening_balance']:,.2f}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Closing Balance:</span>
                    <span class="summary-value">HK${statement_data['closing_balance']:,.2f}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Total Transactions:</span>
                    <span class="summary-value">{statement_data['total_transactions']}</span>
                </div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Nature</th>
                    <th>Party</th>
                    <th class="amount">Debit</th>
                    <th class="amount">Credit</th>
                    <th class="amount">Balance</th>
                    <th>Acknowledged</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody>
                <tr class="opening-row">
                    <td>{period}-01</td>
                    <td>Opening Balance</td>
                    <td>Brought Forward</td>
                    <td class="amount"></td>
                    <td class="amount"></td>
                    <td class="amount balance">HK${statement_data['opening_balance']:,.2f}</td>
                    <td>Yes</td>
                    <td>Opening balance for {period_formatted}</td>
                </tr>
    '''
    
    # Add transaction rows
    for tx in statement_data['transactions']:
        debit_str = f"HK${tx['debit']:,.2f}" if tx['debit'] > 0 else ""
        credit_str = f"HK${tx['credit']:,.2f}" if tx['credit'] > 0 else ""
        
        html += f'''
                <tr>
                    <td>{tx['date']}</td>
                    <td>{tx['nature']}</td>
                    <td>{tx['party']}</td>
                    <td class="amount debit">{debit_str}</td>
                    <td class="amount credit">{credit_str}</td>
                    <td class="amount balance">HK${tx['balance']:,.2f}</td>
                    <td>{tx['acknowledged']}</td>
                    <td>{tx['description']}</td>
                </tr>
        '''
    
    # Add subtotal row
    html += f'''
                <tr class="subtotal-row">
                    <td colspan="3">SUBTOTAL</td>
                    <td class="amount debit">HK${statement_data['total_debit']:,.2f}</td>
                    <td class="amount credit">HK${statement_data['total_credit']:,.2f}</td>
                    <td class="amount"></td>
                    <td></td>
                    <td></td>
                </tr>
    '''
    
    # Add closing balance row
    last_day = '31'  # Simplified for now
    html += f'''
                <tr class="closing-row">
                    <td>{period}-{last_day}</td>
                    <td>Closing Balance</td>
                    <td>Carry Forward</td>
                    <td class="amount"></td>
                    <td class="amount"></td>
                    <td class="amount balance">HK${statement_data['closing_balance']:,.2f}</td>
                    <td>Yes</td>
                    <td>Closing balance for {period_formatted}</td>
                </tr>
            </tbody>
        </table>
    '''
    
    # Add customer transaction summary section
    customer_transactions = [tx for tx in statement_data['transactions'] 
                           if tx['nature'] in ['Gross Payment', 'Gross Charge'] and tx['debit'] > 0]
    
    if customer_transactions:
        html += f'''
        <div style="margin-top: 40px; page-break-inside: avoid;">
            <div class="summary-box">
                <div class="summary-title">Customer Transaction Summary for {period_formatted}</div>
                <p style="color: #64748b; margin-bottom: 20px;">Total Customer Transactions: {len(customer_transactions)}</p>
            </div>
            
            <table style="margin-bottom: 40px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Customer Name</th>
                        <th>Email Address</th>
                        <th class="amount">Amount (HKD)</th>
                        <th>Transaction Type</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        total_customer_amount = 0
        for i, tx in enumerate(customer_transactions, 1):
            # Extract email from description if it contains @
            email = tx['description'] if '@' in tx['description'] else 'N/A'
            customer_name = tx['party'] if tx['party'] not in ['Stripe', 'unknown name'] else 'N/A'
            amount = tx['debit']
            total_customer_amount += amount
            
            row_class = 'style="background: #f8fafc;"' if i % 2 == 0 else ''
            
            html += f'''
                    <tr {row_class}>
                        <td>{tx['date']}</td>
                        <td>{customer_name}</td>
                        <td style="font-family: 'Courier New', monospace; font-size: 0.9em;">{email}</td>
                        <td class="amount" style="font-weight: bold; color: #059669;">HK${amount:,.2f}</td>
                        <td>{tx['nature']}</td>
                    </tr>
            '''
        
        # Add total row
        html += f'''
                    <tr style="background: #e5e7eb; font-weight: bold; border-top: 2px solid #9ca3af;">
                        <td colspan="3" style="text-align: right; font-weight: bold;">Total Customer Payments:</td>
                        <td class="amount" style="font-weight: bold; color: #059669; font-size: 1.1em;">HK${total_customer_amount:,.2f}</td>
                        <td></td>
                    </tr>
                </tbody>
            </table>
        </div>
        '''
    
    html += '''
        <div class="no-print" style="text-align: center; margin-top: 40px;">
            <button class="print-btn" onclick="window.print()">🖨️ Print to PDF</button>
            <a href="/saved-statements" class="print-btn" style="text-decoration: none;">← Back to Statements</a>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/saved-statements')
def saved_statements():
    """View all saved statements"""
    saved_data = load_statement_data()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Saved Monthly Statements</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f8fafc; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; padding: 30px; text-align: center; border-radius: 12px; margin-bottom: 30px; }
            .statements-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
            .statement-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .statement-title { font-size: 1.2rem; font-weight: bold; color: #1e293b; margin-bottom: 15px; }
            .statement-details { background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
            .detail-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
            .detail-label { color: #64748b; }
            .detail-value { font-weight: 600; color: #1e293b; }
            .btn { display: inline-block; background: #6366f1; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; margin: 5px; font-size: 0.9rem; }
            .btn:hover { background: #5338d8; }
            .btn-success { background: #10b981; }
            .btn-success:hover { background: #059669; }
            .btn-danger { background: #dc2626; }
            .btn-danger:hover { background: #b91c1c; }
            .btn-secondary { background: #6b7280; }
            .btn-secondary:hover { background: #4b5563; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📁 Saved Monthly Statements</h1>
                <p>Manage and generate PDFs from your monthly statements</p>
            </div>
    '''
    
    if not saved_data:
        html += '''
            <div style="text-align: center; padding: 60px; background: white; border-radius: 12px;">
                <h2>No saved statements yet</h2>
                <p>Create your first monthly statement to get started.</p>
                <a href="/create-statement" class="btn btn-success">Create New Statement</a>
            </div>
        '''
    else:
        html += '<div class="statements-grid">'
        
        for statement_key, statement_data in saved_data.items():
            company_name = {'cgge': 'CGGE', 'ki': 'Krystal Institute', 'kt': 'Krystal Technology'}.get(statement_data.get('company', ''), 'Unknown')
            
            html += f'''
            <div class="statement-card">
                <div class="statement-title">{company_name} - {statement_data.get('period', 'Unknown Period')}</div>
                <div class="statement-details">
                    <div class="detail-row">
                        <span class="detail-label">Opening Balance:</span>
                        <span class="detail-value">HK${statement_data.get('opening_balance', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Closing Balance:</span>
                        <span class="detail-value">HK${statement_data.get('closing_balance', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Transactions:</span>
                        <span class="detail-value">{statement_data.get('total_transactions', 0)}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Total Debit:</span>
                        <span class="detail-value">HK${statement_data.get('total_debit', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Total Credit:</span>
                        <span class="detail-value">HK${statement_data.get('total_credit', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">{statement_data.get('created_at', '')[:10]}</span>
                    </div>
                </div>
                <div>
                    <a href="/generate-statement-pdf/{statement_key}" class="btn btn-success">📄 Generate PDF</a>
                    <a href="/edit-statement/{statement_key}" class="btn">✏️ Edit</a>
                    <a href="/delete-statement/{statement_key}" class="btn btn-danger" onclick="return confirm('Are you sure?')">🗑️ Delete</a>
                </div>
            </div>
            '''
        
        html += '</div>'
    
    html += '''
            <div style="text-align: center; margin-top: 30px;">
                <a href="/create-statement" class="btn btn-success">➕ Create New Statement</a>
                <a href="/" class="btn btn-secondary">🏠 Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/edit-statement/<statement_key>')
def edit_statement_form(statement_key):
    """Edit an existing monthly statement"""
    saved_data = load_statement_data()
    
    if statement_key not in saved_data:
        return "Statement not found", 404
        
    statement_data = saved_data[statement_key]
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Edit Monthly Statement</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }}
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .header {{ 
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white; 
                padding: 25px; 
                border-radius: 10px; 
                margin-bottom: 30px; 
                text-align: center; 
            }}
            .section {{ 
                margin-bottom: 30px; 
                padding: 25px; 
                border: 2px solid #e5e7eb; 
                border-radius: 10px; 
            }}
            .section-title {{ 
                font-size: 1.3rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 20px; 
                padding-bottom: 10px; 
                border-bottom: 2px solid #f59e0b; 
            }}
            .form-row {{ 
                display: grid; 
                grid-template-columns: 1fr 1fr; 
                gap: 20px; 
                margin-bottom: 20px; 
            }}
            .form-group {{ 
                margin-bottom: 20px; 
            }}
            label {{ 
                display: block; 
                margin-bottom: 8px; 
                font-weight: bold; 
                color: #374151; 
            }}
            input, select {{ 
                width: 100%; 
                padding: 12px; 
                border: 2px solid #e5e7eb; 
                border-radius: 8px; 
                font-size: 16px; 
                transition: border-color 0.2s; 
            }}
            input:focus, select:focus {{ 
                outline: none; 
                border-color: #f59e0b; 
            }}
            .btn {{ 
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 8px; 
                cursor: pointer; 
                font-size: 16px; 
                font-weight: 600; 
                transition: all 0.2s; 
            }}
            .btn:hover {{ 
                transform: translateY(-1px); 
                box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
            }}
            .btn-secondary {{
                background: #6b7280;
                margin-left: 15px;
            }}
            .btn-secondary:hover {{
                background: #4b5563;
            }}
            .info-box {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
                font-size: 0.95rem;
            }}
            .transactions-section {{
                margin-top: 30px;
            }}
            .transaction-item {{
                background: #f8fafc;
                padding: 20px;
                margin-bottom: 15px;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }}
            .add-transaction {{
                background: #10b981;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                margin-top: 20px;
                font-size: 16px;
            }}
            .transaction-header {{
                font-weight: bold;
                margin-bottom: 15px;
                color: #1e293b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>✏️ Edit Monthly Statement</h2>
                <p>Editing: {statement_data.get('company', '').upper()} - {statement_data.get('period', '')}</p>
            </div>
            
            <div class="info-box">
                <strong>📝 Edit Mode:</strong> Modify your statement data. All changes will be saved to preserve your existing data.
            </div>
            
            <form id="statementForm" action="/update-statement/{statement_key}" method="POST">
                <!-- Basic Information -->
                <div class="section">
                    <div class="section-title">📋 Statement Information</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label for="company">Company:</label>
                            <select name="company" id="company" required>
                                <option value="cgge" {'selected' if statement_data.get('company') == 'cgge' else ''}>CGGE</option>
                                <option value="ki" {'selected' if statement_data.get('company') == 'ki' else ''}>Krystal Institute</option>
                                <option value="kt" {'selected' if statement_data.get('company') == 'kt' else ''}>Krystal Technology</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label for="period">Month & Year:</label>
                            <input type="month" name="period" id="period" value="{statement_data.get('period', '')}" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="opening_balance">Opening Balance (HKD):</label>
                            <input type="number" name="opening_balance" id="opening_balance" step="0.01" value="{statement_data.get('opening_balance', 0)}" required>
                            <button type="button" onclick="loadPreviousBalance()" style="margin-top: 10px; padding: 8px 16px; background: #f59e0b; color: white; border: none; border-radius: 6px; cursor: pointer;">Load from Previous Month</button>
                        </div>
                        <div class="form-group">
                            <label for="closing_balance">Closing Balance (HKD):</label>
                            <input type="number" name="closing_balance" id="closing_balance" step="0.01" value="{statement_data.get('closing_balance', 0)}" readonly style="background: #f3f4f6;">
                        </div>
                    </div>
                </div>
                
                <!-- Transactions Section -->
                <div class="section transactions-section">
                    <div class="section-title">📝 Individual Transactions</div>
                    <div id="transactions-container"></div>
                    <button type="button" class="add-transaction" onclick="addTransaction()">+ Add Transaction</button>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn">💾 Update Monthly Statement</button>
                    <a href="/saved-statements" class="btn btn-secondary">← Back to Statements</a>
                </div>
            </form>
        </div>
        
        <script>
            let transactionCount = 0;
            const existingTransactions = {json.dumps(statement_data.get('transactions', []))};
            
            function addTransaction(transactionData = null) {{
                transactionCount++;
                const container = document.getElementById('transactions-container');
                
                // Use existing data or defaults
                const data = transactionData || {{}};
                const date = data.date || '';
                const nature = data.nature || '';
                const party = data.party || '';
                const amountType = (data.debit > 0) ? 'debit' : ((data.credit > 0) ? 'credit' : '');
                const amount = data.debit > 0 ? data.debit : (data.credit > 0 ? data.credit : 0);
                const description = data.description || '';
                
                const transactionHtml = `
                    <div class="transaction-item" id="transaction-${{transactionCount}}">
                        <div class="transaction-header">Transaction ${{transactionCount}}</div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Date:</label>
                                <input type="date" name="transactions[${{transactionCount}}][date]" value="${{date}}" required>
                            </div>
                            <div class="form-group">
                                <label>Nature:</label>
                                <select name="transactions[${{transactionCount}}][nature]" required>
                                    <option value="">-- Select --</option>
                                    <option value="Gross Payment" ${{nature === 'Gross Payment' ? 'selected' : ''}}>Gross Payment</option>
                                    <option value="Gross Charge" ${{nature === 'Gross Charge' ? 'selected' : ''}}>Gross Charge</option>
                                    <option value="Processing Fee" ${{nature === 'Processing Fee' ? 'selected' : ''}}>Processing Fee</option>
                                    <option value="Payout" ${{nature === 'Payout' ? 'selected' : ''}}>Payout</option>
                                    <option value="Refund" ${{nature === 'Refund' ? 'selected' : ''}}>Refund</option>
                                    <option value="Adjustment" ${{nature === 'Adjustment' ? 'selected' : ''}}>Adjustment</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Party:</label>
                                <input type="text" name="transactions[${{transactionCount}}][party]" placeholder="e.g., User 1234, Stripe, customer@email.com" value="${{party}}" required>
                            </div>
                            <div class="form-group">
                                <label>Amount Type:</label>
                                <select name="transactions[${{transactionCount}}][amount_type]" onchange="toggleAmountFields(${{transactionCount}})" required>
                                    <option value="">-- Select --</option>
                                    <option value="debit" ${{amountType === 'debit' ? 'selected' : ''}}>Debit (Increases Balance)</option>
                                    <option value="credit" ${{amountType === 'credit' ? 'selected' : ''}}>Credit (Decreases Balance)</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Amount (HKD):</label>
                                <input type="number" name="transactions[${{transactionCount}}][amount]" step="0.01" min="0" value="${{amount}}" required onchange="calculateBalance()">
                            </div>
                            <div class="form-group">
                                <label>Description:</label>
                                <input type="text" name="transactions[${{transactionCount}}][description]" placeholder="Transaction description" value="${{description}}">
                            </div>
                        </div>
                        <button type="button" onclick="removeTransaction(${{transactionCount}})" 
                                style="background: #dc2626; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">
                            Remove Transaction
                        </button>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', transactionHtml);
            }}
            
            function removeTransaction(id) {{
                document.getElementById(`transaction-${{id}}`).remove();
                calculateBalance();
            }}
            
            function toggleAmountFields(id) {{
                // This can be used for additional logic if needed
            }}
            
            function calculateBalance() {{
                const openingBalance = parseFloat(document.getElementById('opening_balance').value) || 0;
                let runningBalance = openingBalance;
                
                // Get all transaction amounts and types
                const container = document.getElementById('transactions-container');
                const transactions = container.querySelectorAll('.transaction-item');
                
                transactions.forEach(transaction => {{
                    const amountInput = transaction.querySelector('input[name*="[amount]"]');
                    const typeSelect = transaction.querySelector('select[name*="[amount_type]"]');
                    
                    if (amountInput && typeSelect) {{
                        const amount = parseFloat(amountInput.value) || 0;
                        const type = typeSelect.value;
                        
                        if (type === 'debit') {{
                            runningBalance += amount;
                        }} else if (type === 'credit') {{
                            runningBalance -= amount;
                        }}
                    }}
                }});
                
                document.getElementById('closing_balance').value = runningBalance.toFixed(2);
            }}
            
            function loadPreviousBalance() {{
                const company = document.getElementById('company').value;
                const period = document.getElementById('period').value;
                
                if (!company || !period) {{
                    alert('Please select company and period first');
                    return;
                }}
                
                fetch(`/api/previous-balance/${{company}}/${{period}}`)
                    .then(response => response.json())
                    .then(data => {{
                        document.getElementById('opening_balance').value = data.previous_balance.toFixed(2);
                        if (data.previous_balance > 0) {{
                            alert(`Loaded ${{data.previous_period}} closing balance: HK$${{data.previous_balance.toFixed(2)}}`);
                        }} else {{
                            alert('No previous month data found. Opening balance set to 0.');
                        }}
                        calculateBalance();
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                        alert('Error loading previous balance');
                    }});
            }}
            
            // Load existing transactions on page load
            document.addEventListener('DOMContentLoaded', function() {{
                // Add existing transactions
                existingTransactions.forEach(transaction => {{
                    addTransaction(transaction);
                }});
                
                // Add event listener to opening balance
                document.getElementById('opening_balance').addEventListener('input', calculateBalance);
                
                // Recalculate balance after loading existing transactions
                setTimeout(calculateBalance, 100);
            }});
        </script>
    </body>
    </html>
    '''
    
    return html

@app.route('/update-statement/<statement_key>', methods=['POST'])
def update_statement(statement_key):
    """Update an existing monthly statement"""
    try:
        saved_data = load_statement_data()
        
        if statement_key not in saved_data:
            return "Statement not found", 404
        
        # Extract form data (same logic as save_statement)
        company = request.form.get('company')
        period = request.form.get('period')
        opening_balance = float(request.form.get('opening_balance', 0))
        closing_balance = float(request.form.get('closing_balance', 0))
        
        # Parse transactions
        transactions = []
        form_data = request.form.to_dict()
        
        # Extract individual transactions
        transaction_ids = set()
        for key in form_data:
            if key.startswith('transactions[') and key.endswith('][date]'):
                tx_id = key.split('[')[1].split(']')[0]
                transaction_ids.add(tx_id)
        
        for tx_id in sorted(transaction_ids, key=int):
            date = form_data.get(f'transactions[{tx_id}][date]')
            nature = form_data.get(f'transactions[{tx_id}][nature]')
            party = form_data.get(f'transactions[{tx_id}][party]')
            amount_type = form_data.get(f'transactions[{tx_id}][amount_type]')
            amount = form_data.get(f'transactions[{tx_id}][amount]')
            description = form_data.get(f'transactions[{tx_id}][description]')
            
            if date and nature and party and amount_type and amount:
                transactions.append({
                    'date': date,
                    'nature': nature,
                    'party': party,
                    'debit': float(amount) if amount_type == 'debit' else 0,
                    'credit': float(amount) if amount_type == 'credit' else 0,
                    'description': description or nature,
                    'acknowledged': 'No'
                })
        
        # Sort transactions by date
        transactions.sort(key=lambda x: x['date'])
        
        # Calculate running balance for each transaction
        running_balance = opening_balance
        for tx in transactions:
            running_balance += tx['debit'] - tx['credit']
            tx['balance'] = running_balance
        
        # Update statement data - preserve original creation date
        original_created_at = saved_data[statement_key].get('created_at', datetime.now().isoformat())
        
        statement_data = {
            'company': company,
            'period': period,
            'created_at': original_created_at,
            'updated_at': datetime.now().isoformat(),
            'opening_balance': opening_balance,
            'closing_balance': closing_balance,
            'total_transactions': len(transactions),
            'total_debit': sum(tx['debit'] for tx in transactions),
            'total_credit': sum(tx['credit'] for tx in transactions),
            'transactions': transactions
        }
        
        # Save updated data
        new_statement_key = f"{company}_{period}"
        
        # If the key changed (company or period changed), delete old and create new
        if new_statement_key != statement_key and statement_key in saved_data:
            del saved_data[statement_key]
        
        saved_data[new_statement_key] = statement_data
        
        if save_statement_data(saved_data):
            # Redirect to success page
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Statement Updated Successfully</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f0fdf4; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .success-icon {{ font-size: 4rem; color: #f59e0b; margin-bottom: 20px; }}
                    h1 {{ color: #1e293b; }}
                    .summary {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
                    .btn {{ display: inline-block; background: #f59e0b; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 10px; }}
                    .btn:hover {{ background: #d97706; }}
                    .btn-secondary {{ background: #6b7280; }}
                    .btn-secondary:hover {{ background: #4b5563; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✏️</div>
                    <h1>Monthly Statement Updated Successfully!</h1>
                    <div class="summary">
                        <strong>Company:</strong> {statement_data['company'].upper()}<br>
                        <strong>Period:</strong> {statement_data['period']}<br>
                        <strong>Opening Balance:</strong> HK${statement_data['opening_balance']:,.2f}<br>
                        <strong>Closing Balance:</strong> HK${statement_data['closing_balance']:,.2f}<br>
                        <strong>Total Transactions:</strong> {len(transactions)}<br>
                        <strong>Total Debit:</strong> HK${statement_data['total_debit']:,.2f}<br>
                        <strong>Total Credit:</strong> HK${statement_data['total_credit']:,.2f}
                    </div>
                    <a href="/generate-statement-pdf/{new_statement_key}" class="btn">📄 Generate PDF Statement</a>
                    <a href="/saved-statements" class="btn btn-secondary">📁 View All Statements</a>
                    <a href="/" class="btn btn-secondary">🏠 Dashboard</a>
                </div>
            </body>
            </html>
            '''
        else:
            return "Error updating statement", 500
            
    except Exception as e:
        logger.error(f"Error updating statement: {e}")
        return f"Error: {e}", 500

@app.route('/delete-statement/<statement_key>')
def delete_statement(statement_key):
    """Delete a saved statement"""
    saved_data = load_statement_data()
    
    if statement_key in saved_data:
        del saved_data[statement_key]
        save_statement_data(saved_data)
        return f'''
        <script>
            alert('Statement deleted successfully');
            window.location.href = '/saved-statements';
        </script>
        '''
    else:
        return "Statement not found", 404

@app.route('/api/previous-balance/<company>/<period>')
def get_previous_balance(company, period):
    """Get previous month's closing balance for auto-population"""
    previous_balance = get_previous_month_closing_balance(company, period)
    
    # Calculate previous period for display
    try:
        year, month = period.split('-')
        year = int(year)
        month = int(month)
        
        if month == 1:
            prev_year = year - 1
            prev_month = 12
        else:
            prev_year = year
            prev_month = month - 1
            
        prev_period = f"{prev_year}-{prev_month:02d}"
    except:
        prev_period = "Unknown"
    
    return jsonify({
        'previous_balance': previous_balance,
        'previous_period': prev_period,
        'company': company,
        'current_period': period
    })

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    saved_data = load_statement_data()
    
    return jsonify({
        'status': 'operational',
        'version': 'monthly_statement_v1.0',
        'timestamp': datetime.now().isoformat(),
        'system_type': 'Monthly Statement Generator - Debit/Credit Format',
        'saved_statements': len(saved_data),
        'features': {
            'debit_credit_format': 'operational',
            'running_balance': 'operational', 
            'pdf_generation': 'operational',
            'data_persistence': 'operational',
            'opening_balance_carryforward': 'operational'
        },
        'statements_summary': [
            {
                'company': data.get('company', 'unknown'),
                'period': data.get('period', 'unknown'),
                'opening_balance': data.get('opening_balance', 0),
                'closing_balance': data.get('closing_balance', 0),
                'total_transactions': data.get('total_transactions', 0)
            }
            for data in saved_data.values()
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Monthly Statement Generator...")
    logger.info("Traditional debit/credit format with running balance")
    logger.info("Access at: http://localhost:8081")
    
    try:
        app.run(host='0.0.0.0', port=8081, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)