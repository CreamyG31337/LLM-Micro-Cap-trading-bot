#!/usr/bin/env python3
"""Quick verification of politician IDs"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from supabase_client import SupabaseClient
from utils.politician_mapping import resolve_politician_name

client = SupabaseClient()

# Check if IDs exist
print("Checking if invalid IDs exist:")
r = client.supabase.table('politicians').select('id, name').in_('id', [5411, 5414, 5434, 5417]).execute()
print(f'  IDs 5411, 5414, 5434, 5417: Found {len(r.data)}')
for p in r.data:
    print(f"    ID {p['id']}: {p['name']}")

# Check if politicians exist by name
print("\nChecking if politicians exist by name:")
for name in ["Joshua Gottheimer", "Thomas Kean Jr", "Bob Latta"]:
    canonical, _ = resolve_politician_name(name)
    r = client.supabase.table('politicians').select('id, name').eq('name', canonical).execute()
    print(f"  {name} -> {canonical}: Found {len(r.data)}")
    for p in r.data:
        print(f"    ID {p['id']}: {p['name']}")

# Check what lookup returns
print("\nChecking lookup by name:")
for name in ["Bob Latta", "Joshua Gottheimer"]:
    canonical, _ = resolve_politician_name(name)
    r = client.supabase.table('politicians').select('id, name').eq('name', canonical).execute()
    if r.data:
        print(f"  {name} -> {canonical}: Found ID {r.data[0]['id']}")
    else:
        print(f"  {name} -> {canonical}: Not found")

