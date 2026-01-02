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
        self.root_directory = self._resolve_root_directory()
        self.company_names = {
            "cgge": "CGGE",
            "ki": "Krystal Institute",
            "kt": "Krystal Technology",
            "cgge_sz": "CGGE (Shenzhen) Technology Limited"
        }

        self._validate_csv_directory()

    def _resolve_root_directory(self):
        """Resolve root directory where unified CSV files may be located"""
        possible_paths = [
            os.environ.get('ROOT_CSV_PATH'),
            os.getcwd(),
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            '/app',
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                return path

        return os.getcwd()
    
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
        """Find all CSV files in complete_csv directory and root directory (for unified files)"""
        csv_files = []

        try:
            # First, look for unified files in root directory (priority)
            unified_pattern = os.path.join(self.root_directory, "*unified_payments*.csv")
            unified_files = glob.glob(unified_pattern)

            for file_path in unified_files:
                filename = os.path.basename(file_path)
                company_code = self._extract_company_from_filename(filename)
                csv_files.append((file_path, company_code, 'unified'))
                self.logger.info(f"Found unified file: {filename}")

            # Look for WeChat trade data files (cgge_sz)
            wechat_patterns = [
                os.path.join(self.root_directory, "cgge_sz_*TRADE_DATA*.csv"),
                os.path.join(self.root_directory, "*MONTH_TRADE_DATA*.csv"),  # WeChat export format
            ]
            for wechat_pattern in wechat_patterns:
                wechat_files = glob.glob(wechat_pattern)
                for file_path in wechat_files:
                    filename = os.path.basename(file_path)
                    csv_files.append((file_path, 'cgge_sz', 'wechat'))
                    self.logger.info(f"Found WeChat file: {filename}")

            # Then look in complete_csv directory
            pattern = os.path.join(self.csv_directory, "*.csv")
            files = glob.glob(pattern)

            for file_path in files:
                filename = os.path.basename(file_path)
                # Skip backup files
                if '_backup.csv' in filename.lower():
                    continue
                company_code = self._extract_company_from_filename(filename)
                csv_files.append((file_path, company_code, 'complete'))

            self.logger.info(f"Found {len(csv_files)} CSV files total")
            return csv_files

        except Exception as e:
            self.logger.error(f"Error finding CSV files: {e}")
            return []
    
    def _extract_company_from_filename(self, filename):
        """Extract company code from filename"""
        filename_lower = filename.lower()

        # Check cgge_sz first (more specific)
        if filename_lower.startswith('cgge_sz_'):
            return 'cgge_sz'
        elif filename_lower.startswith('cgge_'):
            return 'cgge'
        elif filename_lower.startswith('ki_'):
            return 'ki'
        elif filename_lower.startswith('kt_'):
            return 'kt'
        else:
            return 'unknown'
    
    def import_transactions_from_csv(self):
        """Import all transactions from CSV files (unified files take priority)"""
        all_transactions = []
        csv_files = self._find_csv_files()

        if not csv_files:
            self.logger.warning("No CSV files found to import")
            return []

        # Track which companies have unified files (they take priority)
        unified_companies = set()

        # First pass: identify companies with unified files
        for csv_file_info in csv_files:
            csv_file, company_code, file_type = csv_file_info
            if file_type == 'unified':
                unified_companies.add(company_code)

        # Second pass: import transactions
        for csv_file_info in csv_files:
            csv_file, company_code, file_type = csv_file_info

            # Skip complete_csv files if we have unified file for this company
            if file_type == 'complete' and company_code in unified_companies:
                self.logger.info(f"Skipping {os.path.basename(csv_file)} (unified file takes priority)")
                continue

            try:
                if file_type == 'unified':
                    transactions = self._read_unified_csv_file(csv_file, company_code)
                elif file_type == 'wechat':
                    transactions = self._read_wechat_csv_file(csv_file, company_code)
                else:
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

    def _read_unified_csv_file(self, csv_file, company_code):
        """Read and parse unified payments CSV file (matches Stripe reports)"""
        transactions = []

        try:
            with open(csv_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    try:
                        parsed = self._parse_unified_row(row, company_code)
                        if parsed:
                            if isinstance(parsed, list):
                                transactions.extend(parsed)
                            else:
                                transactions.append(parsed)
                    except Exception as e:
                        self.logger.warning(f"Error parsing row in {csv_file}: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error reading unified CSV file {csv_file}: {e}")

        return transactions

    def _read_wechat_csv_file(self, csv_file, company_code):
        """
        Read and parse WeChat trade data CSV file (GB2312 encoded, Chinese format).

        WeChat CSV format:
        - First line: #起始月份：2024-12  终止月份：2025-12  (date range)
        - Second line: Header for totals (销售金额总计(元),销售总笔数,人均金额(元))
        - Third line: Total summary values
        - Fourth line: Header for monthly data (月份,销售金额(元),销售笔数,人均金额)
        - Remaining lines: Monthly data (YYYY-MM, amount, count, avg)
        """
        transactions = []

        try:
            # Read file with GB2312 encoding (common for WeChat exports)
            with open(csv_file, 'rb') as f:
                content = f.read()

            # Try different encodings
            decoded_content = None
            for encoding in ['gb2312', 'gbk', 'gb18030', 'utf-8']:
                try:
                    decoded_content = content.decode(encoding)
                    self.logger.info(f"WeChat file decoded with {encoding}")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue

            if not decoded_content:
                self.logger.error(f"Could not decode WeChat file {csv_file}")
                return []

            lines = decoded_content.strip().split('\n')
            if len(lines) < 5:
                self.logger.warning(f"WeChat file {csv_file} has too few lines")
                return []

            # Parse monthly data (starting from line 5, index 4)
            for i, line in enumerate(lines[4:], start=5):
                line = line.strip()
                if not line:
                    continue

                # Parse: YYYY-MM,"amount","count","avg"
                # Use csv module to properly handle quoted fields with commas
                import io
                reader = csv.reader(io.StringIO(line))
                try:
                    parts = next(reader)
                except StopIteration:
                    continue

                if len(parts) < 3:
                    continue

                month_str = parts[0].strip()
                amount_str = parts[1].strip().replace(',', '')  # Remove thousands separator
                count_str = parts[2].strip()

                # Parse month (YYYY-MM)
                try:
                    year_month = datetime.strptime(month_str, '%Y-%m')
                except ValueError:
                    self.logger.warning(f"Could not parse month: {month_str}")
                    continue

                # Parse amount (in CNY/RMB)
                try:
                    amount = Decimal(amount_str)
                except (InvalidOperation, ValueError):
                    self.logger.warning(f"Could not parse amount: {amount_str}")
                    continue

                # Parse transaction count
                try:
                    tx_count = int(count_str)
                except ValueError:
                    tx_count = 1

                # Skip zero amounts
                if amount <= 0:
                    continue

                # Create a monthly summary transaction
                # Note: WeChat data is monthly summary, not individual transactions
                # We'll create one transaction per month representing total sales
                tx_date = year_month.date()
                last_day = self._get_last_day_of_month(year_month.year, year_month.month)
                tx_date = datetime(year_month.year, year_month.month, last_day).date()

                transactions.append({
                    'id': f"wechat_{company_code}_{month_str}",
                    'stripe_id': f"wechat_{month_str}",
                    'date': tx_date,
                    'nature': 'WeChat Sales',
                    'party': 'WeChat Customers',
                    'debit': float(amount),  # Income increases balance
                    'credit': 0,
                    'balance': 0,
                    'acknowledged': False,
                    'description': f"WeChat sales for {month_str} ({tx_count} transactions)",
                    'gross': float(amount),
                    'amount': float(amount),
                    'fee': 0,  # WeChat fees are typically handled separately
                    'net_amount': float(amount),
                    'currency': 'CNY',
                    'status': 'succeeded',
                    'type': 'wechat_payment',
                    'created': datetime.combine(tx_date, datetime.min.time()),
                    'available_on': tx_date,
                    'transfer_date': tx_date,
                    'account_name': self.company_names.get(company_code, 'CGGE (Shenzhen)'),
                    'company_code': company_code,
                    'reporting_category': 'wechat_sales',
                    'transaction_count': tx_count
                })

            self.logger.info(f"Parsed {len(transactions)} monthly entries from WeChat file")

        except Exception as e:
            self.logger.error(f"Error reading WeChat CSV file {csv_file}: {e}")

        return transactions

    def _parse_unified_row(self, row, company_code):
        """Parse unified payments CSV row - only include Paid/Refunded transactions"""
        try:
            # Check status first - only include Paid or Refunded
            status_raw = row.get('Status', '').strip().lower()
            if status_raw not in ['paid', 'refunded']:
                return None

            # Must have an ID (skip incomplete records)
            tx_id = row.get('id', '').strip()
            if not tx_id:
                return None

            # Parse created date
            created_str = row.get('Created date (UTC)', '').strip()
            created = None
            if created_str:
                try:
                    created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        pass

            if not created:
                return None

            # Use Converted Amount (HKD) as gross - this matches Stripe's balance reports
            converted_currency = row.get('Converted Currency', '').strip().lower()
            if converted_currency == 'hkd':
                gross = self._parse_decimal(row.get('Converted Amount', '0'))
            else:
                # If not HKD, still use converted amount but log it
                gross = self._parse_decimal(row.get('Converted Amount', '0'))

            fee = self._parse_decimal(row.get('Fee', '0'))
            net = gross - fee

            # Handle refunds - check Amount Refunded and Converted Amount Refunded
            amount_refunded = self._parse_decimal(row.get('Amount Refunded', '0'))
            converted_refunded = self._parse_decimal(row.get('Converted Amount Refunded', '0'))
            refunded_date_str = row.get('Refunded date (UTC)', '').strip()

            # Determine party (customer email)
            party = row.get('Customer Email', '').strip()
            if not party or party == '':
                party = self._extract_party_from_metadata(row) or 'N/A'

            # Get description from metadata
            description = self._build_description_from_metadata(row)

            # Determine transaction type from ID prefix
            if tx_id.startswith('ch_'):
                tx_type = 'charge'
            elif tx_id.startswith('py_'):
                tx_type = 'payment'
            elif tx_id.startswith('re_'):
                tx_type = 'refund'
            else:
                tx_type = 'payment'

            transactions = []

            # Create the main charge/payment transaction
            if gross > 0:
                # Gross entry (debit - increases balance)
                gross_tx = {
                    'id': tx_id + '_gross',
                    'stripe_id': tx_id,
                    'date': created.date(),
                    'nature': 'Charge' if tx_type == 'charge' else 'Payment',
                    'party': party,
                    'debit': float(gross),
                    'credit': 0,
                    'balance': 0,
                    'acknowledged': False,
                    'description': description,
                    'gross': float(gross),
                    'amount': float(gross),
                    'fee': float(fee),
                    'net_amount': float(net),
                    'currency': 'HKD',
                    'status': 'succeeded',
                    'type': tx_type,
                    'created': created,
                    'available_on': created.date(),
                    'transfer_date': (created + timedelta(days=6)).date(),  # Stripe ~6 days to payout
                    'account_name': self.company_names.get(company_code, 'Unknown Company'),
                    'company_code': company_code,
                    'reporting_category': 'charge'
                }
                transactions.append(gross_tx)

                # Fee entry (credit - decreases balance)
                if fee > 0:
                    fee_tx = {
                        'id': tx_id + '_fee',
                        'stripe_id': tx_id,
                        'date': created.date(),
                        'nature': 'Processing Fee',
                        'party': 'Stripe',
                        'debit': 0,
                        'credit': float(fee),
                        'balance': 0,
                        'acknowledged': False,
                        'description': f"Fee for {description}",
                        'gross': 0,
                        'amount': float(-fee),
                        'fee': float(fee),
                        'net_amount': float(-fee),
                        'currency': 'HKD',
                        'status': 'succeeded',
                        'type': 'fee',
                        'created': created,
                        'available_on': created.date(),
                        'transfer_date': (created + timedelta(days=6)).date(),
                        'account_name': self.company_names.get(company_code, 'Unknown Company'),
                        'company_code': company_code,
                        'is_fee': True,
                        'reporting_category': 'fee'
                    }
                    transactions.append(fee_tx)

            # Handle refund if this payment was refunded
            if converted_refunded > 0 and refunded_date_str:
                refund_date = None
                try:
                    refund_date = datetime.strptime(refunded_date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    try:
                        refund_date = datetime.strptime(refunded_date_str, '%Y-%m-%d %H:%M')
                    except ValueError:
                        pass

                if refund_date:
                    # Refund reduces balance (negative gross, positive fee for refund processing)
                    # Stripe charges a fee on refunds (typically same as original fee proportion)
                    refund_fee = self._parse_decimal(row.get('Fee', '0'))  # Approximate refund fee

                    # Refund gross entry (credit - decreases balance)
                    refund_tx = {
                        'id': tx_id + '_refund',
                        'stripe_id': tx_id,
                        'date': refund_date.date(),
                        'nature': 'Refund',
                        'party': party,
                        'debit': 0,
                        'credit': float(converted_refunded),
                        'balance': 0,
                        'acknowledged': False,
                        'description': f"Refund for {description}",
                        'gross': float(-converted_refunded),
                        'amount': float(-converted_refunded),
                        'fee': 0,
                        'net_amount': float(-converted_refunded),
                        'currency': 'HKD',
                        'status': 'refunded',
                        'type': 'refund',
                        'created': refund_date,
                        'available_on': refund_date.date(),
                        'transfer_date': (refund_date + timedelta(days=2)).date(),
                        'account_name': self.company_names.get(company_code, 'Unknown Company'),
                        'company_code': company_code,
                        'reporting_category': 'refund'
                    }
                    transactions.append(refund_tx)

            return transactions if transactions else None

        except Exception as e:
            self.logger.error(f"Error parsing unified row: {e}")
            return None

    def _build_description_from_metadata(self, row):
        """Build description from metadata fields"""
        parts = []

        # Product name
        product = row.get('4. Product name (metadata)', '').strip()
        if product:
            parts.append(product)

        # Site
        site = row.get('1. Site (metadata)', '').strip() or row.get('site (metadata)', '').strip()
        if site and site not in parts:
            parts.append(site)

        # Type (subscription, donation, etc.)
        tx_type = row.get('webhook_event_type (metadata)', '').strip() or row.get('type (metadata)', '').strip()
        if tx_type:
            parts.append(tx_type)

        if parts:
            return ' - '.join(parts)
        else:
            return row.get('Description', '').strip() or 'Payment'
    
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
            # Parse created date - handle both column name variations
            created_str = row.get('Created date (UTC)', '') or row.get('Created (UTC)', '')
            created_str = created_str.strip()
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
            # First try explicit Transfer Date column
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
            
            # If no transfer date but we have a created date, use created + 2 days as estimated transfer
            # (Stripe typically transfers funds 2 days after transaction)
            if not transfer_date and created:
                transfer_date = (created + timedelta(days=2)).date()
            
            # Determine transaction type from ID or Type column
            transaction_type = row.get('Type', '').lower()
            
            # If no Type column, infer from ID prefix
            if not transaction_type:
                tx_id = row.get('id', '').strip()
                if tx_id.startswith('py_') or tx_id.startswith('pi_'):
                    transaction_type = 'payment'
                elif tx_id.startswith('ch_'):
                    transaction_type = 'charge'
                elif tx_id.startswith('re_'):
                    transaction_type = 'refund'
                elif tx_id.startswith('po_'):
                    transaction_type = 'payout'
                else:
                    # Default to payment if we have an amount
                    amount_str = row.get('Amount', '0')
                    if amount_str and amount_str != '0':
                        transaction_type = 'payment'
            
            # Parse amounts with enhanced fee handling
            amount = self._parse_decimal(row.get('Amount', '0'))
            fee = self._parse_decimal(row.get('Fee', '0'))
            net = self._parse_decimal(row.get('Net', '0'))
            
            # Don't estimate fees - use actual fee data from CSV
            # The Fee column should have the actual fees charged
            
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
        """Extract customer reference from metadata fields, prioritizing email addresses"""
        # First, check for email fields in the CSV - expanded list
        email_fields = [
            'Customer Email',
            'customer_email', 
            'email',
            'Email',
            'customer_email (metadata)',
            'email (metadata)',
            '2. User email (metadata)',  # From CGGE CSV format
            'Customer Description'  # Sometimes contains email
        ]
        
        for field in email_fields:
            value = row.get(field, '').strip()
            if value and '@' in value:
                return value
        
        # Check for userID in metadata if no email found
        user_id = row.get('userID (metadata)', '').strip()
        if user_id:
            # Try to find corresponding email in other fields first
            user_email = row.get('2. User email (metadata)', '').strip()
            if user_email and '@' in user_email:
                return user_email
            return f"User {user_id}"
        
        # Check for other customer identifiers
        site = row.get('site (metadata)', '').strip() or row.get('1. Site (metadata)', '').strip()
        stripe_plan = row.get('stripe_plan (metadata)', '').strip()
        
        if site and stripe_plan:
            return f"{site} - {stripe_plan}"
        elif site:
            return site
        elif stripe_plan:
            return stripe_plan
        
        return None
    
    def _extract_party_from_description(self, description):
        """Extract customer reference from description, prioritizing email addresses"""
        if not description:
            return "N/A"
        
        # Look for email pattern (prioritized)
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

        # Try to use Stripe report files first (most accurate)
        stripe_statement = self.generate_monthly_statement_from_stripe_reports(year, month, company_filter)
        if stripe_statement and 'error' not in stripe_statement:
            # Convert to old format for backward compatibility
            return {
                'transactions': stripe_statement.get('transactions', []),
                'opening_balance': stripe_statement['summary']['opening_balance'],
                'closing_balance': stripe_statement['summary']['closing_balance'],
                'month': month,
                'year': year,
                'company_filter': company_filter,
                'total_debit': stripe_statement['statistics']['charge_gross'],
                'total_credit': abs(stripe_statement['statistics']['payout_total']) + abs(stripe_statement['statistics']['refund_gross']),
                'source': 'stripe_reports'
            }

        # Fall back to calculating from unified file
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

    def generate_balance_summary(self, year, month, company_filter=None, start_day=1, end_day=None, starting_balance=None):
        """
        Generate Balance Summary matching Stripe's Balance Summary report format.

        This produces output consistent with:
        - cgge_Balance_Summary_HKD_2025-11-01_to_2025-11-29_UTC.csv

        Args:
            year: The year
            month: The month
            company_filter: Company code to filter by (e.g., 'cgge')
            start_day: Start day of month (default 1)
            end_day: End day of month (default last day of month)
            starting_balance: Optional known starting balance (if None, tries to calculate or read from previous month)
        """
        # Determine date range
        start_date = datetime(year, month, start_day).date()
        if end_day is None:
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month, end_day).date()

        # Get starting balance
        if starting_balance is not None:
            starting_balance = Decimal(str(starting_balance))
        else:
            # Try to get from previous month's Balance Summary file
            prev_month = month - 1
            prev_year = year
            if prev_month == 0:
                prev_month = 12
                prev_year = year - 1
            prev_summary = self._read_stripe_balance_summary(prev_year, prev_month, company_filter)
            if prev_summary and 'ending_balance' in prev_summary:
                starting_balance = Decimal(str(prev_summary['ending_balance']))
            else:
                # Fall back to calculating from transactions
                starting_balance = Decimal(str(self._get_previous_month_closing_balance(year, month, company_filter)))

        # Get all transactions
        all_transactions = self.import_transactions_from_csv()

        # Filter transactions for the period
        activity_gross = Decimal('0')
        activity_fee = Decimal('0')
        refund_gross = Decimal('0')
        refund_fee = Decimal('0')
        charge_count = 0
        refund_count = 0

        for tx in all_transactions:
            if company_filter and tx.get('company_code') != company_filter:
                continue

            tx_date = tx.get('date')
            if not tx_date or tx_date < start_date or tx_date > end_date:
                continue

            tx_type = tx.get('type', '')
            reporting_cat = tx.get('reporting_category', '')

            # Charges/Payments contribute to activity_gross
            if tx_type in ['charge', 'payment'] and not tx.get('is_fee'):
                activity_gross += Decimal(str(tx.get('debit', 0)))
                charge_count += 1
            # Fees reduce the activity
            elif tx_type == 'fee' or tx.get('is_fee'):
                activity_fee += Decimal(str(tx.get('credit', 0)))
            # Refunds are negative activity
            elif tx_type == 'refund':
                refund_gross += Decimal(str(tx.get('credit', 0)))
                refund_count += 1

        # Calculate activity net (gross - fees - refunds)
        # Note: In Stripe's Balance Summary format:
        # - activity_gross = charges gross - refund gross (refunds reduce the gross figure)
        # - activity_fee = total fees (shown as negative)
        # - activity_net = activity_gross + activity_fee
        total_gross = activity_gross - refund_gross  # Stripe shows this as "activity_gross"
        activity_net = total_gross - activity_fee  # This is the net activity

        # Try to read payouts from Stripe's Itemised Payouts file
        payouts_data = self._read_stripe_itemised_payouts(year, month, company_filter, start_date, end_date)
        payouts_gross = Decimal(str(payouts_data.get('gross', 0)))
        payouts_fee = Decimal(str(payouts_data.get('fee', 0)))
        payouts_net = payouts_gross - payouts_fee

        # Calculate ending balance: starting + activity - payouts
        ending_balance = Decimal(str(starting_balance)) + activity_net - payouts_net

        # For accurate results, read from the Stripe Balance Summary if available
        stripe_balance_summary = self._read_stripe_balance_summary(year, month, company_filter)
        if stripe_balance_summary:
            return stripe_balance_summary

        # Otherwise, calculate from transactions
        # Note: Stripe's activity_gross = charges - refunds (total_gross includes refunds already)
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'year': year,
                'month': month
            },
            'company': company_filter,
            'currency': 'hkd',
            'starting_balance': float(starting_balance),
            'activity': {
                'gross': float(total_gross),  # Stripe format: charges - refunds
                'fee': float(-activity_fee),
                'net': float(activity_net),
                'charge_count': charge_count,
                'refund_count': refund_count,
                'detail': {
                    'charges_gross': float(activity_gross),
                    'refunds_gross': float(-refund_gross)
                }
            },
            'payouts': {
                'gross': float(-payouts_gross),  # Negative because money leaves balance
                'fee': float(payouts_fee),
                'net': float(-payouts_net)  # Negative because money leaves balance
            },
            'ending_balance': float(ending_balance),
            'reconciliation': {
                'calculated_ending': float(Decimal(str(starting_balance)) + activity_net - (payouts_gross - payouts_fee)),
                'formula': 'starting_balance + activity_net - payouts_net'
            },
            'source': 'calculated'
        }

    def _build_party_lookup_from_unified(self, company_filter, year, month):
        """
        Build a lookup table from unified payments CSV to get party names.
        Returns a dict mapping (date, amount) -> party_info
        """
        lookup = {}

        # Find the unified file for this company
        pattern = f"{company_filter}_unified_*.csv"
        search_path = os.path.join(self.root_directory, pattern)
        files = glob.glob(search_path)

        if not files:
            self.logger.info(f"No unified file found for {company_filter}")
            return lookup

        # Use the most recent unified file
        unified_file = sorted(files)[-1]
        self.logger.info(f"Building party lookup from {unified_file}")

        try:
            with open(unified_file, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse date
                    created_str = row.get('Created date (UTC)', '').strip()
                    if not created_str:
                        continue

                    try:
                        created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            continue

                    # Only include transactions from the target month
                    if created.year != year or created.month != month:
                        continue

                    # Get amount - use Converted Amount (HKD) for matching with Stripe reports
                    amount_str = row.get('Converted Amount', '').strip()
                    if not amount_str:
                        amount_str = row.get('Amount', '0').strip()
                    try:
                        amount = float(amount_str) if amount_str else 0
                    except ValueError:
                        amount = 0

                    # Skip non-successful payments
                    status = row.get('Status', '').strip().lower()
                    if status not in ['paid', 'succeeded', 'captured']:
                        continue

                    # Get party info
                    party_name = row.get('3. User name (metadata)', '').strip()
                    if not party_name or party_name == 'Not provided':
                        party_name = row.get('Customer Email', '').strip()
                    if not party_name:
                        party_name = row.get('Customer Description', '').strip()

                    product_name = row.get('4. Product name (metadata)', '').strip()
                    customer_email = row.get('Customer Email', '').strip()

                    # If no party name, use product as description
                    if not party_name and product_name:
                        party_name = product_name[:30]

                    # Create lookup key based on date and amount
                    date_key = created.date()

                    # Get additional fields for Sales Transaction Details
                    site_service = row.get('1. Site (metadata)', '').strip()
                    if not site_service:
                        site_service = row.get('site (metadata)', '').strip()

                    # Get subscription plan info
                    subs_type = row.get('subs_type (metadata)', '').strip()
                    plan_days = row.get('plan_days (metadata)', '').strip()
                    subscription_plan = subs_type
                    if plan_days:
                        subscription_plan = f"{subs_type} ({plan_days} days)" if subs_type else f"({plan_days} days)"

                    # Get active and expiry dates
                    active_date = row.get('4. Active date (metadata)', '').strip()
                    if not active_date:
                        active_date = row.get('3. Active date (metadata)', '').strip()
                    expiry_date = row.get('5. Expiry date (metadata)', '').strip()
                    if not expiry_date:
                        expiry_date = row.get('4. Expiry date (metadata)', '').strip()

                    # Get original amount and currency
                    original_amount = row.get('Amount', '').strip()
                    original_currency = row.get('Currency', '').strip().upper()

                    # Get fee
                    fee_str = row.get('Fee', '0').strip()
                    try:
                        fee = float(fee_str) if fee_str else 0
                    except ValueError:
                        fee = 0

                    # Store in lookup with multiple possible keys
                    lookup_key = (date_key, amount)
                    lookup[lookup_key] = {
                        'party_name': party_name if party_name else 'Customer',
                        'product': product_name,
                        'email': customer_email,
                        'payment_id': row.get('id', ''),
                        'customer_id': row.get('Customer ID', '').strip(),
                        'user_name': row.get('3. User name (metadata)', '').strip(),
                        'site_service': site_service,
                        'subscription_plan': subscription_plan,
                        'active_date': active_date,
                        'expiry_date': expiry_date if expiry_date else 'N/A',
                        'original_amount': original_amount,
                        'original_currency': original_currency,
                        'converted_amount': amount,
                        'processing_fee': fee,
                        'transaction_id': row.get('id', ''),
                        'created_date': created_str
                    }

                    # Also store with rounded amounts for matching
                    lookup[(date_key, round(amount, 2))] = lookup[lookup_key]

        except Exception as e:
            self.logger.error(f"Error building party lookup: {e}")

        self.logger.info(f"Built party lookup with {len(lookup)} entries")
        return lookup

    def _generate_wechat_monthly_statement(self, year, month, start_day=1, end_day=None):
        """
        Generate monthly statement for CGGE (Shenzhen) WeChat data.

        WeChat data is monthly summary data (total sales per month), not individual transactions.
        This method generates a simplified statement format suitable for WeChat data.
        """
        company_filter = 'cgge_sz'

        # Determine date range
        start_date = datetime(year, month, start_day).date()
        if end_day is None:
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month, end_day).date()

        # Get WeChat transactions
        all_transactions = self.import_transactions_from_csv()

        # Filter for cgge_sz transactions in the specified month
        monthly_transactions = []
        for tx in all_transactions:
            if tx.get('company_code') != 'cgge_sz':
                continue
            tx_date = tx.get('date')
            if tx_date and tx_date.year == year and tx_date.month == month:
                monthly_transactions.append(tx)

        if not monthly_transactions:
            return {'error': f'No WeChat data found for cgge_sz {year}-{month:02d}. Upload a WeChat TRADE_DATA CSV file.'}

        # Calculate totals
        total_sales = Decimal('0')
        total_transactions = 0

        for tx in monthly_transactions:
            total_sales += Decimal(str(tx.get('gross', 0)))
            total_transactions += tx.get('transaction_count', 1)

        # Get previous month's closing balance as opening balance
        opening_balance = Decimal(str(self._get_previous_month_closing_balance(year, month, company_filter)))

        # WeChat typically doesn't have separate payouts in the same way Stripe does
        # The sales amount is the net amount received
        closing_balance = opening_balance + total_sales

        # Build transaction list for display
        all_statement_transactions = []
        running_balance = opening_balance

        # Add opening balance entry
        all_statement_transactions.append({
            'date': start_date,
            'type': 'opening_balance',
            'nature': 'Opening Balance',
            'party': 'Brought Forward',
            'description': f'Opening balance for {start_date.strftime("%B %Y")}',
            'gross': 0,
            'fee': 0,
            'net': 0,
            'debit': 0,
            'credit': float(opening_balance) if opening_balance >= 0 else 0,
            'balance': float(running_balance),
            'acknowledged': 'Yes',
            'category': 'balance'
        })

        # Add WeChat transaction entries
        for tx in monthly_transactions:
            gross = Decimal(str(tx.get('gross', 0)))
            running_balance += gross

            all_statement_transactions.append({
                'date': tx.get('created') or tx.get('date'),
                'type': 'wechat_sales',
                'nature': 'WeChat Sales',
                'party': 'WeChat Customers',
                'description': tx.get('description', 'WeChat Sales'),
                'gross': float(gross),
                'fee': 0,
                'net': float(gross),
                'debit': float(gross),
                'credit': 0,
                'balance': float(running_balance),
                'acknowledged': 'No',
                'category': 'activity',
                'transaction_count': tx.get('transaction_count', 0),
                'currency': 'CNY'
            })

        # Add subtotal
        total_debit = float(total_sales)
        all_statement_transactions.append({
            'date': end_date,
            'type': 'subtotal',
            'nature': 'SUBTOTAL',
            'party': '',
            'description': '',
            'debit': total_debit,
            'credit': 0,
            'gross': 0,
            'fee': 0,
            'net': 0,
            'balance': 0,
            'acknowledged': '',
            'category': 'subtotal'
        })

        # Add closing balance entry
        all_statement_transactions.append({
            'date': end_date,
            'type': 'closing_balance',
            'nature': 'Closing Balance',
            'party': 'Carry Forward',
            'description': f'Closing balance for {end_date.strftime("%B %Y")}',
            'gross': 0,
            'fee': 0,
            'net': 0,
            'debit': 0,
            'credit': float(closing_balance) if closing_balance >= 0 else 0,
            'balance': float(closing_balance),
            'acknowledged': 'Yes',
            'category': 'balance'
        })

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'year': year,
                'month': month
            },
            'company': company_filter,
            'currency': 'CNY',
            'summary': {
                'opening_balance': float(opening_balance),
                'activity': {
                    'gross': float(total_sales),
                    'fee': 0,
                    'net': float(total_sales)
                },
                'payouts': {
                    'gross': 0,
                    'fee': 0,
                    'net': 0
                },
                'closing_balance': float(closing_balance)
            },
            'statistics': {
                'charge_count': total_transactions,
                'charge_gross': float(total_sales),
                'charge_fees': 0,
                'charge_net': float(total_sales),
                'refund_count': 0,
                'refund_gross': 0,
                'payout_count': 0,
                'payout_total': 0
            },
            'transactions': all_statement_transactions,
            'sales_details': [{
                'sale_number': i + 1,
                'date': (tx.get('date') or tx.get('created')).strftime('%Y-%m-%d') if tx.get('date') or tx.get('created') else '',
                'amount': tx.get('gross', 0),
                'customer_email': 'WeChat Customer',
                'user_name': 'WeChat Users',
                'site_service': 'WeChat Pay',
                'subscription_plan': '',
                'active_date': '',
                'expiry_date': 'N/A',
                'original_amount': f"{tx.get('gross', 0)} CNY",
                'converted_amount': tx.get('gross', 0),
                'processing_fee': 0,
                'customer_id': '',
                'transaction_id': tx.get('id', ''),
                'transaction_count': tx.get('transaction_count', 0)
            } for i, tx in enumerate(monthly_transactions)],
            'source': 'wechat_data'
        }

    def generate_monthly_statement_from_stripe_reports(self, year, month, company_filter, start_day=1, end_day=None):
        """
        Generate a complete monthly statement using the 3 Stripe report CSV files:
        1. Balance Summary - for opening/closing balances and totals
        2. Itemised Balance Change from Activity - for transaction details
        3. Itemised Payouts - for payout details

        If the Stripe report doesn't cover the full month (e.g., ends on Nov 29),
        this method will supplement with data from the unified file.

        For cgge_sz (WeChat), uses WeChat-specific statement generation.

        This is the authoritative source for monthly statements.
        """
        # Handle WeChat (cgge_sz) separately
        if company_filter == 'cgge_sz':
            return self._generate_wechat_monthly_statement(year, month, start_day, end_day)

        # Determine date range
        start_date = datetime(year, month, start_day).date()
        if end_day is None:
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(year, month, end_day).date()

        # Read Balance Summary
        balance_summary = self._read_stripe_balance_summary(year, month, company_filter)
        if not balance_summary:
            return {'error': f'Balance Summary file not found for {company_filter} {year}-{month:02d}'}

        # Check if Stripe report covers the full requested period
        stripe_end_date_str = balance_summary.get('period', {}).get('end_date', '')
        stripe_end_date = None
        if stripe_end_date_str:
            try:
                stripe_end_date = datetime.strptime(stripe_end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # If Stripe report ends before our requested end_date, supplement with unified file
        supplement_transactions = []
        supplement_activity_gross = Decimal('0')
        supplement_activity_fee = Decimal('0')
        supplement_activity_net = Decimal('0')

        if stripe_end_date and stripe_end_date < end_date:
            self.logger.info(f"Stripe report ends on {stripe_end_date}, supplementing with unified file data until {end_date}")
            # Get transactions from unified file for the gap period
            all_transactions = self.import_transactions_from_csv()
            for tx in all_transactions:
                if company_filter and tx.get('company_code') != company_filter:
                    continue
                tx_date = tx.get('date')
                if tx_date and stripe_end_date < tx_date <= end_date:
                    supplement_transactions.append(tx)
                    tx_type = tx.get('type', '')
                    if tx_type in ['charge', 'payment'] and not tx.get('is_fee'):
                        supplement_activity_gross += Decimal(str(tx.get('debit', 0)))
                    elif tx_type == 'fee' or tx.get('is_fee'):
                        supplement_activity_fee += Decimal(str(tx.get('credit', 0)))
                    elif tx_type == 'refund':
                        supplement_activity_gross -= Decimal(str(tx.get('credit', 0)))

            supplement_activity_net = supplement_activity_gross - supplement_activity_fee

        # Read Itemised Activity
        activity_transactions = self._read_stripe_itemised_activity(year, month, company_filter, start_date, end_date)

        # Read Itemised Payouts
        payout_transactions = self._read_stripe_itemised_payouts_detail(year, month, company_filter, start_date, end_date)

        # Build party lookup from unified CSV
        party_lookup = self._build_party_lookup_from_unified(company_filter, year, month)

        # Build complete statement
        opening_balance = Decimal(str(balance_summary.get('starting_balance', 0)))

        # Create transaction list with running balance
        all_transactions = []
        running_balance = opening_balance

        # Add opening balance entry (per sample: Nature="Opening Balance", Party="Brought Forward", Credit=amount)
        all_transactions.append({
            'date': start_date,
            'type': 'opening_balance',
            'nature': 'Opening Balance',
            'party': 'Brought Forward',
            'description': f'Opening balance for {start_date.strftime("%B %Y")}',
            'gross': 0,
            'fee': 0,
            'net': 0,
            'debit': 0,
            'credit': float(opening_balance) if opening_balance >= 0 else 0,
            'balance': float(running_balance),
            'acknowledged': 'Yes',
            'category': 'balance'
        })

        # Combine activity and payout transactions, sort by date
        combined = []

        for tx in activity_transactions:
            # Look up party info from unified file
            tx_date = tx['created'].date() if tx['created'] else None
            gross = tx.get('gross', 0)
            party_info = party_lookup.get((tx_date, gross)) or party_lookup.get((tx_date, round(gross, 2)))

            party_name = 'Customer'
            if party_info:
                party_name = party_info.get('party_name', 'Customer')

            # Determine nature based on category
            category = tx.get('reporting_category', '')
            gross_val = float(tx.get('gross', 0))
            fee_val = float(tx.get('fee', 0))

            # Determine product description
            product_desc = 'Gross'
            if party_info and party_info.get('product'):
                product_desc = party_info['product']

            # Per sample format: Split each transaction into Gross row and Fee row
            if category == 'charge':
                # Row 1: Gross Charge (Debit = gross amount)
                combined.append({
                    'date': tx['created'],
                    'sort_key': (tx['created'], 0),  # Gross first
                    'party': party_name,
                    'nature': 'Gross Charge',
                    'description': product_desc,
                    'debit': gross_val if gross_val > 0 else 0,
                    'credit': 0,
                    'gross': gross_val,
                    'fee': 0,
                    'net': gross_val,  # Gross row adds the full gross
                    'balance_transaction_id': tx.get('balance_transaction_id'),
                    'created': tx['created'],
                    'currency': tx.get('currency', 'HKD'),
                    'reporting_category': 'charge',
                    'acknowledged': 'No',
                    'type': 'activity'
                })
                # Row 2: Processing Fee (Credit = fee amount)
                if fee_val > 0:
                    combined.append({
                        'date': tx['created'],
                        'sort_key': (tx['created'], 1),  # Fee after gross
                        'party': 'Stripe',
                        'nature': 'Processing Fee',
                        'description': f'Processing fee for',
                        'debit': 0,
                        'credit': fee_val,
                        'gross': 0,
                        'fee': fee_val,
                        'net': -fee_val,  # Fee row subtracts the fee
                        'balance_transaction_id': tx.get('balance_transaction_id'),
                        'created': tx['created'],
                        'currency': tx.get('currency', 'HKD'),
                        'reporting_category': 'fee',
                        'acknowledged': 'No',
                        'type': 'activity'
                    })
            elif category == 'refund':
                # Refund: Credit = refund amount (money going out)
                combined.append({
                    'date': tx['created'],
                    'sort_key': (tx['created'], 0),
                    'party': party_name,
                    'nature': 'Refund',
                    'description': 'Refund',
                    'debit': 0,
                    'credit': abs(gross_val),
                    'gross': gross_val,
                    'fee': fee_val,
                    'net': tx.get('net', gross_val + fee_val),
                    'balance_transaction_id': tx.get('balance_transaction_id'),
                    'created': tx['created'],
                    'currency': tx.get('currency', 'HKD'),
                    'reporting_category': 'refund',
                    'acknowledged': 'No',
                    'type': 'activity'
                })
            else:
                # Other activity types
                nature = category.title() if category else 'Activity'
                combined.append({
                    'date': tx['created'],
                    'sort_key': (tx['created'], 0),
                    'party': party_name,
                    'nature': nature,
                    'description': tx.get('description', '') or nature,
                    'debit': gross_val if gross_val > 0 else 0,
                    'credit': fee_val if fee_val > 0 else (abs(gross_val) if gross_val < 0 else 0),
                    'gross': gross_val,
                    'fee': fee_val,
                    'net': tx.get('net', 0),
                    'balance_transaction_id': tx.get('balance_transaction_id'),
                    'created': tx['created'],
                    'currency': tx.get('currency', 'HKD'),
                    'reporting_category': category,
                    'acknowledged': 'No',
                    'type': 'activity'
                })

        for tx in payout_transactions:
            # Payouts are money going out = Credit (per sample: Party="STRIPE PAYOUT", Nature="Payout")
            gross_val = float(tx.get('gross', 0))
            combined.append({
                'date': tx['effective_at'],
                'sort_key': (tx['effective_at'], 2),  # Payouts after activity on same date
                'party': 'STRIPE PAYOUT',
                'nature': 'Payout',
                'description': 'STRIPE PAYOUT',
                'debit': 0,
                'credit': abs(gross_val),
                'gross': gross_val,
                'fee': tx.get('fee', 0),
                'net': tx.get('net', gross_val),
                'balance_transaction_id': tx.get('balance_transaction_id'),
                'created': tx.get('effective_at'),
                'currency': tx.get('currency', 'HKD'),
                'reporting_category': 'payout',
                'acknowledged': 'No',
                'type': 'payout'
            })

        # Add supplement transactions (from unified file for dates not covered by Stripe report)
        # Per sample format: Split into Gross Charge and Processing Fee rows
        for tx in supplement_transactions:
            tx_date = tx.get('date')
            if tx_date:
                tx_type = tx.get('type', 'charge')
                is_fee = tx.get('is_fee', False)
                gross_val = tx.get('debit', 0) if not is_fee else 0
                fee_val = tx.get('credit', 0) if is_fee else 0
                customer_name = tx.get('customer_name', 'Customer')
                description = tx.get('description', '')

                tx_datetime = datetime.combine(tx_date, datetime.min.time())

                if is_fee:
                    # This is a fee row
                    combined.append({
                        'date': tx_datetime,
                        'sort_key': (tx_datetime, 1),  # Fee after gross
                        'party': 'Stripe',
                        'nature': 'Processing Fee',
                        'description': f'Processing fee for',
                        'debit': 0,
                        'credit': fee_val,
                        'gross': 0,
                        'fee': fee_val,
                        'net': -fee_val,
                        'balance_transaction_id': tx.get('id', ''),
                        'created': tx_datetime,
                        'currency': 'HKD',
                        'reporting_category': 'fee',
                        'acknowledged': 'No',
                        'type': 'activity',
                        'source': 'unified_file'
                    })
                else:
                    # This is a gross charge row
                    combined.append({
                        'date': tx_datetime,
                        'sort_key': (tx_datetime, 0),  # Gross first
                        'party': customer_name,
                        'nature': 'Gross Charge',
                        'description': description or 'Gross',
                        'debit': gross_val if gross_val > 0 else 0,
                        'credit': 0,
                        'gross': gross_val,
                        'fee': 0,
                        'net': gross_val,
                        'balance_transaction_id': tx.get('id', ''),
                        'created': tx_datetime,
                        'currency': 'HKD',
                        'reporting_category': 'charge',
                        'acknowledged': 'No',
                        'type': 'activity',
                        'source': 'unified_file'
                    })

        # Sort by date
        combined.sort(key=lambda x: x['sort_key'])

        # Calculate running balance
        for tx in combined:
            net = Decimal(str(tx.get('net', 0)))
            running_balance += net
            tx['balance'] = float(running_balance)
            all_transactions.append(tx)

        # Calculate SUBTOTAL of all debits and credits
        total_debit = sum(float(tx.get('debit', 0)) for tx in combined)
        total_credit = sum(float(tx.get('credit', 0)) for tx in combined)

        # Add SUBTOTAL row (per sample format)
        all_transactions.append({
            'date': end_date,
            'type': 'subtotal',
            'nature': 'SUBTOTAL',
            'party': '',
            'description': '',
            'debit': total_debit,
            'credit': total_credit,
            'gross': 0,
            'fee': 0,
            'net': 0,
            'balance': 0,
            'acknowledged': '',
            'category': 'subtotal'
        })

        # Add closing balance entry (per sample: Nature="Closing Balance", Party="Carry Forward", Credit=amount)
        # Use Stripe's ending balance + any supplement activity
        stripe_ending_balance = Decimal(str(balance_summary.get('ending_balance', 0)))
        closing_balance = stripe_ending_balance + supplement_activity_net
        all_transactions.append({
            'date': end_date,
            'type': 'closing_balance',
            'nature': 'Closing Balance',
            'party': 'Carry Forward',
            'description': f'Closing balance for {end_date.strftime("%B %Y")}',
            'gross': 0,
            'fee': 0,
            'net': 0,
            'debit': 0,
            'credit': float(closing_balance) if closing_balance >= 0 else 0,
            'balance': float(closing_balance),
            'acknowledged': 'Yes',
            'category': 'balance'
        })

        # Summary statistics
        charges = [tx for tx in activity_transactions if tx.get('reporting_category') == 'charge']
        refunds = [tx for tx in activity_transactions if tx.get('reporting_category') == 'refund']

        # Include supplement in activity totals
        total_activity_gross = Decimal(str(balance_summary.get('activity', {}).get('gross', 0))) + supplement_activity_gross
        total_activity_fee = Decimal(str(balance_summary.get('activity', {}).get('fee', 0))) - supplement_activity_fee  # fee is negative
        total_activity_net = Decimal(str(balance_summary.get('activity', {}).get('net', 0))) + supplement_activity_net

        # Count supplement charges
        supplement_charges = [tx for tx in supplement_transactions if tx.get('type') in ['charge', 'payment'] and not tx.get('is_fee')]

        # Build Sales Transaction Details from party_lookup (only Gross Charge transactions)
        sales_details = []
        sale_number = 0
        for tx in all_transactions:
            if tx.get('nature') == 'Gross Charge' and tx.get('type') != 'subtotal':
                tx_date = tx.get('created') or tx.get('date')
                gross_amount = float(tx.get('gross', 0))

                # Try to get date_key for lookup
                date_key = None
                if tx_date:
                    if hasattr(tx_date, 'date'):
                        date_key = tx_date.date()
                    elif isinstance(tx_date, str):
                        # Handle various date string formats
                        from datetime import datetime as dt
                        try:
                            if 'T' in tx_date:
                                # ISO format with T: "2025-11-02T12:00:00Z"
                                date_key = dt.fromisoformat(tx_date.replace('Z', '+00:00')).date()
                            elif tx_date[:4].isdigit():
                                # ISO format: "2025-11-02"
                                date_key = dt.strptime(tx_date[:10], '%Y-%m-%d').date()
                            elif ',' in tx_date:
                                # HTTP date format: "Sun, 02 Nov 2025 03:19:33 GMT"
                                date_key = dt.strptime(tx_date, '%a, %d %b %Y %H:%M:%S %Z').date()
                            else:
                                date_key = None
                        except:
                            date_key = None
                    else:
                        date_key = tx_date

                # Look up party info
                party_info = None
                if date_key:
                    party_info = party_lookup.get((date_key, gross_amount)) or party_lookup.get((date_key, round(gross_amount, 2)))

                # Always add a sale entry, using party_info if available, else use tx data
                sale_number += 1
                if date_key and hasattr(date_key, 'strftime'):
                    sale_date = date_key.strftime('%Y-%m-%d')
                elif tx_date and hasattr(tx_date, 'strftime'):
                    sale_date = tx_date.strftime('%Y-%m-%d')
                else:
                    sale_date = str(tx_date)[:10] if tx_date else ''

                if party_info:
                    sales_details.append({
                        'sale_number': sale_number,
                        'date': sale_date,
                        'amount': gross_amount,
                        'customer_email': party_info.get('email', ''),
                        'user_name': party_info.get('user_name', party_info.get('party_name', '')),
                        'site_service': party_info.get('site_service', ''),
                        'subscription_plan': party_info.get('subscription_plan', ''),
                        'active_date': party_info.get('active_date', sale_date),
                        'expiry_date': party_info.get('expiry_date', 'N/A'),
                        'original_amount': f"{party_info.get('original_amount', '')} {party_info.get('original_currency', '')}",
                        'converted_amount': gross_amount,
                        'processing_fee': party_info.get('processing_fee', 0),
                        'customer_id': party_info.get('customer_id', ''),
                        'transaction_id': party_info.get('transaction_id', '')
                    })
                else:
                    # Use data from transaction itself
                    sales_details.append({
                        'sale_number': sale_number,
                        'date': sale_date,
                        'amount': gross_amount,
                        'customer_email': tx.get('party', ''),
                        'user_name': tx.get('party', ''),
                        'site_service': '',
                        'subscription_plan': '',
                        'active_date': sale_date,
                        'expiry_date': 'N/A',
                        'original_amount': '',
                        'converted_amount': gross_amount,
                        'processing_fee': 0,
                        'customer_id': '',
                        'transaction_id': tx.get('balance_transaction_id', '')
                    })

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'year': year,
                'month': month,
                'stripe_report_end_date': stripe_end_date.isoformat() if stripe_end_date else None
            },
            'company': company_filter,
            'currency': 'HKD',
            'summary': {
                'opening_balance': float(opening_balance),
                'activity': {
                    'gross': float(total_activity_gross),
                    'fee': float(total_activity_fee),
                    'net': float(total_activity_net)
                },
                'payouts': {
                    'gross': balance_summary.get('payouts', {}).get('gross', 0),
                    'fee': balance_summary.get('payouts', {}).get('fee', 0),
                    'net': balance_summary.get('payouts', {}).get('net', 0)
                },
                'closing_balance': float(closing_balance)
            },
            'statistics': {
                'charge_count': len(charges) + len(supplement_charges),
                'charge_gross': float(sum(Decimal(str(tx.get('gross', 0))) for tx in charges) + supplement_activity_gross),
                'charge_fees': float(sum(Decimal(str(tx.get('fee', 0))) for tx in charges) + supplement_activity_fee),
                'charge_net': float(sum(Decimal(str(tx.get('net', 0))) for tx in charges) + supplement_activity_net),
                'refund_count': len(refunds),
                'refund_gross': float(sum(Decimal(str(tx.get('gross', 0))) for tx in refunds)),
                'refund_fees': float(sum(Decimal(str(tx.get('fee', 0))) for tx in refunds)),
                'refund_net': float(sum(Decimal(str(tx.get('net', 0))) for tx in refunds)),
                'payout_count': len(payout_transactions),
                'payout_total': float(sum(Decimal(str(tx.get('net', 0))) for tx in payout_transactions)),
                'supplement_transaction_count': len(supplement_transactions)
            },
            'transactions': all_transactions,
            'activity_detail': activity_transactions,
            'payout_detail': payout_transactions,
            'supplement_detail': supplement_transactions if supplement_transactions else None,
            'sales_details': sales_details,
            'source': 'stripe_reports' + ('_with_supplement' if supplement_transactions else '')
        }

    def _read_stripe_itemised_activity(self, year, month, company_filter, start_date, end_date):
        """Read itemised balance change from activity CSV file"""
        # First, try to find balance_history.csv file (new format)
        balance_history_patterns = [
            f"{company_filter}_balance_history.csv",
            f"{company_filter.upper()}_balance_history.csv",
        ]

        for pattern in balance_history_patterns:
            # Check in data directory first
            data_dir = os.path.join(self.root_directory, 'data')
            file_path = os.path.join(data_dir, pattern)
            if os.path.exists(file_path):
                self.logger.info(f"Found balance_history file: {file_path}")
                return self._parse_balance_history_csv(file_path, start_date, end_date)

            # Check in root directory
            file_path = os.path.join(self.root_directory, pattern)
            if os.path.exists(file_path):
                self.logger.info(f"Found balance_history file: {file_path}")
                return self._parse_balance_history_csv(file_path, start_date, end_date)

        # Fall back to original Itemised_balance_change format
        pattern = f"{company_filter}_Itemised_balance_change_from_activity_*.csv"
        search_path = os.path.join(self.root_directory, pattern)
        files = glob.glob(search_path)

        if not files:
            return []

        # Find file matching the year/month
        for file_path in files:
            filename = os.path.basename(file_path)
            if f"{year}-{month:02d}" in filename:
                return self._parse_stripe_itemised_activity(file_path)

        return []

    def _parse_balance_history_csv(self, file_path, start_date, end_date):
        """Parse the new balance_history.csv format (Stripe Balance History export)"""
        transactions = []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse created date - format: "2025-12-24 02:52"
                    created_str = row.get('Created (UTC)', '').strip()
                    created = None
                    if created_str:
                        try:
                            created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            try:
                                created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                continue

                    # Filter by date range
                    if created:
                        created_date = created.date()
                        start_date_cmp = start_date.date() if hasattr(start_date, 'date') else start_date
                        end_date_cmp = end_date.date() if hasattr(end_date, 'date') else end_date
                        if created_date < start_date_cmp or created_date > end_date_cmp:
                            continue

                    # Parse available_on date
                    available_str = row.get('Available On (UTC)', '').strip()
                    available_on = None
                    if available_str:
                        try:
                            available_on = datetime.strptime(available_str, '%Y-%m-%d %H:%M')
                        except ValueError:
                            try:
                                available_on = datetime.strptime(available_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                pass

                    # Parse amounts
                    amount = self._parse_decimal(row.get('Amount', '0'))
                    fee = self._parse_decimal(row.get('Fee', '0'))
                    net = self._parse_decimal(row.get('Net', '0'))

                    # Get transaction type and map to reporting_category
                    tx_type = row.get('Type', '').strip().lower()

                    # Map Type to reporting_category
                    category_map = {
                        'payment': 'charge',
                        'charge': 'charge',
                        'payment_refund': 'refund',
                        'refund': 'refund',
                        'payout': 'payout',
                    }
                    reporting_category = category_map.get(tx_type, tx_type)

                    # Skip payouts - they're handled separately
                    if tx_type == 'payout':
                        continue

                    # Get description and customer info
                    description = row.get('Description', '').strip()
                    customer_email = row.get('Customer Email', '').strip()
                    customer_name = row.get('3. User name (metadata)', '').strip()
                    site = row.get('1. Site (metadata)', '').strip()

                    # Get original amount info
                    customer_amount = row.get('Customer Facing Amount', '').strip()
                    customer_currency = row.get('Customer Facing Currency', '').strip()

                    # Get subscription/product info
                    product_name = row.get('4. Product name (metadata)', '').strip()
                    subs_type = row.get('subs_type (metadata)', '').strip()
                    plan_days = row.get('plan_days (metadata)', '').strip()
                    active_date = row.get('4. Active date (metadata)', '') or row.get('3. Active date (metadata)', '')
                    expiry_date = row.get('5. Expiry date (metadata)', '') or row.get('4. Expiry date (metadata)', '')

                    transactions.append({
                        'balance_transaction_id': row.get('id', '').strip(),
                        'source_id': row.get('Source', '').strip(),
                        'created': created,
                        'available_on': available_on,
                        'currency': row.get('Currency', 'hkd').strip().upper(),
                        'gross': float(amount),  # Amount is gross
                        'fee': float(fee),
                        'net': float(net),
                        'reporting_category': reporting_category,
                        'description': description,
                        'type': 'activity',
                        # Additional metadata for sales details
                        'customer_email': customer_email,
                        'customer_name': customer_name,
                        'site': site,
                        'customer_amount': customer_amount,
                        'customer_currency': customer_currency,
                        'product_name': product_name,
                        'subs_type': subs_type,
                        'plan_days': plan_days,
                        'active_date': active_date.strip() if active_date else '',
                        'expiry_date': expiry_date.strip() if expiry_date else '',
                    })

        except Exception as e:
            self.logger.error(f"Error parsing balance_history CSV: {e}")

        return transactions

    def _parse_stripe_itemised_activity(self, file_path):
        """Parse Stripe's Itemised Balance Change from Activity CSV format"""
        transactions = []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse created date
                    created_str = row.get('created', '').strip()
                    created = None
                    if created_str:
                        try:
                            created = datetime.strptime(created_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                            except ValueError:
                                continue

                    # Parse available_on date
                    available_str = row.get('available_on', '').strip()
                    available_on = None
                    if available_str:
                        try:
                            available_on = datetime.strptime(available_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                available_on = datetime.strptime(available_str, '%Y-%m-%d %H:%M')
                            except ValueError:
                                pass

                    gross = self._parse_decimal(row.get('gross', '0'))
                    fee = self._parse_decimal(row.get('fee', '0'))
                    net = self._parse_decimal(row.get('net', '0'))
                    category = row.get('reporting_category', '').strip()
                    description = row.get('description', '').strip()

                    transactions.append({
                        'balance_transaction_id': row.get('balance_transaction_id', '').strip(),
                        'created': created,
                        'available_on': available_on,
                        'currency': row.get('currency', 'hkd').strip().upper(),
                        'gross': float(gross),
                        'fee': float(fee),
                        'net': float(net),
                        'reporting_category': category,
                        'description': description,
                        'type': 'activity'
                    })

        except Exception as e:
            self.logger.error(f"Error parsing Stripe Itemised Activity: {e}")

        return transactions

    def _read_stripe_itemised_payouts_detail(self, year, month, company_filter, start_date, end_date):
        """Read itemised payouts CSV file with full details"""
        # First, try to find balance_history.csv file (new format) and extract payouts
        balance_history_patterns = [
            f"{company_filter}_balance_history.csv",
            f"{company_filter.upper()}_balance_history.csv",
        ]

        for pattern in balance_history_patterns:
            # Check in data directory first
            data_dir = os.path.join(self.root_directory, 'data')
            file_path = os.path.join(data_dir, pattern)
            if os.path.exists(file_path):
                self.logger.info(f"Extracting payouts from balance_history file: {file_path}")
                return self._parse_payouts_from_balance_history(file_path, start_date, end_date)

            # Check in root directory
            file_path = os.path.join(self.root_directory, pattern)
            if os.path.exists(file_path):
                self.logger.info(f"Extracting payouts from balance_history file: {file_path}")
                return self._parse_payouts_from_balance_history(file_path, start_date, end_date)

        # Fall back to original Itemised_payouts format
        pattern = f"{company_filter}_Itemised_payouts_*.csv"
        search_path = os.path.join(self.root_directory, pattern)
        files = glob.glob(search_path)

        if not files:
            return []

        for file_path in files:
            filename = os.path.basename(file_path)
            if f"{year}-{month:02d}" in filename:
                return self._parse_stripe_itemised_payouts_detail(file_path)

        return []

    def _parse_payouts_from_balance_history(self, file_path, start_date, end_date):
        """Extract payout transactions from balance_history.csv"""
        payouts = []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Only process payout transactions
                    tx_type = row.get('Type', '').strip().lower()
                    if tx_type != 'payout':
                        continue

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
                                continue

                    # Filter by date range
                    if created:
                        created_date = created.date()
                        start_date_cmp = start_date.date() if hasattr(start_date, 'date') else start_date
                        end_date_cmp = end_date.date() if hasattr(end_date, 'date') else end_date
                        if created_date < start_date_cmp or created_date > end_date_cmp:
                            continue

                    # Parse amounts (payouts have negative amounts)
                    amount = self._parse_decimal(row.get('Amount', '0'))
                    fee = self._parse_decimal(row.get('Fee', '0'))
                    net = self._parse_decimal(row.get('Net', '0'))

                    payouts.append({
                        'payout_id': row.get('Source', '').strip(),
                        'balance_transaction_id': row.get('id', '').strip(),
                        'effective_at': created,
                        'arrival_date': created.date() if created else None,
                        'currency': row.get('Currency', 'hkd').strip().upper(),
                        'gross': float(amount),
                        'fee': float(fee),
                        'net': float(net),
                        'description': row.get('Description', '').strip() or 'STRIPE PAYOUT',
                        'type': 'payout'
                    })

        except Exception as e:
            self.logger.error(f"Error extracting payouts from balance_history: {e}")

        return payouts

    def _parse_stripe_itemised_payouts_detail(self, file_path):
        """Parse Stripe's Itemised Payouts CSV format with full details"""
        payouts = []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse effective_at date
                    effective_str = row.get('effective_at', '').strip()
                    effective_at = None
                    if effective_str:
                        try:
                            effective_at = datetime.strptime(effective_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            try:
                                effective_at = datetime.strptime(effective_str, '%Y-%m-%d %H:%M')
                            except ValueError:
                                continue

                    # Parse arrival date
                    arrival_str = row.get('payout_expected_arrival_date', '').strip()
                    arrival_date = None
                    if arrival_str:
                        try:
                            arrival_date = datetime.strptime(arrival_str, '%Y-%m-%d %H:%M:%S').date()
                        except ValueError:
                            try:
                                arrival_date = datetime.strptime(arrival_str, '%Y-%m-%d').date()
                            except ValueError:
                                pass

                    gross = self._parse_decimal(row.get('gross', '0'))
                    fee = self._parse_decimal(row.get('fee', '0'))
                    net = self._parse_decimal(row.get('net', '0'))

                    payouts.append({
                        'payout_id': row.get('payout_id', '').strip(),
                        'balance_transaction_id': row.get('balance_transaction_id', '').strip(),
                        'effective_at': effective_at,
                        'arrival_date': arrival_date,
                        'currency': row.get('currency', 'hkd').strip().upper(),
                        'gross': float(-gross),  # Negative because money leaves balance
                        'fee': float(fee),
                        'net': float(-net),  # Negative because money leaves balance
                        'status': row.get('payout_status', '').strip(),
                        'description': row.get('description', '').strip(),
                        'reporting_category': 'payout',
                        'type': 'payout'
                    })

        except Exception as e:
            self.logger.error(f"Error parsing Stripe Itemised Payouts: {e}")

        return payouts

    def _read_stripe_itemised_payouts(self, year, month, company_filter, start_date, end_date):
        """Read payouts from Stripe's Itemised Payouts CSV file if available"""
        # Look for files like: cgge_Itemised_payouts_HKD_2025-11-01_to_2025-11-29_UTC.csv
        pattern = f"{company_filter}_Itemised_payouts_*.csv"
        search_path = os.path.join(self.root_directory, pattern)
        files = glob.glob(search_path)

        if not files:
            return {'gross': 0, 'fee': 0, 'count': 0}

        # Find file matching the year/month
        for file_path in files:
            filename = os.path.basename(file_path)
            if f"{year}-{month:02d}" in filename:
                return self._parse_stripe_itemised_payouts(file_path, start_date, end_date)

        return {'gross': 0, 'fee': 0, 'count': 0}

    def _parse_stripe_itemised_payouts(self, file_path, start_date, end_date):
        """Parse Stripe's Itemised Payouts CSV format"""
        try:
            total_gross = Decimal('0')
            total_fee = Decimal('0')
            count = 0

            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    # Parse effective_at date
                    effective_str = row.get('effective_at', '').strip()
                    if not effective_str:
                        continue

                    try:
                        effective_date = datetime.strptime(effective_str, '%Y-%m-%d %H:%M:%S').date()
                    except ValueError:
                        try:
                            effective_date = datetime.strptime(effective_str, '%Y-%m-%d').date()
                        except ValueError:
                            continue

                    # Check if within date range
                    if effective_date < start_date or effective_date > end_date:
                        continue

                    gross = self._parse_decimal(row.get('gross', '0'))
                    fee = self._parse_decimal(row.get('fee', '0'))

                    total_gross += gross
                    total_fee += fee
                    count += 1

            return {
                'gross': float(total_gross),
                'fee': float(total_fee),
                'count': count
            }

        except Exception as e:
            self.logger.error(f"Error parsing Stripe Itemised Payouts: {e}")
            return {'gross': 0, 'fee': 0, 'count': 0}

    def _read_stripe_balance_summary(self, year, month, company_filter):
        """Read Balance Summary from Stripe's exported CSV file if available"""
        # Look for files like: cgge_Balance_Summary_HKD_2025-11-01_to_2025-11-29_UTC.csv
        pattern = f"{company_filter}_Balance_Summary_*.csv"
        search_path = os.path.join(self.root_directory, pattern)
        files = glob.glob(search_path)

        if not files:
            return None

        # Find file matching the year/month
        for file_path in files:
            filename = os.path.basename(file_path)
            # Extract date from filename
            if f"{year}-{month:02d}" in filename:
                return self._parse_stripe_balance_summary(file_path)

        return None

    def _parse_stripe_balance_summary(self, file_path):
        """Parse Stripe's Balance Summary CSV format"""
        try:
            data = {}
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    category = row.get('category', '').strip()
                    description = row.get('description', '').strip()
                    net_amount = self._parse_decimal(row.get('net_amount', '0'))
                    currency = row.get('currency', 'hkd').strip().lower()

                    if category == 'starting_balance':
                        data['starting_balance'] = float(net_amount)
                    elif category == 'activity_gross':
                        data['activity_gross'] = float(net_amount)
                    elif category == 'activity_fee':
                        data['activity_fee'] = float(net_amount)
                    elif category == 'activity':
                        data['activity_net'] = float(net_amount)
                    elif category == 'payouts_gross':
                        data['payouts_gross'] = float(net_amount)
                    elif category == 'payouts_fee':
                        data['payouts_fee'] = float(net_amount)
                    elif category == 'payouts':
                        data['payouts_net'] = float(net_amount)
                    elif category == 'ending_balance':
                        data['ending_balance'] = float(net_amount)

                    data['currency'] = currency

            # Extract date range from filename
            filename = os.path.basename(file_path)
            # Pattern: cgge_Balance_Summary_HKD_2025-11-01_to_2025-11-29_UTC.csv
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})', filename)
            if date_match:
                data['start_date'] = date_match.group(1)
                data['end_date'] = date_match.group(2)

            return {
                'period': {
                    'start_date': data.get('start_date', ''),
                    'end_date': data.get('end_date', ''),
                },
                'currency': data.get('currency', 'hkd'),
                'starting_balance': data.get('starting_balance', 0),
                'activity': {
                    'gross': data.get('activity_gross', 0),
                    'fee': data.get('activity_fee', 0),
                    'net': data.get('activity_net', 0)
                },
                'payouts': {
                    'gross': data.get('payouts_gross', 0),
                    'fee': data.get('payouts_fee', 0),
                    'net': data.get('payouts_net', 0)
                },
                'ending_balance': data.get('ending_balance', 0),
                'source': 'stripe_report',
                'file': os.path.basename(file_path)
            }

        except Exception as e:
            self.logger.error(f"Error parsing Stripe Balance Summary: {e}")
            return None

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
            opening_balance = statement_data['opening_balance']
            opening_debit = f"{abs(opening_balance):.2f}" if opening_balance < 0 else ""
            opening_credit = f"{abs(opening_balance):.2f}" if opening_balance >= 0 else ""
            
            writer.writerow([
                f"{statement_data['year']}-{statement_data['month']:02d}-01",
                "Opening Balance",
                "Brought Forward",
                opening_debit,
                opening_credit,
                f"{opening_balance:.2f}",
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
            closing_balance = statement_data['closing_balance']
            closing_debit = f"{abs(closing_balance):.2f}" if closing_balance < 0 else ""
            closing_credit = f"{abs(closing_balance):.2f}" if closing_balance >= 0 else ""
            
            writer.writerow([
                f"{statement_data['year']}-{statement_data['month']:02d}-{self._get_last_day_of_month(statement_data['year'], statement_data['month']):02d}",
                "Closing Balance",
                "Carry Forward",
                closing_debit,
                closing_credit,
                f"{closing_balance:.2f}",
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

        for file_info in csv_files:
            # Handle both 2-tuple and 3-tuple formats
            if len(file_info) >= 2:
                company_code = file_info[1]
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