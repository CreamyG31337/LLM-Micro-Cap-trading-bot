#!/usr/bin/env python3
"""Investigate why August-September portfolio data is missing"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

print("="*80)
print("INVESTIGATION: Why is August-September data missing?")
print("="*80)

# 1. Check trade log - what's the first trade date?
print("\n1. TRADE LOG DATES")
print("-"*40)
trades_res = client.supabase.table('trade_log').select('date, ticker, fund').eq('fund', 'Project Chimera').order('date').execute()
if trades_res.data:
    df = pd.DataFrame(trades_res.data)
    df['date_only'] = pd.to_datetime(df['date']).dt.date
    print(f"Total trades: {len(df)}")
    print(f"First trade: {df['date_only'].min()}")
    print(f"Last trade: {df['date_only'].max()}")
    first_trade_date = df['date_only'].min()
else:
    print("NO TRADES FOUND!")
    first_trade_date = None

# 2. Check portfolio_positions - what dates exist?
print("\n2. PORTFOLIO_POSITIONS DATES")
print("-"*40)
pos_res = client.supabase.table('portfolio_positions').select('date, created_at').eq('fund', 'Project Chimera').order('date').limit(1000).execute()
if pos_res.data:
    pos_df = pd.DataFrame(pos_res.data)
    pos_df['date_only'] = pd.to_datetime(pos_df['date']).dt.date
    unique_dates = sorted(pos_df['date_only'].unique())
    print(f"Total position records: {len(pos_df)}")
    print(f"Unique dates: {len(unique_dates)}")
    print(f"First date: {unique_dates[0]}")
    print(f"Last date: {unique_dates[-1]}")
    
    # Check when positions were created
    pos_df['created_dt'] = pd.to_datetime(pos_df['created_at'])
    print(f"\nCreation dates: {sorted(pos_df['created_dt'].dt.date.unique())}")
    
    first_pos_date = unique_dates[0]
else:
    print("NO POSITIONS FOUND!")
    first_pos_date = None

# 3. Check the gap
print("\n3. DATE GAP ANALYSIS")
print("-"*40)
if first_trade_date and first_pos_date:
    print(f"First trade: {first_trade_date}")
    print(f"First position: {first_pos_date}")
    gap = (first_pos_date - first_trade_date).days
    print(f"GAP: {gap} days of missing position data!")
    
    # What August-September dates SHOULD exist?
    from datetime import date, timedelta
    current = first_trade_date
    missing_dates = []
    while current < first_pos_date:
        # Skip weekends
        if current.weekday() < 5:  # Monday-Friday
            missing_dates.append(current)
        current += timedelta(days=1)
    
    print(f"\nMissing trading days: {len(missing_dates)}")
    if missing_dates:
        print(f"Missing range: {missing_dates[0]} to {missing_dates[-1]}")

# 4. Check if there's a fund start date setting
print("\n4. FUND CONFIGURATION")
print("-"*40)
fund_res = client.supabase.table('funds').select('*').eq('name', 'Project Chimera').execute()
if fund_res.data:
    fund = fund_res.data[0]
    print(f"Fund name: {fund.get('name')}")
    print(f"Start date: {fund.get('start_date', 'NOT SET')}")
    print(f"Is production: {fund.get('is_production')}")
    print(f"Created at: {fund.get('created_at')}")
else:
    print("Fund not found!")

# 5. Check contributions to see fund activity timeline
print("\n5. CONTRIBUTION TIMELINE")
print("-"*40)
contrib_res = client.supabase.table('fund_contributions').select('timestamp, contributor, amount').eq('fund', 'Project Chimera').order('timestamp').limit(10).execute()
if contrib_res.data:
    for c in contrib_res.data:
        print(f"  {c['timestamp'][:10]} | {c['contributor']:20s} | ${c['amount']:,.2f}")
