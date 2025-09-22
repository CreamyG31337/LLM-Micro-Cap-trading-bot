#!/usr/bin/env python3
"""
Debug script to fix Canadian ticker suffixes in portfolio CSV files.

This script adds .TO suffixes to Canadian tickers that are missing them,
based on the Currency column in the portfolio data.
"""

import pandas as pd
import os
from pathlib import Path


def fix_canadian_tickers_in_portfolio(csv_path):
    """Fix Canadian tickers by adding .TO suffixes where needed."""
    
    print(f"Loading portfolio CSV: {csv_path}")
    
    # Load the CSV
    df = pd.read_csv(csv_path)
    
    print(f"Loaded {len(df)} rows")
    print(f"Columns: {list(df.columns)}")
    
    # Check if required columns exist
    if 'Ticker' not in df.columns or 'Currency' not in df.columns:
        print("Error: CSV must have 'Ticker' and 'Currency' columns")
        return False
    
    # Find Canadian tickers without .TO suffix
    canadian_mask = df['Currency'] == 'CAD'
    missing_suffix_mask = ~df['Ticker'].str.endswith('.TO') & ~df['Ticker'].str.endswith('.V')
    needs_fix_mask = canadian_mask & missing_suffix_mask
    
    tickers_to_fix = df[needs_fix_mask]['Ticker'].unique()
    
    print(f"Found {len(tickers_to_fix)} unique Canadian tickers needing .TO suffix:")
    for ticker in sorted(tickers_to_fix):
        print(f"  {ticker} -> {ticker}.TO")
    
    if len(tickers_to_fix) == 0:
        print("No tickers need fixing!")
        return True
    
    # Create backup
    backup_path = csv_path + f".backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")
    df.to_csv(backup_path, index=False)
    
    # Fix the tickers
    for ticker in tickers_to_fix:
        ticker_mask = (df['Ticker'] == ticker) & (df['Currency'] == 'CAD')
        rows_affected = ticker_mask.sum()
        df.loc[ticker_mask, 'Ticker'] = f"{ticker}.TO"
        print(f"  Fixed {rows_affected} rows for {ticker} -> {ticker}.TO")
    
    # Save the fixed CSV
    print(f"Saving fixed CSV: {csv_path}")
    df.to_csv(csv_path, index=False)
    
    print("✅ Portfolio CSV fixed successfully!")
    return True


def main():
    """Main function to fix all portfolio CSVs."""
    
    # Portfolio CSV paths to check
    portfolio_paths = [
        "trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv",
        "Scripts and CSV Files/chatgpt_portfolio_update.csv",
    ]
    
    print("🔧 Canadian Ticker Fix Script")
    print("=" * 50)
    
    fixed_count = 0
    
    for csv_path in portfolio_paths:
        if os.path.exists(csv_path):
            print(f"\n📁 Processing: {csv_path}")
            print("-" * 50)
            
            if fix_canadian_tickers_in_portfolio(csv_path):
                fixed_count += 1
            else:
                print(f"❌ Failed to fix {csv_path}")
        else:
            print(f"⚠️  File not found: {csv_path}")
    
    print(f"\n🎉 Summary: Fixed {fixed_count} portfolio files")


if __name__ == "__main__":
    main()