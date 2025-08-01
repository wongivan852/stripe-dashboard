from flask import Blueprint, jsonify, render_template_string, request, Response
from app import db
from app.models import StripeAccount, Transaction
from sqlalchemy import func, text
from datetime import datetime, timedelta
from app.services.csv_transaction_service import CSVTransactionService
import json
import csv
import io

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/verify-transactions')
def verify_transactions():
    """Simple endpoint to verify total transaction counts"""
    try:
        # Direct count from database
        total_transactions = db.session.execute(text("""
            SELECT COUNT(*) FROM "transaction" t
            INNER JOIN stripe_account sa ON sa.id = t.account_id
            WHERE sa.is_active = 1
        """)).scalar()
        
        # Count by account
        by_account = db.session.execute(text("""
            SELECT 
                sa.name,
                COUNT(t.id) as count
            FROM stripe_account sa
            LEFT JOIN "transaction" t ON sa.id = t.account_id
            WHERE sa.is_active = 1
            GROUP BY sa.name
            ORDER BY count DESC
        """)).fetchall()
        
        accounts_info = []
        for row in by_account:
            accounts_info.append({
                'account_name': row[0],
                'transaction_count': row[1] or 0
            })
        
        return jsonify({
            'success': True,
            'total_transactions_in_db': total_transactions,
            'accounts': accounts_info,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/debug/transaction-counts')
def debug_transaction_counts():
    """Debug endpoint to verify transaction counts and identify missing data"""
    try:
        # Get raw transaction counts by account
        raw_counts = db.session.execute(text("""
            SELECT 
                sa.name as account_name,
                sa.account_id,
                COUNT(t.id) as transaction_count,
                COUNT(CASE WHEN t.status IS NULL THEN 1 END) as null_status_count,
                COUNT(CASE WHEN t.type IS NULL THEN 1 END) as null_type_count,
                COUNT(CASE WHEN t.status IS NOT NULL AND t.type IS NOT NULL THEN 1 END) as complete_count,
                GROUP_CONCAT(DISTINCT t.status) as all_statuses,
                GROUP_CONCAT(DISTINCT t.type) as all_types,
                MIN(t.created_at) as earliest_transaction,
                MAX(t.created_at) as latest_transaction
            FROM stripe_account sa
            LEFT JOIN "transaction" t ON sa.id = t.account_id
            WHERE sa.is_active = 1
            GROUP BY sa.name, sa.account_id
            ORDER BY transaction_count DESC
        """)).fetchall()
        
        # Get sample transactions with missing data
        missing_data_samples = db.session.execute(text("""
            SELECT 
                sa.name as account_name,
                t.transaction_id,
                t.status,
                t.type,
                t.amount,
                t.created_at,
                t.description
            FROM stripe_account sa
            LEFT JOIN "transaction" t ON sa.id = t.account_id
            WHERE sa.is_active = 1 
            AND (t.status IS NULL OR t.type IS NULL)
            LIMIT 10
        """)).fetchall()
        
        debug_data = {
            'account_summary': [],
            'missing_data_samples': [],
            'total_accounts': 0,
            'total_transactions': 0,
            'transactions_with_missing_data': 0
        }
        
        total_transactions = 0
        total_missing = 0
        
        for row in raw_counts:
            account_info = {
                'account_name': row[0],
                'account_id': row[1],
                'total_transactions': row[2] or 0,
                'null_status_count': row[3] or 0,
                'null_type_count': row[4] or 0,
                'complete_count': row[5] or 0,
                'all_statuses': row[6] or 'None',
                'all_types': row[7] or 'None',
                'earliest_transaction': str(row[8]) if row[8] else 'None',
                'latest_transaction': str(row[9]) if row[9] else 'None'
            }
            debug_data['account_summary'].append(account_info)
            total_transactions += account_info['total_transactions']
            total_missing += account_info['null_status_count'] + account_info['null_type_count']
        
        for row in missing_data_samples:
            sample = {
                'account_name': row[0],
                'transaction_id': row[1],
                'status': row[2],
                'type': row[3],
                'amount': row[4],
                'created_at': str(row[5]) if row[5] else 'None',
                'description': row[6]
            }
            debug_data['missing_data_samples'].append(sample)
        
        debug_data['total_accounts'] = len(debug_data['account_summary'])
        debug_data['total_transactions'] = total_transactions
        debug_data['transactions_with_missing_data'] = total_missing
        
        return jsonify({
            'success': True,
            'debug_data': debug_data,
            'message': f"Found {total_transactions} total transactions across {len(debug_data['account_summary'])} accounts. {total_missing} transactions have missing status or type."
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@analytics_bp.route('/api/account-amounts')
def get_account_amounts():
    """API endpoint for account amounts - returns properly formatted JSON"""
    try:
        # Initialize CSV service
        csv_service = CSVTransactionService()
        
        # Get all transactions from CSV
        transactions = csv_service.get_all_transactions()
        
        # Get account summary
        summary = csv_service.get_account_summary()
        
        # Group transactions by account
        account_data = {}
        
        for tx in transactions:
            account_name = tx['account_name']
            if account_name not in account_data:
                account_data[account_name] = {
                    'account_name': account_name,
                    'stripe_account_id': f"acct_{account_name.lower().replace(' ', '_')}",
                    'total_transactions': 0,
                    'total_amount_hkd': 0.0,
                    'total_fees_hkd': 0.0,
                    'net_amount_hkd': 0.0,
                    'by_status': {},
                    'by_type': {},
                    'is_active': True
                }
            
            # Update totals
            account_data[account_name]['total_transactions'] += 1
            account_data[account_name]['total_amount_hkd'] += tx['amount']
            account_data[account_name]['total_fees_hkd'] += tx['fee']
            account_data[account_name]['net_amount_hkd'] += tx['net_amount']
            
            # Group by status
            status = tx['status']
            if status not in account_data[account_name]['by_status']:
                account_data[account_name]['by_status'][status] = {
                    'count': 0,
                    'amount_hkd': 0.0,
                    'fee_hkd': 0.0,
                    'net_hkd': 0.0
                }
            account_data[account_name]['by_status'][status]['count'] += 1
            account_data[account_name]['by_status'][status]['amount_hkd'] += tx['amount']
            account_data[account_name]['by_status'][status]['fee_hkd'] += tx['fee']
            account_data[account_name]['by_status'][status]['net_hkd'] += tx['net_amount']
            
            # Group by type
            tx_type = tx['type']
            if tx_type not in account_data[account_name]['by_type']:
                account_data[account_name]['by_type'][tx_type] = {
                    'count': 0,
                    'amount_hkd': 0.0,
                    'fee_hkd': 0.0,
                    'net_hkd': 0.0
                }
            account_data[account_name]['by_type'][tx_type]['count'] += 1
            account_data[account_name]['by_type'][tx_type]['amount_hkd'] += tx['amount']
            account_data[account_name]['by_type'][tx_type]['fee_hkd'] += tx['fee']
            account_data[account_name]['by_type'][tx_type]['net_hkd'] += tx['net_amount']
        
        # Calculate summary
        total_accounts = len(account_data)
        total_transactions = summary['total_transactions']
        total_amount = summary['total_amount']
        total_fees = summary['total_fees']
        net_amount = summary['total_net']
        
        # Debug output to console
        print(f"🔍 Analytics API Debug Info (CSV):")
        print(f"   - Total accounts found: {total_accounts}")
        print(f"   - Total transactions: {total_transactions}")
        print(f"   - Gross amount: HK${total_amount:,.2f}")
        print(f"   - Total fees: HK${total_fees:,.2f}")
        print(f"   - Net amount: HK${net_amount:,.2f}")
        for acc_name, acc_data in account_data.items():
            print(f"   - {acc_name}: {acc_data['total_transactions']} txns, Gross: HK${acc_data['total_amount_hkd']:,.2f}, Fees: HK${acc_data['total_fees_hkd']:,.2f}, Net: HK${acc_data['net_amount_hkd']:,.2f}")
        
        response_data = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_accounts': total_accounts,
                'total_transactions': total_transactions,
                'total_amount_hkd': round(total_amount, 2),
                'total_fees_hkd': round(total_fees, 2),
                'net_amount_hkd': round(net_amount, 2),
                'fee_percentage': round((total_fees / total_amount * 100) if total_amount > 0 else 0, 2),
                'debug_info': f"Processed {total_accounts} accounts with {total_transactions} total transactions from CSV"
            },
            'accounts': list(account_data.values())
        }
        
        # Check if request wants raw JSON or formatted HTML
        accept_header = request.headers.get('Accept', '')
        format_param = request.args.get('format', '')
        
        if 'application/json' in accept_header or format_param == 'json':
            # Return raw JSON
            return Response(
                json.dumps(response_data, indent=2, ensure_ascii=False),
                mimetype='application/json',
                headers={
                    'Content-Type': 'application/json; charset=utf-8',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            # Return formatted HTML view
            return render_formatted_json(response_data)
            
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        
        return Response(
            json.dumps(error_response, indent=2),
            mimetype='application/json',
            status=500,
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

def render_formatted_json(data):
    """Render JSON data as formatted HTML"""
    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Data - Account Amounts</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: #f8fafc; line-height: 1.6; color: #334155; padding: 20px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
            .navigation {{
                display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                flex-wrap: wrap;
            }}
            .nav-link {{
                padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                border-radius: 8px; transition: all 0.2s; font-weight: 500;
            }}
            .nav-link:hover {{ background: #4338ca; transform: translateY(-1px); }}
            .summary-cards {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px; margin-bottom: 20px;
            }}
            .summary-card {{
                background: white; padding: 20px; border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center;
                border-left: 4px solid #4f46e5;
            }}
            .summary-number {{
                font-size: 2rem; font-weight: bold; color: #1e293b; margin-bottom: 8px;
            }}
            .summary-label {{
                color: #64748b; font-weight: 500;
            }}
            .json-container {{
                background: white; padding: 24px; border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin: 20px 0;
            }}
            .json-header {{
                display: flex; justify-content: space-between; align-items: center;
                margin-bottom: 16px; flex-wrap: wrap; gap: 10px;
            }}
            .json-title {{
                font-size: 1.3rem; font-weight: bold; color: #1e293b;
            }}
            .action-buttons {{
                display: flex; gap: 10px;
            }}
            .btn {{
                padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer;
                font-weight: 500; transition: all 0.2s; color: white;
            }}
            .btn-copy {{ background: #10b981; }}
            .btn-copy:hover {{ background: #059669; }}
            .btn-download {{ background: #3b82f6; }}
            .btn-download:hover {{ background: #2563eb; }}
            .btn-raw {{ background: #6b7280; }}
            .btn-raw:hover {{ background: #4b5563; }}
            .json-content {{
                background: #1e293b; color: #e2e8f0; padding: 20px; border-radius: 8px;
                overflow-x: auto; font-family: 'Monaco', 'Menlo', monospace; font-size: 14px;
                white-space: pre-wrap; line-height: 1.5; max-height: 500px; overflow-y: auto;
            }}
            .api-info {{
                background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px;
                padding: 16px; margin-bottom: 20px; color: #0c4a6e;
            }}
            @media (max-width: 768px) {{
                .container {{ padding: 10px; }}
                .header {{ padding: 1.5rem; }}
                .navigation {{ flex-direction: column; align-items: center; }}
                .json-header {{ flex-direction: column; align-items: stretch; }}
                .action-buttons {{ justify-content: center; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔗 API Data - Account Amounts</h1>
                <p>Complete JSON API endpoint with all transaction data</p>
            </div>
            
            <div class="navigation">
                <a href="/" class="nav-link">🏠 Home</a>
                <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                <a href="/analytics/summary" class="nav-link">📈 Summary</a>
            </div>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="summary-number">{data['summary']['total_accounts']}</div>
                    <div class="summary-label">Active Accounts</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">{data['summary']['total_transactions']:,}</div>
                    <div class="summary-label">Total Transactions</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">HK${data['summary']['total_amount_hkd']:,.2f}</div>
                    <div class="summary-label">Gross Amount</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">HK${data['summary']['total_fees_hkd']:,.2f}</div>
                    <div class="summary-label">Processing Fees</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">HK${data['summary']['net_amount_hkd']:,.2f}</div>
                    <div class="summary-label">Net Amount</div>
                </div>
                <div class="summary-card">
                    <div class="summary-number">{data['summary']['fee_percentage']:.2f}%</div>
                    <div class="summary-label">Fee Rate</div>
                </div>
            </div>
            
            <div class="api-info">
                <h3>📡 API Usage Information</h3>
                <p><strong>Endpoint:</strong> <code>/analytics/api/account-amounts</code></p>
                <p><strong>Method:</strong> GET</p>
                <p><strong>Response Format:</strong> JSON</p>
                <p><strong>Parameters:</strong></p>
                <ul style="margin: 8px 0 0 20px;">
                    <li><code>format=json</code> - Returns raw JSON (for API calls)</li>
                    <li>No parameters - Returns this formatted view (for browsers)</li>
                </ul>
            </div>
            
            <div class="json-container">
                <div class="json-header">
                    <div class="json-title">📄 Complete API Response</div>
                    <div class="action-buttons">
                        <button class="btn btn-copy" onclick="copyToClipboard()">📋 Copy JSON</button>
                        <button class="btn btn-download" onclick="downloadJSON()">💾 Download</button>
                        <button class="btn btn-raw" onclick="openRawJSON()">🔗 Raw JSON</button>
                    </div>
                </div>
                <div class="json-content" id="jsonContent">{formatted_json}</div>
            </div>
        </div>
        
        <script>
            function copyToClipboard() {{
                const jsonContent = document.getElementById('jsonContent').textContent;
                navigator.clipboard.writeText(jsonContent).then(() => {{
                    const btn = document.querySelector('.btn-copy');
                    const originalText = btn.textContent;
                    btn.textContent = '✅ Copied!';
                    btn.style.background = '#059669';
                    setTimeout(() => {{
                        btn.textContent = originalText;
                        btn.style.background = '#10b981';
                    }}, 2000);
                }}).catch(err => {{
                    alert('Copy failed. Please select and copy manually.');
                }});
            }}
            
            function downloadJSON() {{
                const jsonContent = document.getElementById('jsonContent').textContent;
                const blob = new Blob([jsonContent], {{ type: 'application/json' }});
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'stripe_account_amounts_' + new Date().toISOString().split('T')[0] + '.json';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }}
            
            function openRawJSON() {{
                window.open('/analytics/api/account-amounts?format=json', '_blank');
            }}
            
            // Auto-refresh every 5 minutes
            setTimeout(() => location.reload(), 300000);
        </script>
    </body>
    </html>
    '''
    
    return html

@analytics_bp.route('/summary')
def account_summary():
    """Quick account summary endpoint"""
    try:
        # Get all accounts with transaction counts
        accounts = StripeAccount.query.filter_by(is_active=True).all()
        
        summary_data = []
        total_transactions = 0
        total_amount = 0
        
        for account in accounts:
            # Get transaction count and total amount for this account
            account_transactions = Transaction.query.filter_by(account_id=account.id).count()
            
            account_amount = db.session.query(func.sum(Transaction.amount))\
                                   .filter_by(account_id=account.id)\
                                   .scalar() or 0
            
            account_amount_hkd = account_amount / 100
            
            # Get status breakdown
            status_breakdown = db.session.execute(text("""
                SELECT status, COUNT(*) as count, SUM(amount) as total
                FROM "transaction" 
                WHERE account_id = :account_id
                GROUP BY status
            """), {'account_id': account.id}).fetchall()
            
            status_summary = {}
            for status_row in status_breakdown:
                status_summary[status_row[0]] = {
                    'count': status_row[1],
                    'amount_hkd': (status_row[2] or 0) / 100
                }
            
            account_data = {
                'name': account.name,
                'account_id': account.account_id,
                'stripe_account_id': account.account_id,
                'transactions': account_transactions,
                'total_amount_hkd': round(account_amount_hkd, 2),
                'is_active': account.is_active,
                'status_breakdown': status_summary
            }
            
            summary_data.append(account_data)
            total_transactions += account_transactions
            total_amount += account_amount_hkd
        
        response_data = {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_accounts': len(summary_data),
                'total_transactions': total_transactions,
                'total_amount_hkd': round(total_amount, 2)
            },
            'accounts': summary_data
        }
        
        # Check if JSON is requested
        if request.headers.get('Accept', '').find('application/json') != -1 or request.args.get('format') == 'json':
            return jsonify(response_data)
        
        # Return HTML view
        return render_summary_html(response_data)
        
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
        
        if request.headers.get('Accept', '').find('application/json') != -1:
            return jsonify(error_response), 500
        else:
            return f'''
            <div style="padding: 40px; text-align: center; background: #fef2f2;">
                <h1 style="color: #dc2626;">❌ Error</h1>
                <p>Error loading summary: {str(e)}</p>
                <p><a href="/" style="color: #4f46e5;">← Back to Home</a></p>
            </div>
            '''

def render_summary_html(data):
    """Render summary data as HTML"""
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Account Summary</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: #f8fafc; line-height: 1.6; color: #334155; padding: 20px;
            }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
            .navigation {{
                display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                flex-wrap: wrap;
            }}
            .nav-link {{
                padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                border-radius: 8px; transition: all 0.2s; font-weight: 500;
            }}
            .nav-link:hover {{ background: #4338ca; transform: translateY(-1px); }}
            .summary-stats {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px; margin-bottom: 30px;
            }}
            .stat-card {{
                background: white; padding: 20px; border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center;
                border-left: 4px solid #4f46e5;
            }}
            .stat-number {{
                font-size: 2.5rem; font-weight: bold; color: #1e293b; margin-bottom: 8px;
            }}
            .stat-label {{
                color: #64748b; font-weight: 500;
            }}
            .accounts-grid {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px; margin: 20px 0;
            }}
            .account-card {{
                background: white; padding: 24px; border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #4f46e5;
            }}
            .account-name {{
                font-size: 1.4rem; font-weight: bold; margin-bottom: 16px;
                color: #1e293b; display: flex; align-items: center; gap: 8px;
            }}
            .account-detail {{
                display: flex; justify-content: space-between; padding: 8px 0;
                border-bottom: 1px solid #f1f5f9; align-items: center;
            }}
            .account-detail:last-child {{ border-bottom: none; }}
            .status-active {{ color: #10b981; font-weight: 600; }}
            .status-inactive {{ color: #ef4444; font-weight: 600; }}
            .status-breakdown {{
                margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb;
            }}
            .status-item {{
                display: flex; justify-content: space-between; padding: 4px 0;
                font-size: 0.9rem;
            }}
            .status-succeeded {{ color: #059669; }}
            .status-failed {{ color: #dc2626; }}
            .status-pending {{ color: #d97706; }}
            .total-summary {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white; text-align: center; padding: 24px; border-radius: 12px;
                margin-top: 24px; font-size: 1.3rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
            @media (max-width: 768px) {{
                .container {{ padding: 10px; }}
                .header {{ padding: 1.5rem; }}
                .navigation {{ flex-direction: column; align-items: center; }}
                .accounts-grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 Account Summary</h1>
                <p>Overview of all Stripe accounts and their performance</p>
            </div>
            
            <div class="navigation">
                <a href="/" class="nav-link">🏠 Home</a>
                <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
            </div>
            
            <div class="summary-stats">
                <div class="stat-card">
                    <div class="stat-number">{data['summary']['total_accounts']}</div>
                    <div class="stat-label">Active Accounts</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{data['summary']['total_transactions']:,}</div>
                    <div class="stat-label">Total Transactions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">HK${data['summary']['total_amount_hkd']:,.2f}</div>
                    <div class="stat-label">Total Revenue</div>
                </div>
            </div>
            
            <div class="accounts-grid">
    '''
    
    for account in data['accounts']:
        status_class = "status-active" if account['is_active'] else "status-inactive"
        status_text = "✅ Active" if account['is_active'] else "❌ Inactive"
        
        html += f'''
        <div class="account-card">
            <div class="account-name">🏢 {account['name']}</div>
            <div class="account-detail">
                <span>Status:</span>
                <span class="{status_class}">{status_text}</span>
            </div>
            <div class="account-detail">
                <span>Account ID:</span>
                <span>{account['account_id'] or 'N/A'}</span>
            </div>
            <div class="account-detail">
                <span>Total Transactions:</span>
                <span><strong>{account['transactions']:,}</strong></span>
            </div>
            <div class="account-detail">
                <span>Total Amount:</span>
                <span><strong>HK${account['total_amount_hkd']:,.2f}</strong></span>
            </div>
        '''
        
        if account['status_breakdown']:
            html += '<div class="status-breakdown"><strong>Status Breakdown:</strong>'
            for status, status_data in account['status_breakdown'].items():
                status_class = f"status-{status}"
                html += f'''
                <div class="status-item">
                    <span class="{status_class}">{status.title()}:</span>
                    <span>{status_data['count']} (HK${status_data['amount_hkd']:,.2f})</span>
                </div>
                '''
            html += '</div>'
        
        html += '</div>'
    
    html += f'''
            </div>
            
            <div class="total-summary">
                🎯 Overall Performance: {data['summary']['total_accounts']} accounts managing {data['summary']['total_transactions']:,} transactions worth HK${data['summary']['total_amount_hkd']:,.2f}
            </div>
        </div>
        <script>
            // Auto-refresh every 5 minutes
            setTimeout(() => location.reload(), 300000);
        </script>
    </body>
    </html>
    '''
    
    return html

@analytics_bp.route('/simple')
def simple_analytics():
    """Simple analytics dashboard with improved data handling"""
    try:
        # Get transaction data with proper error handling
        results = db.session.execute(text("""
            SELECT 
                sa.name as account_name,
                t.status,
                COUNT(t.id) as count,
                SUM(t.amount) as total
            FROM stripe_account sa
            LEFT JOIN "transaction" t ON sa.id = t.account_id
            WHERE sa.is_active = 1
            GROUP BY sa.name, t.status
            ORDER BY sa.name, t.status
        """)).fetchall()
        
        # Process data
        accounts = {}
        for row in results:
            account_name = row[0]
            status = row[1]
            count = row[2] or 0
            total = row[3] or 0
            
            if account_name not in accounts:
                accounts[account_name] = {}
            
            if status:  # Only add if status is not None
                accounts[account_name][status] = {
                    'count': count,
                    'amount': total / 100
                }
        
        # Generate HTML
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Analytics - Simple View</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    background: #f8fafc; line-height: 1.6; color: #334155;
                }
                .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                .header { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                    margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }
                .navigation {
                    display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                    background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    flex-wrap: wrap;
                }
                .nav-link {
                    padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                    border-radius: 8px; transition: all 0.2s; font-weight: 500;
                }
                .nav-link:hover { background: #4338ca; transform: translateY(-1px); }
                .account { 
                    background: white; margin: 20px 0; padding: 24px; border-radius: 12px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #4f46e5;
                }
                .account h3 { 
                    color: #1e293b; margin: 0 0 16px 0; font-size: 1.4rem; 
                    display: flex; align-items: center; gap: 8px;
                }
                .status { 
                    margin: 10px 0; padding: 12px 16px; background: #f8fafc; border-radius: 8px; 
                    display: flex; justify-content: space-between; align-items: center;
                    border: 1px solid #e2e8f0;
                }
                .status.succeeded { background: #dcfce7; border-color: #22c55e; color: #166534; }
                .status.failed { background: #fef2f2; border-color: #ef4444; color: #991b1b; }
                .status.canceled { background: #f1f5f9; border-color: #64748b; color: #475569; }
                .status.pending { background: #fef3c7; border-color: #f59e0b; color: #92400e; }
                .total { 
                    font-weight: 600; background: #ecfdf5; border: 2px solid #10b981; 
                    margin-top: 16px; font-size: 1.1rem;
                }
                .grand-total { 
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    color: white; text-align: center; padding: 24px; border-radius: 12px; 
                    margin-top: 24px; font-size: 1.6rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }
                .refresh-btn {
                    background: #4f46e5; color: white; border: none; padding: 8px 16px;
                    border-radius: 6px; cursor: pointer; margin-left: 12px; transition: background 0.2s;
                }
                .refresh-btn:hover { background: #4338ca; }
                @media (max-width: 768px) {
                    .container { padding: 10px; }
                    .header { padding: 1.5rem; }
                    .navigation { flex-direction: column; align-items: center; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💳 Payment Analytics - Simple View</h1>
                    <p>Real-time transaction data across all Stripe accounts</p>
                    <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
                </div>
                
                <div class="navigation">
                    <a href="/" class="nav-link">🏠 Home</a>
                    <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                    <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                    <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
                    <a href="/analytics/summary" class="nav-link">📈 Summary</a>
                </div>
        '''
        
        # Generate HTML for each account
        grand_total = 0
        total_transactions = 0
        
        if not accounts:
            html += '''
            <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                <h3 style="color: #64748b; margin-bottom: 16px;">📊 No Transaction Data Found</h3>
                <p style="color: #64748b;">No transactions have been synced yet.</p>
                <p style="margin-top: 16px;"><a href="/" style="color: #4f46e5;">← Return to Home</a></p>
            </div>
            '''
        else:
            for account_name, statuses in accounts.items():
                html += f'<div class="account"><h3>🏢 {account_name}</h3>'
                
                account_total = 0
                account_count = 0
                
                for status, data in statuses.items():
                    amount = data['amount'];
                    count = data['count'] or 0;
                    account_total += amount
                    account_count += count
                    
                    html += f'''
                    <div class="status {status}">
                        <span><strong>{status.upper()}</strong>: {count:,} transactions</span>
                        <span><strong>HK${amount:,.2f}</strong></span>
                    </div>
                    '''
                
                html += f'''
                <div class="status total">
                    <span><strong>ACCOUNT TOTAL</strong>: {account_count:,} transactions</span>
                    <span><strong>HK${account_total:,.2f}</strong></span>
                </div>
                </div>
                '''
                
                grand_total += account_total
                total_transactions += account_count
            
            html += f'''
                    <div class="grand-total">
                        � GRAND TOTAL: {total_transactions:,} transactions | HK${grand_total:,.2f}
                    </div>
            '''
        
        html += '''
                </div>
                <script>
                    // Auto-refresh every 5 minutes
                    setTimeout(() => location.reload(), 300000);
                </script>
            </body>
            </html>
        '''
        
        return html
        
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Simple View Error</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #fef2f2; }}
                .error {{ background: white; padding: 30px; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .error h1 {{ color: #dc2626; margin-bottom: 16px; }}
                .error-details {{ background: #f9fafb; padding: 16px; border-radius: 6px; margin: 16px 0; }}
                .nav {{ margin-top: 20px; }}
                .nav a {{ margin-right: 15px; color: #4f46e5; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Simple View Error</h1>
                <p>There was an error loading the simple analytics view.</p>
                <div class="error-details">
                    <strong>Error details:</strong><br>
                    {str(e)}
                </div>
                <div class="nav">
                    <a href="/">← Back to Home</a>
                    <a href="/analytics/api/account-amounts">🔗 Try API Data</a>
                    <a href="/analytics/summary">📈 Try Summary</a>
                </div>
            </div>
        </body>
        </html>
        '''

@analytics_bp.route('/dashboard')
def dashboard():
    """Interactive analytics dashboard with charts"""
    try:
        # Get comprehensive account data including fees
        results = db.session.execute(text("""
            SELECT 
                sa.name as account_name,
                t.status,
                t.type,
                COUNT(t.id) as count,
                SUM(t.amount) as total,
                SUM(COALESCE(t.fee, 0)) as fees
            FROM stripe_account sa
            LEFT JOIN "transaction" t ON sa.id = t.account_id
            WHERE sa.is_active = 1
            GROUP BY sa.name, t.status, t.type
            ORDER BY sa.name, t.status, t.type
        """)).fetchall()
        
        # Process data for charts
        accounts_data = {}
        for row in results:
            account_name, status, tx_type, count, total, fees = row
            if account_name not in accounts_data:
                accounts_data[account_name] = {
                    'name': account_name,
                    'total_amount': 0,
                    'total_fees': 0,
                    'net_amount': 0,
                    'total_count': 0,
                    'statuses': {},
                    'types': {}
                }
            
            if status and tx_type and count:  # Only process valid data
                amount = (total or 0) / 100
                fee_amount = (fees or 0) / 100
                net_amount = amount - fee_amount
                
                accounts_data[account_name]['total_amount'] += amount
                accounts_data[account_name]['total_fees'] += fee_amount
                accounts_data[account_name]['net_amount'] += net_amount
                accounts_data[account_name]['total_count'] += count
                
                # Group by status
                if status not in accounts_data[account_name]['statuses']:
                    accounts_data[account_name]['statuses'][status] = {'count': 0, 'amount': 0, 'fees': 0, 'net': 0}
                accounts_data[account_name]['statuses'][status]['count'] += count
                accounts_data[account_name]['statuses'][status]['amount'] += amount
                accounts_data[account_name]['statuses'][status]['fees'] += fee_amount
                accounts_data[account_name]['statuses'][status]['net'] += net_amount
                
                # Group by type
                if tx_type not in accounts_data[account_name]['types']:
                    accounts_data[account_name]['types'][tx_type] = {'count': 0, 'amount': 0, 'fees': 0, 'net': 0}
                accounts_data[account_name]['types'][tx_type]['count'] += count
                accounts_data[account_name]['types'][tx_type]['amount'] += amount
                accounts_data[account_name]['types'][tx_type]['fees'] += fee_amount
                accounts_data[account_name]['types'][tx_type]['net'] += net_amount
        
        # Create JSON data for charts
        chart_data = json.dumps(list(accounts_data.values()))
        
        # Calculate totals
        total_amount = sum(acc['total_amount'] for acc in accounts_data.values())
        total_fees = sum(acc['total_fees'] for acc in accounts_data.values())
        net_amount = sum(acc['net_amount'] for acc in accounts_data.values())
        total_transactions = sum(acc['total_count'] for acc in accounts_data.values())
        total_accounts = len(accounts_data)
        avg_transaction = total_amount / total_transactions if total_transactions > 0 else 0
        fee_percentage = (total_fees / total_amount * 100) if total_amount > 0 else 0
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stripe Analytics Dashboard</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    background: #f8fafc; line-height: 1.6; color: #334155;
                }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                    margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
                .header p {{ font-size: 1.1rem; opacity: 0.9; }}
                .navigation {{
                    display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                    background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    flex-wrap: wrap;
                }}
                .nav-link {{
                    padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                    border-radius: 8px; transition: all 0.2s; font-weight: 500;
                }}
                .nav-link:hover {{ background: #4338ca; transform: translateY(-1px); }}
                .stats-grid {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px; margin-bottom: 30px;
                }}
                .stat-card {{
                    background: white; padding: 24px; border-radius: 12px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08); text-align: center;
                    border-left: 4px solid #4f46e5;
                }}
                .stat-number {{ 
                    font-size: 2.5rem; font-weight: bold; color: #1e293b; margin-bottom: 8px;
                }}
                .stat-label {{ color: #64748b; font-size: 1rem; font-weight: 500; }}
                .charts-section {{ margin-bottom: 30px; }}
                .charts-grid {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); 
                    gap: 30px;
                }}
                .chart-container {{
                    background: white; padding: 24px; border-radius: 12px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08); height: 400px;
                }}
                .chart-title {{ 
                    font-size: 1.3rem; font-weight: bold; margin-bottom: 20px; 
                    color: #1e293b; text-align: center;
                }}
                .chart-canvas {{ position: relative; height: 300px; width: 100%; }}
                .account-details {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                    gap: 20px; margin-top: 30px;
                }}
                .account-card {{
                    background: white; padding: 24px; border-radius: 12px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #4f46e5;
                }}
                .account-name {{ 
                    font-size: 1.4rem; font-weight: bold; margin-bottom: 16px; 
                    color: #1e293b; display: flex; align-items: center; gap: 8px;
                }}
                .detail-item {{
                    display: flex; justify-content: space-between; padding: 12px 0;
                    border-bottom: 1px solid #f1f5f9; align-items: center;
                }}
                .detail-item:last-child {{ border-bottom: none; }}
                .detail-label {{ color: #64748b; font-weight: 500; }}
                .detail-value {{ font-weight: 600; color: #1e293b; }}
                .status-badge {{
                    padding: 4px 8px; border-radius: 4px; font-size: 0.875rem; font-weight: 500;
                }}
                .status-succeeded {{ background: #dcfce7; color: #166534; }}
                .status-failed {{ background: #fef2f2; color: #991b1b; }}
                .status-canceled {{ background: #f1f5f9; color: #475569; }}
                .status-pending {{ background: #fef3c7; color: #92400e; }}
                @media (max-width: 768px) {{
                    .container {{ padding: 10px; }}
                    .header {{ padding: 1.5rem; }}
                    .header h1 {{ font-size: 2rem; }}
                    .charts-grid {{ grid-template-columns: 1fr; }}
                    .account-details {{ grid-template-columns: 1fr; }}
                    .navigation {{ flex-direction: column; align-items: center; }}
                    .chart-container {{ height: 350px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Stripe Analytics Dashboard</h1>
                    <p>Real-time transaction analytics and insights</p>
                </div>
                
                <div class="navigation">
                    <a href="/" class="nav-link">🏠 Home</a>
                    <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                    <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                    <a href="/analytics/statement-generator" class="nav-link">📄 Statement Generator</a>
                    <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
                    <a href="/analytics/summary" class="nav-link">📈 Summary</a>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total_accounts}</div>
                        <div class="stat-label">Active Accounts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{total_transactions:,}</div>
                        <div class="stat-label">Total Transactions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">HK${total_amount:,.0f}</div>
                        <div class="stat-label">Total Revenue</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">HK${avg_transaction:,.0f}</div>
                        <div class="stat-label">Avg Transaction</div>
                    </div>
                </div>
                
                <div class="charts-section">
                    <div class="charts-grid">
                        <div class="chart-container">
                            <div class="chart-title">Revenue by Account</div>
                            <div class="chart-canvas">
                                <canvas id="revenueChart"></canvas>
                            </div>
                        </div>
                        <div class="chart-container">
                            <div class="chart-title">Transaction Count by Account</div>
                            <div class="chart-canvas">
                                <canvas id="transactionChart"></canvas>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="account-details">
        '''
        
        # Account details
        for account_name, data in accounts_data.items():
            html += f'''
            <div class="account-card">
                <div class="account-name">🏢 {account_name}</div>
                <div class="detail-item">
                    <span class="detail-label">Total Revenue:</span>
                    <span class="detail-value">HK${data['total_amount']:,.2f}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Total Transactions:</span>
                    <span class="detail-value">{data['total_count']:,}</span>
                </div>
            '''
            
            # Show status breakdown
            for status, status_data in data['statuses'].items():
                html += f'''
                <div class="detail-item">
                    <span class="detail-label">
                        <span class="status-badge status-{status}">{status.title()}</span>
                    </span>
                    <span class="detail-value">{status_data['count']} (HK${status_data['amount']:,.2f})</span>
                </div>
                '''
            
            html += '</div>'
        
        if not accounts_data:
            html += '''
            <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                <h3 style="color: #64748b; margin-bottom: 16px;">📊 No Data Available</h3>
                <p style="color: #64748b;">No transaction data found. Please sync your Stripe data first.</p>
                <p style="margin-top: 16px;"><a href="/" style="color: #4f46e5;">← Return to Home</a></p>
            </div>
            '''
        
        html += f'''
                </div>
            </div>
            
            <script>
                Chart.defaults.responsive = true;
                Chart.defaults.maintainAspectRatio = false;
                
                const accountsData = {chart_data};
                
                // Only create charts if we have data
                if (accountsData.length > 0) {{
                    // Revenue Chart
                    const revenueCtx = document.getElementById('revenueChart').getContext('2d');
                    new Chart(revenueCtx, {{
                        type: 'doughnut',
                        data: {{
                            labels: accountsData.map(acc => acc.name),
                            datasets: [{{
                                data: accountsData.map(acc => acc.total_amount),
                                backgroundColor: [
                                    '#4f46e5', '#06b6d4', '#10b981', '#f59e0b', 
                                    '#ef4444', '#8b5cf6', '#f97316'
                                ],
                                borderWidth: 3,
                                borderColor: '#fff',
                                hoverBorderWidth: 4
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{
                                        padding: 20,
                                        usePointStyle: true,
                                        font: {{ size: 12 }}
                                    }}
                                }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            const label = context.label || '';
                                            const value = context.parsed;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = ((value / total) * 100).toFixed(1);
                                            return `${{label}}: HK${{value.toLocaleString()}} (${{percentage}}%)`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                    
                    // Transaction Count Chart
                    const transactionCtx = document.getElementById('transactionChart').getContext('2d');
                    new Chart(transactionCtx, {{
                        type: 'bar',
                        data: {{
                            labels: accountsData.map(acc => acc.name),
                            datasets: [{{
                                label: 'Transactions',
                                data: accountsData.map(acc => acc.total_count),
                                backgroundColor: '#4f46e5',
                                borderColor: '#4338ca',
                                borderWidth: 2,
                                borderRadius: 6,
                                borderSkipped: false,
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    grid: {{ color: '#f1f5f9' }},
                                    ticks: {{ font: {{ size: 12 }} }}
                                }},
                                x: {{
                                    grid: {{ display: false }},
                                    ticks: {{ font: {{ size: 12 }} }}
                                }}
                            }},
                            plugins: {{
                                legend: {{ display: false }},
                                tooltip: {{
                                    callbacks: {{
                                        label: function(context) {{
                                            return `Transactions: ${{context.parsed.y.toLocaleString()}}`;
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }});
                }} else {{
                    // Show message if no data
                    document.getElementById('revenueChart').style.display = 'none';
                    document.getElementById('transactionChart').style.display = 'none';
                }}
                
                // Auto-refresh every 5 minutes
                setTimeout(() => location.reload(), 300000);
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Dashboard Error</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #fef2f2; }}
                .error {{ background: white; padding: 30px; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .error h1 {{ color: #dc2626; margin-bottom: 16px; }}
                .error-details {{ background: #f9fafb; padding: 16px; border-radius: 6px; margin: 16px 0; }}
                .nav {{ margin-top: 20px; }}
                .nav a {{ margin-right: 15px; color: #4f46e5; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Dashboard Error</h1>
                <p>There was an error loading the analytics dashboard.</p>
                <div class="error-details">
                    <strong>Error details:</strong><br>
                    {str(e)}
                </div>
                <div class="nav">
                    <a href="/">← Back to Home</a>
                    <a href="/analytics/simple">📋 Try Simple View</a>
                    <a href="/analytics/summary">📈 Try Summary</a>
                </div>
            </div>
        </body>
        </html>
        '''

@analytics_bp.route('/statement-generator')
def statement_generator():
    """Interactive statement generator with company and period selection"""
    try:
        # Get companies from CSV data
        csv_service = CSVTransactionService()
        companies = csv_service.get_available_companies()
        
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bank Statement Generator</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    background: #f8fafc; line-height: 1.6; color: #334155;
                }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                    margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .navigation {{
                    display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                    background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                    flex-wrap: wrap;
                }}
                .nav-link {{
                    padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                    border-radius: 8px; transition: all 0.2s; font-weight: 500;
                }}
                .nav-link:hover {{ background: #4338ca; transform: translateY(-1px); }}
                .form-container {{
                    background: white; padding: 32px; border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 24px;
                }}
                .form-grid {{
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 24px; margin-bottom: 24px;
                }}
                .form-group {{ display: flex; flex-direction: column; gap: 8px; }}
                .form-label {{ font-weight: 600; color: #374151; font-size: 0.95rem; }}
                .form-select, .form-input {{
                    padding: 12px 16px; border: 2px solid #e5e7eb; border-radius: 8px;
                    font-size: 1rem; transition: border-color 0.2s;
                }}
                .form-select:focus, .form-input:focus {{
                    outline: none; border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
                }}
                .btn-group {{
                    display: flex; gap: 12px; justify-content: center; margin-top: 24px;
                    flex-wrap: wrap;
                }}
                .btn {{
                    padding: 14px 28px; border: none; border-radius: 8px; cursor: pointer;
                    font-weight: 600; font-size: 1rem; transition: all 0.2s;
                    display: flex; align-items: center; gap: 8px;
                }}
                .btn-primary {{ background: #4f46e5; color: white; }}
                .btn-primary:hover {{ background: #4338ca; transform: translateY(-1px); }}
                .btn-secondary {{ background: #6b7280; color: white; }}
                .btn-secondary:hover {{ background: #4b5563; }}
                .info-card {{
                    background: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px;
                    padding: 20px; margin-bottom: 24px; color: #0c4a6e;
                }}
                @media (max-width: 768px) {{
                    .container {{ padding: 10px; }}
                    .header {{ padding: 1.5rem; }}
                    .navigation {{ flex-direction: column; align-items: center; }}
                    .form-grid {{ grid-template-columns: 1fr; }}
                    .btn-group {{ flex-direction: column; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📄 Bank Statement Generator</h1>
                    <p>Generate detailed bank statements with company and period filters</p>
                </div>
                
                <div class="navigation">
                    <a href="/" class="nav-link">🏠 Home</a>
                    <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                    <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                    <a href="/analytics/statement-generator" class="nav-link">📄 Statement Generator</a>
                    <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
                    <a href="/analytics/summary" class="nav-link">📈 Summary</a>
                </div>
                
                <div class="info-card">
                    <h3>📋 Statement Generator</h3>
                    <p>Use the form below to generate customized bank statements. Select a company, time period, and format to create detailed financial reports.</p>
                    <p style="margin-top: 10px;"><strong>Available Companies:</strong> {len(companies)} companies loaded from CSV</p>
                </div>
                
                <div style="background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                    <h3 style="margin-bottom: 16px; color: #1e293b;">🏢 Available Companies ({len(companies)})</h3>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 12px;">
        '''
        
        # Add company list
        for company in companies:
            html += f'''
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                            <span style="font-weight: 600; color: #1e293b;">🏢 {company['name']}</span>
                            <span style="color: #64748b; font-size: 0.9rem;">ID: {company['id']}</span>
                        </div>
            '''
        
        html += '''
                    </div>
                </div>
                
                <div class="form-container">
                    <h2 style="margin-bottom: 24px; color: #1e293b;">📋 Statement Configuration</h2>
                    
                    <div class="form-grid">
                        <div class="form-group">
                            <label class="form-label">🏢 Select Company</label>
                            <select class="form-select" id="company" name="company">
                                <option value="">Choose a company...</option>
                                <option value="all">📊 All Companies</option>
        '''
        
        # Add company options
        for company in companies:
            html += f'<option value="{company["id"]}">🏢 {company["name"]}</option>'
        
        html += '''
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">📅 Select Period</label>
                            <select class="form-select" id="period" name="period" onchange="toggleCustomPeriod()">
                                <option value="">Choose period...</option>
                                <option value="7">📅 Last 7 days</option>
                                <option value="30">📅 Last 30 days</option>
                                <option value="90">📅 Last 3 months</option>
                                <option value="365">📅 Last year</option>
                                <option value="2000">📅 All time (last 2000 days)</option>
                                <option value="custom">🗓️ Custom Period</option>
                                <option value="preset-nov2021">📅 November 2021</option>
                                <option value="preset-2021">📅 All of 2021</option>
                            </select>
                        </div>
                        
                        <div class="form-group" id="customPeriodGroup" style="display: none;">
                            <label class="form-label">📅 Custom Date Range</label>
                            <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                                <div style="flex: 1; min-width: 120px;">
                                    <label style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px; display: block;">From Date</label>
                                    <input type="date" class="form-input" id="fromDate" name="fromDate" style="width: 100%;">
                                </div>
                                <div style="flex: 1; min-width: 120px;">
                                    <label style="font-size: 0.85rem; color: #6b7280; margin-bottom: 4px; display: block;">To Date</label>
                                    <input type="date" class="form-input" id="toDate" name="toDate" style="width: 100%;">
                                </div>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">📊 Transaction Status</label>
                            <select class="form-select" id="status" name="status">
                                <option value="all">📊 All Statuses</option>
                                <option value="succeeded">✅ Successful only</option>
                                <option value="failed">❌ Failed only</option>
                                <option value="pending">⏳ Pending only</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label class="form-label">📋 Output Format</label>
                            <select class="form-select" id="format" name="format">
                                <option value="detailed">📄 Detailed Statement</option>
                                <option value="summary">📊 Summary Only</option>
                                <option value="csv">📊 CSV Export</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="btn-group">
                        <button type="button" class="btn btn-primary" onclick="generateStatement()">
                            📄 Generate Statement
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="window.location.href='/analytics/summary'">
                            📈 View Summary Instead
                        </button>
                    </div>
                </div>
                
                <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                    <h3 style="color: #64748b; margin-bottom: 16px;">� Statement Generation</h3>
                    <p style="color: #64748b;">Select your options above and click "Generate Statement" to create a custom report.</p>
                    <div style="margin-top: 20px;">
                        <a href="/analytics/dashboard" style="margin-right: 15px; color: #4f46e5; text-decoration: none;">📊 Dashboard</a>
                        <a href="/analytics/simple" style="margin-right: 15px; color: #4f46e5; text-decoration: none;">📋 Simple View</a>
                        <a href="/analytics/summary" style="color: #4f46e5; text-decoration: none;">📈 Summary</a>
                    </div>
                </div>
            </div>
            
            <script>
                function toggleCustomPeriod() {
                    const periodSelect = document.getElementById('period');
                    const customGroup = document.getElementById('customPeriodGroup');
                    
                    if (periodSelect.value === 'custom') {
                        customGroup.style.display = 'block';
                        // Set default dates (last 30 days)
                        const today = new Date();
                        const thirtyDaysAgo = new Date();
                        thirtyDaysAgo.setDate(today.getDate() - 30);
                        
                        document.getElementById('toDate').value = today.toISOString().split('T')[0];
                        document.getElementById('fromDate').value = thirtyDaysAgo.toISOString().split('T')[0];
                    } else if (periodSelect.value === 'preset-nov2021') {
                        customGroup.style.display = 'block';
                        document.getElementById('fromDate').value = '2021-11-01';
                        document.getElementById('toDate').value = '2021-11-30';
                    } else if (periodSelect.value === 'preset-2021') {
                        customGroup.style.display = 'block';
                        document.getElementById('fromDate').value = '2021-01-01';
                        document.getElementById('toDate').value = '2021-12-31';
                    } else {
                        customGroup.style.display = 'none';
                    }
                }
                
                function generateStatement() {
                    const company = document.getElementById('company').value;
                    const period = document.getElementById('period').value;
                    const status = document.getElementById('status').value;
                    const format = document.getElementById('format').value;
                    
                    if (!company || !period) {
                        alert('Please select both a company and time period.');
                        return;
                    }
                    
                    // Validate custom period if selected
                    if (period === 'custom' || period === 'preset-nov2021' || period === 'preset-2021') {
                        const fromDate = document.getElementById('fromDate').value;
                        const toDate = document.getElementById('toDate').value;
                        
                        if (!fromDate || !toDate) {
                            alert('Please select both start and end dates for the custom period.');
                            return;
                        }
                        
                        if (new Date(fromDate) > new Date(toDate)) {
                            alert('The start date must be before the end date.');
                            return;
                        }
                        
                        // Calculate the number of days for custom period
                        const daysDiff = Math.ceil((new Date(toDate) - new Date(fromDate)) / (1000 * 60 * 60 * 24));
                        if (daysDiff > 1000) {
                            if (!confirm(`You've selected a ${daysDiff}-day period. Large date ranges may take longer to process. Continue?`)) {
                                return;
                            }
                        }
                    }
                    
                    // Show loading state
                    const generateBtn = document.querySelector('.btn-primary');
                    const originalText = generateBtn.innerHTML;
                    generateBtn.innerHTML = '⏳ Generating Statement...';
                    generateBtn.disabled = true;
                    
                    // Build the proper statement generation URL
                    let url = '/analytics/statement-generator/generate';
                    let params = new URLSearchParams();
                    
                    if (company !== 'all') {
                        params.append('company', company);
                    }
                    if (status !== 'all') {
                        params.append('status', status);
                    }
                    params.append('format', format);
                    
                    // Add period parameters
                    if (period === 'custom' || period === 'preset-nov2021' || period === 'preset-2021') {
                        const fromDate = document.getElementById('fromDate').value;
                        const toDate = document.getElementById('toDate').value;
                        params.append('from_date', fromDate);
                        params.append('to_date', toDate);
                    } else {
                        params.append('period', period);
                    }
                    
                    // Add parameters to URL
                    if (params.toString()) {
                        url += '?' + params.toString();
                    }
                    
                    // Redirect to the statement generation endpoint
                    window.location.href = url;
                }
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Statement Generator Error</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #fef2f2; }}
                .error {{ background: white; padding: 30px; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .error h1 {{ color: #dc2626; margin-bottom: 16px; }}
                .error-details {{ background: #f9fafb; padding: 16px; border-radius: 6px; margin: 16px 0; }}
                .nav {{ margin-top: 20px; }}
                .nav a {{ margin-right: 15px; color: #4f46e5; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Statement Generator Error</h1>
                <p>There was an error loading the statement generator.</p>
                <div class="error-details">
                    <strong>Error details:</strong><br>
                    {str(e)}
                </div>
                <div class="nav">
                    <a href="/">← Back to Home</a>
                    <a href="/analytics/simple">📋 Try Simple View</a>
                    <a href="/analytics/summary">📈 Try Summary</a>
                </div>
            </div>
        </body>
        </html>
        '''

def get_transactions_from_database(company_filter=None, status_filter=None, from_date=None, to_date=None, period=None):
    """Get transactions from database with filtering"""
    from datetime import datetime, timedelta
    
    # Handle period parameter
    if period and period.isdigit():
        days = int(period)
        to_date = datetime.now().date()
        from_date = to_date - timedelta(days=days)
    elif period == 'preset-nov2021':
        from_date = datetime(2021, 11, 1).date()
        to_date = datetime(2021, 11, 30).date()
    elif period == 'preset-2021':
        from_date = datetime(2021, 1, 1).date()
        to_date = datetime(2021, 12, 31).date()
    else:
        # Convert string dates to date objects
        if from_date and isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if to_date and isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    
    # Build database query
    query = db.session.query(
        Transaction.stripe_id,
        Transaction.amount,
        Transaction.fee,
        Transaction.currency,
        Transaction.status,
        Transaction.type,
        Transaction.stripe_created,
        Transaction.customer_email,
        Transaction.description,
        StripeAccount.name.label('company_name')
    ).join(StripeAccount)
    
    # Apply filters
    if company_filter:
        # Handle different company filter formats
        if company_filter.lower() == 'cgge':
            query = query.filter(StripeAccount.name == 'CGGE')
        elif company_filter.lower() in ['krystal_institute', 'ki']:
            query = query.filter(StripeAccount.name == 'Krystal Institute')
        elif company_filter.lower() in ['krystal_technology', 'kt']:
            query = query.filter(StripeAccount.name == 'Krystal Technology')
    
    # Date filtering
    if from_date:
        from_datetime = datetime.combine(from_date, datetime.min.time())
        query = query.filter(Transaction.stripe_created >= from_datetime)
    
    if to_date:
        to_datetime = datetime.combine(to_date, datetime.max.time())
        query = query.filter(Transaction.stripe_created <= to_datetime)
    
    # Status filtering
    if status_filter and status_filter != 'all':
        if status_filter.lower() in ['successful', 'succeeded', 'paid']:
            query = query.filter(Transaction.status.in_(['Paid', 'succeeded', 'paid']))
        elif status_filter.lower() in ['failed', 'canceled']:
            query = query.filter(Transaction.status.in_(['Failed', 'canceled', 'failed']))
    
    # Execute query and format results
    results = query.order_by(Transaction.stripe_created.desc()).all()
    
    transactions = []
    currency_totals = {}  # Track currency breakdowns
    
    for row in results:
        # Convert amount from cents to dollars for display
        amount_formatted = row.amount / 100.0 if row.amount else 0.0
        fee_formatted = row.fee / 100.0 if row.fee else 0.0
        currency = (row.currency or 'USD').upper()
        
        # Track currency totals
        if currency not in currency_totals:
            currency_totals[currency] = {
                'count': 0,
                'amount': 0.0,
                'fees': 0.0,
                'net': 0.0
            }
        
        # Only count successful transactions in totals
        if row.status and row.status.lower() in ['paid', 'succeeded']:
            currency_totals[currency]['count'] += 1
            currency_totals[currency]['amount'] += amount_formatted
            currency_totals[currency]['fees'] += fee_formatted
            currency_totals[currency]['net'] += (amount_formatted - fee_formatted)
        
        transaction = {
            'id': row.stripe_id,
            'account_name': row.company_name,
            'amount': amount_formatted,
            'fee': fee_formatted,
            'currency': currency,
            'status': row.status or 'Unknown',
            'type': row.type or 'charge',
            'stripe_created': row.stripe_created,
            'customer_email': row.customer_email or '',
            'description': row.description or '',
            # Additional fields for compatibility with CSV format
            'amount_refunded': 0.0,
            'converted_amount': amount_formatted,
            'converted_currency': currency,
            'net_amount': amount_formatted - fee_formatted
        }
        transactions.append(transaction)
    
    # Add currency breakdown to the first transaction for easy access in templates
    if transactions:
        transactions[0]['currency_breakdown'] = currency_totals
    
    return transactions

@analytics_bp.route('/statement-generator/generate')
def generate_statement():
    """Generate statement based on form parameters"""
    try:
        # Get parameters from request
        company_id = request.args.get('company')
        status_filter = request.args.get('status', 'all')
        format_type = request.args.get('format', 'detailed')
        period = request.args.get('period')
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        # Debug logging
        print(f"Statement generation params: company={company_id}, status={status_filter}, format={format_type}, period={period}, from={from_date}, to={to_date}")
        
        # Get transactions from database instead of CSV
        transactions = get_transactions_from_database(
            company_filter=company_id,
            status_filter=status_filter,
            from_date=from_date,
            to_date=to_date,
            period=period
        )
        
        # Calculate totals and status counts
        total_amount = 0
        total_fees = 0
        status_counts = {}
        
        for tx in transactions:
            amount_hkd = tx['amount']
            fee_hkd = tx['fee']
            
            total_amount += amount_hkd
            total_fees += fee_hkd
            
            # Count statuses
            status_counts[tx['status']] = status_counts.get(tx['status'], 0) + 1
        
        # Generate different formats
        if format_type == 'csv':
            return generate_csv_statement(transactions)
        elif format_type == 'summary':
            return generate_summary_statement(transactions, status_counts, total_amount, total_fees)
        else:
            return generate_detailed_statement(transactions, status_counts, total_amount, total_fees, {
                'company_id': company_id,
                'status_filter': status_filter,
                'period': period,
                'from_date': from_date,
                'to_date': to_date
            })
            
    except Exception as e:
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Statement Generation Error</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; background: #fef2f2; }}
                .error {{ background: white; padding: 30px; border-radius: 8px; border-left: 4px solid #ef4444; }}
                .error h1 {{ color: #dc2626; margin-bottom: 16px; }}
                .error-details {{ background: #f9fafb; padding: 16px; border-radius: 6px; margin: 16px 0; }}
                .nav {{ margin-top: 20px; }}
                .nav a {{ margin-right: 15px; color: #4f46e5; text-decoration: none; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>❌ Statement Generation Error</h1>
                <p>There was an error generating your statement.</p>
                <div class="error-details">
                    <strong>Error details:</strong><br>
                    {str(e)}
                </div>
                <div class="nav">
                    <a href="/analytics/statement-generator">← Back to Statement Generator</a>
                    <a href="/analytics/dashboard">📊 Dashboard</a>
                    <a href="/analytics/summary">📈 Summary</a>
                </div>
            </div>
        </body>
        </html>
        '''

def generate_detailed_statement(transactions, status_counts, total_amount, total_fees, filters):
    """Generate detailed HTML statement optimized for landscape printing"""
    # Format date range for display
    date_range = "All Time"
    if filters['period'] and filters['period'] not in ['custom', 'preset-nov2021', 'preset-2021']:
        date_range = f"Last {filters['period']} days"
    elif filters['from_date'] and filters['to_date']:
        date_range = f"{filters['from_date']} to {filters['to_date']}"
    
    # Get company name from CSV service
    company_name = "All Companies"
    if filters['company_id'] and filters['company_id'] != 'all':
        csv_service = CSVTransactionService()
        companies = csv_service.get_available_companies()
        for company in companies:
            if str(company['id']) == str(filters['company_id']):
                company_name = company['name']
                break
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bank Statement - {company_name}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: #f8fafc; line-height: 1.4; color: #334155; padding: 20px;
            }}
            .container {{ max-width: 1600px; margin: 0 auto; }}
            
            /* Print-specific styles for landscape orientation */
            @media print {{
                @page {{
                    size: A4 landscape;
                    margin: 0.5in;
                }}
                body {{
                    background: white !important;
                    color: black !important;
                    font-size: 11px;
                    line-height: 1.3;
                    padding: 0 !important;
                }}
                .container {{
                    max-width: none !important;
                    margin: 0 !important;
                }}
                .no-print {{
                    display: none !important;
                }}
                .header {{
                    background: #f8f9fa !important;
                    color: #000 !important;
                    padding: 15px !important;
                    margin-bottom: 15px !important;
                    border: 2px solid #000 !important;
                    box-shadow: none !important;
                }}
                .print-header {{
                    display: flex !important;
                    justify-content: space-between !important;
                    align-items: center !important;
                    margin-bottom: 10px !important;
                    padding-bottom: 10px !important;
                    border-bottom: 1px solid #000 !important;
                }}
                .company-logo {{
                    font-size: 18px !important;
                    font-weight: bold !important;
                }}
                .statement-info {{
                    background: white !important;
                    border: 1px solid #000 !important;
                    margin-bottom: 15px !important;
                    box-shadow: none !important;
                    padding: 10px !important;
                }}
                .info-grid {{
                    display: grid !important;
                    grid-template-columns: repeat(4, 1fr) !important;
                    gap: 10px !important;
                }}
                .info-item {{
                    border-bottom: none !important;
                    padding: 5px 0 !important;
                }}
                .summary-cards {{
                    display: grid !important;
                    grid-template-columns: repeat(6, 1fr) !important;
                    gap: 10px !important;
                    margin-bottom: 15px !important;
                }}
                .summary-card {{
                    background: white !important;
                    border: 1px solid #000 !important;
                    padding: 8px !important;
                    text-align: center !important;
                    box-shadow: none !important;
                }}
                .summary-number {{
                    font-size: 14px !important;
                    color: #000 !important;
                }}
                .summary-label {{
                    font-size: 10px !important;
                    color: #000 !important;
                }}
                .transactions-table {{
                    background: white !important;
                    border: 1px solid #000 !important;
                    box-shadow: none !important;
                    margin-bottom: 0 !important;
                    page-break-inside: avoid;
                }}
                .table-header {{
                    background: #f8f9fa !important;
                    border-bottom: 2px solid #000 !important;
                    padding: 8px !important;
                    font-weight: bold !important;
                    color: #000 !important;
                }}
                table {{
                    width: 100% !important;
                    border-collapse: collapse !important;
                    font-size: 10px !important;
                }}
                th, td {{
                    padding: 4px 6px !important;
                    border: 1px solid #000 !important;
                    text-align: left !important;
                }}
                th {{
                    background: #f8f9fa !important;
                    font-weight: bold !important;
                    color: #000 !important;
                    font-size: 10px !important;
                }}
                .status-succeeded {{ color: #000 !important; }}
                .status-failed {{ color: #000 !important; }}
                .status-pending {{ color: #000 !important; }}
                .status-canceled {{ color: #000 !important; }}
                .amount-positive {{ color: #000 !important; font-weight: bold !important; }}
                .amount-negative {{ color: #000 !important; font-weight: bold !important; }}
                .amount-cell {{
                    text-align: right !important;
                    font-weight: bold !important;
                }}
                .date-cell {{
                    white-space: nowrap !important;
                    width: 80px !important;
                }}
                .company-cell {{
                    width: 100px !important;
                }}
                .description-cell {{
                    width: 200px !important;
                    word-wrap: break-word !important;
                }}
                .type-cell {{
                    width: 70px !important;
                }}
                .status-cell {{
                    width: 80px !important;
                }}
                .customer-cell {{
                    width: 150px !important;
                    word-wrap: break-word !important;
                }}
                .page-break {{
                    page-break-after: always !important;
                }}
                .row-even {{
                    background: #f8f9fa !important;
                }}
                .row-odd {{
                    background: white !important;
                }}
                .total-row {{
                    background: #e9ecef !important;
                    font-weight: bold !important;
                    border-top: 2px solid #000 !important;
                }}
            }}
            
            /* Screen styles */
            .header {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; text-align: center; border-radius: 12px; 
                margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
            .print-header {{
                display: none;
            }}
            .statement-info {{
                background: white; padding: 24px; border-radius: 12px; margin-bottom: 24px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #4f46e5;
            }}
            .info-grid {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;
            }}
            .info-item {{ display: flex; justify-content: space-between; padding: 8px 0; }}
            .info-label {{ font-weight: 600; color: #64748b; }}
            .info-value {{ font-weight: 600; color: #1e293b; }}
            .summary-cards {{
                display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px; margin-bottom: 24px;
            }}
            .summary-card {{
                background: white; padding: 20px; border-radius: 12px; text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); border-left: 4px solid #4f46e5;
            }}
            .summary-number {{ font-size: 1.8rem; font-weight: bold; color: #1e293b; margin-bottom: 8px; }}
            .summary-label {{ color: #64748b; font-weight: 500; }}
            .transactions-table {{
                background: white; border-radius: 12px; overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 24px;
            }}
            .table-header {{
                background: #f8fafc; padding: 16px; border-bottom: 1px solid #e5e7eb;
                font-weight: 600; color: #1e293b; display: flex; align-items: center; gap: 8px;
            }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #f1f5f9; }}
            th {{ background: #f8fafc; font-weight: 600; color: #374151; }}
            .status-succeeded {{ color: #059669; font-weight: 600; }}
            .status-failed {{ color: #dc2626; font-weight: 600; }}
            .status-pending {{ color: #d97706; font-weight: 600; }}
            .status-canceled {{ color: #6b7280; font-weight: 600; }}
            .amount-positive {{ color: #059669; font-weight: 600; }}
            .amount-negative {{ color: #dc2626; font-weight: 600; }}
            .amount-cell {{ text-align: right; font-weight: 600; }}
            .navigation {{
                display: flex; justify-content: center; gap: 15px; margin: 20px 0; padding: 20px;
                background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                flex-wrap: wrap;
            }}
            .nav-link {{
                padding: 12px 24px; background: #4f46e5; color: white; text-decoration: none;
                border-radius: 8px; transition: all 0.2s; font-weight: 500;
            }}
            .nav-link:hover {{ background: #4338ca; transform: translateY(-1px); }}
            .export-actions {{
                display: flex; gap: 12px; justify-content: center; margin-bottom: 24px;
                flex-wrap: wrap;
            }}
            .btn {{
                padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer;
                font-weight: 600; transition: all 0.2s; text-decoration: none;
                display: inline-flex; align-items: center; gap: 8px;
            }}
            .btn-primary {{ background: #4f46e5; color: white; }}
            .btn-primary:hover {{ background: #4338ca; }}
            .btn-secondary {{ background: #6b7280; color: white; }}
            .btn-secondary:hover {{ background: #4b5563; }}
            @media (max-width: 768px) {{
                .container {{ padding: 10px; }}
                .header {{ padding: 1.5rem; }}
                .navigation {{ flex-direction: column; align-items: center; }}
                .info-grid {{ grid-template-columns: 1fr; }}
                .summary-cards {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }}
                table {{ font-size: 0.9rem; }}
                th, td {{ padding: 8px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Print-specific header -->
            <div class="print-header">
                <div class="company-logo">🏦 {company_name}</div>
                <div style="text-align: right;">
                    <div style="font-size: 16px; font-weight: bold;">BANK STATEMENT</div>
                    <div style="font-size: 12px;">{date_range}</div>
                </div>
            </div>
            
            <!-- Screen header -->
            <div class="header no-print">
                <h1>📄 Bank Statement</h1>
                <p>Detailed transaction report for {company_name}</p>
            </div>
            
            <div class="navigation no-print">
                <a href="/analytics/statement-generator" class="nav-link">📄 New Statement</a>
                <a href="/analytics/dashboard" class="nav-link">📊 Dashboard</a>
                <a href="/analytics/summary" class="nav-link">📈 Summary</a>
                <a href="/" class="nav-link">🏠 Home</a>
            </div>
            
            <div class="statement-info">
                <h3 style="margin-bottom: 16px; color: #1e293b;">📋 Statement Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Company:</span>
                        <span class="info-value">{company_name}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Period:</span>
                        <span class="info-value">{date_range}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Status Filter:</span>
                        <span class="info-value">{filters['status_filter'].title() if filters['status_filter'] != 'all' else 'All Statuses'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Generated:</span>
                        <span class="info-value">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                    </div>
                </div>
            </div>
            
            <div class="summary-cards">
                <div class="summary-card">
                    <div class="summary-number">{len(transactions):,}</div>
                    <div class="summary-label">Total Transactions</div>
                </div>
                <div class="summary-card" style="border-left: 4px solid #059669;">
                    <div class="summary-number">HK${total_amount:,.2f}</div>
                    <div class="summary-label">Gross Income</div>
                </div>
                <div class="summary-card" style="border-left: 4px solid #f59e0b;">
                    <div class="summary-number">HK${total_fees:,.2f}</div>
                    <div class="summary-label">Processing Fees</div>
                </div>
                <div class="summary-card" style="border-left: 4px solid #10b981;">
                    <div class="summary-number">HK${(total_amount - total_fees):,.2f}</div>
                    <div class="summary-label">Net Income</div>
                </div>
                <div class="summary-card" style="border-left: 4px solid #8b5cf6;">
                    <div class="summary-number">{((total_fees / total_amount * 100) if total_amount > 0 else 0):.2f}%</div>
                    <div class="summary-label">Fee Rate</div>
                </div>
    '''
    
    # Add currency breakdown section
    currency_breakdown = transactions[0].get('currency_breakdown', {}) if transactions else {}
    if currency_breakdown:
        html += '''
            </div>
            
            <!-- Currency Breakdown Section -->
            <div class="statement-info" style="margin-bottom: 24px;">
                <h3 style="margin-bottom: 16px; color: #1e293b;">💱 Currency Breakdown</h3>
                <div class="summary-cards">
        '''
        
        for currency, data in currency_breakdown.items():
            if data['count'] > 0:  # Only show currencies with transactions
                html += f'''
                    <div class="summary-card" style="border-left: 4px solid #3b82f6;">
                        <div class="summary-number" style="font-size: 1.5rem;">{currency}</div>
                        <div class="summary-label">{data['count']} transactions</div>
                        <div style="font-size: 0.9rem; color: #64748b; margin-top: 4px;">
                            Amount: {currency} {data['amount']:,.2f}<br>
                            Fees: {currency} {data['fees']:,.2f}<br>
                            Net: {currency} {data['net']:,.2f}
                        </div>
                    </div>
                '''
        
        html += '''
            </div>
            
            <div class="summary-cards">
        '''
    
    # Add status breakdown cards
    for status, count in status_counts.items():
        html += f'''
                <div class="summary-card">
                    <div class="summary-number">{count:,}</div>
                    <div class="summary-label">{status.title()}</div>
                </div>
        '''
    
    html += '''
            </div>
            
            <!-- Charts Section -->
            <div class="charts-section no-print" style="margin-bottom: 24px;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px; margin-bottom: 24px;">
                    <!-- Income Breakdown Chart -->
                    <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <h3 style="margin-bottom: 16px; color: #1e293b; text-align: center;">💰 Income Breakdown</h3>
                        <div style="height: 300px; position: relative;">
                            <canvas id="incomeChart"></canvas>
                        </div>
                    </div>
                    
                    <!-- Transaction Status Chart -->
                    <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <h3 style="margin-bottom: 16px; color: #1e293b; text-align: center;">📊 Transaction Status</h3>
                        <div style="height: 300px; position: relative;">
                            <canvas id="statusChart"></canvas>
                        </div>
                    </div>
                </div>
                
                <!-- Monthly Trend Chart -->
                <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 24px;">
                    <h3 style="margin-bottom: 16px; color: #1e293b; text-align: center;">📈 Monthly Income & Fee Trend</h3>
                    <div style="height: 400px; position: relative;">
                        <canvas id="trendChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="export-actions no-print">
                <button class="btn btn-primary" onclick="window.print()">🖨️ Print Statement</button>
                <a href="#" class="btn btn-secondary" onclick="exportCSV()">📊 Export CSV</a>
                <button class="btn btn-secondary" onclick="optimizeForPrint()">📄 Optimize for Print</button>
            </div>
    '''
    
    if transactions:
        # Separate transactions into two tiers
        primary_transactions = []  # succeeded, refunded - real money movement
        secondary_transactions = []  # failed, canceled, etc. - no real money movement
        
        for tx in transactions:
            if tx['status'] in ['succeeded', 'refunded']:
                primary_transactions.append(tx)
            else:
                secondary_transactions.append(tx)
        
        html += '''
            <!-- Primary Transactions (Real Money Movement) -->
            <div class="transactions-table">
                <div class="table-header" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                    � Primary Transactions (Real Money Movement) - Succeeded & Refunded
                </div>
                <table>
                    <thead>
                        <tr>
                            <th class="date-cell">Date</th>
                            <th class="company-cell">Company</th>
                            <th class="description-cell">Description</th>
                            <th class="type-cell">Type</th>
                            <th class="status-cell">Status</th>
                            <th class="amount-cell">Gross (HKD)</th>
                            <th class="amount-cell">Fee (HKD)</th>
                            <th class="amount-cell">Net (HKD)</th>
                            <th class="customer-cell">Customer</th>
                        </tr>
                    </thead>
                    <tbody>
        '''
        
        # Primary transactions table
        primary_total = 0
        primary_fees = 0
        for i, tx in enumerate(primary_transactions):
            amount_class = "amount-positive" if tx['amount'] > 0 else "amount-negative"
            status_class = f"status-{tx['status']}"
            row_class = "row-even" if i % 2 == 0 else "row-odd"
            
            fee_amount = tx.get('fee', 0)
            net_amount = tx.get('net_amount', tx['amount'])
            
            primary_total += tx['amount']
            primary_fees += fee_amount
            
            # Truncate description for better print layout
            description = tx['description']
            if len(description) > 40:
                description = description[:37] + "..."
            
            # Truncate customer email for better print layout
            customer_email = tx['customer_email']
            if len(customer_email) > 25:
                customer_email = customer_email[:22] + "..."
            
            html += f'''
                        <tr class="{row_class}">
                            <td class="date-cell">{tx['stripe_created'].strftime('%Y-%m-%d %H:%M') if tx['stripe_created'] else 'N/A'}</td>
                            <td class="company-cell">{tx['account_name']}</td>
                            <td class="description-cell" title="{tx['description']}">{description}</td>
                            <td class="type-cell">{tx['type'] or 'N/A'}</td>
                            <td class="status-cell {status_class}">{tx['status'].title()}</td>
                            <td class="amount-cell {amount_class}">{tx['currency']} {tx['amount']:,.2f}</td>
                            <td class="amount-cell" style="color: #f59e0b; font-weight: 600;">{tx['currency']} {fee_amount:,.2f}</td>
                            <td class="amount-cell" style="color: #10b981; font-weight: 600;">{tx['currency']} {net_amount:,.2f}</td>
                            <td class="customer-cell" title="{tx['customer_email']}">{customer_email}</td>
                        </tr>
            '''
        
        if not primary_transactions:
            html += '''
                        <tr>
                            <td colspan="9" style="text-align: center; padding: 20px; color: #64748b; font-style: italic;">
                                No primary transactions (succeeded/refunded) found for this period.
                            </td>
                        </tr>
            '''
        else:
            # Add primary totals row
            primary_net = primary_total - primary_fees
            html += f'''
                        <tr class="total-row" style="background: #d1fae5; border-top: 2px solid #10b981;">
                            <td colspan="5" style="text-align: right; font-weight: bold; color: #065f46;">PRIMARY TOTALS:</td>
                            <td class="amount-cell" style="font-weight: bold; color: #065f46;">HK${primary_total:,.2f}</td>
                            <td class="amount-cell" style="font-weight: bold; color: #f59e0b;">HK${primary_fees:,.2f}</td>
                            <td class="amount-cell" style="font-weight: bold; color: #10b981;">HK${primary_net:,.2f}</td>
                            <td></td>
                        </tr>
            '''
        
        html += '''
                    </tbody>
                </table>
            </div>
        '''
        
        # Secondary transactions table (if any exist)
        if secondary_transactions:
            html += '''
                <!-- Secondary Transactions (No Real Money Movement) -->
                <div class="transactions-table" style="margin-top: 24px;">
                    <div class="table-header" style="background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);">
                        ⚠️ Secondary Transactions (No Real Money Movement) - Failed, Canceled, etc.
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th class="date-cell">Date</th>
                                <th class="company-cell">Company</th>
                                <th class="description-cell">Description</th>
                                <th class="type-cell">Type</th>
                                <th class="status-cell">Status</th>
                                <th class="amount-cell">Amount (HKD)</th>
                                <th class="customer-cell">Customer</th>
                            </tr>
                        </thead>
                        <tbody>
            '''
            
            for i, tx in enumerate(secondary_transactions):
                amount_class = "amount-negative"  # Secondary transactions are typically failures
                status_class = f"status-{tx['status']}"
                row_class = "row-even" if i % 2 == 0 else "row-odd"
                
                # Truncate description for better print layout
                description = tx['description']
                if len(description) > 40:
                    description = description[:37] + "..."
                
                # Truncate customer email for better print layout
                customer_email = tx['customer_email']
                if len(customer_email) > 25:
                    customer_email = customer_email[:22] + "..."
                
                html += f'''
                            <tr class="{row_class}" style="background: #f9fafb;">
                                <td class="date-cell">{tx['stripe_created'].strftime('%Y-%m-%d %H:%M') if tx['stripe_created'] else 'N/A'}</td>
                                <td class="company-cell">{tx['account_name']}</td>
                                <td class="description-cell" title="{tx['description']}">{description}</td>
                                <td class="type-cell">{tx['type'] or 'N/A'}</td>
                                <td class="status-cell {status_class}">{tx['status'].title()}</td>
                                <td class="amount-cell {amount_class}">{tx['currency']} {tx['amount']:,.2f}</td>
                                <td class="customer-cell" title="{tx['customer_email']}">{customer_email}</td>
                            </tr>
                '''
            
            html += f'''
                            <tr style="background: #f3f4f6; border-top: 2px solid #6b7280;">
                                <td colspan="5" style="text-align: right; font-weight: bold; color: #374151;">SECONDARY COUNT:</td>
                                <td class="amount-cell" style="font-weight: bold; color: #374151;">{len(secondary_transactions)} transactions</td>
                                <td></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            '''
        
        # Overall totals
        total_calculated = sum(tx['amount'] for tx in transactions)
        total_fees_calculated = sum(tx.get('fee', 0) for tx in transactions)
        total_net = total_calculated - total_fees_calculated
        
        html += f'''
            <!-- Overall Summary -->
            <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 20px; border-radius: 12px; margin-top: 24px; text-align: center;">
                <h3 style="margin-bottom: 16px;">📊 Overall Statement Summary</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
                    <div>
                        <div style="font-size: 1.5rem; font-weight: bold;">HK${total_calculated:,.2f}</div>
                        <div style="opacity: 0.9;">Total Gross Amount</div>
                    </div>
                    <div>
                        <div style="font-size: 1.5rem; font-weight: bold;">HK${total_fees_calculated:,.2f}</div>
                        <div style="opacity: 0.9;">Total Fees</div>
                    </div>
                    <div>
                        <div style="font-size: 1.5rem; font-weight: bold;">HK${total_net:,.2f}</div>
                        <div style="opacity: 0.9;">Net Amount</div>
                    </div>
                    <div>
                        <div style="font-size: 1.5rem; font-weight: bold;">{len(primary_transactions)}/{len(transactions)}</div>
                        <div style="opacity: 0.9;">Primary/Total Transactions</div>
                    </div>
                </div>
            </div>
        '''
    else:
        html += '''
            <div style="text-align: center; padding: 40px; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                <h3 style="color: #64748b; margin-bottom: 16px;">📊 No Transactions Found</h3>
                <p style="color: #64748b;">No transactions match your selected criteria.</p>
            </div>
        '''
    
    html += '''
        </div>
        
        <!-- Chart.js Library -->
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        
        <script>
            // Chart data preparation
            const grossAmount = {total_amount:.2f};
            const totalFees = {total_fees:.2f};
            const netAmount = grossAmount - totalFees;
            
            // Transaction data for charts
            const transactionData = ['''
    
    # Add JavaScript transaction data for charts
    if transactions:
        js_data = []
        for tx in transactions:
            # Group by month for trend analysis
            month_key = tx['stripe_created'].strftime('%Y-%m') if tx['stripe_created'] else '2025-01'
            js_data.append(f'''
                {{
                    date: "{tx['stripe_created'].strftime('%Y-%m-%d') if tx['stripe_created'] else '2025-01-01'}",
                    month: "{month_key}",
                    status: "{tx['status']}",
                    amount: {tx['amount']:.2f},
                    fee: {tx.get('fee', 0):.2f},
                    net: {tx.get('net_amount', tx['amount']):.2f}
                }}''')
        html += ','.join(js_data)
    
    html += '''
            ];
            
            // Status counts for pie chart
            const statusCounts = {'''
    
    # Add status counts
    status_js = []
    for status, count in status_counts.items():
        status_js.append(f'"{status}": {count}')
    html += ', '.join(status_js)
    
    html += '''};
            
            // Initialize charts when page loads
            document.addEventListener('DOMContentLoaded', function() {
                createIncomeChart();
                createStatusChart();
                createTrendChart();
            });
            
            function createIncomeChart() {
                const ctx = document.getElementById('incomeChart').getContext('2d');
                new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Net Income', 'Processing Fees'],
                        datasets: [{
                            data: [netAmount, totalFees],
                            backgroundColor: ['#10b981', '#f59e0b'],
                            borderColor: ['#059669', '#d97706'],
                            borderWidth: 3,
                            hoverOffset: 4
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 20,
                                    usePointStyle: true,
                                    font: { size: 14 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed;
                                        const percentage = ((value / grossAmount) * 100).toFixed(1);
                                        return `${label}: HK$${value.toLocaleString()} (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            function createStatusChart() {
                const ctx = document.getElementById('statusChart').getContext('2d');
                const labels = Object.keys(statusCounts);
                const data = Object.values(statusCounts);
                const colors = {
                    'succeeded': '#10b981',
                    'paid': '#10b981', 
                    'failed': '#ef4444',
                    'canceled': '#6b7280',
                    'requires_payment_method': '#f59e0b',
                    'requires_action': '#8b5cf6',
                    'refunded': '#06b6d4'
                };
                
                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: labels.map(s => s.charAt(0).toUpperCase() + s.slice(1)),
                        datasets: [{
                            data: data,
                            backgroundColor: labels.map(status => colors[status] || '#94a3b8'),
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    font: { size: 12 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        const label = context.label || '';
                                        const value = context.parsed;
                                        const total = data.reduce((a, b) => a + b, 0);
                                        const percentage = ((value / total) * 100).toFixed(1);
                                        return `${label}: ${value} transactions (${percentage}%)`;
                                    }
                                }
                            }
                        }
                    }
                });
            }
            
            function createTrendChart() {
                // Group transactions by month
                const monthlyData = {};
                transactionData.forEach(tx => {
                    const month = tx.month;
                    if (!monthlyData[month]) {
                        monthlyData[month] = { gross: 0, fees: 0, net: 0, count: 0 };
                    }
                    if (tx.status === 'succeeded' || tx.status === 'paid') {
                        monthlyData[month].gross += tx.amount;
                        monthlyData[month].fees += tx.fee;
                        monthlyData[month].net += tx.net;
                        monthlyData[month].count += 1;
                    }
                });
                
                const sortedMonths = Object.keys(monthlyData).sort();
                const grossData = sortedMonths.map(month => monthlyData[month].gross);
                const feeData = sortedMonths.map(month => monthlyData[month].fees);
                const netData = sortedMonths.map(month => monthlyData[month].net);
                
                const ctx = document.getElementById('trendChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: sortedMonths.map(month => {
                            const date = new Date(month + '-01');
                            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
                        }),
                        datasets: [
                            {
                                label: 'Gross Income',
                                data: grossData,
                                borderColor: '#059669',
                                backgroundColor: 'rgba(5, 150, 105, 0.1)',
                                fill: false,
                                tension: 0.1,
                                borderWidth: 3
                            },
                            {
                                label: 'Processing Fees',
                                data: feeData,
                                borderColor: '#d97706',
                                backgroundColor: 'rgba(217, 119, 6, 0.1)',
                                fill: false,
                                tension: 0.1,
                                borderWidth: 2
                            },
                            {
                                label: 'Net Income',
                                data: netData,
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                                fill: true,
                                tension: 0.1,
                                borderWidth: 3
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            y: {
                                beginAtZero: true,
                                grid: { color: '#f1f5f9' },
                                ticks: { 
                                    font: { size: 12 },
                                    callback: function(value) {
                                        return 'HK$' + value.toLocaleString();
                                    }
                                }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { font: { size: 12 } }
                            }
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    padding: 20,
                                    usePointStyle: true,
                                    font: { size: 13 }
                                }
                            },
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: HK$${context.parsed.y.toLocaleString()}`;
                                    }
                                }
                            }
                        },
                        interaction: {
                            intersect: false,
                            mode: 'index'
                        }
                    }
                });
            }
            
            function exportCSV() {
                const transactions = ['''
    
    # Add JavaScript data for CSV export including fees
    if transactions:
        js_data = []
        for tx in transactions:
            # Escape quotes in description for JavaScript
            description = tx['description'].replace('"', '\\"')
            js_data.append(f'''
                {{
                    date: "{tx['stripe_created'].strftime('%Y-%m-%d %H:%M') if tx['stripe_created'] else 'N/A'}",
                    company: "{tx['account_name']}",
                    description: "{description}",
                    type: "{tx['type'] or 'N/A'}",
                    status: "{tx['status']}",
                    amount: {tx['amount']:.2f},
                    fee: {tx.get('fee', 0):.2f},
                    net: {tx.get('net_amount', tx['amount']):.2f},
                    customer: "{tx['customer_email']}"
                }}''')
        html += ','.join(js_data)
    
    html += '''
                ];
                
                if (transactions.length === 0) {
                    alert('No transactions to export');
                    return;
                }
                
                let csvContent = "Date,Company,Description,Type,Status,Gross Amount (HKD),Fee (HKD),Net Amount (HKD),Customer\\n";
                transactions.forEach(tx => {
                    csvContent += `"${tx.date}","${tx.company}","${tx.description}","${tx.type}","${tx.status}","${tx.amount.toFixed(2)}","${tx.fee.toFixed(2)}","${tx.net.toFixed(2)}","${tx.customer}"\\n`;
                });
                
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement('a');
                const url = URL.createObjectURL(blob);
                link.setAttribute('href', url);
                link.setAttribute('download', `bank_statement_${new Date().toISOString().split('T')[0]}.csv`);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
            
            function optimizeForPrint() {
                // Add print-specific optimizations
                document.body.style.fontSize = '10px';
                document.body.style.lineHeight = '1.2';
                
                // Remove any remaining rounded corners for print
                const elements = document.querySelectorAll('*');
                elements.forEach(el => {
                    el.style.borderRadius = '0';
                    el.style.boxShadow = 'none';
                });
                
                alert('Layout optimized for printing. Click OK then use Ctrl+P (or Cmd+P on Mac) to print.');
            }
            
            // Auto-optimize table for better landscape printing
            document.addEventListener('DOMContentLoaded', function() {
                const table = document.querySelector('table');
                if (table) {
                    table.style.tableLayout = 'fixed';
                    table.style.width = '100%';
                }
            });
        </script>
    </body>
    </html>
    '''
    
    return html

def generate_summary_statement(transactions, status_counts, total_amount, total_fees):
    """Generate summary-only statement"""
    # This would be a simplified version - for now, redirect to detailed
    return generate_detailed_statement(transactions, status_counts, total_amount, total_fees, {
        'company_id': 'all',
        'status_filter': 'all',
        'period': '30',
        'from_date': None,
        'to_date': None
    })

def generate_csv_statement(transactions):
    """Generate CSV statement"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header including fee information
    writer.writerow(['Date', 'Company', 'Description', 'Type', 'Status', 'Gross Amount (HKD)', 'Fee (HKD)', 'Net Amount (HKD)', 'Customer Email']);
    
    # Write transactions including fee information
    for tx in transactions:
        writer.writerow([
            tx['stripe_created'].strftime('%Y-%m-%d %H:%M') if tx['stripe_created'] else 'N/A',
            tx['account_name'],
            tx['description'],
            tx['type'] or 'N/A',
            tx['status'],
            f"{tx['amount']:.2f}",
            f"{tx.get('fee', 0):.2f}",
            f"{tx.get('net_amount', tx['amount']):.2f}",
            tx['customer_email']
        ])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bank_statement.csv'}
    )

# Add a route to test statement generation with debug info
@analytics_bp.route('/statement-generator/debug')
def debug_statement_generation():
    """Debug endpoint to test statement generation"""
    try:
        # Test with November 2021 date range
        from_date = '2021-11-01'
        to_date = '2021-11-30'
        
        # Build the base query
        query = db.session.query(
            StripeAccount.name.label('account_name'),
            Transaction.id,
            Transaction.amount,
            Transaction.status,
            Transaction.type,
            Transaction.stripe_created,
            Transaction.description,
            Transaction.customer_email
        ).join(Transaction, StripeAccount.id == Transaction.account_id)
        
        # Filter by date range
        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
        to_datetime = datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(
            Transaction.stripe_created >= from_datetime,
            Transaction.stripe_created <= to_datetime
        )
        
        # Execute query and get results
        results = query.order_by(Transaction.stripe_created.desc()).all()
        
        # Process results
        transactions = []
        for row in results:
            amount_hkd = (row.amount or 0) / 100
            transactions.append({
                'account_name': row.account_name,
                'id': row.id,
                'amount': amount_hkd,
                'status': row.status,
                'type': row.type,
                'stripe_created': row.stripe_created,
                'description': row.description or 'N/A',
                'customer_email': row.customer_email or 'N/A'
            })
        
        # Create debug response
        debug_info = {
            'date_range': f"{from_date} to {to_date}",
            'from_datetime': from_datetime.isoformat(),
            'to_datetime': to_datetime.isoformat(),
            'total_transactions_found': len(transactions),
            'transactions': transactions
        }
        
        return jsonify({
            'success': True,
            'debug_info': debug_info
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500