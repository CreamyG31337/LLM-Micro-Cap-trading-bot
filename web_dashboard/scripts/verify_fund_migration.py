#!/usr/bin/env python3
"""Verify that the fund column migration was successful."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")

def verify_migration():
    """Verify the fund column exists."""
    try:
        client = PostgresClient()
        
        # Check if column exists
        result = client.execute_query("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'research_articles' AND column_name = 'fund'
        """)
        
        if result:
            col = result[0]
            print(f"[OK] Fund column exists!")
            print(f"   Type: {col['data_type']}")
            print(f"   Nullable: {col['is_nullable']}")
        else:
            print("[ERROR] Fund column not found!")
            return False
        
        # Check if index exists
        index_result = client.execute_query("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'research_articles' AND indexname = 'idx_research_fund'
        """)
        
        if index_result:
            print(f"[OK] Index 'idx_research_fund' exists!")
        else:
            print("[WARN] Index 'idx_research_fund' not found (may not be critical)")
        
        # Show current fund distribution
        stats = client.execute_query("""
            SELECT 
                COUNT(*) as total,
                COUNT(fund) as with_fund,
                COUNT(*) - COUNT(fund) as without_fund
            FROM research_articles
        """)
        
        if stats:
            s = stats[0]
            print(f"\n[INFO] Current Statistics:")
            print(f"   Total articles: {s['total']}")
            print(f"   Articles with fund: {s['with_fund']}")
            print(f"   Articles without fund (general): {s['without_fund']}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error verifying migration: {e}")
        return False

if __name__ == "__main__":
    print("Verifying Fund Column Migration")
    print("=" * 50)
    success = verify_migration()
    sys.exit(0 if success else 1)

