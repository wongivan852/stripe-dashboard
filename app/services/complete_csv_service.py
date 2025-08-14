import os
import csv
import glob
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

class CompleteCsvService:
    """Service to import and process complete CSV data for monthly statements"""
    
    def __init__(self, csv_directory=None):
        self.logger = logging.getLogger(__name__)
        
        if csv_directory is None:
            csv_directory = self._resolve_csv_directory()
        
        self.csv_directory = csv_directory
        self.company_names = {
            "cgge": "CGGE", 
            "ki": "Krystal Institute",
            "kt": "Krystal Technology"
        }
        
        self._validate_csv_directory()
    
    def _resolve_csv_directory(self):
        """Resolve complete_csv directory path"""
        possible_paths = [
            os.environ.get('COMPLETE_CSV_PATH'),
            os.path.join(os.getcwd(), 'complete_csv'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'complete_csv'),
            '/app/complete_csv',
            '/Users/wongivan/company_apps/stripe-dashboard/complete_csv'
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                self.logger.info(f"Found complete_csv directory: {path}")
                return path
        
        fallback_path = os.path.join(os.getcwd(), 'complete_csv')
        self.logger.warning(f"No complete_csv directory found, using fallback: {fallback_path}")
        return fallback_path
    
    def _validate_csv_directory(self):
        """Validate and create CSV directory if needed"""
        try:
            if not os.path.exists(self.csv_directory):
                os.makedirs(self.csv_directory, exist_ok=True)
                self.logger.warning(f"Created complete_csv directory: {self.csv_directory}")
        except Exception as e:
            self.logger.error(f"Failed to create complete_csv directory {self.csv_directory}: {e}")
    
    def _find_csv_files(self):
        """Find all CSV files in complete_csv directory"""
        csv_files = []
        
        try:
            pattern = os.path.join(self.csv_directory, "*.csv")
            files = glob.glob(pattern)
            
            for file_path in files:
                filename = os.path.basename(file_path)
                # Skip backup files
                if '_backup.csv' in filename.lower():
                    continue
                company_code = self._extract_company_from_filename(filename)
                csv_files.append((file_path, company_code))
            
            self.logger.info(f"Found {len(csv_files)} CSV files in {self.csv_directory}")
            return csv_files
            
        except Exception as e:
            self.logger.error(f"Error finding CSV files: {e}")
            return []
    
    def _extract_company_from_filename(self, filename):
        """Extract company code from filename"""
        filename_lower = filename.lower()
        
        if filename_lower.startswith('cgge_'):
            return 'cgge'
        elif filename_lower.startswith('ki_'):
            return 'ki' 
        elif filename_lower.startswith('kt_'):
            return 'kt'
        else:
            return 'unknown'
    
    def import_transactions_from_csv(self):
        """Import all transactions from complete_csv files"""
        all_transactions = []
        csv_files = self._find_csv_files()
        
        if not csv_files:
            self.logger.warning("No CSV files found to import")
            return []
        
        for csv_file, company_code in csv_files:
            try:
                transactions = self._read_csv_file(csv_file, company_code)
                all_transactions.extend(transactions)
                self.logger.info(f"Imported {len(transactions)} transactions from {os.path.basename(csv_file)}")
            except Exception as e:
                self.logger.error(f"Error reading {csv_file}: {e}")
                continue
        
        # Sort by created date
        all_transactions.sort(key=lambda x: x.get('created') or datetime.min)
        
        self.logger.info(f"Total imported transactions: {len(all_transactions)}")
        return all_transactions
    
    def _read_csv_file(self, csv_file, company_code):
        """Read and parse a single CSV file"""
        transactions = []
        
        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row in reader:
                    if not row.get('id', '').strip():
                        continue
                    
                    try:
                        parsed_transactions = self._parse_csv_row(row, company_code)
                        if parsed_transactions:
                            if isinstance(parsed_transactions, list):
                                transactions.extend(parsed_transactions)
                            else:
                                transactions.append(parsed_transactions)
                    except Exception as e:
                        self.logger.warning(f"Error parsing row in {csv_file}: {e}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error reading CSV file {csv_file}: {e}")
            
        return transactions
    
    def _parse_csv_row(self, row, company_code):
        """Parse a CSV row into standardized transaction format"""
        try:
            # Parse created date
            created_str = row.get('Created (UTC)', '').strip()
            created = None
            if created_str:
                try:
                    created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                except ValueError:
                    try:
                        created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        pass
            
            # Parse available date
            available_str = row.get('Available On (UTC)', '').strip()
            available_on = None
            if available_str:
                try:
                    available_on = datetime.strptime(available_str, '%Y-%m-%d %H:%M').date()
                except ValueError:
                    try:
                        available_on = datetime.strptime(available_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
            
            # Parse transfer date (for payout reconciliation)
            transfer_str = row.get('Transfer Date (UTC)', '').strip()
            transfer_date = None
            if transfer_str:
                try:
                    transfer_date = datetime.strptime(transfer_str, '%Y-%m-%d %H:%M').date()
                except ValueError:
                    try:
                        transfer_date = datetime.strptime(transfer_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
            
            # Determine transaction type first
            transaction_type = row.get('Type', '').lower()
            
            # Parse amounts with enhanced fee handling
            amount = self._parse_decimal(row.get('Amount', '0'))
            fee = self._parse_decimal(row.get('Fee', '0'))
            net = self._parse_decimal(row.get('Net', '0'))
            
            # Enhanced fee estimation for missing fee data
            if fee == 0 and transaction_type in ['charge', 'payment'] and amount > 0:
                # Estimate fee based on typical Stripe rates if not provided
                estimated_fee = amount * Decimal('0.042')  # ~4.2% typical rate
                self.logger.debug(f"Estimating fee for transaction {row.get('id', '')}: {estimated_fee}")
                fee = estimated_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Get description
            description = row.get('Description', '').strip()
            
            # Map status based on transaction type
            status = self._determine_status(transaction_type, amount)
            
            # Include transactions that affect balance: succeeded, refunded, failed payouts (payout reversals)
            if status not in ['succeeded', 'refunded', 'failed']:
                return None
            
            # Determine party (customer reference)
            party = self._extract_party_from_metadata(row) or self._extract_party_from_description(description)
            
            # For charges, we'll create multiple entries: gross, fee, net
            transactions = []
            
            if transaction_type in ['charge', 'payment'] and fee > 0:
                # Create gross amount entry (debit)
                gross_tx = {
                    'id': row.get('id', '') + '_gross',
                    'stripe_id': row.get('id', ''),
                    'date': created.date() if created else (available_on if available_on else None),
                    'nature': 'Gross ' + self._map_nature(transaction_type, description),
                    'party': party,
                    'debit': abs(amount),
                    'credit': 0,
                    'balance': 0,
                    'acknowledged': False,
                    'description': f"Gross {description}",
                    'amount': amount,
                    'fee': 0,
                    'net_amount': amount,
                    'currency': row.get('Currency', 'hkd').upper(),
                    'status': status,
                    'type': transaction_type,
                    'created': created,
                    'available_on': available_on,
                    'transfer_date': transfer_date,
                    'account_name': self.company_names.get(company_code, 'Unknown Company'),
                    'company_code': company_code,
                    'raw_row': row
                }
                
                # Create fee entry (credit - reduces balance)
                fee_tx = {
                    'id': row.get('id', '') + '_fee',
                    'stripe_id': row.get('id', ''),
                    'date': created.date() if created else (available_on if available_on else None),
                    'nature': 'Processing Fee',
                    'party': 'Stripe',
                    'debit': 0,
                    'credit': abs(fee),
                    'balance': 0,
                    'acknowledged': False,
                    'description': f"Processing fee for {description}",
                    'amount': -fee,
                    'fee': fee,
                    'net_amount': -fee,
                    'currency': row.get('Currency', 'hkd').upper(),
                    'status': status,
                    'type': 'fee',
                    'created': created,
                    'available_on': available_on,
                    'transfer_date': transfer_date,
                    'account_name': self.company_names.get(company_code, 'Unknown Company'),
                    'company_code': company_code,
                    'raw_row': row,
                    'is_fee': True
                }
                
                return [gross_tx, fee_tx]
            elif transaction_type in ['charge', 'payment']:
                # For charges without fees, use net amount
                net_debit = abs(net) if net > 0 else 0
                net_credit = abs(net) if net < 0 else 0
                
                return [{
                    'id': row.get('id', ''),
                    'stripe_id': row.get('id', ''),
                    'date': created.date() if created else (available_on if available_on else None),
                    'nature': self._map_nature(transaction_type, description),
                    'party': party,
                    'debit': net_debit,
                    'credit': net_credit,
                    'balance': 0,
                    'acknowledged': False,
                    'description': description,
                    'amount': amount,
                    'fee': fee,
                    'net_amount': net,
                    'currency': row.get('Currency', 'hkd').upper(),
                    'status': status,
                    'type': transaction_type,
                    'created': created,
                    'available_on': available_on,
                    'transfer_date': transfer_date,
                    'account_name': self.company_names.get(company_code, 'Unknown Company'),
                    'company_code': company_code,
                    'raw_row': row
                }]
            else:
                # Simple transaction for payouts, refunds, etc.
                if transaction_type == 'payout':
                    # Regular payout - money leaving balance (credit reduces balance)
                    debit_amount = 0
                    credit_amount = abs(amount)
                elif transaction_type == 'payout_failure':
                    # Payout failure - money returned to balance (debit increases balance)
                    debit_amount = abs(amount)
                    credit_amount = 0
                elif transaction_type == 'refund':
                    # Refund - money leaving balance (credit reduces balance)
                    # Amount is already negative, so we use abs() for credit
                    debit_amount = 0
                    credit_amount = abs(amount)
                else:
                    # Default handling for other transaction types
                    debit_amount = abs(amount) if amount > 0 else 0
                    credit_amount = abs(amount) if amount < 0 else 0
                
                return [{
                    'id': row.get('id', ''),
                    'stripe_id': row.get('id', ''),
                    'date': created.date() if created else (available_on if available_on else None),
                    'nature': self._map_nature(transaction_type, description),
                    'party': party,
                    'debit': debit_amount,
                    'credit': credit_amount,
                    'balance': 0,
                    'acknowledged': False,
                    'description': description,
                    'amount': amount,
                    'fee': fee,
                    'net_amount': net,
                    'currency': row.get('Currency', 'hkd').upper(),
                    'status': status,
                    'type': transaction_type,
                    'created': created,
                    'available_on': available_on,
                    'transfer_date': transfer_date,
                    'account_name': self.company_names.get(company_code, 'Unknown Company'),
                    'company_code': company_code,
                    'raw_row': row  # Keep original row for reference
                }]
            
        except Exception as e:
            self.logger.error(f"Error parsing transaction: {e}")
            return None
    
    def _parse_decimal(self, value_str):
        """Parse decimal value from string with enhanced precision"""
        try:
            # Remove quotes and strip whitespace
            clean_value = str(value_str).strip('"').strip()
            if not clean_value or clean_value == '':
                return Decimal('0')
            # Enhanced precision with better rounding
            decimal_val = Decimal(clean_value)
            return decimal_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError) as e:
            self.logger.warning(f"Failed to parse decimal value '{value_str}': {e}")
            return Decimal('0')
    
    def _determine_status(self, transaction_type, amount):
        """Determine transaction status based on type"""
        if transaction_type in ['payment', 'charge']:
            return 'succeeded'
        elif transaction_type == 'refund':
            return 'refunded'
        elif transaction_type == 'payout':
            return 'succeeded'
        elif transaction_type == 'payout_failure':
            return 'failed'
        else:
            return 'succeeded'  # Default for real money movement
    
    def _map_nature(self, transaction_type, description):
        """Map transaction type to nature field (Stripe reference)"""
        if transaction_type == 'payment':
            return 'Payment'
        elif transaction_type == 'charge':
            return 'Charge'
        elif transaction_type == 'refund':
            return 'Refund'
        elif transaction_type == 'payout':
            return 'Payout'
        elif transaction_type == 'payout_failure':
            # Check if it's a payout reversal/refund
            if 'REFUND FOR PAYOUT' in description.upper():
                return 'Payout Reversal'
            else:
                return 'Payout Failure'
        else:
            return transaction_type.title()
    
    def _extract_party_from_metadata(self, row):
        """Extract customer reference from metadata fields"""
        # Check for userID in metadata
        user_id = row.get('userID (metadata)', '').strip()
        if user_id:
            return f"User {user_id}"
        
        # Check for other customer identifiers
        site = row.get('site (metadata)', '').strip()
        stripe_plan = row.get('stripe_plan (metadata)', '').strip()
        
        if site and stripe_plan:
            return f"{site} - {stripe_plan}"
        elif site:
            return site
        elif stripe_plan:
            return stripe_plan
        
        return None
    
    def _extract_party_from_description(self, description):
        """Extract customer reference from description"""
        if not description:
            return "N/A"
        
        # Look for email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, description)
        if emails:
            return emails[0]
        
        # Look for order references
        order_pattern = r'Order #[A-Z0-9]+'
        orders = re.findall(order_pattern, description)
        if orders:
            return orders[0]
        
        # Default to shortened description
        return description[:50] + "..." if len(description) > 50 else description
    
    def generate_monthly_statement(self, year, month, company_filter=None, previous_balance=None, use_transfer_dates=False):
        """Generate monthly statement with running balance"""
        
        # If use_transfer_dates is True, generate payout reconciliation instead
        if use_transfer_dates:
            return self.generate_payout_reconciliation(year, month, company_filter)
        
        # If previous_balance is not provided, get it from the previous month
        if previous_balance is None:
            previous_balance = self._get_previous_month_closing_balance(year, month, company_filter)
        
        # Get all transactions for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        all_transactions = self.import_transactions_from_csv()
        
        # Filter transactions for the month by TRANSACTION DATE (for proper monthly balance tracking)
        monthly_transactions = []
        for tx in all_transactions:
            tx_date = tx.get('date')
            if tx_date and start_date <= tx_date <= end_date:
                if company_filter and tx['company_code'] != company_filter:
                    continue
                monthly_transactions.append(tx)
        
        # Sort by transaction date for proper chronological order
        monthly_transactions.sort(key=lambda x: x.get('date') or datetime.min.date())
        
        # Calculate running balance, but exclude transactions that occur in current month 
        # but have transfer dates in the next month (for proper month-end balance)
        running_balance = Decimal(str(previous_balance))
        actual_closing_balance = running_balance
        
        for tx in monthly_transactions:
            debit = Decimal(str(tx['debit']))
            credit = Decimal(str(tx['credit']))
            transfer_date = tx.get('transfer_date')
            
            # Standard debit/credit logic: debits increase balance, credits decrease balance
            running_balance += debit - credit
            
            tx['balance'] = float(running_balance)
            
            # For month-end closing balance, exclude transactions that transfer in the immediate next month only
            # (not transactions with transfer dates years in the future)
            exclude_from_closing = (transfer_date and 
                                  transfer_date > end_date and 
                                  transfer_date <= end_date.replace(day=28) + timedelta(days=4))
            if not exclude_from_closing:
                actual_closing_balance = running_balance
        
        closing_balance = float(actual_closing_balance)
        
        return {
            'transactions': monthly_transactions,
            'opening_balance': previous_balance,
            'closing_balance': closing_balance,
            'month': month,
            'year': year,
            'company_filter': company_filter,
            'total_debit': sum(tx['debit'] for tx in monthly_transactions),
            'total_credit': sum(tx['credit'] for tx in monthly_transactions)
        }
    
    def generate_payout_reconciliation(self, year, month, company_filter=None):
        """Generate payout reconciliation based on transfer dates (matches Stripe's payout reconciliation)"""
        
        # Get date range for the month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        
        all_transactions = self.import_transactions_from_csv()
        
        # Filter transactions by TRANSFER DATE (when they were paid out)
        payout_transactions = []
        ending_balance_transactions = []
        
        for tx in all_transactions:
            if company_filter and tx['company_code'] != company_filter:
                continue
                
            transfer_date = tx.get('transfer_date')
            if transfer_date:
                if start_date <= transfer_date <= end_date:
                    # This transaction was paid out during this month
                    payout_transactions.append(tx)
                elif transfer_date > end_date:
                    # This transaction will be paid out in the future (ending balance)
                    ending_balance_transactions.append(tx)
        
        # Sort by transfer date
        payout_transactions.sort(key=lambda x: x.get('transfer_date') or datetime.min.date())
        
        # Calculate totals for payout reconciliation with enhanced precision
        charges_count = 0
        charges_gross = Decimal('0')
        charges_fees = Decimal('0')
        refunds_count = 0
        refunds_gross = Decimal('0')
        payout_reversals_count = 0
        payout_reversals_gross = Decimal('0')
        
        self.logger.info(f"Processing {len(payout_transactions)} payout transactions for {company_filter} {year}-{month:02d}")
        
        for tx in payout_transactions:
            if tx['type'] in ['charge', 'payment']:
                if not tx.get('is_fee'):
                    charges_count += 1
                    charges_gross += Decimal(str(tx['debit']))
            elif tx['type'] == 'fee' or tx.get('is_fee'):
                # Use absolute value for fees to ensure proper calculation
                charges_fees += abs(Decimal(str(tx['credit'])))
            elif tx['type'] == 'refund':
                refunds_count += 1
                refunds_gross += Decimal(str(tx['debit']))
            elif tx['type'] == 'payout_failure':
                payout_reversals_count += 1
                payout_reversals_gross += Decimal(str(tx['debit']))
        
        # Calculate ending balance items with enhanced precision
        ending_charges_count = 0
        ending_charges_gross = Decimal('0')
        ending_charges_fees = Decimal('0')
        ending_payout_reversals_count = 0
        ending_payout_reversals_gross = Decimal('0')
        
        self.logger.info(f"Processing {len(ending_balance_transactions)} ending balance transactions")
        
        for tx in ending_balance_transactions:
            if tx['type'] in ['charge', 'payment']:
                if not tx.get('is_fee'):
                    ending_charges_count += 1
                    ending_charges_gross += Decimal(str(tx['debit']))
            elif tx['type'] == 'fee' or tx.get('is_fee'):
                # Use absolute value for fees
                ending_charges_fees += abs(Decimal(str(tx['credit'])))
            elif tx['type'] == 'payout_failure':
                ending_payout_reversals_count += 1
                ending_payout_reversals_gross += Decimal(str(tx['debit']))
        
        # Calculate total paid out with proper precision
        total_paid_out = (
            charges_gross 
            - charges_fees  # Subtract fees from gross amounts
            + refunds_gross 
            + payout_reversals_gross
        )
        
        # Calculate ending balance with proper precision
        ending_balance = ending_charges_gross - ending_charges_fees + ending_payout_reversals_gross
        
        # Log reconciliation details for debugging
        self.logger.info(f"Payout Reconciliation Summary for {company_filter} {year}-{month:02d}:")
        self.logger.info(f"  Charges: {charges_count} transactions, Gross: {charges_gross}, Fees: {charges_fees}")
        self.logger.info(f"  Refunds: {refunds_count} transactions, Gross: {refunds_gross}")
        self.logger.info(f"  Payout Reversals: {payout_reversals_count} transactions, Gross: {payout_reversals_gross}")
        self.logger.info(f"  Total Paid Out: {total_paid_out}")
        self.logger.info(f"  Ending Balance: {ending_balance}")
        
        # Check for discrepancies against known Stripe totals (July 2025 CGGE)
        if company_filter == 'cgge' and year == 2025 and month == 7:
            expected_total = Decimal('2636.78')
            if abs(total_paid_out - expected_total) > Decimal('0.01'):
                self.logger.warning(f"Payout total discrepancy: Expected {expected_total}, Got {total_paid_out}, Difference: {total_paid_out - expected_total}")
            
            expected_ending = Decimal('554.77')
            if abs(ending_balance - expected_ending) > Decimal('0.01'):
                self.logger.warning(f"Ending balance discrepancy: Expected {expected_ending}, Got {ending_balance}, Difference: {ending_balance - expected_ending}")
        
        return {
            'month': month,
            'year': year,
            'company_filter': company_filter,
            'payout_reconciliation': {
                'charges': {
                    'count': charges_count,
                    'gross_amount': float(charges_gross),
                    'fees': -float(charges_fees)
                },
                'refunds': {
                    'count': refunds_count,
                    'gross_amount': float(refunds_gross)
                },
                'payout_reversals': {
                    'count': payout_reversals_count,
                    'gross_amount': float(payout_reversals_gross)
                },
                'total_paid_out': float(total_paid_out)
            },
            'ending_balance_reconciliation': {
                'charges': {
                    'count': ending_charges_count,
                    'gross_amount': float(ending_charges_gross),
                    'fees': -float(ending_charges_fees)
                },
                'payout_reversals': {
                    'count': ending_payout_reversals_count,
                    'gross_amount': float(ending_payout_reversals_gross)
                },
                'ending_balance': float(ending_balance)
            },
            'payout_transactions': payout_transactions,
            'ending_balance_transactions': ending_balance_transactions
        }
    
    def export_monthly_statement_csv(self, statement_data):
        """Export monthly statement to CSV format"""
        try:
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            header = [
                'Date', 'Nature', 'Party', 'Debit', 'Credit', 
                'Balance', 'Acknowledged', 'Description'
            ]
            writer.writerow(header)
            
            # Write opening balance row
            writer.writerow([
                f"{statement_data['year']}-{statement_data['month']:02d}-01",
                "Opening Balance",
                "Brought Forward",
                "",
                "",
                f"{statement_data['opening_balance']:.2f}",
                "Yes",
                f"Opening balance for {statement_data['month']}/{statement_data['year']}"
            ])
            
            # Write transaction rows
            for tx in statement_data['transactions']:
                writer.writerow([
                    tx['date'].strftime('%Y-%m-%d') if tx['date'] else '',
                    tx['nature'],
                    tx['party'],
                    f"{tx['debit']:.2f}" if tx['debit'] > 0 else "",
                    f"{tx['credit']:.2f}" if tx['credit'] > 0 else "",
                    f"{tx['balance']:.2f}",
                    "No" if not tx['acknowledged'] else "Yes",
                    tx['description']
                ])
            
            # Write closing balance row
            writer.writerow([
                f"{statement_data['year']}-{statement_data['month']:02d}-{self._get_last_day_of_month(statement_data['year'], statement_data['month']):02d}",
                "Closing Balance",
                "Carry Forward",
                "",
                "",
                f"{statement_data['closing_balance']:.2f}",
                "Yes",
                f"Closing balance for {statement_data['month']}/{statement_data['year']}"
            ])
            
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            self.logger.error(f"Error exporting monthly statement to CSV: {e}")
            return None
    
    def _get_last_day_of_month(self, year, month):
        """Get the last day of the month"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        last_day = next_month - timedelta(days=1)
        return last_day.day
    
    def get_available_companies(self):
        """Get list of companies from CSV files"""
        csv_files = self._find_csv_files()
        companies = set()
        
        for _, company_code in csv_files:
            if company_code in self.company_names:
                companies.add((company_code, self.company_names[company_code]))
        
        return [{'code': code, 'name': name} for code, name in sorted(companies)]
    
    def get_available_months(self):
        """Get list of available months from transaction data"""
        transactions = self.import_transactions_from_csv()
        months = set()
        
        for tx in transactions:
            if tx['date']:
                months.add((tx['date'].year, tx['date'].month))
        
        return sorted(list(months), reverse=True)
    
    def _get_previous_month_closing_balance(self, year, month, company_filter):
        """Get the closing balance from the previous month"""
        try:
            # Get all transactions for the company
            all_transactions = self.import_transactions_from_csv()
            
            # Filter by company if specified
            if company_filter:
                all_transactions = [tx for tx in all_transactions if tx['company_code'] == company_filter]
            
            # Sort all transactions by date
            all_transactions.sort(key=lambda x: x['date'] if x['date'] else datetime.min.date())
            
            # Calculate running balance up to the end of the previous month
            target_date = datetime(year, month, 1).date() - timedelta(days=1)  # Last day of previous month
            
            running_balance = Decimal('0')
            for tx in all_transactions:
                if tx['date'] and tx['date'] <= target_date:
                    debit = Decimal(str(tx['debit']))
                    credit = Decimal(str(tx['credit']))
                    
                    # Standard debit/credit logic: debits increase balance, credits decrease balance
                    running_balance += debit - credit
                else:
                    break  # Stop when we reach the target month
            
            return float(running_balance)
            
        except Exception as e:
            self.logger.warning(f"Could not get previous month balance: {e}")
            return 0