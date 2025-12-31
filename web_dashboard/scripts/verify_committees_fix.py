#!/usr/bin/env python3
"""Verify politicians can now be looked up for committees"""
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
from utils.politician_mapping import resolve_politician_name

client = SupabaseClient(use_service_role=True)

# Check a few of the fixed politicians
test_names = ["Joshua Gottheimer", "Bob Latta", "Thomas Kean Jr"]

print("Verifying politicians and committee assignments:")
print("=" * 70)

for name in test_names:
    canonical, _ = resolve_politician_name(name)
    r = client.supabase.table('politicians')\
        .select('id, name')\
        .eq('name', canonical)\
        .execute()
    
    if r.data:
        pid = r.data[0]['id']
        print(f"\n{name} -> {canonical}")
        print(f"  [OK] Found in database: ID {pid}")
        
        # Check committee assignments
        ca = client.supabase.table('committee_assignments')\
            .select('id, committees(name)')\
            .eq('politician_id', pid)\
            .execute()
        
        if ca.data:
            print(f"  [OK] Has {len(ca.data)} committee assignment(s)")
            for assignment in ca.data[:3]:
                comm = assignment.get('committees', {})
                print(f"      - {comm.get('name', 'Unknown')}")
        else:
            print(f"  [INFO] No committee assignments (politician exists, committees need to be synced)")
    else:
        print(f"\n{name} -> {canonical}")
        print(f"  [ERROR] Not found in database")

print("\n" + "=" * 70)
print("Summary: Politicians are now in database and can be looked up.")
print("If they don't have committees, run seed_committees.py to add them.")


