#!/usr/bin/env python3
"""
Test Paywall Bypass System
===========================

Test script to verify paywall detection and bypass (12ft.io, archive.is) work correctly.
Takes a URL parameter to test a specific paywalled article.
"""

import sys
import argparse
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_paywall_bypass(url: str):
    """Test paywall bypass for a specific URL."""
    print(f"\n{'='*80}")
    print(f"Testing Paywall Bypass for: {url}")
    print(f"{'='*80}\n")
    
    try:
        from research_utils import extract_article_content
        from paywall_detector import detect_paywall, is_paywalled_article
        from archive_service import check_archived
        
        # Step 1: Extract content from original URL
        print("Step 1: Extracting content from original URL...")
        result = extract_article_content(url)
        
        if not result.get('success'):
            print(f"❌ Extraction failed: {result.get('error', 'unknown error')}")
            if result.get('archive_submitted'):
                print("✅ URL was submitted to archive service for later processing")
            return
        
        content = result.get('content', '')
        title = result.get('title', 'Untitled')
        source = result.get('source', 'Unknown')
        
        print(f"✅ Content extracted successfully")
        print(f"   Title: {title[:60]}...")
        print(f"   Source: {source}")
        print(f"   Content length: {len(content)} characters")
        
        # Step 2: Check for paywall
        print(f"\nStep 2: Checking for paywall...")
        paywall_type = detect_paywall(content, url)
        
        if paywall_type:
            print(f"⚠️  Paywall detected: {paywall_type}")
            print(f"   Paywall message found in content")
            
            # Show snippet of paywall message
            if 'The article requires paid subscription' in content:
                print(f"   Found: 'The article requires paid subscription'")
            elif 'Subscribe to unlock this article' in content:
                print(f"   Found: 'Subscribe to unlock this article'")
            else:
                # Find paywall message
                lines = content.split('\n')
                for line in lines[:20]:
                    if any(keyword in line.lower() for keyword in ['subscribe', 'paid', 'subscription', 'unlock']):
                        print(f"   Paywall snippet: {line[:80]}...")
                        break
            
            # Step 3: Test archive services
            print(f"\nStep 3: Testing archive services...")
            archived_url = check_archived(url)
            
            if archived_url:
                print(f"✅ Found archived version: {archived_url}")
            else:
                print(f"ℹ️  URL not yet archived (this is normal for new articles)")
                print(f"   Archive services require time to process submissions")
        else:
            print(f"✅ No paywall detected - article is accessible")
            print(f"   Content preview: {content[:200]}...")
        
        print(f"\n{'='*80}")
        print("Test completed!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Test paywall bypass system with a specific URL')
    parser.add_argument('url', help='URL of article to test')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    test_paywall_bypass(args.url)


if __name__ == "__main__":
    main()

