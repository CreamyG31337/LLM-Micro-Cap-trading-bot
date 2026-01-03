
import sys
import os
import logging
from pathlib import Path

# Setup path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestRunner")

def test_rss_job():
    logger.info(">>> Testing RSS Feed Ingest Job...")
    try:
        from scheduler.jobs_research import rss_feed_ingest_job
        # We can't easily limit it without modifying code, but we can trust it runs fast for 5 feeds
        rss_feed_ingest_job()
        logger.info("✅ RSS Job Completed Successfully")
        return True
    except Exception as e:
        logger.error(f"❌ RSS Job Failed: {e}")
        return False

def test_market_job():
    logger.info(">>> Testing Market Research Job...")
    try:
        from scheduler.jobs_research import market_research_job
        market_research_job()
        logger.info("✅ Market Research Job Completed Successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Market Research Job Failed: {e}")
        return False

def test_subreddit_job():
    logger.info(">>> Testing Subreddit Scanner Job...")
    try:
        from scheduler.jobs_reddit_discovery import subreddit_scanner_job
        # This might take a while due to sleeping. 
        # Ideally we'd patch the sleep or just run it. 
        # For this test, we accept it runs full cycle (it only scans a few subs).
        subreddit_scanner_job()
        logger.info("✅ Subreddit Scanner Job Completed Successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Subreddit Scanner Job Failed: {e}")
        return False

if __name__ == "__main__":
    success = True
    
    if not test_rss_job(): success = False
    print("-" * 30)
    
    if not test_market_job(): success = False
    print("-" * 30)
    
    if not test_subreddit_job(): success = False
    print("-" * 30)
    
    if success:
        print("\n🎉 ALL JOBS PASSED")
        sys.exit(0)
    else:
        print("\n❌ SOME JOBS FAILED")
        sys.exit(1)
