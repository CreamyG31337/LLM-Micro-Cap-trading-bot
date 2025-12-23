import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def full_table_check():
    client = SupabaseClient()
    
    # Get count of all records by fund
    print("=== RECORD COUNTS BY FUND ===")
    response = client.supabase.table("portfolio_positions") \
        .select("fund", count="exact") \
        .execute()
    
    df_all = pd.DataFrame(response.data)
    if not df_all.empty:
        fund_counts = df_all.groupby('fund').size()
        for fund, count in fund_counts.items():
            print(f"{fund}: {count} records")
    
    print(f"\nTotal records across all funds: {response.count}")
    
    # Check for Dec 22 specifically
    print("\n=== DEC 22 CHECK ===")
    dec22_response = client.supabase.table("portfolio_positions") \
        .select("*", count="exact") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    print(f"Dec 22 records found: {dec22_response.count}")
    
    if dec22_response.data:
        dec22_df = pd.DataFrame(dec22_response.data)
        print("\nDec 22 records by fund:")
        print(dec22_df.groupby('fund').size())
        
        print("\nDec 22 sample records:")
        print(dec22_df[['id', 'fund', 'date', 'ticker', 'created_at']].head())
    
    # Check the most recent actual trading day
    print("\n=== MOST RECENT TRADING DAY ===")
    latest = client.supabase.table("portfolio_positions") \
        .select("date") \
        .eq("fund", "Project Chimera") \
        .order("date", desc=True) \
        .limit(1) \
        .execute()
    
    if latest.data:
        print(f"Most recent date: {latest.data[0]['date']}")

if __name__ == "__main__":
    full_table_check()
