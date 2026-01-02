"""
Unified Payment Service - Combines Stripe and WeChat Pay data with fee categorization.

This service reads payment data from:
1. Stripe CSV files (stripe_cgge_payments.csv, stripe_ki_payments.csv, stripe_kt_payments.csv)
2. WeChat Pay CSV files (Chinese format with transaction details)

All fees are partitioned into:
- Conference: Event tickets (BCONSZ25, IAICC, Origin CG Ticketing, etc.)
- Subscription: Recurring subscriptions (Blender Studio, VIP Member, M1, M3, Y1, etc.)
"""

import os
import csv
import glob
import json
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class UnifiedPaymentService:
    """Service to process both Stripe and WeChat Pay data with fee categorization"""

    # Conference-related keywords (case-insensitive)
    CONFERENCE_KEYWORDS = [
        'bconsz', 'iaicc', 'conference', 'summit', 'event', 'ticket',
        'ticketing', '全票', '一日票', '门票', '門票', 'day pass',
        'full ticket', 'one day', 'origin cg ticketing'
    ]

    # Subscription-related keywords (case-insensitive)
    SUBSCRIPTION_KEYWORDS = [
        'subscription', 'member', 'vip', 'blender studio', 'premium',
        '会员', '會員', '一年', '订阅', '訂閱', 'monthly', 'yearly',
        'm1', 'm3', 'm6', 'y1', 'sy1', 'intelligence', 'krystal_pass',
        'recharge'
    ]

    def __init__(self, data_directory=None):
        self.logger = logging.getLogger(__name__)

        if data_directory is None:
            data_directory = self._resolve_data_directory()

        self.data_directory = data_directory
        self.company_names = {
            "cgge": "CGGE",
            "ki": "Krystal Institute",
            "kt": "Krystal Technology",
            "wechat": "WeChat Pay (CGGE)"
        }

        self._validate_data_directory()

    def _resolve_data_directory(self) -> str:
        """Resolve data directory path for different deployment environments"""
        possible_paths = [
            os.environ.get('DATA_PATH'),
            os.path.join(os.getcwd(), 'data'),
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data'),
            '/app/data',
            '/home/user/stripe-dashboard/data'
        ]

        for path in possible_paths:
            if path and os.path.exists(path):
                self.logger.info(f"Found data directory: {path}")
                return path

        fallback_path = os.path.join(os.getcwd(), 'data')
        self.logger.warning(f"No data directory found, using fallback: {fallback_path}")
        return fallback_path

    def _validate_data_directory(self):
        """Validate data directory exists"""
        if not os.path.exists(self.data_directory):
            self.logger.error(f"Data directory does not exist: {self.data_directory}")

    def _find_csv_files(self) -> List[Tuple[str, str, str]]:
        """Find all CSV files in data directory
        Returns list of tuples: (file_path, source_type, company_code)
        """
        csv_files = []

        try:
            # Find Stripe CSV files
            stripe_patterns = [
                ('stripe_cgge_*.csv', 'stripe', 'cgge'),
                ('stripe_ki_*.csv', 'stripe', 'ki'),
                ('stripe_kt_*.csv', 'stripe', 'kt'),
            ]

            for pattern, source_type, company_code in stripe_patterns:
                pattern_path = os.path.join(self.data_directory, pattern)
                files = glob.glob(pattern_path)
                for file_path in files:
                    csv_files.append((file_path, source_type, company_code))
                    self.logger.info(f"Found Stripe file: {os.path.basename(file_path)}")

            # Find WeChat CSV files (format: merchantid_x_x_All_date_date.csv)
            wechat_patterns = [
                '*_*_*_All_*.csv',  # WeChat export format
                '*TRADE_DATA*.csv',  # Alternative format
            ]

            for pattern in wechat_patterns:
                pattern_path = os.path.join(self.data_directory, pattern)
                files = glob.glob(pattern_path)
                for file_path in files:
                    # Skip stripe files
                    if 'stripe_' in os.path.basename(file_path).lower():
                        continue
                    csv_files.append((file_path, 'wechat', 'wechat'))
                    self.logger.info(f"Found WeChat file: {os.path.basename(file_path)}")

            self.logger.info(f"Found {len(csv_files)} CSV files total")
            return csv_files

        except Exception as e:
            self.logger.error(f"Error finding CSV files: {e}")
            return []

    def get_all_transactions(self, company_filter=None, status_filter=None,
                            from_date=None, to_date=None, fee_category=None) -> List[Dict]:
        """Get all transactions from both Stripe and WeChat Pay with optional filtering"""
        all_transactions = []
        csv_files = self._find_csv_files()

        if not csv_files:
            self.logger.warning("No CSV files found to import")
            return []

        for file_path, source_type, company_code in csv_files:
            try:
                if source_type == 'stripe':
                    transactions = self._read_stripe_csv(file_path, company_code)
                elif source_type == 'wechat':
                    transactions = self._read_wechat_csv(file_path)
                else:
                    continue

                all_transactions.extend(transactions)
                self.logger.info(f"Loaded {len(transactions)} transactions from {os.path.basename(file_path)}")

            except Exception as e:
                self.logger.error(f"Error reading {file_path}: {e}")
                continue

        # Apply filters
        filtered = self._apply_filters(
            all_transactions,
            company_filter=company_filter,
            status_filter=status_filter,
            from_date=from_date,
            to_date=to_date,
            fee_category=fee_category
        )

        # Sort by date (newest first)
        filtered.sort(key=lambda x: x.get('created') or datetime.min, reverse=True)

        self.logger.info(f"Total transactions after filtering: {len(filtered)}")
        return filtered

    def _read_stripe_csv(self, file_path: str, company_code: str) -> List[Dict]:
        """Read and parse Stripe CSV file"""
        transactions = []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    try:
                        parsed = self._parse_stripe_row(row, company_code)
                        if parsed:
                            transactions.append(parsed)
                    except Exception as e:
                        self.logger.warning(f"Error parsing Stripe row: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error reading Stripe CSV {file_path}: {e}")

        return transactions

    def _parse_stripe_row(self, row: Dict, company_code: str) -> Optional[Dict]:
        """Parse a Stripe CSV row into standardized transaction format"""
        # Must have an ID and be Paid status (only count successful payments)
        tx_id = row.get('id', '').strip()
        status_raw = row.get('Status', '').strip().lower()

        # Skip incomplete or non-successful records for fee calculation
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

        # Parse amounts - prefer HKD converted amounts
        converted_currency = row.get('Converted Currency', '').strip().lower()
        if converted_currency == 'hkd':
            amount = self._parse_decimal(row.get('Converted Amount', '0'))
        else:
            amount = self._parse_decimal(row.get('Amount', '0'))

        fee = self._parse_decimal(row.get('Fee', '0'))
        net = amount - fee

        # Get customer email
        customer_email = row.get('Customer Email', '').strip() or 'N/A'

        # Build description from metadata
        description = self._build_stripe_description(row)

        # Determine fee category
        fee_category = self._categorize_fee(row, description)

        # Map status
        status = self._map_stripe_status(status_raw)

        return {
            'id': tx_id,
            'stripe_id': tx_id,
            'source': 'stripe',
            'date': created.date(),
            'amount': float(amount),
            'fee': float(fee),
            'net_amount': float(net),
            'currency': 'HKD',
            'original_currency': row.get('Currency', 'hkd').upper(),
            'status': status,
            'type': 'payment',
            'description': description,
            'customer_email': customer_email,
            'created': created,
            'account_name': self.company_names.get(company_code, 'Unknown'),
            'company_code': company_code,
            'fee_category': fee_category,
            'raw_metadata': {
                'product_name': row.get('4. Product name (metadata)', ''),
                'site': row.get('1. Site (metadata)', '') or row.get('site (metadata)', ''),
                'stripe_plan': row.get('stripe_plan (metadata)', ''),
                'subs_type': row.get('subs_type (metadata)', ''),
                'type': row.get('type (metadata)', ''),
            }
        }

    def _build_stripe_description(self, row: Dict) -> str:
        """Build description from Stripe metadata fields"""
        parts = []

        # Product name
        product = row.get('4. Product name (metadata)', '').strip()
        if product:
            parts.append(product)

        # Site
        site = row.get('1. Site (metadata)', '').strip() or row.get('site (metadata)', '').strip()
        if site and site not in parts:
            parts.append(site)

        # Subscription type
        subs_type = row.get('subs_type (metadata)', '').strip()
        if subs_type:
            parts.append(f"Plan: {subs_type}")

        # Stripe plan
        stripe_plan = row.get('stripe_plan (metadata)', '').strip()
        if stripe_plan and stripe_plan not in str(parts):
            parts.append(f"({stripe_plan})")

        if parts:
            return ' - '.join(parts)

        # Fallback to Description column
        return row.get('Description', '').strip() or 'Payment'

    def _read_wechat_csv(self, file_path: str) -> List[Dict]:
        """Read and parse WeChat Pay CSV file (Chinese format with backticks)"""
        transactions = []

        try:
            # Read file content and try different encodings
            with open(file_path, 'rb') as f:
                content = f.read()

            decoded_content = None
            for encoding in ['utf-8-sig', 'utf-8', 'gb2312', 'gbk', 'gb18030']:
                try:
                    decoded_content = content.decode(encoding)
                    self.logger.info(f"WeChat file decoded with {encoding}")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue

            if not decoded_content:
                self.logger.error(f"Could not decode WeChat file {file_path}")
                return []

            # Parse CSV content
            lines = decoded_content.strip().split('\n')
            if len(lines) < 2:
                return []

            # Parse header (first line) - remove BOM and backticks
            header_line = lines[0].replace('\ufeff', '').strip()
            headers = [h.strip('`').strip() for h in header_line.split(',')]

            # Find important column indices
            header_map = {h: i for i, h in enumerate(headers)}

            # Parse data rows (skip last summary rows)
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue

                # Skip summary rows (start with Chinese characters for "总")
                if line.startswith('`总') or line.startswith('总'):
                    continue

                # Parse row values - handle backtick-prefixed values
                values = [v.strip('`').strip() for v in line.split(',')]

                try:
                    parsed = self._parse_wechat_row(values, header_map)
                    if parsed:
                        transactions.append(parsed)
                except Exception as e:
                    self.logger.warning(f"Error parsing WeChat row: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error reading WeChat CSV {file_path}: {e}")

        return transactions

    def _parse_wechat_row(self, values: List[str], header_map: Dict[str, int]) -> Optional[Dict]:
        """Parse a WeChat CSV row into standardized transaction format"""

        def get_value(key: str, default: str = '') -> str:
            idx = header_map.get(key, -1)
            if idx >= 0 and idx < len(values):
                return values[idx].strip()
            return default

        # Get transaction time
        tx_time_str = get_value('交易时间')
        if not tx_time_str:
            return None

        try:
            created = datetime.strptime(tx_time_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None

        # Get transaction status
        status_raw = get_value('交易状态').upper()
        if status_raw != 'SUCCESS':
            status = 'failed' if status_raw == 'FAIL' else 'canceled'
        else:
            status = 'succeeded'

        # Get amounts (in CNY)
        amount_str = get_value('应结订单金额', '0')
        fee_str = get_value('手续费', '0')

        try:
            amount = float(amount_str)
            fee = float(fee_str)
        except ValueError:
            amount = 0.0
            fee = 0.0

        if amount <= 0:
            return None

        net = amount - fee

        # Get product name and merchant data
        product_name = get_value('商品名称')
        merchant_data_str = get_value('商户数据包')

        # Parse merchant data JSON for type info
        merchant_data = {}
        if merchant_data_str:
            try:
                # Fix escaped backslashes and malformed JSON from WeChat
                cleaned = merchant_data_str.replace('\\', '')
                # Fix missing comma between fields (e.g., "\"type\": \"subscription\"  \"code\"")
                cleaned = re.sub(r'"\s+"', '", "', cleaned)
                merchant_data = json.loads(cleaned)
            except json.JSONDecodeError:
                # Try to extract type manually
                type_match = re.search(r'"type"\s*:\s*"([^"]+)"', merchant_data_str)
                if type_match:
                    merchant_data = {'type': type_match.group(1)}
                code_match = re.search(r'"code"\s*:\s*"([^"]+)"', merchant_data_str)
                if code_match:
                    merchant_data['code'] = code_match.group(1)

        # Build description
        description = product_name or 'WeChat Payment'

        # Determine fee category from product name and merchant data
        fee_category = self._categorize_wechat_fee(product_name, merchant_data)

        # Get order ID
        wechat_order_id = get_value('微信订单号')
        merchant_order_id = get_value('商户订单号')

        return {
            'id': wechat_order_id or merchant_order_id,
            'stripe_id': wechat_order_id,  # For compatibility
            'source': 'wechat',
            'date': created.date(),
            'amount': amount,
            'fee': fee,
            'net_amount': net,
            'currency': 'CNY',
            'original_currency': 'CNY',
            'status': status,
            'type': 'wechat_payment',
            'description': description,
            'customer_email': 'WeChat User',
            'created': created,
            'account_name': 'WeChat Pay (CGGE)',
            'company_code': 'wechat',
            'fee_category': fee_category,
            'raw_metadata': {
                'product_name': product_name,
                'merchant_data': merchant_data,
                'merchant_order_id': merchant_order_id,
            }
        }

    def _categorize_fee(self, row: Dict, description: str) -> str:
        """Categorize a Stripe transaction fee as Conference or Subscription"""
        # Check product name
        product_name = row.get('4. Product name (metadata)', '').lower()

        # Check site
        site = (row.get('1. Site (metadata)', '') or row.get('site (metadata)', '')).lower()

        # Check subscription type
        subs_type = row.get('subs_type (metadata)', '').lower()
        stripe_plan = row.get('stripe_plan (metadata)', '').lower()
        tx_type = row.get('type (metadata)', '').lower()

        # Combine all text for matching
        all_text = f"{product_name} {site} {subs_type} {stripe_plan} {tx_type} {description}".lower()

        # Check for conference keywords
        for keyword in self.CONFERENCE_KEYWORDS:
            if keyword in all_text:
                return 'Conference'

        # Check for subscription keywords
        for keyword in self.SUBSCRIPTION_KEYWORDS:
            if keyword in all_text:
                return 'Subscription'

        # Default based on presence of subscription-related metadata
        if stripe_plan or subs_type:
            return 'Subscription'

        # If has ticketing site, it's conference
        if 'ticketing' in site:
            return 'Conference'

        return 'Other'

    def _categorize_wechat_fee(self, product_name: str, merchant_data: Dict) -> str:
        """Categorize a WeChat transaction fee as Conference or Subscription"""
        product_lower = product_name.lower() if product_name else ''
        merchant_type = str(merchant_data.get('type', '')).lower()
        merchant_code = str(merchant_data.get('code', '')).lower()

        all_text = f"{product_lower} {merchant_type} {merchant_code}"

        # Check for conference keywords
        for keyword in self.CONFERENCE_KEYWORDS:
            if keyword in all_text:
                return 'Conference'

        # Check for subscription keywords
        for keyword in self.SUBSCRIPTION_KEYWORDS:
            if keyword in all_text:
                return 'Subscription'

        # Default based on merchant data type
        if merchant_type == 'subscription':
            return 'Subscription'

        return 'Other'

    def _map_stripe_status(self, status_raw: str) -> str:
        """Map Stripe status to standardized status"""
        status_map = {
            'paid': 'succeeded',
            'refunded': 'refunded',
            'failed': 'failed',
            'canceled': 'canceled',
            'requires_action': 'pending',
            'requires_payment_method': 'pending',
        }
        return status_map.get(status_raw, 'succeeded')

    def _parse_decimal(self, value: str) -> Decimal:
        """Safely parse a decimal value"""
        try:
            cleaned = str(value).strip().replace(',', '')
            if not cleaned:
                return Decimal('0')
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal('0')

    def _apply_filters(self, transactions: List[Dict], company_filter=None,
                      status_filter=None, from_date=None, to_date=None,
                      fee_category=None) -> List[Dict]:
        """Apply filters to transactions"""
        filtered = []

        # Parse date filters if strings
        if from_date and isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if to_date and isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()

        for tx in transactions:
            # Company filter
            if company_filter and company_filter != 'all':
                if tx['company_code'] != company_filter and tx['account_name'] != company_filter:
                    continue

            # Status filter
            if status_filter and status_filter != 'all':
                if tx['status'] != status_filter:
                    continue

            # Date range filter
            if tx.get('date'):
                if from_date and tx['date'] < from_date:
                    continue
                if to_date and tx['date'] > to_date:
                    continue

            # Fee category filter
            if fee_category and fee_category != 'all':
                if tx.get('fee_category') != fee_category:
                    continue

            filtered.append(tx)

        return filtered

    def get_fee_summary(self, transactions: List[Dict] = None,
                       from_date=None, to_date=None) -> Dict:
        """Get summary of fees partitioned by category"""
        if transactions is None:
            transactions = self.get_all_transactions(
                status_filter='succeeded',
                from_date=from_date,
                to_date=to_date
            )

        summary = {
            'total': {
                'count': 0,
                'amount': 0.0,
                'fee': 0.0,
                'net': 0.0,
            },
            'by_category': {
                'Conference': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                'Subscription': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                'Other': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
            },
            'by_source': {
                'stripe': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                'wechat': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
            },
            'by_company': {},
        }

        for tx in transactions:
            if tx['status'] != 'succeeded':
                continue

            amount = tx['amount']
            fee = tx['fee']
            net = tx['net_amount']
            category = tx.get('fee_category', 'Other')
            source = tx.get('source', 'stripe')
            company = tx.get('account_name', 'Unknown')

            # Total
            summary['total']['count'] += 1
            summary['total']['amount'] += amount
            summary['total']['fee'] += fee
            summary['total']['net'] += net

            # By category
            if category in summary['by_category']:
                summary['by_category'][category]['count'] += 1
                summary['by_category'][category]['amount'] += amount
                summary['by_category'][category]['fee'] += fee
                summary['by_category'][category]['net'] += net

            # By source
            if source in summary['by_source']:
                summary['by_source'][source]['count'] += 1
                summary['by_source'][source]['amount'] += amount
                summary['by_source'][source]['fee'] += fee
                summary['by_source'][source]['net'] += net

            # By company
            if company not in summary['by_company']:
                summary['by_company'][company] = {
                    'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0,
                    'by_category': {
                        'Conference': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                        'Subscription': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                        'Other': {'count': 0, 'amount': 0.0, 'fee': 0.0, 'net': 0.0},
                    }
                }
            summary['by_company'][company]['count'] += 1
            summary['by_company'][company]['amount'] += amount
            summary['by_company'][company]['fee'] += fee
            summary['by_company'][company]['net'] += net

            if category in summary['by_company'][company]['by_category']:
                summary['by_company'][company]['by_category'][category]['count'] += 1
                summary['by_company'][company]['by_category'][category]['amount'] += amount
                summary['by_company'][company]['by_category'][category]['fee'] += fee
                summary['by_company'][company]['by_category'][category]['net'] += net

        return summary

    def get_monthly_summary(self, year: int, month: int, company_filter=None) -> Dict:
        """Get monthly summary with fee breakdown"""
        from_date = datetime(year, month, 1).date()
        if month == 12:
            to_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
        else:
            to_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

        transactions = self.get_all_transactions(
            company_filter=company_filter,
            from_date=from_date,
            to_date=to_date
        )

        # Get fee summary
        fee_summary = self.get_fee_summary(transactions)

        # Month names
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December']

        return {
            'year': year,
            'month': month,
            'month_name': month_names[month],
            'from_date': str(from_date),
            'to_date': str(to_date),
            'transactions': transactions,
            'transaction_count': len(transactions),
            'fee_summary': fee_summary,
        }

    def get_available_companies(self) -> List[Dict]:
        """Get list of available companies/accounts"""
        return [
            {'code': 'cgge', 'name': 'CGGE'},
            {'code': 'ki', 'name': 'Krystal Institute'},
            {'code': 'kt', 'name': 'Krystal Technology'},
            {'code': 'wechat', 'name': 'WeChat Pay (CGGE)'},
        ]

    def get_health_status(self) -> Dict:
        """Get health status of the service"""
        try:
            csv_files = self._find_csv_files()
            transactions = self.get_all_transactions()

            return {
                'status': 'healthy',
                'data_directory': self.data_directory,
                'csv_files_found': len(csv_files),
                'total_transactions': len(transactions),
                'files': [os.path.basename(f[0]) for f in csv_files],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'data_directory': self.data_directory,
                'timestamp': datetime.now().isoformat()
            }
