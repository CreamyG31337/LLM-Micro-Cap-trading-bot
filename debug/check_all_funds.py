import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Get ALL funds
all_funds = client.supabase.table('funds').select('name, is_production').execute()

print('All funds:')
for f in all_funds.data:
    prod = "PRODUCTION" if f.get('is_production') else "non-prod"
    print(f'  - {f["name"]} ({prod})')

# Count portfolio positions by fund
print('\nPortfolio positions per fund:')
positions = client.supabase.table('portfolio_positions') \
    .select('fund', count='exact') \
    .execute()

import pandas as pd
if positions.data:
    df = pd.DataFrame(positions.data)
    counts = df.groupby('fund').size()
    for fund, count in counts.items():
        print(f'  {fund}: {count} records')
else:
    print('  (no positions found)')
