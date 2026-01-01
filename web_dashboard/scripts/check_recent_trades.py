#!/usr/bin/env python3
"""Check recent trade IDs to verify pagination"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postgres_client import PostgresClient
from datetime import datetime, timedelta

pg = PostgresClient()

result = pg.execute_query(
    'SELECT trade_id, analyzed_at FROM congress_trades_analysis '
    'WHERE analyzed_at > %s ORDER BY analyzed_at DESC LIMIT 30',
    (datetime.now() - timedelta(minutes=30),)
)

print("Recent trade IDs analyzed (last 30 minutes):")
trade_ids = []
for r in result:
    trade_id = r['trade_id']
    trade_ids.append(trade_id)
    print(f"  {trade_id} at {r['analyzed_at']}")

print(f"\nTotal: {len(trade_ids)}")
print(f"Unique: {len(set(trade_ids))}")
if len(trade_ids) > 0:
    print(f"First: {trade_ids[0]}, Last: {trade_ids[-1]}")

