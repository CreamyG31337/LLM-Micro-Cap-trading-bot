import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

result = client.supabase.table('congress_trades_staging')\
    .select('import_batch_id,import_timestamp', count='exact')\
    .order('import_timestamp', desc=True)\
    .limit(1)\
    .execute()

if result.data:
    batch_id = result.data[0]['import_batch_id']
    timestamp = result.data[0]['import_timestamp']
    print(f"Latest batch ID: {batch_id}")
    print(f"Imported at: {timestamp}")
    print(f"Total staging records: {result.count}")
else:
    print("No staging data found")
