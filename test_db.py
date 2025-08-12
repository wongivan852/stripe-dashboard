#!/usr/bin/env python3
import sqlite3
import os

# Test SQLite connection
db_path = '/home/user/krystal-company-apps/stripe-dashboard/instance/payments.db'

print(f"Testing SQLite connection...")
print(f"Database path: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

try:
    # Create a new database file
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test table
    cursor.execute('''
        CREATE TABLE test (
            id INTEGER PRIMARY KEY,
            name TEXT
        )
    ''')
    
    # Insert test data
    cursor.execute("INSERT INTO test (name) VALUES (?)", ("test_data",))
    
    # Query test data
    cursor.execute("SELECT * FROM test")
    results = cursor.fetchall()
    
    print(f"✅ SQLite test successful! Results: {results}")
    
    conn.commit()
    conn.close()
    
except Exception as e:
    print(f"❌ SQLite error: {e}")
