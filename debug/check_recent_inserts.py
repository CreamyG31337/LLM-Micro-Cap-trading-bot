import os
import sys
from datetime import datetime, timedelta
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_recent_insertions():
    client = SupabaseClient()
    
    print("=== RECENTLY CREATED PORTFOLIO POSITIONS ===\n")
    
    # Get records created in last 2 hours
    two_hours_ago = (datetime.now() - timedelta(hours=2)).isoformat()
    
    response = client.supabase.table("portfolio_positions") \
        .select("date, fund, ticker, created_at, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .gte("created_at", two_hours_ago) \
        .order("created_at", desc=True) \
        .execute()
    
    if not response.data:
        print("No records created in last 2 hours")
        return
    
    df = pd.DataFrame(response.data)
    
    print(f"Found {len(df)} records created in last 2 hours:\n")
    
    # Group by date
    by_date = df.groupby(df['date'].str[:10])['ticker'].count()
    print("Records by date:")
    for date_str, count in by_date.items():
        records = df[df['date'].str.startswith(date_str)]
        created_at = records['created_at'].iloc[0]
        total_value = (records['price'] * 1).sum()  # Simplified value calc
        print(f"  {date_str}: {count} positions (created at {created_at}, est value: ${total_value:.2f})")

if __name__ == "__main__":
    check_recent_insertions()
