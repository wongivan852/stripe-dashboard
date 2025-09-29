#!/usr/bin/env python3
"""
Import test data from CSV files into the Stripe Dashboard database
"""

import os
import csv
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.stripe_account import StripeAccount
from app.models.transaction import Transaction

def parse_amount(amount_str):
    """Convert amount string to cents (integer)"""
    try:
        if not amount_str or amount_str == '':
            return 0
        # Remove commas and convert to float, then to cents
        amount_float = float(str(amount_str).replace(',', ''))
        return int(amount_float * 100)  # Convert to cents
    except (ValueError, TypeError):
        return 0

def parse_datetime(date_str):
    """Parse datetime string from CSV"""
    if not date_str or date_str == '':
        return None
    try:
        # Try different date formats
        formats = [
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y %H:%M',
            '%m/%d/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # If none work, return current time
        print(f"Warning: Could not parse date '{date_str}', using current time")
        return datetime.utcnow()
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        return datetime.utcnow()

def get_or_create_account(name, account_prefix):
    """Get or create a Stripe account"""
    account = StripeAccount.query.filter_by(name=name).first()
    if not account:
        account = StripeAccount(
            name=name,
            api_key=f"sk_test_{account_prefix}_dummy_key",
            account_id=f"acct_{account_prefix}123456789"
        )
        db.session.add(account)
        db.session.flush()  # Get the ID
        print(f"✅ Created account: {name}")
    return account

def import_csv_file(file_path, account_name, account_prefix):
    """Import a single CSV file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return 0
    
    print(f"\n📁 Importing {file_path}")
    
    # Get or create the account
    account = get_or_create_account(account_name, account_prefix)
    
    imported_count = 0
    error_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            # Detect if file uses quotes
            sample = file.read(1024)
            file.seek(0)
            
            # Use appropriate CSV reader
            if '"' in sample:
                reader = csv.DictReader(file, quotechar='"')
            else:
                reader = csv.DictReader(file)
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                try:
                    # Clean up field names (remove quotes if present)
                    clean_row = {}
                    for key, value in row.items():
                        clean_key = key.strip(' "')
                        clean_value = value.strip(' "') if isinstance(value, str) else value
                        clean_row[clean_key] = clean_value
                    
                    # Extract required fields
                    stripe_id = clean_row.get('id', '').strip()
                    if not stripe_id:
                        print(f"⚠️  Row {row_num}: Missing transaction ID, skipping")
                        continue
                    
                    # Check if transaction already exists
                    if Transaction.query.filter_by(stripe_id=stripe_id).first():
                        continue  # Skip duplicates
                    
                    # Parse amount and fee
                    amount = parse_amount(clean_row.get('Amount', '0'))
                    fee = parse_amount(clean_row.get('Fee', '0'))
                    
                    # Get other fields
                    currency = clean_row.get('Currency', 'hkd').lower()
                    transaction_type = clean_row.get('Type', 'unknown')
                    description = clean_row.get('Description', '')
                    
                    # Parse created date
                    created_date = parse_datetime(clean_row.get('Created (UTC)', ''))
                    
                    # Build metadata from extra fields
                    metadata = {}
                    for key, value in clean_row.items():
                        if 'metadata' in key.lower() and value:
                            metadata[key] = value
                    
                    # Add source and other useful fields to metadata
                    if clean_row.get('Source'):
                        metadata['source'] = clean_row.get('Source')
                    if clean_row.get('Transfer'):
                        metadata['transfer'] = clean_row.get('Transfer')
                    if clean_row.get('Customer Facing Amount'):
                        metadata['customer_facing_amount'] = clean_row.get('Customer Facing Amount')
                    
                    # Create transaction
                    transaction = Transaction(
                        stripe_id=stripe_id,
                        account_id=account.id,
                        amount=amount,
                        fee=fee,
                        currency=currency,
                        status='succeeded',  # Assume succeeded for historical data
                        type=transaction_type,
                        stripe_created=created_date or datetime.utcnow(),
                        description=description,
                        stripe_metadata=metadata if metadata else None
                    )
                    
                    db.session.add(transaction)
                    imported_count += 1
                    
                    # Commit every 50 transactions to avoid memory issues
                    if imported_count % 50 == 0:
                        db.session.commit()
                        print(f"  📊 Imported {imported_count} transactions...")
                
                except Exception as e:
                    error_count += 1
                    print(f"⚠️  Row {row_num}: Error processing transaction: {e}")
                    continue
        
        # Final commit
        db.session.commit()
        print(f"✅ Successfully imported {imported_count} transactions from {account_name}")
        if error_count > 0:
            print(f"⚠️  {error_count} rows had errors and were skipped")
            
    except Exception as e:
        print(f"❌ Error reading file {file_path}: {e}")
        db.session.rollback()
        return 0
    
    return imported_count

def main():
    """Main import function"""
    print("🔄 Starting test data import for Stripe Dashboard...")
    
    app = create_app()
    
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        total_imported = 0
        
        # Import data from complete_csv files
        csv_files = [
            ('complete_csv/cgge_2021_Nov-2025_Jul.csv', 'CGGE Media', 'cgge'),
            ('complete_csv/ki_2023_Jul-2025_Jul.csv', 'Krystal Intelligence', 'ki'),
            ('complete_csv/kt_2022_Sept-2025_Jul.csv', 'Krystal Technologies', 'kt')
        ]
        
        for file_path, account_name, account_prefix in csv_files:
            full_path = os.path.join(os.path.dirname(__file__), file_path)
            imported = import_csv_file(full_path, account_name, account_prefix)
            total_imported += imported
        
        print(f"\n🎉 Import completed!")
        print(f"📊 Total transactions imported: {total_imported}")
        
        # Display summary statistics
        print(f"\n📈 Database Summary:")
        account_count = StripeAccount.query.count()
        transaction_count = Transaction.query.count()
        
        print(f"  - Stripe Accounts: {account_count}")
        print(f"  - Total Transactions: {transaction_count}")
        
        # Show account breakdown
        for account in StripeAccount.query.all():
            trans_count = Transaction.query.filter_by(account_id=account.id).count()
            total_amount = db.session.query(db.func.sum(Transaction.amount)).filter_by(account_id=account.id).scalar() or 0
            print(f"  - {account.name}: {trans_count} transactions, Total: {total_amount/100:.2f} HKD")

if __name__ == '__main__':
    main()
