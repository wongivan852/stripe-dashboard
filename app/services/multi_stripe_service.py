from app.models import StripeAccount, Transaction
from app.services.stripe_service import StripeService
from app import db

class MultiStripeService:
    def __init__(self):
        self.accounts = StripeAccount.query.filter_by(is_active=True).all()
        self.services = {}
        
        # Initialize services for each account
        for account in self.accounts:
            if account.api_key:  # Only create service if API key exists
                self.services[account.id] = StripeService(account)
    
    def sync_all_accounts(self):
        """Sync transactions from all active accounts"""
        results = []
        
        for account_id, service in self.services.items():
            try:
                print(f"Syncing account {service.account.name}...")
                service.sync_transactions()
                results.append({
                    'account_id': account_id,
                    'account_name': service.account.name,
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'account_id': account_id,
                    'account_name': service.account.name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def get_account_transactions(self, account_id: int, limit: int = 50):
        """Get transactions for specific account"""
        return Transaction.query.filter_by(account_id=account_id)\
                               .order_by(Transaction.stripe_created.desc())\
                               .limit(limit).all()
    
    def get_all_transactions(self, limit: int = 100):
        """Get transactions from all accounts"""
        return Transaction.query.order_by(Transaction.stripe_created.desc())\
                               .limit(limit).all()
    
    def get_account_summary(self):
        """Get summary statistics for all accounts"""
        summary = []
        
        for account in self.accounts:
            total_transactions = Transaction.query.filter_by(account_id=account.id).count()
            total_amount = db.session.query(db.func.sum(Transaction.amount))\
                                   .filter_by(account_id=account.id).scalar() or 0
            
            summary.append({
                'account': account,
                'total_transactions': total_transactions,
                'total_amount': total_amount / 100,  # Convert from cents
                'has_api_key': bool(account.api_key)
            })
        
        return summary