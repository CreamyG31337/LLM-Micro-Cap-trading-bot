#!/usr/bin/env python3
"""Check if trades are being analyzed repeatedly"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postgres_client import PostgresClient
from datetime import datetime, timedelta

pg = PostgresClient()

print("=" * 70)
print("ANALYSIS PROGRESS CHECK")
print("=" * 70)

# Check recent analyses
print("\n1. Recent analyses (last 10):")
result = pg.execute_query(
    "SELECT trade_id, conflict_score, analyzed_at, model_used "
    "FROM congress_trades_analysis "
    "ORDER BY analyzed_at DESC LIMIT 10"
)

for r in result:
    print(f"  Trade ID: {r['trade_id']}, Score: {r['conflict_score']}, "
          f"Analyzed: {r['analyzed_at']}")

# Check for duplicates
print("\n2. Trades analyzed multiple times:")
result = pg.execute_query(
    "SELECT trade_id, COUNT(*) as count, MAX(analyzed_at) as last_analyzed "
    "FROM congress_trades_analysis "
    "GROUP BY trade_id "
    "HAVING COUNT(*) > 1 "
    "ORDER BY count DESC LIMIT 10"
)

if result:
    for r in result:
        print(f"  Trade ID: {r['trade_id']}, Count: {r['count']}, "
              f"Last: {r['last_analyzed']}")
else:
    print("  None found")

# Check analyses in last hour
print("\n3. Analyses in last hour:")
result = pg.execute_query(
    "SELECT COUNT(*) as count FROM congress_trades_analysis "
    "WHERE analyzed_at > %s",
    (datetime.now() - timedelta(hours=1),)
)
print(f"  Count: {result[0]['count'] if result else 0}")

# Check if same trade_id appears multiple times recently
print("\n4. Same trade analyzed multiple times in last hour:")
result = pg.execute_query(
    "SELECT trade_id, COUNT(*) as count, MAX(analyzed_at) as last_analyzed "
    "FROM congress_trades_analysis "
    "WHERE analyzed_at > %s "
    "GROUP BY trade_id "
    "HAVING COUNT(*) > 1 "
    "ORDER BY count DESC",
    (datetime.now() - timedelta(hours=1),)
)

if result:
    print("  WARNING: Found trades analyzed multiple times!")
    for r in result:
        print(f"  Trade ID: {r['trade_id']}, Count: {r['count']}, "
              f"Last: {r['last_analyzed']}")
else:
    print("  None found - looks good!")

print("\n" + "=" * 70)

