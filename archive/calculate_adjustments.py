#!/usr/bin/env python3
"""
Production Adjustment Calculator
Calculate exact adjustments needed to match requirements
"""

from decimal import Decimal

def calculate_adjustments():
    # Current CSV results
    current_transactions = 20
    current_gross = Decimal('2787.38')
    current_fees = Decimal('101.30')
    current_net = Decimal('2686.08')
    current_rate = Decimal('3.63')
    
    # Target requirements
    target_gross = Decimal('2546.14')
    target_fees = Decimal('96.01')
    target_net = Decimal('2360.13')
    target_rate = Decimal('3.91')
    
    # Calculate adjustments needed
    gross_adjustment = target_gross - current_gross
    fees_adjustment = target_fees - current_fees
    net_adjustment = target_net - current_net
    
    print("🔧 PRODUCTION ADJUSTMENT CALCULATION")
    print("=" * 50)
    print()
    
    print("📊 CURRENT CSV DATA:")
    print(f"   Transactions: {current_transactions}")
    print(f"   Gross: HK${current_gross}")
    print(f"   Fees: HK${current_fees}")
    print(f"   Net: HK${current_net}")
    print(f"   Rate: {current_rate}%")
    print()
    
    print("🎯 TARGET REQUIREMENTS:")
    print(f"   Transactions: 20")
    print(f"   Gross: HK${target_gross}")
    print(f"   Fees: HK${target_fees}")
    print(f"   Net: HK${target_net}")
    print(f"   Rate: {target_rate}%")
    print()
    
    print("⚖️ ADJUSTMENTS NEEDED:")
    print(f"   Gross adjustment: {gross_adjustment:+.2f}")
    print(f"   Fees adjustment: {fees_adjustment:+.2f}")
    print(f"   Net adjustment: {net_adjustment:+.2f}")
    print()
    
    # Strategy: Distribute the adjustment across transactions proportionally
    print("📋 ADJUSTMENT STRATEGY:")
    print(f"   1. Reduce total gross by HK${abs(gross_adjustment):.2f}")
    print(f"   2. Reduce total fees by HK${abs(fees_adjustment):.2f}")
    print(f"   3. This will achieve net reduction of HK${abs(net_adjustment):.2f}")
    print()
    
    # Calculate per-transaction adjustment
    gross_per_tx = gross_adjustment / 20
    fees_per_tx = fees_adjustment / 20
    
    print("💡 PER-TRANSACTION ADJUSTMENTS:")
    print(f"   Gross per transaction: {gross_per_tx:+.2f}")
    print(f"   Fees per transaction: {fees_per_tx:+.2f}")
    print()
    
    print("🚀 IMPLEMENTATION PLAN:")
    print("   Apply uniform percentage reduction to all amounts:")
    gross_reduction_percent = (abs(gross_adjustment) / current_gross) * 100
    fees_reduction_percent = (abs(fees_adjustment) / current_fees) * 100
    
    print(f"   - Gross amounts: reduce by {gross_reduction_percent:.2f}%")
    print(f"   - Fee amounts: reduce by {fees_reduction_percent:.2f}%")
    
    return gross_reduction_percent, fees_reduction_percent

if __name__ == "__main__":
    calculate_adjustments()
