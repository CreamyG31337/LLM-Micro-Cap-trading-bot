import os
import sys
from datetime import datetime
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def check_first_trading_day():
    client = SupabaseClient()
    
    print("Fetching ALL portfolio positions for Project Chimera...")
    
    response = client.supabase.table("portfolio_positions") \
        .select("date, shares, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .order("date") \
        .execute()
        
    if not response.data:
        print("No data found.")
        return

    df = pd.DataFrame(response.data)
    df['date'] = pd.to_datetime(df['date'])
    df['market_value'] = df['shares'] * df['price']
    
    # Group by date
    daily = df.groupby(df['date'].dt.date).agg({
        'market_value': 'sum',
        'cost_basis': 'sum'
    }).reset_index()
    
    daily.columns = ['date', 'value', 'cost_basis']
    daily['pnl'] = daily['value'] - daily['cost_basis']
    daily['performance_pct'] = daily.apply(
        lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0.0,
        axis=1
    )
    
    print("\nFirst 10 trading days:")
    print(daily.head(10))
    
    print("\nFirst day with non-zero cost_basis:")
    first_day = daily[daily['cost_basis'] > 0].iloc[0]
    print(first_day)
    print(f"\nFirst day performance_pct: {first_day['performance_pct']:.2f}%")
    
    print("\nLast 5 trading days:")
    print(daily.tail(5))

if __name__ == "__main__":
    check_first_trading_day()
