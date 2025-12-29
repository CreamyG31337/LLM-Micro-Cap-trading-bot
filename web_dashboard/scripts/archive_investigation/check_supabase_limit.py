import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Fetch with explicit count
result = client.supabase.table('congress_trades_staging')\
    .select('id', count='exact')\
    .execute()

print(f"Total staging records: {result.count}")
print(f"Records fetched: {len(result.data)}")

# The default limit is 1000, need to paginate
print("\nSupabase has a default 1000 row limit per query!")
