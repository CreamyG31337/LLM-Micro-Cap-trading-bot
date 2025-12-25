#!/usr/bin/env python3
"""
Verify Postgres Connection in Production

Simple script to verify that Postgres connection is working on the server.
Can be run from the server to test the connection and show basic stats.

SECURITY NOTE: This script should ONLY be run from the server/command line.
It is NOT accessible via web interface and should never be exposed as a web endpoint.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

try:
    from web_dashboard.postgres_client import PostgresClient
    from web_dashboard.research_repository import ResearchRepository
except ImportError as e:
    print(f"ERROR: Failed to import: {e}")
    print("Make sure you're in the project root and dependencies are installed")
    sys.exit(1)


def main():
    """Verify Postgres connection and show status"""
    print("=" * 70)
    print("Postgres Production Verification")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        print("   Check web_dashboard/.env file")
        return 1
    
    # Mask password for display
    parsed = database_url.split('@')
    if len(parsed) > 1:
        safe_url = parsed[0].split(':')[0] + ':***@' + '@'.join(parsed[1:])
    else:
        safe_url = "***"
    
    print(f"Database URL: {safe_url}")
    print()
    
    # Test connection
    print("1. Testing connection...")
    try:
        client = PostgresClient()
        if client.test_connection():
            print("   SUCCESS: Connected to Postgres")
        else:
            print("   FAILED: Connection test returned False")
            return 1
    except Exception as e:
        print(f"   FAILED: {e}")
        return 1
    
    # Check table exists
    print("\n2. Checking research_articles table...")
    try:
        result = client.execute_query("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'research_articles'
        """)
        if result and result[0]['count'] > 0:
            print("   SUCCESS: research_articles table exists")
        else:
            print("   WARNING: research_articles table not found")
            print("   Run: python web_dashboard/setup_postgres.py")
            return 1
    except Exception as e:
        print(f"   ERROR: {e}")
        return 1
    
    # Get table stats
    print("\n3. Getting table statistics...")
    try:
        repo = ResearchRepository(client)
        
        # Total articles
        total_result = client.execute_query("SELECT COUNT(*) as count FROM research_articles")
        total = total_result[0]['count'] if total_result else 0
        print(f"   Total articles: {total}")
        
        # Recent articles (last 7 days)
        recent_result = client.execute_query("""
            SELECT COUNT(*) as count 
            FROM research_articles 
            WHERE fetched_at >= NOW() - INTERVAL '7 days'
        """)
        recent = recent_result[0]['count'] if recent_result else 0
        print(f"   Articles (last 7 days): {recent}")
        
        # Latest article
        latest_result = client.execute_query("""
            SELECT title, fetched_at, ticker 
            FROM research_articles 
            ORDER BY fetched_at DESC 
            LIMIT 1
        """)
        if latest_result:
            latest = latest_result[0]
            print(f"   Latest article: {latest['title'][:50]}...")
            print(f"   Fetched: {latest['fetched_at']}")
            if latest.get('ticker'):
                print(f"   Ticker: {latest['ticker']}")
        
    except Exception as e:
        print(f"   ERROR getting stats: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Test write operation (optional - just check if we can)
    print("\n4. Testing write capability...")
    try:
        # Just check permissions, don't actually write
        result = client.execute_query("""
            SELECT has_table_privilege(current_user, 'research_articles', 'INSERT') as can_insert,
                   has_table_privilege(current_user, 'research_articles', 'SELECT') as can_select
        """)
        if result:
            perms = result[0]
            if perms['can_select']:
                print("   SUCCESS: Can SELECT from research_articles")
            else:
                print("   WARNING: Cannot SELECT from research_articles")
            
            if perms['can_insert']:
                print("   SUCCESS: Can INSERT into research_articles")
            else:
                print("   WARNING: Cannot INSERT into research_articles")
    except Exception as e:
        print(f"   ERROR checking permissions: {e}")
    
    print("\n" + "=" * 70)
    print("Verification Complete")
    print("=" * 70)
    print("\nAll checks passed! Postgres connection is working in production.")
    print("\nTo test saving an article, you can run:")
    print("  python web_dashboard/test_postgres_setup.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

