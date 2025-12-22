#!/usr/bin/env python3
"""Debug: Check what get_historical_fund_values returns vs what's in portfolio_positions"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime
import pandas as pd

client = SupabaseClient(use_service_role=True)

# Lance's contribution dates (from earlier)
contribution_dates = [
    '2025-09-07',
    '2025-09-08',
    '2025-09-12',
    '2025-09-15',
    '2025-09-16',
    '2025-12-16',
]

print("="*80)
print("CHECKING PORTFOLIO VALUES FOR EACH CONTRIBUTION DATE")
print("="*80)

# Get all portfolio positions
all_pos = client.supabase.table('portfolio_positions')\
    .select('date, shares, price, currency, ticker')\
    .eq('fund', 'Project Chimera')\
    .order('date')\
    .execute()

pos_df = pd.DataFrame(all_pos.data)
pos_df['date_only'] = pos_df['date'].str[:10]

# Check each contribution date
for date_str in sorted(set(contribution_dates)):
    matches = pos_df[pos_df['date_only'] == date_str]
    
    if len(matches) > 0:
        total = (matches['shares'].astype(float) * matches['price'].astype(float)).sum()
        print(f"\n{date_str}: {len(matches)} positions, total value = ${total:,.2f}")
    else:
        print(f"\n{date_str}: NO DATA - checking closest prior date...")
        prior = pos_df[pos_df['date_only'] < date_str]
        if len(prior) > 0:
            closest = prior['date_only'].max()
            closest_matches = pos_df[pos_df['date_only'] == closest]
            total = (closest_matches['shares'].astype(float) * closest_matches['price'].astype(float)).sum()
            print(f"  Closest prior: {closest} with ${total:,.2f}")
        else:
            print(f"  No prior data found!")

# Check the date format
print("\n\n" + "="*80)
print("DATE FORMAT CHECK")
print("="*80)
print(f"Sample date values: {pos_df['date'].head(3).tolist()}")
print(f"Sample date_only: {pos_df['date_only'].head(3).tolist()}")

# Check if Sep 7 exists
print("\n\n" + "="*80)
print("SEPTEMBER 7 SPECIFIC CHECK")
print("="*80)
sep7 = pos_df[pos_df['date_only'] == '2025-09-07']
print(f"Rows matching 2025-09-07: {len(sep7)}")

# What dates around Sep 7 exist?
around_sep7 = pos_df[(pos_df['date_only'] >= '2025-09-05') & (pos_df['date_only'] <= '2025-09-09')]
print(f"\nDates from Sep 5-9:")
print(sorted(around_sep7['date_only'].unique()))
