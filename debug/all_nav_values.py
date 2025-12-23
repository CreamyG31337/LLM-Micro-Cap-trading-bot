#!/usr/bin/env python3
"""Print ALL NAV values with sanity check applied"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime, timedelta
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund = 'Project Chimera'

# Get all contributions
result = client.supabase.table('fund_contributions').select(
    'contributor, email, amount, contribution_type, timestamp'
).eq('fund', fund).order('timestamp').execute()

contributions = []
for r in result.data:
    contributions.append({
        'contributor': r['contributor'],
        'email': r.get('email', ''),
        'amount': float(r['amount']),
        'type': r.get('contribution_type', 'CONTRIBUTION').lower(),
        'timestamp': r.get('timestamp')
    })

# Get historical values with currency conversion
positions_result = client.supabase.table('portfolio_positions').select(
    'date, shares, price, currency'
).eq('fund', fund).execute()

historical_values = {}
if positions_result.data:
    df = pd.DataFrame(positions_result.data)
    df['date'] = pd.to_datetime(df['date'])
    df['price'] = df['price'].astype(float)
    df['shares'] = df['shares'].astype(float)
    df['value_cad'] = df.apply(
        lambda row: row['shares'] * row['price'] * (1.42 if row.get('currency') == 'USD' else 1.0),
        axis=1
    )
    daily = df.groupby('date')['value_cad'].sum()
    for date_ts, value in daily.items():
        historical_values[date_ts.strftime('%Y-%m-%d')] = value

print("="*110)
print("NAV VALUES WITH SANITY CHECK (50% drop protection)")
print("="*110)
print(f"{'Date':<12} {'Contributor':<20} {'Amount':>12} {'Source':<25} {'Calc NAV':>10} {'Used NAV':>10} {'Units':>10}")
print("-"*110)

total_units = 0.0
contributor_units = {}
units_at_start_of_day = 0.0
last_contribution_date = None
last_valid_nav = 1.0  # Track for sanity check

for contrib in contributions:
    contributor = contrib['contributor']
    amount = contrib['amount']
    contrib_type = contrib['type']
    ts = contrib['timestamp']
    
    # Parse date
    date_str = None
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    # Same-day tracking
    if date_str != last_contribution_date:
        units_at_start_of_day = total_units
        last_contribution_date = date_str
    
    if contributor not in contributor_units:
        contributor_units[contributor] = 0.0
    
    if contrib_type == 'withdrawal':
        print(f"{date_str:<12} {contributor[:20]:<20} {f'-${amount:,.2f}':>12} {'WITHDRAWAL':<25} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
        continue
    
    # Calculate NAV
    calculated_nav = 1.0
    used_nav = 1.0
    source = ""
    
    if total_units == 0:
        calculated_nav = 1.0
        used_nav = 1.0
        last_valid_nav = 1.0
        source = "FIRST (NAV=1.0)"
    elif date_str and date_str in historical_values:
        fund_value = historical_values[date_str]
        units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
        calculated_nav = fund_value / units_for_nav if units_for_nav > 0 else 1.0
        
        # SANITY CHECK: If calculated NAV drops more than 50%, use previous NAV
        if calculated_nav < last_valid_nav * 0.5:
            used_nav = last_valid_nav
            source = f"**BLOCKED** ({date_str})"
        else:
            used_nav = calculated_nav
            last_valid_nav = calculated_nav
            source = f"HISTORICAL ({date_str})"
    else:
        # Weekend fallback
        calculated_nav = last_valid_nav
        used_nav = last_valid_nav
        source = "FALLBACK (prev NAV)"
        
        if date_str:
            try:
                contrib_date = datetime.strptime(date_str, '%Y-%m-%d')
                for days_back in range(1, 8):
                    prior = contrib_date - timedelta(days=days_back)
                    prior_str = prior.strftime('%Y-%m-%d')
                    if prior_str in historical_values:
                        units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
                        if units_for_nav > 0:
                            calculated_nav = historical_values[prior_str] / units_for_nav
                            # Apply sanity check to fallback too
                            if calculated_nav < last_valid_nav * 0.5:
                                used_nav = last_valid_nav
                                source = f"**BLOCKED** -> {prior_str}"
                            else:
                                used_nav = calculated_nav
                                last_valid_nav = calculated_nav
                                source = f"FALLBACK -> {prior_str}"
                        break
            except:
                pass
    
    units = amount / used_nav
    contributor_units[contributor] += units
    total_units += units
    
    flag = "[BLOCKED]" if "BLOCKED" in source else ""
    print(f"{date_str:<12} {contributor[:20]:<20} {f'${amount:,.2f}':>12} {source:<25} {f'${calculated_nav:.4f}':>10} {f'${used_nav:.4f}':>10} {f'{units:.2f}':>10} {flag}")

print("="*110)
print("\nFINAL SUMMARY:")
print("-"*50)

latest_date = max(historical_values.keys())
current_value = historical_values[latest_date]
current_nav = current_value / total_units if total_units > 0 else 1.0

print(f"Latest date: {latest_date}")
print(f"Fund value (CAD): ${current_value:,.2f}")
print(f"Total units: {total_units:,.2f}")
print(f"Current NAV: ${current_nav:.4f}")

print("\n" + "="*110)
print("INVESTOR RETURNS (WITH SANITY CHECK):")
print("-"*110)
print(f"{'Contributor':<25} {'Net Contribution':>15} {'Units':>12} {'Value':>12} {'Return':>12} {'%':>8}")
print("-"*110)

# Get net contributions
contributor_net = {}
for contrib in contributions:
    c = contrib['contributor']
    if c not in contributor_net:
        contributor_net[c] = 0.0
    if contrib['type'] == 'withdrawal':
        contributor_net[c] -= contrib['amount']
    else:
        contributor_net[c] += contrib['amount']

for contributor, units in sorted(contributor_units.items(), key=lambda x: -x[1]):
    net = contributor_net.get(contributor, 0)
    value = units * current_nav
    gain = value - net
    pct = (gain / net * 100) if net > 0 else 0
    print(f"{contributor:<25} {f'${net:,.2f}':>15} {f'{units:,.2f}':>12} {f'${value:,.2f}':>12} {f'${gain:,.2f}':>12} {f'{pct:+.2f}%':>8}")
