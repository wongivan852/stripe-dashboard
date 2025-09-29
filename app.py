"""
Stripe Dashboard - Flask Application
Integrated with Central Authentication Platform
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
import requests
import os
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'stripe-dashboard-secret-key-change-in-production')

# SSO Configuration
SSO_BASE_URL = os.environ.get('SSO_BASE_URL', 'http://localhost:8080')
SSO_SECRET_KEY = os.environ.get('SSO_SECRET_KEY', 'default-secret-key')
APP_NAME = 'stripe_dashboard'


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
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
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


@app.route('/')
@login_required
def dashboard():
    """Main dashboard view"""
    user = session.get('user', {})

    # Mock Stripe dashboard data
    dashboard_data = {
        'total_revenue': '$12,450.00',
        'total_transactions': 156,
        'successful_payments': 98.7,
        'recent_transactions': [
            {
                'id': 'ch_1A2B3C4D5E6F',
                'amount': '$89.99',
                'customer': 'john.doe@example.com',
                'status': 'succeeded',
                'created': '2025-09-29 10:30'
            },
            {
                'id': 'ch_2B3C4D5E6F7G',
                'amount': '$156.50',
                'customer': 'jane.smith@example.com',
                'status': 'succeeded',
                'created': '2025-09-29 09:15'
            },
            {
                'id': 'ch_3C4D5E6F7G8H',
                'amount': '$45.00',
                'customer': 'bob.wilson@example.com',
                'status': 'failed',
                'created': '2025-09-29 08:45'
            }
        ]
    }

    return render_template('dashboard.html', user=user, data=dashboard_data)


@app.route('/transactions')
@login_required
def transactions():
    """Transactions view"""
    user = session.get('user', {})

    # Mock transaction data
    transactions = [
        {
            'id': 'ch_1A2B3C4D5E6F',
            'amount': '$89.99',
            'customer': 'john.doe@example.com',
            'status': 'succeeded',
            'created': '2025-09-29 10:30',
            'description': 'Product Purchase'
        },
        {
            'id': 'ch_2B3C4D5E6F7G',
            'amount': '$156.50',
            'customer': 'jane.smith@example.com',
            'status': 'succeeded',
            'created': '2025-09-29 09:15',
            'description': 'Subscription Payment'
        },
        {
            'id': 'ch_3C4D5E6F7G8H',
            'amount': '$45.00',
            'customer': 'bob.wilson@example.com',
            'status': 'failed',
            'created': '2025-09-29 08:45',
            'description': 'Service Fee'
        }
    ]

    return render_template('transactions.html', user=user, transactions=transactions)


@app.route('/customers')
@login_required
def customers():
    """Customers view"""
    user = session.get('user', {})

    # Mock customer data
    customers = [
        {
            'id': 'cus_1A2B3C4D5E',
            'email': 'john.doe@example.com',
            'name': 'John Doe',
            'created': '2025-09-20',
            'total_spent': '$189.98'
        },
        {
            'id': 'cus_2B3C4D5E6F',
            'email': 'jane.smith@example.com',
            'name': 'Jane Smith',
            'created': '2025-09-18',
            'total_spent': '$456.50'
        },
        {
            'id': 'cus_3C4D5E6F7G',
            'email': 'bob.wilson@example.com',
            'name': 'Bob Wilson',
            'created': '2025-09-15',
            'total_spent': '$0.00'
        }
    ]

    return render_template('customers.html', user=user, customers=customers)


@app.route('/logout')
def logout():
    """Handle logout"""
    sso_token = session.get('sso_token')
    if sso_token:
        sso_logout(sso_token)

    session.clear()
    return redirect(url_for('dashboard'))


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'app': 'stripe_dashboard',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8006)