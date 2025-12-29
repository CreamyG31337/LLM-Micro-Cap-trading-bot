import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Get all unique batch IDs with counts
result = client.supabase.table('congress_trades_staging')\
    .select('import_batch_id,import_timestamp')\
    .execute()

from collections import Counter
batch_counts = Counter()
batch_timestamps = {}

for record in result.data:
    batch_id = record['import_batch_id']
    batch_counts[batch_id] += 1
    if batch_id not in batch_timestamps:
        batch_timestamps[batch_id] = record['import_timestamp']

print("All staging batches:")
print("="*70)
for batch_id, count in sorted(batch_counts.items(), key=lambda x: batch_timestamps[x[0]], reverse=True):
    timestamp = batch_timestamps[batch_id][:19]
    print(f"{count:6d} trades | {timestamp} | {batch_id}")
