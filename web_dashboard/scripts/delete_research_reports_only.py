#!/usr/bin/env python3
"""
Delete ONLY Research Reports from Database
==========================================

Deletes ONLY articles with article_type = 'Research Report'
Does NOT touch any other articles.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv(Path('web_dashboard/.env'))

from postgres_client import PostgresClient

def main():
    print("=" * 70)
    print("Delete Research Reports ONLY")
    print("=" * 70)
    print()
    print("WARNING: This will delete ONLY articles with article_type = 'Research Report'")
    print("         All other articles will remain untouched.")
    print()
    
    try:
        client = PostgresClient()
        print("[OK] Connected to database")
        print()
        
        # Count research reports
        count_result = client.execute_query("""
            SELECT COUNT(*) as count
            FROM research_articles
            WHERE article_type = 'Research Report'
        """)
        
        count = count_result[0]['count'] if count_result else 0
        
        if count == 0:
            print("[OK] No research reports found. Nothing to delete.")
            return
        
        print(f"Found {count} research report(s) to delete:")
        print()
        
        # Show what will be deleted
        articles = client.execute_query("""
            SELECT id, url, title
            FROM research_articles
            WHERE article_type = 'Research Report'
            ORDER BY url
        """)
        
        for article in articles:
            print(f"  - {article['url']}")
            print(f"    Title: {article['title']}")
            print()
        
        print(f"Total: {count} article(s)")
        print()
        response = input("Delete these research reports? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y']:
            print("Cancelled. No articles deleted.")
            return
        
        print()
        print("Deleting research reports...")
        
        # Delete ONLY research reports
        deleted = client.execute_update("""
            DELETE FROM research_articles
            WHERE article_type = 'Research Report'
        """)
        
        print(f"[OK] Deleted {deleted} research report(s)")
        print()
        print("All other articles remain untouched.")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

