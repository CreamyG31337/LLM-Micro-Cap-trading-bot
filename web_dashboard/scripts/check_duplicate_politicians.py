#!/usr/bin/env python3
"""Check for duplicate politicians"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Check Ro Khanna specifically
print("Checking Ro Khanna:")
r = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .eq('name', 'Ro Khanna')\
    .execute()

print(f"Found {len(r.data)} politicians named 'Ro Khanna':")
for p in r.data:
    print(f"  ID {p['id']}: bioguide={p.get('bioguide_id', 'N/A')}")
    ca = client.supabase.table('committee_assignments')\
        .select('id')\
        .eq('politician_id', p['id'])\
        .execute()
    print(f"    Committee assignments: {len(ca.data)}")
    
    # Check trades
    trades = client.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .eq('politician_id', p['id'])\
        .execute()
    trade_count = trades.count if hasattr(trades, 'count') else len(trades.data)
    print(f"    Trades: {trade_count}")

# Check for duplicates by bioguide_id
print("\n\nChecking for duplicate bioguide IDs:")
all_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.is_('bioguide_id', 'null')\
    .execute()

bioguide_counts = {}
for p in all_pols.data:
    bg = p.get('bioguide_id')
    if bg not in bioguide_counts:
        bioguide_counts[bg] = []
    bioguide_counts[bg].append(p)

duplicates = {bg: pols for bg, pols in bioguide_counts.items() if len(pols) > 1}
print(f"Found {len(duplicates)} bioguide IDs with duplicates:")

for bg, pols in list(duplicates.items())[:10]:
    print(f"\n  {bg}: {len(pols)} politicians")
    for p in pols:
        ca = client.supabase.table('committee_assignments')\
            .select('id')\
            .eq('politician_id', p['id'])\
            .execute()
        trades = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .eq('politician_id', p['id'])\
            .execute()
        trade_count = trades.count if hasattr(trades, 'count') else len(trades.data)
        print(f"    ID {p['id']}: {p['name']} - {len(ca.data)} committees, {trade_count} trades")

if len(duplicates) > 10:
    print(f"\n  ... and {len(duplicates) - 10} more duplicate bioguide IDs")


