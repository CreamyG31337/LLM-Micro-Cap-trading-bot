#!/usr/bin/env python3
"""
Backfill Politician IDs
=======================

Populates the politician_id column for existing congress_trades records
based on the politician name field.

This should be run AFTER:
1. Schema migration 25_add_politician_fk_to_trades.sql
2. Sync script to ensure all politicians exist in politicians table

Usage:
    python scripts/backfill_politician_ids.py [--dry-run] [--batch-size 100]
"""

import sys
from pathlib import Path
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from supabase_client import SupabaseClient
from utils.politician_mapping import resolve_politician_name, get_or_create_politician

def backfill_politician_ids(dry_run: bool = True, batch_size: int = 100):
    """
    Backfill politician_id for all trades based on politician name.
    
    Args:
        dry_run: If True, only report what would be done
        batch_size: Number of records to process per batch
    """
    client = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("BACKFILL POLITICIAN IDs TO CONGRESS_TRADES")
    print("="*70)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"Batch Size: {batch_size}")
    print()
    
    # Process in chunks until done
    while True:
        # Get next batch of trades without politician_id
        # We fetch ALL columns so we can safely upsert (replace) the row with the new ID
        print("📥 Fetching next batch of trades without politician_id...")
        response = client.supabase.table('congress_trades')\
            .select('*')\
            .is_('politician_id', 'null')\
            .limit(1000)\
            .execute()
        
        trades = response.data
        count = len(trades)
        print(f"   Found {count} trades needing backfill in this chunk")
        
        if count == 0:
            print("✅ All trades have politician_id!")
            break
            
        # Process this chunk
        updates_batch = []
        failed = []
        politician_cache = {}
        
        for trade in trades:
            trade_to_update = trade.copy() # Key copy
            
            politician_name = trade['politician']
            party = trade.get('party')
            state = trade.get('state')
            chamber = trade.get('chamber')
            
            # Check cache first
            canonical_name, _ = resolve_politician_name(politician_name)
            
            if canonical_name in politician_cache:
                politician_id = politician_cache[canonical_name]
            else:
                # Look up or create politician
                politician_id = get_or_create_politician(
                    client,
                    politician_name,
                    party=party,
                    state=state,
                    chamber=chamber,
                    create_if_missing=not dry_run
                )
                
                if politician_id:
                    politician_cache[canonical_name] = politician_id
            
            if politician_id:
                # Update the object
                trade_to_update['politician_id'] = politician_id
                updates_batch.append(trade_to_update)
            else:
                failed.append({
                    'trade_id': trade['id'],
                    'politician': politician_name,
                    'reason': 'Politician not found'
                })
        
        # Perform Bulk Upsert
        if updates_batch and not dry_run:
            print(f"   🔄 Bulk upserting {len(updates_batch)} trades...")
            try:
                # Upsert relies on Primary Key (id) to update existing rows
                client.supabase.table('congress_trades').upsert(updates_batch).execute()
                print(f"   ✅ Successfully updated chunk of {len(updates_batch)} trades")
            except Exception as e:
                print(f"   ❌ Error batch upserting: {e}")
                # Fallback to slow loop? Or just break?
                # For now, let's break to analyze
                break
        
        if failed:
             print(f"   ⚠️  {len(failed)} trades failed mapping in this chunk.")
             if len(failed) == count:
                 print("   ❌ All trades failed. Breaking.")
                 break
    
    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print("✅ Backfill complete!")
    
    print("="*70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill politician IDs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--batch-size', type=int, default=100, help='Number of records to process per batch')
    args = parser.parse_args()
    
    backfill_politician_ids(dry_run=args.dry_run, batch_size=args.batch_size)
