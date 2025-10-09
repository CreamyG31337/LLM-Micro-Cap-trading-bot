#!/usr/bin/env python3
"""Fix incorrect company names in Supabase database."""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.repositories.supabase_repository import SupabaseRepository
from utils.ticker_utils import get_company_name

def fix_company_names():
    """Fix incorrect company names in the database."""
    print("🔧 Fixing Company Names in Supabase...")
    
    # Set environment variables
    os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"
    
    # Initialize Supabase repository
    repository = SupabaseRepository(fund="TEST")
    
    print("✅ Initialized Supabase repository")
    
    # Get current portfolio data
    latest_snapshot = repository.get_latest_portfolio_snapshot()
    if not latest_snapshot:
        print("❌ No portfolio data found")
        return False
    
    print(f"📊 Found {len(latest_snapshot.positions)} positions")
    
    # Check the actual company names for the problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "XMA.TO", "DRX.TO", "VEE.TO", "CTRN"]
    print("\n🔍 Current company names in database:")
    found_tickers = []
    for position in latest_snapshot.positions:
        if position.ticker in problematic_tickers:
            found_tickers.append(position.ticker)
            print(f"   {position.ticker}: '{position.company}'")
    
    if not found_tickers:
        print("   No problematic tickers found. Showing first 10 tickers:")
        for i, position in enumerate(latest_snapshot.positions[:10]):
            print(f"   {position.ticker}: '{position.company}'")
    
    # Also check for any tickers that might be the wrong ones
    print("\n🔍 Looking for wrong company names:")
    wrong_names = ["XTM Inc", "DRI Healthcare Trust", "Veeva Systems Inc", "Core & Main"]
    for position in latest_snapshot.positions:
        if position.company in wrong_names:
            print(f"   FOUND WRONG: {position.ticker}: '{position.company}'")
    
    # Define the corrections needed
    corrections = {
        "XMA": "iShares S&P/TSX Capped Materials Index ETF",
        "DRX": "ADF Group Inc.", 
        "VEE": "Vanguard FTSE Emerging Markets All Cap Index ETF",
        "CTRN": "Citi Trends, Inc."
    }
    
    # Check which positions need fixing
    positions_to_fix = []
    for position in latest_snapshot.positions:
        if position.ticker in corrections:
            current_name = position.company or "Unknown"
            correct_name = corrections[position.ticker]
            if current_name != correct_name:
                positions_to_fix.append((position.ticker, current_name, correct_name))
                print(f"🔍 {position.ticker}: '{current_name}' → '{correct_name}'")
    
    if not positions_to_fix:
        print("✅ All company names are already correct")
        return True
    
    print(f"\n🔄 Fixing {len(positions_to_fix)} company names...")
    
    # Update each position with correct company name
    for ticker, old_name, new_name in positions_to_fix:
        try:
            # Find the position in the snapshot
            position = latest_snapshot.get_position_by_ticker(ticker)
            if position:
                # Update the company name
                position.company = new_name
                print(f"✅ Updated {ticker}: '{old_name}' → '{new_name}'")
            else:
                print(f"❌ Position not found for {ticker}")
        except Exception as e:
            print(f"❌ Failed to update {ticker}: {e}")
    
    # Save the updated snapshot
    try:
        repository.save_portfolio_snapshot(latest_snapshot)
        print("✅ Saved updated portfolio snapshot to Supabase")
    except Exception as e:
        print(f"❌ Failed to save updated snapshot: {e}")
        return False
    
    # Verify the changes
    print("\n🔍 Verifying changes...")
    updated_snapshot = repository.get_latest_portfolio_snapshot()
    for ticker, old_name, new_name in positions_to_fix:
        position = updated_snapshot.get_position_by_ticker(ticker)
        if position and position.company == new_name:
            print(f"✅ {ticker}: {position.company}")
        else:
            print(f"❌ {ticker}: Update failed")
    
    return True

if __name__ == "__main__":
    fix_company_names()