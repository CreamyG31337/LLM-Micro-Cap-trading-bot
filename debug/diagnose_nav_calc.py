#!/usr/bin/env python3
"""Diagnose the actual NAV calculation happening for Lance Colton"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime, timedelta
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

print("="*80)
print("DIAGNOSING ACTUAL NAV CALCULATION")
print("="*80)

# Get Lance's contributions
contribs = client.supabase.table('fund_contributions')\
    .select('*')\
    .eq('fund', fund_name)\
    .eq('contributor', 'Lance Colton')\
    .order('timestamp')\
    .execute()

# Get historical fund values (simulate get_historical_fund_values)
# Get ALL portfolio positions
all_rows = []
batch_size = 1000
offset = 0

while True:
    result = client.supabase.table("portfolio_positions").select(
        "date, ticker, shares, price, currency"
    ).eq("fund", fund_name).gte("date", '2025-09-01').order("date").range(offset, offset + batch_size - 1).execute()
    
    if not result.data:
        break
    
    all_rows.extend(result.data)
    
    if len(result.data) < batch_size:
        break
    
    offset += batch_size
    
    if offset > 50000:
        break

print(f"\nFetched {len(all_rows)} portfolio position rows")

# Build historical_values dict
historical_values = {}
for row in all_rows:
    date_key = row['date'][:10]
    shares = float(row.get('shares', 0) or 0)
    price = float(row.get('price', 0) or 0)
    
    if date_key not in historical_values:
        historical_values[date_key] = 0
    
    historical_values[date_key] += shares * price

print(f"Historical values for {len(historical_values)} unique dates")
print(f"Date range: {min(historical_values.keys())} to {max(historical_values.keys())}")

# Simulate the NAV calculation
total_units = 0.0
user_units = 0.0
net_contribution = 0.0

print("\n" + "="*80)
print("CONTRIBUTION-BY-CONTRIBUTION NAV CALCULATION")
print("="*80)

for contrib in contribs.data:
    amount = float(contrib['amount'])
    timestamp_raw = contrib['timestamp']
    timestamp = pd.to_datetime(timestamp_raw)
    date_str = timestamp.strftime('%Y-%m-%d')
    
    net_contribution += amount
    
    # Calculate NAV (simulating the fixed logic)
    if total_units == 0:
        nav_at_contribution = 1.0
        print(f"\n{date_str}: ${amount:>8.2f} | FIRST CONTRIBUTION -> NAV = 1.0000")
    elif date_str in historical_values:
        fund_value = historical_values[date_str]
        nav_at_contribution = fund_value / total_units
        print(f"\n{date_str}: ${amount:>8.2f} | Fund=${fund_value:,.2f} / {total_units:.4f} units = NAV {nav_at_contribution:.4f}")
    else:
        # Weekend/holiday - search backwards
        nav_at_contribution = 1.0
        contribution_date = datetime.strptime(date_str, '%Y-%m-%d')
        
        for days_back in range(1, 8):
            prior_date = contribution_date - timedelta(days=days_back)
            prior_date_str = prior_date.strftime('%Y-%m-%d')
            
            if prior_date_str in historical_values:
                fund_value = historical_values[prior_date_str]
                nav_at_contribution = fund_value / total_units
                print(f"\n{date_str}: ${amount:>8.2f} | WEEKEND → using {prior_date_str} ({prior_date.strftime('%A')})")
                print(f"  Fund=${fund_value:,.2f} / {total_units:.4f} units = NAV {nav_at_contribution:.4f}")
                break
        
        if nav_at_contribution == 1.0:
            print(f"\n{date_str}: ${amount:>8.2f} | !! NO DATA WITHIN 7 DAYS -> NAV = 1.0")
    
    units_purchased = amount / nav_at_contribution
    user_units += units_purchased
    total_units += units_purchased
    
    print(f"  Purchased: {units_purchased:.4f} units (total: {user_units:.4f})")

# Get current fund value
latest = client.supabase.table('portfolio_positions')\
    .select('date, shares, price')\
    .eq('fund', fund_name)\
    .order('date', desc=True)\
    .limit(100)\
    .execute()

current_value = sum(float(p['shares']) * float(p['price']) for p in latest.data if p['shares'] and p['price'])

print("\n" + "="*80)
print("FINAL CALCULATION")
print("="*80)
print(f"Net contribution: ${net_contribution:,.2f}")
print(f"Total units: {user_units:,.4f}")
print(f"Fund total units: {total_units:,.4f}")
print(f"Current fund value: ${current_value:,.2f}")
print(f"Current NAV: ${current_value / total_units:.4f}")
print(f"Your value: ${user_units * (current_value / total_units):,.2f}")
print(f"Your return: ${(user_units * (current_value / total_units) - net_contribution):,.2f}")
print(f"Return %: {((user_units * (current_value / total_units) - net_contribution) / net_contribution * 100):.2f}%")
