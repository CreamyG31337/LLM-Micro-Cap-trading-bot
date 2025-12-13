#!/usr/bin/env python3
"""
Quick test script to verify ensure_ticker_in_securities works correctly.
This creates a test trade and verifies the ticker is added to securities table.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime
from web_dashboard.supabase_client import SupabaseClient

def test_ensure_ticker_in_securities():
    """Test that tickers are automatically added to securities table on trade"""
    
    print("🧪 Testing Auto-Population of Securities Table")
    print("=" * 60)
    
    # Initialize client with service role (admin access)
    try:
        client = SupabaseClient(use_service_role=True)
        print("✅ Connected to Supabase")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    # Test ticker that might not exist in securities
    test_ticker = "AAPL"
    
    print(f"\n📊 Testing with ticker: {test_ticker}")
    
    # Check if ticker exists before
    before = client.supabase.table('securities').select('*').eq('ticker', test_ticker).execute()
    print(f"   Ticker exists before: {len(before.data) > 0}")
    if before.data:
        print(f"   Company name before: {before.data[0].get('company_name', 'NULL')}")
    
    # Create a test trade for TEST fund (never touch real funds!)
    print(f"\n📝 Creating test trade for {test_ticker} in TEST fund...")
    trade_df = pd.DataFrame([{
        'Date': datetime.now(),
        'Fund': 'TEST',  # Use TEST fund only!
        'Ticker': test_ticker,
        'Currency': 'USD',
        'Shares': 100,
        'Price': 150.0,
        'Cost Basis': 15000.0,
        'PnL': 0.0,
        'Reason': 'AUTO_POPULATE_TEST'
    }])
    
    # Upsert trade (should trigger ensure_ticker_in_securities)
    result = client.upsert_trade_log(trade_df)
    
    if result:
        print("✅ Trade logged successfully")
    else:
        print("❌ Failed to log trade")
        return False
    
    # Check if ticker exists after
    print(f"\n🔍 Checking securities table...")
    after = client.supabase.table('securities').select('*').eq('ticker', test_ticker).execute()
    
    if after.data:
        ticker_data = after.data[0]
        print(f"✅ Ticker {test_ticker} found in securities table!")
        print(f"   Company Name: {ticker_data.get('company_name', 'NULL')}")
        print(f"   Sector: {ticker_data.get('sector', 'NULL')}")
        print(f"   Industry: {ticker_data.get('industry', 'NULL')}")
        print(f"   Currency: {ticker_data.get('currency', 'NULL')}")
        
        # Cleanup: delete test trade (only from TEST fund!)
        print(f"\n🧹 Cleaning up test trade from TEST fund...")
        client.supabase.table('trade_log').delete().eq('fund', 'TEST').eq('ticker', test_ticker).eq('reason', 'AUTO_POPULATE_TEST').execute()
        print("✅ Test trade removed from TEST fund")
        
        return True
    else:
        print(f"❌ Ticker {test_ticker} NOT found in securities table")
        return False

if __name__ == "__main__":
    success = test_ensure_ticker_in_securities()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 TEST PASSED - Auto-population working correctly!")
    else:
        print("❌ TEST FAILED - Auto-population not working")
    
    sys.exit(0 if success else 1)
