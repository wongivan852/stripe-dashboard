from flask import Flask, Response, jsonify, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from functools import wraps
import os
import json
import requests
import logging
from datetime import datetime

# Load environment variables automatically
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SQLAlchemy()
migrate = Migrate()

# SSO Configuration
SSO_BASE_URL = os.environ.get('SSO_BASE_URL', 'http://localhost:8080')
SSO_SECRET_KEY = os.environ.get('SSO_SECRET_KEY', 'default-secret-key')
APP_NAME = 'stripe_dashboard'
SSO_ENABLED = os.environ.get('SSO_ENABLED', 'false').lower() == 'true'


def get_sso_login_url(return_url=None):
    """Generate SSO login URL for redirecting to central platform"""
    login_url = f"{SSO_BASE_URL}/auth/login/"
    if return_url:
        login_url += f"?next={return_url}"
    return login_url


def validate_sso_token(sso_token):
    """Validate SSO token with central platform"""
    try:
        response = requests.get(
            f"{SSO_BASE_URL}/auth/api/sso/validate/",
            params={'token': sso_token, 'app_name': APP_NAME},
            timeout=5
        )
        if response.status_code == 200:
            user_response = requests.get(
                f"{SSO_BASE_URL}/auth/api/sso/user-info/",
                params={'token': sso_token},
                timeout=5
            )
            if user_response.status_code == 200:
                return user_response.json()
    except requests.RequestException as e:
        logger.error(f"SSO authentication failed: {e}")
    return None


def sso_logout(sso_token):
    """Handle SSO logout - notify central platform"""
    if sso_token:
        try:
            requests.post(
                f"{SSO_BASE_URL}/auth/api/sso/logout/",
                json={'token': sso_token},
                timeout=5
            )
        except requests.RequestException as e:
            logger.warning(f"Failed to notify central platform of logout: {e}")


