#!/bin/bash

# Production deployment script for Stripe Dashboard
echo "🚀 Deploying Stripe Dashboard..."

# Set production environment
export FLASK_ENV=production

# Create instance directory if it doesn't exist
mkdir -p instance

# Initialize database
echo "🔧 Initializing database..."
python init_db.py

if [ $? -eq 0 ]; then
    echo "✅ Database initialization successful"
    echo "🎯 Starting production server..."
    python run.py
else
    echo "❌ Database initialization failed"
    exit 1
fi