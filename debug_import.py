#!/usr/bin/env python3

import sys
import traceback

print("Testing analytics blueprint import...")

try:
    from app.routes.analytics import analytics_bp
    print("✅ Analytics blueprint import successful")
    print(f"Analytics blueprint: {analytics_bp}")
    print(f"Analytics blueprint routes: {[rule.rule for rule in analytics_bp.url_map.iter_rules()]}")
except Exception as e:
    print(f"❌ Analytics blueprint import failed: {e}")
    print("Full traceback:")
    traceback.print_exc()

print("\nTesting full app creation...")
try:
    from app import create_app
    app = create_app()
    
    print("✅ App creation successful")
    print("Registered blueprints:")
    for blueprint_name, blueprint in app.blueprints.items():
        print(f"  - {blueprint_name}: {blueprint}")
    
    print("\nAll routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.methods} {rule.rule}")
        
except Exception as e:
    print(f"❌ App creation failed: {e}")
    print("Full traceback:")
    traceback.print_exc()
