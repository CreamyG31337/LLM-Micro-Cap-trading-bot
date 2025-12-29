import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient
from collections import defaultdict

client = SupabaseClient(use_service_role=True)

print("="*80)
print("COMPREHENSIVE DUPLICATE CHECK - ALL POLITICIANS")
print("="*80)
print()

# Get all trades
result = client.supabase.table('congress_trades').select('*').execute()
print(f"Total trades: {len(result.data)}\n")

# Strategy: Check for duplicates where SAME owner (including NULL)
# Group by: politician, ticker, date, type, amount, owner
groups_with_owner = defaultdict(list)

for trade in result.data:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount'],
        str(trade.get('owner'))  # Include owner as string (None becomes 'None')
    )
    groups_with_owner[key].append(trade)

# Find duplicates with same owner
exact_duplicates = {k: v for k, v in groups_with_owner.items() if len(v) > 1}

print(f"EXACT DUPLICATES (same owner): {len(exact_duplicates)}")
if exact_duplicates:
    print("\nThese are TRUE duplicates that should be removed:")
    print("-"*80)
    
    for k, trades in list(exact_duplicates.items())[:20]:
        print(f"\n{k[0]:25s} | {k[1]:6s} | {k[2]} | {k[3]:8s} | Owner: {k[5]}")
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"  ID {t['id']:6d}: Party={str(t.get('party') or 'NULL'):10s} "
                  f"State={str(t.get('state') or 'NULL'):4s} Created={t['created_at'][:19]}")

print(f"\n{'='*80}")
print("METADATA-ONLY DUPLICATES (same trade, different metadata)")
print("="*80)

# Group WITHOUT owner to find metadata duplicates
groups_no_owner = defaultdict(list)

for trade in result.data:
    key = (
        trade['politician'],
        trade['ticker'],
        str(trade['transaction_date']),
        trade['type'],
        trade['amount']
    )
    groups_no_owner[key].append(trade)

metadata_duplicates = {k: v for k, v in groups_no_owner.items() if len(v) > 1}

print(f"\nTrades appearing multiple times (ignoring owner): {len(metadata_duplicates)}")

# Filter to find ACTUAL duplicates (not just different owners)
actual_metadata_dupes = []
for k, trades in metadata_duplicates.items():
    # Group by owner
    by_owner = defaultdict(list)
    for t in trades:
        by_owner[str(t.get('owner'))].append(t)
    
    # Check each owner group for duplicates within it
    for owner, owner_trades in by_owner.items():
        if len(owner_trades) > 1:
            actual_metadata_dupes.append((k, owner, owner_trades))

if actual_metadata_dupes:
    print(f"\nFOUND {len(actual_metadata_dupes)} GROUPS with duplicate records:")
    print("-"*80)
    for k, owner, trades in actual_metadata_dupes[:20]:
        print(f"\n{k[0]:25s} | {k[1]:6s} | {k[2]} | {k[3]:8s} | Owner: {owner}")
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"  ID {t['id']:6d}: Party={str(t.get('party') or 'NULL'):10s} "
                  f"State={str(t.get('state') or 'NULL'):4s}")
else:
    print("\n✅ No metadata duplicates found!")
