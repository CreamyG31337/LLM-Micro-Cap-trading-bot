#!/usr/bin/env python3
"""
Safe Migration: Staging → Production (Preserving AI Analysis)
==============================================================

SAFE migration that preserves existing trade IDs to maintain AI analysis integrity.

Strategy:
1. For existing trades (matched by business key): UPDATE with new data, KEEP same ID
2. For new trades: INSERT with auto-generated IDs
3. AI analysis foreign keys remain valid

This is the CORRECT way to migrate without losing AI analysis.

Usage:
    python safe_migrate_staging_to_production.py
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
from datetime import datetime

def safe_migration(fix_angus_king: bool = True, dry_run: bool = False):
    """Safe migration preserving AI analysis"""
    
    supabase = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("SAFE MIGRATION: STAGING → PRODUCTION")
    print("="*70)
    print("Strategy: UPDATE existing, INSERT new (preserves AI analysis)\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Get ALL staging data (paginate)
    print("📥 Fetching staging records...")
    all_staging_trades = []
    offset = 0
    BATCH_SIZE = 1000
    
    while True:
        batch_result = supabase.supabase.table('congress_trades_staging')\
            .select('*')\
            .range(offset, offset + BATCH_SIZE - 1)\
            .execute()
        
        if not batch_result.data:
            break
        
        all_staging_trades.extend(batch_result.data)
        offset += BATCH_SIZE
        
        if len(batch_result.data) < BATCH_SIZE:
            break
    
    print(f"   Fetched {len(all_staging_trades)} staging trades")
    
    # Fix Angus King
    if fix_angus_king:
        for trade in all_staging_trades:
            if trade['politician'] == 'Angus King' and not trade.get('party'):
                trade['party'] = 'Independent'
    
    # Clean duplicates from staging
    print("\n🧹 Cleaning duplicates...")
    groups = defaultdict(list)
    for trade in all_staging_trades:
        key = (
            trade['politician'], trade['ticker'], 
            str(trade['transaction_date']), trade['type'], 
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        groups[key].append(trade)
    
    staging_clean = []
    for key, trade_list in groups.items():
        sorted_trades = sorted(trade_list, key=lambda x: x['id'])
        staging_clean.append(sorted_trades[0])
    
    print(f"   Clean staging: {len(staging_clean)} trades")
    
    # Get ALL production data (paginate)
    print("\n📥 Fetching production records...")
    all_prod_trades = []
    offset = 0
    
    while True:
        batch_result = supabase.supabase.table('congress_trades')\
            .select('*')\
            .range(offset, offset + BATCH_SIZE - 1)\
            .execute()
        
        if not batch_result.data:
            break
        
        all_prod_trades.extend(batch_result.data)
        offset += BATCH_SIZE
        
        if len(batch_result.data) < BATCH_SIZE:
            break
    
    print(f"   Fetched {len(all_prod_trades)} production trades")
    
    # Build production index by business key
    print("\n🗺️  Building ID mapping...")
    prod_by_key = {}
    for trade in all_prod_trades:
        key = (
            trade['politician'], trade['ticker'],
            str(trade['transaction_date']), trade['type'],
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        prod_by_key[key] = trade['id']
    
    # Categorize staging trades
    to_update = []  # Existing trades - UPDATE with same ID
    to_insert = []  # New trades - INSERT with new ID
    
    for trade in staging_clean:
        key = (
            trade['politician'], trade['ticker'],
            str(trade['transaction_date']), trade['type'],
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        
        if key in prod_by_key:
            # Existing trade - UPDATE (preserves ID and AI analysis)
            to_update.append((prod_by_key[key], trade))
        else:
            # New trade - INSERT
            to_insert.append(trade)
    
    print(f"   To UPDATE (existing): {len(to_update)}")
    print(f"   To INSERT (new): {len(to_insert)}")
    
    # Confirm
    print(f"\n" + "="*70)
    print(f"READY TO MIGRATE:")
    print(f"  Updates: {len(to_update)} (preserves IDs & AI analysis)")
    print(f"  Inserts: {len(to_insert)} (new trades)")
    print(f"  Total production after: {len(to_update) + len(to_insert)}")
    print("="*70)
    
    if dry_run:
        print("\n✅ DRY RUN COMPLETE - No changes made")
        return
    
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Update existing trades (preserves IDs)
    print(f"\n🔄 Updating {len(to_update)} existing trades...")
    updated = 0
    
    for prod_id, staging_trade in to_update:
        try:
            update_data = {
                'ticker': staging_trade['ticker'],
                'politician': staging_trade['politician'],
                'chamber': staging_trade['chamber'],
                'transaction_date': staging_trade['transaction_date'],
                'disclosure_date': staging_trade['disclosure_date'],
                'type': staging_trade['type'],
                'amount': staging_trade['amount'],
                'price': staging_trade.get('price'),
                'asset_type': staging_trade.get('asset_type'),
                'party': staging_trade['party'],
                'state': staging_trade['state'],
                'owner': staging_trade.get('owner') or 'Not-Disclosed',
                'notes': staging_trade.get('notes')
            }
            
            supabase.supabase.table('congress_trades')\
                .update(update_data)\
                .eq('id', prod_id)\
                .execute()
            
            updated += 1
            if updated % 1000 == 0:
                print(f"   ✓ Updated {updated}/{len(to_update)}...")
        except Exception as e:
            print(f"   ⚠️  Error updating ID {prod_id}: {e}")
    
    print(f"   ✅ Updated {updated} trades")
    
    # Insert new trades
    print(f"\n📥 Inserting {len(to_insert)} new trades...")
    
    to_insert_data = []
    for trade in to_insert:
        to_insert_data.append({
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
            'owner': trade.get('owner') or 'Not-Disclosed',
            'notes': trade.get('notes')
        })
    
    # Insert in batches
    BATCH_SIZE = 100
    inserted = 0
    
    for i in range(0, len(to_insert_data), BATCH_SIZE):
        batch = to_insert_data[i:i+BATCH_SIZE]
        try:
            supabase.supabase.table('congress_trades').insert(batch).execute()
            inserted += len(batch)
            if (i // BATCH_SIZE) % 10 == 0:
                print(f"   ✓ Inserted {inserted}/{len(to_insert_data)}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"   ✅ Inserted {inserted} new trades")
    
    # Get final count
    final_result = supabase.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .execute()
    
    print(f"\n" + "="*70)
    print(f"✅ SAFE MIGRATION COMPLETE!")
    print(f"   Production now has {final_result.count} trades")
    print(f"   Updated: {updated} (AI analysis preserved)")
    print(f"   Inserted: {inserted} (new trades)")
    print(f"   ✅ All AI analysis foreign keys remain valid")
    print("="*70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-fix-angus', action='store_true',
                        help="Don't fix Angus King party")
    parser.add_argument('--dry-run', action='store_true',
                        help="Show what would be done without making changes")
    
    args = parser.parse_args()
    safe_migration(
        fix_angus_king=not args.no_fix_angus,
        dry_run=args.dry_run
    )
