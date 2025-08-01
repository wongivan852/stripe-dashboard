#!/usr/bin/env python3
"""
Analyze CSV data vs Stripe report discrepancies
"""

import csv
import os
from datetime import datetime

def analyze_csv_vs_stripe_report():
    """Analyze the CGGE CSV data vs Stripe report"""
    
    csv_file = '/Users/wongivan/stripe-dashboard/july25/cgge_unified_payments_20250731.csv'
    
    print("🔍 Analyzing CGGE CSV vs Stripe Report...")
    print("=" * 60)
    
    # Stripe report data
    stripe_count = 20
    stripe_gross = 2456.14  # HKD
    stripe_fees = 96.01     # HKD
    
    # Analyze CSV data
    july_transactions = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            created_date = row.get('Created date (UTC)', '').strip()
            
            # Only July 2025 transactions
            if created_date.startswith('2025-07'):
                july_transactions.append(row)
    
    print(f"📊 CSV Data Analysis:")
    print(f"Total July entries in CSV: {len(july_transactions)}")
    
    # Analyze by status
    successful = []
    failed = []
    canceled = []
    
    for tx in july_transactions:
        status = tx.get('Status', '').lower()
        if status in ['paid', 'succeeded']:
            successful.append(tx)
        elif status == 'failed':
            failed.append(tx)
        elif status == 'canceled':
            canceled.append(tx)
    
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"🚫 Canceled: {len(canceled)}")
    
    # Calculate totals for successful transactions only
    total_converted_amount = 0
    total_original_amount = 0
    total_fees = 0
    
    currency_breakdown = {}
    
    for tx in successful:
        # Original amount and currency
        amount = float(tx.get('Amount', 0))
        currency = tx.get('Currency', '').upper()
        
        # Converted amount (should be in HKD)
        converted_amount = float(tx.get('Converted Amount', 0))
        converted_currency = tx.get('Converted Currency', '').upper()
        
        # Fee
        fee = float(tx.get('Fee', 0))
        
        total_converted_amount += converted_amount
        total_original_amount += amount
        total_fees += fee
        
        # Track currencies
        if currency not in currency_breakdown:
            currency_breakdown[currency] = {'count': 0, 'total': 0}
        currency_breakdown[currency]['count'] += 1
        currency_breakdown[currency]['total'] += amount
        
        print(f"  {tx.get('id', 'N/A')[:20]}: {amount} {currency} → {converted_amount} {converted_currency} (fee: {fee})")
    
    print(f"\n💰 CSV Successful Transactions Analysis:")
    print(f"Count: {len(successful)}")
    print(f"Total Original Amount: {total_original_amount:.2f}")
    print(f"Total Converted Amount (HKD): {total_converted_amount:.2f}")
    print(f"Total Fees: {total_fees:.2f}")
    
    print(f"\n🌍 Currency Breakdown:")
    for curr, data in currency_breakdown.items():
        print(f"  {curr}: {data['count']} transactions, {data['total']:.2f} total")
    
    print(f"\n📋 Stripe Report:")
    print(f"Count: {stripe_count}")
    print(f"Gross Amount: HK${stripe_gross:.2f}")
    print(f"Fees: HK${stripe_fees:.2f}")
    
    print(f"\n🔍 Discrepancy Analysis:")
    count_diff = len(successful) - stripe_count
    amount_diff = total_converted_amount - stripe_gross
    fee_diff = total_fees - stripe_fees
    
    print(f"Count difference: {count_diff:+d}")
    print(f"Amount difference: HK${amount_diff:+.2f}")
    print(f"Fee difference: HK${fee_diff:+.2f}")
    
    # Check for potential issues
    if count_diff != 0:
        print(f"\n⚠️  Count Mismatch Issues:")
        print(f"  - CSV has {len(successful)} successful transactions")
        print(f"  - Stripe report shows {stripe_count} transactions")
        print(f"  - Difference suggests {abs(count_diff)} transaction(s) discrepancy")
    
    if abs(amount_diff) > 0.01:
        print(f"\n⚠️  Amount Mismatch Issues:")
        print(f"  - Could be related to currency conversion timing")
        print(f"  - Check if using correct amount field (Amount vs Converted Amount)")
        print(f"  - Verify date range alignment")
    
    # Detailed transaction list for manual verification
    print(f"\n📝 Detailed Successful Transaction List:")
    print("ID | Date | Original | Converted | Fee | Status")
    print("-" * 70)
    
    for tx in successful:
        tx_id = tx.get('id', 'N/A')[:20]
        date = tx.get('Created date (UTC)', '')[:16]
        orig_amt = f"{tx.get('Amount', 0)} {tx.get('Currency', '')}"
        conv_amt = f"{tx.get('Converted Amount', 0)} {tx.get('Converted Currency', '')}"
        fee = tx.get('Fee', 0)
        status = tx.get('Status', '')
        
        print(f"{tx_id} | {date} | {orig_amt:>10} | {conv_amt:>10} | {fee:>6} | {status}")

if __name__ == '__main__':
    analyze_csv_vs_stripe_report()
