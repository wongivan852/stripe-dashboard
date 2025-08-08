from flask import Flask, Response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
import json
from datetime import datetime

# Load environment variables automatically
from dotenv import load_dotenv
load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    # Configure database with flexible path for deployment
    if os.getenv('DATABASE_URL'):
        # Use environment variable if provided (production/Docker)
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    else:
        # Use absolute path for development to ensure consistent database access
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/wongivan/stripe-dashboard/instance/payments.db'
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
    
    # Main routes
    @app.route('/')
    def index():
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Dashboard</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * { box-sizing: border-box; margin: 0; padding: 0; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh; padding: 20px; color: #333;
                }
                .container { 
                    max-width: 900px; margin: 0 auto; background: white; 
                    border-radius: 16px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                    overflow: hidden;
                }
                .header { 
                    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                    color: white; padding: 3rem 2rem; text-align: center;
                }
                .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
                .header p { font-size: 1.1rem; opacity: 0.9; }
                .nav-grid { 
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                    gap: 0; 
                }
                .nav-item { 
                    padding: 2rem; text-align: center; text-decoration: none; 
                    color: #333; transition: all 0.3s; border-bottom: 1px solid #e5e7eb;
                    display: flex; flex-direction: column; align-items: center; gap: 1rem;
                }
                .nav-item:hover { 
                    background: #f8fafc; transform: translateY(-2px);
                    box-shadow: inset 0 4px 0 #4f46e5;
                }
                .nav-icon { font-size: 3rem; }
                .nav-title { font-size: 1.3rem; font-weight: 600; }
                .nav-desc { color: #64748b; font-size: 0.95rem; line-height: 1.4; }
                .footer { 
                    padding: 2rem; text-align: center; color: #64748b; 
                    border-top: 1px solid #e5e7eb; background: #f9fafb;
                }
                @media (max-width: 768px) {
                    .nav-grid { grid-template-columns: 1fr; }
                    .header { padding: 2rem 1rem; }
                    .header h1 { font-size: 2rem; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💳 Payment Dashboard</h1>
                    <p>Stripe Analytics & Transaction Management</p>
                </div>
                
                <div class="nav-grid">
                    <a href="/analytics/simple" class="nav-item">
                        <div class="nav-icon">📋</div>
                        <div class="nav-title">Simple Dashboard</div>
                        <div class="nav-desc">Clean, easy-to-read transaction summary with account breakdowns</div>
                    </a>
                    
                    <a href="/analytics/statement-generator" class="nav-item">
                        <div class="nav-icon">📄</div>
                        <div class="nav-title">Statement Generator</div>
                        <div class="nav-desc">Generate custom bank statements with company and period filters, print & save options</div>
                    </a>
                    
                    <a href="/analytics/api/account-amounts" class="nav-item">
                        <div class="nav-icon">🔗</div>
                        <div class="nav-title">API Data</div>
                        <div class="nav-desc">JSON API endpoint for programmatic access to account data</div>
                    </a>
                </div>
                
                <div class="footer">
                    <p>🔄 Data syncs automatically | 🔒 Secure Stripe integration</p>
                    <p style="margin-top: 0.5rem; font-size: 0.85rem;">
                        Last updated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''
                    </p>
                </div>
            </div>
        </body>
        </html>
        '''
    
    # Register analytics blueprint if it exists
    try:
        from app.routes.analytics import analytics_bp
        app.register_blueprint(analytics_bp, url_prefix='/analytics')
        # Analytics blueprint registered successfully
    except ImportError as e:
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
                            <h1>💳 Payment Analytics - Simple View</h1>
                            <p>Real-time transaction data across all Stripe accounts</p>
                        </div>
                        
                        <div class="navigation">
                            <a href="/" class="nav-link">🏠 Home</a>
                            <a href="/analytics/simple" class="nav-link">📋 Simple View</a>
                            <a href="/analytics/statement-generator" class="nav-link">📄 Statement Generator</a>
                            <a href="/analytics/api/account-amounts" class="nav-link">🔗 API Data</a>
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