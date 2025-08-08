import os
import csv
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import logging

class CSVTransactionService:
    """Service to read transaction data from CSV files with robust deployment support"""
    
    def __init__(self, csv_directory=None):
        # Setup logging first
        self.logger = logging.getLogger(__name__)
        
        # Deployment-friendly path resolution
        if csv_directory is None:
            csv_directory = self._resolve_csv_directory()
        
        self.csv_directory = csv_directory
        self.company_names = {
            "cgge": "CGGE", 
            "krystal_institute": "Krystal Institute",
            "krystal_technology": "Krystal Technology"
        }
        
        # Validate directory on initialization
        self._validate_csv_directory()
    
    def _resolve_csv_directory(self):
        """Resolve CSV directory path for different deployment environments"""
        # Try different possible locations in order of preference
        possible_paths = [
            # Environment variable override
            os.environ.get('CSV_DATA_PATH'),
            # Current working directory relative paths
            os.path.join(os.getcwd(), 'july25'),
            os.path.join(os.getcwd(), 'new_csv'),
            os.path.join(os.getcwd(), 'csv_data'),
            # App root relative paths  
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'july25'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'new_csv'),
            # Docker/container paths
            '/app/july25',
            '/app/new_csv',
            '/app/csv_data',
            # Fallback development path
            '/Users/wongivan/stripe-dashboard/july25',
            '/Users/wongivan/stripe-dashboard/new_csv'
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                self.logger.info(f"Found CSV directory: {path}")
                return path
        
        # Default fallback - create in current directory
        fallback_path = os.path.join(os.getcwd(), 'csv_data')
        self.logger.warning(f"No CSV directory found, using fallback: {fallback_path}")
        return fallback_path
    
    def _validate_csv_directory(self):
        """Validate and create CSV directory if needed"""
        try:
            if not os.path.exists(self.csv_directory):
                os.makedirs(self.csv_directory, exist_ok=True)
                self.logger.warning(f"Created CSV directory: {self.csv_directory}")
        except Exception as e:
            self.logger.error(f"Failed to create CSV directory {self.csv_directory}: {e}")
    
    def _find_csv_files(self):
        """Find CSV files with flexible naming patterns"""
        csv_files = []
        
        # Multiple file patterns to support different CSV formats
        file_patterns = [
            "*unified_payments_*.csv",
            "Itemised_balance_change_from_activity_*.csv", 
            "*transactions*.csv",
            "*payments*.csv",
            "*.csv"
        ]
        
        # Check for company subdirectory structure
        company_dirs = ['cgge', 'krystal_institute', 'krystal_technology']
        has_company_dirs = all(os.path.isdir(os.path.join(self.csv_directory, dir_name)) for dir_name in company_dirs)
        
        if has_company_dirs:
            # New structure: read from company subdirectories
            for company_dir in company_dirs:
                company_path = os.path.join(self.csv_directory, company_dir)
                for pattern in file_patterns:
                    pattern_path = os.path.join(company_path, pattern)
                    company_files = glob.glob(pattern_path)
                    for file_path in company_files:
                        csv_files.append((file_path, company_dir))
                        if company_files:  # Stop at first successful pattern
                            break
        else:
            # Flat structure: read from root directory
            for pattern in file_patterns:
                pattern_path = os.path.join(self.csv_directory, pattern)
                root_files = glob.glob(pattern_path)
                for file_path in root_files:
                    csv_files.append((file_path, None))
                if root_files:  # Stop at first successful pattern
                    break
        
        self.logger.info(f"Found {len(csv_files)} CSV files in {self.csv_directory}")
        return csv_files
    
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
        
        # Use the new robust file finding method
        try:
            csv_files = self._find_csv_files()
        except Exception as e:
            self.logger.error(f"Error finding CSV files: {e}")
            return []  # Return empty list instead of crashing
        
        if not csv_files:
            self.logger.warning(f"No CSV files found in {self.csv_directory}")
            return []
        
        # Process each CSV file
        for csv_file_info in csv_files:
            if isinstance(csv_file_info, tuple):
                csv_file, company_dir = csv_file_info
            else:
                csv_file, company_dir = csv_file_info, None
            
            try:
                file_transactions = self._read_csv_file(csv_file, company_filter, status_filter, from_date, to_date, company_dir)
                transactions.extend(file_transactions)
            except Exception as e:
                self.logger.error(f"Error processing CSV file {csv_file}: {e}")
                continue  # Continue processing other files
        
        # Sort by created date (newest first)
        try:
            transactions.sort(key=lambda x: x.get('created') or datetime.min, reverse=True)
        except Exception as e:
            self.logger.error(f"Error sorting transactions: {e}")
        
        self.logger.info(f"Retrieved {len(transactions)} transactions from {len(csv_files)} CSV files")
        return transactions
    
    def _read_csv_file(self, csv_file, company_filter, status_filter, from_date, to_date, company_dir=None):
        """Read transactions from a single CSV file with robust error handling"""
        transactions = []
        
        try:
            # Check if file exists and is readable
            if not os.path.exists(csv_file):
                self.logger.warning(f"CSV file not found: {csv_file}")
                return []
                
            if not os.access(csv_file, os.R_OK):
                self.logger.error(f"CSV file not readable: {csv_file}")
                return []
            
            with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Check if file has expected headers
                if not reader.fieldnames:
                    self.logger.warning(f"CSV file has no headers: {csv_file}")
                    return []
                
                row_count = 0
                for row in reader:
                    row_count += 1
                    
                    # Skip empty rows - check for different ID field names
                    row_id = (row.get('balance_transaction_id') or 
                             row.get('id') or 
                             row.get('transaction_id') or
                             row.get('payment_id'))
                    
                    if not row_id or not row_id.strip():
                        continue
                        
                    try:
                        transaction = self._parse_csv_row(row, company_dir, csv_file)
                        
                        if transaction and self._should_include_transaction(transaction, company_filter, status_filter, from_date, to_date):
                            transactions.append(transaction)
                    except Exception as e:
                        self.logger.warning(f"Error parsing row {row_count} in {csv_file}: {e}")
                        continue  # Skip problematic rows instead of failing
                        
                self.logger.info(f"Processed {row_count} rows from {csv_file}, extracted {len(transactions)} valid transactions")
                        
        except FileNotFoundError:
            self.logger.error(f"CSV file not found: {csv_file}")
        except PermissionError:
            self.logger.error(f"Permission denied reading CSV file: {csv_file}")
        except UnicodeDecodeError:
            self.logger.error(f"Encoding error reading CSV file: {csv_file}")
        except Exception as e:
            self.logger.error(f"Unexpected error reading CSV file {csv_file}: {str(e)}")
            
        return transactions
    
    def _parse_csv_row(self, row, company_dir=None, csv_file=None):
        """Parse a CSV row into transaction format - supports multiple CSV formats"""
        
        # Detect CSV format based on available columns
        is_unified_payments = 'Created date (UTC)' in row
        is_balance_change = 'balance_transaction_id' in row
        
        try:
            if is_unified_payments:
                return self._parse_unified_payments_row(row, company_dir, csv_file)
            elif is_balance_change:
                return self._parse_balance_change_row(row, company_dir, csv_file)
            else:
                # Generic CSV parsing
                return self._parse_generic_csv_row(row, company_dir, csv_file)
        except Exception as e:
            self.logger.error(f"Error parsing CSV row: {e}")
            return None
    
    def _parse_unified_payments_row(self, row, company_dir=None, csv_file=None):
        """Parse unified payments CSV format (like cgge_unified_payments_20250731.csv)"""
        # Parse the created date
        created_str = row.get('Created date (UTC)', '').strip()
        try:
            created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            self.logger.warning(f"Invalid date format: {created_str}")
            created = None
            
        # Get amounts - prefer converted amounts (HKD) over original
        try:
            # Try converted amount first (usually HKD)
            amount = float(row.get('Converted Amount', row.get('Amount', 0)) or 0)
            fee = float(row.get('Fee', 0) or 0)
            currency = (row.get('Converted Currency', row.get('Currency', 'hkd')) or 'hkd').lower()
        except (ValueError, TypeError):
            amount = fee = 0
            currency = 'hkd'
            
        # Determine company from filename or directory
        if company_dir:
            company_name = self._get_company_name_from_dir(company_dir)
        elif csv_file:
            company_name = self._extract_company_from_filename(csv_file)
        else:
            company_name = self._extract_company_from_description(row.get('Description', ''))
        
        # Get status - map from Status field
        status_raw = (row.get('Status') or '').lower().strip()
        status = self._map_status_field(status_raw)
        
        # Get other fields
        stripe_id = row.get('id', '').strip()
        description = row.get('Description', '').strip()
        customer_email = row.get('Customer Email', '').strip() or self._extract_customer_email(description)
        
        return {
            'id': stripe_id,
            'stripe_id': stripe_id,
            'amount': amount,
            'fee': fee,
            'net_amount': amount - fee,
            'currency': currency.upper(),
            'status': status,
            'type': 'charge',
            'description': description,
            'customer_email': customer_email if customer_email else 'N/A',
            'created': created,
            'stripe_created': created,
            'available_on': created.date() if created else None,
            'account_name': company_name,
            'company_id': self._get_company_id(company_name),
            'reporting_category': 'charge'
        }
    
    def _parse_balance_change_row(self, row, company_dir=None, csv_file=None):
        """Parse balance change CSV format (original format)"""
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
            company_name = self._get_company_name_from_dir(company_dir)
        else:
            description = row.get('description', '')
            company_name = self._extract_company_from_description(description)
        
        # Parse amounts
        try:
            gross = float(row.get('gross', 0))
            fee = float(row.get('fee', 0))
            net = float(row.get('net', 0))
        except:
            gross = fee = net = 0
            
        # Extract customer email if available
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
    
    def _parse_generic_csv_row(self, row, company_dir=None, csv_file=None):
        """Parse generic CSV format as fallback"""
        # Try to find any ID field
        stripe_id = (row.get('id') or row.get('transaction_id') or 
                    row.get('payment_id') or row.get('stripe_id', ''))
        
        # Try to find amount fields
        amount = 0
        fee = 0
        for amt_field in ['amount', 'Amount', 'gross', 'total']:
            try:
                if row.get(amt_field):
                    amount = float(row[amt_field])
                    break
            except:
                continue
                
        for fee_field in ['fee', 'Fee', 'processing_fee']:
            try:
                if row.get(fee_field):
                    fee = float(row[fee_field])
                    break
            except:
                continue
        
        # Try to find date
        created = None
        for date_field in ['created', 'Created', 'date', 'Date', 'timestamp']:
            try:
                if row.get(date_field):
                    created = datetime.strptime(row[date_field], '%Y-%m-%d %H:%M:%S')
                    break
            except:
                continue
        
        company_name = 'Unknown Company'
        if csv_file:
            company_name = self._extract_company_from_filename(csv_file)
        
        return {
            'id': stripe_id,
            'stripe_id': stripe_id,
            'amount': amount,
            'fee': fee,
            'net_amount': amount - fee,
            'currency': 'HKD',
            'status': 'succeeded',
            'type': 'charge',
            'description': row.get('description', row.get('Description', '')),
            'customer_email': 'N/A',
            'created': created,
            'stripe_created': created,
            'available_on': created.date() if created else None,
            'account_name': company_name,
            'company_id': self._get_company_id(company_name),
            'reporting_category': 'charge'
        }
    
    def _get_company_name_from_dir(self, company_dir):
        """Map directory name to company name"""
        dir_to_company = {
            'cgge': 'CGGE',
            'krystal_institute': 'Krystal Institute',
            'krystal_technology': 'Krystal Technology'
        }
        return dir_to_company.get(company_dir, 'Unknown Company')
    
    def _extract_company_from_filename(self, csv_file):
        """Extract company name from CSV filename"""
        filename = os.path.basename(csv_file).lower()
        
        if 'cgge' in filename:
            return 'CGGE'
        elif 'ki_' in filename or 'krystal_institute' in filename:
            return 'Krystal Institute'  
        elif 'kt_' in filename or 'krystal_technology' in filename:
            return 'Krystal Technology'
        else:
            return 'Combined Account'
    
    def _map_status_field(self, status_raw):
        """Map status field from unified payments CSV to standard status"""
        if not status_raw:
            return 'succeeded'
            
        status_lower = status_raw.lower().strip()
        
        if status_lower == 'paid':
            return 'succeeded'
        elif status_lower == 'failed':
            return 'failed'
        elif status_lower in ['canceled', 'cancelled']:
            return 'canceled'
        elif status_lower == 'pending':
            return 'pending'
        else:
            return 'succeeded'  # Default
    
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
    
    def export_transactions_to_csv(self, transactions, filename=None):
        """Export transactions to CSV format for download"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'transactions_export_{timestamp}.csv'
        
        try:
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = [
                'Transaction ID', 'Company', 'Amount', 'Fee', 'Net Amount', 
                'Currency', 'Status', 'Type', 'Customer Email', 
                'Description', 'Created Date', 'Available Date'
            ]
            writer.writerow(header)
            
            # Write data rows
            for tx in transactions:
                writer.writerow([
                    tx.get('stripe_id', ''),
                    tx.get('account_name', ''),
                    f"{tx.get('amount', 0):.2f}",
                    f"{tx.get('fee', 0):.2f}",
                    f"{tx.get('net_amount', 0):.2f}",
                    tx.get('currency', 'HKD'),
                    tx.get('status', ''),
                    tx.get('type', ''),
                    tx.get('customer_email', ''),
                    tx.get('description', ''),
                    tx.get('created', '').strftime('%Y-%m-%d %H:%M:%S') if tx.get('created') else '',
                    tx.get('available_on', '').strftime('%Y-%m-%d') if tx.get('available_on') else ''
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            self.logger.info(f"Exported {len(transactions)} transactions to CSV")
            return csv_content, filename
            
        except Exception as e:
            self.logger.error(f"Error exporting transactions to CSV: {e}")
            return None, None
    
    def get_health_status(self):
        """Get health status of CSV service for monitoring"""
        try:
            csv_files = self._find_csv_files()
            total_transactions = len(self.get_all_transactions())
            
            return {
                'status': 'healthy',
                'csv_directory': self.csv_directory,
                'csv_files_found': len(csv_files),
                'total_transactions': total_transactions,
                'csv_files': [os.path.basename(f[0]) if isinstance(f, tuple) else os.path.basename(f) for f in csv_files],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'csv_directory': self.csv_directory,
                'timestamp': datetime.now().isoformat()
            }
