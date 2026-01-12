#!/usr/bin/env python3
"""
Debug script to test Flask route context and caching behavior.

This simulates the Flask route's exact execution path to see if there's
a caching or context issue causing the wrong data.
"""

import sys
import os
import pandas as pd
from flask import Flask, request

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("Flask Route Context Debug")
print("=" * 80)
print()

# Create a minimal Flask app context
app = Flask(__name__)

# Import after path setup
try:
    from streamlit_utils import calculate_portfolio_value_over_time
    from user_preferences import get_user_currency
    from flask_auth_utils import get_user_email_flask
    print("[OK] Successfully imported modules")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

print()

# Test parameters
test_fund = "Project Chimera"  # Change as needed
display_currency = get_user_currency() or 'CAD'

print(f"Fund: {test_fund}")
print(f"Display Currency: {display_currency}")
print()

# Test 1: Without Flask context (like Streamlit)
print("=" * 80)
print("TEST 1: Without Flask Request Context (Streamlit-like)")
print("=" * 80)
print()

try:
    df_no_context = calculate_portfolio_value_over_time(
        fund=test_fund,
        days=None,
        display_currency=display_currency
    )
    
    if df_no_context.empty:
        print("[ERROR] Empty DataFrame")
    else:
        print(f"[OK] Got {len(df_no_context)} rows")
        if 'performance_index' in df_no_context.columns:
            print(f"   First 20 performance_index: {df_no_context['performance_index'].head(20).tolist()}")
            print(f"   Min: {df_no_context['performance_index'].min():.2f}, Max: {df_no_context['performance_index'].max():.2f}")
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: With Flask context (simulating the route)
print("=" * 80)
print("TEST 2: With Flask Request Context (Flask route-like)")
print("=" * 80)
print()

try:
    with app.test_request_context('/api/dashboard/charts/performance?fund=Project%20Chimera'):
        # This simulates the Flask route's context
        print("[OK] Flask request context created")
        
        # Try to get user email (might fail without cookies, that's OK)
        try:
            user_email = get_user_email_flask()
            print(f"   User email: {user_email or 'None (no auth cookie)'}")
        except Exception as e:
            print(f"   User email: Error - {e}")
        
        # Call the same function
        df_with_context = calculate_portfolio_value_over_time(
            fund=test_fund,
            days=None,
            display_currency=display_currency
        )
        
        if df_with_context.empty:
            print("[ERROR] Empty DataFrame")
        else:
            print(f"[OK] Got {len(df_with_context)} rows")
            if 'performance_index' in df_with_context.columns:
                print(f"   First 20 performance_index: {df_with_context['performance_index'].head(20).tolist()}")
                print(f"   Min: {df_with_context['performance_index'].min():.2f}, Max: {df_with_context['performance_index'].max():.2f}")
                
                # Compare with no-context version
                if not df_no_context.empty and 'performance_index' in df_no_context.columns:
                    print(f"\n   Comparison:")
                    print(f"   No context first 10: {df_no_context['performance_index'].head(10).tolist()}")
                    print(f"   With context first 10: {df_with_context['performance_index'].head(10).tolist()}")
                    
                    if len(df_no_context) == len(df_with_context):
                        diff = (df_no_context['performance_index'] - df_with_context['performance_index']).abs().max()
                        print(f"   Max difference: {diff:.2f}")
                        if diff > 0.01:
                            print("   [WARNING] Results differ between contexts!")
                    else:
                        print(f"   [WARNING] Different row counts ({len(df_no_context)} vs {len(df_with_context)})")
                        
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Check cache behavior
print("=" * 80)
print("TEST 3: Cache Behavior Check")
print("=" * 80)
print()

try:
    # Call twice to see if cache affects results
    print("First call...")
    df1 = calculate_portfolio_value_over_time(
        fund=test_fund,
        days=None,
        display_currency=display_currency
    )
    
    print("Second call (should use cache)...")
    df2 = calculate_portfolio_value_over_time(
        fund=test_fund,
        days=None,
        display_currency=display_currency
    )
    
    if not df1.empty and not df2.empty and 'performance_index' in df1.columns:
        print(f"   First call first 10: {df1['performance_index'].head(10).tolist()}")
        print(f"   Second call first 10: {df2['performance_index'].head(10).tolist()}")
        
        if (df1['performance_index'] == df2['performance_index']).all():
            print("   [OK] Results identical (cache working)")
        else:
            print("   [WARNING] Results differ (cache issue?)")
            
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("Done")
print("="*80)
