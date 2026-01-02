#!/usr/bin/env python3
"""
CSV Import Route for Stripe Dashboard
This module provides CSV import functionality that can be added to the main app
"""
import os
import csv
import hashlib
import logging
from datetime import datetime
from flask import request, jsonify
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_csv_row(row, account_id):
    """Parse a CSV row into transaction data - handles multiple CSV formats"""
    try:
        # Format 1: Unified payments format (cgge_unified_payments_till_30Nov2025.csv)
        if 'id' in row and 'Created date (UTC)' in row:
            stripe_id = row.get('id', '').strip()
            if not stripe_id:
                # Generate unique ID for rows without ID
                unique_str = f"{row.get('Created date (UTC)')}_{row.get('Amount')}_{row.get('Customer Email')}_{row.get('Description')}"
                stripe_id = f"csv_{hashlib.md5(unique_str.encode()).hexdigest()[:16]}"
            
            amount_str = row.get('Amount', '0').replace(',', '').strip()
            amount = float(amount_str) if amount_str else 0
            
            fee_str = row.get('Fee', '0').replace(',', '').strip()
            fee = float(fee_str) if fee_str else 0
            
            currency = row.get('Currency', 'hkd').lower().strip()
            
            # Parse date - handle multiple formats
            date_str = row.get('Created date (UTC)', '').strip()
            if not date_str:
                return None
                
            try:
                stripe_created = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except:
                try:
                    stripe_created = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    logger.warning(f"Could not parse date: {date_str}")
                    return None
            
            status = row.get('Status', 'succeeded').lower().strip()
            if not status:
                status = 'succeeded'
                
            customer_email = row.get('Customer Email', '').strip()
            description = row.get('Description', '').strip()
            
            return {
                'stripe_id': stripe_id,
                'account_id': account_id,
                'amount': int(amount * 100),  # Convert to cents
                'fee': int(fee * 100),  # Convert to cents
                'currency': currency,
                'status': status,
                'type': 'charge',
                'stripe_created': stripe_created,
                'customer_email': customer_email if customer_email else None,
                'description': description if description else None
            }
        
        # Format 2: Itemised balance change format
        elif 'Created (UTC)' in row and 'Gross' in row:
            stripe_id = row.get('id', '').strip()
            if not stripe_id:
                unique_str = f"{row.get('Created (UTC)')}_{row.get('Gross')}_{row.get('Reporting Category')}"
                stripe_id = f"csv_{hashlib.md5(unique_str.encode()).hexdigest()[:16]}"
            
            gross_str = row.get('Gross', '0').replace(',', '').strip()
            gross = float(gross_str) if gross_str else 0
            
            fee_str = row.get('Fee', '0').replace(',', '').strip()
            fee = float(fee_str) if fee_str else 0
            
            currency = row.get('Currency', 'hkd').lower().strip()
            
            date_str = row.get('Created (UTC)', '').strip()
            if not date_str:
                return None
                
            try:
                stripe_created = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
            except:
                try:
                    stripe_created = datetime.strptime(date_str, '%Y-%m-%d')
                except:
                    logger.warning(f"Could not parse date: {date_str}")
                    return None
            
            reporting_category = row.get('Reporting Category', '').strip()
            description = row.get('Description', reporting_category).strip()
            
            return {
                'stripe_id': stripe_id,
                'account_id': account_id,
                'amount': int(gross * 100),
                'fee': int(abs(fee) * 100),
                'currency': currency,
                'status': 'succeeded',
                'type': reporting_category.lower() if reporting_category else 'charge',
                'stripe_created': stripe_created,
                'customer_email': None,
                'description': description if description else None
            }
        
        # Format 3: Payout format - skip summary rows
        elif 'Automatic payout id' in row or 'Payout id' in row:
            return None
        
        # Format 4: Balance Summary - skip
        elif 'Balance' in row and 'Currency' in row and len(row.keys()) < 5:
            return None
        
        return None
    
    except Exception as e:
        logger.error(f"Error parsing CSV row: {e}")
        return None

