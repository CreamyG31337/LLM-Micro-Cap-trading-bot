#!/usr/bin/env python3
"""Calculate correct fund return"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get all contributions
contribs = client.supabase.table('fund_contributions')\
    .select('*')\
    .eq('fund', fund_name)\
    .execute()

total_contributed = sum(float(c['amount']) for c in contribs.data)

# Get latest portfolio value
latest_pos = client.supabase.table('portfolio_positions')\
    .select('*')\
    .eq('fund', fund_name)\
    .order('date', desc=True)\
    .limit(100)\
    .execute()

df = pd.DataFrame(latest_pos.data)
latest_date = df['date'].max()
latest_df = df[df['date'] == latest_date]

# Check for duplicates again
duplicates = latest_df.groupby('ticker').size()
duplicates = duplicates[duplicates > 1]

if len(duplicates) > 0:
    print(f"!! WARNING: {len(duplicates)} duplicate tickers on {latest_date}")

portfolio_value = (latest_df['shares'].astype(float) * latest_df['price'].astype(float)).sum()

# Get cash
cash_res = client.supabase.table('cash_balances')\
    .select('*')\
    .eq('fund', fund_name)\
    .execute()

total_cash = 0
for row in cash_res.data:
    currency = row.get('currency', 'CAD')
    balance = float(row.get('balance', 0))
    if currency == 'USD':
        # Use rough conversion
        balance *= 1.42
    total_cash += balance

total_value = portfolio_value + total_cash

print("="*80)
print("ACTUAL FUND METRICS")
print("="*80)
print(f"Latest date: {latest_date}")
print(f"Portfolio value: ${portfolio_value:,.2f}")
print(f"Cash: ${total_cash:,.2f}")
print(f"Total fund value: ${total_value:,.2f}")
print(f"\nTotal contributed: ${total_contributed:,.2f}")
print(f"Return: ${total_value - total_contributed:,.2f}")
print(f"Return %: {((total_value - total_contributed) / total_contributed * 100):.2f}%")
