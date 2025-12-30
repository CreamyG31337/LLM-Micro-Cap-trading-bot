#!/usr/bin/env python3
"""
Social Sentiment AI Analysis Job
=================================

Scheduled job to perform AI analysis on social sentiment data.
Similar to congress trades analysis but for social sentiment.

This job:
1. Extracts posts from raw_data into structured social_posts
2. Creates sentiment analysis sessions
3. Performs AI analysis using Ollama
4. Stores results in research database
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from social_service import SocialSentimentService

logger = logging.getLogger(__name__)

def main():
    """Run the social sentiment AI analysis job"""
    try:
        logger.info("🤖 Starting Social Sentiment AI Analysis Job")

        # Initialize service
        service = SocialSentimentService()

        # Step 1: Extract posts from raw_data
        logger.info("📝 Step 1: Extracting posts from raw_data...")
        extraction_result = service.extract_posts_from_raw_data()
        logger.info(f"✅ Extracted {extraction_result['posts_created']} posts from {extraction_result['processed']} metrics")

        # Step 2: Create sentiment sessions
        logger.info("🎯 Step 2: Creating sentiment analysis sessions...")
        session_result = service.create_sentiment_sessions()
        logger.info(f"✅ Created {session_result['sessions_created']} sessions with {session_result['posts_assigned']} posts")

        # Step 3: Perform AI analysis on pending sessions
        logger.info("🧠 Step 3: Performing AI analysis...")
        analyses_completed = 0

        # Get sessions that need analysis
        postgres = service.postgres
        pending_sessions_query = """
            SELECT id, ticker, platform FROM sentiment_sessions
            WHERE needs_ai_analysis = TRUE
            ORDER BY created_at ASC
            LIMIT 10  -- Process in batches
        """
        pending_sessions = postgres.execute_query(pending_sessions_query)

        for session in pending_sessions:
            session_id = session['id']
            ticker = session['ticker']
            platform = session['platform']

            logger.info(f"Analyzing session {session_id} for {ticker} ({platform})...")
            result = service.analyze_sentiment_session(session_id)

            if result:
                analyses_completed += 1
                logger.info(f"✅ Completed AI analysis for {ticker}")
            else:
                logger.warning(f"❌ Failed AI analysis for session {session_id}")

        logger.info(f"✅ Completed {analyses_completed} AI analyses")

        # Step 4: Cleanup old data
        logger.info("🧹 Step 4: Running cleanup...")
        cleanup_result = service.run_daily_cleanup()
        logger.info(f"✅ Cleanup complete: {cleanup_result['rows_updated']} updated, {cleanup_result['rows_deleted']} deleted")

        logger.info("🎉 Social Sentiment AI Analysis Job completed successfully!")

    except Exception as e:
        logger.error(f"❌ Social Sentiment AI Analysis Job failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    main()