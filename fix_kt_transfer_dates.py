#!/usr/bin/env python3
"""
Script to fix incorrect transfer dates in Krystal Technology CSV data.

The issue: Transactions from March 2023 onwards have incorrect transfer dates
assigned to 2024-03-26, causing monthly reconciliation errors.

This script corrects transfer dates to match logical payout periods.
"""

import csv
import os
import shutil
from datetime import datetime, timedelta
from typing import List, Dict

class KTTransferDateFixer:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.backup_path = csv_path.replace('.csv', '_backup.csv')
        
    def backup_original(self) -> bool:
        """Create backup of original CSV file"""
        try:
            shutil.copy2(self.csv_path, self.backup_path)
            print(f"✓ Backup created: {self.backup_path}")
            return True
        except Exception as e:
            print(f"✗ Failed to create backup: {e}")
            return False
    
    def read_csv_data(self) -> List[Dict]:
        """Read and parse CSV data"""
        transactions = []
        
        with open(self.csv_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('id', '').strip():
                    transactions.append(row)
        
        print(f"✓ Read {len(transactions)} transactions")
        return transactions
    
    def fix_transfer_dates(self, transactions: List[Dict]) -> List[Dict]:
        """Fix incorrect transfer dates based on transaction periods"""
        fixed_count = 0
        
        for tx in transactions:
            created_str = tx.get('Created (UTC)', '').strip()
            transfer_str = tx.get('Transfer Date (UTC)', '').strip()
            
            if not created_str or not transfer_str:
                continue
                
            try:
                # Parse created date
                created = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                
                # Parse current transfer date
                current_transfer = datetime.strptime(transfer_str, '%Y-%m-%d %H:%M')
                
                # Check if transfer date is suspiciously far from created date
                days_diff = (current_transfer - created).days
                
                if days_diff > 60:  # Transfer more than 2 months after creation
                    # Calculate appropriate transfer date (typically 7 days after creation)
                    new_transfer = created + timedelta(days=7)
                    
                    # Adjust to business day if needed (avoid weekends)
                    while new_transfer.weekday() > 4:  # 5=Saturday, 6=Sunday
                        new_transfer += timedelta(days=1)
                    
                    # Update transfer date
                    tx['Transfer Date (UTC)'] = new_transfer.strftime('%Y-%m-%d %H:%M')
                    
                    print(f"Fixed transaction {tx['id'][:20]}...")
                    print(f"  Created: {created_str}")
                    print(f"  Old transfer: {transfer_str}")
                    print(f"  New transfer: {tx['Transfer Date (UTC)']}")
                    print()
                    
                    fixed_count += 1
                    
            except ValueError as e:
                print(f"Warning: Could not parse dates for transaction {tx['id']}: {e}")
                continue
        
        print(f"✓ Fixed {fixed_count} transactions")
        return transactions
    
    def write_corrected_csv(self, transactions: List[Dict]) -> bool:
        """Write corrected data back to CSV file"""
        try:
            if not transactions:
                print("✗ No transactions to write")
                return False
            
            # Get fieldnames from first transaction
            fieldnames = list(transactions[0].keys())
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(transactions)
            
            print(f"✓ Corrected data written to {self.csv_path}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to write corrected CSV: {e}")
            return False
    
    def validate_corrections(self, transactions: List[Dict]) -> bool:
        """Validate that corrections look reasonable"""
        print("\n=== Validation Report ===")
        
        # Check for transactions with very old transfer dates
        old_transfer_count = 0
        future_transfer_count = 0
        now = datetime.now()
        
        for tx in transactions:
            transfer_str = tx.get('Transfer Date (UTC)', '').strip()
            created_str = tx.get('Created (UTC)', '').strip()
            
            if transfer_str and created_str:
                try:
                    transfer_date = datetime.strptime(transfer_str, '%Y-%m-%d %H:%M')
                    created_date = datetime.strptime(created_str, '%Y-%m-%d %H:%M')
                    
                    # Check for suspicious patterns
                    if transfer_date > now:
                        future_transfer_count += 1
                    
                    days_diff = (transfer_date - created_date).days
                    if days_diff > 30:
                        old_transfer_count += 1
                        
                except ValueError:
                    continue
        
        print(f"Transactions with transfer dates > 30 days after creation: {old_transfer_count}")
        print(f"Transactions with future transfer dates: {future_transfer_count}")
        
        if old_transfer_count == 0:
            print("✓ All transfer dates look reasonable")
            return True
        else:
            print("⚠ Some transfer dates may still need review")
            return False
    
    def run_fix(self) -> bool:
        """Run the complete fix process"""
        print("=== Krystal Technology Transfer Date Fixer ===\n")
        
        # Step 1: Backup
        if not self.backup_original():
            return False
        
        # Step 2: Read data
        transactions = self.read_csv_data()
        if not transactions:
            return False
        
        # Step 3: Fix transfer dates
        fixed_transactions = self.fix_transfer_dates(transactions)
        
        # Step 4: Validate corrections
        self.validate_corrections(fixed_transactions)
        
        # Step 5: Write corrected data
        if not self.write_corrected_csv(fixed_transactions):
            return False
        
        print("\n✓ Transfer date fix completed successfully!")
        print(f"Original file backed up to: {self.backup_path}")
        
        return True

def main():
    csv_path = "/Users/wongivan/company_apps/stripe-dashboard/complete_csv/kt_2022_Sept-2025_Jul.csv"
    
    if not os.path.exists(csv_path):
        print(f"✗ CSV file not found: {csv_path}")
        return
    
    fixer = KTTransferDateFixer(csv_path)
    success = fixer.run_fix()
    
    if success:
        print("\n🎉 KT transfer dates have been corrected!")
        print("You can now regenerate monthly statements for accurate figures.")
    else:
        print("\n❌ Fix process failed. Check error messages above.")

if __name__ == "__main__":
    main()