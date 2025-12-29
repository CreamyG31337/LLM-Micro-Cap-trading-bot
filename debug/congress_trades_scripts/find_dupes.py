import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Get Dwight Evans trades
result = client.supabase.table('congress_trades')\
    .select('*')\
    .ilike('politician', '%dwight%evans%')\
    .execute()

print(f"Total trades: {len(result.data)}\n")

# Simple duplicate check
from collections import defaultdict
seen = defaultdict(list)

for trade in result.data:
    key = (
        trade['politician'], 
        trade['ticker'], 
        str(trade['transaction_date']), 
        trade['amount'],
        trade['type'],
        trade.get('owner')  # This can be None!
    )
    seen[key].append(trade)

# Find duplicates
duplicates = {k: v for k, v in seen.items() if len(v) > 1}

print(f"Duplicate groups: {len(duplicates)}\n")

for key, trades in duplicates.items():
    print(f"\n{'='*80}")
    print(f"Duplicate: {key[1]} on {key[2]} - {key[4]} - {key[3]}")
    print(f"{'='*80}")
    for t in sorted(trades, key=lambda x: x['id']):
        print(f"  ID: {t['id']:6d} | State: {str(t.get('state', 'NULL')):4s} | Party: {str(t.get('party', 'NULL')):10s} | Owner: {str(t.get('owner', 'NULL')):15s} | Created: {t['created_at']}")
    print()
