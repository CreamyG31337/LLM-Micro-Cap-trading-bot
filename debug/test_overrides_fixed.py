#!/usr/bin/env python3
"""
Test script to verify fundamentals overrides are working after clearing cache
============================================================================
"""

import sys
from pathlib import Path

# Add the current directory to Python path to import modules
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from config.settings import get_settings

def test_overrides_after_cache_clear():
    """Test that fundamentals overrides are working after clearing cache"""
    
    # Your problematic tickers from the prompt screen
    test_tickers = [
        "VFV.TO",    # Should show: Large Cap / US Equity ETF 
        "VOO",       # Should show: Large Cap / US Equity ETF
        "VTI",       # Should show: Large Cap / US Total Market ETF
        "XEQT.TO",   # Should show: Large Cap / Global Equity ETF
        "XGD.TO",    # Should show: Materials / Gold ETF
        "XHAK.TO",   # Should show: Technology / Cybersecurity ETF
        "XHC.TO",    # Should show: Healthcare / Healthcare ETF
        "XIC.TO",    # Should show: Large Cap / Canadian Equity ETF
        "ZEA.TO"     # Should show: Financials / Canadian Banks ETF
    ]
    
    # Initialize the market data fetcher
    settings = get_settings()
    price_cache = PriceCache()
    fetcher = MarketDataFetcher(cache_instance=price_cache)
    
    print("🧹 Clearing fundamentals cache first...")
    
    # Clear the fundamentals cache
    try:
        # Access private cache attribute to clear it
        fetcher._fund_cache.clear()
        fetcher._fund_cache_meta.clear()
        print("✅ In-memory fundamentals cache cleared")
        
        # Also try to clear any disk cache
        fundamentals_cache_path = Path("cache/fundamentals_cache.json")
        if fundamentals_cache_path.exists():
            fundamentals_cache_path.unlink()
            print("✅ Disk fundamentals cache cleared")
            
    except Exception as e:
        print(f"⚠️  Cache clearing had issues: {e}")
    
    print("\n🔍 Testing Fundamentals Overrides (After Cache Clear)")
    print("=" * 80)
    
    for ticker in test_tickers:
        print(f"\n📈 Testing {ticker}")
        print("-" * 40)
        
        try:
            fundamentals = fetcher.fetch_fundamentals(ticker)
            
            sector = fundamentals.get('sector', 'N/A')
            industry = fundamentals.get('industry', 'N/A')
            
            if sector != 'N/A' and industry != 'N/A':
                print(f"  ✅ Sector: {sector}")
                print(f"  ✅ Industry: {industry}")
                print(f"  ✅ Country: {fundamentals.get('country', 'N/A')}")
            else:
                print(f"  ❌ Sector: {sector} (STILL SHOWING N/A)")
                print(f"  ❌ Industry: {industry} (STILL SHOWING N/A)")
                print(f"  ❌ This indicates the override is not being applied!")
                
                # Debug: check if override exists
                if hasattr(fetcher, '_fundamentals_overrides'):
                    override_data = fetcher._fundamentals_overrides.get(ticker.upper())
                    if override_data:
                        print(f"  🔍 Override found: {override_data}")
                    else:
                        print(f"  🔍 No override found for key: {ticker.upper()}")
                        # Check what keys are actually in the overrides
                        print(f"  🔍 Available override keys: {list(fetcher._fundamentals_overrides.keys())[:10]}...")
                
        except Exception as e:
            print(f"  ❌ Error fetching fundamentals: {e}")
            
    print("\n" + "=" * 80)
    print("🔍 Override Test Complete")

if __name__ == "__main__":
    test_overrides_after_cache_clear()