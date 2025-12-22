#!/usr/bin/env python3
"""Calculate NAV correctly with proper timing"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd
from datetime import datetime, timedelta, time as dt_time, timezone

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Step 1: Get portfolio values by date
all_rows = []
offset = 0
batch_size = 1000

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

# Calculate daily portfolio values
df = pd.DataFrame(all_rows)
df['date'] = pd.to_datetime(df['date']).dt.date
df['value'] = df['shares'].astype(float) * df['price'].astype(float)
portfolio_by_date = df.groupby('date')['value'].sum().to_dict()

print(f"Portfolio dates: {len(portfolio_by_date)}")

# Step 2: Get contributions with timestamps
contribs = client.supabase.table('fund_contributions').select(
    'timestamp, amount, contribution_type'
).eq('fund', fund_name).order('timestamp').execute()

# Build historical_values dict
historical_values = {}
for date_obj, value in portfolio_by_date.items():
    date_str = date_obj.strftime('%Y-%m-%d')
    historical_values[date_str] = value

# Step 3: Calculate total_units at each snapshot time (4 PM UTC)
# Only count contributions made BEFORE 4 PM UTC on that date
SNAPSHOT_HOUR_UTC = 16  # 4 PM UTC = market close (12 PM ET / 9 AM PT during winter)

total_units = 0.0
units_at_start_of_day = 0.0
last_contribution_date = None
date_to_units_at_snapshot = {}  # Maps date -> units at 4 PM snapshot time

sorted_contribs = sorted(contribs.data, key=lambda r: r['timestamp'])

for record in sorted_contribs:
    timestamp = pd.to_datetime(record['timestamp'])
    amount = float(record.get('amount', 0))
    contrib_type = record.get('contribution_type', 'CONTRIBUTION').lower()
    
    date_obj = timestamp.date()
    date_str = date_obj.strftime('%Y-%m-%d')
    
    # Check if this contribution was before or after snapshot time
    hour = timestamp.hour
    
    # Same-day NAV fix
    if date_str != last_contribution_date:
        units_at_start_of_day = total_units
        last_contribution_date = date_str
    
    if contrib_type == 'withdrawal':
        if date_str in historical_values and units_at_start_of_day > 0:
            nav = historical_values[date_str] / units_at_start_of_day
            units_to_redeem = amount / nav if nav > 0 else 0
            total_units = max(0, total_units - units_to_redeem)
    else:
        if total_units == 0:
            nav = 1.0
        elif date_str in historical_values:
            units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
            nav = historical_values[date_str] / units_for_nav if units_for_nav > 0 else 1.0
        else:
            nav = 1.0
            for days_back in range(1, 8):
                prior_date = date_obj - timedelta(days=days_back)
                prior_date_str = prior_date.strftime('%Y-%m-%d')
                units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
                if prior_date_str in historical_values and units_for_nav > 0:
                    nav = historical_values[prior_date_str] / units_for_nav
                    break
        
        units = amount / nav if nav > 0 else 0
        total_units += units
        
        # Only record snapshot units if this contribution was BEFORE 4 PM UTC
        # Contributions after 4 PM don't affect today's snapshot, they affect tomorrow's
        if hour < SNAPSHOT_HOUR_UTC:
            date_to_units_at_snapshot[date_obj] = total_units
    
    # Always update the date_to_units_at_snapshot for this date if we haven't yet
    if date_obj not in date_to_units_at_snapshot:
        # First contribution of the day (before processing) - use units_at_start_of_day
        date_to_units_at_snapshot[date_obj] = units_at_start_of_day

print(f"\nUnits at snapshot time by date:")
for d in sorted(date_to_units_at_snapshot.keys()):
    print(f"  {d}: {date_to_units_at_snapshot[d]:.2f} units")

# Step 4: For each portfolio date, find the units at snapshot time
sorted_snapshot_dates = sorted(date_to_units_at_snapshot.keys())
final_total_units = total_units  # Ultimate total after all contributions

def get_units_at_snapshot(target_date):
    """Get total_units that were valid at 4 PM snapshot on this date"""
    result = 0.0
    for snap_date in sorted_snapshot_dates:
        if snap_date <= target_date:
            result = date_to_units_at_snapshot[snap_date]
        else:
            break
    # If target_date is after all contribution dates, use final total
    if target_date > sorted_snapshot_dates[-1] if sorted_snapshot_dates else True:
        result = final_total_units
    return result

print("\n" + "="*80)
print("NAV OVER TIME (TIMING-CORRECTED)")
print("="*80)

nav_data = []
for date_obj in sorted(portfolio_by_date.keys()):
    portfolio_value = portfolio_by_date[date_obj]
    units = get_units_at_snapshot(date_obj)
    
    if units > 0:
        nav = portfolio_value / units
    else:
        nav = 1.0
    
    nav_data.append({
        'date': date_obj,
        'value': portfolio_value,
        'units': units,
        'nav': nav
    })

# Normalize to start at 100
if nav_data:
    first_nav = nav_data[0]['nav']
    for item in nav_data:
        item['nav_index'] = (item['nav'] / first_nav) * 100 if first_nav > 0 else 100

# Print first 10 and last 5
print("\nFirst 10 dates:")
for item in nav_data[:10]:
    print(f"  {item['date']}: value=${item['value']:,.2f}, units={item['units']:.2f}, NAV=${item['nav']:.4f}, index={item['nav_index']:.2f}")

print("\nLast 5 dates:")
for item in nav_data[-5:]:
    print(f"  {item['date']}: value=${item['value']:,.2f}, units={item['units']:.2f}, NAV=${item['nav']:.4f}, index={item['nav_index']:.2f}")

# Calculate overall NAV return
if nav_data:
    first_nav = nav_data[0]['nav']
    last_nav = nav_data[-1]['nav']
    nav_return = ((last_nav / first_nav) - 1) * 100 if first_nav > 0 else 0
    print(f"\nNAV Return: {nav_return:+.2f}%")
    print(f"First NAV: ${first_nav:.4f}")
    print(f"Last NAV: ${last_nav:.4f}")
