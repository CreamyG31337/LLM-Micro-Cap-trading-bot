#!/usr/bin/env python3
"""
Test the Flask calculate_portfolio_value_over_time_flask function directly
to see what it returns.
"""

import sys
import os
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("Testing Flask calculate_portfolio_value_over_time_flask Function")
print("=" * 80)
print()

try:
    from flask_data_utils import calculate_portfolio_value_over_time_flask
    from supabase_client import SupabaseClient
    print("[OK] Successfully imported modules")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

# Patch get_supabase_client_flask to use service role
import flask_data_utils
original_get_client = flask_data_utils.get_supabase_client_flask

def get_supabase_client_flask_service_role():
    """Use service role to bypass RLS for debugging"""
    return SupabaseClient(use_service_role=True)

flask_data_utils.get_supabase_client_flask = get_supabase_client_flask_service_role
print("[INFO] Patched get_supabase_client_flask to use service role\n")

# Test parameters
test_fund = "Project Chimera"
display_currency = 'CAD'

print(f"Fund: {test_fund}")
print(f"Display Currency: {display_currency}")
print()

try:
    print("Calling calculate_portfolio_value_over_time_flask...")
    df = calculate_portfolio_value_over_time_flask(
        fund=test_fund,
        days=None,
        display_currency=display_currency
    )
    
    if df.empty:
        print("[ERROR] Empty DataFrame returned")
    else:
        print(f"[OK] Got {len(df)} rows")
        print(f"\nColumns: {list(df.columns)}")
        
        print(f"\nFirst 30 rows:")
        print(df.head(30).to_string())
        
        if 'performance_index' in df.columns:
            print(f"\n[INFO] Performance Index Analysis:")
            print(f"   First 30 values: {df['performance_index'].head(30).tolist()}")
            print(f"   Last 10 values: {df['performance_index'].tail(10).tolist()}")
            print(f"   Min: {df['performance_index'].min():.2f}")
            print(f"   Max: {df['performance_index'].max():.2f}")
            print(f"   Mean: {df['performance_index'].mean():.2f}")
            
            # Check for the 0,1,2,3... pattern
            first_30 = df['performance_index'].head(30).tolist()
            is_pattern = all(abs(first_30[i] - i) < 2.0 for i in range(min(30, len(first_30))))
            if is_pattern:
                print("\n   [WARNING] Detected 0,1,2,3... pattern!")
            else:
                print("\n   [OK] No 0,1,2,3... pattern detected")
        
        if 'performance_pct' in df.columns:
            print(f"\n[INFO] Performance % Analysis:")
            print(f"   First 30 values: {df['performance_pct'].head(30).tolist()}")
            print(f"   Min: {df['performance_pct'].min():.2f}")
            print(f"   Max: {df['performance_pct'].max():.2f}")
        
        if 'cost_basis' in df.columns:
            print(f"\n[INFO] Cost Basis Analysis:")
            print(f"   First 30 values: {df['cost_basis'].head(30).tolist()}")
            first_investment_idx = (df['cost_basis'] > 0).idxmax() if (df['cost_basis'] > 0).any() else None
            if first_investment_idx is not None:
                print(f"   First investment at row {first_investment_idx}: {df.loc[first_investment_idx, 'date']}")
                print(f"   First investment cost_basis: {df.loc[first_investment_idx, 'cost_basis']}")
                print(f"   First investment performance_pct: {df.loc[first_investment_idx, 'performance_pct']}")
                print(f"   First investment performance_index: {df.loc[first_investment_idx, 'performance_index']}")
        
        # Save to CSV
        output_file = "debug_flask_function_output.csv"
        df.to_csv(output_file, index=False)
        print(f"\n[SAVED] Full output saved to: {output_file}")
        
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original function
    flask_data_utils.get_supabase_client_flask = original_get_client

print("\n" + "="*80)
print("Done")
print("="*80)
