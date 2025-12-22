#!/usr/bin/env python3
"""Debug the NAV calculation to see what's wrong"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd
from datetime import datetime, timedelta

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get contributions
contribs = client.supabase.table('fund_contributions').select(
    'timestamp, amount, contribution_type'
).eq('fund', fund_name).order('timestamp').execute()

print(f"Contributions: {len(contribs.data)}")

# Get historical values
from streamlit_utils import get_historical_fund_values
contrib_dates = [pd.to_datetime(c['timestamp']) for c in contribs.data if c['timestamp']]
historical_values = get_historical_fund_values(fund_name, contrib_dates)

print(f"Historical values: {len(historical_values)} dates")
print(f"Sample historical values: {list(historical_values.items())[:5]}")

# Calculate units like the function does
total_units = 0.0
units_at_start_of_day = 0.0
last_contribution_date = None
date_to_units = {}

for record in contribs.data:
    timestamp = pd.to_datetime(record['timestamp']) if record['timestamp'] else None
    amount = float(record.get('amount', 0))
    contrib_type = record.get('contribution_type', 'CONTRIBUTION').lower()
    
    if not timestamp:
        continue
    
    date_str = timestamp.strftime('%Y-%m-%d')
    
    if date_str != last_contribution_date:
        units_at_start_of_day = total_units
        last_contribution_date = date_str
    
    if contrib_type != 'withdrawal':
        if total_units == 0:
            nav = 1.0
        elif date_str in historical_values:
            units_for_nav = units_at_start_of_day if units_at_start_of_day > 0 else total_units
            nav = historical_values[date_str] / units_for_nav if units_for_nav > 0 else 1.0
        else:
            nav = 1.0
        
        units = amount / nav if nav > 0 else 0
        total_units += units
    
    date_obj = timestamp.date()
    date_to_units[date_obj] = total_units

print(f"\nDate to units mapping ({len(date_to_units)} entries):")
for d, u in sorted(date_to_units.items()):
    print(f"  {d}: {u:.4f} units")

# Get portfolio data
result = client.supabase.table('portfolio_positions').select(
    'date, total_value'
).eq('fund', fund_name).order('date').limit(10).execute()

print(f"\nFirst 10 portfolio dates:")
for row in result.data[:10]:
    date_obj = pd.to_datetime(row['date']).date()
    # Find units at this date
    units = 0.0
    for contrib_date in sorted([d for d in date_to_units.keys() if d <= date_obj], reverse=True):
        units = date_to_units[contrib_date]
        break
    print(f"  {date_obj}: value=?, units={units:.4f}")
