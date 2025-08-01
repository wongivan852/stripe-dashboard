#!/bin/bash

# Stripe Dashboard Startup Script
# This script activates the virtual environment and starts the Flask application

echo "🚀 Starting Stripe Dashboard..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if instance directory exists
if [ ! -d "instance" ]; then
    echo "📁 Creating instance directory for database..."
    mkdir -p instance
fi

# Start the application using virtual environment Python
echo "✅ Starting Flask application..."
echo "📱 Open http://localhost:5001 in your browser"
echo "🔄 Press Ctrl+C to stop"
echo ""

#!/bin/bash

# Production startup script for Stripe Dashboard Analytics

echo "🚀 Starting Stripe Dashboard Analytics..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

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

echo "✅ Starting application on http://localhost:5001"
echo "🔄 Press Ctrl+C to stop"

# Start the application
python run.py
