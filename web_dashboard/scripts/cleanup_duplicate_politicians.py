#!/usr/bin/env python3
"""
Cleanup Duplicate Politicians
==============================

Removes duplicate politicians we created and updates trades to use original IDs.
Then seed_committees.py can be run to add proper bioguide IDs and committees.

Usage:
    python web_dashboard/scripts/cleanup_duplicate_politicians.py [--dry-run] [--force]
"""

import sys
from pathlib import Path
from typing import Dict, List
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

# Mapping: new_id -> (old_id, politician_name)
# These are the duplicates we created that need to be cleaned up
DUPLICATE_MAPPING = {
    5514: (5411, "Joshua Gottheimer"),
    5493: (5417, "Bob Latta"),
    5494: (5439, "David Joyce"),
    5495: (5431, "Deborah Dingell"),
    5496: (5451, "Deborah Wasserman Schultz"),
    5497: (5467, "Garret Graves"),
    5498: (5452, "Gary Peters"),
    5499: (5448, "George Kelly"),
    5500: (5469, "Gerald Moran"),
    5501: (5407, "Gerry Connolly"),
    5502: (5412, "Gregory Landsman"),
    5503: (5440, "Gus Bilirakis"),
    5504: (5445, "James Hill"),
    5505: (5484, "James Scott"),
    5506: (5427, "Jamin Raskin"),
    5507: (5479, "Jennifer McClellan"),
    5508: (5471, "John Curtis"),
    5509: (5409, "John Hickenlooper"),
    5510: (5437, "John Knott"),
    5511: (5418, "John McGuire III"),
    5512: (5422, "John Neely Kennedy"),
    5513: (5406, "Jonathan Jackson"),
    5515: (5466, "Katherine Clark"),
    5516: (5443, "Laurel Lee"),
    5517: (5436, "Mark Green"),
    5518: (5430, "Neal Dunn"),
    5519: (5421, "Rick Allen"),
    5520: (5491, "Robert Aderholt"),
    5521: (5475, "Robert Wittman"),
    5522: (5438, "Ronald Wyden"),
    5523: (5442, "Stephen Cohen"),
    5524: (5457, "Stephen Lynch"),
    5525: (5413, "Suzan DelBene"),
    5526: (5428, "Suzanne Lee"),
    5527: (5423, "Thomas Suozzi"),
}

def cleanup_duplicates(dry_run: bool = True):
    """Clean up duplicate politicians and fix trades."""
    client = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("CLEANUP DUPLICATE POLITICIANS")
    print("="*70)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print()
    
    # Step 1: Verify original politicians exist
    print("Step 1: Verifying original politicians exist...")
    print("-" * 70)
    
    original_ids = [old_id for old_id, _ in DUPLICATE_MAPPING.values()]
    original_check = client.supabase.table('politicians')\
        .select('id, name')\
        .in_('id', original_ids[:10])\
        .execute()
    
    print(f"   Found {len(original_check.data)} of {len(set(original_ids))} original politicians")
    
    # Step 2: Update trades to use original IDs
    print("\nStep 2: Updating trades to use original IDs...")
    print("-" * 70)
    
    total_updated = 0
    for new_id, (old_id, name) in DUPLICATE_MAPPING.items():
        # Count trades using new_id
        count_result = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .eq('politician_id', new_id)\
            .execute()
        
        count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
        
        if count > 0:
            print(f"   {name}: {count} trades using new_id {new_id} -> updating to old_id {old_id}")
            
            if not dry_run:
                # Update trades
                try:
                    client.supabase.table('congress_trades')\
                        .update({'politician_id': old_id})\
                        .eq('politician_id', new_id)\
                        .execute()
                    total_updated += count
                    print(f"      [OK] Updated {count} trades")
                except Exception as e:
                    print(f"      [ERROR] Failed to update: {e}")
            else:
                print(f"      [DRY RUN] Would update {count} trades")
        else:
            print(f"   {name}: No trades using new_id {new_id}")
    
    if not dry_run:
        print(f"\n   [OK] Successfully updated {total_updated} trades")
    
    # Step 3: Delete duplicate politicians
    print("\nStep 3: Deleting duplicate politicians...")
    print("-" * 70)
    
    duplicate_ids = list(DUPLICATE_MAPPING.keys())
    print(f"   Will delete {len(duplicate_ids)} duplicate politicians")
    
    if not dry_run:
        # Delete in batches
        BATCH_SIZE = 10
        deleted = 0
        for i in range(0, len(duplicate_ids), BATCH_SIZE):
            batch = duplicate_ids[i:i+BATCH_SIZE]
            try:
                client.supabase.table('politicians')\
                    .delete()\
                    .in_('id', batch)\
                    .execute()
                deleted += len(batch)
                print(f"   Deleted batch {i//BATCH_SIZE + 1}: {len(batch)} politicians")
            except Exception as e:
                print(f"   [ERROR] Failed to delete batch: {e}")
        
        print(f"\n   [OK] Successfully deleted {deleted} duplicate politicians")
    else:
        print(f"   [DRY RUN] Would delete {len(duplicate_ids)} politicians")
        for new_id, (old_id, name) in list(DUPLICATE_MAPPING.items())[:5]:
            print(f"      - ID {new_id}: {name}")
        if len(DUPLICATE_MAPPING) > 5:
            print(f"      ... and {len(DUPLICATE_MAPPING) - 5} more")
    
    # Step 4: Validation
    print("\nStep 4: Validating cleanup...")
    print("-" * 70)
    
    if not dry_run:
        # Check duplicates are gone
        remaining = client.supabase.table('politicians')\
            .select('id')\
            .in_('id', duplicate_ids)\
            .execute()
        
        if remaining.data:
            print(f"   [WARNING] {len(remaining.data)} duplicates still exist")
        else:
            print(f"   [OK] All duplicates removed")
        
        # Check trades are using original IDs
        trades_check = client.supabase.table('congress_trades')\
            .select('id', count='exact')\
            .in_('politician_id', duplicate_ids)\
            .execute()
        
        remaining_trades = trades_check.count if hasattr(trades_check, 'count') else len(trades_check.data)
        
        if remaining_trades == 0:
            print(f"   [OK] No trades using duplicate IDs")
        else:
            print(f"   [WARNING] {remaining_trades} trades still using duplicate IDs")
    else:
        print("   [DRY RUN] Skipping validation")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Duplicates to remove: {len(DUPLICATE_MAPPING)}")
    print(f"Trades to update: {total_updated}")
    
    if dry_run:
        print("\n[INFO] This was a dry run. Use --force to apply changes.")
        print("[NEXT STEP] After cleanup, run: python web_dashboard/scripts/seed_committees.py")
    print("="*70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cleanup duplicate politicians')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Dry run mode (default)')
    parser.add_argument('--force', action='store_true', help='Actually apply changes')
    args = parser.parse_args()
    
    dry_run = not args.force
    
    if not dry_run:
        import sys
        if sys.stdin.isatty():
            response = input("\n⚠️  This will delete duplicate politicians and update trades. Continue? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                sys.exit(0)
        else:
            print("\n⚠️  Running in non-interactive mode - proceeding with cleanup...")
    
    cleanup_duplicates(dry_run=dry_run)


