"""
Test if calculate_portfolio_value_over_time is actually fetching all data with pagination
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Disable streamlit to avoid import issues
import builtins
builtins.st = None

def test_pagination():
    # Import after disabling streamlit
    from streamlit_utils import calculate_portfolio_value_over_time
    
    print("Calling calculate_portfolio_value_over_time...")
    
    try:
        df = calculate_portfolio_value_over_time("Project Chimera")
        
        print(f"\nResults:")
        print(f"  Total rows returned: {len(df)}")
        
        if not df.empty:
            print(f"  Columns: {df.columns.tolist()}")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"\n  Last 10 dates:")
            for date in df['date'].tail(10):
                print(f"    {date}")
        else:
            print("  DataFrame is EMPTY!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pagination()
