#!/usr/bin/env python3
"""
Debug script to get actual prices for suspicious tickers
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from datetime import datetime, timedelta

def debug_actual_prices():
    """Get actual prices for suspicious tickers."""
    
    # Test the suspicious tickers
    fetcher = MarketDataFetcher()
    cache = PriceCache()
    fetcher.cache = cache

    end_date = datetime.now()
    start_date = end_date - timedelta(days=15)

    suspicious_tickers = ['NXTG', 'GLCC', 'DOL', 'KEY']

    print('Getting actual prices for suspicious tickers:')
    print('=' * 60)

    for ticker in suspicious_tickers:
        print(f'\nTesting {ticker}:')
        result = fetcher.fetch_price_data(ticker, start_date, end_date)
        
        if not result.df.empty and 'Close' in result.df.columns:
            latest_close = float(result.df['Close'].iloc[-1])
            print(f'  Current price: ${latest_close:.2f} (from {result.source})')
            
            # Show recent price history
            recent_prices = result.df['Close'].tail(3)
            print(f'  Recent prices: {[float(p) for p in recent_prices]}')
        else:
            print(f'  FAILED: {result.source}')

    print('\n' + '=' * 60)
    print('Checking original trade data:')
    print('=' * 60)

    # Read CSV to see original trade data
    df = pd.read_csv('trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv')

    for ticker in suspicious_tickers:
        # Get the original BUY entry
        buy_entries = df[(df['Ticker'] == ticker) & (df['Action'] == 'BUY')]
        if not buy_entries.empty:
            original_price = buy_entries.iloc[0]['Average Price']
            print(f'{ticker}: Original buy price was ${original_price:.2f}')
        else:
            print(f'{ticker}: No BUY entry found')

    print('\n' + '=' * 60)
    print('Checking if these are Canadian tickers:')
    print('=' * 60)

    # Test with Canadian suffixes
    for ticker in suspicious_tickers:
        print(f'\nTesting {ticker}.TO:')
        result = fetcher.fetch_price_data(f'{ticker}.TO', start_date, end_date)
        
        if not result.df.empty and 'Close' in result.df.columns:
            latest_close = float(result.df['Close'].iloc[-1])
            print(f'  {ticker}.TO price: ${latest_close:.2f} (from {result.source})')
        else:
            print(f'  {ticker}.TO: FAILED - {result.source}')

if __name__ == "__main__":
    debug_actual_prices()
