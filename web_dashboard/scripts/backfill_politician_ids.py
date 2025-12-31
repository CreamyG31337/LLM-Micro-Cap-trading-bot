#!/usr/bin/env python3
"""
Backfill Politician IDs (FIXED VERSION)
========================================

Populates the politician_id column for existing congress_trades records
based on the politician name field.

IMPORTANT FIXES:
- Validates politician_id exists before setting it
- Does NOT create politicians automatically (use sync_missing_politicians.py first)
- Validates all IDs before bulk upsert
- Handles invalid IDs gracefully

This should be run AFTER:
1. Schema migration 25_add_politician_fk_to_trades.sql
2. sync_missing_politicians.py to ensure all politicians exist in politicians table

Usage:
    python scripts/backfill_politician_ids.py [--dry-run] [--batch-size 100]
"""

import sys
from pathlib import Path
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

from supabase_client import SupabaseClient
from utils.politician_mapping import resolve_politician_name

def validate_politician_id(client: SupabaseClient, politician_id: int) -> bool:
    """Validate that a politician_id actually exists in the database."""
    try:
        result = client.supabase.table('politicians')\
            .select('id')\
            .eq('id', politician_id)\
            .limit(1)\
            .execute()
        return bool(result.data)
    except Exception:
        return False

def get_politician_id(client: SupabaseClient, politician_name: str) -> int | None:
    """
    Get politician ID from database by name.
    Does NOT create politicians - they must already exist.
    
    Returns:
        Politician ID if found, None otherwise
    """
    # Resolve to canonical name
    canonical_name, bioguide_id = resolve_politician_name(politician_name)
    
    # Look up by canonical name
    result = client.supabase.table('politicians')\
        .select('id')\
        .eq('name', canonical_name)\
        .limit(1)\
        .execute()
    
    if result.data:
        politician_id = result.data[0]['id']
        # Validate the ID exists (double-check)
        if validate_politician_id(client, politician_id):
            return politician_id
    
    # Try looking up by Bioguide ID if we have one (in case name varies)
    if bioguide_id:
        result = client.supabase.table('politicians')\
            .select('id')\
            .eq('bioguide_id', bioguide_id)\
            .limit(1)\
            .execute()
        
        if result.data:
            politician_id = result.data[0]['id']
            # Validate the ID exists (double-check)
            if validate_politician_id(client, politician_id):
                return politician_id
    
    # Not found - return None (don't create)
    return None

