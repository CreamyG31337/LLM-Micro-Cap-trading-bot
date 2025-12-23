import os
import sys
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data.data_fetcher import YFinanceDataFetcher
from market_data.price_cache import PriceCache

def test_fetch_today_prices():
    """Test fetching prices for today to see what happens"""
    
    fetcher = YFinanceDataFetcher()
    cache = PriceCache()
    
    # Test with a sample ticker
    ticker = "PLTR"
    today = date.today()
    
    print(f"Testing price fetch for {ticker} on {today}")
    print(f"Current time: {datetime.now()}")
    
    # Try to fetch like the job does
    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())
    
    print(f"\nFetching with start={start_dt}, end={end_dt}")
    
    result = fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
    
    if result and result.df is not None and not result.df.empty:
        print(f"\n✅ SUCCESS - Got {len(result.df)} rows")
        print(f"Source: {result.source}")
        print(f"\nData:")
        print(result.df[['Close']].tail())
        print(f"\nLatest close price: ${result.df['Close'].iloc[-1]}")
    else:
        print(f"\n❌ FAILED - No data returned")
        print(f"Result: {result}")
        
        # Check cache
        print("\nChecking cache...")
        cached = cache.get_cached_price(ticker)
        if cached is not None and not cached.empty:
            print(f"✅ Cache has data - {len(cached)} rows")
            print(f"Latest cached close: ${cached['Close'].iloc[-1]}")
        else:
            print("❌ No cached data either")

if __name__ == "__main__":
    test_fetch_today_prices()
