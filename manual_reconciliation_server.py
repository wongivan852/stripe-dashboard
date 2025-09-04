#!/usr/bin/env python3
"""
Manual Reconciliation Input Server
Allows manual input of reconciliation data to match Stripe reports exactly
"""

from flask import Flask, request, jsonify, render_template_string, Response
from datetime import datetime
import json
import os
import sys
from io import BytesIO
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['DEBUG'] = False

# Storage for manual reconciliation data
RECONCILIATION_DATA_FILE = 'data/manual_reconciliation_data.json'

def load_reconciliation_data():
    """Load saved reconciliation data"""
    if os.path.exists(RECONCILIATION_DATA_FILE):
        try:
            with open(RECONCILIATION_DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_previous_month_ending_balance(company, period):
    """Get the ending balance from the previous month for the same company"""
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
        
        saved_data = load_reconciliation_data()
        if prev_key in saved_data:
            return saved_data[prev_key].get('ending_balance', 0)
        
        return 0
    except:
        return 0

def save_reconciliation_data(data):
    """Save reconciliation data"""
    try:
        with open(RECONCILIATION_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving data: {e}")
        return False

@app.route('/')
def home():
    """Main dashboard"""
    saved_data = load_reconciliation_data()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manual Reconciliation Input System</title>
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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
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
            .data-grid { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 15px; 
                margin-top: 15px; 
            }
            .data-item { 
                background: white; 
                padding: 15px; 
                border-radius: 8px; 
                text-align: center; 
            }
            .data-label { 
                color: #64748b; 
                font-size: 0.9rem; 
                margin-bottom: 5px; 
            }
            .data-value { 
                font-weight: bold; 
                color: #1e293b; 
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Manual Reconciliation Input System</h1>
                <div class="badge">Perfect Stripe Report Matching</div>
                <p>Enter reconciliation data manually to match Stripe reports exactly</p>
            </div>
    '''
    
    # Show saved data if available
    if saved_data:
        html += '''
            <div class="saved-data">
                <h3>💾 Recently Saved Reconciliation Data</h3>
                <div class="data-grid">
        '''
        for key, report_data in saved_data.items():
            if isinstance(report_data, dict) and 'company' in report_data:
                html += f'''
                    <div class="data-item">
                        <div class="data-label">{report_data.get('company', 'Unknown')} - {report_data.get('period', 'Unknown')}</div>
                        <div class="data-value">HK${report_data.get('total_paid_out', 0):,.2f}</div>
                    </div>
                '''
        html += '''
                </div>
            </div>
        '''
    
    html += '''
            <div class="actions">
                <a href="/manual-input" class="action-card">
                    <div class="action-icon">✏️</div>
                    <div class="action-title">Manual Data Input</div>
                    <div class="action-desc">Enter reconciliation data from your Stripe report manually with full control over all values</div>
                </a>
                
                <a href="/template-generator" class="action-card">
                    <div class="action-icon">📋</div>
                    <div class="action-title">Excel Template Generator</div>
                    <div class="action-desc">Download an Excel template for easy data entry and bulk upload</div>
                </a>
                
                <a href="/saved-reports" class="action-card">
                    <div class="action-icon">📁</div>
                    <div class="action-title">Saved Reports</div>
                    <div class="action-desc">View, edit, and generate PDFs from previously entered reconciliation data</div>
                </a>
                
                <a href="/api/status" class="action-card">
                    <div class="action-icon">🔧</div>
                    <div class="action-title">System Status</div>
                    <div class="action-desc">Check system health and view saved data summary</div>
                </a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/manual-input')
def manual_input_form():
    """Manual input form for reconciliation data"""
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Manual Reconciliation Data Input</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 20px; 
                background: #f8fafc; 
            }
            .container { 
                max-width: 900px; 
                margin: 0 auto; 
                background: white; 
                padding: 30px; 
                border-radius: 12px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                border-bottom: 2px solid #667eea; 
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
                border-color: #667eea; 
            }
            .btn { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
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
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            .add-transaction {
                background: #10b981;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>✏️ Manual Reconciliation Data Input</h2>
                <p>Enter data exactly as shown in your Stripe payout reconciliation report</p>
            </div>
            
            <div class="info-box">
                <strong>💡 Pro Tip:</strong> Have your Stripe payout reconciliation PDF open while filling this form. 
                Copy the exact values to ensure perfect matching.
            </div>
            
            <form id="reconciliationForm" action="/save-reconciliation" method="POST">
                <!-- Basic Information -->
                <div class="section">
                    <div class="section-title">📋 Report Information</div>
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
                </div>
                
                <!-- Payout Reconciliation Section -->
                <div class="section">
                    <div class="section-title">💰 Payout Reconciliation (Money Transferred to Bank)</div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="charges_count">Number of Charges:</label>
                            <input type="number" name="charges_count" id="charges_count" min="0" step="1" required>
                        </div>
                        <div class="form-group">
                            <label for="charges_gross">Charges Gross Amount (HKD):</label>
                            <input type="number" name="charges_gross" id="charges_gross" step="0.01" min="0" required>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="charges_fees">Processing Fees (HKD):</label>
                            <input type="number" name="charges_fees" id="charges_fees" step="0.01" min="0" required>
                        </div>
                        <div class="form-group">
                            <label for="refunds_count">Number of Refunds:</label>
                            <input type="number" name="refunds_count" id="refunds_count" min="0" step="1" value="0">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="refunds_amount">Refunds Amount (HKD):</label>
                            <input type="number" name="refunds_amount" id="refunds_amount" step="0.01" min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label for="total_paid_out">Total Paid Out (HKD):</label>
                            <input type="number" name="total_paid_out" id="total_paid_out" step="0.01" readonly 
                                   style="background: #f3f4f6;">
                        </div>
                    </div>
                </div>
                
                <!-- Opening Balance Section -->
                <div class="section">
                    <div class="section-title">📈 Opening Balance (Brought Forward from Previous Month)</div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="opening_balance">Opening Balance (HKD):</label>
                            <input type="number" name="opening_balance" id="opening_balance" step="0.01" 
                                   placeholder="Will auto-populate from previous month" onchange="updateOpeningBalance()">
                        </div>
                        <div class="form-group">
                            <label>Auto-populate from previous month:</label>
                            <button type="button" class="btn" onclick="loadPreviousBalance()" 
                                    style="padding: 8px 16px; font-size: 14px;">Load Previous Month Balance</button>
                        </div>
                    </div>
                </div>
                
                <!-- Ending Balance Section -->
                <div class="section">
                    <div class="section-title">🏦 Ending Balance (Money Remaining in Stripe)</div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="ending_charges_count">Charges Count (Ending Balance):</label>
                            <input type="number" name="ending_charges_count" id="ending_charges_count" min="0" step="1" value="0">
                        </div>
                        <div class="form-group">
                            <label for="ending_charges_gross">Charges Gross (Ending Balance):</label>
                            <input type="number" name="ending_charges_gross" id="ending_charges_gross" step="0.01" min="0" value="0">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="ending_charges_fees">Fees (Ending Balance):</label>
                            <input type="number" name="ending_charges_fees" id="ending_charges_fees" step="0.01" min="0" value="0">
                        </div>
                        <div class="form-group">
                            <label for="ending_balance">Total Ending Balance (HKD):</label>
                            <input type="number" name="ending_balance" id="ending_balance" step="0.01" readonly 
                                   style="background: #f3f4f6;">
                        </div>
                    </div>
                </div>
                
                <!-- Individual Transactions (Optional) -->
                <div class="section transactions-section">
                    <div class="section-title">📝 Individual Transactions (Optional - for detailed PDF)</div>
                    <button type="button" class="add-transaction" onclick="addTransaction()">+ Add Transaction</button>
                    <div id="transactions-container"></div>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <button type="submit" class="btn">💾 Save Reconciliation Data</button>
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
                        <h4>Transaction ${transactionCount}</h4>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Date:</label>
                                <input type="date" name="transactions[${transactionCount}][date]">
                            </div>
                            <div class="form-group">
                                <label>Customer Email:</label>
                                <input type="email" name="transactions[${transactionCount}][email]" placeholder="customer@example.com">
                            </div>
                        </div>
                        <div class="form-row">
                            <div class="form-group">
                                <label>Amount (HKD):</label>
                                <input type="number" name="transactions[${transactionCount}][amount]" step="0.01">
                            </div>
                            <div class="form-group">
                                <label>Fee (HKD):</label>
                                <input type="number" name="transactions[${transactionCount}][fee]" step="0.01">
                            </div>
                        </div>
                        <button type="button" onclick="removeTransaction(${transactionCount})" 
                                style="background: #dc2626; color: white; padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer;">
                            Remove
                        </button>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', transactionHtml);
            }
            
            function removeTransaction(id) {
                document.getElementById(`transaction-${id}`).remove();
            }
            
            // Auto-calculate totals
            function calculateTotals() {
                const chargesGross = parseFloat(document.getElementById('charges_gross').value) || 0;
                const chargesFees = parseFloat(document.getElementById('charges_fees').value) || 0;
                const refundsAmount = parseFloat(document.getElementById('refunds_amount').value) || 0;
                
                const totalPaidOut = chargesGross - chargesFees + refundsAmount;
                document.getElementById('total_paid_out').value = totalPaidOut.toFixed(2);
                
                const endingGross = parseFloat(document.getElementById('ending_charges_gross').value) || 0;
                const endingFees = parseFloat(document.getElementById('ending_charges_fees').value) || 0;
                
                const endingBalance = endingGross - endingFees;
                document.getElementById('ending_balance').value = endingBalance.toFixed(2);
            }
            
            // Add event listeners for auto-calculation
            ['charges_gross', 'charges_fees', 'refunds_amount', 'ending_charges_gross', 'ending_charges_fees']
                .forEach(id => {
                    document.getElementById(id).addEventListener('input', calculateTotals);
                });
            
            function loadPreviousBalance() {
                const company = document.getElementById('company').value;
                const period = document.getElementById('period').value;
                
                if (!company || !period) {
                    alert('Please select company and period first');
                    return;
                }
                
                // Call API to get previous month balance
                fetch(`/api/previous-balance/${company}/${period}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.previous_balance !== undefined) {
                            document.getElementById('opening_balance').value = data.previous_balance.toFixed(2);
                            if (data.previous_balance > 0) {
                                alert(`Loaded ${data.previous_period} ending balance: HK$${data.previous_balance.toFixed(2)}`);
                            } else {
                                alert('No previous month data found. Opening balance set to 0.');
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Error loading previous balance');
                    });
            }
            
            function updateOpeningBalance() {
                // This function can be used for additional logic when opening balance changes
            }
        </script>
    </body>
    </html>
    '''
    
    return html

@app.route('/save-reconciliation', methods=['POST'])
def save_reconciliation():
    """Save manually entered reconciliation data"""
    try:
        # Extract form data
        company = request.form.get('company')
        period = request.form.get('period')
        
        # Parse transactions if any
        transactions = []
        form_data = request.form.to_dict()
        
        # Extract individual transactions
        for key in form_data:
            if key.startswith('transactions[') and key.endswith('][date]'):
                tx_id = key.split('[')[1].split(']')[0]
                
                date = form_data.get(f'transactions[{tx_id}][date]')
                email = form_data.get(f'transactions[{tx_id}][email]')
                amount = form_data.get(f'transactions[{tx_id}][amount]')
                fee = form_data.get(f'transactions[{tx_id}][fee]')
                
                if date or email or amount or fee:  # Only add if at least one field is filled
                    transactions.append({
                        'date': date,
                        'email': email,
                        'amount': float(amount) if amount else 0,
                        'fee': float(fee) if fee else 0
                    })
        
        # Build reconciliation data
        reconciliation_data = {
            'company': company,
            'period': period,
            'created_at': datetime.now().isoformat(),
            'opening_balance': float(request.form.get('opening_balance', 0)),
            'charges_count': int(request.form.get('charges_count', 0)),
            'charges_gross': float(request.form.get('charges_gross', 0)),
            'charges_fees': float(request.form.get('charges_fees', 0)),
            'refunds_count': int(request.form.get('refunds_count', 0)),
            'refunds_amount': float(request.form.get('refunds_amount', 0)),
            'total_paid_out': float(request.form.get('total_paid_out', 0)),
            'ending_charges_count': int(request.form.get('ending_charges_count', 0)),
            'ending_charges_gross': float(request.form.get('ending_charges_gross', 0)),
            'ending_charges_fees': float(request.form.get('ending_charges_fees', 0)),
            'ending_balance': float(request.form.get('ending_balance', 0)),
            'transactions': transactions
        }
        
        # Save to file
        saved_data = load_reconciliation_data()
        report_key = f"{company}_{period}"
        saved_data[report_key] = reconciliation_data
        
        if save_reconciliation_data(saved_data):
            # Redirect to success page with option to generate PDF
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Data Saved Successfully</title>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f0fdf4; }}
                    .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 40px; border-radius: 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .success-icon {{ font-size: 4rem; color: #10b981; margin-bottom: 20px; }}
                    h1 {{ color: #1e293b; }}
                    .summary {{ background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: left; }}
                    .btn {{ display: inline-block; background: #10b981; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin: 10px; }}
                    .btn:hover {{ background: #059669; }}
                    .btn-secondary {{ background: #6b7280; }}
                    .btn-secondary:hover {{ background: #4b5563; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success-icon">✅</div>
                    <h1>Reconciliation Data Saved Successfully!</h1>
                    <div class="summary">
                        <strong>Company:</strong> {reconciliation_data['company'].upper()}<br>
                        <strong>Period:</strong> {reconciliation_data['period']}<br>
                        <strong>Opening Balance:</strong> HK${reconciliation_data['opening_balance']:,.2f}<br>
                        <strong>Total Paid Out:</strong> HK${reconciliation_data['total_paid_out']:,.2f}<br>
                        <strong>Ending Balance:</strong> HK${reconciliation_data['ending_balance']:,.2f}<br>
                        <strong>Transactions:</strong> {len(transactions)} individual transactions
                    </div>
                    <a href="/generate-pdf/{report_key}" class="btn">📄 Generate PDF Report</a>
                    <a href="/saved-reports" class="btn btn-secondary">📁 View All Reports</a>
                    <a href="/" class="btn btn-secondary">🏠 Dashboard</a>
                </div>
            </body>
            </html>
            '''
        else:
            return "Error saving data", 500
            
    except Exception as e:
        logger.error(f"Error saving reconciliation: {e}")
        return f"Error: {e}", 500

@app.route('/saved-reports')
def saved_reports():
    """View all saved reconciliation reports"""
    saved_data = load_reconciliation_data()
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Saved Reconciliation Reports</title>
        <meta charset="UTF-8">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f8fafc; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 12px; margin-bottom: 30px; }
            .reports-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
            .report-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .report-title { font-size: 1.2rem; font-weight: bold; color: #1e293b; margin-bottom: 15px; }
            .report-details { background: #f8fafc; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
            .detail-row { display: flex; justify-content: space-between; margin-bottom: 8px; }
            .detail-label { color: #64748b; }
            .detail-value { font-weight: 600; color: #1e293b; }
            .btn { display: inline-block; background: #667eea; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; margin: 5px; font-size: 0.9rem; }
            .btn:hover { background: #5a67d8; }
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
                <h1>📁 Saved Reconciliation Reports</h1>
                <p>Manage and generate PDFs from your saved reconciliation data</p>
            </div>
    '''
    
    if not saved_data:
        html += '''
            <div style="text-align: center; padding: 60px; background: white; border-radius: 12px;">
                <h2>No saved reports yet</h2>
                <p>Create your first reconciliation report to get started.</p>
                <a href="/manual-input" class="btn btn-success">Create New Report</a>
            </div>
        '''
    else:
        html += '<div class="reports-grid">'
        
        for report_key, report_data in saved_data.items():
            company_name = {'cgge': 'CGGE', 'ki': 'Krystal Institute', 'kt': 'Krystal Technology'}.get(report_data.get('company', ''), 'Unknown')
            
            html += f'''
            <div class="report-card">
                <div class="report-title">{company_name} - {report_data.get('period', 'Unknown Period')}</div>
                <div class="report-details">
                    <div class="detail-row">
                        <span class="detail-label">Opening Balance:</span>
                        <span class="detail-value">HK${report_data.get('opening_balance', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Total Paid Out:</span>
                        <span class="detail-value">HK${report_data.get('total_paid_out', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Ending Balance:</span>
                        <span class="detail-value">HK${report_data.get('ending_balance', 0):,.2f}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Charges:</span>
                        <span class="detail-value">{report_data.get('charges_count', 0)} transactions</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Individual Transactions:</span>
                        <span class="detail-value">{len(report_data.get('transactions', []))}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Created:</span>
                        <span class="detail-value">{report_data.get('created_at', '')[:10]}</span>
                    </div>
                </div>
                <div>
                    <a href="/generate-pdf/{report_key}" class="btn btn-success">📄 Generate PDF</a>
                    <a href="/edit-report/{report_key}" class="btn">✏️ Edit</a>
                    <a href="/delete-report/{report_key}" class="btn btn-danger" onclick="return confirm('Are you sure?')">🗑️ Delete</a>
                </div>
            </div>
            '''
        
        html += '</div>'
    
    html += '''
            <div style="text-align: center; margin-top: 30px;">
                <a href="/manual-input" class="btn btn-success">➕ Create New Report</a>
                <a href="/" class="btn btn-secondary">🏠 Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/generate-pdf/<report_key>')
def generate_pdf(report_key):
    """Generate HTML version for PDF printing"""
    saved_data = load_reconciliation_data()
    
    if report_key not in saved_data:
        return "Report not found", 404
    
    report_data = saved_data[report_key]
    
    # Company name mapping
    company_names = {'cgge': 'CGGE', 'ki': 'Krystal Institute', 'kt': 'Krystal Technology'}
    company_name = company_names.get(report_data['company'], 'Unknown Company')
    
    # Period formatting
    period = report_data['period']
    try:
        date_obj = datetime.strptime(period, '%Y-%m')
        period_formatted = date_obj.strftime('%B %Y')
    except:
        period_formatted = period
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payout Reconciliation Report - {company_name} {period_formatted}</title>
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
            }}
            .header {{ 
                text-align: center; 
                margin-bottom: 30px;
                border-bottom: 3px solid #667eea;
                padding-bottom: 20px;
            }}
            .company-name {{ 
                font-size: 2.5rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 10px;
            }}
            .report-title {{ 
                font-size: 1.8rem; 
                color: #64748b; 
                margin-bottom: 10px;
            }}
            .opening-balance {{
                background: #f0fdf4;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                text-align: center;
                font-size: 1.1rem;
            }}
            .section {{ 
                margin-bottom: 30px; 
            }}
            .section-title {{ 
                font-size: 1.4rem; 
                font-weight: bold; 
                color: #1e293b; 
                margin-bottom: 15px;
                padding: 10px 0;
                border-bottom: 2px solid #e5e7eb;
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            th {{ 
                background: #f8fafc; 
                padding: 15px 12px; 
                text-align: left; 
                font-weight: bold; 
                color: #374151; 
                border: 1px solid #e5e7eb;
            }}
            td {{ 
                padding: 12px; 
                border: 1px solid #e5e7eb;
                text-align: left;
            }}
            .amount {{ 
                text-align: right; 
                font-family: 'Courier New', monospace;
            }}
            .total-row {{ 
                font-weight: bold; 
                background: #f0fdf4;
            }}
            .print-btn {{
                background: #667eea;
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
            }}
            .print-btn:hover {{
                background: #5a67d8;
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
            <div class="report-title">Payout Reconciliation Report - {period_formatted}</div>
        </div>
    '''
    
    # Opening Balance
    if report_data.get('opening_balance', 0) > 0:
        html += f'''
        <div class="opening-balance">
            <strong>Opening Balance (Brought Forward):</strong> HK${report_data['opening_balance']:,.2f}
        </div>
        '''
    
    # Payout Reconciliation Section
    html += f'''
        <div class="section">
            <div class="section-title">💰 Payout Reconciliation</div>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Count</th>
                        <th class="amount">Gross Amount (HKD)</th>
                        <th class="amount">Fees (HKD)</th>
                        <th class="amount">Net Amount (HKD)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Charges</td>
                        <td>{report_data['charges_count']}</td>
                        <td class="amount">HK${report_data['charges_gross']:,.2f}</td>
                        <td class="amount">HK${report_data['charges_fees']:,.2f}</td>
                        <td class="amount">HK${report_data['charges_gross'] - report_data['charges_fees']:,.2f}</td>
                    </tr>
                    <tr>
                        <td>Refunds</td>
                        <td>{report_data['refunds_count']}</td>
                        <td class="amount">HK${report_data['refunds_amount']:,.2f}</td>
                        <td class="amount">-</td>
                        <td class="amount">HK${report_data['refunds_amount']:,.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td><strong>Total Paid Out</strong></td>
                        <td><strong>{report_data['charges_count'] + report_data['refunds_count']}</strong></td>
                        <td class="amount">-</td>
                        <td class="amount">-</td>
                        <td class="amount"><strong>HK${report_data['total_paid_out']:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">🏦 Ending Balance Reconciliation</div>
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Count</th>
                        <th class="amount">Gross Amount (HKD)</th>
                        <th class="amount">Fees (HKD)</th>
                        <th class="amount">Net Amount (HKD)</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Charges</td>
                        <td>{report_data['ending_charges_count']}</td>
                        <td class="amount">HK${report_data['ending_charges_gross']:,.2f}</td>
                        <td class="amount">HK${report_data['ending_charges_fees']:,.2f}</td>
                        <td class="amount">HK${report_data['ending_charges_gross'] - report_data['ending_charges_fees']:,.2f}</td>
                    </tr>
                    <tr class="total-row">
                        <td><strong>Ending Balance</strong></td>
                        <td><strong>{report_data['ending_charges_count']}</strong></td>
                        <td class="amount">-</td>
                        <td class="amount">-</td>
                        <td class="amount"><strong>HK${report_data['ending_balance']:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>
    '''
    
    # Individual Transactions
    if report_data.get('transactions'):
        valid_transactions = [tx for tx in report_data['transactions'] 
                            if tx.get('date') or tx.get('email') or tx.get('amount')]
        
        if valid_transactions:
            html += '''
            <div class="section">
                <div class="section-title">📝 Individual Transactions</div>
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Customer Email</th>
                            <th class="amount">Amount (HKD)</th>
                            <th class="amount">Fee (HKD)</th>
                            <th class="amount">Net (HKD)</th>
                        </tr>
                    </thead>
                    <tbody>
            '''
            
            for tx in valid_transactions:
                net_amount = (tx.get('amount', 0) or 0) - (tx.get('fee', 0) or 0)
                html += f'''
                        <tr>
                            <td>{tx.get('date', '')}</td>
                            <td>{tx.get('email', '')}</td>
                            <td class="amount">HK${tx.get('amount', 0):,.2f}</td>
                            <td class="amount">HK${tx.get('fee', 0):,.2f}</td>
                            <td class="amount">HK${net_amount:,.2f}</td>
                        </tr>
                '''
            
            html += '''
                    </tbody>
                </table>
            </div>
            '''
    
    html += '''
        <div class="no-print" style="text-align: center; margin-top: 40px;">
            <button class="print-btn" onclick="window.print()">🖨️ Print to PDF</button>
            <a href="/saved-reports" class="print-btn" style="text-decoration: none;">← Back to Reports</a>
        </div>
    </body>
    </html>
    '''
    
    return html

@app.route('/delete-report/<report_key>')
def delete_report(report_key):
    """Delete a saved report"""
    saved_data = load_reconciliation_data()
    
    if report_key in saved_data:
        del saved_data[report_key]
        save_reconciliation_data(saved_data)
        return f'''
        <script>
            alert('Report deleted successfully');
            window.location.href = '/saved-reports';
        </script>
        '''
    else:
        return "Report not found", 404

@app.route('/api/previous-balance/<company>/<period>')
def get_previous_balance(company, period):
    """Get previous month's ending balance for auto-population"""
    previous_balance = get_previous_month_ending_balance(company, period)
    
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
    saved_data = load_reconciliation_data()
    
    return jsonify({
        'status': 'operational',
        'version': 'manual_input_v1.0',
        'timestamp': datetime.now().isoformat(),
        'system_type': 'Manual Reconciliation Input System',
        'saved_reports': len(saved_data),
        'features': {
            'manual_data_entry': 'operational',
            'pdf_generation': 'operational', 
            'data_persistence': 'operational',
            'individual_transactions': 'operational'
        },
        'reports_summary': [
            {
                'company': data.get('company', 'unknown'),
                'period': data.get('period', 'unknown'),
                'total_paid_out': data.get('total_paid_out', 0),
                'ending_balance': data.get('ending_balance', 0)
            }
            for data in saved_data.values()
        ]
    })

if __name__ == '__main__':
    logger.info("Starting Manual Reconciliation Input Server...")
    logger.info("Perfect Stripe report matching with manual data entry")
    logger.info("Access at: http://localhost:8081")
    
    try:
        app.run(host='0.0.0.0', port=8081, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)