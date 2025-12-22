#!/usr/bin/env python3
"""Check what historical_values has for Sept 7 and Dec 16"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

fund_name = 'Project Chimera'

# Simulate get_historical_fund_values
result = client.supabase.table('portfolio_positions')\
    .select('date, shares, price, currency')\
    .eq('fund', fund_name)\
    .gte('date', '2025-09-01')\
    .order('date')\
    .execute()

# Build historical_values dict
historical_values = {}
for row in result.data:
    date_key = row['date'][:10]  # YYYY-MM-DD format
    shares = float(row.get('shares', 0) or 0)
    price = float(row.get('price', 0) or 0)
    
    if date_key not in historical_values:
        historical_values[date_key] = 0
    
    historical_values[date_key] += shares * price

print("="*80)
print("HISTORICAL VALUES FOR KEY DATES")
print("="*80)

# Check Sept 7, Sept 8, Dec 16, Dec 19
dates_to_check = ['2025-09-07', '2025-09-08', '2025-12-16', '2025-12-19']

for d in dates_to_check:
    if d in historical_values:
        print(f"{d}: ${historical_values[d]:,.2f}")
    else:
        print(f"{d}: NO DATA")

# Show Sept 5-9 range
print("\n\nSeptember 5-9 range:")
for d in sorted(historical_values.keys()):
    if d >= '2025-09-05' and d <= '2025-09-09':
        print(f"  {d}: ${historical_values[d]:,.2f}")

# Show Dec 14-20 range
print("\n\nDecember 14-20 range:")
for d in sorted(historical_values.keys()):
    if d >= '2025-12-14' and d <= '2025-12-20':
        print(f"  {d}: ${historical_values[d]:,.2f}")
