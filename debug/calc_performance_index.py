"""
Calculate performance index exactly like streamlit_utils does to see what baseline it gets
"""
import os  
import sys
import pandas as pd
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'web_dashboard'))

from web_dashboard.supabase_client import SupabaseClient

def calculate_like_dashboard():
    client = SupabaseClient()
    fund = "Project Chimera"
    
    # Fetch ALL data with pagination
    all_rows = []
    batch_size = 1000
    offset = 0
    
    while True:
        result = client.supabase.table("portfolio_positions").select(
            "date, shares, price, cost_basis"
        ).eq("fund", fund).order("date").range(offset, offset + batch_size - 1).execute()
        
        if not result.data:
            break
        all_rows.extend(result.data)
        if len(result.data) < batch_size:
            break
        offset += batch_size
    
    print(f"Fetched {len(all_rows)} records")
    
    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = df['shares'] * df['price']
    
    # Group by date (like the dashboard does)
    daily_totals = df.groupby(df['date'].dt.date).agg({
        'value': 'sum',
        'cost_basis': 'sum'
    }).reset_index()
    
    daily_totals.columns = ['date', 'value', 'cost_basis']
    daily_totals['date'] = pd.to_datetime(daily_totals['date'])
    daily_totals = daily_totals.sort_values('date').reset_index(drop=True)
    
    daily_totals['pnl'] = daily_totals['value'] - daily_totals['cost_basis']
    daily_totals['performance_pct'] = daily_totals.apply(
        lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0.0,
        axis=1
    )
    
    # THIS IS THE KEY NORMALIZATION LOGIC
    first_day_with_investment = daily_totals[daily_totals['cost_basis'] > 0]
    if not first_day_with_investment.empty:
        first_day_performance = first_day_with_investment.iloc[0]['performance_pct']
        daily_totals['performance_pct'] = daily_totals['performance_pct'] - first_day_performance
    
    daily_totals['performance_index'] = 100 + daily_totals['performance_pct']
    
    print(f"\nTotal days: {len(daily_totals)}")
    print(f"First day: {daily_totals.iloc[0]['date'].date()}")
    print(f"Last day: {daily_totals.iloc[-1]['date'].date()}")
    print(f"\nFirst day performance before norm: {first_day_performance:.2f}%")
    print(f"\nPerformance Index:")
    print(f"  First: {daily_totals['performance_index'].iloc[0]:.2f}")
    print(f"  Last: {daily_totals['performance_index'].iloc[-1]:.2f}")
    print(f"  Min: {daily_totals['performance_index'].min():.2f}")
    print(f"  Max: {daily_totals['performance_index'].max():.2f}")
    
    print(f"\nLast 10 days:")
    print(daily_totals[['date', 'performance_pct', 'performance_index']].tail(10))

if __name__ == "__main__":
    calculate_like_dashboard()
