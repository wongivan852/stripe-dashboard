import os
import csv
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

class CSVTransactionService:
    """Service to read transaction data from new_csv directory"""
    
    def __init__(self, csv_directory="/Users/wongivan/stripe-dashboard/new_csv"):
        self.csv_directory = csv_directory
        self.company_names = {
            "cgge": "CGGE", 
            "krystal_institute": "Krystal Institute",
            "krystal_technology": "Krystal Technology"
        }
    
    def get_all_transactions(self, company_filter=None, status_filter=None, from_date=None, to_date=None, period=None):
        """Get all transactions from CSV files with optional filtering"""
        transactions = []
        
        # Handle different period types
        if period and period.isdigit():
            # Period specified as number of days
            days = int(period)
            to_date = datetime.now().date()
            from_date = to_date - timedelta(days=days)
        elif period == 'preset-nov2021':
            # November 2021 preset
            from_date = datetime(2021, 11, 1).date()
            to_date = datetime(2021, 11, 30).date()
        elif period == 'preset-2021':
            # Full year 2021 preset
            from_date = datetime(2021, 1, 1).date()
            to_date = datetime(2021, 12, 31).date()
        else:
            # Convert string dates to date objects
            if from_date and isinstance(from_date, str):
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            if to_date and isinstance(to_date, str):
                to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
        
        # Find all itemized balance change CSV files from all company directories
        csv_files = []
        
        # Check if using new directory structure with company subdirectories
        company_dirs = ['cgge', 'krystal_institute', 'krystal_technology']
        has_company_dirs = all(os.path.isdir(os.path.join(self.csv_directory, dir_name)) for dir_name in company_dirs)
        
        if has_company_dirs:
            # New structure: read from company subdirectories
            for company_dir in company_dirs:
                company_path = os.path.join(self.csv_directory, company_dir)
                pattern = os.path.join(company_path, "Itemised_balance_change_from_activity_*.csv")
                company_files = glob.glob(pattern)
                # Add company info to file path for later processing
                for file_path in company_files:
                    csv_files.append((file_path, company_dir))
        else:
            # Old structure: read from root directory
            pattern = os.path.join(self.csv_directory, "Itemised_balance_change_from_activity_*.csv")
            root_files = glob.glob(pattern)
            for file_path in root_files:
                csv_files.append((file_path, None))
        
        for csv_file_info in csv_files:
            if isinstance(csv_file_info, tuple):
                csv_file, company_dir = csv_file_info
            else:
                csv_file, company_dir = csv_file_info, None
            transactions.extend(self._read_csv_file(csv_file, company_filter, status_filter, from_date, to_date, company_dir))
        
        # Sort by created date (newest first)
        transactions.sort(key=lambda x: x['created'], reverse=True)
        
        return transactions
    
    def _read_csv_file(self, csv_file, company_filter, status_filter, from_date, to_date, company_dir=None):
        """Read transactions from a single CSV file"""
        transactions = []
        
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    # Skip empty rows
                    if not row.get('balance_transaction_id'):
                        continue
                        
                    transaction = self._parse_csv_row(row, company_dir)
                    
                    # Apply filters
                    if self._should_include_transaction(transaction, company_filter, status_filter, from_date, to_date):
                        transactions.append(transaction)
                        
        except Exception as e:
            print(f"Error reading CSV file {csv_file}: {str(e)}")
            
        return transactions
    
    def _parse_csv_row(self, row, company_dir=None):
        """Parse a CSV row into transaction format"""
        # Parse the created date
        created_str = row.get('created', '')
        try:
            created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
        except:
            created = None
            
        # Parse available_on date
        available_on_str = row.get('available_on', '')
        try:
            available_on = datetime.strptime(available_on_str, '%Y-%m-%d %H:%M:%S').date()
        except:
            try:
                available_on = datetime.strptime(available_on_str, '%Y-%m-%d').date()
            except:
                available_on = None
        
        # Determine company name based on directory structure or description
        if company_dir:
            # Use directory name to determine company
            company_name = self._get_company_name_from_dir(company_dir)
        else:
            # Fall back to extracting from description
            description = row.get('description', '')
            company_name = self._extract_company_from_description(description)
        
        # Parse amounts
        try:
            gross = float(row.get('gross', 0))
            fee = float(row.get('fee', 0))
            net = float(row.get('net', 0))
        except:
            gross = fee = net = 0
            
        # Extract customer email if available (might be in description)
        description = row.get('description', '')
        customer_email = self._extract_customer_email(description)
        
        # Map reporting category to status
        status = self._map_category_to_status(row.get('reporting_category', ''))
        
        return {
            'id': row.get('balance_transaction_id', ''),
            'stripe_id': row.get('balance_transaction_id', ''),
            'amount': gross,
            'fee': fee,
            'net_amount': net,
            'currency': row.get('currency', 'hkd').upper(),
            'status': status,
            'type': row.get('reporting_category', 'charge'),
            'description': description,
            'customer_email': customer_email,
            'created': created,
            'stripe_created': created,
            'available_on': available_on,
            'account_name': company_name,
            'company_id': self._get_company_id(company_name),
            'reporting_category': row.get('reporting_category', '')
        }
    
    def _get_company_name_from_dir(self, company_dir):
        """Map directory name to company name"""
        dir_to_company = {
            'cgge': 'CGGE',
            'krystal_institute': 'Krystal Institute',
            'krystal_technology': 'Krystal Technology'
        }
        return dir_to_company.get(company_dir, 'Unknown Company')
    
    def _extract_company_from_description(self, description):
        """Extract company name from transaction description"""
        description_upper = description.upper()
        
        # If description is empty, try to determine from file context or default mapping
        if not description.strip():
            return 'Combined Account'  # Default for files without description
        
        if 'CG GLOBAL ENTERTAINMENT' in description_upper or 'CGGE' in description_upper:
            return 'CGGE'
        elif 'KRYSTAL INSTITUTE' in description_upper:
            return 'Krystal Institute'
        elif 'KRYSTAL TECHNOLOGY' in description_upper or 'KRYSTAL TECH' in description_upper:
            return 'Krystal Technology'
        else:
            # If no company found in description, use a default
            return 'Combined Account'
    
    def _get_company_id(self, company_name):
        """Map company name to ID for compatibility"""
        company_map = {
            'CGGE': 1,
            'Krystal Institute': 2,
            'Krystal Technology': 3,
            'Combined Account': 4,
            'Unknown Company': 0
        }
        return company_map.get(company_name, 0)
    
    def _extract_customer_email(self, description):
        """Try to extract customer email from description"""
        # Look for email pattern in description
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        matches = re.findall(email_pattern, description)
        return matches[0] if matches else 'N/A'
    
    def _map_category_to_status(self, category):
        """Map reporting category to transaction status"""
        category_lower = category.lower()
        if category_lower == 'charge':
            return 'succeeded'
        elif category_lower in ['refund', 'chargeback']:
            return 'refunded'
        elif category_lower == 'payout':
            return 'paid'
        else:
            return 'succeeded'  # Default status
    
    def _should_include_transaction(self, transaction, company_filter, status_filter, from_date, to_date):
        """Check if transaction should be included based on filters"""
        # Company filter
        if company_filter and company_filter != 'all':
            try:
                company_id = int(company_filter)
                if transaction['company_id'] != company_id:
                    return False
            except:
                pass
        
        # Status filter
        if status_filter and status_filter != 'all':
            if transaction['status'] != status_filter:
                return False
        
        # Date range filter
        if transaction['created']:
            tx_date = transaction['created'].date()
            
            if from_date and tx_date < from_date:
                return False
            if to_date and tx_date > to_date:
                return False
        
        return True
    
    def get_account_summary(self, company_filter=None, status_filter=None, from_date=None, to_date=None, period=None):
        """Get summary statistics for accounts"""
        transactions = self.get_all_transactions(company_filter, status_filter, from_date, to_date, period)
        
        total_amount = sum(tx['amount'] for tx in transactions)
        total_fees = sum(tx['fee'] for tx in transactions)
        total_net = sum(tx['net_amount'] for tx in transactions)
        
        # Count by status
        status_counts = {}
        for tx in transactions:
            status = tx['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by company
        company_counts = {}
        company_amounts = {}
        for tx in transactions:
            company = tx['account_name']
            company_counts[company] = company_counts.get(company, 0) + 1
            company_amounts[company] = company_amounts.get(company, 0) + tx['amount']
        
        return {
            'total_transactions': len(transactions),
            'total_amount': total_amount,
            'total_fees': total_fees,
            'total_net': total_net,
            'status_counts': status_counts,
            'company_counts': company_counts,
            'company_amounts': company_amounts,
            'transactions': transactions
        }
    
    def get_available_companies(self):
        """Get list of available companies from CSV data"""
        companies = []
        
        # Always provide the three main companies even if no data is found yet
        predefined_companies = [
            {'id': 1, 'name': 'CGGE'},
            {'id': 2, 'name': 'Krystal Institute'},
            {'id': 3, 'name': 'Krystal Technology'}
        ]
        
        # Get companies that have actual transactions
        sample_transactions = self.get_all_transactions()[:100]  # Sample for existing companies
        actual_companies = set()
        
        for tx in sample_transactions:
            company_id = tx['company_id']
            company_name = tx['account_name']
            if company_id not in [1, 2, 3]:  # Not one of the predefined companies
                actual_companies.add((company_id, company_name))
        
        # Add predefined companies first
        companies.extend(predefined_companies)
        
        # Add any additional companies found in data
        for company_id, company_name in sorted(actual_companies):
            companies.append({
                'id': company_id,
                'name': company_name
            })
        
        return companies
