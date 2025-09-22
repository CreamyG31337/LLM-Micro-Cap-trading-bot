#!/usr/bin/env python3
"""
Debug script to investigate N/A values in fundamentals data
===========================================================

This script tests the fetch_fundamentals method directly on the tickers
showing N/A values in your prompt generation screen to identify the issue.
"""

import sys
from pathlib import Path

# Add the current directory to Python path to import modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from config.settings import get_settings

def test_fundamentals_data():
    """Test fundamentals data for specific tickers showing N/A values"""
    
    # Your problematic tickers from the prompt screen
    test_tickers = [
        "VFV.TO",    # Vanguard S&P 500 Index ETF 
        "VOO",       # Vanguard S&P 500 ETF
        "VTI",       # Vanguard Total Stock Market ETF
        "XEQT.TO",   # iShares Core Equity ETF Portfolio
        "XGD.TO",    # iShares Core S&P Total Canadian Gold ETF
        "XHAK.TO",   # iShares Core FTSE Developed ex North America IMI Index ETF
        "XHC.TO",    # iShares Core S&P US Total Market ETF
        "XIC.TO",    # iShares Core S&P Total Canadian Stock Market ETF  
        "ZEA.TO"     # BMO Emerging Markets Equity Index ETF
    ]
    
    # Initialize the market data fetcher
    settings = get_settings()
    price_cache = PriceCache()
    fetcher = MarketDataFetcher(cache_instance=price_cache)
    
    print("🔍 Testing Fundamentals Data for N/A Issue")
    print("=" * 80)
    
    for ticker in test_tickers:
        print(f"\n📈 Testing {ticker}")
        print("-" * 40)
        
        try:
            fundamentals = fetcher.fetch_fundamentals(ticker)
            
            print(f"Raw fundamentals data for {ticker}:")
            for key, value in fundamentals.items():
                if value == 'N/A' or value is None:
                    print(f"  ❌ {key}: {value} (PROBLEM)")
                else:
                    print(f"  ✅ {key}: {value}")
            
            # Also test the raw yfinance data
            import yfinance as yf
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                print(f"\n📊 Raw yfinance info keys available:")
                keys_with_data = []
                na_keys = []
                for key, value in info.items():
                    if key in ['sector', 'industry', 'country', 'marketCap', 'trailingPE', 'dividendYield', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow']:
                        if value is not None and value != 'N/A' and value != '':
                            keys_with_data.append(f"{key}: {value}")
                        else:
                            na_keys.append(f"{key}: {value}")
                
                if keys_with_data:
                    print(f"  ✅ Available data: {', '.join(keys_with_data)}")
                if na_keys:
                    print(f"  ❌ Missing/N/A data: {', '.join(na_keys)}")
                    
                # Check if it's detected as ETF
                long_name = info.get('longName', ticker)
                if 'ETF' in long_name.upper():
                    print(f"  ℹ️  Detected as ETF: {long_name}")
                    
            except Exception as e:
                print(f"  ❌ Error getting raw yfinance data: {e}")
                
        except Exception as e:
            print(f"  ❌ Error fetching fundamentals: {e}")
            
    print("\n" + "=" * 80)
    print("🔍 Analysis Complete")
    
    # Let's also test a normal stock ticker for comparison
    print(f"\n📈 Testing normal stock for comparison: AAPL")
    print("-" * 40)
    try:
        fundamentals = fetcher.fetch_fundamentals("AAPL")
        for key, value in fundamentals.items():
            if value == 'N/A' or value is None:
                print(f"  ❌ {key}: {value}")
            else:
                print(f"  ✅ {key}: {value}")
    except Exception as e:
        print(f"  ❌ Error fetching AAPL fundamentals: {e}")

if __name__ == "__main__":
    test_fundamentals_data()