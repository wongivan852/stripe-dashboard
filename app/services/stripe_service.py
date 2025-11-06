import stripe
from typing import List, Dict, Optional
from datetime import datetime
from app.models import StripeAccount, Transaction
from app import db

class StripeService:
    def __init__(self, account: StripeAccount):
        self.account = account
        stripe.api_key = account.api_key
    
    def fetch_charges(self, limit: int = 100) -> List[Dict]:
        """Fetch charges from Stripe API"""
        try:
            charges = stripe.Charge.list(limit=limit)
            return charges.data
        except stripe.error.StripeError as e:
            print(f"Stripe API Error for account {self.account.name}: {e}")
            return []
    
    def fetch_payment_intents(self, limit: int = 100) -> List[Dict]:
        """Fetch payment intents from Stripe API"""
        try:
            payment_intents = stripe.PaymentIntent.list(limit=limit)
            return payment_intents.data
        except stripe.error.StripeError as e:
            print(f"Stripe API Error for account {self.account.name}: {e}")
            return []
    
    def sync_transactions(self, limit_per_type: int = 100, prefer_charges: bool = True):
        """
        Sync transactions from Stripe to database.
        If prefer_charges=True, prioritize charges over payment_intents to avoid duplicates.
        """
        synced_count = 0
        
        if prefer_charges:
            # Strategy: Sync charges first, then only sync payment_intents that don't have charges
            synced_count += self._sync_charges(limit_per_type)
            synced_count += self._sync_payment_intents_without_charges(limit_per_type)
        else:
            # Sync both types independently
            synced_count += self._sync_charges(limit_per_type)
            synced_count += self._sync_payment_intents(limit_per_type)
        
        try:
            db.session.commit()
            print(f"Successfully synced {synced_count} transactions for account {self.account.name}")
            return synced_count
        except Exception as e:
            db.session.rollback()
            print(f"Error syncing transactions for account {self.account.name}: {e}")
            raise
    
    def _sync_charges(self, limit: int) -> int:
        """Sync charges specifically"""
        charges = self.fetch_charges(limit)
        synced = 0
        
        for charge in charges:
            existing = Transaction.query.filter_by(stripe_id=charge.id).first()
            
            if not existing:
                transaction = Transaction(
                    stripe_id=charge.id,
                    account_id=self.account.id,
                    amount=charge.amount,
                    currency=charge.currency,
                    status=charge.status,
                    type='charge',
                    stripe_created=datetime.fromtimestamp(charge.created),
                    customer_email=charge.receipt_email,
                    description=charge.description,
                    stripe_metadata=dict(charge.metadata) if charge.metadata else None
                )
                db.session.add(transaction)
                synced += 1
            else:
                # Update status if it changed
                if existing.status != charge.status:
                    existing.status = charge.status
                    synced += 1
        
        return synced
    
    def _sync_payment_intents(self, limit: int) -> int:
        """Sync all payment intents"""
        payment_intents = self.fetch_payment_intents(limit)
        synced = 0
        
        for pi in payment_intents:
            existing = Transaction.query.filter_by(stripe_id=pi.id).first()
            
            if not existing:
                transaction = Transaction(
                    stripe_id=pi.id,
                    account_id=self.account.id,
                    amount=pi.amount,
                    currency=pi.currency,
                    status=pi.status,
                    type='payment_intent',
                    stripe_created=datetime.fromtimestamp(pi.created),
                    customer_email=pi.receipt_email if hasattr(pi, 'receipt_email') else None,
                    description=pi.description,
                    stripe_metadata=dict(pi.metadata) if pi.metadata else None
                )
                db.session.add(transaction)
                synced += 1
            else:
                # Update status if it changed
                if existing.status != pi.status:
                    existing.status = pi.status
                    synced += 1
        
        return synced
    
    def _sync_payment_intents_without_charges(self, limit: int) -> int:
        """Sync only payment intents that don't have corresponding charges"""
        payment_intents = self.fetch_payment_intents(limit)
        synced = 0
        
        for pi in payment_intents:
            existing = Transaction.query.filter_by(stripe_id=pi.id).first()
            
            if not existing:
                # Check if there's a charge for this payment intent
                has_charge = False
                
                # Look for charges with the same amount, currency, and similar timestamp
                # This is a heuristic to avoid duplicates
                similar_charges = Transaction.query.filter_by(
                    account_id=self.account.id,
                    amount=pi.amount,
                    currency=pi.currency,
                    type='charge'
                ).filter(
                    Transaction.stripe_created.between(
                        datetime.fromtimestamp(pi.created - 300),  # 5 minutes before
                        datetime.fromtimestamp(pi.created + 300)   # 5 minutes after
                    )
                ).first()
                
                if not similar_charges:
                    transaction = Transaction(
                        stripe_id=pi.id,
                        account_id=self.account.id,
                        amount=pi.amount,
                        currency=pi.currency,
                        status=pi.status,
                        type='payment_intent',
                        stripe_created=datetime.fromtimestamp(pi.created),
                        customer_email=pi.receipt_email if hasattr(pi, 'receipt_email') else None,
                        description=pi.description,
                        stripe_metadata=dict(pi.metadata) if pi.metadata else None
                    )
                    db.session.add(transaction)
                    synced += 1
        
        return synced