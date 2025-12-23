"""
Simulate what calculate_portfolio_value_over_time does to see if pagination works
"""
import os
import sys
import pandas as pd
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_dashboard'))

from web_dashboard.supabase_client import SupabaseClient

def test_with_pagination():
    client = SupabaseClient()
    fund = "Project Chimera"
    
    print("Simulating calculate_portfolio_value_over_time pagination logic...")
    print("=" * 60)
    
    # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
    all_rows = []
    batch_size = 1000
    offset = 0
    
    while True:
        print(f"\nFetching batch at offset {offset}...")
        
        query = client.supabase.table("portfolio_positions").select(
            "date, ticker, shares, price, cost_basis, fund"
        )
        
        query = query.eq("fund", fund)
        
        result = query.order("date").range(offset, offset + batch_size - 1).execute()
        
        rows = result.data
        print(f"  Got {len(rows)} rows")
        
        if not rows:
            break
            
        all_rows.extend(rows)
        
        # If we got fewer rows than batch_size, we're done
        if len(rows) < batch_size:
            print(f"  Last batch (only {len(rows)} rows) - pagination complete")
            break
            
        offset += batch_size
        
        # Safety break
        if offset > 50000:
            print("Warning: Reached safety limit")
            break
    
    print(f"\n" + "=" * 60)
    print(f"Total rows fetched: {len(all_rows)}")
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        df['date'] = pd.to_datetime(df['date'])
        
        unique_dates = sorted(df['date'].dt.date.unique())
        print(f"Unique dates: {len(unique_dates)}")
        print(f"Date range: {unique_dates[0]} to {unique_dates[-1]}")
        
        print(f"\nLast 10 dates:")
        for d in unique_dates[-10:]:
            print(f"  {d}")

if __name__ == "__main__":
    test_with_pagination()
