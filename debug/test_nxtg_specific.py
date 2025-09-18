#!/usr/bin/env python3
"""
Test NXTG specifically to see what's wrong
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.ticker_utils import get_company_name
from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from datetime import datetime, timedelta
import pandas as pd

def test_nxtg_specific():
    """Test NXTG specifically to see what's wrong."""
    
    print('Testing NXTG specifically:')
    print('=' * 40)

    # Check company name
    company_name = get_company_name('NXTG')
    print(f'Company name: {company_name}')

    # Check what price we're getting
    fetcher = MarketDataFetcher()
    cache = PriceCache()
    fetcher.cache = cache

    end_date = datetime.now()
    start_date = end_date - timedelta(days=15)

    result = fetcher.fetch_price_data('NXTG', start_date, end_date)
    if not result.df.empty and 'Close' in result.df.columns:
        latest_close = float(result.df['Close'].iloc[-1])
        print(f'Current price: ${latest_close:.2f} (from {result.source})')
        
        # Check if this matches the expected Canadian price
        print(f'Expected: ~$14 Canadian')
        if 13 <= latest_close <= 15:
            print('✅ Price looks correct for Canadian market')
        else:
            print('❌ Price looks wrong')
    else:
        print('❌ Failed to get price data')

    # Check what the original buy price was
    df = pd.read_csv('trading_data/funds/RRSP Lance Webull/llm_portfolio_update.csv')
    nxtg_entries = df[df['Ticker'] == 'NXTG']
    if not nxtg_entries.empty:
        latest = nxtg_entries.iloc[-1]
        print(f'\nPortfolio data:')
        print(f'  Company: {latest["Company"]}')
        print(f'  Shares: {latest["Shares"]}')
        print(f'  Avg Price: ${latest["Average Price"]:.2f}')
        print(f'  Current Price: ${latest["Current Price"]:.2f}')
        print(f'  P&L: ${latest["PnL"]:.2f}')
        print(f'  Currency: {latest["Currency"]}')
        
        # Calculate what the P&L should be
        shares = latest["Shares"]
        avg_price = latest["Average Price"]
        current_price = latest["Current Price"]
        expected_pnl = shares * (current_price - avg_price)
        print(f'\nExpected P&L calculation:')
        print(f'  {shares} shares × (${current_price:.2f} - ${avg_price:.2f}) = ${expected_pnl:.2f}')
        print(f'  Actual P&L: ${latest["PnL"]:.2f}')
        
        if abs(expected_pnl - latest["PnL"]) < 1.0:
            print('✅ P&L calculation looks correct')
        else:
            print('❌ P&L calculation is wrong')

if __name__ == "__main__":
    test_nxtg_specific()
