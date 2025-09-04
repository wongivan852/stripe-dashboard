#!/usr/bin/env python3
"""
Production WSGI Configuration for Stripe Dashboard
Dell Server Deployment - Production Ready
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import the Flask application
from app import create_app, db

# Create the application instance
application = create_app()

# Ensure database tables are created
with application.app_context():
    try:
        db.create_all()
        print("✅ Database tables created/verified successfully")
    except Exception as e:
        print(f"⚠️ Database initialization warning: {e}")

if __name__ == "__main__":
    # This allows the WSGI file to be run directly for testing
    application.run(host='0.0.0.0', port=5000, debug=False)