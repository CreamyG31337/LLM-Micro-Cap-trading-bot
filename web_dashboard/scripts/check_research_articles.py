#!/usr/bin/env python3
"""
Check Research Articles in Database
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from postgres_client import PostgresClient

client = PostgresClient()

# Check all article types
print("Article types in database:")
result = client.execute_query("""
    SELECT article_type, COUNT(*) as count
    FROM research_articles
    GROUP BY article_type
    ORDER BY article_type
""")

for row in result:
    print(f"  {row['article_type']}: {row['count']} articles")

# Check research reports specifically
print("\nResearch Reports:")
result = client.execute_query("""
    SELECT article_type, title, url, published_at
    FROM research_articles
    WHERE article_type LIKE '%Research%' OR article_type LIKE '%research%'
    ORDER BY published_at DESC
    LIMIT 10
""")

if result:
    for row in result:
        print(f"  Type: {row['article_type']}")
        print(f"  Title: {row['title']}")
        print(f"  URL: {row['url']}")
        print(f"  Published: {row['published_at']}")
        print()
else:
    print("  No research reports found")

