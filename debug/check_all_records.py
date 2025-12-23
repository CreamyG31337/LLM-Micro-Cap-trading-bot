import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Fetch ALL records using .range() to bypass limit
response = client.supabase.table("portfolio_positions") \
    .select("date, shares, price, cost_basis") \
    .eq("fund", "Project Chimera") \
    .order("date") \
    .range(0, 2000) \
    .execute()

print(f"Records returned: {len(response.data)}")

import pandas as pd
df = pd.DataFrame(response.data)
df['date'] = pd.to_datetime(df['date'])

unique_dates = sorted(df['date'].dt.date.unique())
print(f"Unique dates: {len(unique_dates)}")
print(f"First date: {unique_dates[0]}")
print(f"Last date: {unique_dates[-1]}")

print(f"\nLast 15 dates:")
for d in unique_dates[-15:]:
    print(f"  {d}")
