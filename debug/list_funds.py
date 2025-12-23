import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Get all production funds
funds = client.supabase.table('funds').select('name').eq('is_production', True).execute()

print('Production funds:')
for f in funds.data:
    print(f'  - {f["name"]}')
