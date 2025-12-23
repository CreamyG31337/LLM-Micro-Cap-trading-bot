import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_table_quality():
    client = SupabaseClient()
    
    # Get recent data with all columns
    response = client.supabase.table("portfolio_positions") \
        .select("*") \
        .eq("fund", "Project Chimera") \
        .order("date", desc=True) \
        .limit(50) \
        .execute()
        
    if not response.data:
        print("No data found.")
        return

    df = pd.DataFrame(response.data)
    
    print(f"Total columns: {len(df.columns)}")
    print(f"Columns: {df.columns.tolist()}\n")
    
    # Check for suspicious values
    print("Last 10 records (most recent first):")
    print(df[['date', 'ticker', 'shares', 'price', 'cost_basis', 'currency']].head(10))
    
    print("\n\nChecking for data quality issues:")
    
    # Check for duplicates
    duplicates = df.groupby(['date', 'ticker']).size()
    dups = duplicates[duplicates > 1]
    if len(dups) > 0:
        print(f"\n⚠️  Found {len(dups)} duplicate date+ticker combinations:")
        print(dups.head(10))
    else:
        print("✅ No duplicate date+ticker combinations")
    
    # Check for null/zero values
    print(f"\n📊 Null values:")
    print(df[['shares', 'price', 'cost_basis']].isnull().sum())
    
    print(f"\n📊 Zero values:")
    print(f"  Shares = 0: {(df['shares'] == 0).sum()}")
    print(f"  Price = 0: {(df['price'] == 0).sum()}")
    print(f"  Cost basis = 0: {(df['cost_basis'] == 0).sum()}")
    
    # Check date distribution
    print(f"\n📅 Records per date (last 10 dates):")
    date_counts = df.groupby(df['date'].str[:10]).size().sort_index(ascending=False)
    print(date_counts.head(10))

if __name__ == "__main__":
    check_table_quality()
