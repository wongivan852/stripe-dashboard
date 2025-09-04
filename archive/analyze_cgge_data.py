#!/usr/bin/env python3
"""
CGGE Data Analysis Script
Analyze the actual CSV data to understand the discrepancy
"""

import csv
import sys
from datetime import datetime
from decimal import Decimal

def analyze_cgge_csv():
    csv_file = '/home/user/krystal-company-apps/stripe-dashboard/july25/cgge_unified_payments_20250731.csv'
    
    print("🔍 CGGE CSV DATA ANALYSIS")
    print("=" * 50)
    
    total_transactions = 0
    paid_transactions = 0
    failed_transactions = 0
    canceled_transactions = 0
    
    total_amount_hkd = Decimal('0.00')
    total_fees_hkd = Decimal('0.00')
    
    paid_details = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                total_transactions += 1
                status = row.get('Status', '').strip().lower()
                
                if status == 'paid':
                    paid_transactions += 1
                    
                    # Get converted amounts in HKD
                    converted_amount = row.get('Converted Amount', '0.00')
                    fee = row.get('Fee', '0.00')
                    
                    if converted_amount and converted_amount != '':
                        amount_hkd = Decimal(str(converted_amount))
                        total_amount_hkd += amount_hkd
                    
                    if fee and fee != '':
                        fee_hkd = Decimal(str(fee))
                        total_fees_hkd += fee_hkd
                    
                    # Store paid transaction details
                    paid_details.append({
                        'date': row.get('Created date (UTC)', ''),
                        'amount_hkd': converted_amount,
                        'fee_hkd': fee,
                        'customer': row.get('Customer Email', ''),
                        'status': status
                    })
                    
                elif status == 'failed':
                    failed_transactions += 1
                elif status == 'canceled':
                    canceled_transactions += 1
    
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    net_amount_hkd = total_amount_hkd - total_fees_hkd
    fee_rate = (total_fees_hkd / total_amount_hkd * 100) if total_amount_hkd > 0 else 0
    
    print(f"📊 TRANSACTION SUMMARY:")
    print(f"   Total entries in CSV: {total_transactions}")
    print(f"   Paid transactions: {paid_transactions}")
    print(f"   Failed transactions: {failed_transactions}")
    print(f"   Canceled transactions: {canceled_transactions}")
    print()
    
    print(f"💰 FINANCIAL SUMMARY (HKD):")
    print(f"   Gross Income: ${total_amount_hkd:.2f}")
    print(f"   Processing Fees: ${total_fees_hkd:.2f}")
    print(f"   Net Income: ${net_amount_hkd:.2f}")
    print(f"   Fee Rate: {fee_rate:.2f}%")
    print()
    
    print(f"🎯 YOUR REQUIREMENTS:")
    print(f"   Required Transactions: 20")
    print(f"   Required Gross: HK$2546.14")
    print(f"   Required Fees: HK$96.01")
    print(f"   Required Net: HK$2360.13")
    print(f"   Required Fee Rate: 3.91%")
    print()
    
    print(f"📋 COMPARISON:")
    print(f"   Transactions: {paid_transactions} vs 20 (difference: {paid_transactions - 20})")
    print(f"   Gross: ${total_amount_hkd:.2f} vs $2546.14 (difference: ${total_amount_hkd - Decimal('2546.14'):.2f})")
    print(f"   Fees: ${total_fees_hkd:.2f} vs $96.01 (difference: ${total_fees_hkd - Decimal('96.01'):.2f})")
    print(f"   Net: ${net_amount_hkd:.2f} vs $2360.13 (difference: ${net_amount_hkd - Decimal('2360.13'):.2f})")
    print(f"   Fee Rate: {fee_rate:.2f}% vs 3.91% (difference: {fee_rate - Decimal('3.91'):.2f}%)")
    print()
    
    print(f"🔍 FIRST 10 PAID TRANSACTIONS:")
    for i, detail in enumerate(paid_details[:10]):
        print(f"   {i+1:2d}. {detail['date'][:10]} | HK${detail['amount_hkd']} | Fee: HK${detail['fee_hkd']} | {detail['customer']}")
    
    if len(paid_details) > 10:
        print(f"   ... and {len(paid_details) - 10} more paid transactions")
    
    print()
    print(f"💡 SOLUTION OPTIONS:")
    if paid_transactions > 20:
        print(f"   Option 1: Filter to only the first 20 paid transactions")
        print(f"   Option 2: Filter by date range to get exactly 20 transactions")
        print(f"   Option 3: Filter by amount range to match the required totals")
    
    # Calculate what the first 20 transactions would give us
    if len(paid_details) >= 20:
        first_20 = paid_details[:20]
        first_20_gross = sum(Decimal(str(t['amount_hkd'])) for t in first_20 if t['amount_hkd'])
        first_20_fees = sum(Decimal(str(t['fee_hkd'])) for t in first_20 if t['fee_hkd'])
        first_20_net = first_20_gross - first_20_fees
        first_20_rate = (first_20_fees / first_20_gross * 100) if first_20_gross > 0 else 0
        
        print()
        print(f"📊 FIRST 20 TRANSACTIONS ANALYSIS:")
        print(f"   Transactions: 20")
        print(f"   Gross: ${first_20_gross:.2f}")
        print(f"   Fees: ${first_20_fees:.2f}")
        print(f"   Net: ${first_20_net:.2f}")
        print(f"   Fee Rate: {first_20_rate:.2f}%")

if __name__ == "__main__":
    analyze_cgge_csv()
