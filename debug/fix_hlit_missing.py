#!/usr/bin/env python3
"""
Fix HLIT.TO missing from latest portfolio snapshot.

This script adds HLIT.TO to the latest portfolio snapshot so it appears in the portfolio display.
"""

import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def fix_hlit_missing():
    """Fix HLIT.TO missing from latest portfolio snapshot."""
    
    print("🔧 Fixing HLIT.TO missing from latest portfolio snapshot")
    print("=" * 60)
    
    # Load portfolio data
    portfolio_file = Path("my trading/llm_portfolio_update.csv")
    if not portfolio_file.exists():
        print("❌ Portfolio file not found")
        return False
    
    df = pd.read_csv(portfolio_file)
    print(f"📊 Loaded portfolio with {len(df)} records")
    
    # Find the latest snapshot timestamp
    latest_timestamp = df['Date'].max()
    print(f"📅 Latest snapshot: {latest_timestamp}")
    
    # Check if HLIT.TO is in the latest snapshot
    latest_snapshot = df[df['Date'] == latest_timestamp]
    hlit_in_latest = 'HLIT.TO' in latest_snapshot['Ticker'].values
    
    print(f"🔍 HLIT.TO in latest snapshot: {hlit_in_latest}")
    
    if hlit_in_latest:
        print("✅ HLIT.TO is already in the latest snapshot - no fix needed")
        return True
    
    # Find the most recent HLIT.TO entry
    hlit_entries = df[df['Ticker'] == 'HLIT.TO']
    if hlit_entries.empty:
        print("❌ No HLIT.TO entries found in portfolio")
        return False
    
    latest_hlit = hlit_entries.iloc[-1]  # Get the most recent HLIT.TO entry
    print(f"📈 Latest HLIT.TO entry: {latest_hlit['Date']} - {latest_hlit['Action']}")
    
    # Create a new HLIT.TO entry for the latest snapshot
    new_hlit_entry = latest_hlit.copy()
    new_hlit_entry['Date'] = latest_timestamp
    new_hlit_entry['Action'] = 'HOLD'  # Change to HOLD for the latest snapshot
    
    print(f"➕ Adding HLIT.TO to latest snapshot: {latest_timestamp}")
    
    # Add the new entry to the dataframe
    df = pd.concat([df, new_hlit_entry.to_frame().T], ignore_index=True)
    
    # Sort by Date to maintain order
    df = df.sort_values('Date')
    
    # Save the updated portfolio
    df.to_csv(portfolio_file, index=False)
    print(f"💾 Updated portfolio saved to: {portfolio_file}")
    
    # Verify the fix
    updated_df = pd.read_csv(portfolio_file)
    latest_snapshot_after = updated_df[updated_df['Date'] == latest_timestamp]
    hlit_in_latest_after = 'HLIT.TO' in latest_snapshot_after['Ticker'].values
    
    print(f"✅ Verification - HLIT.TO in latest snapshot: {hlit_in_latest_after}")
    
    if hlit_in_latest_after:
        print("🎉 HLIT.TO is now in the latest portfolio snapshot!")
        print("   It should now appear in your portfolio display.")
        return True
    else:
        print("❌ Fix failed - HLIT.TO still missing from latest snapshot")
        return False

if __name__ == "__main__":
    success = fix_hlit_missing()
    sys.exit(0 if success else 1)
