#!/usr/bin/env python3
"""
Test Social APIs
================

Test script to verify StockTwits API structure and mock Reddit PRAW logic.
Run this before implementing the full social sentiment service.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(project_root / "web_dashboard" / ".env")

logger = None
try:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
except:
    pass

def log(message: str):
    """Log message to console and logger if available"""
    # Handle Windows console encoding issues
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace problematic Unicode characters for Windows console
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)
    if logger:
        logger.info(message)


def test_stocktwits_api(ticker: str = "AAPL") -> Optional[Dict[str, Any]]:
    """Test StockTwits API endpoint and parse response structure.
    
    Args:
        ticker: Ticker symbol to test (default: AAPL)
        
    Returns:
        Parsed JSON response or None if failed
    """
    log(f"\n{'='*60}")
    log(f"Testing StockTwits API for {ticker}")
    log(f"{'='*60}")
    
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    
    # Use browser-like User-Agent (required by StockTwits)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        log(f"Requesting: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        log(f"\n✅ Success! Status: {response.status_code}")
        log(f"\nResponse structure:")
        log(f"  - Top-level keys: {list(data.keys())}")
        
        # Check for messages
        if 'messages' in data:
            messages = data['messages']
            log(f"  - Messages count: {len(messages)}")
            
            if messages:
                # Analyze first message structure
                first_msg = messages[0]
                log(f"\n  First message structure:")
                log(f"    - Keys: {list(first_msg.keys())}")
                
                # Check for sentiment entities
                if 'entities' in first_msg:
                    entities = first_msg['entities']
                    log(f"    - Entities keys: {list(entities.keys())}")
                    
                    if 'sentiment' in entities:
                        sentiment = entities['sentiment']
                        log(f"    - Sentiment: {sentiment}")
                    else:
                        log(f"    - No sentiment in entities")
                
                # Check for created_at timestamp
                if 'created_at' in first_msg:
                    created_at = first_msg['created_at']
                    log(f"    - Created at: {created_at}")
                    
                    # Parse timestamp and check if within last hour
                    try:
                        # StockTwits uses ISO format like "2024-01-15T10:30:00Z"
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        now = datetime.now(timezone.utc)
                        age_minutes = (now - dt).total_seconds() / 60
                        log(f"    - Age: {age_minutes:.1f} minutes")
                        
                        if age_minutes <= 60:
                            log(f"    - ✅ Within last 60 minutes")
                        else:
                            log(f"    - ⚠️  Older than 60 minutes")
                    except Exception as e:
                        log(f"    - ⚠️  Could not parse timestamp: {e}")
                
                # Count sentiment labels in all messages
                bull_count = 0
                bear_count = 0
                recent_messages = []
                cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=60)
                
                for msg in messages:
                    # Check if message is within last hour
                    if 'created_at' in msg:
                        try:
                            msg_dt = datetime.fromisoformat(msg['created_at'].replace('Z', '+00:00'))
                            if msg_dt >= cutoff_time:
                                recent_messages.append(msg)
                                
                                # Check sentiment
                                if 'entities' in msg and 'sentiment' in msg['entities']:
                                    sentiment = msg['entities']['sentiment']
                                    if sentiment and 'basic' in sentiment:
                                        basic = sentiment['basic']
                                        if basic == 'Bullish':
                                            bull_count += 1
                                        elif basic == 'Bearish':
                                            bear_count += 1
                        except:
                            pass
                
                log(f"\n  Volume calculation (last 60 minutes):")
                log(f"    - Recent messages: {len(recent_messages)}")
                log(f"    - Bullish: {bull_count}")
                log(f"    - Bearish: {bear_count}")
                
                if bull_count + bear_count > 0:
                    ratio = bull_count / (bull_count + bear_count)
                    log(f"    - Bull/Bear Ratio: {ratio:.2f}")
                else:
                    log(f"    - Bull/Bear Ratio: 0.0 (no labels)")
        
        # Save full response to file for inspection
        output_file = project_root / "web_dashboard" / "scripts" / f"stocktwits_{ticker}_response.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        log(f"\n  Full response saved to: {output_file}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        log(f"\n❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        log(f"\n❌ JSON decode failed: {e}")
        return None
    except Exception as e:
        log(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_reddit_public_api(ticker: str = "AAPL") -> Optional[Dict[str, Any]]:
    """Test Reddit public JSON endpoint and parse response structure.
    
    Args:
        ticker: Ticker symbol to test (default: AAPL)
        
    Returns:
        Parsed JSON response or None if failed
    """
    log(f"\n{'='*60}")
    log(f"Testing Reddit Public JSON API for {ticker}")
    log(f"{'='*60}")
    
    # Use browser-like User-Agent (required to avoid 429 errors)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Test search query
    query = f"${ticker}"
    url = f"https://www.reddit.com/search.json?q={query}&sort=new&t=day&limit=10"
    
    try:
        log(f"Requesting: {url}")
        log("   (Using public JSON endpoint - no authentication required)")
        
        # Rate limiting: wait 2 seconds before request
        import time
        time.sleep(2)
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 429:
            log(f"\n⚠️  Rate limit hit (429). Reddit requires delays between requests.")
            log("   The service will automatically handle this with 2-second delays.")
            return None
        
        response.raise_for_status()
        data = response.json()
        
        log(f"\n✅ Success! Status: {response.status_code}")
        log(f"\nResponse structure:")
        log(f"  - Top-level keys: {list(data.keys())}")
        
        # Parse nested structure
        if 'data' in data and 'children' in data['data']:
            children = data['data']['children']
            log(f"  - Children count: {len(children)}")
            
            if children:
                # Analyze first post
                first_post_data = children[0].get('data', {})
                log(f"\n  First post structure:")
                log(f"    - Keys: {list(first_post_data.keys())[:10]}...")  # Show first 10 keys
                
                # Extract key fields
                title = first_post_data.get('title', '')
                selftext = first_post_data.get('selftext', '')
                ups = first_post_data.get('ups', 0)
                num_comments = first_post_data.get('num_comments', 0)
                created_utc = first_post_data.get('created_utc', 0)
                subreddit = first_post_data.get('subreddit', '')
                
                log(f"    - Title: {title[:50]}...")
                log(f"    - Subreddit: r/{subreddit}")
                log(f"    - Upvotes: {ups}")
                log(f"    - Comments: {num_comments}")
                
                if created_utc:
                    from datetime import datetime, timezone
                    post_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                    now = datetime.now(timezone.utc)
                    age_hours = (now - post_dt).total_seconds() / 3600
                    log(f"    - Created: {post_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    log(f"    - Age: {age_hours:.1f} hours")
                    
                    if age_hours <= 24:
                        log(f"    - ✅ Within last 24 hours")
                    else:
                        log(f"    - ⚠️  Older than 24 hours")
        
        # Save full response to file for inspection
        output_file = project_root / "web_dashboard" / "scripts" / f"reddit_{ticker}_response.json"
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        log(f"\n  Full response saved to: {output_file}")
        
        log("\n📋 Reddit Integration Notes:")
        log("   - Uses public JSON endpoint (no API key required)")
        log("   - Requires browser-like User-Agent header")
        log("   - Rate limiting: 2-second delay between requests")
        log("   - Handles 429 errors gracefully with longer waits")
        
        return data
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            log(f"\n⚠️  Rate limit (429). Reddit requires delays between requests.")
        else:
            log(f"\n❌ HTTP error: {e}")
        return None
    except requests.exceptions.RequestException as e:
        log(f"\n❌ Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        log(f"\n❌ JSON decode failed: {e}")
        return None
    except Exception as e:
        log(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function"""
    log("\n" + "="*60)
    log("Social APIs Test Script")
    log("="*60)
    
    # Test StockTwits
    ticker = "AAPL"
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
    
    stocktwits_data = test_stocktwits_api(ticker)
    
    # Test Reddit public API
    reddit_data = test_reddit_public_api(ticker)
    
    log("\n" + "="*60)
    log("Test Complete")
    log("="*60)
    log("\nNext steps:")
    log("1. Review StockTwits response structure")
    log("2. Configure Reddit credentials in .env file")
    log("3. Implement SocialSentimentService")
    log("4. Test full pipeline")


if __name__ == "__main__":
    main()

