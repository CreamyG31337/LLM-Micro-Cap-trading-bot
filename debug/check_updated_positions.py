#!/usr/bin/env python3
"""Check what's in updated_positions."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
# Use environment variable instead of hardcoded key
    # # Use environment variable instead of hardcoded key
    # os.environ["SUPABASE_ANON_KEY"] = "your-key-here"  # REMOVED FOR SECURITY  # REMOVED FOR SECURITY

from data.repositories.supabase_repository import SupabaseRepository
from portfolio.position_calculator import PositionCalculator
from market_data.price_cache import PriceCache
from config.settings import Settings

def check_updated_positions():
    """Check what's in updated_positions."""
    print("Checking updated_positions...")
    
    # Initialize components the same way the trading script does
    repository = SupabaseRepository(fund="TEST")
    position_calculator = PositionCalculator(repository)
    settings = Settings()
    price_cache = PriceCache(settings=settings)
    
    # Get latest snapshot
    latest_snapshot = repository.get_latest_portfolio_snapshot()
    
    if not latest_snapshot:
        print("No snapshot found")
        return
    
    print(f"Latest snapshot has {len(latest_snapshot.positions)} positions")
    
    # Update positions with current prices (same as trading script)
    updated_positions = []
    for position in latest_snapshot.positions:
        cached_data = price_cache.get_cached_price(position.ticker)
        if cached_data is not None and not cached_data.empty:
            from decimal import Decimal
            current_price = Decimal(str(cached_data['Close'].iloc[-1]))
            updated_position = position_calculator.update_position_with_price(
                position, current_price
            )
            updated_positions.append(updated_position)
        else:
            if position.current_price is not None:
                updated_positions.append(position)
    
    print(f"Updated positions has {len(updated_positions)} positions")
    
    # Check for problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
    
    for pos in updated_positions:
        ticker_display = pos.ticker.replace(".TO", "").replace(".V", "")
        if ticker_display in problematic_tickers:
            print(f"\n{ticker_display} ({pos.ticker}): '{pos.company}'")

if __name__ == "__main__":
    check_updated_positions()
