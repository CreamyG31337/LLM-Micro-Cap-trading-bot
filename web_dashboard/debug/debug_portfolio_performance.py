#!/usr/bin/env python3
"""
Debug script to investigate Portfolio Performance graph issue in Flask.

The issue: Graph shows 0, 1, 2, 3... pattern instead of starting at 100 with realistic performance.

This script will:
1. Test Flask route's data fetching
2. Compare Flask vs Streamlit data queries
3. Test calculate_portfolio_value_over_time function step by step
4. Check what columns are actually being returned
5. Verify the performance calculation logic
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("Portfolio Performance Debug Script")
print("=" * 80)
print()

# Import after path setup
try:
    from supabase_client import SupabaseClient
    from streamlit_utils import (
        get_supabase_client,
        calculate_portfolio_value_over_time,
        get_user_display_currency
    )
    from flask_data_utils import get_supabase_client_flask
    from chart_utils import _filter_trading_days
    print("[OK] Successfully imported modules")
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)

# Patch get_supabase_client to use service role for debugging
def patch_supabase_client():
    """Patch streamlit_utils to use service role client for debugging"""
    import streamlit_utils
    original_get_client = streamlit_utils.get_supabase_client
    
    def get_supabase_client_service_role(*args, **kwargs):
        """Use service role to bypass RLS for debugging"""
        return SupabaseClient(use_service_role=True)
    
    streamlit_utils.get_supabase_client = get_supabase_client_service_role
    return original_get_client

print()


def test_data_query(fund: Optional[str] = None, use_flask_client: bool = False):
    """Test the raw data query from portfolio_positions table"""
    print(f"\n{'='*80}")
    print(f"TEST 1: Raw Data Query (fund={fund}, flask_client={use_flask_client})")
    print(f"{'='*80}\n")
    
    if use_flask_client:
        # For Flask client, use service role directly since we're outside request context
        try:
            client = SupabaseClient(use_service_role=True)
            print("Using Flask client (service role - bypasses RLS)")
        except Exception as e:
            print(f"[ERROR] Failed to create Flask client: {e}")
            return None
    else:
        client = get_supabase_client()
        print("Using Streamlit client (get_supabase_client)")
    
    if not client:
        print("[ERROR] Failed to get Supabase client")
        return None
    
    try:
        # Query with same columns as streamlit_utils.py
        query = client.supabase.table("portfolio_positions").select(
            "date, total_value, cost_basis, pnl, fund, currency, "
            "total_value_base, cost_basis_base, pnl_base, base_currency"
        )
        
        if fund:
            query = query.eq("fund", fund)
        
        # Get first 100 rows to inspect
        result = query.order("date").limit(100).execute()
        
        if not result.data:
            print("[ERROR] No data returned")
            return None
        
        df = pd.DataFrame(result.data)
        print(f"[OK] Retrieved {len(df)} rows")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst few rows:")
        print(df.head(10).to_string())
        
        # Check for pre-converted values
        if 'total_value_base' in df.columns:
            preconverted_pct = df['total_value_base'].notna().mean()
            print(f"\n[INFO] Pre-converted values: {preconverted_pct*100:.1f}% have total_value_base")
            print(f"   Sample total_value_base values: {df['total_value_base'].head(5).tolist()}")
        
        # Check currencies
        if 'currency' in df.columns:
            currencies = df['currency'].value_counts()
            print(f"\n[INFO] Currencies: {currencies.to_dict()}")
        
        # Check date range
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            print(f"\n[INFO] Date range: {df['date'].min()} to {df['date'].max()}")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error querying data: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_calculate_function(fund: Optional[str] = None, days: Optional[int] = None, use_flask_client: bool = False):
    """Test the calculate_portfolio_value_over_time function"""
    print(f"\n{'='*80}")
    print(f"TEST 2: calculate_portfolio_value_over_time (fund={fund}, days={days}, flask_client={use_flask_client})")
    print(f"{'='*80}\n")
    
    try:
        # Temporarily patch get_supabase_client if using Flask client
        if use_flask_client:
            import streamlit_utils
            original_get_client = streamlit_utils.get_supabase_client
            streamlit_utils.get_supabase_client = get_supabase_client_flask
            print("[WARNING] Patched get_supabase_client to use Flask client")
        
        display_currency = get_user_display_currency() or 'CAD'
        print(f"Display currency: {display_currency}")
        
        df = calculate_portfolio_value_over_time(fund, days=days, display_currency=display_currency)
        
        if df.empty:
            print("[ERROR] Empty DataFrame returned")
            return None
        
        print(f"[OK] Retrieved {len(df)} rows")
        print(f"\nColumns: {list(df.columns)}")
        print(f"\nFirst 20 rows:")
        print(df.head(20).to_string())
        
        # Check for the 0,1,2,3... pattern
        if 'performance_index' in df.columns:
            print(f"\n[INFO] Performance Index Analysis:")
            print(f"   First 10 values: {df['performance_index'].head(10).tolist()}")
            print(f"   Last 10 values: {df['performance_index'].tail(10).tolist()}")
            print(f"   Min: {df['performance_index'].min()}, Max: {df['performance_index'].max()}")
            print(f"   Mean: {df['performance_index'].mean():.2f}")
            
            # Check if it's the problematic pattern
            first_10 = df['performance_index'].head(10).tolist()
            if all(abs(first_10[i] - i) < 1.0 for i in range(len(first_10))):
                print("   [WARNING] Detected 0,1,2,3... pattern!")
        
        if 'performance_pct' in df.columns:
            print(f"\n[INFO] Performance % Analysis:")
            print(f"   First 10 values: {df['performance_pct'].head(10).tolist()}")
            print(f"   Last 10 values: {df['performance_pct'].tail(10).tolist()}")
            print(f"   Min: {df['performance_pct'].min()}, Max: {df['performance_pct'].max()}")
        
        if 'cost_basis' in df.columns:
            print(f"\n[INFO] Cost Basis Analysis:")
            print(f"   First 10 values: {df['cost_basis'].head(10).tolist()}")
            print(f"   Days with cost_basis > 0: {(df['cost_basis'] > 0).sum()}")
            first_investment = df[df['cost_basis'] > 0]
            if not first_investment.empty:
                print(f"   First investment day: {first_investment.iloc[0]['date']}")
                print(f"   First investment cost_basis: {first_investment.iloc[0]['cost_basis']}")
                print(f"   First investment performance_pct: {first_investment.iloc[0].get('performance_pct', 'N/A')}")
        
        # Restore original function
        if use_flask_client:
            streamlit_utils.get_supabase_client = original_get_client
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error calculating portfolio value: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_step_by_step_calculation(fund: Optional[str] = None):
    """Test the calculation step by step to find where it goes wrong"""
    print(f"\n{'='*80}")
    print(f"TEST 3: Step-by-Step Calculation (fund={fund})")
    print(f"{'='*80}\n")
    
    client = get_supabase_client()
    if not client:
        print("[ERROR] Failed to get Supabase client")
        return None
    
    try:
        # Step 1: Query data
        print("Step 1: Querying portfolio_positions...")
        query = client.supabase.table("portfolio_positions").select(
            "date, total_value, cost_basis, pnl, fund, currency, "
            "total_value_base, cost_basis_base, pnl_base, base_currency"
        )
        
        if fund:
            query = query.eq("fund", fund)
        
        result = query.order("date").limit(1000).execute()
        
        if not result.data:
            print("[ERROR] No data returned")
            return None
        
        df = pd.DataFrame(result.data)
        print(f"   [OK] Retrieved {len(df)} rows")
        
        # Step 2: Normalize dates
        print("\nStep 2: Normalizing dates...")
        df['date'] = pd.to_datetime(df['date']).dt.normalize() + pd.Timedelta(hours=12)
        print(f"   Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Step 3: Check pre-converted values
        print("\nStep 3: Checking pre-converted values...")
        has_preconverted = False
        if 'total_value_base' in df.columns and 'base_currency' in df.columns:
            preconverted_pct = df['total_value_base'].notna().mean()
            has_preconverted = preconverted_pct > 0.8
            print(f"   Pre-converted: {preconverted_pct*100:.1f}% (threshold: 80%)")
            print(f"   Using pre-converted: {has_preconverted}")
        
        # Step 4: Select columns
        if has_preconverted:
            value_col = 'total_value_base'
            cost_col = 'cost_basis_base'
            pnl_col = 'pnl_base'
            print(f"\nStep 4: Using pre-converted columns: {value_col}, {cost_col}, {pnl_col}")
        else:
            value_col = 'total_value'
            cost_col = 'cost_basis'
            pnl_col = 'pnl'
            print(f"\nStep 4: Using raw columns: {value_col}, {cost_col}, {pnl_col}")
        
        # Step 5: Aggregate by date
        print("\nStep 5: Aggregating by date...")
        daily_totals = df.groupby(df['date'].dt.date).agg({
            value_col: 'sum',
            cost_col: 'sum',
            pnl_col: 'sum'
        }).reset_index()
        
        daily_totals.columns = ['date', 'value', 'cost_basis', 'pnl']
        daily_totals['date'] = pd.to_datetime(daily_totals['date'])
        daily_totals = daily_totals.sort_values('date').reset_index(drop=True)
        
        print(f"   [OK] Aggregated to {len(daily_totals)} days")
        print(f"   First 5 rows:")
        print(daily_totals.head(5).to_string())
        
        # Step 6: Calculate performance_pct
        print("\nStep 6: Calculating performance_pct...")
        daily_totals['performance_pct'] = np.where(
            daily_totals['cost_basis'] > 0,
            (daily_totals['pnl'] / daily_totals['cost_basis'] * 100),
            0.0
        )
        print(f"   First 10 performance_pct values: {daily_totals['performance_pct'].head(10).tolist()}")
        
        # Step 7: Normalize to first day
        print("\nStep 7: Normalizing to first investment day...")
        first_day_with_investment = daily_totals[daily_totals['cost_basis'] > 0]
        if not first_day_with_investment.empty:
            first_day_performance = first_day_with_investment.iloc[0]['performance_pct']
            print(f"   First investment day: {first_day_with_investment.iloc[0]['date']}")
            print(f"   First day performance_pct: {first_day_performance}")
            
            mask = daily_totals['cost_basis'] > 0
            daily_totals.loc[mask, 'performance_pct'] = daily_totals.loc[mask, 'performance_pct'] - first_day_performance
            print(f"   After normalization, first 10 performance_pct values: {daily_totals['performance_pct'].head(10).tolist()}")
        else:
            print("   [WARNING] No days with investment found!")
        
        # Step 8: Calculate performance_index
        print("\nStep 8: Calculating performance_index...")
        daily_totals['performance_index'] = 100 + daily_totals['performance_pct']
        print(f"   First 10 performance_index values: {daily_totals['performance_index'].head(10).tolist()}")
        print(f"   Last 10 performance_index values: {daily_totals['performance_index'].tail(10).tolist()}")
        
        # Step 9: Filter trading days
        print("\nStep 9: Filtering trading days...")
        before_filter = len(daily_totals)
        daily_totals = _filter_trading_days(daily_totals, 'date')
        after_filter = len(daily_totals)
        print(f"   Before filter: {before_filter} days, After filter: {after_filter} days")
        print(f"   First 10 performance_index values after filter: {daily_totals['performance_index'].head(10).tolist()}")
        
        return daily_totals
        
    except Exception as e:
        print(f"[ERROR] Error in step-by-step calculation: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all debug tests"""
    print("\n" + "="*80)
    print("Starting Portfolio Performance Debug Tests")
    print("="*80 + "\n")
    
    # Patch to use service role for debugging
    original_get_client = patch_supabase_client()
    print("[INFO] Patched get_supabase_client to use service role (bypasses RLS)\n")
    
    # Test with a specific fund (change as needed)
    test_fund = "Project Chimera"  # Change this to your test fund
    # test_fund = None  # Uncomment to test all funds
    
    print(f"Testing with fund: {test_fund or 'ALL FUNDS'}\n")
    
    # Test 1: Raw data query (Streamlit client)
    df_streamlit = test_data_query(test_fund, use_flask_client=False)
    
    # Test 1b: Raw data query (Flask client)
    df_flask = test_data_query(test_fund, use_flask_client=True)
    
    # Compare the two
    if df_streamlit is not None and df_flask is not None:
        print(f"\n{'='*80}")
        print("COMPARISON: Streamlit vs Flask Client Queries")
        print(f"{'='*80}\n")
        print(f"Streamlit rows: {len(df_streamlit)}, Flask rows: {len(df_flask)}")
        print(f"Streamlit columns: {list(df_streamlit.columns)}")
        print(f"Flask columns: {list(df_flask.columns)}")
        
        if 'total_value_base' in df_streamlit.columns and 'total_value_base' in df_flask.columns:
            streamlit_preconverted = df_streamlit['total_value_base'].notna().mean()
            flask_preconverted = df_flask['total_value_base'].notna().mean()
            print(f"\nPre-converted values:")
            print(f"  Streamlit: {streamlit_preconverted*100:.1f}%")
            print(f"  Flask: {flask_preconverted*100:.1f}%")
    
    # Test 2: Full calculation (Streamlit client)
    result_streamlit = test_calculate_function(test_fund, days=None, use_flask_client=False)
    
    # Test 2b: Full calculation (Flask client)
    result_flask = test_calculate_function(test_fund, days=None, use_flask_client=True)
    
    # Test 3: Step-by-step calculation
    result_step_by_step = test_step_by_step_calculation(test_fund)
    
    # Restore original function
    import streamlit_utils
    streamlit_utils.get_supabase_client = original_get_client
    
    print("\n" + "="*80)
    print("Debug Tests Complete")
    print("="*80)
    print("\nReview the output above to identify the issue.")


if __name__ == "__main__":
    main()
