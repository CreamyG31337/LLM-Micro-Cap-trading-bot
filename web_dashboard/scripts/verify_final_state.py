#!/usr/bin/env python3
"""Verify final state after fix"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Get all committee assignments
all_ca = client.supabase.table('committee_assignments').select('politician_id').execute()
unique_pols_with_ca = {ca['politician_id'] for ca in all_ca.data}

# Get all politicians with proper bioguide IDs
proper_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

proper_pol_ids = {p['id'] for p in proper_pols.data}
without_ca = proper_pol_ids - unique_pols_with_ca

print("="*70)
print("FINAL STATE VERIFICATION")
print("="*70)
print(f"\nTotal politicians: {len(proper_pols.data)}")
print(f"Politicians with committee assignments: {len(unique_pols_with_ca)}")
print(f"Politicians WITHOUT committee assignments: {len(without_ca)}")

# Check a few that should have committees
test_names = ["Ro Khanna", "Katie Boyd Britt", "Tommy Tuberville", "John W. Hickenlooper"]
print(f"\n\nChecking specific politicians:")
print("-" * 70)

for name in test_names:
    r = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .eq('name', name)\
        .execute()
    
    if r.data:
        pol = r.data[0]
        ca = client.supabase.table('committee_assignments')\
            .select('id')\
            .eq('politician_id', pol['id'])\
            .execute()
        print(f"{name}: {len(ca.data)} committees")

print("\n" + "="*70)
print(f"✅ Final count: {len(without_ca)} politicians with proper bioguide IDs")
print(f"   but no committee assignments")
print("="*70)


