#!/usr/bin/env python3
"""Simpler NAV approach - what is the actual fund return from first to last?"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get portfolio values
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

df = pd.DataFrame(all_rows)
df['date'] = pd.to_datetime(df['date']).dt.date
df['value'] = df['shares'].astype(float) * df['price'].astype(float)
portfolio_by_date = df.groupby('date')['value'].sum().to_dict()

# Get cost_basis by date (what was actually invested in stocks)
cost_rows = []
offset = 0
while True:
    result = client.supabase.table("portfolio_positions").select(
        "date, cost_basis"
    ).eq("fund", fund_name).gte("date", '2025-09-01').order("date").range(offset, offset + batch_size - 1).execute()
    
    if not result.data:
        break
    cost_rows.extend(result.data)
    if len(result.data) < batch_size:
        break
    offset += batch_size

df2 = pd.DataFrame(cost_rows)
df2['date'] = pd.to_datetime(df2['date']).dt.date
df2['cost_basis'] = df2['cost_basis'].astype(float)
cost_by_date = df2.groupby('date')['cost_basis'].sum().to_dict()

print("="*80)
print("SIMPLER APPROACH: Portfolio Value vs Cost Basis")
print("="*80)
print("\nThis shows proper investment return - how much your actual stock picks gained")

sorted_dates = sorted(portfolio_by_date.keys())

# Normalize first day to 100
first_date = sorted_dates[0]
first_value = portfolio_by_date[first_date]
first_cost = cost_by_date.get(first_date, 0)

print("\nFirst 10:")
for d in sorted_dates[:10]:
    value = portfolio_by_date[d]
    cost = cost_by_date.get(d, 0)
    pnl_pct = ((value - cost) / cost * 100) if cost > 0 else 0
    index = (value / first_value * 100) if first_value > 0 else 100
    print(f"  {d}: value=${value:,.2f}, cost=${cost:,.2f}, P&L={pnl_pct:+.1f}%, value_index={index:.1f}")

print("\nLast 5:")
for d in sorted_dates[-5:]:
    value = portfolio_by_date[d]
    cost = cost_by_date.get(d, 0)
    pnl_pct = ((value - cost) / cost * 100) if cost > 0 else 0
    index = (value / first_value * 100) if first_value > 0 else 100
    print(f"  {d}: value=${value:,.2f}, cost=${cost:,.2f}, P&L={pnl_pct:+.1f}%, value_index={index:.1f}")

last_date = sorted_dates[-1]
last_value = portfolio_by_date[last_date]
last_cost = cost_by_date.get(last_date, 0)

print(f"\nOverall P&L: {((last_value - last_cost) / last_cost * 100):+.2f}%")
print(f"Cost basis: ${last_cost:,.2f}")
print(f"Current value: ${last_value:,.2f}")
