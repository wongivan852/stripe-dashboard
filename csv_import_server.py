#!/usr/bin/env python3
"""
Standalone CSV Import Server for Stripe Dashboard
Runs on port 8007 and provides CSV import functionality
"""
import os
import sys

# Set environment before imports
os.environ['DATABASE_URL'] = 'sqlite:////opt/stripe-dashboard/instance/payments.db'

# Add stripe dashboard to path
sys.path.insert(0, '/opt/stripe-dashboard')
sys.path.insert(0, '/home/user/stripe-dashboard')

from flask import Flask, request, jsonify, render_template_string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'csv-import-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Import the app factory's db instance
from app import db
db.init_app(app)

# Import models
from app.models import StripeAccount, Transaction

# Import CSV import functionality
from csv_import_route import import_csv_files

@app.route('/')
def home():
    """Home page with CSV import form"""
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stripe CSV Import</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f8fafc;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
                border-radius: 12px;
                margin-bottom: 30px;
            }
            .card {
                background: white;
                border-radius: 12px;
                padding: 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                font-weight: 600;
                margin-bottom: 8px;
                color: #334155;
            }
            select, input[type="file"] {
                width: 100%;
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 14px;
            }
            .btn {
                background: #4f46e5;
                color: white;
                padding: 14px 28px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: all 0.2s;
            }
            .btn:hover {
                background: #4338ca;
                transform: translateY(-1px);
            }
            .btn:disabled {
                background: #94a3b8;
                cursor: not-allowed;
                transform: none;
            }
            .message {
                padding: 16px;
                border-radius: 8px;
                margin: 20px 0;
            }
            .message.success {
                background: #dcfce7;
                border: 2px solid #22c55e;
                color: #166534;
            }
            .message.error {
                background: #fef2f2;
                border: 2px solid #ef4444;
                color: #991b1b;
            }
            .message.info {
                background: #dbeafe;
                border: 2px solid #3b82f6;
                color: #1e40af;
            }
            .file-list {
                margin-top: 10px;
                padding: 10px;
                background: #f8fafc;
                border-radius: 6px;
                font-size: 14px;
            }
            .loader {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #4f46e5;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .hidden {
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Stripe CSV Import</h1>
                <p>Import transaction data from CSV files</p>
            </div>

            <div class="card">
                <form id="import-form" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="company">Company Account:</label>
                        <select id="company" name="company" required>
                            <option value="CGGE">CGGE</option>
                            <option value="Krystal Institute">Krystal Institute</option>
                            <option value="Krystal Technology">Krystal Technology</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="csv-files">Select CSV Files (Multiple files allowed):</label>
                        <input type="file" id="csv-files" name="csv_files[]" accept=".csv" multiple required>
                        <div id="file-list" class="file-list hidden"></div>
                    </div>

                    <button type="submit" class="btn" id="submit-btn">
                        Import CSV Files
                    </button>
                </form>

                <div id="loader" class="loader hidden"></div>
                <div id="message"></div>
            </div>

            <div class="card">
                <h3>📋 Instructions</h3>
                <ol>
                    <li>Select the company account (CGGE, KI, or KT)</li>
                    <li>Choose one or more CSV files to import</li>
                    <li>Click "Import CSV Files" to start the import</li>
                    <li>The system will automatically skip duplicate transactions</li>
                </ol>
                <p><strong>Supported CSV formats:</strong></p>
                <ul>
                    <li>Unified payments (from Stripe dashboard)</li>
                    <li>Itemised balance change from activity</li>
                    <li>Itemised payouts</li>
                    <li>Balance summary</li>
                </ul>
            </div>
        </div>

        <script>
            const form = document.getElementById('import-form');
            const fileInput = document.getElementById('csv-files');
            const fileList = document.getElementById('file-list');
            const message = document.getElementById('message');
            const loader = document.getElementById('loader');
            const submitBtn = document.getElementById('submit-btn');

            fileInput.addEventListener('change', function() {
                if (this.files.length > 0) {
                    fileList.classList.remove('hidden');
                    fileList.innerHTML = '<strong>Selected files:</strong><br>';
                    for (let i = 0; i < this.files.length; i++) {
                        fileList.innerHTML += `${i + 1}. ${this.files[i].name} (${(this.files[i].size / 1024).toFixed(2)} KB)<br>`;
                    }
                } else {
                    fileList.classList.add('hidden');
                }
            });

            form.addEventListener('submit', async function(e) {
                e.preventDefault();

                const files = fileInput.files;
                if (files.length === 0) {
                    showMessage('Please select at least one CSV file', 'error');
                    return;
                }

                const formData = new FormData();
                formData.append('company', document.getElementById('company').value);
                
                for (let i = 0; i < files.length; i++) {
                    formData.append('csv_files[]', files[i]);
                }

                // Show loader
                loader.classList.remove('hidden');
                message.innerHTML = '';
                submitBtn.disabled = true;

                try {
                    const response = await fetch('/api/import', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (data.success) {
                        let msg = `<strong>${data.message}</strong><br><br>`;
                        msg += `<strong>Summary:</strong><br>`;
                        msg += `✅ Imported: ${data.total_imported}<br>`;
                        msg += `⏭️ Skipped (duplicates): ${data.total_skipped}<br>`;
                        msg += `❌ Errors: ${data.total_errors}<br>`;
                        
                        if (data.file_results && data.file_results.length > 0) {
                            msg += `<br><strong>Per File:</strong><br>`;
                            data.file_results.forEach(file => {
                                msg += `<br><strong>${file.filename}:</strong><br>`;
                                msg += `  Imported: ${file.imported}, Skipped: ${file.skipped}`;
                                if (file.errors > 0) {
                                    msg += `, Errors: ${file.errors}`;
                                }
                            });
                        }
                        
                        showMessage(msg, 'success');
                    } else {
                        showMessage(`<strong>Import failed:</strong><br>${data.error || 'Unknown error'}`, 'error');
                    }
                } catch (error) {
                    showMessage(`<strong>Import failed:</strong><br>${error.message}`, 'error');
                } finally {
                    loader.classList.add('hidden');
                    submitBtn.disabled = false;
                }
            });

            function showMessage(text, type) {
                message.className = `message ${type}`;
                message.innerHTML = text;
            }
        </script>
    </body>
    </html>
    ''')

@app.route('/api/import', methods=['POST'])
def api_import():
    """API endpoint for CSV import"""
    try:
        if 'csv_files[]' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No files selected'
            }), 400
        
        files = request.files.getlist('csv_files[]')
        company = request.form.get('company', 'CGGE')
        
        logger.info(f"Importing {len(files)} files for company {company}")
        
        result = import_csv_files(files, company, db, StripeAccount, Transaction)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.error(f"CSV import failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        account_count = StripeAccount.query.count()
        transaction_count = Transaction.query.count()
        
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'accounts': account_count,
            'transactions': transaction_count
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting CSV Import Server")
    print("=" * 60)
    print(f"   URL: http://0.0.0.0:8007")
    print(f"   Network: http://192.168.0.104:8007")
    print(f"   Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=8007,
        debug=False,
        threaded=True
    )
