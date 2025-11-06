import re
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from .complete_csv_service import CompleteCsvService


class CustomerSubscriptionService:
    """Service for analyzing customer subscription patterns and behaviors"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.csv_service = CompleteCsvService()
        
        # Subscription plan mappings
        self.plan_names = {
            'M1': 'Monthly Plan (1 month)',
            'M3': 'Quarterly Plan (3 months)', 
            'SY1': 'Semi-Annual Plan (6 months)',
            'RECHARGE': 'Account Recharge',
            'INTELLIGENCE': 'Intelligence Service',
            '30': '30-Day Plan',
            '90': '90-Day Plan',
            '180': '180-Day Plan',
            '365': 'Annual Plan (365 days)',
            'test': 'Test Plan'
        }
    
    def get_customer_analytics(self, company_filter: Optional[str] = None) -> Dict:
        """Get comprehensive customer subscription analytics"""
        all_transactions = self.csv_service.import_transactions_from_csv()
        
        # Filter by company if specified
        if company_filter:
            all_transactions = [tx for tx in all_transactions if tx['company_code'] == company_filter]
        
        customer_data = self._process_customer_data(all_transactions)
        
        return {
            'customers': self._format_customer_list(customer_data),
            'summary': self._generate_summary_stats(customer_data),
            'plan_analytics': self._analyze_subscription_plans(customer_data),
            'company_breakdown': self._analyze_by_company(customer_data),
            'revenue_trends': self._analyze_revenue_trends(all_transactions)
        }
    
    def _process_customer_data(self, transactions: List[Dict]) -> Dict:
        """Process transactions to extract customer subscription data"""
        customer_data = defaultdict(lambda: {
            'customer_id': '',
            'email': '',
            'user_id': '',
            'transactions': [],
            'total_spent': Decimal('0'),
            'net_spent': Decimal('0'),  # After refunds
            'subscription_plans': set(),
            'plan_days': set(),
            'companies': set(),
            'first_purchase': None,
            'last_purchase': None,
            'purchase_count': 0,
            'refund_count': 0,
            'total_refunded': Decimal('0')
        })
        
        for tx in transactions:
            # Only process actual customer transactions (charges and refunds)
            if tx['type'] not in ['charge', 'payment', 'refund']:
                continue
                
            raw_row = tx.get('raw_row', {})
            description = tx.get('description', '')
            
            # Extract customer identifier
            customer_key, customer_email, user_id = self._extract_customer_info(tx, raw_row, description)
            
            if not customer_key or customer_key in ['Stripe', 'Unknown']:
                continue
                
            # Update customer data
            customer = customer_data[customer_key]
            customer['customer_id'] = customer_key
            customer['email'] = customer_email or customer.get('email', '')
            customer['user_id'] = user_id or customer.get('user_id', '')
            customer['transactions'].append(tx)
            customer['companies'].add(tx['account_name'])
            
            # Process subscription metadata
            plan = raw_row.get('stripe_plan (metadata)', '').strip()
            plan_days = raw_row.get('plan_days (metadata)', '').strip()
            
            if plan:
                customer['subscription_plans'].add(plan)
            if plan_days:
                customer['plan_days'].add(plan_days)
            
            # Calculate financials
            amount = Decimal(str(tx.get('net_amount', 0)))
            
            if tx['type'] == 'refund':
                customer['refund_count'] += 1
                customer['total_refunded'] += abs(amount)
                customer['net_spent'] -= abs(amount)
            else:
                customer['purchase_count'] += 1
                customer['total_spent'] += amount
                customer['net_spent'] += amount
            
            # Track purchase timeline
            tx_date = tx.get('date')
            if tx_date:
                if not customer['first_purchase'] or tx_date < customer['first_purchase']:
                    customer['first_purchase'] = tx_date
                if not customer['last_purchase'] or tx_date > customer['last_purchase']:
                    customer['last_purchase'] = tx_date
        
        return customer_data
    
    def _extract_customer_info(self, tx: Dict, raw_row: Dict, description: str) -> Tuple[str, str, str]:
        """Extract customer identifier, email, and user ID from transaction"""
        customer_key = None
        email = None
        user_id = None
        
        # Priority 1: Email from description
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', description)
        if email_match:
            email = email_match.group()
            customer_key = email
        
        # Priority 2: User ID from metadata
        elif raw_row.get('stripe_user (metadata)'):
            user_id = raw_row.get('stripe_user (metadata)')
            customer_key = f'User-{user_id}'
        elif raw_row.get('userID (metadata)'):
            user_id = raw_row.get('userID (metadata)')
            customer_key = f'User-{user_id}'
        
        # Priority 3: Extract from party field
        elif tx.get('party') and tx.get('party') not in ['Stripe', 'N/A']:
            party = tx.get('party', '').strip()
            # Check if party contains email
            email_in_party = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', party)
            if email_in_party:
                email = email_in_party.group()
                customer_key = email
            elif party and len(party) > 2:
                customer_key = party
        
        return customer_key, email, user_id
    
    def _format_customer_list(self, customer_data: Dict) -> List[Dict]:
        """Format customer data for frontend display"""
        customers = []
        
        for customer_key, data in customer_data.items():
            # Calculate customer lifetime value and metrics
            lifetime_value = float(data['net_spent'])
            avg_order_value = float(data['total_spent'] / data['purchase_count']) if data['purchase_count'] > 0 else 0
            
            # Determine customer status
            days_since_last = None
            status = 'Active'
            if data['last_purchase']:
                days_since_last = (datetime.now().date() - data['last_purchase']).days
                if days_since_last > 90:
                    status = 'Inactive'
                elif days_since_last > 30:
                    status = 'At Risk'
            
            customers.append({
                'customer_id': data['customer_id'],
                'email': data['email'],
                'user_id': data['user_id'],
                'total_spent': float(data['total_spent']),
                'net_spent': lifetime_value,
                'total_refunded': float(data['total_refunded']),
                'purchase_count': data['purchase_count'],
                'refund_count': data['refund_count'],
                'avg_order_value': avg_order_value,
                'subscription_plans': list(data['subscription_plans']),
                'subscription_plans_display': [self.plan_names.get(p, p) for p in data['subscription_plans']],
                'plan_days': sorted(list(data['plan_days'])),
                'companies': list(data['companies']),
                'first_purchase': data['first_purchase'].isoformat() if data['first_purchase'] else None,
                'last_purchase': data['last_purchase'].isoformat() if data['last_purchase'] else None,
                'days_since_last_purchase': days_since_last,
                'status': status,
                'transaction_count': len(data['transactions'])
            })
        
        # Sort by lifetime value descending
        customers.sort(key=lambda x: x['net_spent'], reverse=True)
        return customers
    
    def _generate_summary_stats(self, customer_data: Dict) -> Dict:
        """Generate summary statistics"""
        if not customer_data:
            return {
                'total_customers': 0,
                'total_revenue': 0,
                'total_refunded': 0,
                'avg_customer_value': 0,
                'active_customers': 0,
                'subscription_customers': 0
            }
        
        total_revenue = sum(float(data['total_spent']) for data in customer_data.values())
        total_refunded = sum(float(data['total_refunded']) for data in customer_data.values())
        subscription_customers = sum(1 for data in customer_data.values() if data['subscription_plans'])
        
        # Count active customers (purchased in last 90 days)
        active_count = 0
        for data in customer_data.values():
            if data['last_purchase']:
                days_since = (datetime.now().date() - data['last_purchase']).days
                if days_since <= 90:
                    active_count += 1
        
        return {
            'total_customers': len(customer_data),
            'total_revenue': total_revenue,
            'total_refunded': total_refunded,
            'net_revenue': total_revenue - total_refunded,
            'avg_customer_value': total_revenue / len(customer_data),
            'active_customers': active_count,
            'subscription_customers': subscription_customers,
            'subscription_rate': (subscription_customers / len(customer_data)) * 100
        }
    
    def _analyze_subscription_plans(self, customer_data: Dict) -> Dict:
        """Analyze subscription plan popularity and revenue"""
        plan_stats = defaultdict(lambda: {
            'customers': 0,
            'revenue': Decimal('0'),
            'transactions': 0,
            'avg_value': Decimal('0')
        })
        
        for data in customer_data.values():
            for plan in data['subscription_plans']:
                plan_stats[plan]['customers'] += 1
                
                # Calculate revenue for this plan
                plan_revenue = sum(
                    Decimal(str(tx.get('net_amount', 0)))
                    for tx in data['transactions']
                    if tx['type'] in ['charge', 'payment'] and 
                       tx.get('raw_row', {}).get('stripe_plan (metadata)', '') == plan
                )
                plan_stats[plan]['revenue'] += plan_revenue
                
                # Count transactions for this plan
                plan_txs = sum(
                    1 for tx in data['transactions']
                    if tx.get('raw_row', {}).get('stripe_plan (metadata)', '') == plan
                )
                plan_stats[plan]['transactions'] += plan_txs
        
        # Calculate averages and format for display
        formatted_plans = []
        for plan, stats in plan_stats.items():
            avg_value = float(stats['revenue'] / stats['customers']) if stats['customers'] > 0 else 0
            
            formatted_plans.append({
                'plan_code': plan,
                'plan_name': self.plan_names.get(plan, plan),
                'customers': stats['customers'],
                'revenue': float(stats['revenue']),
                'transactions': stats['transactions'],
                'avg_customer_value': avg_value,
                'market_share': 0  # Will be calculated after sorting
            })
        
        # Sort by revenue and calculate market share
        formatted_plans.sort(key=lambda x: x['revenue'], reverse=True)
        total_plan_revenue = sum(p['revenue'] for p in formatted_plans)
        
        for plan in formatted_plans:
            plan['market_share'] = (plan['revenue'] / total_plan_revenue * 100) if total_plan_revenue > 0 else 0
        
        return formatted_plans
    
    def _analyze_by_company(self, customer_data: Dict) -> Dict:
        """Analyze customer distribution by company"""
        company_stats = defaultdict(lambda: {
            'customers': set(),
            'revenue': Decimal('0'),
            'transactions': 0
        })
        
        for data in customer_data.values():
            for company in data['companies']:
                company_stats[company]['customers'].add(data['customer_id'])
                company_stats[company]['revenue'] += data['net_spent']
                company_stats[company]['transactions'] += len(data['transactions'])
        
        # Format for display
        companies = []
        for company, stats in company_stats.items():
            companies.append({
                'company': company,
                'customers': len(stats['customers']),
                'revenue': float(stats['revenue']),
                'transactions': stats['transactions'],
                'avg_revenue_per_customer': float(stats['revenue'] / len(stats['customers'])) if stats['customers'] else 0
            })
        
        companies.sort(key=lambda x: x['revenue'], reverse=True)
        return companies
    
    def _analyze_revenue_trends(self, transactions: List[Dict]) -> Dict:
        """Analyze revenue trends over time"""
        monthly_data = defaultdict(lambda: {
            'revenue': Decimal('0'),
            'customers': set(),
            'transactions': 0,
            'new_customers': set()
        })
        
        all_customers = set()
        
        for tx in transactions:
            if tx['type'] not in ['charge', 'payment']:
                continue
                
            tx_date = tx.get('date')
            if not tx_date:
                continue
                
            month_key = tx_date.strftime('%Y-%m')
            customer_key, _, _ = self._extract_customer_info(tx, tx.get('raw_row', {}), tx.get('description', ''))
            
            if customer_key and customer_key not in ['Stripe', 'Unknown']:
                monthly_data[month_key]['revenue'] += Decimal(str(tx.get('net_amount', 0)))
                monthly_data[month_key]['customers'].add(customer_key)
                monthly_data[month_key]['transactions'] += 1
                
                # Track new customers
                if customer_key not in all_customers:
                    monthly_data[month_key]['new_customers'].add(customer_key)
                    all_customers.add(customer_key)
        
        # Format for charting
        trends = []
        for month_key in sorted(monthly_data.keys()):
            data = monthly_data[month_key]
            trends.append({
                'month': month_key,
                'revenue': float(data['revenue']),
                'customers': len(data['customers']),
                'new_customers': len(data['new_customers']),
                'transactions': data['transactions'],
                'avg_transaction_value': float(data['revenue'] / data['transactions']) if data['transactions'] > 0 else 0
            })
        
        return trends
    
    def get_customer_details(self, customer_id: str) -> Optional[Dict]:
        """Get detailed information for a specific customer"""
        all_transactions = self.csv_service.import_transactions_from_csv()
        customer_data = self._process_customer_data(all_transactions)
        
        if customer_id not in customer_data:
            return None
        
        data = customer_data[customer_id]
        
        # Sort transactions by date
        sorted_transactions = sorted(
            data['transactions'], 
            key=lambda x: x.get('date') or datetime.min.date(),
            reverse=True
        )
        
        # Format transactions for display
        transaction_history = []
        for tx in sorted_transactions:
            raw_row = tx.get('raw_row', {})
            transaction_history.append({
                'date': tx.get('date').isoformat() if tx.get('date') else None,
                'type': tx['type'],
                'description': tx['description'],
                'amount': tx['amount'],
                'net_amount': tx['net_amount'],
                'currency': tx['currency'],
                'status': tx['status'],
                'company': tx['account_name'],
                'plan': raw_row.get('stripe_plan (metadata)', ''),
                'plan_days': raw_row.get('plan_days (metadata)', ''),
                'stripe_id': tx.get('stripe_id', '')
            })
        
        return {
            'customer_id': data['customer_id'],
            'email': data['email'],
            'user_id': data['user_id'],
            'total_spent': float(data['total_spent']),
            'net_spent': float(data['net_spent']),
            'total_refunded': float(data['total_refunded']),
            'purchase_count': data['purchase_count'],
            'refund_count': data['refund_count'],
            'subscription_plans': list(data['subscription_plans']),
            'plan_days': list(data['plan_days']),
            'companies': list(data['companies']),
            'first_purchase': data['first_purchase'].isoformat() if data['first_purchase'] else None,
            'last_purchase': data['last_purchase'].isoformat() if data['last_purchase'] else None,
            'transaction_history': transaction_history
        }
    
    def export_customer_data_csv(self, company_filter: Optional[str] = None) -> str:
        """Export customer data to CSV format"""
        analytics = self.get_customer_analytics(company_filter)
        customers = analytics['customers']
        
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Customer ID', 'Email', 'User ID', 'Total Spent (HKD)', 'Net Spent (HKD)',
            'Total Refunded (HKD)', 'Purchase Count', 'Refund Count', 'Avg Order Value (HKD)',
            'Subscription Plans', 'Plan Days', 'Companies', 'First Purchase', 'Last Purchase',
            'Days Since Last Purchase', 'Status', 'Transaction Count'
        ])
        
        # Write customer data
        for customer in customers:
            writer.writerow([
                customer['customer_id'],
                customer['email'],
                customer['user_id'],
                f"{customer['total_spent']:.2f}",
                f"{customer['net_spent']:.2f}",
                f"{customer['total_refunded']:.2f}",
                customer['purchase_count'],
                customer['refund_count'],
                f"{customer['avg_order_value']:.2f}",
                ', '.join(customer['subscription_plans_display']),
                ', '.join(customer['plan_days']),
                ', '.join(customer['companies']),
                customer['first_purchase'],
                customer['last_purchase'],
                customer['days_since_last_purchase'],
                customer['status'],
                customer['transaction_count']
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return csv_content