#!/usr/bin/env python3
"""Test the grouping logic."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"

from data.repositories.supabase_repository import SupabaseRepository

def test_grouping_logic():
    """Test the grouping logic."""
    print("Testing grouping logic...")
    
    # Get latest snapshot using the repository method
    repository = SupabaseRepository(fund="TEST")
    snapshot = repository.get_latest_portfolio_snapshot()
    
    if not snapshot:
        print("No snapshot found")
        return
    
    print(f"Snapshot has {len(snapshot.positions)} positions")
    
    # Check for problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
    
    for pos in snapshot.positions:
        ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
        if ticker_display in problematic_tickers:
            print(f"\n{ticker_display} ({pos.ticker}):")
            print(f"  Company: '{pos.company}'")
            print(f"  Timestamp: {pos.position_id}")  # This might have the timestamp

if __name__ == "__main__":
    test_grouping_logic()
