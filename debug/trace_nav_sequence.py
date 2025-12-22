#!/usr/bin/env python3
"""Trace the exact NAV calculation step by step"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime, timedelta
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get ALL contributions
all_contribs = client.supabase.table('fund_contributions')\
    .select('*')\
    .eq('fund', fund_name)\
    .order('timestamp')\
    .execute()

# Get historical values
all_rows = []
batch_size = 1000
offset = 0

while True:
    result = client.supabase.table("portfolio_positions").select(
        "date, shares, price"
    ).eq("fund", fund_name).gte("date", '2025-09-01').order("date").range(offset, offset + batch_size - 1).execute()
    
    if not result.data:
        break
    all_rows.extend(result.data)
    if len(result.data) < batch_size:
        break
    offset += batch_size

historical_values = {}
for row in all_rows:
    date_key = row['date'][:10]
    shares = float(row.get('shares', 0) or 0)
    price = float(row.get('price', 0) or 0)
    if date_key not in historical_values:
        historical_values[date_key] = 0
    historical_values[date_key] += shares * price

print("="*80)
print("FIRST 10 CONTRIBUTIONS - DETAILED TRACE")
print("="*80)

total_units = 0.0

for idx, contrib in enumerate(all_contribs.data[:10]):
    contributor = contrib['contributor']
    amount = float(contrib['amount'])
    timestamp = pd.to_datetime(contrib['timestamp'])
    date_str = timestamp.strftime('%Y-%m-%d')
    
    # Show NAV calculation
    print(f"\n[{idx+1}] {timestamp} | {contributor:20s} | ${amount:>8.2f}")
    
    if total_units == 0:
        nav = 1.0
        print(f"    NAV = 1.0000 (first contribution)")
    elif date_str in historical_values:
        fund_value = historical_values[date_str]
        nav = fund_value / total_units
        print(f"    Fund value on {date_str}: ${fund_value:,.2f}")
        print(f"    Total units so far: {total_units:,.4f}")
        print(f"    NAV = ${fund_value:,.2f} / {total_units:,.4f} = ${nav:.4f}")
    else:
        contribution_date = datetime.strptime(date_str, '%Y-%m-%d')
        found = False
        for days_back in range(1, 8):
            prior_date = contribution_date - timedelta(days=days_back)
            prior_date_str = prior_date.strftime('%Y-%m-%d')
            
            if prior_date_str in historical_values:
                fund_value = historical_values[prior_date_str]
                nav = fund_value / total_units
                print(f"    {date_str} is weekend/holiday -> using {prior_date_str}")
                print(f"    Fund value on {prior_date_str}: ${fund_value:,.2f}")
                print(f"    Total units so far: {total_units:,.4f}")
                print(f"    NAV = ${fund_value:,.2f} / {total_units:,.4f} = ${nav:.4f}")
                found = True
                break
        
        if not found:
            nav = 1.0
            print(f"    !! NO DATA for {date_str} (fallback to NAV=1.0)")
    
    units = amount / nav
    total_units += units
    
    print(f"    Units purchased: ${amount:.2f} / ${nav:.4f} = {units:.4f} units")
    print(f"    Running total units: {total_units:.4f}")
