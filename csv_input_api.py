from flask import Blueprint, request, jsonify, render_template_string
import csv
import io
from datetime import datetime
from decimal import Decimal
import logging

# Create blueprint for CSV input UI
csv_input_bp = Blueprint('csv_input', __name__)

logger = logging.getLogger(__name__)

@csv_input_bp.route('/csv-input')
def csv_input_interface():
    """Serve the CSV input UI"""
    try:
        with open('stripe_csv_input_ui.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Return a simple version if file not found
        return render_template_string("""
        <html>
        <head><title>CSV Input Interface</title></head>
        <body>
        <h1>Stripe CSV Input Interface</h1>
        <p>The main interface file is not available. Please ensure stripe_csv_input_ui.html exists.</p>
        <p><a href="/csv-input/api/process">API Endpoint: /csv-input/api/process</a></p>
        </body>
        </html>
        """)

@csv_input_bp.route('/csv-input/api/process', methods=['POST'])
def process_csv_api():
    """API endpoint to process CSV data"""
    try:
        # Handle file upload or raw CSV data
        csv_content = None
        
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                csv_content = file.read().decode('utf-8')
            else:
                return jsonify({'success': False, 'error': 'Invalid file type. Please upload a CSV file.'}), 400
        elif 'csv_data' in request.json:
            csv_content = request.json['csv_data']
        else:
            return jsonify({'success': False, 'error': 'No CSV data provided'}), 400
        
        # Get processing configuration
        config = request.json if request.is_json else request.form.to_dict()
        
        # Default configuration
        processing_config = {
            'company': config.get('company', 'cgge'),
            'year': int(config.get('year', 2025)),
            'month': int(config.get('month', 8)),
            'opening_balance': float(config.get('opening_balance', 0.0)),
            'skip_invalid': config.get('skip_invalid', 'true').lower() == 'true',
            'generate_synthetic': config.get('generate_synthetic', 'false').lower() == 'true',
            'validate_balances': config.get('validate_balances', 'true').lower() == 'true',
            'allowed_dates': None,
            'payouts': config.get('payouts', [])  # Added payout data
        }
        
        # Parse allowed dates for August 2025 CGGE
        if (processing_config['year'] == 2025 and 
            processing_config['month'] == 8 and 
            processing_config['company'] == 'cgge'):
            allowed_dates_str = config.get('allowed_dates', '1,4,15,17,19')
            processing_config['allowed_dates'] = [int(d.strip()) for d in allowed_dates_str.split(',') if d.strip().isdigit()]
        
        # Process the CSV data
        result = process_csv_data(csv_content, processing_config)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"CSV processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500

def process_csv_data(csv_content, config):
    """Process CSV data using the same logic as complete_csv_service"""
    
    # Parse CSV content
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    transactions = []
    skipped = 0
    errors = []
    
    for index, row in enumerate(rows):
        try:
            # Parse date - handle "Created date (UTC)" column
            date_str = (row.get('Created date (UTC)') or row.get('Created (UTC)', '')).strip()
            if not date_str:
                if not config['skip_invalid']:
                    errors.append(f'Row {index + 1}: Missing date')
                skipped += 1
                continue
                
            try:
                # Parse datetime format "YYYY-MM-DD HH:MM:SS"
                created_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # Try alternative format
                    created_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except ValueError:
                    if not config['skip_invalid']:
                        errors.append(f'Row {index + 1}: Invalid date format: {date_str}')
                    skipped += 1
                    continue
            
            # Filter by year and month
            if created_date.year != config['year'] or created_date.month != config['month']:
                skipped += 1
                continue
            
            # Check allowed dates
            if config['allowed_dates'] and created_date.day not in config['allowed_dates']:
                skipped += 1
                continue
            
            # Skip invalid transactions (empty ID or zero amounts)
            transaction_id = (row.get('id', '') or '').strip()
            amount_str = (row.get('Converted Amount') or row.get('Amount') or '0').strip()
            
            if not transaction_id and config['skip_invalid']:
                skipped += 1
                continue
                
            try:
                amount = float(amount_str) if amount_str else 0.0
            except ValueError:
                amount = 0.0
                
            if amount == 0 and config['skip_invalid']:
                skipped += 1
                continue
            
            # Process fee
            fee_str = (row.get('Fee') or '0').strip()
            try:
                fee = float(fee_str) if fee_str else 0.0
            except ValueError:
                fee = 0.0
            
            net = amount - fee
            
            transaction = {
                'id': transaction_id or f'generated_{index}',
                'created': created_date.isoformat(),
                'date': created_date.strftime('%Y-%m-%d'),
                'amount': round(amount, 2),
                'fee': round(fee, 2),
                'net': round(net, 2),
                'currency': (row.get('Converted Currency') or row.get('Currency') or 'hkd').lower(),
                'status': row.get('Status', ''),
                'description': row.get('Description', ''),
                'customer_email': row.get('Customer Email', ''),
                'metadata': {
                    'stripe_plan': row.get('stripe_plan (metadata)', ''),
                    'site': row.get('1. Site (metadata)', '') or row.get('site (metadata)', ''),
                    'user_email': row.get('2. User email (metadata)', ''),
                    'active_date': row.get('3. Active date (metadata)', ''),
                    'expiry_date': row.get('4. Expiry date (metadata)', '')
                },
                'raw_row': dict(row)  # Store original row for reference
            }
            transactions.append(transaction)
            
        except Exception as e:
            errors.append(f'Row {index + 1}: {str(e)}')
            skipped += 1
            continue
    
    # Sort transactions by date
    transactions.sort(key=lambda x: x['created'])
    
    # Calculate running balances
    running_balance = Decimal(str(config['opening_balance']))
    
    for tx in transactions:
        net = Decimal(str(tx['net']))
        running_balance += net
        tx['running_balance'] = float(running_balance)
    
    # Calculate summary
    total_amount = sum(tx['amount'] for tx in transactions)
    total_fees = sum(tx['fee'] for tx in transactions)
    total_net = sum(tx['net'] for tx in transactions)
    
    # Process payout data if provided
    payout_summary = None
    if config.get('payouts'):
        payouts = config['payouts']
        payout_total = sum(float(p.get('amount', 0)) for p in payouts)
        
        payout_summary = {
            'total_entries': len(payouts),
            'total_amount': payout_total,
            'entries': payouts,
            'reconciliation': {
                'transaction_net': total_net,
                'payout_amount': payout_total,
                'difference': total_net - payout_total,
                'reconciled': abs(total_net - payout_total) < 0.01
            }
        }
    
    return {
        'success': True,
        'config': config,
        'summary': {
            'opening_balance': config['opening_balance'],
            'closing_balance': round(config['opening_balance'] + total_net, 2),
            'total_transactions': len(transactions),
            'total_amount': round(total_amount, 2),
            'total_fees': round(total_fees, 2),
            'total_net': round(total_net, 2),
            'processed_rows': len(rows),
            'skipped_rows': skipped
        },
        'transactions': transactions,
        'payout_summary': payout_summary,
        'errors': errors[:50]  # Limit errors to prevent large responses
    }

@csv_input_bp.route('/csv-input/api/validate', methods=['POST'])
def validate_csv_api():
    """API endpoint to validate CSV structure without processing"""
    try:
        csv_content = request.json.get('csv_data', '')
        
        if not csv_content:
            return jsonify({'success': False, 'error': 'No CSV data provided'}), 400
        
        # Parse CSV headers
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        headers = csv_reader.fieldnames
        
        if not headers:
            return jsonify({'success': False, 'error': 'No headers found in CSV'}), 400
        
        # Check for required columns
        required_columns = ['id', 'Created date (UTC)', 'Amount', 'Fee']
        alternative_columns = {
            'Created date (UTC)': ['Created (UTC)', 'Created'],
            'Amount': ['Converted Amount', 'Gross'],
            'Fee': ['Processing Fee', 'Stripe Fee']
        }
        
        missing_columns = []
        found_columns = {}
        
        for req_col in required_columns:
            found = False
            for header in headers:
                if header == req_col:
                    found_columns[req_col] = header
                    found = True
                    break
                elif req_col in alternative_columns:
                    for alt in alternative_columns[req_col]:
                        if header == alt:
                            found_columns[req_col] = header
                            found = True
                            break
            
            if not found:
                missing_columns.append(req_col)
        
        # Count rows
        rows = list(csv_reader)
        row_count = len(rows)
        
        return jsonify({
            'success': True,
            'validation': {
                'headers': headers,
                'found_columns': found_columns,
                'missing_columns': missing_columns,
                'row_count': row_count,
                'is_valid': len(missing_columns) == 0
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Validation error: {str(e)}'}), 500

# Template for integration into main Flask app
def register_csv_input_routes(app):
    """Register CSV input routes with the main Flask app"""
    app.register_blueprint(csv_input_bp)
    app.logger.info("CSV Input routes registered successfully")
