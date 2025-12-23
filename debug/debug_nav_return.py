#!/usr/bin/env python3
"""Debug NAV calculation to verify user return is correct"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from decimal import Decimal
from datetime import datetime
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund = 'Project Chimera'
user_email = 'lance@lancecolt.com'

print("="*80)
print("DEBUGGING NAV CALCULATION")
print("="*80)

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

# Get historical values
positions_result = client.supabase.table('portfolio_positions').select(
    'date, shares, price'
).eq('fund', fund).execute()

historical_values = {}
if positions_result.data:
    df = pd.DataFrame(positions_result.data)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = df['shares'].astype(float) * df['price'].astype(float)
    daily = df.groupby('date')['value'].sum()
    for date, value in daily.items():
        historical_values[date.strftime('%Y-%m-%d')] = value

print(f"\nContributions: {len(contributions)}")
print(f"Historical dates: {len(historical_values)}")

# Calculate NAV for each contribution
total_units = 0.0
contributor_units = {}
contributor_data = {}
units_at_start_of_day = 0.0
last_contribution_date = None

print("\n" + "="*80)
print("NAV CALCULATION TRACE")
print("="*80)

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
        contributor_data[contributor] = {'net': 0.0, 'email': contrib['email']}
    
    if contrib_type == 'withdrawal':
        contributor_data[contributor]['net'] -= amount
        if total_units > 0 and contributor_units[contributor] > 0:
            nav = 1.0
            units_redeemed = min(amount / nav, contributor_units[contributor])
            contributor_units[contributor] -= units_redeemed
            total_units -= units_redeemed
    else:
        contributor_data[contributor]['net'] += amount
        
        # Calculate NAV
        if total_units == 0:
            nav = 1.0
            source = "FIRST"
        elif date_str and date_str in historical_values:
            fund_value = historical_values[date_str]
            units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
            nav = fund_value / units_for_nav if units_for_nav > 0 else 1.0
            source = f"HISTORICAL ({date_str})"
        else:
            # Weekend fallback
            nav = 1.0
            source = "FALLBACK"
            units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
            if date_str and units_for_nav > 0:
                try:
                    from datetime import timedelta
                    contrib_date = datetime.strptime(date_str, '%Y-%m-%d')
                    for days_back in range(1, 8):
                        prior = contrib_date - timedelta(days=days_back)
                        prior_str = prior.strftime('%Y-%m-%d')
                        if prior_str in historical_values:
                            nav = historical_values[prior_str] / units_for_nav
                            source = f"FALLBACK -> {prior_str}"
                            break
                except:
                    pass
        
        units = amount / nav
        contributor_units[contributor] += units
        total_units += units
        
        # Print trace for Lance
        if 'lance' in contributor.lower() or 'colton' in contributor.lower():
            print(f"\n{date_str}: Lance contributes ${amount:,.2f}")
            print(f"  Source: {source}")
            print(f"  Units at start of day: {units_at_start_of_day:.4f}")
            print(f"  Total units before: {total_units - units:.4f}")
            print(f"  NAV: ${nav:.4f}")
            print(f"  Units purchased: {units:.4f}")
            print(f"  Total units after: {total_units:.4f}")

# Get current fund value
latest_date = max(historical_values.keys())
current_value = historical_values[latest_date]
print(f"\n" + "="*80)
print(f"CURRENT STATE (as of {latest_date})")
print("="*80)
print(f"Fund value: ${current_value:,.2f}")
print(f"Total units: {total_units:.4f}")
current_nav = current_value / total_units if total_units > 0 else 1.0
print(f"Current NAV: ${current_nav:.4f}")

# Find Lance
print(f"\n" + "="*80)
print("LANCE'S METRICS")
print("="*80)
for contributor, units in contributor_units.items():
    if 'lance' in contributor.lower() or 'colton' in contributor.lower():
        data = contributor_data[contributor]
        net = data['net']
        value = units * current_nav
        gain = value - net
        pct = (gain / net * 100) if net > 0 else 0
        ownership = (units / total_units * 100) if total_units > 0 else 0
        
        print(f"Contributor: {contributor}")
        print(f"Net contributed: ${net:,.2f}")
        print(f"Units owned: {units:.4f}")
        print(f"Current value: ${value:,.2f}")
        print(f"Gain/Loss: ${gain:,.2f} ({pct:+.2f}%)")
        print(f"Ownership: {ownership:.2f}%")
        
        # Average NAV paid
        avg_nav = net / units if units > 0 else 0
        print(f"Average NAV paid: ${avg_nav:.4f}")
        print(f"Current NAV: ${current_nav:.4f}")
        nav_gain_pct = ((current_nav / avg_nav) - 1) * 100 if avg_nav > 0 else 0
        print(f"NAV change: {nav_gain_pct:+.2f}%")
