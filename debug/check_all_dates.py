import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_all_dates():
    client = SupabaseClient()
    
    response = client.supabase.table("portfolio_positions") \
        .select("date") \
        .eq("fund", "Project Chimera") \
        .execute()
        
    if not response.data:
        print("No data found.")
        return

    df = pd.DataFrame(response.data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Get unique dates
    unique_dates = sorted(df['date'].dt.date.unique())
    
    print(f"Total unique dates: {len(unique_dates)}")
    print("\nAll dates:")
    for date in unique_dates:
        print(f"  {date}")

if __name__ == "__main__":
    check_all_dates()
