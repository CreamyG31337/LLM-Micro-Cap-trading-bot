#!/usr/bin/env python3
"""Calculate with CORRECT current fund value"""

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

print("Historical values built from portfolio_positions")

# Process ALL contributions with FIXED NAV logic
contributor_units = {}
contributor_contributions = {}
total_units = 0.0
units_at_start_of_day = 0.0
last_contribution_date = None

for contrib in all_contribs.data:
    contributor = contrib['contributor']
    amount = float(contrib['amount'])
    timestamp_raw = contrib['timestamp']
    timestamp = pd.to_datetime(timestamp_raw)
    date_str = timestamp.strftime('%Y-%m-%d')
    
    # SAME-DAY NAV FIX
    if date_str != last_contribution_date:
        units_at_start_of_day = total_units
        last_contribution_date = date_str
    
    if contributor not in contributor_units:
        contributor_units[contributor] = 0.0
        contributor_contributions[contributor] = 0.0
    
    contributor_contributions[contributor] += amount
    
    # Calculate NAV
    if total_units == 0:
        nav = 1.0
    elif date_str in historical_values:
        nav = historical_values[date_str] / units_at_start_of_day if units_at_start_of_day > 0 else 1.0
    else:
        nav = 1.0
        contribution_date = datetime.strptime(date_str, '%Y-%m-%d')
        for days_back in range(1, 8):
            prior_date = contribution_date - timedelta(days=days_back)
            prior_date_str = prior_date.strftime('%Y-%m-%d')
            if prior_date_str in historical_values:
                nav = historical_values[prior_date_str] / units_at_start_of_day if units_at_start_of_day > 0 else 1.0
                break
    
    units = amount / nav
    contributor_units[contributor] += units
    total_units += units

# Get CORRECT current fund value (latest date only!)
latest = client.supabase.table('portfolio_positions')\
    .select('*')\
    .eq('fund', fund_name)\
    .order('date', desc=True)\
    .limit(100)\
    .execute()

df = pd.DataFrame(latest.data)
latest_date = df['date'].max()
latest_df = df[df['date'] == latest_date]
current_fund_value = (latest_df['shares'].astype(float) * latest_df['price'].astype(float)).sum()

current_nav = current_fund_value / total_units if total_units > 0 else 1.0

print("="*80)
print("CORRECT CALCULATION WITH ACTUAL FUND VALUE")
print("="*80)
print(f"Latest date: {latest_date}")
print(f"Current fund value: ${current_fund_value:,.2f}")
print(f"Total units: {total_units:,.2f}")
print(f"Current NAV: ${current_nav:.4f}")

print("\n" + "="*80)
print("INVESTOR RETURNS")
print("="*80)

for contributor in sorted(contributor_units.keys(), key=lambda c: contributor_units[c], reverse=True):
    units = contributor_units[contributor]
    contribution = contributor_contributions[contributor]
    current_value = units * current_nav
    return_amount = current_value - contribution
    return_pct = (return_amount / contribution * 100) if contribution > 0 else 0
    ownership = (units / total_units * 100) if total_units > 0 else 0
    
    marker = " <-- LANCE" if contributor == "Lance Colton" else ""
    print(f"\n{contributor:20s} | Own: {ownership:>6.2f}% | Units: {units:>10.2f}{marker}")
    print(f"  Contributed: ${contribution:>10,.2f}")
    print(f"  Current val: ${current_value:>10,.2f}")
    print(f"  Return:      ${return_amount:>10,.2f} ({return_pct:>+6.2f}%)")
