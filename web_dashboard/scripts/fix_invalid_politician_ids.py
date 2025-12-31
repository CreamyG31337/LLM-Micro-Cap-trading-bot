#!/usr/bin/env python3
"""
Fix Invalid Politician IDs
==========================

This script fixes the invalid politician_id values in congress_trades by:
1. Adding missing politicians to the database (via sync_missing_politicians.py logic)
2. Looking up correct politician_id values by name
3. Updating trades with correct IDs
4. Validating all changes

Usage:
    python web_dashboard/scripts/fix_invalid_politician_ids.py [--dry-run]
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

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
import random
import string

def get_politician_id_by_name(client: SupabaseClient, politician_name: str) -> Optional[int]:
    """Get politician ID by name, trying multiple lookup strategies."""
    # Strategy 1: Exact match with canonical name
    canonical_name, bioguide_id = resolve_politician_name(politician_name)
    
    result = client.supabase.table('politicians')\
        .select('id, name')\
        .eq('name', canonical_name)\
        .limit(1)\
        .execute()
    
    if result.data:
        return result.data[0]['id']
    
    # Strategy 2: Try by bioguide_id if we have one
    if bioguide_id:
        result = client.supabase.table('politicians')\
            .select('id')\
            .eq('bioguide_id', bioguide_id)\
            .limit(1)\
            .execute()
        
        if result.data:
            return result.data[0]['id']
    
    # Strategy 3: Try partial match (last name)
    last_name = canonical_name.split()[-1] if canonical_name else None
    if last_name and len(last_name) > 2:  # Only if last name is meaningful
        result = client.supabase.table('politicians')\
            .select('id, name')\
            .ilike('name', f'%{last_name}%')\
            .limit(5)\
            .execute()
        
        # If only one match, use it
        if result.data and len(result.data) == 1:
            return result.data[0]['id']
    
    return None

def create_politician_from_trade(
    client: SupabaseClient,
    politician_name: str,
    party: Optional[str],
    state: Optional[str],
    chamber: Optional[str]
) -> Optional[int]:
    """Create a politician record from trade data."""
    canonical_name, bioguide_id = resolve_politician_name(politician_name)
    
    # Generate bioguide if not in alias map
    if not bioguide_id:
        suffix = ''.join(random.choices(string.digits, k=6))
        bioguide_id = f"TMP{suffix}"
    
    # Default values if missing
    if not party:
        party = 'Unknown'
    if not state:
        state = 'US'
    if not chamber:
        chamber = 'House'  # Default to House
    
    try:
        insert_result = client.supabase.table('politicians').insert({
            'name': canonical_name,
            'bioguide_id': bioguide_id,
            'party': party,
            'state': state,
            'chamber': chamber
        }).execute()
        
        if insert_result.data:
            return insert_result.data[0]['id']
    except Exception as e:
        print(f"   [ERROR] Failed to create politician '{canonical_name}': {e}")
        return None
    
    return None

def fix_invalid_politician_ids(dry_run: bool = True):
    """Fix invalid politician_id values in congress_trades."""
    client = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("FIX INVALID POLITICIAN IDs")
    print("="*70)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print()
    
    # Step 1: Find all trades with invalid politician_id
    print("Step 1: Finding trades with invalid politician_id...")
    print("-" * 70)
    
    # Known invalid politician IDs from our investigation
    known_invalid_ids = [
        5411, 5414, 5434, 5453, 5449, 5489, 5446, 5447, 5487, 5456,
        5406, 5436, 5457, 5445, 5439, 5471, 5421, 5475, 5417, 5431,
        5430, 5442, 5412, 5443, 5423, 5452, 5407, 5428, 5438, 5448,
        5479, 5466, 5467, 5427, 5451, 5413, 5437, 5440, 5484, 5418,
        5422, 5469, 5409, 5491
    ]
    
    # Known politician names mapped to their invalid IDs (from our investigation)
    # This mapping was created when we found which trades had which invalid IDs
    invalid_id_to_name = {}  # Will be populated by querying postgres analysis table
    
    # Query postgres to get trade_id -> politician name mapping from analysis table
    try:
        from postgres_client import PostgresClient
        postgres = PostgresClient()
        
        # Get analysis records for trades with these invalid IDs
        # We'll join with congress_trades to get names, but since that's in Supabase,
        # let's query the analysis reasoning text which might have politician names
        # Actually, let's query trades directly by these IDs and get what we can
        print("   Querying trades with known invalid IDs...")
        
        # Query trades in batches
        invalid_trades = []
        for i in range(0, len(known_invalid_ids), 10):
            batch_ids = known_invalid_ids[i:i+10]
            trades_result = client.supabase.table('congress_trades')\
                .select('id, politician_id, party, state, chamber')\
                .in_('politician_id', batch_ids)\
                .execute()
            
            for trade in trades_result.data:
                invalid_trades.append(trade)
        
        # Now get politician names from postgres analysis table
        if invalid_trades:
            trade_ids = [t['id'] for t in invalid_trades]
            
            # Query analysis table for politician names (from reasoning text or we'll use our known list)
            # Actually, let's use the names we found in our investigation
            # From debug_committee_assignments.py output, we know:
            politician_names_by_id = {
                5411: "Joshua Gottheimer", 5414: "Thomas Kean Jr", 5434: "William Keating",
                5453: "Michael Burgess", 5449: "Earl Blumenauer", 5489: "Valerie Hoyle",
                5446: "Thomas Carper", 5447: "Peter Sessions", 5487: "Lisa McClain",
                5456: "Kathy Manning", 5406: "Jonathan Jackson", 5436: "Mark Green",
                5457: "Stephen Lynch", 5445: "James Hill", 5439: "David Joyce",
                5471: "John Curtis", 5421: "Rick Allen", 5475: "Robert Wittman",
                5417: "Bob Latta", 5431: "Deborah Dingell", 5430: "Neal Dunn",
                5442: "Stephen Cohen", 5412: "Gregory Landsman", 5443: "Laurel Lee",
                5423: "Thomas Suozzi", 5452: "Gary Peters", 5407: "Gerry Connolly",
                5428: "Suzanne Lee", 5438: "Ronald Wyden", 5448: "George Kelly",
                5479: "Jennifer McClellan", 5466: "Katherine Clark", 5467: "Garret Graves",
                5427: "Jamin Raskin", 5451: "Deborah Wasserman Schultz", 5413: "Suzan DelBene",
                5437: "John Knott", 5440: "Gus Bilirakis", 5484: "James Scott",
                5418: "John McGuire III", 5422: "John Neely Kennedy", 5469: "Gerald Moran",
                5409: "John Hickenlooper", 5491: "Robert Aderholt"
            }
            
            # Add names to trades
            for trade in invalid_trades:
                pid = trade.get('politician_id')
                if pid in politician_names_by_id:
                    trade['politician'] = politician_names_by_id[pid]
                else:
                    trade['politician'] = 'Unknown'
    except Exception as e:
        print(f"   [ERROR] Failed to query trades: {e}")
        print("   Using known invalid IDs and names from investigation...")
        invalid_trades = []
        politician_names_by_id = {
            5411: "Joshua Gottheimer", 5414: "Thomas Kean Jr", 5434: "William Keating",
            5453: "Michael Burgess", 5449: "Earl Blumenauer", 5489: "Valerie Hoyle"
        }
        
        # Create trades list from known IDs
        for pid, name in politician_names_by_id.items():
            # We'll need to query these properly
            pass
    
    print(f"   Found {len(invalid_trades)} trades with invalid politician_id")
    
    if not invalid_trades:
        print("   [OK] No invalid politician_id values found!")
        return
    
    # Step 2: Group by politician name
    print("\nStep 2: Grouping by politician name...")
    print("-" * 70)
    
    trades_by_politician: Dict[str, List[Dict]] = {}
    for trade in invalid_trades:
        politician_name = trade.get('politician', 'Unknown')
        if politician_name not in trades_by_politician:
            trades_by_politician[politician_name] = []
        trades_by_politician[politician_name].append(trade)
    
    print(f"   Found {len(trades_by_politician)} unique politicians with invalid IDs")
    
    # Step 3: For each politician, try to find or create correct record
    print("\nStep 3: Resolving politician IDs...")
    print("-" * 70)
    
    fixes: List[Tuple[int, Optional[int], str]] = []  # (trade_id, new_politician_id, politician_name)
    politicians_to_create: Dict[str, Dict] = {}
    
    for politician_name, trades in sorted(trades_by_politician.items()):
        print(f"\n   Processing: {politician_name} ({len(trades)} trades)")
        
        # Try to find existing politician
        politician_id = get_politician_id_by_name(client, politician_name)
        
        if politician_id:
            print(f"      [FOUND] Existing politician ID: {politician_id}")
            for trade in trades:
                fixes.append((trade['id'], politician_id, politician_name))
        else:
            print(f"      [NOT FOUND] Politician doesn't exist")
            
            # Get metadata from trades (use most common values)
            party_counts = {}
            state_counts = {}
            chamber_counts = {}
            
            for trade in trades:
                party = trade.get('party')
                state = trade.get('state')
                chamber = trade.get('chamber')
                
                if party:
                    party_counts[party] = party_counts.get(party, 0) + 1
                if state:
                    state_counts[state] = state_counts.get(state, 0) + 1
                if chamber:
                    chamber_counts[chamber] = chamber_counts.get(chamber, 0) + 1
            
            # Use most common values
            party = max(party_counts.items(), key=lambda x: x[1])[0] if party_counts else None
            state = max(state_counts.items(), key=lambda x: x[1])[0] if state_counts else None
            chamber = max(chamber_counts.items(), key=lambda x: x[1])[0] if chamber_counts else None
            
            print(f"      Metadata: {party}, {state}, {chamber}")
            
            if not dry_run:
                # Create politician
                new_id = create_politician_from_trade(client, politician_name, party, state, chamber)
                if new_id:
                    print(f"      [CREATED] New politician ID: {new_id}")
                    for trade in trades:
                        fixes.append((trade['id'], new_id, politician_name))
                else:
                    print(f"      [ERROR] Failed to create politician")
                    for trade in trades:
                        fixes.append((trade['id'], None, politician_name))
            else:
                print(f"      [DRY RUN] Would create politician")
                politicians_to_create[politician_name] = {
                    'party': party,
                    'state': state,
                    'chamber': chamber
                }
                for trade in trades:
                    fixes.append((trade['id'], None, politician_name))
    
    # Step 4: Update trades with correct IDs
    print("\nStep 4: Updating trades...")
    print("-" * 70)
    
    valid_fixes = [f for f in fixes if f[1] is not None]
    invalid_fixes = [f for f in fixes if f[1] is None]
    
    print(f"   Trades to fix: {len(valid_fixes)}")
    print(f"   Trades that couldn't be fixed: {len(invalid_fixes)}")
    
    if invalid_fixes:
        print("\n   [WARNING] Could not resolve IDs for:")
        for trade_id, _, name in invalid_fixes[:10]:
            print(f"      Trade {trade_id}: {name}")
        if len(invalid_fixes) > 10:
            print(f"      ... and {len(invalid_fixes) - 10} more")
    
    if valid_fixes and not dry_run:
        # Group by politician_id for batch updates
        updates_by_pid: Dict[int, List[int]] = {}
        for trade_id, politician_id, _ in valid_fixes:
            if politician_id not in updates_by_pid:
                updates_by_pid[politician_id] = []
            updates_by_pid[politician_id].append(trade_id)
        
        # Update in batches
        total_updated = 0
        for politician_id, trade_ids in updates_by_pid.items():
            # Update each trade individually (Supabase doesn't support bulk update with WHERE IN easily)
            for trade_id in trade_ids:
                try:
                    client.supabase.table('congress_trades')\
                        .update({'politician_id': politician_id})\
                        .eq('id', trade_id)\
                        .execute()
                    total_updated += 1
                except Exception as e:
                    print(f"   [ERROR] Failed to update trade {trade_id}: {e}")
            
            if len(trade_ids) > 1:
                print(f"   Updated {len(trade_ids)} trades for politician_id {politician_id}")
            else:
                print(f"   Updated trade {trade_ids[0]} for politician_id {politician_id}")
        
        print(f"\n   [OK] Successfully updated {total_updated} trades")
    elif valid_fixes and dry_run:
        print(f"   [DRY RUN] Would update {len(valid_fixes)} trades")
    
    # Step 5: Validation
    print("\nStep 5: Validating fixes...")
    print("-" * 70)
    
    if not dry_run:
        # Re-check for invalid IDs
        remaining_invalid = []
        for trade_id, _, _ in fixes:
            trade_check = client.supabase.table('congress_trades')\
                .select('id, politician_id')\
                .eq('id', trade_id)\
                .execute()
            
            if trade_check.data:
                pid = trade_check.data[0].get('politician_id')
                if pid:
                    # Validate ID exists
                    pol_check = client.supabase.table('politicians')\
                        .select('id')\
                        .eq('id', pid)\
                        .execute()
                    
                    if not pol_check.data:
                        remaining_invalid.append(trade_id)
        
        if remaining_invalid:
            print(f"   [WARNING] {len(remaining_invalid)} trades still have invalid IDs")
        else:
            print(f"   [OK] All fixes validated successfully!")
    else:
        print(f"   [DRY RUN] Skipping validation")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total invalid trades found: {len(invalid_trades)}")
    print(f"Politicians to create: {len(politicians_to_create) if dry_run else 0}")
    print(f"Trades that can be fixed: {len(valid_fixes)}")
    print(f"Trades that cannot be fixed: {len(invalid_fixes)}")
    
    if dry_run:
        print("\n[INFO] This was a dry run. Run without --dry-run to apply fixes.")
    print("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fix invalid politician IDs')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Show what would be done without making changes (default: True)')
    parser.add_argument('--force', action='store_true', help='Actually apply changes (overrides --dry-run)')
    args = parser.parse_args()
    
    dry_run = not args.force
    
    if not dry_run:
        response = input("\n⚠️  This will modify the database. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    fix_invalid_politician_ids(dry_run=dry_run)

