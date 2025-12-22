#!/usr/bin/env python3
"""Check what the graph would actually show"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get historical portfolio values (what graph uses)
all_rows = []
batch_size = 1000
offset = 0

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

df = pd.DataFrame(all_rows)
df['date'] = pd.to_datetime(df['date']).dt.date
df['value'] = df['shares'].astype(float) * df['price'].astype(float)

# Group by date and sum
daily_values = df.groupby('date')['value'].sum().sort_index()

print("="*80)
print("PORTFOLIO VALUE OVER TIME (WHAT GRAPH SHOWS)")
print("="*80)

first_date = daily_values.index[0]
last_date = daily_values.index[-1]
first_value = daily_values.iloc[0]
last_value = daily_values.iloc[-1]

print(f"\nFirst date: {first_date} = ${first_value:,.2f}")
print(f"Last date:  {last_date} = ${last_value:,.2f}")
print(f"\nChange: ${last_value - first_value:,.2f}")
print(f"Return: {((last_value - first_value) / first_value * 100):.2f}%")

print(f"\nAll dates and values:")
for date, value in daily_values.items():
    print(f"  {date}: ${value:,.2f}")
