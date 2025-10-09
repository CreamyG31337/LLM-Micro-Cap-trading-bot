#!/usr/bin/env python3
"""Check what's in the fundamentals cache."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from config.settings import Settings

def check_fundamentals_cache():
    """Check what's in the fundamentals cache."""
    print("Checking fundamentals cache...")
    
    # Initialize components the same way the trading script does
    settings = Settings()
    price_cache = PriceCache(settings=settings)
    market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
    
    print(f"Market data fetcher: {type(market_data_fetcher).__name__}")
    
    # Check if fundamentals cache exists
    if hasattr(market_data_fetcher, '_fund_cache'):
        print(f"Fundamentals cache exists: {len(market_data_fetcher._fund_cache)} entries")
        
        # Check for problematic tickers
        problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
        
        for ticker in problematic_tickers:
            print(f"\n=== {ticker} ===")
            
            # Check both with and without .TO suffix
            for ticker_variant in [ticker, f"{ticker}.TO"]:
                if ticker_variant in market_data_fetcher._fund_cache:
                    fundamentals = market_data_fetcher._fund_cache[ticker_variant]
                    print(f"  {ticker_variant}: '{fundamentals.get('company_name', 'N/A')}'")
                else:
                    print(f"  {ticker_variant}: Not in cache")
    else:
        print("No fundamentals cache found")
    
    # Check cache metadata
    if hasattr(market_data_fetcher, '_fund_cache_meta'):
        print(f"Cache metadata: {market_data_fetcher._fund_cache_meta}")
    
    # Check disk cache
    try:
        fund_cache_path = market_data_fetcher._get_fund_cache_path()
        if fund_cache_path and fund_cache_path.exists():
            print(f"Disk cache exists: {fund_cache_path}")
            print(f"Disk cache size: {fund_cache_path.stat().st_size} bytes")
        else:
            print("No disk cache found")
    except Exception as e:
        print(f"Error checking disk cache: {e}")

if __name__ == "__main__":
    check_fundamentals_cache()
