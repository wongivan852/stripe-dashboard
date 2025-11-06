#!/bin/bash

# Stripe Dashboard Startup Script
# This script activates the virtual environment and starts the Flask application

echo "🚀 Starting Stripe Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📥 Installing/updating dependencies..."
    pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Create instance directory if it doesn't exist
mkdir -p instance

# Set production environment
export FLASK_ENV=production

echo "✅ Starting application on http://localhost:8081"
echo "🔄 Press Ctrl+C to stop"
echo ""

# Start the application with virtual environment activated
source venv/bin/activate && python run.py