import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.streamlit_utils import calculate_portfolio_value_over_time

def check_performance_index():
    print("Running calculate_portfolio_value_over_time for Project Chimera...")
    
    df = calculate_portfolio_value_over_time("Project Chimera")
    
    if df.empty:
        print("No data returned!")
        return
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    print("\nFirst 5 rows:")
    print(df.head())
    
    print("\nLast 5 rows:")
    print(df.tail())
    
    if 'performance_index' in df.columns:
        print(f"\nPerformance Index Stats:")
        print(f"  Min: {df['performance_index'].min():.2f}")
        print(f"  Max: {df['performance_index'].max():.2f}")
        print(f"  First: {df['performance_index'].iloc[0]:.2f}")
        print(f"  Last: {df['performance_index'].iloc[-1]:.2f}")

if __name__ == "__main__":
    check_performance_index()
