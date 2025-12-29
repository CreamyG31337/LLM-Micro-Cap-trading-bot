import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

# Get all Dwight Evans trades (search by politician name)
result = client.supabase.table('congress_trades')\
    .select('*')\
    .ilike('politician', '%dwight%evans%')\
    .execute()

print(f"Total Dwight Evans trades: {len(result.data)}")
print()

# Convert to DataFrame for easier analysis
df = pd.DataFrame(result.data)

if len(df) > 0:
   # Group by unique constraint fields to find duplicates
    print("Checking for duplicates based on unique constraint:")
    print("(politician, ticker, transaction_date, amount, type, owner)")
    print()
    
    # Create a composite key
    df['composite_key'] = df.apply(
        lambda x: (x['politician'], x['ticker'], str(x['transaction_date']), 
                   x['amount'], x['type'], x.get('owner')), 
        axis=1
    )
    
    # Find duplicates
    duplicates = df[df.duplicated(subset='composite_key', keep=False)]
    
    if len(duplicates) > 0:
        print(f"⚠️ Found {len(duplicates)} duplicate trades!")
        print()
        print("Duplicate records:")
        print(duplicates[['id', 'transaction_date', 'ticker', 'type', 'amount', 
                          'owner', 'state', 'party', 'created_at']].sort_values('id').to_string(index=False))
        print()
        
        # Show which records have missing fields
        print("Records with missing data columns:")
        cols_to_check = ['state', 'party', 'owner']
        for col in cols_to_check:
            missing = duplicates[duplicates[col].isna() | (duplicates[col] == '')]
            if len(missing) > 0:
                print(f"  {col}: {len(missing)} records missing")
                print(f"    IDs: {sorted(missing['id'].tolist())}")
    else:
        print("✅ No duplicates found based on unique constraint")
        print()
        print("Sample trades:")
        print(df[['id', 'transaction_date', 'ticker', 'type', 'amount', 
                  'owner', 'state', 'party']].head(10).to_string(index=False))
else:
    print("No trades found for Dwight Evans")
