import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("="*80)
print("CHECKING FOR DUPLICATES (treating NULL as empty string)")
print("="*80)
print()

# Get ALL trades for Dwight Evans first
result = client.supabase.table('congress_trades')\
    .select('*')\
    .ilike('politician', '%dwight%evans%')\
    .execute()

print(f"Dwight Evans trades: {len(result.data)}\n")

from collections import defaultdict
seen = defaultdict(list)

for trade in result.data:
    # Treat None/NULL as empty string for comparison
    key = (
        trade['politician'], 
        trade['ticker'], 
        str(trade['transaction_date']), 
        trade['amount'],
        trade['type'],
        trade.get('owner') or ''  # Treat NULL as empty
    )
    seen[key].append(trade)

# Find duplicates
duplicates = {k: v for k, v in seen.items() if len(v) > 1}

if duplicates:
    print(f"⚠️ FOUND {len(duplicates)} DUPLICATE GROUPS\n")
    for key, trades in duplicates.items():
        print(f"\nDuplicate: {key[1]} on {key[2]} - {key[4]}")
        print("-"*80)
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"  ID: {t['id']:6d} | State: {str(t.get('state') or 'NULL'):4s} | "
                  f"Party: {str(t.get('party') or 'NULL'):12s} | "
                  f"Owner: {str(t.get('owner') or 'NULL'):15s} | "
                  f"Created: {t['created_at'][:19]}")
else:
    print("No duplicates found")

# Now check ALL politicians
print("\n" + "="*80)
print("CHECKING ALL POLITICIANS FOR DUPLICATES")
print("="*80)

result = client.supabase.table('congress_trades')\
    .select('*')\
    .execute()

print(f"\nTotal trades: {len(result.data)}")

seen_all = defaultdict(list)

for trade in result.data:
    key = (
        trade['politician'], 
        trade['ticker'], 
        str(trade['transaction_date']), 
        trade['amount'],
        trade['type'],
        trade.get('owner') or ''  # Treat NULL as empty
    )
    seen_all[key].append(trade)

# Find ALL duplicates
all_duplicates = {k: v for k, v in seen_all.items() if len(v) > 1}

if all_duplicates:
    print(f"\n⚠️ FOUND {len(all_duplicates)} DUPLICATE GROUPS ACROSS ALL POLITICIANS\n")
    
    # Show first 10
    for i, (key, trades) in enumerate(list(all_duplicates.items())[:10]):
        print(f"\n{i+1}. {key[0]} | {key[1]} | {key[2]}")
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"   ID:{t['id']:6d} State:{str(t.get('state') or 'NULL'):4s} "
                  f"Party:{str(t.get('party') or 'NULL'):12s} Owner:{str(t.get('owner') or 'NULL'):15s}")
    
    total_dupe_records = sum(len(v) for v in all_duplicates.values())
    print(f"\nTotal duplicate records: {total_dupe_records}")
else:
    print("\n✅ No duplicates found")
