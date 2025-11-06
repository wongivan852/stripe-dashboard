#!/usr/bin/env python3
"""
Database initialization script for production deployment
Creates database tables and ensures proper setup
"""

import os
import sys
from flask import Flask
from app import create_app, db
from app.models import StripeAccount, Transaction

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def init_database():
    """Initialize database with tables and basic setup"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created successfully")
            
            # Check if we have any accounts
            account_count = StripeAccount.query.count()
            transaction_count = Transaction.query.count()
            
            print(f"📊 Current database status:")
            print(f"   - Accounts: {account_count}")
            print(f"   - Transactions: {transaction_count}")
            
            if account_count == 0:
                print("⚠️  No accounts found. Consider importing your Stripe account data.")
            
            # Verify database connectivity
            test_query = db.session.execute(db.text("SELECT 1")).scalar()
            if test_query == 1:
                print("✅ Database connectivity verified")
                return True
            else:
                print("❌ Database connectivity test failed")
                return False
                
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False

def main():
    """Main initialization function"""
    print("🔧 Initializing Stripe Dashboard Database...")
    
    # Check if instance directory exists
    instance_dir = 'instance'
    if not os.path.exists(instance_dir):
        os.makedirs(instance_dir)
        print(f"📁 Created {instance_dir} directory")
    
    # Initialize database
    if init_database():
        print("🎉 Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("💥 Database initialization failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()