#!/usr/bin/env python3
"""
Test RSS Feed Parsing
=====================

Simple test script to verify RSS parsing and ticker extraction.
"""

import sys
from pathlib import Path

# Add web_dashboard to path
project_root = Path(__file__).resolve().parent.parent
web_dashboard_path = project_root / "web_dashboard"
sys.path.insert(0, str(web_dashboard_path))

from rss_utils import get_rss_client

def test_rss_parsing():
    """Test RSS feed parsing with StockTwits feed."""
    print("=" * 70)
    print("RSS FEED PARSING TEST")
    print("=" * 70)
    print()
    
    # Test with StockTwits (has ticker metadata)
    stocktwits_url = "https://www.stocktwits.com/sitemap/rss_feed.xml"
    
    print(f"Testing feed: {stocktwits_url}")
    print()
    
    rss_client = get_rss_client()
    feed_data = rss_client.fetch_feed(stocktwits_url)
    
    if not feed_data:
        print("❌ Failed to fetch feed")
        return False
    
    items = feed_data.get('items', [])
    print(f"✅ Fetched {len(items)} items (after junk filtering)")
    print()
    
    if not items:
        print("⚠️ No items found after filtering")
        return False
    
    # Show first few items with ticker info
    print("Sample articles with ticker extraction:")
    print("-" * 70)
    
    for i, item in enumerate(items[:5], 1):
        title = item.get('title', 'No title')
        tickers = item.get('tickers', [])
        url = item.get('url', '')
        
        print(f"\n{i}. {title[:60]}...")
        print(f"   URL: {url[:80]}...")
        print(f"   Tickers: {tickers if tickers else 'None extracted'}")
        print(f"   Source: {item.get('source', 'Unknown')}")
        
        # Show content preview
        content = item.get('content', '')
        if content:
            print(f"   Content preview: {content[:100]}...")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    
    # Summary
    items_with_tickers = sum(1 for item in items if item.get('tickers'))
    print(f"\nSummary:")
    print(f"  Total items: {len(items)}")
    print(f"  Items with tickers: {items_with_tickers}")
    print(f"  Items without tickers: {len(items) - items_with_tickers}")
    
    if items_with_tickers == 0:
        print("\n⚠️ WARNING: No tickers extracted from any items!")
        print("   This suggests the ticker extraction logic may need review.")
    
    return True

if __name__ == "__main__":
    try:
        success = test_rss_parsing()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
