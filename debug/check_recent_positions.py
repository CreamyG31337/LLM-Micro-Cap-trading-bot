
import os
import sys
from datetime import datetime, timedelta
import pandas as pd

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_recent_positions():
    client = SupabaseClient()
    
    # Get last 7 days of data
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"Fetching positions since {start_date}...")
    
    response = client.supabase.table("portfolio_positions") \
        .select("date, fund, ticker, shares, price, currency") \
        .gte("date", start_date) \
        .order("date") \
        .execute()
        
    if not response.data:
        print("No recent data found.")
        return

    df = pd.DataFrame(response.data)
    
    # Calculate market value
    df['market_value'] = df['shares'] * df['price']
    
    # Group by date and fund
    print("\nSummary by Date and Fund:")
    summary = df.groupby(['date', 'fund']).agg({
        'market_value': 'sum',
        'ticker': 'count'
    }).reset_index()
    
    summary.rename(columns={'ticker': 'position_count'}, inplace=True)
    print(summary)
    
    print("\nDetailed breakdown for today (if any):")
    today = datetime.now().strftime('%Y-%m-%d')
    today_data = df[df['date'].str.startswith(today)]
    if not today_data.empty:
        print(today_data[['date', 'fund', 'ticker', 'shares', 'price', 'market_value']])
    else:
        print(f"No data found for today ({today})")

if __name__ == "__main__":
    check_recent_positions()
