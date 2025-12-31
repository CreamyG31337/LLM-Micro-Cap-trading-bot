#!/usr/bin/env python3
"""Verify the fix worked"""
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

# Check politicians we created
print("Checking newly created politicians...")
r = client.supabase.table('politicians')\
    .select('id, name')\
    .in_('id', [5493, 5494, 5514])\
    .execute()

print(f"Found {len(r.data)} of the new politicians:")
for p in r.data:
    print(f"  ID {p['id']}: {p['name']}")

# Check trades we fixed
print("\nChecking fixed trades...")
r2 = client.supabase.table('congress_trades')\
    .select('id, politician_id')\
    .in_('politician_id', [5514])\
    .limit(5)\
    .execute()

print(f"Found {len(r2.data)} trades with politician_id 5514 (Joshua Gottheimer)")

# Check for remaining invalid IDs
print("\nChecking for remaining invalid IDs...")
all_trades = client.supabase.table('congress_trades')\
    .select('id, politician_id')\
    .not_.is_('politician_id', 'null')\
    .limit(100)\
    .execute()

all_pols = client.supabase.table('politicians')\
    .select('id')\
    .execute()

valid_ids = {p['id'] for p in all_pols.data}
invalid = [t for t in all_trades.data if t.get('politician_id') not in valid_ids]

print(f"Sample of 100 trades: {len(invalid)} have invalid IDs")
if invalid:
    invalid_ids = set(t.get('politician_id') for t in invalid)
    print(f"Invalid IDs found: {sorted(list(invalid_ids))[:10]}")


