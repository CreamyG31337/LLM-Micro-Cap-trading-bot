#!/usr/bin/env python3
"""
SIMPLE PROPER NAV FIX

Key insight: Fund Value = max(Stock Value, Running Contributions)
If there's uninvested cash, fund value can't be less than what was contributed.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime, timedelta
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund = 'Project Chimera'

# Get contributions
result = client.supabase.table('fund_contributions').select(
    'contributor, amount, contribution_type, timestamp'
).eq('fund', fund).order('timestamp').execute()

contributions = []
for r in result.data:
    contributions.append({
        'contributor': r['contributor'],
        'amount': float(r['amount']),
        'type': r.get('contribution_type', 'CONTRIBUTION').lower(),
        'timestamp': r.get('timestamp')
    })

# Get historical stock values
positions_result = client.supabase.table('portfolio_positions').select(
    'date, shares, price, currency'
).eq('fund', fund).execute()

daily_stock_value = {}
if positions_result.data:
    df = pd.DataFrame(positions_result.data)
    df['date'] = pd.to_datetime(df['date'])
    df['value_cad'] = df.apply(
        lambda row: float(row['shares']) * float(row['price']) * (1.42 if row.get('currency') == 'USD' else 1.0),
        axis=1
    )
    for date_ts, value in df.groupby('date')['value_cad'].sum().items():
        daily_stock_value[date_ts.strftime('%Y-%m-%d')] = value

print("="*110)
print("SIMPLE NAV FIX: Fund Value = max(Stock Value, Running Contributions)")
print("="*110)
print(f"{'Date':<12} {'Contributor':<18} {'Amount':>10} {'RunningContribs':>15} {'StockVal':>12} {'UsedFundVal':>12} {'NAV':>8} {'Units':>10}")
print("-"*110)

total_units = 0.0
contributor_units = {}
running_contributions = 0.0
units_at_start_of_day = 0.0
last_date = None

for contrib in contributions:
    contributor = contrib['contributor']
    amount = contrib['amount']
    contrib_type = contrib['type']
    ts = contrib['timestamp']
    
    date_str = None
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
        except:
            pass
    
    # Same-day tracking
    if date_str != last_date:
        units_at_start_of_day = total_units
        last_date = date_str
    
    if contributor not in contributor_units:
        contributor_units[contributor] = 0.0
    
    if contrib_type == 'withdrawal':
        running_contributions -= amount
        continue
    
    # Get stock value (with fallback)
    stock_value = daily_stock_value.get(date_str, 0)
    if stock_value == 0 and date_str:
        for days_back in range(1, 8):
            prior = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=days_back)).strftime('%Y-%m-%d')
            if prior in daily_stock_value:
                stock_value = daily_stock_value[prior]
                break
    
    # SIMPLE FIX: Fund value is at least running contributions (money doesn't vanish)
    # Use units at start of day to prevent same-day dilution
    units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
    
    if units_for_nav == 0:
        nav = 1.0
        fund_value = 0
    else:
        # Fund value = max(stock value, what's been contributed so far)
        fund_value = max(stock_value, running_contributions)
        nav = fund_value / units_for_nav
    
    units = amount / nav
    contributor_units[contributor] += units
    total_units += units
    running_contributions += amount
    
    fixed = "*FIXED*" if stock_value < running_contributions and stock_value > 0 else ""
    print(f"{date_str:<12} {contributor[:18]:<18} {f'${amount:,.0f}':>10} {f'${running_contributions:,.0f}':>15} {f'${stock_value:,.0f}':>12} {f'${fund_value:,.0f}':>12} {f'${nav:.4f}':>8} {f'{units:.1f}':>10} {fixed}")

# Current state
latest = max(daily_stock_value.keys())
current_stock = daily_stock_value[latest]
current_fund = max(current_stock, running_contributions)
current_nav = current_fund / total_units

print("="*110)
print(f"\nCURRENT: Stock ${current_stock:,.0f}, Contributions ${running_contributions:,.0f}, Fund ${current_fund:,.0f}, Units {total_units:,.1f}, NAV ${current_nav:.4f}")
print(f"Fund Return (from NAV=1): +{((current_nav-1)/1)*100:.1f}%")

print("\nINVESTOR RETURNS:")
print("-"*80)

contrib_net = {}
for c in contributions:
    name = c['contributor']
    if name not in contrib_net:
        contrib_net[name] = 0.0
    if c['type'] == 'withdrawal':
        contrib_net[name] -= c['amount']
    else:
        contrib_net[name] += c['amount']

for name, units in sorted(contributor_units.items(), key=lambda x: -x[1]):
    net = contrib_net.get(name, 0)
    val = units * current_nav
    gain = val - net
    pct = (gain/net*100) if net > 0 else 0
    print(f"{name:<20} Contributed: ${net:>8,.0f}  Units: {units:>8,.1f}  Value: ${val:>8,.0f}  Return: {pct:>+7.2f}%")
