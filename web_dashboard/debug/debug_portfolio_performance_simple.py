#!/usr/bin/env python3
"""
Simplified debug script - just test the Flask route's actual behavior.

This simulates what the Flask route does when calling the API.
"""

import sys
import os
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("Simple Portfolio Performance Debug")
print("=" * 80)
print()

# Import after path setup
try:
    from streamlit_utils import calculate_portfolio_value_over_time, get_user_display_currency
    print("[OK] Successfully imported modules")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

print()

# Test with same parameters as Flask route
test_fund = "Project Chimera"  # Change as needed
display_currency = get_user_display_currency() or 'CAD'

print(f"Fund: {test_fund}")
print(f"Display Currency: {display_currency}")
print()

try:
    print("Calling calculate_portfolio_value_over_time...")
    df = calculate_portfolio_value_over_time(
        fund=test_fund,
        days=None,  # ALL
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
            print(f"\n📊 Performance Index:")
            print(f"   First 20: {df['performance_index'].head(20).tolist()}")
            print(f"   Last 20: {df['performance_index'].tail(20).tolist()}")
            print(f"   Min: {df['performance_index'].min():.2f}")
            print(f"   Max: {df['performance_index'].max():.2f}")
            print(f"   Mean: {df['performance_index'].mean():.2f}")
            
            # Check for the pattern
            first_20 = df['performance_index'].head(20).tolist()
            is_pattern = all(abs(first_20[i] - i) < 2.0 for i in range(min(20, len(first_20))))
            if is_pattern:
                print("\n   [WARNING] Detected 0,1,2,3... pattern!")
        
        if 'performance_pct' in df.columns:
            print(f"\n📊 Performance %:")
            print(f"   First 20: {df['performance_pct'].head(20).tolist()}")
            print(f"   Min: {df['performance_pct'].min():.2f}")
            print(f"   Max: {df['performance_pct'].max():.2f}")
        
        if 'cost_basis' in df.columns:
            print(f"\n💰 Cost Basis:")
            print(f"   First 20: {df['cost_basis'].head(20).tolist()}")
            first_investment_idx = (df['cost_basis'] > 0).idxmax() if (df['cost_basis'] > 0).any() else None
            if first_investment_idx is not None:
                print(f"   First investment at row {first_investment_idx}: {df.loc[first_investment_idx, 'date']}")
                print(f"   First investment cost_basis: {df.loc[first_investment_idx, 'cost_basis']}")
                print(f"   First investment performance_pct: {df.loc[first_investment_idx, 'performance_pct']}")
                print(f"   First investment performance_index: {df.loc[first_investment_idx, 'performance_index']}")
        
        # Save to CSV for inspection
        output_file = "debug_portfolio_performance_output.csv"
        df.to_csv(output_file, index=False)
        print(f"\n[SAVED] Full output saved to: {output_file}")
        
except Exception as e:
    print(f"[ERROR] Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("Done")
print("="*80)
