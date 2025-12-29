#!/usr/bin/env python3
"""
Sync Missing Politicians
========================

Ensures every politician name found in 'congress_trades' has a corresponding
record in the 'politicians' table.

This fixes the "Unmatched (no DB record)" issue where we have trades but
no identity record to attach committee assignments to.
"""

import sys
import random
import string
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
from utils.politician_mapping import POLITICIAN_ALIASES, resolve_politician_name, update_trade_politician_names

def main():
    client = SupabaseClient(use_service_role=True)
    
    print("="*60)
    print("SYNCING MISSING POLITICIANS")
    print("="*60)
    
    # 1. Get all unique politician names from TRADES
    print("📥 Fetching distinct politicians from trades...")
    trades_response = client.supabase.table('congress_trades')\
        .select('politician, state, party, chamber')\
        .execute()
    
    trade_names = set(t['politician'] for t in trades_response.data)
    print(f"   Found {len(trade_names)} distinct politicians in trades.")

    # 2. Get all politician names from DB
    print("📚 Fetching existing politicians from DB...")
    db_response = client.supabase.table('politicians')\
        .select('name, bioguide_id')\
        .execute()
    db_names = set(p['name'] for p in db_response.data)
    db_bioguides = set(p['bioguide_id'] for p in db_response.data if p.get('bioguide_id'))
    print(f"   Found {len(db_names)} politicians in DB.")

    # 3. Handle Canonical Mappings (Aliases)
    # --------------------------------------
    missing_names = []
    
    for name in trade_names:
        if name in db_names:
            continue
            
        # Resolve using shared mapping
        canonical, bioguide = resolve_politician_name(name)
        
        if canonical != name and canonical in db_names:
            # Case A: Alias exists (Addison -> Mitch). Update trades to use canonical name.
            print(f"🔄 Resolving Alias: '{name}' -> '{canonical}' (Updating trades...)")
            try:
                client.supabase.table('congress_trades')\
                    .update({'politician': canonical})\
                    .eq('politician', name)\
                    .execute()
                print(f"   ✅ Updated trades for {name}")
            except Exception as e:
                print(f"   ❌ Error updating alias {name}: {e}")
        else:
            # Case B: Canonical name ALSO missing. Needs insertion.
            missing_names.append(name)

    print(f"\n🔍 Found {len(missing_names)} politicians to insert:")
    for name in missing_names:
        print(f"   - {name}")
        
    if not missing_names:
        print("\n✅ All politicians resolved!")
        return

    # Pre-fetch trade info to fill state/party/chamber (ONLY for missing names)
    trade_summary = {}
    for t in trades_response.data:
        pol = t.get('politician')
        if pol in missing_names:
            if pol not in trade_summary:
                trade_summary[pol] = {
                    'state': t.get('state'), 
                    'party': t.get('party'),
                    'chamber': t.get('chamber')
                }
            # Prefer non-null values
            if not trade_summary[pol]['state'] and t.get('state'):
                trade_summary[pol]['state'] = t.get('state')
            if not trade_summary[pol]['party'] and t.get('party'):
                trade_summary[pol]['party'] = t.get('party')
            if not trade_summary[pol]['chamber'] and t.get('chamber'):
                trade_summary[pol]['chamber'] = t.get('chamber')
    
    new_records = []
    for i, name in enumerate(missing_names):
        # Resolve using shared mapping
        canonical, bioguide = resolve_politician_name(name)
        
        # Check if this bioguide already exists in DB (even if name didn't match perfectly)
        if bioguide and bioguide in db_bioguides:
            print(f"   ⚠️  Skipping insert for {canonical}: Bioguide {bioguide} already exists.")
            # We should probably update the trades to point to the canonical name here?
            # But let's just skip insertion for now to fix the crash.
            
            # Additional safety: ensure trades use the canonical name if we found a match
            if canonical != name:
                 print(f"      (Updating trades to canonical name '{canonical}')")
                 try:
                    client.supabase.table('congress_trades')\
                        .update({'politician': canonical})\
                        .eq('politician', name)\
                        .execute()
                 except: pass
            continue

        if not bioguide:
            # Generate temp ID for unknowns
            suffix = ''.join(random.choices(string.digits, k=4))
            bioguide = f"TMP{suffix}{i}"
        
        # Get extracted metadata
        meta = trade_summary.get(name, {})
        state = meta.get('state') or 'US'
        party = meta.get('party') or 'Unknown'
        chamber = meta.get('chamber') or 'House'  # Default to House if unknown
        
        new_records.append({
            'name': canonical,
            'bioguide_id': bioguide,
            'state': state,
            'party': party,
            'chamber': chamber
        })
        print(f"   Prepared: {canonical} ({party}-{state}-{chamber}) [ID: {bioguide}]")
    
    try:
        # Insert politicians
        data = client.supabase.table('politicians').insert(new_records).execute()
        print(f"   ✅ Successfully inserted {len(data.data)} politicians")
        
        # If we inserted distinct names (e.g. "Anthony Wied" -> "Tony Wied"), update trades
        for record in new_records:
            # Find original name that maps to this canonical name
            original_names = [name for name in missing_names 
                            if resolve_politician_name(name)[0] == record['name']]
            
            for original_name in original_names:
                if original_name != record['name']:
                    print(f"   🔄 Updating trades from '{original_name}' -> '{record['name']}'...")
                    client.supabase.table('congress_trades')\
                        .update({'politician': record['name']})\
                        .eq('politician', original_name)\
                        .execute()
                    
    except Exception as e:
        print(f"   ❌ Error inserting records: {e}")
        
        # 5. Show next steps
        print("\nNext Steps:")
        print("1. Run Committee Scraper to fetch data for these new names")
        print("2. Or manually deduplicate if they are just aliases (e.g. 'Chuck' vs 'Charles')")
        
    except Exception as e:
        print(f"   ❌ Error inserting records: {e}")

if __name__ == "__main__":
    main()
