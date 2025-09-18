#!/usr/bin/env python3
"""
Debug script to investigate price fetching issues
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from datetime import datetime, timedelta
import pandas as pd

def debug_prices():
    """Debug price fetching for problematic tickers."""
    
    # Initialize fetcher
    fetcher = MarketDataFetcher()
    cache = PriceCache()
    fetcher.cache = cache

    # Simulate the exact call from trading_script.py
    end_date = datetime.now()
    start_date = end_date - timedelta(days=15)

    problematic_tickers = ['ATRL', 'CGL', 'VFV', 'XEQT', 'XGD', 'XHAK', 'XHC', 'XIC', 'ZEA']

    print("Actual prices being fetched for problematic tickers:")
    print("=" * 60)

    for ticker in problematic_tickers:
        print(f"\nTesting {ticker}:")
        result = fetcher.fetch_price_data(ticker, start_date, end_date)
        
        if not result.df.empty and 'Close' in result.df.columns:
            # Convert Decimal to float for display
            latest_close = float(result.df['Close'].iloc[-1])
            print(f"  SUCCESS: ${latest_close:.2f} (from {result.source})")
            
            # Show a few recent prices for context
            recent_prices = result.df['Close'].tail(3)
            print(f"  Recent prices: {[float(p) for p in recent_prices]}")
        else:
            print(f"  FAILED: {result.source}")

    print("\n" + "=" * 60)
    print("Now checking what prices are in your portfolio CSV...")
    print("=" * 60)

    # Read the CSV
    df = pd.read_csv('trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv')
    
    # Get the latest entry for each ticker
    latest_entries = df.groupby('Ticker').last().reset_index()

    for ticker in problematic_tickers:
        entry = latest_entries[latest_entries['Ticker'] == ticker]
        if not entry.empty:
            csv_price = entry['Current Price'].iloc[0]
            print(f"{ticker:4s}: ${csv_price:8.2f} (from CSV)")
        else:
            print(f"{ticker:4s}: Not found in CSV")

    print("\n" + "=" * 60)
    print("Price comparison analysis:")
    print("=" * 60)

    # Compare prices
    for ticker in problematic_tickers:
        # Get fetched price
        result = fetcher.fetch_price_data(ticker, start_date, end_date)
        fetched_price = None
        if not result.df.empty and 'Close' in result.df.columns:
            fetched_price = float(result.df['Close'].iloc[-1])
        
        # Get CSV price
        entry = latest_entries[latest_entries['Ticker'] == ticker]
        csv_price = None
        if not entry.empty:
            csv_price = entry['Current Price'].iloc[0]
        
        if fetched_price and csv_price:
            diff = fetched_price - csv_price
            diff_pct = (diff / csv_price) * 100
            print(f"{ticker:4s}: CSV=${csv_price:8.2f} | Fetched=${fetched_price:8.2f} | Diff=${diff:+.2f} ({diff_pct:+.1f}%)")
            
            if abs(diff_pct) > 10:  # More than 10% difference
                print(f"         ⚠️  WARNING: Large price difference detected!")
        else:
            print(f"{ticker:4s}: Could not compare - fetched={fetched_price}, csv={csv_price}")

if __name__ == "__main__":
    debug_prices()
