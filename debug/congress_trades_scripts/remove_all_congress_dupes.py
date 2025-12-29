#!/usr/bin/env python3
"""Find and remove ALL duplicate congress trades with NULL metadata"""

import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*80)
print("FINDING ALL DUPLICATE CONGRESS TRADES")
print("="*80)
print()

# Get all trades
result = client.supabase.table('congress_trades').select('*').execute()
print(f"Total trades: {len(result.data)}\n")

# Group by business key (politician, ticker, date, type, amount)
# Ignoring owner because NULL owner != NULL owner in unique constraints
groups = defaultdict(list)

for trade in result.data:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount']
    )
    groups[key].append(trade)

# Find duplicates
duplicates = {k: v for k, v in groups.items() if len(v) > 1}

print(f"Duplicate groups found: {len(duplicates)}\n")

if not duplicates:
    print("✅ No duplicates to clean up!")
    sys.exit(0)

# Analyze duplicates
ids_to_delete = []
details = []

for key, trades in duplicates.items():
    # Check if this is a REAL duplicate (same owner) or different owners (legitimate)
    owners = [t.get('owner') for t in trades]
    unique_owners = set(owners)
    
    #  If all owners are the same (or all NULL), these are duplicates
    if len(unique_owners) == 1:
        # Sort by completeness
        sorted_trades = sorted(trades, key=lambda x: (
            1 if x.get('party') else 0,
            1 if x.get('state') else 0,
            1 if x.get('owner') else 0,
            x['created_at']
        ), reverse=True)
        
        keeper = sorted_trades[0]
        to_delete = sorted_trades[1:]
        
        for t in to_delete:
            ids_to_delete.append(t['id'])
            details.append(f"  ID {t['id']:6d}: {key[0]:25s} | {key[1]:6s} | {key[2]} | {key[3]:8s} | "
                         f"Party={str(t.get('party') or 'NULL'):10s} State={str(t.get('state') or 'NULL'):4s}")

print("Duplicates to DELETE (incomplete records):")
print("-"*80)
for d in details[:20]:
    print(d)
if len(details) > 20:
    print(f"... and {len(details)-20} more")

print(f"\nTotal duplicate records to delete: {len(ids_to_delete)}")

if len(ids_to_delete) == 0:
    print("✅ No true duplicates found (different owners are legitimate separate trades)")
    sys.exit(0)

# Delete
response = input(f"\nDelete {len(ids_to_delete)} duplicate records? (yes/no): ")

if response.lower() != 'yes':
    print("Aborted.")
    sys.exit(0)

try:
    # Delete in batches
    BATCH_SIZE = 100
    for i in range(0, len(ids_to_delete), BATCH_SIZE):
        batch = ids_to_delete[i:i+BATCH_SIZE]
        client.supabase.table('congress_trades').delete().in_('id', batch).execute()
        print(f"Deleted batch {i//BATCH_SIZE + 1}/{(len(ids_to_delete) + BATCH_SIZE - 1)//BATCH_SIZE}")
    
    print(f"\n✅ Deleted {len(ids_to_delete)} duplicate records!")
    
    # Verify
    result = client.supabase.table('congress_trades').select('id', count='exact').execute()
    print(f"Remaining trades: {result.count}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
