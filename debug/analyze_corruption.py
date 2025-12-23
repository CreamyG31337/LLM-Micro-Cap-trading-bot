import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

def analyze_corruption():
    client = SupabaseClient()
    
    print("=== ANALYZING DEC 22 DATA THAT CORRUPTED THE GRAPH ===\n")
    
    # Get Dec 22 data
    dec22 = client.supabase.table("portfolio_positions") \
        .select("ticker, shares, price, cost_basis, created_at, total_value_base, cost_basis_base") \
        .eq("fund", "Project Chimera") \
        .gte("date", "2025-12-22T00:00:00") \
        .lt("date", "2025-12-23T00:00:00") \
        .execute()
    
    if not dec22.data:
        print("No Dec 22 data found!")
        return
    
    dec22_df = pd.DataFrame(dec22.data)
    print(f"Dec 22: {len(dec22_df)} positions")
    print(f"Created at: {dec22_df['created_at'].iloc[0]}")
    
    # Get Dec 19 for comparison
    dec19 = client.supabase.table("portfolio_positions") \
        .select("ticker, shares, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .gte("date", "2025-12-19T00:00:00") \
        .lt("date", "2025-12-20T00:00:00") \
        .execute()
    
    dec19_df = pd.DataFrame(dec19.data)
    
    # Calculate totals
    dec22_value = (dec22_df['shares'] * dec22_df['price']).sum()
    dec22_cost = dec22_df['cost_basis'].sum()
    dec22_value_base = dec22_df['total_value_base'].sum() if 'total_value_base' in dec22_df.columns else 0
    dec22_cost_base = dec22_df['cost_basis_base'].sum() if 'cost_basis_base' in dec22_df.columns else 0
    
    dec19_value = (dec19_df['shares'] * dec19_df['price']).sum()
    dec19_cost = dec19_df['cost_basis'].sum()
    
    print(f"\nDec 22 totals:")
    print(f"  Stock value: ${dec22_value:,.2f}")
    print(f"  Cost basis: ${dec22_cost:,.2f}")
    print(f"  Performance: {((dec22_value / dec22_cost - 1) * 100):.2f}%")
    print(f"  Value (base): ${dec22_value_base:,.2f}")
    print(f"  Cost (base): ${dec22_cost_base:,.2f}")
    
    print(f"\nDec 19 totals:")
    print(f"  Stock value: ${dec19_value:,.2f}")
    print(f"  Cost basis: ${dec19_cost:,.2f}")
    print(f"  Performance: {((dec19_value / dec19_cost - 1) * 100):.2f}%")
    
    # Check if prices are identical (stale)
    value_diff = abs(dec22_value - dec19_value)
    print(f"\nValue difference: ${value_diff:,.2f}")
    
    if value_diff < 100:
        print("ALERT: Values are nearly identical - likely STALE DATA!")
    
    # Now the KEY question - check what the normalization baseline would be
    print("\n=== BASELINE CALCULATION IMPACT ===")
    
    # Get ALL data to see what "first day" is detected
    all_data = client.supabase.table("portfolio_positions") \
        .select("date, shares, price, cost_basis") \
        .eq("fund", "Project Chimera") \
        .order("date") \
        .limit(5000) \
        .execute()
    
    all_df = pd.DataFrame(all_data.data)
    all_df['date'] = pd.to_datetime(all_df['date'])
    all_df['value'] = all_df['shares'] * all_df['price']
    
    # Group by date
    daily = all_df.groupby(all_df['date'].dt.date).agg({
        'value': 'sum',
        'cost_basis': 'sum'
    }).reset_index()
    
    daily['pnl'] = daily['value'] - daily['cost_basis']
    daily['performance_pct'] = daily.apply(
        lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0.0,
        axis=1
    )
    
    # Find first day with investment
    first_day = daily[daily['cost_basis'] > 0].iloc[0]
    print(f"\nFirst day with investment: {first_day['date']}")
    print(f"First day performance: {first_day['performance_pct']:.2f}%")
    print(f"First day cost_basis: ${first_day['cost_basis']:,.2f}")
    print(f"First day value: ${first_day['value']:,.2f}")
    
    # Show normalized performance
    daily['normalized_pct'] = daily['performance_pct'] - first_day['performance_pct']
    daily['performance_index'] = 100 + daily['normalized_pct']
    
    print(f"\nPerformance Index range:")
    print(f"  Min: {daily['performance_index'].min():.2f}")
    print(f"  Max: {daily['performance_index'].max():.2f}")
    print(f"  First: {daily['performance_index'].iloc[0]:.2f}")
    print(f"  Last: {daily['performance_index'].iloc[-1]:.2f}")
    
    print(f"\nLast 5 days performance_index:")
    print(daily[['date', 'performance_pct', 'normalized_pct', 'performance_index']].tail())

if __name__ == "__main__":
    analyze_corruption()
