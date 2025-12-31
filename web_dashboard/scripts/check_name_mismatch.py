#!/usr/bin/env python3
"""
Check for name mismatches between trades and politicians table
This could explain why politician_id values are invalid
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient
from utils.politician_mapping import resolve_politician_name

def main():
    print("Checking Name Mismatches Between Trades and Politicians")
    print("=" * 70)
    
    supabase = SupabaseClient()
    
    # Problematic politician names from our investigation
    problematic_names = [
        "Joshua Gottheimer", "Thomas Kean Jr", "William Keating", "Michael Burgess",
        "Earl Blumenauer", "Valerie Hoyle", "Thomas Carper", "Peter Sessions",
        "Lisa McClain", "Kathy Manning"
    ]
    
    print("\n1. Checking how trade names resolve to canonical names...")
    print("-" * 70)
    
    for trade_name in problematic_names:
        canonical_name, bioguide_id = resolve_politician_name(trade_name)
        
        if canonical_name != trade_name:
            print(f"   {trade_name} -> {canonical_name} (mapped)")
        else:
            print(f"   {trade_name} -> {canonical_name} (no mapping)")
        
        # Check if canonical name exists in database
        result = supabase.supabase.table('politicians')\
            .select('id, name, bioguide_id')\
            .eq('name', canonical_name)\
            .execute()
        
        if result.data:
            pol = result.data[0]
            print(f"      [FOUND] ID: {pol['id']}, Name: {pol['name']}, Bioguide: {pol.get('bioguide_id', 'N/A')}")
        else:
            print(f"      [NOT FOUND] Canonical name '{canonical_name}' not in database")
            
            # Try searching by partial match
            partial_result = supabase.supabase.table('politicians')\
                .select('id, name, bioguide_id')\
                .ilike('name', f'%{canonical_name.split()[-1]}%')\
                .execute()
            
            if partial_result.data:
                print(f"      [PARTIAL MATCH] Found similar names:")
                for p in partial_result.data[:3]:
                    print(f"         - {p['name']} (ID: {p['id']})")
    
    print("\n2. Checking what names are actually in trades...")
    print("-" * 70)
    
    # Get sample trades for these politicians
    for trade_name in problematic_names[:5]:
        trades = supabase.supabase.table('congress_trades_enriched')\
            .select('politician, politician_id')\
            .eq('politician', trade_name)\
            .limit(1)\
            .execute()
        
        if trades.data:
            trade = trades.data[0]
            print(f"   Trade name: '{trade['politician']}' -> politician_id: {trade.get('politician_id')}")
            
            # Check if this ID exists
            if trade.get('politician_id'):
                pol_check = supabase.supabase.table('politicians')\
                    .select('id, name')\
                    .eq('id', trade['politician_id'])\
                    .execute()
                
                if pol_check.data:
                    print(f"      [ID EXISTS] Points to: {pol_check.data[0]['name']}")
                else:
                    print(f"      [ID INVALID] ID {trade['politician_id']} does not exist")
    
    print("\n3. Checking if politicians exist with different name variations...")
    print("-" * 70)
    
    # Try searching for these politicians by last name
    for trade_name in problematic_names[:5]:
        last_name = trade_name.split()[-1]
        
        result = supabase.supabase.table('politicians')\
            .select('id, name, bioguide_id')\
            .ilike('name', f'%{last_name}%')\
            .execute()
        
        if result.data:
            print(f"   '{trade_name}' (last name: {last_name}):")
            for pol in result.data:
                print(f"      - {pol['name']} (ID: {pol['id']}, Bioguide: {pol.get('bioguide_id', 'N/A')})")
        else:
            print(f"   '{trade_name}' (last name: {last_name}): [NOT FOUND]")
    
    print("\n4. Checking if backfill script would find these politicians...")
    print("-" * 70)
    
    from utils.politician_mapping import get_or_create_politician
    
    for trade_name in problematic_names[:5]:
        # Simulate what backfill script would do
        canonical_name, _ = resolve_politician_name(trade_name)
        
        # Try lookup (without creating)
        result = supabase.supabase.table('politicians')\
            .select('id, name')\
            .eq('name', canonical_name)\
            .execute()
        
        if result.data:
            print(f"   '{trade_name}' -> '{canonical_name}' -> ID: {result.data[0]['id']} [OK]")
        else:
            print(f"   '{trade_name}' -> '{canonical_name}' -> [NOT FOUND]")
            print(f"      This would fail in backfill script!")

if __name__ == "__main__":
    main()

