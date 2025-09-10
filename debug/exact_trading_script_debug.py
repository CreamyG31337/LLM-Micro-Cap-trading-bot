#!/usr/bin/env python3
"""
Debug script that simulates the exact same environment as trading_script.py
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import from trading_script
sys.path.append(str(Path(__file__).parent.parent))

# Import the exact same modules and functions as trading_script.py
from trading_script import (
    parse_csv_timestamp, 
    get_trading_timezone, 
    get_timezone_config,
    create_portfolio_table,
    DATA_DIR,
    PORTFOLIO_CSV,
    TRADE_LOG_CSV
)

def debug_exact_environment():
    """Debug using the exact same environment as trading_script.py"""
    print("🔍 Debugging Exact Trading Script Environment")
    print("=" * 60)
    
    print(f"📁 DATA_DIR: {DATA_DIR}")
    print(f"📁 PORTFOLIO_CSV: {PORTFOLIO_CSV}")
    print(f"📁 TRADE_LOG_CSV: {TRADE_LOG_CSV}")
    print()
    
    # Check if files exist
    print("📋 File existence check:")
    print(f"  Portfolio CSV exists: {PORTFOLIO_CSV.exists()}")
    print(f"  Trade log CSV exists: {TRADE_LOG_CSV.exists()}")
    print()
    
    # Read the data using the exact same logic
    try:
        portfolio_df = pd.read_csv(PORTFOLIO_CSV)
        print(f"✅ Portfolio loaded: {len(portfolio_df)} rows")
        print(f"📊 Portfolio tickers: {list(portfolio_df['Ticker'].unique())}")
        print()
        
        # Test the exact create_portfolio_table function
        print("🔬 Testing create_portfolio_table function:")
        print("-" * 40)
        
        # This should show the actual table with dates
        create_portfolio_table(portfolio_df)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_exact_environment()
