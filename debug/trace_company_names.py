#!/usr/bin/env python3
"""Trace where company names are being changed."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"

from data.repositories.supabase_repository import SupabaseRepository
from portfolio.position_calculator import PositionCalculator

def trace_company_names():
    """Trace where company names are being changed."""
    print("Tracing company names...")
    
    # Get positions from database
    repository = SupabaseRepository(fund="TEST")
    snapshot = repository.get_latest_portfolio_snapshot()
    
    if not snapshot:
        print("No snapshot found")
        return
    
    # Find problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
    
    for pos in snapshot.positions:
        ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
        if ticker_display in problematic_tickers:
            print(f"\n=== {ticker_display} ({pos.ticker}) ===")
            print(f"Database company name: '{pos.company}'")
            
            # Check what happens when we convert to dict
            pos_dict = pos.to_dict()
            print(f"After to_dict: '{pos_dict.get('company', 'N/A')}'")
            
            # Check what happens when we update with price
            position_calculator = PositionCalculator(repository)
            if pos.current_price:
                updated_pos = position_calculator.update_position_with_price(pos, pos.current_price)
                print(f"After update_position_with_price: '{updated_pos.company}'")
                
                # Check dict after update
                updated_pos_dict = updated_pos.to_dict()
                print(f"After updated to_dict: '{updated_pos_dict.get('company', 'N/A')}'")
            
            # Only check first occurrence of each ticker
            break

if __name__ == "__main__":
    trace_company_names()
