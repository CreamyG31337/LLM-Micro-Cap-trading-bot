#!/usr/bin/env python3
"""
Debug script to investigate suspicious P&L tickers
"""

import sys
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from datetime import datetime, timedelta

def debug_suspicious_tickers():
    """Debug suspicious P&L tickers."""
    
    # Test the suspicious tickers
    fetcher = MarketDataFetcher()
    cache = PriceCache()
    fetcher.cache = cache

    end_date = datetime.now()
    start_date = end_date - timedelta(days=15)

    suspicious_tickers = ['NXTG', 'GLCC', 'DOL', 'KEY']

    print('Investigating suspicious P&L tickers:')
    print('=' * 60)

    for ticker in suspicious_tickers:
        print(f'\nTesting {ticker}:')
        result = fetcher.fetch_price_data(ticker, start_date, end_date)
        
        if not result.df.empty and 'Close' in result.df.columns:
            latest_close = float(result.df['Close'].iloc[-1])
            print(f'  Fetched price: ${latest_close:.2f} (from {result.source})')
            
            # Check if this looks reasonable
            if latest_close < 0.01:
                print(f'  ⚠️  WARNING: Extremely low price - might be wrong ticker')
            elif latest_close > 10000:
                print(f'  ⚠️  WARNING: Extremely high price - might be wrong ticker')
            else:
                print(f'  Price looks reasonable')
        else:
            print(f'  FAILED: {result.source}')

    print('\n' + '=' * 60)
    print('Checking what these tickers should be:')
    print('=' * 60)

    # Read CSV to see what we think these should be
    df = pd.read_csv('trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv')
    latest_entries = df.groupby('Ticker').last().reset_index()

    for ticker in suspicious_tickers:
        entry = latest_entries[latest_entries['Ticker'] == ticker]
        if not entry.empty:
            row = entry.iloc[0]
            print(f'{ticker}:')
            print(f'  Company: {row["Company"]}')
            print(f'  Shares: {row["Shares"]}')
            print(f'  Avg Price: ${row["Average Price"]:.2f}')
            print(f'  Current Price: ${row["Current Price"]:.2f}')
            print(f'  P&L: ${row["PnL"]:.2f}')
            pnl_pct = (row["PnL"] / (row["Shares"] * row["Average Price"])) * 100
            print(f'  P&L %: {pnl_pct:.1f}%')
        else:
            print(f'{ticker}: Not found in CSV')

if __name__ == "__main__":
    debug_suspicious_tickers()
