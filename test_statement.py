import sys
sys.path.append('/home/user/krystal-company-apps/stripe-dashboard')
from app.services.complete_csv_service import CompleteCsvService

print('=== TESTING MONTHLY STATEMENT GENERATION ===')
service = CompleteCsvService()

try:
    statement = service.generate_monthly_statement(2025, 8, 'cgge', 554.77)
    print(f'✅ Generated statement successfully')
    print(f'Total transactions: {len(statement["transactions"])}')
    
    payments = [t for t in statement['transactions'] if t['type'] == 'payment' and not t.get('is_fee')]
    print(f'Payment transactions: {len(payments)}')
    
    print('Transaction IDs in statement:')
    for i, tx in enumerate(statement['transactions'][:10], 1):
        tx_type = 'PAYMENT' if tx['type'] == 'payment' and not tx.get('is_fee') else tx['type'].upper()
        print(f'{i}. {tx["stripe_id"]} ({tx_type}) - Amount: {tx["amount"]}')
        
    print(f'\nOpening Balance: HK${statement["opening_balance"]}')
    print(f'Closing Balance: HK${statement["closing_balance"]}')
    
except Exception as e:
    print(f'❌ Error generating statement: {e}')
    import traceback
    traceback.print_exc()