def backfill_politician_ids(dry_run: bool = True, batch_size: int = 100):
    """
    Backfill politician_id for all trades based on politician name.
    
    FIXED VERSION: Validates all IDs before setting them.
    
    Args:
        dry_run: If True, only report what would be done
        batch_size: Number of records to process per batch (not used for upsert, but for reporting)
    """
    client = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("BACKFILL POLITICIAN IDs TO CONGRESS_TRADES (FIXED VERSION)")
    print("="*70)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Batch Size: {batch_size}")
    print()
    print("[IMPORTANT] This script does NOT create politicians.")
    print("            Run sync_missing_politicians.py first to ensure all politicians exist.")
    print()
    
    total_processed = 0
    total_updated = 0
    total_failed = 0
    total_skipped_invalid = 0
    
    # Process in chunks until done
    while True:
        # Get next batch of trades without politician_id
        print("[INFO] Fetching next batch of trades without politician_id...")
        response = client.supabase.table('congress_trades')\
            .select('*')\
            .is_('politician_id', 'null')\
            .limit(1000)\
            .execute()
        
        trades = response.data
        count = len(trades)
        print(f"   Found {count} trades needing backfill in this chunk")
        
        if count == 0:
            print("[OK] All trades have politician_id!")
            break
        
        # Process this chunk
        updates_batch = []
        failed = []
        politician_cache = {}
        
        for trade in trades:
            total_processed += 1
            trade_to_update = trade.copy()  # Deep copy
            
            politician_name = trade['politician']
            party = trade.get('party')
            state = trade.get('state')
            chamber = trade.get('chamber')
            
            # Check cache first
            canonical_name, _ = resolve_politician_name(politician_name)
            
            if canonical_name in politician_cache:
                politician_id = politician_cache[canonical_name]
            else:
                # Look up politician (does NOT create)
                politician_id = get_politician_id(client, politician_name)
                
                if politician_id:
                    # Validate ID exists before caching
                    if validate_politician_id(client, politician_id):
                        politician_cache[canonical_name] = politician_id
                    else:
                        print(f"   [WARNING] Politician ID {politician_id} for '{canonical_name}' does not exist - skipping")
                        politician_id = None
            
            if politician_id:
                # Validate one more time before adding to batch
                if validate_politician_id(client, politician_id):
                    trade_to_update['politician_id'] = politician_id
                    updates_batch.append(trade_to_update)
                else:
                    total_skipped_invalid += 1
                    failed.append({
                        'trade_id': trade['id'],
                        'politician': politician_name,
                        'reason': f'Politician ID {politician_id} validation failed'
                    })
            else:
                total_failed += 1
                failed.append({
                    'trade_id': trade['id'],
                    'politician': politician_name,
                    'reason': 'Politician not found in database (run sync_missing_politicians.py first)'
                })
        
        # Validate all politician_ids in batch before upsert
        if updates_batch:
            print(f"   [INFO] Validating {len(updates_batch)} politician_ids before update...")
            politician_ids_to_validate = {t['politician_id'] for t in updates_batch if t.get('politician_id')}
            
            if politician_ids_to_validate:
                # Check all IDs exist
                validation_result = client.supabase.table('politicians')\
                    .select('id')\
                    .in_('id', list(politician_ids_to_validate))\
                    .execute()
                
                valid_ids = {p['id'] for p in validation_result.data}
                invalid_trades = [t for t in updates_batch if t.get('politician_id') not in valid_ids]
                
                if invalid_trades:
                    print(f"   [WARNING] {len(invalid_trades)} trades have invalid politician_id - removing from batch")
                    updates_batch = [t for t in updates_batch if t.get('politician_id') in valid_ids]
                    total_skipped_invalid += len(invalid_trades)
        
        # Perform Bulk Upsert
        if updates_batch and not dry_run:
            print(f"   [INFO] Bulk upserting {len(updates_batch)} trades...")
            try:
                # Upsert relies on Primary Key (id) to update existing rows
                client.supabase.table('congress_trades').upsert(updates_batch).execute()
                print(f"   [OK] Successfully updated chunk of {len(updates_batch)} trades")
                total_updated += len(updates_batch)
            except Exception as e:
                print(f"   [ERROR] Error batch upserting: {e}")
                # Don't break - continue with next batch
                # But log the error
                import traceback
                traceback.print_exc()
        elif updates_batch and dry_run:
            print(f"   [DRY RUN] Would update {len(updates_batch)} trades")
            total_updated += len(updates_batch)
        
        if failed:
            print(f"   [WARNING] {len(failed)} trades failed mapping in this chunk.")
            if len(failed) <= 10:
                for f in failed:
                    print(f"      - Trade {f['trade_id']}: {f['politician']} - {f['reason']}")
            else:
                for f in failed[:5]:
                    print(f"      - Trade {f['trade_id']}: {f['politician']} - {f['reason']}")
                print(f"      ... and {len(failed) - 5} more")
            
            if len(failed) == count:
                print("   [WARNING] All trades failed. Breaking.")
                break
    
    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total processed: {total_processed}")
    print(f"Total updated: {total_updated}")
    print(f"Total failed: {total_failed}")
    print(f"Total skipped (invalid IDs): {total_skipped_invalid}")
    
    if total_failed > 0:
        print()
        print("[ACTION REQUIRED] Some politicians are missing from database.")
        print("                 Run: python web_dashboard/scripts/sync_missing_politicians.py")
    
    print("="*70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill politician IDs (fixed version)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of records to process per batch')
    args = parser.parse_args()
    
    backfill_politician_ids(dry_run=args.dry_run, batch_size=args.batch_size)

