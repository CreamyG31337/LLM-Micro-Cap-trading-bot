#!/usr/bin/env python3
"""Find remaining invalid politician IDs"""
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

client = SupabaseClient()

# Get all trades with politician_id
all_trades = client.supabase.table('congress_trades')\
    .select('id, politician_id')\
    .not_.is_('politician_id', 'null')\
    .limit(5000)\
    .execute()

# Get all valid politician IDs
valid_pols = client.supabase.table('politicians')\
    .select('id')\
    .execute()

valid_ids = {p['id'] for p in valid_pols.data}
print(f"Valid politician IDs: {len(valid_ids)}")
if valid_ids:
    print(f"Sample range: {min(valid_ids)} to {max(valid_ids)}")
else:
    print("  [WARNING] No politicians found in database!")

# Find invalid
invalid_trades = [t for t in all_trades.data if t.get('politician_id') not in valid_ids]
invalid_ids = set(t.get('politician_id') for t in invalid_trades if t.get('politician_id'))

print(f"\nInvalid trades: {len(invalid_trades)}")
print(f"Unique invalid IDs: {len(invalid_ids)}")
print(f"Invalid IDs: {sorted(list(invalid_ids))[:20]}")

