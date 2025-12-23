import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def analyze_current_data():
    client = SupabaseClient()
    
    print("=== CURRENT DATA STATE FOR PROJECT CHIMERA ===\n")
    
    # Get all unique dates
    response = client.supabase.table("portfolio_positions") \
        .select("date") \
        .eq("fund", "Project Chimera") \
        .execute()
    
    df = pd.DataFrame(response.data)
    df['date_only'] = pd.to_datetime(df['date']).dt.date
    unique_dates = sorted(df['date_only'].unique())
    
    print(f"Total unique dates: {len(unique_dates)}")
    print(f"Date range: {unique_dates[0]} to {unique_dates[-1]}")
    
    # Check if Dec 22 exists
    from datetime import date
    dec_22 = date(2025, 12, 22)
    
    if dec_22 in unique_dates:
        print(f"\n⚠️  Dec 22 data EXISTS")
        
        # Get Dec 22 details
        dec22_response = client.supabase.table("portfolio_positions") \
            .select("ticker, price, cost_basis, created_at") \
            .eq("fund", "Project Chimera") \
            .gte("date", "2025-12-22T00:00:00") \
            .lt("date", "2025-12-23T00:00:00") \
            .execute()
        
        dec22_df = pd.DataFrame(dec22_response.data)
        print(f"  {len(dec22_df)} positions")
        print(f"  Created at: {dec22_df['created_at'].iloc[0]}")
        
        # Compare to Dec 19
        dec19_response = client.supabase.table("portfolio_positions") \
            .select("ticker, price, cost_basis") \
            .eq("fund", "Project Chimera") \
            .gte("date", "2025-12-19T00:00:00") \
            .lt("date", "2025-12-20T00:00:00") \
            .execute()
        
        dec19_df = pd.DataFrame(dec19_response.data)
        
        # Check if prices match (indicating stale data)
        dec22_total = dec22_df['price'].sum()
        dec19_total = dec19_df['price'].sum()
        
        print(f"\n  Dec 22 total price: ${dec22_total:.2f}")
        print(f"  Dec 19 total price: ${dec19_total:.2f}")
        
        if abs(dec22_total - dec19_total) < 1.0:
            print("  🚨 PRICES ARE IDENTICAL - STALE DATA DETECTED!")
        else:
            print("  ✅ Prices differ - looks like live data")
    else:
        print(f"\n✅ No Dec 22 data (as expected after deletion)")
    
    # Check last 5 dates
    print(f"\nLast 5 trading days:")
    for d in unique_dates[-5:]:
        count_resp = client.supabase.table("portfolio_positions") \
            .select("count", count="exact") \
            .eq("fund", "Project Chimera") \
            .gte("date", f"{d}T00:00:00") \
            .lt("date", f"{d}T23:59:59") \
            .execute()
        print(f"  {d}: {count_resp.count} positions")

if __name__ == "__main__":
    analyze_current_data()
