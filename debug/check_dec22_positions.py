#!/usr/bin/env python3
"""Check what dates exist in portfolio_positions and when they were created"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd
from datetime import datetime, timezone

client = SupabaseClient(use_service_role=True)

# Get the most recent portfolio positions to see what dates exist
result = client.supabase.table('portfolio_positions').select(
    'date, created_at, fund'
).order('date', desc=True).limit(20).execute()

print("="*80)
print("MOST RECENT PORTFOLIO POSITIONS")
print("="*80)
print(f"Current time: {datetime.now(timezone.utc)} UTC")
print(f"Current time: {datetime.now()} local\n")

if result.data:
    df = pd.DataFrame(result.data)
    df['date'] = pd.to_datetime(df['date'])
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # Group by date and show when each date's positions were created
    for date in df['date'].unique()[:5]:
        date_rows = df[df['date'] == date]
        print(f"\nDate: {date}")
        print(f"  Rows: {len(date_rows)}")
        print(f"  Funds: {date_rows['fund'].unique().tolist()}")
        print(f"  Created at: {date_rows['created_at'].min()} to {date_rows['created_at'].max()}")
        
        # Check if this is a future date
        if date.date() > datetime.now(timezone.utc).date():
            print(f"  ⚠️  WARNING: This is a FUTURE date!")

# Also check what the dashboard would show
print("\n" + "="*80)
print("CHECKING DASHBOARD DISPLAY LOGIC")
print("="*80)

# Get latest position date per fund
latest = client.supabase.table('portfolio_positions').select(
    'fund, date'
).order('date', desc=True).execute()

if latest.data:
    df2 = pd.DataFrame(latest.data)
    df2['date'] = pd.to_datetime(df2['date'])
    
    for fund in df2['fund'].unique():
        fund_latest = df2[df2['fund'] == fund]['date'].max()
        print(f"\n{fund}:")
        print(f"  Latest position date: {fund_latest}")
        print(f"  Display would show: {fund_latest.strftime('%b %d, %-I %p' if fund_latest.hour != 0 else '%b %d')}")
