#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Missing Party Information for Angus King
============================================

Updates the party field to 'Independent' for Angus King trades
that are missing party information in the staging table.

Usage:
    python fix_angus_king_party.py <batch-id>
    python fix_angus_king_party.py --latest
    python fix_angus_king_party.py --dry-run  # Preview changes without applying
"""

import sys
import argparse
import io
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient


def fix_angus_king_party(client: SupabaseClient, batch_id: str, dry_run: bool = False) -> dict:
    """Fix missing party information for Angus King trades"""
    
    print(f"{'[DRY RUN] ' if dry_run else ''}Fixing Angus King party information...")
    print(f"Batch ID: {batch_id}\n")
    
    # First, find all Angus King trades with missing party
    result = client.supabase.table('congress_trades_staging')\
        .select('id, politician, ticker, transaction_date, party, state, chamber')\
        .eq('import_batch_id', batch_id)\
        .eq('politician', 'Angus King')\
        .is_('party', 'null')\
        .execute()
    
    if not result.data:
        print("✅ No Angus King trades with missing party found.")
        return {'updated': 0, 'found': 0}
    
    trades_to_fix = result.data
    print(f"Found {len(trades_to_fix)} Angus King trades with missing party information:\n")
    
    # Show what we'll update
    for i, trade in enumerate(trades_to_fix[:10], 1):
        print(f"  {i}. ID {trade['id']}: {trade['ticker']} | {trade['transaction_date']} | State: {trade.get('state', 'N/A')} | Chamber: {trade.get('chamber', 'N/A')}")
    
    if len(trades_to_fix) > 10:
        print(f"  ... and {len(trades_to_fix) - 10} more")
    
    if dry_run:
        print(f"\n[DRY RUN] Would update {len(trades_to_fix)} records to set party='Independent'")
        return {'updated': 0, 'found': len(trades_to_fix), 'dry_run': True}
    
    # Update all records
    print(f"\nUpdating {len(trades_to_fix)} records...")
    
    updated_count = 0
    failed_count = 0
    
    # Update in batches (Supabase might have limits)
    batch_size = 100
    for i in range(0, len(trades_to_fix), batch_size):
        batch = trades_to_fix[i:i + batch_size]
        record_ids = [trade['id'] for trade in batch]
        
        try:
            # Update all records in this batch
            update_result = client.supabase.table('congress_trades_staging')\
                .update({'party': 'Independent'})\
                .in_('id', record_ids)\
                .execute()
            
            if update_result.data:
                updated_count += len(update_result.data)
                print(f"  Updated batch {i//batch_size + 1}: {len(update_result.data)} records")
            else:
                failed_count += len(batch)
                print(f"  ⚠️  Batch {i//batch_size + 1}: No records updated (may already be updated)")
        
        except Exception as e:
            print(f"  ❌ Error updating batch {i//batch_size + 1}: {e}")
            failed_count += len(batch)
    
    print(f"\n{'='*60}")
    print(f"Update Summary:")
    print(f"  Found: {len(trades_to_fix)} records")
    print(f"  Updated: {updated_count} records")
    if failed_count > 0:
        print(f"  Failed: {failed_count} records")
    print(f"{'='*60}\n")
    
    # Verify the fix
    print("Verifying fix...")
    verify_result = client.supabase.table('congress_trades_staging')\
        .select('id, party')\
        .eq('import_batch_id', batch_id)\
        .eq('politician', 'Angus King')\
        .is_('party', 'null')\
        .execute()
    
    if verify_result.data and len(verify_result.data) > 0:
        print(f"⚠️  Warning: {len(verify_result.data)} records still have NULL party")
        print("   This might indicate the update didn't work. Check the records manually.")
    else:
        print("✅ Verification passed: All Angus King trades now have party='Independent'")
    
    return {
        'updated': updated_count,
        'found': len(trades_to_fix),
        'failed': failed_count
    }


def main():
    parser = argparse.ArgumentParser(description='Fix missing party information for Angus King')
    parser.add_argument('batch_id', nargs='?', help='Batch ID to fix')
    parser.add_argument('--latest', action='store_true', help='Fix in most recent batch')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    
    args = parser.parse_args()
    
    client = SupabaseClient(use_service_role=True)
    
    # Get batch ID
    if args.latest:
        # Get latest batch
        result = client.supabase.table('congress_trades_staging')\
            .select('import_batch_id')\
            .order('import_timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        if not result.data:
            print("❌ No batches found in staging")
            return
        
        batch_id = result.data[0]['import_batch_id']
        print(f"Using latest batch: {batch_id}\n")
    elif args.batch_id:
        batch_id = args.batch_id
    else:
        print("Error: Must provide batch_id or --latest")
        parser.print_help()
        sys.exit(1)
    
    # Fix the issue
    result = fix_angus_king_party(client, batch_id, dry_run=args.dry_run)
    
    if args.dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply changes.")
    elif result['updated'] > 0:
        print("\n✅ Successfully fixed Angus King party information!")


if __name__ == '__main__':
    main()

