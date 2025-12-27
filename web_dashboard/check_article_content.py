#!/usr/bin/env python3
"""Check article content to see if logic_check classification is accurate."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

client = PostgresClient()

# Get a few articles with their logic_check
result = client.execute_query("""
    SELECT title, logic_check, 
           SUBSTRING(content, 1, 800) as content_preview
    FROM research_articles 
    WHERE logic_check IS NOT NULL 
    ORDER BY fetched_at DESC 
    LIMIT 5
""")

print("=" * 80)
print("Sample Articles - Logic Check Classification")
print("=" * 80)

for i, article in enumerate(result, 1):
    print(f"\n[{i}] Title: {article['title'][:60]}...")
    print(f"    Logic Check: {article['logic_check']}")
    print(f"    Content Preview (first 300 chars):")
    content = article['content_preview'] or ""
    print(f"    {content[:300]}...")
    print("-" * 80)

