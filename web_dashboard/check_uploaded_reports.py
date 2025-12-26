#!/usr/bin/env python3
"""
Script to check for uploaded reports in the database
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.research_repository import ResearchRepository


def format_datetime(dt):
    """Format datetime for display (convert UTC to local if needed)"""
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        return dt
    # Convert UTC to local timezone for display
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # Convert to local time
    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    """Query and display all uploaded reports"""
    try:
        # Initialize repository
        repo = ResearchRepository()
        
        # Query for all uploaded reports
        print("Searching for uploaded reports in database...\n")
        
        query = """
            SELECT 
                id,
                title,
                url,
                source,
                fund,
                tickers,
                sector,
                published_at,
                fetched_at,
                relevance_score,
                CASE 
                    WHEN LENGTH(content) > 0 THEN LENGTH(content) 
                    ELSE 0 
                END as content_length,
                CASE 
                    WHEN summary IS NOT NULL AND LENGTH(summary) > 0 THEN LENGTH(summary) 
                    ELSE 0 
                END as summary_length,
                (embedding IS NOT NULL) as has_embedding
            FROM research_articles
            WHERE article_type = 'uploaded_report'
            ORDER BY fetched_at DESC
        """
        
        client = PostgresClient()
        results = client.execute_query(query)
        
        if not results:
            print("No uploaded reports found in the database.")
            print("\nTips:")
            print("   - Make sure you uploaded the report through the web dashboard")
            print("   - Check that the upload completed successfully")
            print("   - Verify the database connection is working")
            return
        
        print(f"Found {len(results)} uploaded report(s):\n")
        print("=" * 100)
        
        for i, report in enumerate(results, 1):
            print(f"\nReport #{i}")
            print("-" * 100)
            print(f"ID:           {report['id']}")
            print(f"Title:        {report['title'] or 'N/A'}")
            print(f"URL:          {report['url']}")
            print(f"Source:       {report['source'] or 'N/A'}")
            print(f"Fund:         {report['fund'] or 'None (general)'}")
            print(f"Tickers:      {report['tickers'] or 'None'}")
            print(f"Sector:       {report['sector'] or 'None'}")
            print(f"Published:    {format_datetime(report['published_at'])}")
            print(f"Uploaded:     {format_datetime(report['fetched_at'])}")
            print(f"Relevance:    {report['relevance_score'] or 'N/A'}")
            print(f"Content:      {report['content_length']:,} characters")
            print(f"Summary:      {report['summary_length']:,} characters")
            print(f"Embedding:    {'Yes' if report['has_embedding'] else 'No'}")
            
            # Show summary preview if available
            if report['summary_length'] > 0:
                summary_query = "SELECT summary FROM research_articles WHERE id = %s"
                summary_result = client.execute_query(summary_query, (report['id'],))
                if summary_result and summary_result[0].get('summary'):
                    summary = summary_result[0]['summary']
                    preview = summary[:200] + "..." if len(summary) > 200 else summary
                    print(f"\nSummary Preview:")
                    print(f"  {preview}")
        
        print("\n" + "=" * 100)
        print(f"\nTotal: {len(results)} uploaded report(s)")
        
    except Exception as e:
        print(f"Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

