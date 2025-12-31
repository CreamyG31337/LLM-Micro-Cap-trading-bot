#!/usr/bin/env python3
"""Check for duplicate politicians"""
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

# Check for duplicates
names_to_check = ["Joshua Gottheimer", "Bob Latta", "Thomas Kean Jr"]

print("Checking for duplicate politicians:")
print("=" * 70)

for name in names_to_check:
    r = client.supabase.table('politicians')\
        .select('id, name, bioguide_id')\
        .eq('name', name)\
        .execute()
    
    print(f"\n{name}: {len(r.data)} record(s)")
    for p in r.data:
        print(f"  ID {p['id']}: bioguide={p.get('bioguide_id', 'N/A')}")

# Check which IDs trades are using
print("\n" + "=" * 70)
print("Checking which politician_ids trades are using:")
print("=" * 70)

r = client.supabase.table('congress_trades')\
    .select('politician_id')\
    .eq('politician_id', 5411)\
    .limit(1)\
    .execute()

print(f"Trades with politician_id 5411: {r.count if hasattr(r, 'count') else 'checking...'}")

r2 = client.supabase.table('congress_trades')\
    .select('politician_id')\
    .eq('politician_id', 5514)\
    .limit(1)\
    .execute()

print(f"Trades with politician_id 5514: {r2.count if hasattr(r2, 'count') else 'checking...'}")


