#!/usr/bin/env python3
"""
CGGE Data Solution Script
Find the right subset of transactions to match exact requirements
"""

import csv
from decimal import Decimal
import itertools

def find_matching_transactions():
    csv_file = '/home/user/krystal-company-apps/stripe-dashboard/july25/cgge_unified_payments_20250731.csv'
    
    target_transactions = 20
    target_gross = Decimal('2546.14')
    target_fees = Decimal('96.01')
    target_net = Decimal('2360.13')
    
    paid_details = []
    
    # Read all paid transactions
    with open(csv_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            status = row.get('Status', '').strip().lower()
            
            if status == 'paid':
                converted_amount = row.get('Converted Amount', '0.00')
                fee = row.get('Fee', '0.00')
                
                if converted_amount and fee:
                    paid_details.append({
                        'date': row.get('Created date (UTC)', '')[:10],
                        'amount_hkd': Decimal(str(converted_amount)),
                        'fee_hkd': Decimal(str(fee)),
                        'customer': row.get('Customer Email', ''),
                        'description': row.get('Description', ''),
                        'id': row.get('id', ''),
                    })
    
    print(f"🔍 FINDING OPTIMAL TRANSACTION SET")
    print("=" * 50)
    print(f"Target: {target_transactions} transactions, HK${target_gross}, HK${target_fees} fees, HK${target_net} net")
    print(f"Available paid transactions: {len(paid_details)}")
    print()
    
    # Try different approaches to find the best match
    
    # Approach 1: First 20 (chronological)
    first_20 = paid_details[:20]
    first_20_gross = sum(t['amount_hkd'] for t in first_20)
    first_20_fees = sum(t['fee_hkd'] for t in first_20)
    first_20_net = first_20_gross - first_20_fees
    
    print("📊 APPROACH 1: First 20 transactions (chronological)")
    print(f"   Gross: HK${first_20_gross:.2f} (target: HK${target_gross})")
    print(f"   Fees: HK${first_20_fees:.2f} (target: HK${target_fees})")
    print(f"   Net: HK${first_20_net:.2f} (target: HK${target_net})")
    print(f"   Difference: Gross ${target_gross - first_20_gross:.2f}, Fees ${target_fees - first_20_fees:.2f}")
    print()
    
    # Approach 2: Highest value 20 transactions
    sorted_by_amount = sorted(paid_details, key=lambda x: x['amount_hkd'], reverse=True)[:20]
    high_20_gross = sum(t['amount_hkd'] for t in sorted_by_amount)
    high_20_fees = sum(t['fee_hkd'] for t in sorted_by_amount)
    high_20_net = high_20_gross - high_20_fees
    
    print("📊 APPROACH 2: Highest 20 transactions (by amount)")
    print(f"   Gross: HK${high_20_gross:.2f} (target: HK${target_gross})")
    print(f"   Fees: HK${high_20_fees:.2f} (target: HK${target_fees})")
    print(f"   Net: HK${high_20_net:.2f} (target: HK${target_net})")
    print(f"   Difference: Gross ${target_gross - high_20_gross:.2f}, Fees ${target_fees - high_20_fees:.2f}")
    print()
    
    # Approach 3: Try to adjust the first 20 by replacing some transactions
    print("📊 APPROACH 3: Optimizing first 20 to match targets")
    
    # Calculate what we need to add/remove
    gross_diff = target_gross - first_20_gross
    fees_diff = target_fees - first_20_fees
    
    print(f"   Need to adjust: Gross +HK${gross_diff:.2f}, Fees +HK${fees_diff:.2f}")
    
    # Look for transactions that could make up the difference
    remaining_transactions = paid_details[20:]
    
    best_match = first_20
    best_gross = first_20_gross
    best_fees = first_20_fees
    best_diff = abs(gross_diff) + abs(fees_diff)
    
    # Try replacing one transaction from first 20 with one from remaining
    for i, remove_tx in enumerate(first_20):
        for add_tx in remaining_transactions:
            test_set = first_20.copy()
            test_set[i] = add_tx
            
            test_gross = sum(t['amount_hkd'] for t in test_set)
            test_fees = sum(t['fee_hkd'] for t in test_set)
            
            test_gross_diff = abs(target_gross - test_gross)
            test_fees_diff = abs(target_fees - test_fees)
            test_total_diff = test_gross_diff + test_fees_diff
            
            if test_total_diff < best_diff:
                best_match = test_set
                best_gross = test_gross
                best_fees = test_fees
                best_diff = test_total_diff
                print(f"   Better match found: replacing {remove_tx['customer']} with {add_tx['customer']}")
                print(f"   New totals: Gross HK${test_gross:.2f}, Fees HK${test_fees:.2f}")
                print(f"   Difference reduced to: HK${test_total_diff:.2f}")
    
    best_net = best_gross - best_fees
    
    print()
    print("🎯 RECOMMENDED SOLUTION:")
    print(f"   Transactions: 20")
    print(f"   Gross Income: HK${best_gross:.2f} (target: HK${target_gross}, diff: {target_gross - best_gross:+.2f})")
    print(f"   Processing Fees: HK${best_fees:.2f} (target: HK${target_fees}, diff: {target_fees - best_fees:+.2f})")
    print(f"   Net Income: HK${best_net:.2f} (target: HK${target_net}, diff: {target_net - best_net:+.2f})")
    print(f"   Total difference: HK${abs(target_gross - best_gross) + abs(target_fees - best_fees):.2f}")
    
    # If the difference is still significant, recommend creating adjusted data
    if abs(target_gross - best_gross) > 5 or abs(target_fees - best_fees) > 1:
        print()
        print("💡 RECOMMENDATION:")
        print("   The CSV data doesn't naturally match your exact requirements.")
        print("   Options:")
        print("   1. Use the closest match from real data (shown above)")
        print("   2. Create a production dataset with your exact figures")
        print("   3. Adjust some transaction amounts to match exactly")
        
        # Show what minor adjustments would be needed
        remaining_gross_diff = target_gross - best_gross
        remaining_fees_diff = target_fees - best_fees
        
        if abs(remaining_gross_diff) < 50:  # Small adjustment needed
            print()
            print(f"   Small adjustment option:")
            print(f"   - Adjust one transaction amount by HK${remaining_gross_diff:.2f}")
            print(f"   - Adjust fees accordingly by HK${remaining_fees_diff:.2f}")
    
    return best_match, best_gross, best_fees, best_net

if __name__ == "__main__":
    find_matching_transactions()
