#!/usr/bin/env python3
"""
Quick script to find article IDs by title, ticker, or keywords.
Useful for finding specific articles to test with Chain of Thought analysis.
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


def search_articles(search_term: str = None, ticker: str = None, limit: int = 10):
    """Search for articles and display their IDs."""
    try:
        repo = ResearchRepository()
        db_client = PostgresClient()
        
        if ticker:
            print(f"\nSearching for articles with ticker: {ticker}")
            articles = repo.get_articles_by_ticker(ticker, limit=limit)
        elif search_term:
            print(f"\nSearching for articles matching: '{search_term}'")
            # Try both text search and title search
            articles = repo.search_articles(search_term, limit=limit)
            
            # Also search titles directly
            title_query = """
                SELECT id, title, tickers, sector, article_type, source, 
                       published_at, sentiment
                FROM research_articles
                WHERE title ILIKE %s
                ORDER BY fetched_at DESC
                LIMIT %s
            """
            title_results = db_client.execute_query(
                title_query, 
                (f"%{search_term}%", limit)
            )
            
            # Merge results (avoid duplicates)
            seen_ids = {str(a.get('id')) for a in articles}
            for article in title_results:
                if str(article.get('id')) not in seen_ids:
                    articles.append(article)
        else:
            print("\nShowing recent articles...")
            query = """
                SELECT id, title, tickers, sector, article_type, source,
                       published_at, sentiment
                FROM research_articles
                WHERE content IS NOT NULL
                ORDER BY fetched_at DESC
                LIMIT %s
            """
            articles = db_client.execute_query(query, (limit,))
        
        if not articles:
            print("\n[INFO] No articles found")
            return
        
        print(f"\n{'='*80}")
        print(f"Found {len(articles)} articles:")
        print(f"{'='*80}\n")
        
        for i, article in enumerate(articles, 1):
            article_id = str(article.get('id', 'N/A'))
            title = article.get('title', 'Untitled')
            tickers = article.get('tickers', [])
            if isinstance(tickers, str):
                tickers = [tickers] if tickers else []
            ticker_str = ', '.join(tickers) if tickers else 'N/A'
            sector = article.get('sector', 'N/A')
            article_type = article.get('article_type', 'N/A')
            sentiment = article.get('sentiment', 'N/A')
            published = article.get('published_at', 'N/A')
            
            print(f"{i}. {title}")
            print(f"   ID: {article_id}")
            print(f"   Ticker: {ticker_str} | Sector: {sector} | Type: {article_type}")
            print(f"   Sentiment: {sentiment} | Published: {published}")
            print()
        
        print(f"{'='*80}")
        print("\nTo use these articles in the test script:")
        print("1. Copy the article IDs you want")
        print("2. Run: python web_dashboard/scripts/test_chain_of_thought_prompt.py")
        print("3. Choose option 4 (Enter specific article IDs)")
        print("4. Paste the IDs (comma-separated)")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"[ERROR] Error searching articles: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Find article IDs by title, ticker, or keywords"
    )
    parser.add_argument(
        "-s", "--search",
        type=str,
        help="Search text (searches title and content)"
    )
    parser.add_argument(
        "-t", "--ticker",
        type=str,
        help="Ticker symbol (e.g., META, PANW)"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Always use command-line mode (non-interactive)
    search_articles(
        search_term=args.search,
        ticker=args.ticker,
        limit=args.limit
    )


if __name__ == "__main__":
    main()

