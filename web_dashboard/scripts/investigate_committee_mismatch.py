#!/usr/bin/env python3
"""Investigate why so many politicians don't have committee assignments"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

print("="*70)
print("INVESTIGATING COMMITTEE ASSIGNMENT MISMATCH")
print("="*70)

# 1. Check total committee assignments
print("\n1. Total committee assignments in database:")
print("-" * 70)
all_ca = client.supabase.table('committee_assignments')\
    .select('id, politician_id')\
    .execute()

print(f"   Total committee assignments: {len(all_ca.data)}")
unique_pols_with_ca = {ca['politician_id'] for ca in all_ca.data}
print(f"   Unique politicians with committee assignments: {len(unique_pols_with_ca)}")

# 2. Check if these politician IDs actually exist
print("\n2. Verifying politician IDs in committee assignments:")
print("-" * 70)
sample_pol_ids = list(unique_pols_with_ca)[:10]
pol_check = client.supabase.table('politicians')\
    .select('id, name')\
    .in_('id', sample_pol_ids)\
    .execute()

print(f"   Sample of {len(sample_pol_ids)} politician IDs from committee_assignments:")
print(f"   Found {len(pol_check.data)} in politicians table")
for pol in pol_check.data[:5]:
    print(f"     - ID {pol['id']}: {pol['name']}")

# 3. Check politicians that SHOULD have committees (proper bioguide IDs)
print("\n3. Politicians with proper bioguide IDs:")
print("-" * 70)
proper_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

print(f"   Total with proper bioguide IDs: {len(proper_pols.data)}")
proper_pol_ids = {p['id'] for p in proper_pols.data}

# 4. Check overlap
print("\n4. Overlap analysis:")
print("-" * 70)
pols_with_ca_and_proper_bioguide = proper_pol_ids & unique_pols_with_ca
pols_with_proper_bioguide_but_no_ca = proper_pol_ids - unique_pols_with_ca

print(f"   Politicians with proper bioguide IDs AND committee assignments: {len(pols_with_ca_and_proper_bioguide)}")
print(f"   Politicians with proper bioguide IDs BUT NO committee assignments: {len(pols_with_proper_bioguide_but_no_ca)}")

if pols_with_proper_bioguide_but_no_ca:
    print(f"\n   Sample of politicians with proper bioguide but no committees:")
    sample_ids = list(pols_with_proper_bioguide_but_no_ca)[:10]
    sample_pols = [p for p in proper_pols.data if p['id'] in sample_ids]
    for pol in sample_pols[:10]:
        print(f"     - {pol['name']} (ID {pol['id']}, bioguide={pol['bioguide_id']})")

# 5. Check if committee assignments are linked to wrong politician IDs
print("\n5. Checking for orphaned committee assignments:")
print("-" * 70)
all_ca_pol_ids = {ca['politician_id'] for ca in all_ca.data}
all_pol_ids = {p['id'] for p in client.supabase.table('politicians').select('id').execute().data}
orphaned_ca = all_ca_pol_ids - all_pol_ids

if orphaned_ca:
    print(f"   [WARNING] Found {len(orphaned_ca)} committee assignments linked to non-existent politician IDs!")
    print(f"   Sample orphaned IDs: {list(orphaned_ca)[:10]}")
else:
    print(f"   [OK] All committee assignments linked to existing politicians")

# 6. Check a specific politician that should have committees
print("\n6. Checking specific politician (Ro Khanna - has 11K trades):")
print("-" * 70)
ro_khanna = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .eq('name', 'Ro Khanna')\
    .execute()

if ro_khanna.data:
    pol = ro_khanna.data[0]
    print(f"   Found: ID {pol['id']}, bioguide={pol.get('bioguide_id', 'N/A')}")
    
    # Check committee assignments
    ca = client.supabase.table('committee_assignments')\
        .select('id, committees(name)')\
        .eq('politician_id', pol['id'])\
        .execute()
    
    print(f"   Committee assignments: {len(ca.data)}")
    if ca.data:
        for assignment in ca.data:
            comm = assignment.get('committees', {})
            print(f"     - {comm.get('name', 'Unknown')}")
    else:
        # Check if there are committee assignments for this bioguide_id via another politician
        if pol.get('bioguide_id'):
            other_pols = client.supabase.table('politicians')\
                .select('id, name')\
                .eq('bioguide_id', pol['bioguide_id'])\
                .execute()
            
            if len(other_pols.data) > 1:
                print(f"   [WARNING] Found {len(other_pols.data)} politicians with same bioguide_id!")
                for other in other_pols.data:
                    other_ca = client.supabase.table('committee_assignments')\
                        .select('id')\
                        .eq('politician_id', other['id'])\
                        .execute()
                    print(f"     - ID {other['id']}: {other['name']} - {len(other_ca.data)} committees")

print("\n" + "="*70)


