#!/usr/bin/env python3
"""
Diagnostic script to check database for reports and articles
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.research_repository import ResearchRepository


def format_datetime(dt):
    """Format datetime for display"""
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    """Diagnose database and show all articles"""
    try:
        client = PostgresClient()
        
        # Test connection
        print("Testing database connection...")
        if not client.test_connection():
            print("ERROR: Database connection failed!")
            return 1
        print("OK: Database connection successful\n")
        
        # Check total articles
        total_query = "SELECT COUNT(*) as count FROM research_articles"
        total_result = client.execute_query(total_query)
        total_count = total_result[0]['count'] if total_result else 0
        print(f"Total articles in database: {total_count}\n")
        
        if total_count == 0:
            print("No articles found in database at all.")
            print("This could mean:")
            print("  - The database is empty")
            print("  - Articles are stored in a different table")
            print("  - There's a connection to the wrong database")
            return 0
        
        # Check by article type
        print("Articles by type:")
        type_query = """
            SELECT article_type, COUNT(*) as count
            FROM research_articles
            GROUP BY article_type
            ORDER BY count DESC
        """
        type_results = client.execute_query(type_query)
        for row in type_results:
            print(f"  {row['article_type'] or '(NULL)'}: {row['count']}")
        print()
        
        # Check for uploaded reports specifically
        uploaded_query = """
            SELECT COUNT(*) as count
            FROM research_articles
            WHERE article_type = 'uploaded_report'
        """
        uploaded_result = client.execute_query(uploaded_query)
        uploaded_count = uploaded_result[0]['count'] if uploaded_result else 0
        print(f"Uploaded reports (article_type='uploaded_report'): {uploaded_count}\n")
        
        # Show recent articles (last 10)
        print("Recent articles (last 10, all types):")
        print("=" * 100)
        recent_query = """
            SELECT 
                id,
                article_type,
                title,
                url,
                source,
                fund,
                fetched_at
            FROM research_articles
            ORDER BY fetched_at DESC
            LIMIT 10
        """
        recent_results = client.execute_query(recent_query)
        
        if not recent_results:
            print("No recent articles found.")
        else:
            for i, article in enumerate(recent_results, 1):
                print(f"\n{i}. {article['article_type'] or '(NULL)'}")
                print(f"   Title: {article['title'][:60] if article['title'] else 'N/A'}...")
                print(f"   URL: {article['url'][:60] if article['url'] else 'N/A'}...")
                print(f"   Source: {article['source'] or 'N/A'}")
                print(f"   Fund: {article['fund'] or 'None'}")
                print(f"   Fetched: {format_datetime(article['fetched_at'])}")
        
        print("\n" + "=" * 100)
        
        # Check for articles with "upload://" URL pattern
        print("\nChecking for articles with 'upload://' URL pattern...")
        upload_url_query = """
            SELECT COUNT(*) as count
            FROM research_articles
            WHERE url LIKE 'upload://%'
        """
        upload_url_result = client.execute_query(upload_url_query)
        upload_url_count = upload_url_result[0]['count'] if upload_url_result else 0
        print(f"Articles with 'upload://' URL: {upload_url_count}")
        
        if upload_url_count > 0:
            print("\nArticles with upload:// URLs:")
            upload_url_list_query = """
                SELECT 
                    id,
                    article_type,
                    title,
                    url,
                    source,
                    fund,
                    fetched_at
                FROM research_articles
                WHERE url LIKE 'upload://%'
                ORDER BY fetched_at DESC
            """
            upload_url_list = client.execute_query(upload_url_list_query)
            for article in upload_url_list:
                print(f"\n  - {article['title'] or 'N/A'}")
                print(f"    Type: {article['article_type'] or 'N/A'}")
                print(f"    URL: {article['url']}")
                print(f"    Fund: {article['fund'] or 'None'}")
                print(f"    Fetched: {format_datetime(article['fetched_at'])}")
        
        print("\n" + "=" * 100)
        print("\nDiagnosis complete!")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

