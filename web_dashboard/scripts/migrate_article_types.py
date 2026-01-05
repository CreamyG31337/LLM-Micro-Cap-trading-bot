#!/usr/bin/env python3
"""
Migrate Article Types from Underscore to Space Format
======================================================

Updates all article_type values in research_articles table from underscore format
(e.g., 'market_news') to space format (e.g., 'Market News').

Run this script to migrate existing database records.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

try:
    from postgres_client import PostgresClient
except ImportError:
    print("ERROR: postgres_client not available")
    print("Make sure you're running from the project root with web_dashboard in the path")
    sys.exit(1)

# Migration mappings: old_format -> new_format
MIGRATIONS = [
    ('market_news', 'Market News'),
    ('ticker_news', 'Ticker News'),
    ('opportunity_discovery', 'Opportunity Discovery'),
    ('research_report', 'Research Report'),
    ('uploaded_report', 'Research Report'),  # Also migrate old uploaded_report
    ('reddit_discovery', 'Reddit Discovery'),
    ('alpha_research', 'Alpha Research'),
    ('etf_change', 'ETF Change'),
    ('seeking_alpha_symbol', 'Seeking Alpha Symbol'),
]


def main():
    """Run the migration"""
    print("=" * 70)
    print("Article Type Migration: Underscore -> Space Format")
    print("=" * 70)
    print()
    
    try:
        client = PostgresClient()
        print("[OK] Connected to database")
        print()
        
        # Check current counts
        print("Checking current article type distribution...")
        check_query = """
            SELECT article_type, COUNT(*) as count
            FROM research_articles
            WHERE article_type IN %s
            GROUP BY article_type
            ORDER BY article_type
        """
        old_types = tuple([old for old, _ in MIGRATIONS])
        current_counts = client.execute_query(check_query, (old_types,))
        
        if current_counts:
            print("\nCurrent article types (underscore format):")
            total_old = 0
            for row in current_counts:
                count = row['count']
                total_old += count
                print(f"  {row['article_type']}: {count:,} articles")
            print(f"\nTotal articles to migrate: {total_old:,}")
        else:
            print("  No articles found with underscore format types")
            print("  Migration not needed!")
            return
        
        print()
        # Auto-proceed if running non-interactively
        import sys
        if not sys.stdin.isatty():
            print("Non-interactive mode: proceeding automatically...")
        else:
            response = input("Proceed with migration? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("Migration cancelled.")
                return
        
        print()
        print("Running migrations...")
        print("-" * 70)
        
        total_updated = 0
        for old_type, new_type in MIGRATIONS:
            # Check if any records exist with old type
            check_count_query = "SELECT COUNT(*) as count FROM research_articles WHERE article_type = %s"
            count_result = client.execute_query(check_count_query, (old_type,))
            count = count_result[0]['count'] if count_result else 0
            
            if count > 0:
                # Run migration
                update_query = """
                    UPDATE research_articles 
                    SET article_type = %s 
                    WHERE article_type = %s
                """
                rows_updated = client.execute_update(update_query, (new_type, old_type))
                total_updated += rows_updated
                print(f"  [OK] {old_type:30} -> {new_type:30} ({rows_updated:,} articles)")
            else:
                print(f"  [SKIP] {old_type:30} -> {new_type:30} (0 articles, skipped)")
        
        print("-" * 70)
        print(f"\n[OK] Migration complete! Updated {total_updated:,} articles")
        
        # Verify migration
        print("\nVerifying migration...")
        verify_query = """
            SELECT article_type, COUNT(*) as count
            FROM research_articles
            WHERE article_type IN %s
            GROUP BY article_type
            ORDER BY article_type
        """
        new_types = tuple([new for _, new in MIGRATIONS])
        verify_counts = client.execute_query(verify_query, (new_types,))
        
        if verify_counts:
            print("\nNew article types (space format):")
            for row in verify_counts:
                print(f"  {row['article_type']}: {row['count']:,} articles")
        
        # Check for any remaining underscore types
        remaining_query = """
            SELECT article_type, COUNT(*) as count
            FROM research_articles
            WHERE article_type LIKE '%_%'
            GROUP BY article_type
            ORDER BY article_type
        """
        remaining = client.execute_query(remaining_query)
        if remaining:
            print("\n[WARNING] Found remaining underscore types:")
            for row in remaining:
                print(f"  {row['article_type']}: {row['count']:,} articles")
        else:
            print("\n[OK] No remaining underscore types found")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

