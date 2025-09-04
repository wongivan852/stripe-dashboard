#!/usr/bin/env python3
"""
Test the actual API endpoints to verify the monthly statement functionality
"""

import requests
import json
from datetime import datetime

def test_monthly_statement_api():
    """Test the monthly statement API endpoint"""
    
    # API endpoint
    base_url = "http://127.0.0.1:8081"  # Using the running server
    api_url = f"{base_url}/analytics/api/monthly-statement"
    
    # Test parameters
    params = {
        'company': 'cgge',
        'year': 2025,
        'month': 7
    }
    
    try:
        print("🧪 Testing Monthly Statement API...")
        print(f"URL: {api_url}")
        print(f"Parameters: {params}")
        
        response = requests.get(api_url, params=params, timeout=30)
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                statement = data.get('statement', {})
                print(f"✅ Company: {statement.get('company_filter')}")
                print(f"✅ Opening Balance: HK${statement.get('opening_balance', 0):.2f}")
                print(f"✅ Closing Balance: HK${statement.get('closing_balance', 0):.2f}")
                print(f"✅ Total Transactions: {len(statement.get('transactions', []))}")
                print(f"✅ Total Debit: {statement.get('total_debit')}")
                print(f"✅ Total Credit: {statement.get('total_credit')}")
                
                # Show first few transactions
                transactions = statement.get('transactions', [])[:3]
                print("\n📋 Sample Transactions:")
                for i, tx in enumerate(transactions):
                    print(f"  {i+1}. {tx.get('date')} - {tx.get('nature')} - {tx.get('party')} - Debit: {tx.get('debit')} - Credit: {tx.get('credit')} - Balance: {tx.get('balance')}")
                
                return True
            else:
                print(f"❌ API Error: {data.get('error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_pdf_export():
    """Test the PDF export endpoint"""
    
    base_url = "http://127.0.0.1:8081"
    pdf_url = f"{base_url}/analytics/api/export-pdf"
    
    params = {
        'company': 'cgge',
        'year': 2025,
        'month': 7
    }
    
    try:
        print("\n🧪 Testing PDF Export...")
        print(f"URL: {pdf_url}")
        
        response = requests.get(pdf_url, params=params, timeout=30)
        
        print(f"✅ Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Save the PDF
            filename = f"test_export_cgge_2025_07.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ PDF saved: {filename}")
            print(f"✅ PDF size: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Monthly Statement Implementation")
    print("=" * 50)
    
    # Test API
    api_success = test_monthly_statement_api()
    
    # Test PDF export
    pdf_success = test_pdf_export()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  API Test: {'✅ PASS' if api_success else '❌ FAIL'}")
    print(f"  PDF Test: {'✅ PASS' if pdf_success else '❌ FAIL'}")
    
    if api_success and pdf_success:
        print("\n🎉 All tests passed! The monthly statement system is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Please check the server logs.")

if __name__ == "__main__":
    main()