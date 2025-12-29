import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*70)
print("REMOVING TRUE DUPLICATES FROM STAGING")
print("="*70)

# Get all staging records
result = client.supabase.table('congress_trades_staging')\
    .select('*')\
    .execute()

trades = result.data

# Group by business key
groups = defaultdict(list)
for trade in trades:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount'],
        trade.get('owner') or 'Not-Disclosed'
    )
    groups[key].append(trade)

# Find duplicates with SAME source TX ID
to_delete = []

for key, trade_list in groups.items():
    if len(trade_list) > 1:
        # Check source TX IDs
        by_source = defaultdict(list)
        for t in trade_list:
            raw = t.get('raw_data', {})
            tx_id = raw.get('_txId') if isinstance(raw, dict) else None
            by_source[tx_id].append(t)
        
        # For each source TX ID with multiple records, keep the lowest ID
        for source_id, dupes in by_source.items():
            if len(dupes) > 1:
                # Sort by ID, keep first, delete rest
                dupes_sorted = sorted(dupes, key=lambda x: x['id'])
                for dupe in dupes_sorted[1:]:
                    to_delete.append(dupe['id'])
                    print(f"Will delete ID {dupe['id']}: {dupe['politician']:25s} | {dupe['ticker']:6s} | {dupe['transaction_date']}")

print(f"\n📊 Found {len(to_delete)} duplicate records to delete")

if len(to_delete) == 0:
    print("✅ No duplicates found!")
    sys.exit(0)

response = input(f"\nDelete {len(to_delete)} duplicate records? (yes/no): ")

if response.lower() != 'yes':
    print("Aborted.")
    sys.exit(0)

# Delete in batches
deleted = 0
BATCH_SIZE = 50

for i in range(0, len(to_delete), BATCH_SIZE):
    batch = to_delete[i:i+BATCH_SIZE]
    try:
        client.supabase.table('congress_trades_staging')\
            .delete()\
            .in_('id', batch)\
            .execute()
        deleted += len(batch)
        print(f"   ✓ Deleted batch {i//BATCH_SIZE + 1}/{(len(to_delete) + BATCH_SIZE - 1)//BATCH_SIZE}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        break

print(f"\n✅ Deleted {deleted} duplicate records")

# Verify
final_result = client.supabase.table('congress_trades_staging')\
    .select('*', count='exact')\
    .execute()

print(f"📊 Staging records after cleanup: {final_result.count}")
