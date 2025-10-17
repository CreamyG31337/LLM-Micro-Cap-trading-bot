#!/usr/bin/env python3
"""Check what company names are in the position objects."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
# Use environment variable instead of hardcoded key
    # # Use environment variable instead of hardcoded key
    # os.environ["SUPABASE_ANON_KEY"] = "your-key-here"  # REMOVED FOR SECURITY  # REMOVED FOR SECURITY

from data.repositories.supabase_repository import SupabaseRepository

def check_position_company_names():
    """Check what company names are in the position objects."""
    print("Checking position company names...")
    
    repository = SupabaseRepository(fund="TEST")
    snapshot = repository.get_latest_portfolio_snapshot()
    
    if not snapshot:
        print("No snapshot found")
        return
    
    print(f"Snapshot timestamp: {snapshot.timestamp}")
    print(f"Number of positions: {len(snapshot.positions)}")
    
    # Check the problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
    
    for pos in snapshot.positions:
        ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
        if ticker_display in problematic_tickers:
            print(f"\n{ticker_display} ({pos.ticker}):")
            print(f"  Company: '{pos.company}'")
            print(f"  Ticker: '{pos.ticker}'")
            print(f"  Shares: {pos.shares}")
            print(f"  Current Price: {pos.current_price}")

if __name__ == "__main__":
    check_position_company_names()
