#!/usr/bin/env python3
"""
Debug script to test the fallback mode portfolio display logic
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import from trading_script
sys.path.append(str(Path(__file__).parent.parent))

from trading_script import parse_csv_timestamp, get_trading_timezone, get_timezone_config

def debug_fallback_mode():
    """Debug the fallback mode portfolio display logic"""
    print("🔍 Debugging Fallback Mode Portfolio Display")
    print("=" * 60)
    
    # Production data directory
    production_dir = Path(__file__).parent.parent / "my trading"
    portfolio_csv = production_dir / "llm_portfolio_update.csv"
    trade_log_csv = production_dir / "llm_trade_log.csv"
    
    print(f"📁 Reading portfolio from: {portfolio_csv}")
    print(f"📁 Reading trade log from: {trade_log_csv}")
    
    # Read portfolio data
    portfolio_df = pd.read_csv(portfolio_csv)
    print(f"✅ Portfolio CSV: {len(portfolio_df)} rows")
    print(f"📊 Portfolio tickers: {list(portfolio_df['Ticker'].unique())}")
    print()
    
    # Read trade log data (simulate the exact logic from trading_script.py)
    trade_log_df = None
    try:
        trade_log_df = pd.read_csv(trade_log_csv)
        print(f"✅ Trade log CSV loaded: {len(trade_log_df)} rows")
        print(f"📊 Trade log columns: {list(trade_log_df.columns)}")
        print(f"📊 Trade log tickers: {list(trade_log_df['Ticker'].unique())}")
        
        # Apply date parsing (exact logic from trading_script.py)
        trade_log_df['Date'] = trade_log_df['Date'].apply(parse_csv_timestamp)
        print("✅ Date parsing applied to trade log")
        print(f"📅 Parsed dates sample: {trade_log_df['Date'].head().tolist()}")
        print()
        
    except Exception as e:
        print(f"❌ Error loading trade log: {e}")
        trade_log_df = None
    
    # Simulate the exact fallback mode logic
    print("🔬 Testing Fallback Mode Logic:")
    print("-" * 40)
    
    # Create display_df (simulate the logic)
    display_df = portfolio_df.copy()
    display_df['Company'] = display_df['Ticker']  # Simplified for testing
    
    print(f"📊 Display DF shape: {display_df.shape}")
    print(f"📊 Display DF tickers: {list(display_df['Ticker'].unique())}")
    print()
    
    # Add position open dates (exact logic from trading_script.py lines 485-499)
    open_dates = []
    if trade_log_df is not None:
        print("✅ Trade log is not None, processing dates...")
        for i, (_, row) in enumerate(display_df.iterrows()):
            ticker = str(row.get('Ticker', ''))
            print(f"  Processing row {i+1}: {ticker}")
            
            ticker_trades = trade_log_df[trade_log_df['Ticker'] == ticker]
            print(f"    Found {len(ticker_trades)} matching trades")
            
            if not ticker_trades.empty:
                print(f"    Trades found, getting min date...")
                min_date = ticker_trades['Date'].min()
                print(f"    Min date: {min_date} (type: {type(min_date)})")
                
                if pd.isna(min_date):
                    print(f"    ❌ Min date is NaN!")
                    open_dates.append("N/A")
                else:
                    try:
                        open_date = min_date.strftime("%m/%d")
                        print(f"    ✅ Formatted date: {open_date}")
                        open_dates.append(open_date)
                    except Exception as e:
                        print(f"    ❌ strftime error: {e}")
                        open_dates.append("N/A")
            else:
                print(f"    ❌ No trades found for {ticker}")
                open_dates.append("N/A")
            print()
    else:
        print("❌ Trade log is None, using N/A for all dates")
        open_dates = ["N/A"] * len(display_df)
    
    print(f"📋 Final open_dates: {open_dates}")
    display_df['Opened'] = open_dates
    
    # Show the final result
    print("\n📊 Final Display DataFrame:")
    print(display_df[['Ticker', 'Opened']].to_string(index=False))

if __name__ == "__main__":
    debug_fallback_mode()