def login_required(f):
    """Decorator to require authentication (only when SSO is enabled)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip SSO check if not enabled (development mode)
        if not SSO_ENABLED:
            return f(*args, **kwargs)

        if 'user' not in session:
            # Check for SSO token
            sso_token = request.args.get('sso_token')
            if sso_token:
                user_data = validate_sso_token(sso_token)
                if user_data:
                    session['user'] = user_data
                    session['sso_token'] = sso_token
                    # Redirect to remove token from URL
                    return redirect(request.path)

            # Redirect to SSO login
            return_url = request.url
            sso_login_url = f"{get_sso_login_url()}?app=stripe_dashboard&return_to={return_url}"
            return redirect(sso_login_url)

        return f(*args, **kwargs)
    return decorated_function

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    # Configure database with flexible path for deployment
    if os.getenv('DATABASE_URL'):
        # Use environment variable if provided (production/Docker)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    else:
        # Use relative path for development - works across different environments
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        instance_dir = os.path.join(base_dir, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_dir, "payments.db")}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    try:
        db.init_app(app)
        migrate.init_app(app, db)
    except Exception as db_init_error:
        print(f"Database Initialization Error: {db_init_error}")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        raise
    
    # Import models (important to do this before registering blueprints)
    from app.models import StripeAccount, Transaction
    
    # Register health check blueprint
    try:
        from app.health import health_bp
        app.register_blueprint(health_bp)
        print("✅ Health check blueprint registered successfully")
    except ImportError as e:
        print(f"❌ Health check blueprint import failed: {e}")
        # Create basic health endpoint as fallback
        @app.route('/health')
        def basic_health():
            return jsonify({
                'status': 'ok',
                'timestamp': datetime.now().isoformat()
            }), 200
    
    # Logout route
    @app.route('/logout')
    def logout():
        """Handle logout"""
        sso_token = session.get('sso_token')
        if sso_token:
            sso_logout(sso_token)
        session.clear()
        if SSO_ENABLED:
            return redirect(f"{SSO_BASE_URL}/auth/logout/")
        return redirect('/')

    # Main routes
    @app.route('/')
    @login_required
    def index():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stripe Dashboard - Balance Testing</title>
            <style>
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .opening-balance { background-color: #f0f9ff; font-weight: bold; }
                .test-section { margin: 20px 0; padding: 20px; border: 2px solid #ddd; }
                .pass { color: green; font-weight: bold; }
                .fail { color: red; font-weight: bold; }
                body { font-family: Arial, sans-serif; margin: 20px; }
                button { padding: 10px 20px; margin: 5px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background: #45a049; }
                .api-button { background: #2196F3; }
                .api-button:hover { background: #1976D2; }
            </style>
        </head>
        <body>
            <h1>🏦 Stripe Balance Reconciliation Dashboard</h1>
            <p><strong>Status:</strong> Balance carry-forward FIXED | July 2025: HK$554.77 ✅</p>
            
            <div class="test-section">
                <h2>📅 Monthly Statement Testing</h2>
                <button onclick="testNovember()">November 2021</button>
                <button onclick="testDecember()">December 2021</button>
                <button onclick="testJuly()">July 2025</button>
                <button onclick="testContinuity()">Test Continuity</button>
                <div id="statement-results"></div>
            </div>
            
            <div class="test-section">
                <h2>💰 Payout Reconciliation Testing</h2>
                <button onclick="testPayoutJuly()" class="api-button">July 2025 Payout</button>
                <button onclick="openPayoutInterface()" class="api-button">Open Interface</button>
                <div id="payout-results"></div>
            </div>
            
            <div class="test-section">
                <h2>📤 Data Management</h2>
                <button onclick="window.location.href='/analytics/csv-upload'" class="api-button">Upload CSV Files</button>
                <p style="margin-top: 10px; color: #64748b;">Import multiple CSV files to update transaction data</p>
            </div>
            
            <div class="test-section" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none;">
                <h2>💳 Unified Payment Dashboard (Stripe + WeChat Pay)</h2>
                <p style="margin-bottom: 15px;">Combined view of all payment sources with fee categorization</p>
                <button onclick="window.open('/analytics/unified-dashboard', '_blank')" style="background: white; color: #667eea; font-weight: bold;">Open Unified Dashboard</button>
                <button onclick="window.open('/analytics/api/unified-fee-summary', '_blank')" style="background: rgba(255,255,255,0.2); color: white;">Fee Summary API</button>
                <button onclick="window.open('/analytics/api/unified-payments', '_blank')" style="background: rgba(255,255,255,0.2); color: white;">All Transactions API</button>
            </div>

            <div class="test-section">
                <h2>🔗 Quick Links</h2>
                <button onclick="window.open('/analytics/simple', '_blank')">Simple Analytics</button>
                <button onclick="window.open('/analytics/monthly-statement', '_blank')">Monthly Generator</button>
                <button onclick="window.open('/analytics/payout-reconciliation', '_blank')">Payout Reconciliation</button>
                <button onclick="window.open('/health', '_blank')" class="api-button">Health Check</button>
            </div>
            
            <script>
                let novemberStatement = null;
                let decemberStatement = null;
                let julyStatement = null;
                
                async function testNovember() {
                    try {
                        const response = await fetch('/analytics/api/monthly-statement?company=cgge&year=2021&month=11');
                        const data = await response.json();
                        
                        if (data.success) {
                            novemberStatement = data.statement;
                            displayStatement(data.statement, 'November 2021', 'statement-results');
                        } else {
                            document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + data.error + '</div>';
                        }
                    } catch (error) {
                        document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + error.message + '</div>';
                    }
                }
                
                async function testDecember() {
                    try {
                        const response = await fetch('/analytics/api/monthly-statement?company=cgge&year=2021&month=12');
                        const data = await response.json();
                        
                        if (data.success) {
                            decemberStatement = data.statement;
                            displayStatement(data.statement, 'December 2021', 'statement-results');
                        } else {
                            document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + data.error + '</div>';
                        }
                    } catch (error) {
                        document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + error.message + '</div>';
                    }
                }
                
                async function testJuly() {
                    try {
                        const response = await fetch('/analytics/api/monthly-statement?company=cgge&year=2025&month=7');
                        const data = await response.json();
                        
                        if (data.success) {
                            julyStatement = data.statement;
                            let html = '<h3>July 2025 - CGGE</h3>';
                            html += '<p><strong>Opening Balance:</strong> HK$' + julyStatement.opening_balance.toFixed(2) + '</p>';
                            html += '<p><strong>Closing Balance:</strong> HK$' + julyStatement.closing_balance.toFixed(2);
                            html += (julyStatement.closing_balance.toFixed(2) === '554.77') ? ' <span class="pass">[CORRECT]</span>' : ' <span class="fail">[INCORRECT - Should be 554.77]</span>';
                            html += '</p><p><strong>Transactions:</strong> ' + julyStatement.transactions.length + '</p>';
                            
                            document.getElementById('statement-results').innerHTML = html;
                        } else {
                            document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + data.error + '</div>';
                        }
                    } catch (error) {
                        document.getElementById('statement-results').innerHTML = '<div class="fail">Error: ' + error.message + '</div>';
                    }
                }
                
                function displayStatement(statement, title, targetId) {
                    let html = '<h3>' + title + ' - CGGE</h3>';
                    html += '<p><strong>Opening Balance:</strong> HK$' + statement.opening_balance.toFixed(2) + '</p>';
                    html += '<p><strong>Closing Balance:</strong> HK$' + statement.closing_balance.toFixed(2) + '</p>';
                    html += '<p><strong>Transactions:</strong> ' + statement.transactions.length + '</p>';
                    
                    if (statement.transactions.length > 0) {
                        html += '<table><thead><tr><th>Date</th><th>Nature</th><th>Party</th><th>Debit</th><th>Credit</th><th>Balance</th><th>Description</th></tr></thead><tbody>';
                        html += '<tr class="opening-balance"><td>' + statement.year + '-' + statement.month.toString().padStart(2, '0') + '-01</td><td>Opening Balance</td><td>Brought Forward</td><td></td><td></td><td>HK$' + statement.opening_balance.toFixed(2) + '</td><td>Opening balance</td></tr>';
                        
                        statement.transactions.forEach(tx => {
                            html += '<tr><td>' + tx.date + '</td><td>' + tx.nature + '</td><td>' + tx.party + '</td>';
                            html += '<td>' + (tx.debit > 0 ? 'HK$' + parseFloat(tx.debit).toFixed(2) : '') + '</td>';
                            html += '<td>' + (tx.credit > 0 ? 'HK$' + parseFloat(tx.credit).toFixed(2) : '') + '</td>';
                            html += '<td>HK$' + parseFloat(tx.balance).toFixed(2) + '</td><td>' + tx.description + '</td></tr>';
                        });
                        
                        html += '<tr class="opening-balance"><td>' + statement.year + '-' + statement.month.toString().padStart(2, '0') + '-31</td><td>Closing Balance</td><td>Carry Forward</td><td></td><td></td><td>HK$' + statement.closing_balance.toFixed(2) + '</td><td>Closing balance</td></tr>';
                        html += '</tbody></table>';
                    }
                    
                    document.getElementById(targetId).innerHTML = html;
                }
                
                async function testContinuity() {
                    if (!novemberStatement || !decemberStatement) {
                        document.getElementById('statement-results').innerHTML = '<div class="fail">Please load November and December statements first!</div>';
                        return;
                    }
                    
                    const novClosing = novemberStatement.closing_balance;
                    const decOpening = decemberStatement.opening_balance;
                    const match = Math.abs(novClosing - decOpening) < 0.01;
                    
                    let html = '<h3>Balance Continuity Check</h3>';
                    html += '<p><strong>November 2021 Closing:</strong> HK$' + novClosing.toFixed(2) + '</p>';
                    html += '<p><strong>December 2021 Opening:</strong> HK$' + decOpening.toFixed(2) + '</p>';
                    html += '<p class="' + (match ? 'pass' : 'fail') + '"><strong>Balance Continuity:</strong> ' + (match ? 'PASS ✓' : 'FAIL ✗') + '</p>';
                    
                    if (match) {
                        html += '<p class="pass">Perfect! The November closing balance correctly carries forward to December opening balance.</p>';
                    } else {
                        html += '<p class="fail">Error: Balance continuity is broken. Check the carry-forward logic.</p>';
                    }
                    
                    document.getElementById('statement-results').innerHTML = html;
                }
                
                async function testPayoutJuly() {
                    try {
                        const response = await fetch('/analytics/api/payout-reconciliation?company=cgge&year=2025&month=7');
                        const data = await response.json();
                        
                        if (data.success) {
                            const reconciliation = data.reconciliation;
                            const payout = reconciliation.payout_reconciliation;
                            
                            let html = '<h3>July 2025 Payout Reconciliation - CGGE</h3>';
                            html += '<p><strong>Total Paid Out:</strong> HK$' + payout.total_paid_out.toFixed(2);
                            html += (payout.total_paid_out.toFixed(2) === '2636.78') ? ' <span class="pass">[MATCHES STRIPE]</span>' : ' <span class="fail">[DOES NOT MATCH]</span>';
                            html += '</p>';
                            html += '<p><strong>Charges:</strong> ' + payout.charges.count + ' transactions, HK$' + payout.charges.gross_amount.toFixed(2) + '</p>';
                            html += '<p><strong>Fees:</strong> HK$' + payout.charges.fees.toFixed(2) + '</p>';
                            html += '<p><strong>Ending Balance:</strong> HK$' + reconciliation.ending_balance_reconciliation.ending_balance.toFixed(2) + '</p>';
                            
                            document.getElementById('payout-results').innerHTML = html;
                        } else {
                            document.getElementById('payout-results').innerHTML = '<div class="fail">Error: ' + data.error + '</div>';
                        }
                    } catch (error) {
                        document.getElementById('payout-results').innerHTML = '<div class="fail">Error: ' + error.message + '</div>';
                    }
                }
                
                function openPayoutInterface() {
                    window.open('/analytics/payout-reconciliation', '_blank');
                }
            </script>
        </body>
        </html>
        '''
    
    # Register analytics blueprint if it exists
    try:
        from app.routes.analytics import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
        print("✅ Analytics blueprint registered successfully")
    except ImportError as e:
        print(f"❌ Analytics blueprint import failed: {e}")
        # Analytics blueprint not found - using fallback routes
        
        # Create fallback analytics routes directly in the main app
        @app.route('/analytics/simple')
        def fallback_simple_analytics():
            from sqlalchemy import text
            
            try:
                # Get account data
                results = db.session.execute(text("""
                    SELECT sa.name, t.status, COUNT(t.id) as count, SUM(t.amount) as total
                    FROM stripe_account sa
                    JOIN "transaction" t ON sa.id = t.account_id
                    GROUP BY sa.name, t.status
                    ORDER BY sa.name, t.status
                """)).fetchall()
                
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
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>💳 Company Stripe Dashboard - Simple View</h1>
                            <p>Real-time transaction data across all Stripe accounts</p>
                        </div>
                        
                        <div class="navigation">
                            <a href="/" class="nav-link">🏠 Home</a>
                            <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                            <a href="/analytics/statement-generator" class="nav-link">📄 Statement Generator</a>
                            <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
                            <a href="/health" class="nav-link">🩺 Health Check</a>
                        </div>
                '''
                
                # Process data
                accounts = {}
                for row in results:
                    account_name, status, count, total = row
                    if account_name not in accounts:
                        accounts[account_name] = {}
                    accounts[account_name][status] = {
                        'count': count,
                        'amount': (total or 0) / 100
                    }
                
                # Generate HTML for each account
                grand_total = 0
                total_transactions = 0
                
                for account_name, statuses in accounts.items():
                    html += f'<div class="account"><h3>🏢 {account_name}</h3>'
                    
                    account_total = 0
                    account_count = 0
                    
                    for status, data in statuses.items():
                        amount = data['amount']
                        count = data['count']
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
                            💰 GRAND TOTAL: {total_transactions:,} transactions | HK${grand_total:,.2f}
                        </div>
                    </div>
                </body>
                </html>
                '''
                
                return html
                
            except Exception as e:
                return f'''
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Analytics Error</title>
                    <style>
                        body {{ font-family: sans-serif; margin: 40px; background: #fef2f2; }}
                        .error {{ background: white; padding: 30px; border-radius: 8px; border-left: 4px solid #ef4444; }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h1>❌ Error</h1>
                        <p>Database error: {e}</p>
                        <p><a href="/">← Back to Home</a></p>
                    </div>
                </body>
                </html>
                '''
        
        @app.route('/analytics/api/account-amounts')
        def fallback_api_account_amounts():
            from sqlalchemy import text
            
            try:
                results = db.session.execute(text("""
                    SELECT sa.name, t.status, COUNT(t.id) as count, SUM(t.amount) as total
                    FROM stripe_account sa
                    JOIN "transaction" t ON sa.id = t.account_id
                    GROUP BY sa.name, t.status
                    ORDER BY sa.name, t.status
                """)).fetchall()
                
                account_data = {}
                for row in results:
                    account_name, status, count, total = row
                    if account_name not in account_data:
                        account_data[account_name] = {
                            'name': account_name,
                            'statuses': {},
                            'total_amount': 0,
                            'total_count': 0
                        }
                    
                    amount = (total or 0) / 100
                    account_data[account_name]['statuses'][status] = {
                        'count': count,
                        'amount': amount
                    }
                    account_data[account_name]['total_amount'] += amount
                    account_data[account_name]['total_count'] += count
                
                response_data = {
                    'success': True,
                    'timestamp': datetime.now().isoformat(),
                    'data': list(account_data.values()),
                    'summary': {
                        'total_accounts': len(account_data),
                        'total_amount': sum(acc['total_amount'] for acc in account_data.values()),
                        'total_transactions': sum(acc['total_count'] for acc in account_data.values())
                    }
                }
                
                # Return properly formatted JSON
                response = Response(
                    json.dumps(response_data, indent=2, ensure_ascii=False),
                    mimetype='application/json',
                    headers={
                        'Content-Type': 'application/json; charset=utf-8',
                        'Access-Control-Allow-Origin': '*'
                    }
                )
                return response
                
            except Exception as e:
                error_response = {
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                
                response = Response(
                    json.dumps(error_response, indent=2),
                    mimetype='application/json',
                    status=500,
                    headers={'Content-Type': 'application/json; charset=utf-8'}
                )
                return response


        # Fallback analytics routes created
    
    return app