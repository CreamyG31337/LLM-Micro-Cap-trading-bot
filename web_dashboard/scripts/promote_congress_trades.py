#!/usr/bin/env python3
"""
Promote Congress Trades from Staging to Production
==================================================

Reviews staged congress trades data and promotes approved records
to the production congress_trades table.

Usage:
    python web_dashboard/scripts/promote_congress_trades.py --batch-id <uuid>
    python web_dashboard/scripts/promote_congress_trades.py --all-approved
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
from datetime import datetime

def validate_batch(client: SupabaseClient, batch_id: str) -> Dict[str, Any]:
    """Validate a staging batch and return validation report"""
    
    print(f"\n🔍 Validating batch {batch_id}...")
    
    # Get all trades in batch
    result = client.supabase.table('congress_trades_staging')\
        .select('*')\
        .eq('import_batch_id', batch_id)\
        .execute()
    
    trades = result.data
    
    if not trades:
        return {'valid': False, 'error': f'No trades found for batch {batch_id}'}
    
    print(f"   Found {len(trades)} trades in batch\n")
    
    issues = []
    warnings = []
    
    # Check 1: Missing required metadata
    missing_party = [t for t in trades if not t.get('party')]
    missing_state = [t for t in trades if not t.get('state')]
    missing_owner = [t for t in trades if not t.get('owner')]
    
    if missing_party:
        issues.append(f"❌ {len(missing_party)} records missing 'party' field")
    if missing_state:
        issues.append(f"❌ {len(missing_state)} records missing 'state' field")
    if missing_owner:
        warnings.append(f"⚠️  {len(missing_owner)} records missing 'owner' field (will default to 'Not-Disclosed')")
    
    # Check 2: Duplicates within batch
    groups = defaultdict(list)
    for trade in trades:
        key = (
            trade['politician'],
            trade['ticker'],
            str(trade['transaction_date']),
            trade['type'],
            trade['amount'],
            trade.get('owner') or 'Not-Disclosed'
        )
        groups[key].append(trade['id'])
    
    duplicates_in_batch = {k: v for k, v in groups.items() if len(v) > 1}
    if duplicates_in_batch:
        issues.append(f"❌ {len(duplicates_in_batch)} duplicate groups within batch")
        # Show examples
        for i, (key, ids) in enumerate(list(duplicates_in_batch.items())[:3]):
            issues.append(f"   Example: {key[0]} | {key[1]} | {key[2]} - IDs: {ids}")
    
    # Check 3: Duplicates with production
    prod_result = client.supabase.table('congress_trades')\
        .select('politician,ticker,transaction_date,type,amount,owner')\
        .execute()
    
    prod_keys = set()
    for t in prod_result.data:
        key = (
            t['politician'],
            t['ticker'],
            str(t['transaction_date']),
            t['type'],
            t['amount'],
            t.get('owner') or 'Not-Disclosed'
        )
        prod_keys.add(key)
    
    duplicates_with_prod = []
    for trade in trades:
        key = (
            trade['politician'],
            trade['ticker'],
            str(trade['transaction_date']),
            trade['type'],
            trade['amount'],
            trade.get('owner') or 'Not-Disclosed'
        )
        if key in prod_keys:
            duplicates_with_prod.append(trade)
    
    if duplicates_with_prod:
        warnings.append(f"⚠️  {len(duplicates_with_prod)} trades already exist in production (will skip)")
    
    # Print report
    if issues:
        print("   ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    if warnings:
        print("   WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
        print()
    
    if not issues and not warnings:
        print("   ✅ No issues found! Batch is ready for promotion.\n")
    
    return {
        'valid': len(issues) == 0,
        'total_trades': len(trades),
        'issues': issues,
        'warnings': warnings,
        'duplicate_with_prod_count': len(duplicates_with_prod),
        'duplicate_with_prod_ids': [t['id'] for t in duplicates_with_prod]
    }


def promote_batch(client: SupabaseClient, batch_id: str, skip_duplicates: bool = True) -> bool:
    """Promote a batch from staging to production"""
    
    print(f"\n🚀 Promoting batch {batch_id} to production...\n")
    
    # Get approved trades from staging
    result = client.supabase.table('congress_trades_staging')\
        .select('*')\
        .eq('import_batch_id', batch_id)\
        .eq('promoted_to_production', False)\
        .execute()
    
    trades = result.data
    
    if not trades:
        print("   ⚠️  No unpromoted trades found in this batch")
        return False
    
    # Get existing production records to check for duplicates
    if skip_duplicates:
        prod_result = client.supabase.table('congress_trades')\
            .select('politician,ticker,transaction_date,type,amount,owner')\
            .execute()
        
        prod_keys = set()
        for t in prod_result.data:
            key = (
                t['politician'],
                t['ticker'],
                str(t['transaction_date']),
                t['type'],
                t['amount'],
                t.get('owner') or 'Not-Disclosed'
            )
            prod_keys.add(key)
    
    # Prepare records for production
    to_insert = []
    skipped_duplicates = []
    
    for trade in trades:
        # Check if duplicate with production
        if skip_duplicates:
            key = (
                trade['politician'],
                trade['ticker'],
                str(trade['transaction_date']),
                trade['type'],
                trade['amount'],
                trade.get('owner') or 'Not-Disclosed'
            )
            if key in prod_keys:
                skipped_duplicates.append(trade['id'])
                continue
        
        # Remove staging-specific fields
        prod_trade = {
            'ticker': trade['ticker'],
            'politician': trade['politician'],
            'chamber': trade['chamber'],
            'transaction_date': trade['transaction_date'],
            'disclosure_date': trade['disclosure_date'],
            'type': trade['type'],
            'amount': trade['amount'],
            'price': trade.get('price'),
            'asset_type': trade.get('asset_type'),
            'party': trade['party'],
            'state': trade['state'],
            'owner': trade.get('owner') or 'Not-Disclosed',  # Default if NULL
            'conflict_score': trade.get('conflict_score'),
            'notes': trade.get('notes')
        }
        to_insert.append((trade['id'], prod_trade))
    
    if skipped_duplicates:
        print(f"   ⏭️  Skipping {len(skipped_duplicates)} duplicates that already exist in production")
    
    if not to_insert:
        print("   ⚠️  No new trades to promote (all are duplicates)")
        return False
    
    print(f"   📝 Promoting {len(to_insert)} trades to production...")
    
    # Insert to production in batches
    BATCH_SIZE = 100
    inserted_count = 0
    
    for i in range(0, len(to_insert), BATCH_SIZE):
        batch = [t[1] for t in to_insert[i:i+BATCH_SIZE]]
        try:
            client.supabase.table('congress_trades')\
                .insert(batch)\
                .execute()
            inserted_count += len(batch)
            print(f"   ✓ Batch {i//BATCH_SIZE + 1}/{(len(to_insert) + BATCH_SIZE - 1)//BATCH_SIZE} inserted")
        except Exception as e:
            print(f"   ❌ Error inserting batch: {e}")
            return False
    
    # Mark staging records as promoted
    all_staging_ids = [t[0] for t in to_insert] + skipped_duplicates
    
    if all_staging_ids:
        try:
            client.supabase.table('congress_trades_staging')\
                .update({
                    'promoted_to_production': True,
                    'promoted_at': datetime.now().isoformat()
                })\
                .in_('id', all_staging_ids)\
                .execute()
            print(f"   ✓ Marked {len(all_staging_ids)} staging records as promoted")
        except Exception as e:
            print(f"   ⚠️  Error marking staging records: {e}")
    
    print(f"\n   ✅ Successfully promoted {inserted_count} trades to production!")
    print(f"   📊 Total in batch: {len(trades)}")
    print(f"   ✅ Inserted: {inserted_count}")
    print(f"   ⏭️  Skipped (duplicates): {len(skipped_duplicates)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Promote congress trades from staging to production')
    parser.add_argument('--batch-id', type=str, help='Batch ID to promote')
    parser.add_argument('--validate-only', action='store_true', help='Only validate, do not promote')
    parser.add_argument('--skip-validation', action='store_true', help='Skip validation and promote directly')
    parser.add_argument('--allow-duplicates', action='store_true', help='Allow duplicates with production')
    
    args = parser.parse_args()
    
    if not args.batch_id:
        print("❌ Error: --batch-id is required")
        print("\nUsage: python promote_congress_trades.py --batch-id <uuid>")
        sys.exit(1)
    
    # Validate batch_id is a UUID
    try:
        uuid.UUID(args.batch_id)
    except ValueError:
        print(f"❌ Error: Invalid batch ID format: {args.batch_id}")
        sys.exit(1)
    
    # Initialize Supabase client
    try:
        client = SupabaseClient(use_service_role=True)
        print("✅ Connected to Supabase\n")
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        sys.exit(1)
    
    # Validate batch
    if not args.skip_validation:
        validation = validate_batch(client, args.batch_id)
        
        if not validation['valid']:
            print(f"❌ Validation failed: {validation.get('error', 'Unknown error')}")
            sys.exit(1)
        
        if validation['issues']:
            print("❌ Batch has validation issues. Fix these before promoting.")
            sys.exit(1)
        
        if args.validate_only:
            print("✅ Validation complete (--validate-only mode, not promoting)")
            sys.exit(0)
    
    # Promote batch
    skip_duplicates = not args.allow_duplicates
    success = promote_batch(client, args.batch_id, skip_duplicates=skip_duplicates)
    
    if success:
        print("\n" + "="*70)
        print("✅ PROMOTION COMPLETE")
        print("="*70)
        sys.exit(0)
    else:
        print("\n❌ Promotion failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
