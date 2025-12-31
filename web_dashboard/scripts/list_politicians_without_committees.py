#!/usr/bin/env python3
"""List all politicians without committee assignments"""
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
print("POLITICIANS WITHOUT COMMITTEE ASSIGNMENTS")
print("="*70)

# Get all politicians
all_politicians = client.supabase.table('politicians')\
    .select('id, name, bioguide_id, party, state, chamber')\
    .execute()

print(f"\nTotal politicians in database: {len(all_politicians.data)}")

# Get all politicians with committee assignments (handle pagination)
pol_ids_with_committees = set()
page_size = 1000
offset = 0

while True:
    pols_with_committees = client.supabase.table('committee_assignments')\
        .select('politician_id')\
        .range(offset, offset + page_size - 1)\
        .execute()
    
    if not pols_with_committees.data:
        break
    
    pol_ids_with_committees.update({ca['politician_id'] for ca in pols_with_committees.data})
    
    if len(pols_with_committees.data) < page_size:
        break
    
    offset += page_size

# Find politicians without committees
pols_without_committees = [
    p for p in all_politicians.data 
    if p['id'] not in pol_ids_with_committees
]

print(f"Politicians with committee assignments: {len(pol_ids_with_committees)}")
print(f"Politicians WITHOUT committee assignments: {len(pols_without_committees)}")

# Group by bioguide type
tmp_bioguide = [p for p in pols_without_committees if p.get('bioguide_id', '').startswith('TMP')]
proper_bioguide = [p for p in pols_without_committees if p.get('bioguide_id') and not p.get('bioguide_id', '').startswith('TMP')]
no_bioguide = [p for p in pols_without_committees if not p.get('bioguide_id')]

print(f"\nBreakdown:")
print(f"  - With temporary bioguide IDs (TMP...): {len(tmp_bioguide)}")
print(f"  - With proper bioguide IDs: {len(proper_bioguide)}")
print(f"  - No bioguide ID: {len(no_bioguide)}")

# Count trades for each
print("\n" + "="*70)
print("DETAILED LIST")
print("="*70)

# Sort by number of trades (descending)
pols_with_trade_counts = []
for pol in pols_without_committees:
    # Count trades for this politician
    trades_result = client.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .eq('politician_id', pol['id'])\
        .execute()
    
    trade_count = trades_result.count if hasattr(trades_result, 'count') else len(trades_result.data)
    pols_with_trade_counts.append((pol, trade_count))

# Sort by trade count descending
pols_with_trade_counts.sort(key=lambda x: x[1], reverse=True)

print(f"\n{'Name':<35} {'Bioguide ID':<15} {'Party':<12} {'State':<6} {'Chamber':<8} {'Trades':<8}")
print("-" * 100)

for pol, trade_count in pols_with_trade_counts:
    name = pol['name'][:34]  # Truncate if too long
    bioguide = pol.get('bioguide_id', 'N/A')[:14]
    party = (pol.get('party') or 'N/A')[:11]
    state = (pol.get('state') or 'N/A')[:5]
    chamber = (pol.get('chamber') or 'N/A')[:7]
    
    print(f"{name:<35} {bioguide:<15} {party:<12} {state:<6} {chamber:<8} {trade_count:<8}")

# Summary by category
print("\n" + "="*70)
print("SUMMARY BY CATEGORY")
print("="*70)

if tmp_bioguide:
    print(f"\n1. Politicians with TEMPORARY bioguide IDs ({len(tmp_bioguide)}):")
    print("   (These were likely created from trade data and not in YAML)")
    tmp_with_trades = [(p, sum(1 for _, count in pols_with_trade_counts if _['id'] == p['id'] and count > 0)) 
                       for p in tmp_bioguide]
    tmp_with_trades.sort(key=lambda x: x[1], reverse=True)
    for pol, _ in tmp_with_trades[:20]:  # Show top 20
        trades_result = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .eq('politician_id', pol['id'])\
            .execute()
        trade_count = trades_result.count if hasattr(trades_result, 'count') else len(trades_result.data)
        if trade_count > 0:
            print(f"   - {pol['name']} ({pol.get('bioguide_id', 'N/A')}) - {trade_count} trades")
    if len([p for p, _ in tmp_with_trades if _ > 0]) > 20:
        print(f"   ... and {len([p for p, _ in tmp_with_trades if _ > 0]) - 20} more with trades")

if proper_bioguide:
    print(f"\n2. Politicians with PROPER bioguide IDs but no committees ({len(proper_bioguide)}):")
    print("   (These should be in YAML but might not have committee assignments)")
    for pol in proper_bioguide[:20]:  # Show top 20
        trades_result = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .eq('politician_id', pol['id'])\
            .execute()
        trade_count = trades_result.count if hasattr(trades_result, 'count') else len(trades_result.data)
        if trade_count > 0:
            print(f"   - {pol['name']} ({pol.get('bioguide_id', 'N/A')}) - {trade_count} trades")
    remaining = [p for p in proper_bioguide[20:] if True]
    if remaining:
        print(f"   ... and {len(remaining)} more")

if no_bioguide:
    print(f"\n3. Politicians with NO bioguide ID ({len(no_bioguide)}):")
    for pol in no_bioguide[:20]:  # Show top 20
        trades_result = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .eq('politician_id', pol['id'])\
            .execute()
        trade_count = trades_result.count if hasattr(trades_result, 'count') else len(trades_result.data)
        if trade_count > 0:
            print(f"   - {pol['name']} - {trade_count} trades")
    if len(no_bioguide) > 20:
        print(f"   ... and {len(no_bioguide) - 20} more")

# Export to CSV
print("\n" + "="*70)
print("EXPORTING TO CSV")
print("="*70)

csv_path = Path(__file__).parent / 'politicians_without_committees.csv'
with open(csv_path, 'w', encoding='utf-8') as f:
    f.write("Name,Bioguide ID,Party,State,Chamber,Trade Count\n")
    for pol, trade_count in pols_with_trade_counts:
        name = pol['name'].replace(',', ';')  # Replace commas to avoid CSV issues
        bioguide = pol.get('bioguide_id', 'N/A')
        party = pol.get('party', 'N/A')
        state = pol.get('state', 'N/A')
        chamber = pol.get('chamber', 'N/A')
        f.write(f"{name},{bioguide},{party},{state},{chamber},{trade_count}\n")

print(f"\n✅ Exported to: {csv_path}")
print(f"   Total politicians without committees: {len(pols_without_committees)}")
print("="*70)

