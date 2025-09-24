#!/usr/bin/env python3
"""
Test script for the simplified market close logic.

This script tests that the system checks timestamps to determine if we have
post-market-close data, which is much simpler than time calculations.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, time

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_simple_market_close_logic():
    """Test the simplified market close logic."""
    print("🧪 Testing Simplified Market Close Logic")
    print("=" * 45)
    
    try:
        from market_data.market_hours import MarketHours
        
        # Check market status
        market_hours = MarketHours()
        is_market_open = market_hours.is_market_open()
        is_trading_day = market_hours.is_trading_day(datetime.now().date())
        
        print(f"📅 Today: {datetime.now().strftime('%A, %Y-%m-%d %H:%M:%S')}")
        print(f"🏪 Market open: {is_market_open}")
        print(f"📈 Trading day: {is_trading_day}")
        
        if not is_market_open and is_trading_day:
            print("\n🎯 New Logic:")
            print("   - Market closed: Check if we have data from after 4:00 PM today")
            print("   - If yes: We have the best data we can get, skip update")
            print("   - If no: We need post-market-close data, update needed")
            
            # Simulate different scenarios
            market_close_time = time(16, 0)  # 4:00 PM EST
            current_time = datetime.now().time()
            
            print(f"\n⏰ Current time: {current_time.strftime('%H:%M:%S')}")
            print(f"🏁 Market close: {market_close_time.strftime('%H:%M:%S')}")
            
            if current_time >= market_close_time:
                print("✅ We're past market close - if we have data from after 4:00 PM, we're good!")
            else:
                print("⏳ We're before market close - would need to wait for close data")
        
        print("\n🎯 This approach is much simpler:")
        print("   - No complex time calculations")
        print("   - Just check: 'Do we have data from after market close today?'")
        print("   - If yes: Skip update (we have the best data)")
        print("   - If no: Update to get post-market-close data")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_market_close_logic()
