#!/usr/bin/env python3
"""Check what data is actually being loaded by the trading script."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"

from data.repositories.supabase_repository import SupabaseRepository
from portfolio.portfolio_manager import PortfolioManager
from portfolio.fund_manager import Fund

def check_actual_data():
    """Check what data is actually being loaded."""
    print("🔍 Checking actual data being loaded...")
    
    # Create repository and portfolio manager the same way the trading script does
    repository = SupabaseRepository(fund="TEST")
    print(f"✅ Repository type: {type(repository).__name__}")
    
    fund = Fund(id="TEST", name="TEST", description="Test Fund")
    portfolio_manager = PortfolioManager(repository, fund)
    print(f"✅ Portfolio manager initialized")
    
    # Load portfolio the same way the trading script does
    print("\n📊 Loading portfolio snapshots...")
    snapshots = portfolio_manager.load_portfolio()
    print(f"   Loaded {len(snapshots)} snapshots")
    
    if snapshots:
        latest = snapshots[-1]
        print(f"\n   Latest snapshot: {latest.timestamp}")
        print(f"   Positions: {len(latest.positions)}")
        
        # Show the problematic tickers
        problem_tickers = ["XMA", "DRX", "VEE", "CTRN"]
        print("\n   Company names for problematic tickers:")
        for pos in latest.positions:
            ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
            if ticker_display in problem_tickers:
                print(f"     {pos.ticker} (display: {ticker_display}): '{pos.company}'")

if __name__ == "__main__":
    check_actual_data()
