from app import db
from datetime import datetime

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stripe_id = db.Column(db.String(100), unique=True, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('stripe_account.id'), nullable=False)
    
    # Transaction details
    amount = db.Column(db.Integer, nullable=False)  # Amount in cents
    fee = db.Column(db.Integer, nullable=True, default=0)  # Processing fee in cents
    currency = db.Column(db.String(3), nullable=False, default='usd')
    status = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # charge, refund, etc.
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    stripe_created = db.Column(db.DateTime, nullable=False)
    
    # Customer and transaction metadata
    customer_email = db.Column(db.String(100))
    description = db.Column(db.Text)
    stripe_metadata = db.Column(db.JSON)
    
    def __repr__(self):
        return f'<Transaction {self.stripe_id}: {self.amount/100} {self.currency}>'
    
    @property
    def amount_formatted(self):
        """Return amount in dollars/euros etc (divided by 100)"""
        return self.amount / 100
    
    @property
    def fee_formatted(self):
        """Return fee in dollars/euros etc (divided by 100)"""
        return (self.fee or 0) / 100
    
    @property
    def net_amount_formatted(self):
        """Return net amount after fees in dollars/euros etc"""
        return self.amount_formatted - self.fee_formatted