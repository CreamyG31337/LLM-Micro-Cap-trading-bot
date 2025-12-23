import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def calculate_performance_manually():
    client = SupabaseClient()
    
    # Get all data
    response = client.supabase.table("portfolio_positions") \
        .select("date, shares, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .order("date") \
        .execute()
        
    df = pd.DataFrame(response.data)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = df['shares'] * df['price']
    
    # Group by date
    daily = df.groupby(df['date'].dt.date).agg({
        'value': 'sum',
        'cost_basis': 'sum'
    }).reset_index()
    
    daily['pnl'] = daily['value'] - daily['cost_basis']
    daily['performance_pct'] = daily.apply(
        lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0.0,
        axis=1
    )
    
    # Normalize to start at 100
    first_day = daily[daily['cost_basis'] > 0].iloc[0]
    first_perf = first_day['performance_pct']
    
    daily['normalized_pct'] = daily['performance_pct'] - first_perf
    daily['performance_index'] = 100 + daily['normalized_pct']
    
    print(f"First day: {first_day['date']}")
    print(f"First day performance: {first_perf:.2f}%")
    print(f"\nFirst 5 days:")
    print(daily[['date', 'performance_pct', 'normalized_pct', 'performance_index']].head())
    
    print(f"\nLast 5 days:")
    print(daily[['date', 'performance_pct', 'normalized_pct', 'performance_index']].tail())
    
    print(f"\nPerformance Index range: {daily['performance_index'].min():.2f} - {daily['performance_index'].max():.2f}")

if __name__ == "__main__":
    calculate_performance_manually()
