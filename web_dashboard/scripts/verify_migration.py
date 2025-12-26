#!/usr/bin/env python3
"""Verify that the Chain of Thought migration was applied successfully."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

client = PostgresClient()

# Check for new columns
result = client.execute_query("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'research_articles' 
      AND column_name IN ('claims', 'fact_check', 'conclusion', 'sentiment', 'sentiment_score')
    ORDER BY column_name
""")

print("=" * 60)
print("Chain of Thought Migration Verification")
print("=" * 60)

if result:
    print("\n[OK] New columns found:")
    for row in result:
        print(f"  - {row['column_name']}: {row['data_type']}")
else:
    print("\n[ERROR] No new columns found!")

# Check for indexes
index_result = client.execute_query("""
    SELECT indexname 
    FROM pg_indexes 
    WHERE tablename = 'research_articles' 
      AND indexname IN ('idx_research_sentiment', 'idx_research_sentiment_score', 'idx_research_claims')
    ORDER BY indexname
""")

if index_result:
    print("\n[OK] New indexes found:")
    for row in index_result:
        print(f"  - {row['indexname']}")
else:
    print("\n[WARN] No new indexes found (may already exist)")

print("\n" + "=" * 60)
print("Migration verification complete!")
print("=" * 60)

