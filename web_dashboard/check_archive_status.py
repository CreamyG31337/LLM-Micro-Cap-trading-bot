#!/usr/bin/env python3
"""Check archive status of articles"""

import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from research_repository import ResearchRepository

repo = ResearchRepository()

# Get articles with archive submissions
result = repo.client.execute_query("""
    SELECT id, title, url, archive_submitted_at, archive_checked_at, archive_url 
    FROM research_articles 
    WHERE archive_submitted_at IS NOT NULL
    ORDER BY archive_submitted_at DESC
    LIMIT 10
""")

print(f"\nFound {len(result)} articles with archive submissions:\n")
for r in result:
    print(f"ID: {r['id']}")
    print(f"Title: {r['title'][:60]}...")
    print(f"URL: {r['url'][:80]}...")
    print(f"Submitted: {r['archive_submitted_at']}")
    print(f"Checked: {r['archive_checked_at']}")
    print(f"Archive URL: {r['archive_url']}")
    print("-" * 80)

