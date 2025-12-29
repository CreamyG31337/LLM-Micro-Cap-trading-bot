import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Get Rohit Khanna duplicates
result = client.supabase.table('congress_trades_staging')\
    .select('id,politician,ticker,transaction_date,type,amount,owner,import_timestamp,raw_data')\
    .eq('politician', 'Rohit Khanna')\
    .order('ticker')\
    .execute()

print(f"Total Rohit Khanna trades: {len(result.data)}\n")

# Group by business key
from collections import defaultdict
groups = defaultdict(list)

for trade in result.data:
    key = (trade['ticker'], str(trade['transaction_date']), trade['type'], trade['amount'], trade.get('owner'))
    groups[key].append(trade)

# Find duplicates
dupes = {k: v for k, v in groups.items() if len(v) > 1}

print(f"Duplicate groups: {len(dupes)}\n")

# Show first few
for i, (key, trades) in enumerate(list(dupes.items())[:5]):
    print(f"{i+1}. {key[0]:6s} | {key[1]} | {key[2]:8s} | {key[3]}")
    for t in sorted(trades, key=lambda x: x['id']):
        # Check if raw_data has _txId
        raw = t.get('raw_data', {})
        tx_id = raw.get('_txId') if isinstance(raw, dict) else 'N/A'
        timestamp = t['import_timestamp'][:19] if t.get('import_timestamp') else 'N/A'
        print(f"   ID: {t['id']:6d} | Source TX: {str(tx_id):10s} | Imported: {timestamp}")
    print()
