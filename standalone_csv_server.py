#!/usr/bin/env python3
"""
Standalone CSV Input UI Server
A simple Flask server to run the CSV input interface locally
"""

from flask import Flask, send_from_directory
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from csv_input_api import csv_input_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'csv-input-dev-key'

# Register the CSV input blueprint
app.register_blueprint(csv_input_bp)

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stripe CSV Input Interface</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                background: #f8fafc; margin: 0; padding: 40px; text-align: center;
            }
            .container { 
                max-width: 800px; margin: 0 auto; background: white; 
                padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            .header { 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                color: white; padding: 2rem; margin: -40px -40px 40px -40px; 
                border-radius: 12px 12px 0 0;
            }
            .button { 
                display: inline-block; padding: 15px 30px; margin: 15px; 
                background: #4f46e5; color: white; text-decoration: none; 
                border-radius: 8px; font-weight: 500; transition: all 0.2s;
            }
            .button:hover { 
                background: #4338ca; transform: translateY(-1px); 
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            }
            .api-button { background: #059669; }
            .api-button:hover { background: #047857; }
            .info { 
                background: #f0f9ff; padding: 20px; border-radius: 8px; 
                border-left: 4px solid #0ea5e9; margin: 20px 0; text-align: left;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Stripe CSV Input Interface</h1>
                <p>Process your Stripe CSV data with the debugged logic</p>
            </div>
            
            <div class="info">
                <h3>🎯 Current Configuration</h3>
                <ul>
                    <li><strong>Company:</strong> CGGE</li>
                    <li><strong>Period:</strong> August 2025</li>
                    <li><strong>Opening Balance:</strong> HK$0.00 (corrected after payout analysis)</li>
                    <li><strong>Expected Transactions:</strong> 5 (dates: 1, 4, 15, 17, 19)</li>
                    <li><strong>Processing Logic:</strong> Same as debugged complete_csv_service.py</li>
                </ul>
            </div>
            
            <div>
                <a href="/csv-input" class="button">🚀 Open CSV Input UI</a>
                <a href="/csv-input/api/validate" class="button api-button">🔍 API Documentation</a>
            </div>
            
            <div class="info">
                <h3>📋 Quick Start</h3>
                <ol>
                    <li>Click "Open CSV Input UI" above</li>
                    <li>Drag & drop your Stripe CSV file</li>
                    <li>Verify settings (CGGE, August 2025, Balance: 0.00)</li>
                    <li>Click "Process CSV" to analyze</li>
                    <li>Review results and export if needed</li>
                </ol>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {
        'status': 'ok',
        'service': 'CSV Input UI Server',
        'endpoints': [
            '/csv-input',
            '/csv-input/api/process',
            '/csv-input/api/validate'
        ]
    }

if __name__ == '__main__':
    print("🚀 Starting Stripe CSV Input UI Server...")
    print("📍 Access at: http://localhost:5001")
    print("🎯 CSV Input UI: http://localhost:5001/csv-input")
    print("🔍 API Health: http://localhost:5001/health")
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        threaded=True
    )
