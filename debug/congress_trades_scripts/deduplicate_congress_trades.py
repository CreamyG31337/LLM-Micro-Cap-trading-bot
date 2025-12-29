#!/usr/bin/env python3
"""
Deduplicate Congress Trades
============================
Removes duplicate trades where the only difference is missing metadata fields.
Keeps the record with the most complete data (non-NULL party, state, owner).
"""

import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*80)
print("CONGRESS TRADES DEDUPLICATION")
print("="*80)
print()

# Get all trades
result = client.supabase.table('congress_trades').select('*').execute()
print(f"Total trades: {len(result.data)}\n")

# Group by business key (ignoring owner and metadata fields that might be NULL)
groups = defaultdict(list)

for trade in result.data:
    # Business key: politician, ticker, date, amount, type
    # NOT including owner because it can be NULL and mess up the grouping
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['amount'],
        trade['type']
    )
    groups[key].append(trade)


# Find groups with duplicates
duplicates = {k: v for k, v in groups.items() if len(v) > 1}

print(f"Duplicate groups found: {len(duplicates)}")

if not duplicates:
    print("✅ No duplicates to clean up!")
    sys.exit(0)

print(f"Total duplicate records: {sum(len(v) for v in duplicates.values())}\n")

# Show examples
print("Examples of duplicates:")
print("-"*80)
for i, (key, trades) in enumerate(list(duplicates.items())[:5]):
    print(f"\n{i+1}. {key[0]} | {key[1]} | {key[2]} | {key[4]}")
    for t in sorted(trades, key=lambda x: x['id']):
        print(f"   ID {t['id']:6d}: Party={str(t.get('party') or 'NULL'):10s} "
              f"State={str(t.get('state') or 'NULL'):4s} "
              f"Owner={str(t.get('owner') or 'NULL'):15s}")

print("\n" + "="*80)
print("DEDUPLICATION PLAN")
print("="*80)

ids_to_delete = []

for key, trades in duplicates.items():
    # Sort by completeness: prioritize records with non-NULL fields
    def completeness_score(trade):
        score = 0
        if trade.get('party'): score += 10
        if trade.get('state'): score += 10
        if trade.get('owner'): score += 5
        # Use created_at as tiebreaker (newer is better)
        return (score, trade['created_at'])
    
    sorted_trades = sorted(trades, key=completeness_score, reverse=True)
    
    # Keep the first (most complete), delete the rest
    keeper = sorted_trades[0]
    to_delete = sorted_trades[1:]
    
    for trade in to_delete:
        ids_to_delete.append(trade['id'])

print(f"\nRecords to KEEP: {len(duplicates)} (most complete from each group)")
print(f"Records to DELETE: {len(ids_to_delete)}\n")

# Show what will be deleted
print("Sample of records that will be DELETED (incomplete duplicates):")
print("-"*80)
sample_to_delete = ids_to_delete[:10]
for trade_id in sample_to_delete:
    trade = next(t for trades in duplicates.values() for t in trades if t['id'] == trade_id)
    print(f"ID {trade_id:6d}: {trade['politician']:20s} | {trade['ticker']:6s} | "
          f"{trade['transaction_date']} | Party={str(trade.get('party') or 'NULL'):10s} "
          f"State={str(trade.get('state') or 'NULL'):4s}")

print("\n" + "="*80)
print("EXECUTION")
print("="*80)

# Ask for confirmation
response = input(f"\nDelete {len(ids_to_delete)} duplicate records? (yes/no): ")

if response.lower() != 'yes':
    print("Aborted. No changes made.")
    sys.exit(0)

# Delete in batches
BATCH_SIZE = 100
deleted_count = 0

for i in range(0, len(ids_to_delete), BATCH_SIZE):
    batch = ids_to_delete[i:i+BATCH_SIZE]
    try:
        result = client.supabase.table('congress_trades')\
            .delete()\
            .in_('id', batch)\
            .execute()
        deleted_count += len(batch)
        print(f"Deleted batch {i//BATCH_SIZE + 1}/{(len(ids_to_delete) + BATCH_SIZE - 1)//BATCH_SIZE}")
    except Exception as e:
        print(f"Error deleting batch: {e}")
        break

print(f"\n✅ Deleted {deleted_count} duplicate records!")

# Verify
result = client.supabase.table('congress_trades').select('id', count='exact').execute()
print(f"Remaining trades: {result.count}")
