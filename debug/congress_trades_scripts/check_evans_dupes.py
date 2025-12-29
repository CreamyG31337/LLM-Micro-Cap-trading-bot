import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("Dwight Evans Duplicate Analysis")
print("="*80)

result = client.supabase.table('congress_trades')\
    .select('*')\
    .eq('politician', 'Dwight Evans')\
    .order('transaction_date', desc=True)\
    .execute()

print(f"\nTotal Dwight Evans trades: {len(result.data)}\n")

from collections import defaultdict
groups = defaultdict(list)

for trade in result.data:
    key = (trade['ticker'], str(trade['transaction_date']), trade['type'], trade['amount'])
    groups[key].append(trade)

dupes = {k: v for k, v in groups.items() if len(v) > 1}

print(f"Duplicate groups (ignoring owner): {len(dupes)}\n")

if dupes:
    for k, trades in dupes.items():
        print(f"\n{k[0]} {k[2]} on {k[1]} - {k[3]}")
        print("-"*80)
        for t in sorted(trades, key=lambda x: x['id']):
            print(f"  ID {t['id']:6d}: Party={str(t.get('party') or 'NULL'):10s} "
                  f"State={str(t.get('state') or 'NULL'):4s} "
                  f"Owner={str(t.get('owner') or 'NULL'):15s}")
    
    print("\n" + "="*80)
    print("IDS TO DELETE (keeping most complete record):")
    print("="*80)
    
    to_delete = []
    for k, trades in dupes.items():
        # Sort by completeness
        sorted_trades = sorted(trades, key=lambda x: (
            1 if x.get('party') else 0,
            1 if x.get('state') else 0,
            1 if x.get('owner') else 0,
            x['created_at']
        ), reverse=True)
        
        # Delete all but the first
        for t in sorted_trades[1:]:
            to_delete.append(t['id'])
            print(f"  DELETE ID {t['id']}: {k[0]} {k[2]} on {k[1]} "
                  f"(Party={str(t.get('party') or 'NULL')}, State={str(t.get('state') or 'NULL')})")
    
    print(f"\nTotal to delete: {len(to_delete)}")
    print(f"\n{to_delete}")
else:
    print("✅ No duplicates found!")
