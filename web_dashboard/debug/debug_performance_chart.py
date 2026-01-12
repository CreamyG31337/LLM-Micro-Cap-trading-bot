#!/usr/bin/env python3
"""
Debug script to test Portfolio Performance data calculation.

Tests both Streamlit and Flask code paths to identify where the
0, 1, 2, 3... pattern is coming from.
"""

import sys
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path (we're in web_dashboard/debug/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("PORTFOLIO PERFORMANCE DEBUG SCRIPT")
print("=" * 80)

# Test 1: Import and test Streamlit function
print("\n" + "=" * 80)
print("TEST 1: Streamlit calculate_portfolio_value_over_time")
print("=" * 80)

try:
    from streamlit_utils import get_supabase_client, calculate_portfolio_value_over_time

    print("[Streamlit] Getting Supabase client...")
    client = get_supabase_client()
    if not client:
        print("[Streamlit] ERROR: Could not get Supabase client")
    else:
        print("[Streamlit] Got Supabase client successfully")

    print("\n[Streamlit] Calling calculate_portfolio_value_over_time...")
    df_streamlit = calculate_portfolio_value_over_time(
        fund=None,  # All funds
        days=None,   # All time
        display_currency='CAD'
    )

    print(f"\n[Streamlit] Result:")
    print(f"  - Rows: {len(df_streamlit)}")
    print(f"  - Columns: {df_streamlit.columns.tolist()}")

    if not df_streamlit.empty:
        print(f"\n[Streamlit] First 5 rows:")
        print(df_streamlit[['date', 'value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']].head())

        print(f"\n[Streamlit] Last 5 rows:")
        print(df_streamlit[['date', 'value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']].tail())

        # Check for the 0,1,2,3 pattern
        perf_index_vals = df_streamlit['performance_index'].values
        print(f"\n[Streamlit] Performance Index Analysis:")
        print(f"  - First 10 values: {perf_index_vals[:10]}")
        print(f"  - Last 10 values: {perf_index_vals[-10:]}")

        # Check if it matches 0,1,2,3 pattern
        expected_pattern = list(range(len(perf_index_vals)))
        if list(perf_index_vals) == expected_pattern:
            print(f"  ⚠️ WARNING: Performance index matches exact 0,1,2,3 pattern!")
        else:
            # Check how close it is
            diff = perf_index_vals - pd.Series(expected_pattern, index=df_streamlit.index)
            max_diff = diff.abs().max()
            print(f"  ✅ OK: Max deviation from 0,1,2,3 pattern: {max_diff:.2f}")

except Exception as e:
    print(f"[Streamlit] ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Test Flask data utils function
print("\n" + "=" * 80)
print("TEST 2: Flask calculate_portfolio_value_over_time_flask")
print("=" * 80)

try:
    from flask_data_utils import get_supabase_client_flask, calculate_portfolio_value_over_time_flask

    print("[Flask] Getting Supabase client...")
    client_flask = get_supabase_client_flask()
    if not client_flask:
        print("[Flask] ERROR: Could not get Supabase client")
    else:
        print("[Flask] Got Supabase client successfully")

    print("\n[Flask] Calling calculate_portfolio_value_over_time_flask...")
    df_flask = calculate_portfolio_value_over_time_flask(
        fund=None,
        days=None
    )

    print(f"\n[Flask] Result:")
    print(f"  - Rows: {len(df_flask)}")
    print(f"  - Columns: {df_flask.columns.tolist()}")

    if not df_flask.empty:
        print(f"\n[Flask] First 5 rows:")
        print(df_flask[['date', 'value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']].head())

        print(f"\n[Flask] Last 5 rows:")
        print(df_flask[['date', 'value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']].tail())

        # Check for the 0,1,2,3 pattern
        perf_index_vals_flask = df_flask['performance_index'].values
        print(f"\n[Flask] Performance Index Analysis:")
        print(f"  - First 10 values: {perf_index_vals_flask[:10]}")
        print(f"  - Last 10 values: {perf_index_vals_flask[-10:]}")

        # Check if it matches 0,1,2,3 pattern
        expected_pattern = list(range(len(perf_index_vals_flask)))
        if list(perf_index_vals_flask) == expected_pattern:
            print(f"  ⚠️ WARNING: Performance index matches exact 0,1,2,3 pattern!")
        else:
            # Check how close it is
            diff = perf_index_vals_flask - pd.Series(expected_pattern, index=df_flask.index)
            max_diff = diff.abs().max()
            print(f"  ✅ OK: Max deviation from 0,1,2,3 pattern: {max_diff:.2f}")

except Exception as e:
    print(f"[Flask] ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Direct database query
print("\n" + "=" * 80)
print("TEST 3: Direct Database Query (portfolio_positions)")
print("=" * 80)

try:
    from streamlit_utils import get_supabase_client

    client = get_supabase_client()
    if not client:
        print("[DB] ERROR: Could not get Supabase client")
    else:
        print("[DB] Querying portfolio_positions table...")

        # Query first 100 rows to see raw data
        result = client.supabase.table("portfolio_positions").select(
            "date, fund, ticker, total_value, cost_basis, pnl, currency"
        ).order("date").limit(100).execute()

        if result.data:
            df_raw = pd.DataFrame(result.data)
            print(f"\n[DB] Raw portfolio_positions data:")
            print(f"  - Rows: {len(df_raw)}")
            print(f"  - Columns: {df_raw.columns.tolist()}")

            print(f"\n[DB] First 10 rows (raw):")
            print(df_raw.head(10))

            # Check unique dates
            print(f"\n[DB] Date statistics:")
            print(f"  - Unique dates: {df_raw['date'].nunique()}")
            print(f"  - Date range: {df_raw['date'].min()} to {df_raw['date'].max()}")

            # Aggregate by date (mimic Flask logic)
            df_raw['date'] = pd.to_datetime(df_raw['date'])
            daily_totals = df_raw.groupby(df_raw['date'].dt.date).agg({
                'total_value': 'sum',
                'cost_basis': 'sum',
                'pnl': 'sum'
            }).reset_index()

            daily_totals.columns = ['date', 'value', 'cost_basis', 'pnl']
            daily_totals['date'] = pd.to_datetime(daily_totals['date'])

            print(f"\n[DB] Aggregated daily totals (mimic Flask logic):")
            print(f"  - Rows: {len(daily_totals)}")

            # Calculate performance_pct (Flask style)
            daily_totals['performance_pct'] = daily_totals.apply(
                lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0,
                axis=1
            )

            daily_totals['performance_index'] = 100 + daily_totals['performance_pct']

            print(f"\n[DB] Calculated performance (Flask style):")
            print(daily_totals[['date', 'value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']].head(10))

            print(f"\n[DB] Performance Index (Flask style):")
            print(f"  - First 10 values: {daily_totals['performance_index'].head(10).tolist()}")

        else:
            print("[DB] No data returned")

except Exception as e:
    print(f"[DB] ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Check Flask route
print("\n" + "=" * 80)
print("TEST 4: Flask API Endpoint (/api/dashboard/charts/performance)")
print("=" * 80)

try:
    import requests

    # Try to fetch from Flask endpoint
    url = "http://localhost:5000/api/dashboard/charts/performance?range=ALL"
    print(f"[Flask API] Fetching from: {url}")

    try:
        response = requests.get(url, timeout=30)
        print(f"[Flask API] Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            print(f"[Flask API] Response keys: {data.keys()}")

            if 'data' in data:
                traces = data['data']
                print(f"[Flask API] Number of traces: {len(traces)}")

                for i, trace in enumerate(traces):
                    print(f"\n[Flask API] Trace {i+1}:")
                    print(f"  - Name: {trace.get('name', 'Unknown')}")
                    print(f"  - Mode: {trace.get('mode', 'Unknown')}")

                    if 'y' in trace:
                        y_values = trace['y']
                        print(f"  - Y values (first 10): {y_values[:10]}")
                        print(f"  - Y values (last 10): {y_values[-10:]}")

                        # Check for 0,1,2,3 pattern
                        if isinstance(y_values, list) and len(y_values) > 10:
                            expected = list(range(len(y_values)))
                            if y_values == expected:
                                print(f"  ⚠️ WARNING: Y values match exact 0,1,2,3 pattern!")
                            else:
                                # Check how close
                                diff_vals = [abs(y - e) for y, e in zip(y_values, expected)]
                                max_diff = max(diff_vals)
                                avg_diff = sum(diff_vals) / len(diff_vals)
                                print(f"  - Max deviation from 0,1,2,3: {max_diff:.2f}")
                                print(f"  - Avg deviation from 0,1,2,3: {avg_diff:.2f}")
        else:
            print(f"[Flask API] ERROR: {response.status_code}")
            print(response.text[:500])

    except requests.exceptions.ConnectionError:
        print("[Flask API] ERROR: Could not connect to Flask server")
        print("  Make sure Flask is running on port 5000")
    except Exception as e:
        print(f"[Flask API] ERROR: {e}")

except ImportError:
    print("[Flask API] requests module not available, skipping Flask API test")

print("\n" + "=" * 80)
print("DEBUG SCRIPT COMPLETE")
print("=" * 80)
