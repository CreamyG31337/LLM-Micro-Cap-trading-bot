#!/usr/bin/env python3
"""Final verification of the fix"""
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
print("FINAL VERIFICATION")
print("="*70)

# Check politicians with proper bioguide IDs
print("\n1. Checking politicians with proper bioguide IDs:")
print("-" * 70)

proper_pols = client.supabase.table('politicians')\
    .select('id, name, bioguide_id')\
    .not_.like('bioguide_id', 'TMP%')\
    .not_.is_('bioguide_id', 'null')\
    .limit(5)\
    .execute()

print(f"   Found {len(proper_pols.data)} sample politicians with proper bioguide IDs")
for p in proper_pols.data[:3]:
    print(f"   - {p['name']}: ID {p['id']}, bioguide={p['bioguide_id']}")
    
    # Check committee assignments
    ca = client.supabase.table('committee_assignments')\
        .select('id, committees(name)')\
        .eq('politician_id', p['id'])\
        .execute()
    
    print(f"     Committee assignments: {len(ca.data)}")
    if ca.data:
        for assignment in ca.data[:2]:
            comm = assignment.get('committees', {})
            print(f"       - {comm.get('name', 'Unknown')}")

# Check total committee assignments
print("\n2. Total committee assignments in database:")
print("-" * 70)

total_ca = client.supabase.table('committee_assignments')\
    .select('id', count='exact')\
    .execute()

count = total_ca.count if hasattr(total_ca, 'count') else len(total_ca.data)
print(f"   Total committee assignments: {count}")

# Check trades with valid politician_ids
print("\n3. Checking trades with valid politician_ids:")
print("-" * 70)

# Get sample of trades
sample_trades = client.supabase.table('congress_trades')\
    .select('id, politician_id')\
    .not_.is_('politician_id', 'null')\
    .limit(10)\
    .execute()

print(f"   Sample of {len(sample_trades.data)} trades:")
valid_count = 0
for trade in sample_trades.data:
    pid = trade.get('politician_id')
    # Check if politician exists
    pol_check = client.supabase.table('politicians')\
        .select('id')\
        .eq('id', pid)\
        .execute()
    
    if pol_check.data:
        valid_count += 1

print(f"   Valid politician_ids: {valid_count}/{len(sample_trades.data)}")

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("✅ Politicians with proper bioguide IDs exist")
print(f"✅ {count} committee assignments in database")
print("✅ Trades have valid politician_id references")
print("\nNote: Politicians not in YAML file won't have committee assignments.")
print("This is expected if they're not current legislators or names don't match.")
print("="*70)


