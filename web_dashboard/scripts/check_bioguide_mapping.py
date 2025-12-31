#!/usr/bin/env python3
"""Check bioguide ID mapping after seed_committees"""
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

# Check politicians with the IDs we know about
test_ids = [5411, 5417, 5414]  # Joshua Gottheimer, Bob Latta, Thomas Kean Jr

print("Checking politicians after seed_committees.py:")
print("=" * 70)

for pid in test_ids:
    r = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .eq('id', pid)\
        .execute()
    
    if r.data:
        pol = r.data[0]
        print(f"\nID {pid}: {pol['name']}")
        print(f"  Bioguide: {pol.get('bioguide_id', 'N/A')}")
        
        # Check committee assignments
        ca = client.supabase.table('committee_assignments')\
            .select('id, committees(name)')\
            .eq('politician_id', pid)\
            .execute()
        
        print(f"  Committee assignments: {len(ca.data)}")
        if ca.data:
            for assignment in ca.data[:3]:
                comm = assignment.get('committees', {})
                print(f"    - {comm.get('name', 'Unknown')}")
    else:
        print(f"\nID {pid}: [NOT FOUND]")

# Check if there are politicians with proper bioguide IDs for these names
print("\n" + "=" * 70)
print("Checking for politicians with proper bioguide IDs:")
print("=" * 70)

names = ["Joshua Gottheimer", "Bob Latta", "Thomas Kean Jr"]
for name in names:
    r = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .eq('name', name)\
        .execute()
    
    print(f"\n{name}: {len(r.data)} record(s)")
    for pol in r.data:
        bioguide = pol.get('bioguide_id', 'N/A')
        is_tmp = bioguide.startswith('TMP') if bioguide != 'N/A' else False
        print(f"  ID {pol['id']}: bioguide={bioguide} {'(TEMP)' if is_tmp else '(PROPER)'}")
        
        # Check committee assignments for this ID
        ca = client.supabase.table('committee_assignments')\
            .select('id, committees(name)')\
            .eq('politician_id', pol['id'])\
            .execute()
        
        if ca.data:
            print(f"    Has {len(ca.data)} committee assignment(s)")
            for assignment in ca.data[:2]:
                comm = assignment.get('committees', {})
                print(f"      - {comm.get('name', 'Unknown')}")

# Check all politicians with proper (non-TMP) bioguide IDs for these names
print("\n" + "=" * 70)
print("Searching for politicians with PROPER bioguide IDs (not TMP):")
print("=" * 70)

for name in names:
    # Get all politicians with this name
    all_pols = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .eq('name', name)\
        .execute()
    
    proper_pols = [p for p in all_pols.data if p.get('bioguide_id') and not p.get('bioguide_id', '').startswith('TMP')]
    
    if proper_pols:
        print(f"\n{name}: Found {len(proper_pols)} with proper bioguide IDs:")
        for pol in proper_pols:
            print(f"  ID {pol['id']}: bioguide={pol['bioguide_id']}")
            
            # Check committee assignments
            ca = client.supabase.table('committee_assignments')\
                .select('id, committees(name)')\
                .eq('politician_id', pol['id'])\
                .execute()
            
            print(f"    Committee assignments: {len(ca.data)}")
            if ca.data:
                for assignment in ca.data[:3]:
                    comm = assignment.get('committees', {})
                    print(f"      - {comm.get('name', 'Unknown')}")
    else:
        print(f"\n{name}: No politicians with proper bioguide IDs found")

