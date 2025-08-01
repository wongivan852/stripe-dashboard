from flask import Blueprint, render_template, jsonify, request
from app.services.multi_stripe_service import MultiStripeService
from app.models import StripeAccount, Transaction

bp = Blueprint('main', __name__)

@bp.route('/')
def dashboard():
    """Main dashboard view"""
    service = MultiStripeService()
    account_summary = service.get_account_summary()
    recent_transactions = service.get_all_transactions(limit=10)
    
    return render_template('dashboard.html', 
                         account_summary=account_summary, 
                         transactions=recent_transactions)

@bp.route('/api/sync')
def sync_accounts():
    """API endpoint to sync all accounts"""
    try:
        service = MultiStripeService()
        results = service.sync_all_accounts()
        
        # Check if any failed
        failed_accounts = [r for r in results if r['status'] == 'error']
        
        if failed_accounts:
            return jsonify({
                'status': 'partial_success',
                'message': f'Some accounts failed to sync: {len(failed_accounts)} failed',
                'results': results
            }), 207  # Multi-status
        else:
            return jsonify({
                'status': 'success',
                'message': 'All accounts synced successfully',
                'results': results
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Sync failed: {str(e)}'
        }), 500

@bp.route('/api/transactions')
def get_transactions():
    """API endpoint to get transactions"""
    account_id = request.args.get('account_id')
    limit = request.args.get('limit', 50, type=int)
    
    service = MultiStripeService()
    
    if account_id:
        transactions = service.get_account_transactions(int(account_id), limit)
    else:
        transactions = service.get_all_transactions(limit)
    
    return jsonify([{
        'id': t.id,
        'stripe_id': t.stripe_id,
        'account_id': t.account_id,
        'account_name': t.account.name,
        'amount': t.amount_formatted,
        'currency': t.currency.upper(),
        'status': t.status,
        'type': t.type,
        'created_at': t.created_at.isoformat(),
        'stripe_created': t.stripe_created.isoformat(),
        'customer_email': t.customer_email,
        'description': t.description
    } for t in transactions])

@bp.route('/api/accounts')
def get_accounts():
    """API endpoint to get account information"""
    service = MultiStripeService()
    summary = service.get_account_summary()
    
    return jsonify([{
        'id': s['account'].id,
        'name': s['account'].name,
        'is_active': s['account'].is_active,
        'has_api_key': s['has_api_key'],
        'total_transactions': s['total_transactions'],
        'total_amount': s['total_amount'],
        'created_at': s['account'].created_at.isoformat()
    } for s in summary])