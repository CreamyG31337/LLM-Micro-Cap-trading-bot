#!/usr/bin/env python3
"""Check relationship statistics."""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient

client = PostgresClient()

# Count total relationships
count_result = client.execute_query("SELECT COUNT(*) as count FROM market_relationships")
total = count_result[0]['count'] if count_result else 0

print(f"Total relationships saved: {total}")

# Show sample relationships
if total > 0:
    sample = client.execute_query("""
        SELECT source_ticker, target_ticker, relationship_type, confidence_score 
        FROM market_relationships 
        ORDER BY detected_at DESC 
        LIMIT 10
    """)
    
    print("\nSample relationships:")
    for rel in sample:
        print(f"  {rel['source_ticker']} -> {rel['relationship_type']} -> {rel['target_ticker']} (confidence: {rel['confidence_score']})")

