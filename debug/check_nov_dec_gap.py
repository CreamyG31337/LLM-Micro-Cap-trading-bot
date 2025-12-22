#!/usr/bin/env python3
"""Check the November-December gap in portfolio data"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

# Get ALL portfolio positions with created_at
all_pos = client.supabase.table('portfolio_positions')\
    .select('date, created_at')\
    .eq('fund', 'Project Chimera')\
    .order('date')\
    .execute()

pos_df = pd.DataFrame(all_pos.data)
pos_df['date_only'] = pos_df['date'].str[:10]
pos_df['created_date'] = pd.to_datetime(pos_df['created_at']).dt.date

unique_dates = sorted(pos_df['date_only'].unique())

print("="*80)
print("DATE COVERAGE ANALYSIS")
print("="*80)
print(f"\nTotal dates with data: {len(unique_dates)}")
print(f"Date range: {unique_dates[0]} to {unique_dates[-1]}")

# Check November
nov_dates = [d for d in unique_dates if d.startswith('2025-11')]
print(f"\nNovember dates: {len(nov_dates)}")
for d in nov_dates:
    print(f"  {d}")

# Check December
dec_dates = [d for d in unique_dates if d.startswith('2025-12')]
print(f"\nDecember dates: {len(dec_dates)}")
for d in dec_dates:
    print(f"  {d}")

# Check what was created when
print("\n\n" + "="*80)
print("CREATION DATES BREAKDOWN")
print("="*80)
for created_date in sorted(pos_df['created_date'].unique()):
    count = len(pos_df[pos_df['created_date'] == created_date])
    dates = sorted(pos_df[pos_df['created_date'] == created_date]['date_only'].unique())
    print(f"\nCreated {created_date}: {count} records")
    print(f"  Covers dates: {dates[0]} to {dates[-1]}")
