#!/usr/bin/env python3
"""
Find potentially bullish articles by searching for keywords and checking sentiment.
Non-interactive script to help find good test articles.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.research_repository import ResearchRepository
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")


def find_potentially_bullish_articles(limit: int = 20):
    """Find articles that might be bullish based on keywords."""
    try:
        db_client = PostgresClient()
        
        # Keywords that often indicate bullish sentiment
        bullish_keywords = [
            "bargain", "buy", "upside", "growth", "rally", "surge", "gain",
            "beat", "outperform", "upgrade", "bullish", "positive", "strong",
            "expansion", "acquisition", "partnership", "breakthrough", "record",
            "win", "success", "profit", "earnings beat", "price target"
        ]
        
        # Build search query
        keyword_conditions = " OR ".join([f"title ILIKE %s" for _ in bullish_keywords])
        params = [f"%{kw}%" for kw in bullish_keywords]
        
        query = f"""
            SELECT id, title, tickers, sector, article_type, source,
                   published_at, sentiment, sentiment_score
            FROM research_articles
            WHERE ({keyword_conditions})
              AND content IS NOT NULL
              AND LENGTH(content) > 200
            ORDER BY 
              CASE 
                WHEN sentiment_score IS NOT NULL THEN sentiment_score
                ELSE 0
              END DESC,
              fetched_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        articles = db_client.execute_query(query, tuple(params))
        
        if not articles:
            print("\n[INFO] No articles found with bullish keywords")
            return []
        
        print(f"\n{'='*80}")
        print(f"Found {len(articles)} potentially bullish articles:")
        print(f"{'='*80}\n")
        
        for i, article in enumerate(articles, 1):
            article_id = str(article.get('id', 'N/A'))
            title = article.get('title', 'Untitled')
            tickers = article.get('tickers', [])
            if isinstance(tickers, str):
                tickers = [tickers] if tickers else []
            ticker_str = ', '.join(tickers) if tickers else 'N/A'
            sentiment = article.get('sentiment', 'N/A')
            sentiment_score = article.get('sentiment_score', 'N/A')
            
            print(f"{i}. {title}")
            print(f"   ID: {article_id}")
            print(f"   Ticker: {ticker_str} | Sentiment: {sentiment} (Score: {sentiment_score})")
            print()
        
        return articles
        
    except Exception as e:
        print(f"[ERROR] Error finding articles: {e}")
        import traceback
        traceback.print_exc()
        return []


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find potentially bullish articles for testing"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=20,
        help="Maximum number of results (default: 20)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Finding Potentially Bullish Articles")
    print("=" * 80)
    print("\nSearching for articles with bullish keywords...")
    print("(bargain, buy, upside, growth, rally, surge, beat, upgrade, etc.)")
    
    articles = find_potentially_bullish_articles(limit=args.limit)
    
    if articles:
        print(f"\n{'='*80}")
        print("To test these articles:")
        print("1. Copy the article IDs you want")
        print("2. Run: python web_dashboard/scripts/test_chain_of_thought_prompt.py")
        print("3. Choose option 4 (Enter specific article IDs)")
        print("4. Paste the IDs (comma-separated)")
        print(f"{'='*80}")


if __name__ == "__main__":
    main()

