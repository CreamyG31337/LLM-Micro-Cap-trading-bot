import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_september():
    client = SupabaseClient()
    
    # Check for September data
    response = client.supabase.table("portfolio_positions") \
        .select("date, fund, ticker, shares, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .gte("date", "2025-09-01") \
        .lt("date", "2025-10-01") \
        .execute()
        
    print(f"September records: {len(response.data) if response.data else 0}")
    
    if response.data:
        df = pd.DataFrame(response.data)
        df['date'] = pd.to_datetime(df['date'])
        
        unique_dates = sorted(df['date'].dt.date.unique())
        print(f"\nSeptember dates ({len(unique_dates)}):")
        for date in unique_dates:
            print(f"  {date}")
            
        # Check values for first day
        first_day = df[df['date'].dt.date == unique_dates[0]]
        print(f"\nFirst day ({unique_dates[0]}) has {len(first_day)} positions")
        print(f"Total cost basis: ${first_day['cost_basis'].sum():.2f}")
        print(f"Total value: ${(first_day['shares'] * first_day['price']).sum():.2f}")
    else:
        print("No September data found!")

if __name__ == "__main__":
    check_september()
