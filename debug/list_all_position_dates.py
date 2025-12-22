#!/usr/bin/env python3
"""List ALL dates in portfolio_positions for Project Chimera"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd
from datetime import date, timedelta

client = SupabaseClient(use_service_role=True)

print("="*80)
print("ALL PORTFOLIO POSITION DATES FOR PROJECT CHIMERA")
print("="*80)

# Get ALL positions with pagination
all_rows = []
batch_size = 1000
offset = 0

while True:
    result = client.supabase.table('portfolio_positions')\
        .select('date')\
        .eq('fund', 'Project Chimera')\
        .order('date')\
        .range(offset, offset + batch_size - 1)\
        .execute()
    
    if not result.data:
        break
    
    all_rows.extend(result.data)
    
    if len(result.data) < batch_size:
        break
    
    offset += batch_size
    if offset > 50000:
        break

print(f"\nTotal position records: {len(all_rows)}")

# Extract unique dates
dates = sorted(set(row['date'][:10] for row in all_rows))
print(f"Unique dates: {len(dates)}")
print(f"Date range: {dates[0]} to {dates[-1]}")

print(f"\nALL dates with data:")
for d in dates:
    print(f"  {d}")

# Check for September specifically
sept_dates = [d for d in dates if d.startswith('2025-09')]
print(f"\n\nSEPTEMBER DATES: {len(sept_dates)}")
for d in sept_dates:
    print(f"  {d}")

# What September dates are MISSING?
print(f"\n\nMISSING SEPTEMBER WEEKDAYS:")
start = date(2025, 9, 1)
end = date(2025, 9, 30)
current = start
missing = []
while current <= end:
    if current.weekday() < 5:  # Weekday
        date_str = current.isoformat()
        if date_str not in dates:
            missing.append(date_str)
    current += timedelta(days=1)

for d in missing:
    print(f"  {d}")

print(f"\nTotal missing September weekdays: {len(missing)}")
