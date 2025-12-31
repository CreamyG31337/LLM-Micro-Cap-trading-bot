#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Check Katie Boyd Britt
r = client.supabase.table('politicians').select('id, name, bioguide_id').eq('bioguide_id', 'B001319').execute()
print('Katie Boyd Britt:', len(r.data))
for p in r.data:
    print(f"  ID {p['id']}: {p['name']}")
    pid = p['id']
    ca = client.supabase.table('committee_assignments').select('id').eq('politician_id', pid).execute()
    print(f"    Committee assignments: {len(ca.data)}")

# Check total assignments now
all_ca = client.supabase.table('committee_assignments').select('politician_id').execute()
unique_pols = {ca['politician_id'] for ca in all_ca.data}
print(f"\nTotal unique politicians with committees: {len(unique_pols)}")

# Check politicians with proper bioguide
proper_pols = client.supabase.table('politicians')\
    .select('id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

proper_pol_ids = {p['id'] for p in proper_pols.data}
without_ca = proper_pol_ids - unique_pols
print(f"Politicians with proper bioguide but no committees: {len(without_ca)}")


