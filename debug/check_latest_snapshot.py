#!/usr/bin/env python3
"""Check the latest snapshot data."""

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

def check_latest_snapshot():
    """Check what's in the latest snapshot."""
    print("🔍 Checking Latest Snapshot...")
    
    repository = SupabaseRepository(fund="TEST")
    snapshot = repository.get_latest_portfolio_snapshot()
    
    if not snapshot:
        print("❌ No snapshot found")
        return
    
    print(f"\n📊 Snapshot timestamp: {snapshot.timestamp}")
    print(f"📊 Number of positions: {len(snapshot.positions)}")
    
    # Show company names for all positions
    print("\n🏢 All company names:")
    for pos in sorted(snapshot.positions, key=lambda p: p.ticker):
        ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
        print(f"   {ticker_display:8} ({pos.ticker:12}): '{pos.company}'")

if __name__ == "__main__":
    check_latest_snapshot()
