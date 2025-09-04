#!/usr/bin/env python3

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app

print("Creating app...")
app = create_app()

print("Registered blueprints:")
for name, bp in app.blueprints.items():
    print(f"  - {name}: {bp}")

print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    print(f"  {rule.methods} {rule.rule} -> {rule.endpoint}")

print(f"\nStarting app on port 9001...")
print("Test URLs:")
print("  - http://localhost:9001/")
print("  - http://localhost:9001/analytics/api/csv-health")
print("  - http://localhost:9001/analytics/simple")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9001)