def import_csv_files(files, company, db, StripeAccount, Transaction):
    """
    Import CSV files into database
    
    Args:
        files: List of FileStorage objects from request.files
        company: Company name (e.g., 'CGGE')
        db: SQLAlchemy database instance
        StripeAccount: StripeAccount model
        Transaction: Transaction model
    
    Returns:
        dict: Results dictionary with import statistics
    """
    if not files or len(files) == 0:
        return {
            'success': False,
            'error': 'No files provided'
        }
    
    # Get or create the account
    account = StripeAccount.query.filter_by(name=company).first()
    if not account:
        account = StripeAccount(name=company, is_active=True)
        db.session.add(account)
        db.session.commit()
    
    total_imported = 0
    total_skipped = 0
    total_errors = 0
    file_results = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            try:
                # Read CSV file
                file_content = file.read().decode('utf-8')
                csv_reader = csv.DictReader(file_content.splitlines())
                
                imported = 0
                skipped = 0
                errors = 0
                
                for row in csv_reader:
                    try:
                        # Parse transaction from CSV row
                        transaction_data = parse_csv_row(row, account.id)
                        
                        if transaction_data:
                            # Check if transaction already exists
                            existing = Transaction.query.filter_by(
                                stripe_id=transaction_data['stripe_id']
                            ).first()
                            
                            if existing:
                                skipped += 1
                            else:
                                transaction = Transaction(**transaction_data)
                                db.session.add(transaction)
                                imported += 1
                    
                    except Exception as row_error:
                        logger.error(f"Error parsing row in {filename}: {row_error}")
                        errors += 1
                
                # Commit transactions for this file
                db.session.commit()
                
                total_imported += imported
                total_skipped += skipped
                total_errors += errors
                
                file_results.append({
                    'filename': filename,
                    'imported': imported,
                    'skipped': skipped,
                    'errors': errors,
                    'status': 'success'
                })
            
            except Exception as file_error:
                logger.error(f"Error processing file {filename}: {file_error}")
                total_errors += 1
                file_results.append({
                    'filename': filename,
                    'imported': 0,
                    'skipped': 0,
                    'errors': 1,
                    'status': 'error',
                    'error': str(file_error)
                })
    
    # Build response message
    if total_imported == 0 and total_skipped > 0:
        message = f"All {total_skipped} transactions from {len(files)} files already exist in the database for account \"{company}\". No duplicates were imported. This is normal if you've uploaded these files before."
    elif total_imported > 0:
        message = f"Successfully imported {total_imported} new transactions from {len(files)} files for account \"{company}\"."
        if total_skipped > 0:
            message += f" {total_skipped} duplicate transactions were skipped."
    else:
        message = f"No transactions were imported from {len(files)} files."
        if total_errors > 0:
            message += f" {total_errors} errors occurred."
    
    return {
        'success': True,
        'message': message,
        'total_imported': total_imported,
        'total_skipped': total_skipped,
        'total_errors': total_errors,
        'file_results': file_results
    }

def create_import_route(bp, db, StripeAccount, Transaction):
    """
    Create and register the CSV import route
    
    Args:
        bp: Flask Blueprint
        db: SQLAlchemy database instance
        StripeAccount: StripeAccount model
        Transaction: Transaction model
    """
    
    @bp.route('/import-csv', methods=['POST'])
    def import_csv():
        """Import CSV data into database - supports multiple files"""
        try:
            # Check if files were uploaded
            if 'csv_files[]' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No files selected. Please select CSV files to import.'
                }), 400
            
            files = request.files.getlist('csv_files[]')
            company = request.form.get('company', 'CGGE')
            
            # Perform import
            result = import_csv_files(files, company, db, StripeAccount, Transaction)
            
            if result.get('success'):
                return jsonify(result)
            else:
                return jsonify(result), 400
        
        except Exception as e:
            logger.error(f"CSV import failed: {e}")
            return jsonify({
                'success': False,
                'error': f'Import failed: {str(e)}'
            }), 500
    
    return import_csv
