#!/usr/bin/env python3
"""
Clean up excessive decimal places in portfolio CSV
"""

import pandas as pd
from pathlib import Path
import sys

def cleanup_decimal_places():
    """Clean up excessive decimal places in portfolio CSV."""
    
    print("🔧 Cleaning up excessive decimal places")
    print("=" * 40)
    
    # Load portfolio
    portfolio_file = Path("my trading/llm_portfolio_update.csv")
    df = pd.read_csv(portfolio_file)
    
    print(f"📊 Loaded portfolio with {len(df)} records")
    
    # Round all numeric columns to 2 decimal places
    numeric_columns = ['Shares', 'Average Price', 'Cost Basis', 'Stop Loss', 'Current Price', 'Total Value', 'PnL']
    
    for col in numeric_columns:
        if col in df.columns:
            print(f"   Rounding {col} to 2 decimal places")
            df[col] = df[col].round(2)
    
    # Create backup
    backup_file = f"{portfolio_file}.backup_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    df.to_csv(backup_file, index=False)
    print(f"💾 Created backup: {backup_file}")
    
    # Save cleaned data
    df.to_csv(portfolio_file, index=False)
    print(f"💾 Saved cleaned portfolio to: {portfolio_file}")
    
    # Show sample of cleaned data
    print(f"\n✅ Sample of cleaned data:")
    print(df[['Ticker', 'Current Price', 'Total Value', 'PnL']].head())
    
    return True

if __name__ == "__main__":
    success = cleanup_decimal_places()
    sys.exit(0 if success else 1)
