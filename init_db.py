#!/usr/bin/env python3
"""
Initialize database for Stripe Dashboard
"""

import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize the database"""
    try:
        from app import create_app, db
        from app.models import StripeAccount, Transaction

        app = create_app()
        with app.app_context():
            db.create_all()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization warning: {e}")
        # Continue anyway - the database might already exist

if __name__ == '__main__':
    init_database()
