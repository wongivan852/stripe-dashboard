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

./venv/bin/python run.py
