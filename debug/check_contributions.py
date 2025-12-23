import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Get contributions for the user
fund = 'Project Chimera'

# Get total contributions
contribs = client.supabase.table('fund_contributions') \
    .select('amount, email, timestamp') \
    .eq('fund', fund) \
    .execute()

import pandas as pd
df = pd.DataFrame(contribs.data)

print(f"Total contributions to {fund}:")
print(df.groupby('email')['amount'].sum().sort_values(ascending=False))

total_contrib = df['amount'].sum()
print(f"\nTotal contributions: ${total_contrib:,.2f}")

# Get latest portfolio value
from datetime import datetime
latest_positions = client.supabase.table('portfolio_positions') \
    .select('date, shares, price, total_value_base') \
    .eq('fund', fund) \
    .order('date', desc=True) \
    .limit(100) \
    .execute()

if latest_positions.data:
    pos_df = pd.DataFrame(latest_positions.data)
    latest_date = pos_df['date'].max()
    latest_day = pos_df[pos_df['date'] == latest_date]
    
    if 'total_value_base' in latest_day.columns and latest_day['total_value_base'].notna().any():
        total_value = latest_day['total_value_base'].sum()
    else:
        total_value = (latest_day['shares'] * latest_day['price']).sum()
    
    print(f"\nLatest portfolio value ({latest_date[:10]}): ${total_value:,.2f}")
    print(f"Contribution as % of fund: {(total_contrib / total_value * 100):.1f}%")
