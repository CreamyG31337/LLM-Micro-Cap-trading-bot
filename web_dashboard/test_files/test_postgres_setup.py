#!/usr/bin/env python3
"""
Test script for Postgres setup and research repository

Run this after setting up Postgres to verify everything works.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.research_repository import ResearchRepository
from datetime import datetime, timezone


def test_connection():
    """Test basic database connection"""
    print("=" * 50)
    print("Test 1: Database Connection")
    print("=" * 50)
    
    try:
        client = PostgresClient()
        if client.test_connection():
            print("✅ Connection successful!")
            return True
        else:
            print("❌ Connection failed")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_table_exists():
    """Test that research_articles table exists"""
    print("\n" + "=" * 50)
    print("Test 2: Table Exists")
    print("=" * 50)
    
    try:
        client = PostgresClient()
        result = client.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = 'research_articles'"
        )
        if result and result[0]['count'] > 0:
            print("✅ research_articles table exists")
            return True
        else:
            print("❌ research_articles table not found")
            print("   Run: python web_dashboard/scripts/setup_postgres.py")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_save_article():
    """Test saving an article"""
    print("\n" + "=" * 50)
    print("Test 3: Save Article")
    print("=" * 50)
    
    try:
        repo = ResearchRepository()
        
        # Save a test article
        article_id = repo.save_article(
            ticker="TEST",
            sector="Technology",
            article_type="ticker_news",
            title="Test Article - Postgres Setup Verification",
            url="https://example.com/test-postgres-setup",
            summary="This is a test article to verify Postgres setup is working correctly.",
            content="Full test article content. This verifies that the research repository can save articles to the database.",
            source="Test Source",
            published_at=datetime.now(timezone.utc),
            relevance_score=0.95
        )
        
        if article_id:
            print(f"✅ Article saved successfully! ID: {article_id}")
            return True, article_id
        else:
            print("❌ Failed to save article")
            return False, None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_get_articles():
    """Test retrieving articles"""
    print("\n" + "=" * 50)
    print("Test 4: Get Articles")
    print("=" * 50)
    
    try:
        repo = ResearchRepository()
        
        # Get articles by ticker
        articles = repo.get_articles_by_ticker("TEST", limit=5)
        print(f"✅ Retrieved {len(articles)} articles for ticker TEST")
        
        if articles:
            print(f"   First article: {articles[0]['title'][:50]}...")
        
        # Get recent articles
        recent = repo.get_recent_articles(limit=5, days=7)
        print(f"✅ Retrieved {len(recent)} recent articles")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_search_articles():
    """Test searching articles"""
    print("\n" + "=" * 50)
    print("Test 5: Search Articles")
    print("=" * 50)
    
    try:
        repo = ResearchRepository()
        
        results = repo.search_articles("test", limit=5)
        print(f"✅ Found {len(results)} articles matching 'test'")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "=" * 50)
    print("Cleanup: Remove Test Data")
    print("=" * 50)
    
    try:
        client = PostgresClient()
        result = client.execute_update(
            "DELETE FROM research_articles WHERE url = %s",
            ("https://example.com/test-postgres-setup",)
        )
        print(f"✅ Deleted {result} test article(s)")
        return True
    except Exception as e:
        print(f"⚠️  Error cleaning up: {e}")
        return False


def main():
    """Run all tests"""
    print("\n🧪 Postgres Setup Test Suite")
    print("=" * 50)
    
    results = []
    
    # Run tests
    results.append(("Connection", test_connection()))
    results.append(("Table Exists", test_table_exists()))
    
    save_result, article_id = test_save_article()
    results.append(("Save Article", save_result))
    
    if save_result:
        results.append(("Get Articles", test_get_articles()))
        results.append(("Search Articles", test_search_articles()))
        
        # Ask if user wants to clean up
        response = input("\n🧹 Delete test article? (y/n): ")
        if response.lower() == 'y':
            cleanup_test_data()
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Postgres setup is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

