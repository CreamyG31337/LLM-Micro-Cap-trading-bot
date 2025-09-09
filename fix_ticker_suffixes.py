#!/usr/bin/env python3
"""
Utility script to fix ticker suffixes in existing portfolio and trade log files.
This helps correct any tickers that were logged without proper .TO suffixes.
"""

import pandas as pd
from trading_script import detect_and_correct_ticker
import os

def fix_portfolio_tickers(data_dir: str = "my trading"):
    """Fix ticker suffixes in portfolio and trade log files"""
    
    portfolio_file = os.path.join(data_dir, "llm_portfolio_update.csv")
    trade_log_file = os.path.join(data_dir, "llm_trade_log.csv")
    
    print("🔧 Fixing ticker suffixes in portfolio files...")
    print("=" * 50)
    
    # Fix portfolio file
    if os.path.exists(portfolio_file):
        print(f"\n📊 Processing {portfolio_file}")
        df = pd.read_csv(portfolio_file)
        
        if not df.empty and 'Ticker' in df.columns:
            print("Before fixes:")
            print(df[['Ticker']].to_string())
            
            # Fix ticker symbols
            df['Ticker'] = df['Ticker'].apply(detect_and_correct_ticker)
            
            print("\nAfter fixes:")
            print(df[['Ticker']].to_string())
            
            # Save the corrected file
            df.to_csv(portfolio_file, index=False, quoting=1)
            print(f"✅ Portfolio file updated")
        else:
            print("⚠️ No ticker data found in portfolio file")
    
    # Fix trade log file
    if os.path.exists(trade_log_file):
        print(f"\n📈 Processing {trade_log_file}")
        df = pd.read_csv(trade_log_file)
        
        if not df.empty and 'Ticker' in df.columns:
            print("Before fixes:")
            print(df[['Ticker']].to_string())
            
            # Fix ticker symbols
            df['Ticker'] = df['Ticker'].apply(detect_and_correct_ticker)
            
            print("\nAfter fixes:")
            print(df[['Ticker']].to_string())
            
            # Save the corrected file
            df.to_csv(trade_log_file, index=False, quoting=1)
            print(f"✅ Trade log file updated")
        else:
            print("⚠️ No ticker data found in trade log file")
    
    print("\n🎉 Ticker suffix fixes complete!")

if __name__ == "__main__":
    fix_portfolio_tickers()
