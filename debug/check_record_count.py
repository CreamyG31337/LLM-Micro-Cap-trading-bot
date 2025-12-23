import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

response = client.supabase.table("portfolio_positions") \
    .select("date, shares, price, cost_basis", count="exact") \
    .eq("fund", "Project Chimera") \
    .order("date") \
    .limit(5000) \
    .execute()

print(f"Total records for Project Chimera: {response.count}")
print(f"Records returned: {len(response.data)}")

import pandas as pd
df = pd.DataFrame(response.data)
df['date'] = pd.to_datetime(df['date'])

unique_dates = sorted(df['date'].dt.date.unique())
print(f"\nUnique dates: {len(unique_dates)}")
print(f"First date: {unique_dates[0]}")
print(f"Last date: {unique_dates[-1]}")

print(f"\nLast 10 dates:")
for d in unique_dates[-10:]:
    print(f"  {d}")
