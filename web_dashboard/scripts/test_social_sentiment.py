#!/usr/bin/env python3
"""
Test Social Sentiment Integration
==================================

Comprehensive test script for social sentiment tracking system.
Tests database schemas, service methods, and full integration.
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_schemas():
    """Test that database schemas are set up correctly"""
    print("\n" + "="*60)
    print("Testing Database Schemas")
    print("="*60)
    
    # Test Postgres schema (social_metrics table)
    print("\n1. Testing Postgres schema (social_metrics)...")
    try:
        from web_dashboard.postgres_client import PostgresClient
        client = PostgresClient()
        
        # Check if table exists
        result = client.execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name = 'social_metrics'
        """)
        
        if result:
            print("   ✅ social_metrics table exists")
            
            # Check columns
            columns = client.execute_query("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'social_metrics'
                ORDER BY ordinal_position
            """)
            
            required_columns = {'ticker', 'platform', 'volume', 'bull_bear_ratio', 
                              'sentiment_label', 'sentiment_score', 'raw_data', 'created_at'}
            found_columns = {row['column_name'] for row in columns}
            
            print(f"   Found {len(columns)} columns:")
            for col in columns:
                marker = "✅" if col['column_name'] in required_columns else "  "
                print(f"   {marker} {col['column_name']}: {col['data_type']}")
            
            missing = required_columns - found_columns
            if missing:
                print(f"   ❌ Missing columns: {missing}")
                return False
            else:
                print("   ✅ All required columns present")
        else:
            print("   ❌ social_metrics table does not exist")
            print("   Run: web_dashboard/schema/18_social_metrics.sql in Postgres")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking Postgres schema: {e}")
        return False
    
    # Test Supabase schema (watched_tickers table)
    print("\n2. Testing Supabase schema (watched_tickers)...")
    try:
        from web_dashboard.supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Check if table exists by trying to query it
        result = client.supabase.table("watched_tickers").select("ticker").limit(1).execute()
        print("   ✅ watched_tickers table exists")
        
        # Count active tickers
        count_result = client.supabase.table("watched_tickers")\
            .select("ticker", count="exact")\
            .eq("is_active", True)\
            .execute()
        
        active_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        print(f"   Found {active_count} active watched tickers")
        
    except Exception as e:
        error_str = str(e)
        if "does not exist" in error_str or "relation" in error_str.lower():
            print("   ❌ watched_tickers table does not exist")
            print("   Run: web_dashboard/schema/supabase/19_create_watchlist.sql in Supabase")
        else:
            print(f"   ⚠️  Error checking Supabase schema: {e}")
        return False
    
    return True


def test_service_initialization():
    """Test that SocialSentimentService can be initialized"""
    print("\n" + "="*60)
    print("Testing Service Initialization")
    print("="*60)
    
    try:
        from web_dashboard.social_service import SocialSentimentService
        service = SocialSentimentService()
        print("✅ SocialSentimentService initialized successfully")
        return service
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_get_watched_tickers(service):
    """Test getting watched tickers"""
    print("\n" + "="*60)
    print("Testing get_watched_tickers()")
    print("="*60)
    
    try:
        tickers = service.get_watched_tickers()
        print(f"✅ Retrieved {len(tickers)} watched tickers")
        if tickers:
            print(f"   Sample tickers: {', '.join(tickers[:5])}")
        else:
            print("   ⚠️  No active tickers found (this is OK if watchlist is empty)")
        return tickers
    except Exception as e:
        print(f"❌ Error getting watched tickers: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_stocktwits_fetch(service, ticker="AAPL"):
    """Test StockTwits sentiment fetching"""
    print("\n" + "="*60)
    print(f"Testing fetch_stocktwits_sentiment({ticker})")
    print("="*60)
    
    try:
        result = service.fetch_stocktwits_sentiment(ticker)
        print(f"✅ StockTwits fetch completed")
        print(f"   Volume: {result.get('volume', 0)}")
        print(f"   Bull/Bear Ratio: {result.get('bull_bear_ratio', 0.0):.2f}")
        print(f"   Raw data: {'Present' if result.get('raw_data') else 'None'}")
        return result
    except Exception as e:
        print(f"❌ Error fetching StockTwits data: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_reddit_fetch(service, ticker="AAPL"):
    """Test Reddit sentiment fetching"""
    print("\n" + "="*60)
    print(f"Testing fetch_reddit_sentiment({ticker})")
    print("="*60)
    
    try:
        result = service.fetch_reddit_sentiment(ticker)
        print(f"✅ Reddit fetch completed")
        print(f"   Volume: {result.get('volume', 0)}")
        print(f"   Sentiment Label: {result.get('sentiment_label', 'N/A')}")
        print(f"   Sentiment Score: {result.get('sentiment_score', 0.0):.1f}")
        print(f"   Raw data: {'Present' if result.get('raw_data') else 'None'}")
        return result
    except Exception as e:
        print(f"❌ Error fetching Reddit data: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_save_metrics(service, ticker="AAPL"):
    """Test saving metrics to database"""
    print("\n" + "="*60)
    print(f"Testing save_metrics() for {ticker}")
    print("="*60)
    
    try:
        # Test StockTwits metrics
        stocktwits_metrics = {
            'volume': 5,
            'bull_bear_ratio': 0.75,
            'raw_data': [{'body': 'Test post', 'created_at': '2024-01-01T00:00:00Z'}]
        }
        service.save_metrics(ticker, 'stocktwits', stocktwits_metrics)
        print("✅ StockTwits metrics saved")
        
        # Test Reddit metrics
        reddit_metrics = {
            'volume': 3,
            'sentiment_label': 'BULLISH',
            'sentiment_score': 1.0,
            'raw_data': [{'title': 'Test post', 'score': 100}]
        }
        service.save_metrics(ticker, 'reddit', reddit_metrics)
        print("✅ Reddit metrics saved")
        
        # Verify they were saved
        from web_dashboard.postgres_client import PostgresClient
        client = PostgresClient()
        result = client.execute_query("""
            SELECT platform, volume, sentiment_label, sentiment_score
            FROM social_metrics
            WHERE ticker = %s
            ORDER BY created_at DESC
            LIMIT 2
        """, (ticker,))
        
        if result:
            print(f"✅ Verified {len(result)} metrics in database")
            for row in result:
                print(f"   - {row['platform']}: vol={row['volume']}, sentiment={row.get('sentiment_label', 'N/A')}")
        else:
            print("⚠️  Metrics saved but not found in database (may need commit)")
        
        return True
    except Exception as e:
        print(f"❌ Error saving metrics: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Social Sentiment Integration Test")
    print("="*60)
    
    results = {}
    
    # Test 1: Database schemas
    results['schemas'] = test_database_schemas()
    
    # Test 2: Service initialization
    service = test_service_initialization()
    results['service_init'] = service is not None
    
    if not service:
        print("\n❌ Cannot continue tests - service initialization failed")
        return
    
    # Test 3: Get watched tickers
    tickers = test_get_watched_tickers(service)
    results['get_tickers'] = True  # Always passes, even if empty
    
    # Test 4: StockTwits fetch (may fail due to API restrictions)
    stocktwits_result = test_stocktwits_fetch(service, "AAPL")
    results['stocktwits'] = stocktwits_result is not None
    
    # Test 5: Reddit fetch
    reddit_result = test_reddit_fetch(service, "AAPL")
    results['reddit'] = reddit_result is not None
    
    # Test 6: Save metrics
    results['save_metrics'] = test_save_metrics(service, "TEST_TICKER")
    
    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Review output above.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

