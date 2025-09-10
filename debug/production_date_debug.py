#!/usr/bin/env python3
"""
Debug script to test the actual production data
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add the parent directory to the path so we can import from trading_script
sys.path.append(str(Path(__file__).parent.parent))

from trading_script import parse_csv_timestamp, get_trading_timezone, get_timezone_config

def debug_production_dates():
    """Debug the actual production data"""
    print("🔍 Debugging Production Data")
    print("=" * 50)
    
    # Production data directory
    production_dir = Path(__file__).parent.parent / "my trading"
    portfolio_csv = production_dir / "llm_portfolio_update.csv"
    trade_log_csv = production_dir / "llm_trade_log.csv"
    
    print(f"📁 Reading portfolio from: {portfolio_csv}")
    print(f"📁 Reading trade log from: {trade_log_csv}")
    
    # Read portfolio data
    try:
        portfolio_df = pd.read_csv(portfolio_csv)
        print(f"✅ Portfolio CSV: {len(portfolio_df)} rows")
        print(f"📊 Portfolio tickers: {list(portfolio_df['Ticker'].unique())}")
        print()
        
        # Read trade log data
        trade_log_df = pd.read_csv(trade_log_csv)
        print(f"✅ Trade log CSV: {len(trade_log_df)} rows")
        print(f"📊 Trade log columns: {list(trade_log_df.columns)}")
        print(f"📊 Trade log tickers: {list(trade_log_df['Ticker'].unique())}")
        print(f"📅 Date column sample values:")
        print(trade_log_df['Date'].head())
        print()
        
        # Test date parsing
        print("🧪 Testing date parsing:")
        for i, date_str in enumerate(trade_log_df['Date'].head(3)):
            print(f"  Row {i+1}: '{date_str}'")
            try:
                parsed_date = parse_csv_timestamp(date_str)
                print(f"    ✅ Parsed: {parsed_date}")
                print(f"    📅 Type: {type(parsed_date)}")
                if hasattr(parsed_date, 'strftime'):
                    formatted = parsed_date.strftime("%m/%d")
                    print(f"    🎯 Formatted (mm/dd): {formatted}")
                else:
                    print(f"    ❌ No strftime method available")
            except Exception as e:
                print(f"    ❌ Error parsing: {e}")
            print()
        
        # Apply date parsing to the trade log
        print("🔄 Applying date parsing to trade log...")
        trade_log_df['Date'] = trade_log_df['Date'].apply(parse_csv_timestamp)
        print("✅ Date parsing applied")
        print()
        
        # Test the actual logic from trading_script.py
        print("🔬 Testing portfolio display logic:")
        print("-" * 40)
        
        for _, row in portfolio_df.iterrows():
            ticker = str(row.get('Ticker', ''))
            print(f"🎯 Processing ticker: {ticker}")
            
            # Get position open date from trade log (exact logic from trading_script.py)
            open_date = "N/A"
            if trade_log_df is not None:
                ticker_trades = trade_log_df[trade_log_df['Ticker'] == ticker]
                print(f"   Found {len(ticker_trades)} matching trades in trade log")
                
                if not ticker_trades.empty:
                    # Get the earliest trade date for this ticker
                    min_date = ticker_trades['Date'].min()
                    print(f"   📅 Min date: {min_date}")
                    if pd.isna(min_date):
                        print(f"   ❌ Min date is NaN!")
                    else:
                        open_date = min_date.strftime("%m/%d")
                        print(f"   ✅ Formatted date: {open_date}")
                else:
                    print(f"   ❌ No trades found for {ticker} - will show N/A")
            else:
                print(f"   ❌ Trade log is None - will show N/A")
            
            print(f"   📋 Final open_date: {open_date}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_production_dates()
