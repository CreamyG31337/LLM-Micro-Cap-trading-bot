import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_nulls():
    client = SupabaseClient()
    
    # Get recent data
    response = client.supabase.table("portfolio_positions") \
        .select("*") \
        .eq("fund", "Project Chimera") \
        .order("date", desc=True) \
        .limit(100) \
        .execute()
        
    if not response.data:
        print("No data found.")
        return

    df = pd.DataFrame(response.data)
    
    print("=== NULL VALUE ANALYSIS ===\n")
    
    # Check each column for nulls
    for col in df.columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            pct = (null_count / len(df)) * 100
            print(f"{col:20s}: {null_count:4d} nulls ({pct:5.1f}%)")
    
    print("\n=== SAMPLE OF RECENT RECORDS ===")
    print("\nCore columns:")
    print(df[['date', 'ticker', 'shares', 'price', 'cost_basis']].head(5))
    
    print("\nPre-converted base currency columns:")
    print(df[['total_value_base', 'cost_basis_base', 'pnl_base', 'base_currency']].head(5))
    
    print("\nExchange rate column:")
    print(df[['currency', 'exchange_rate']].head(5))

if __name__ == "__main__":
    check_nulls()
