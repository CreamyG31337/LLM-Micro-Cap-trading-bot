import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Check for duplicate positions
positions = client.supabase.table('portfolio_positions') \
    .select('date, ticker, fund, shares, price') \
    .eq('fund', 'Project Chimera') \
    .execute()

df = pd.DataFrame(positions.data)
df['date_key'] = pd.to_datetime(df['date']).dt.date

# Find duplicates
duplicates = df.groupby(['date_key', 'ticker']).size().reset_index(name='count')
dupes = duplicates[duplicates['count'] > 1]

print(f"Total positions: {len(df)}")
print(f"Unique date+ticker combinations: {len(duplicates)}")
print(f"Duplicate date+ticker combinations: {len(dupes)}")

if len(dupes) > 0:
    print("\nDUPLICATES FOUND:")
    print(dupes.head(10))
    
    # Show example
    example = dupes.iloc[0]
    example_records = df[(df['date_key'] == example['date_key']) & (df['ticker'] == example['ticker'])]
    print(f"\nExample duplicate for {example['ticker']} on {example['date_key']}:")
    print(example_records[['date', 'ticker', 'shares', 'price']])
else:
    print("\nNo duplicates found - data looks clean")
