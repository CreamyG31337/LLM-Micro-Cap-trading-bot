#!/usr/bin/env python3
"""
Check the status of Chain of Thought backfill.
Shows how many articles have been processed and which ones are still missing.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")


def check_backfill_status():
    """Check how many articles have been backfilled."""
    try:
        client = PostgresClient()
        
        # Overall status
        query = """
            SELECT 
                COUNT(*) as total,
                COUNT(sentiment) as with_sentiment,
                COUNT(*) - COUNT(sentiment) as missing,
                COUNT(CASE WHEN sentiment IS NOT NULL AND claims IS NOT NULL THEN 1 END) as with_claims,
                COUNT(CASE WHEN sentiment IS NOT NULL AND fact_check IS NOT NULL THEN 1 END) as with_fact_check,
                COUNT(CASE WHEN sentiment IS NOT NULL AND conclusion IS NOT NULL THEN 1 END) as with_conclusion,
                COUNT(CASE WHEN sentiment IS NOT NULL AND logic_check IS NOT NULL THEN 1 END) as with_logic_check
            FROM research_articles
            WHERE content IS NOT NULL 
              AND LENGTH(content) > 200
        """
        
        result = client.execute_query(query)
        if not result:
            print("[ERROR] Could not query database")
            return
        
        stats = result[0]
        total = stats['total']
        with_sentiment = stats['with_sentiment']
        missing = stats['missing']
        with_claims = stats['with_claims']
        with_fact_check = stats['with_fact_check']
        with_conclusion = stats['with_conclusion']
        with_logic_check = stats['with_logic_check']
        
        print("=" * 80)
        print("Chain of Thought Backfill Status")
        print("=" * 80)
        print(f"\nTotal articles: {total}")
        print(f"With sentiment: {with_sentiment} ({with_sentiment/total*100:.1f}%)")
        print(f"Missing: {missing} ({missing/total*100:.1f}%)")
        print(f"\nChain of Thought fields:")
        print(f"  With claims: {with_claims}")
        print(f"  With fact_check: {with_fact_check}")
        print(f"  With conclusion: {with_conclusion}")
        print(f"  With logic_check: {with_logic_check}")
        
        # Sentiment distribution
        if with_sentiment > 0:
            sentiment_query = """
                SELECT sentiment, COUNT(*) as count
                FROM research_articles
                WHERE sentiment IS NOT NULL
                GROUP BY sentiment
                ORDER BY 
                    CASE sentiment
                        WHEN 'VERY_BULLISH' THEN 1
                        WHEN 'BULLISH' THEN 2
                        WHEN 'NEUTRAL' THEN 3
                        WHEN 'BEARISH' THEN 4
                        WHEN 'VERY_BEARISH' THEN 5
                    END
            """
            sentiment_result = client.execute_query(sentiment_query)
            
            if sentiment_result:
                print(f"\nSentiment Distribution:")
                for row in sentiment_result:
                    sentiment = row['sentiment']
                    count = row['count']
                    pct = count / with_sentiment * 100
                    print(f"  {sentiment}: {count} ({pct:.1f}%)")
        
        # Logic check distribution
        if with_logic_check > 0:
            logic_check_query = """
                SELECT logic_check, COUNT(*) as count
                FROM research_articles
                WHERE logic_check IS NOT NULL
                GROUP BY logic_check
                ORDER BY 
                    CASE logic_check
                        WHEN 'DATA_BACKED' THEN 1
                        WHEN 'NEUTRAL' THEN 2
                        WHEN 'HYPE_DETECTED' THEN 3
                    END
            """
            logic_check_result = client.execute_query(logic_check_query)
            
            if logic_check_result:
                print(f"\nLogic Check Distribution:")
                for row in logic_check_result:
                    logic_check = row['logic_check']
                    count = row['count']
                    pct = count / with_logic_check * 100
                    print(f"  {logic_check}: {count} ({pct:.1f}%)")
        
        # Show recent articles that are missing
        if missing > 0:
            missing_query = """
                SELECT id, title, fetched_at
                FROM research_articles
                WHERE sentiment IS NULL
                  AND content IS NOT NULL
                  AND LENGTH(content) > 200
                ORDER BY fetched_at DESC
                LIMIT 10
            """
            missing_result = client.execute_query(missing_query)
            
            if missing_result:
                print(f"\nNext articles to process (showing up to 10):")
                for i, article in enumerate(missing_result, 1):
                    try:
                        title = article['title'][:60]
                        fetched = article['fetched_at']
                        print(f"  {i}. {title}... (fetched: {fetched})")
                    except UnicodeEncodeError:
                        # Fallback for Unicode issues
                        title_safe = article['title'][:60].encode('ascii', 'ignore').decode('ascii')
                        fetched = article['fetched_at']
                        print(f"  {i}. {title_safe}... (fetched: {fetched})")
        
        print("\n" + "=" * 80)
        
        if missing == 0:
            print("[OK] All articles have been backfilled!")
        else:
            print(f"[INFO] {missing} articles still need processing")
            print("Run: python web_dashboard/scripts/backfill_chain_of_thought.py --model granite3.3:8b")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"[ERROR] Error checking status: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_backfill_status()

