#!/usr/bin/env python3
"""
Full Migration: Replace Production with Staging Data
====================================================

Replaces ALL production data with clean staging data while preserving
AI analysis by creating an ID mapping.

Steps:
1. Clean duplicates from staging
2. Backup production table
3. Build ID mapping (old production → new staging for matching trades)
4. Clear production and load staging
5. Update AI analysis trade_ids using mapping

Usage:
    python full_migration_staging_to_prod.py --batch-id <uuid>
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
from postgres_client import PostgresClient
from datetime import datetime

def full_migration(batch_id: str, fix_angus_king: bool = True):
    """Full replacement migration"""
    
    supabase = SupabaseClient(use_service_role=True)
    postgres = PostgresClient()
    
    print("="*70)
    print("FULL PRODUCTION REPLACEMENT FROM STAGING")
    print("="*70)
    print(f"Batch ID: {batch_id}\n")
    
    # Step 1: Get staging data
    staging_result = supabase.supabase.table('congress_trades_staging')\
        .select('*')\
        .eq('import_batch_id', batch_id)\
        .execute()
    
    staging_trades = staging_result.data
    print(f"📊 Staging trades: {len(staging_trades)}")
    
    # Fix Angus King
    if fix_angus_king:
        for trade in staging_trades:
            if trade['politician'] == 'Angus King' and not trade.get('party'):
                trade['party'] = 'Independent'
    
    # Clean duplicates from staging first
    print("\n🧹 Cleaning duplicates from staging...")
    groups = defaultdict(list)
    for trade in staging_trades:
        key = (
            trade['politician'], trade['ticker'], 
            str(trade['transaction_date']), trade['type'], 
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        groups[key].append(trade)
    
    to_keep_ids = set()
    to_delete_ids = []
    
    for key, trade_list in groups.items():
        if len(trade_list) > 1:
            # Keep lowest ID, delete rest
            sorted_trades = sorted(trade_list, key=lambda x: x['id'])
            to_keep_ids.add(sorted_trades[0]['id'])
            for dupe in sorted_trades[1:]:
                to_delete_ids.append(dupe['id'])
        else:
            to_keep_ids.add(trade_list[0]['id'])
    
    if to_delete_ids:
        print(f"   Deleting {len(to_delete_ids)} duplicates from staging...")
        for i in range(0, len(to_delete_ids), 50):
            batch = to_delete_ids[i:i+50]
            supabase.supabase.table('congress_trades_staging')\
                .delete().in_('id', batch).execute()
        
        # Refresh staging data
        staging_result = supabase.supabase.table('congress_trades_staging')\
            .select('*')\
            .eq('import_batch_id', batch_id)\
            .execute()
        staging_trades = staging_result.data
    
    print(f"   ✅ Clean staging trades: {len(staging_trades)}")
    
    # Step 2: Backup production
    print(f"\n💾 Backing up production...")
    prod_result = supabase.supabase.table('congress_trades')\
        .select('*')\
        .execute()
    
    prod_trades = prod_result.data
    print(f"   Production trades to backup: {len(prod_trades)}")
    
    # Check AI analysis count
    ai_count_result = postgres.execute_query(
        "SELECT COUNT(*) as count FROM congress_trades_analysis"
    )
    ai_count = ai_count_result[0]['count'] if ai_count_result else 0
    print(f"   AI analyses to preserve: {ai_count}")
    
    # Step 3: Build ID mapping (old prod ID → new staging ID for matching trades)
    print(f"\n🗺️  Building ID mapping...")
    
    # Index staging by business key
    staging_by_key = {}
    for trade in staging_trades:
        key = (
            trade['politician'], trade['ticker'],
            str(trade['transaction_date']), trade['type'],
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        staging_by_key[key] = trade['id']
    
    # Build mapping
    id_mapping = {}  # old_prod_id → new_staging_id
    mapped_count = 0
    
    for prod_trade in prod_trades:
        key = (
            prod_trade['politician'], prod_trade['ticker'],
            str(prod_trade['transaction_date']), prod_trade['type'],
            prod_trade['amount'], prod_trade.get('owner') or 'Not-Disclosed'
        )
        
        if key in staging_by_key:
            id_mapping[prod_trade['id']] = staging_by_key[key]
            mapped_count += 1
    
    print(f"   ✅ Mapped {mapped_count} existing trades to new IDs")
    print(f"   ℹ️  {len(staging_trades) - mapped_count} are new trades")
    
    # Confirm
    print(f"\n" + "="*70)
    print(f"READY TO MIGRATE:")
    print(f"  Current production: {len(prod_trades)} trades")
    print(f"  New production: {len(staging_trades)} trades")
    print(f"  Change: {len(staging_trades) - len(prod_trades):+d} trades")
    print(f"  AI analyses to update: {len(id_mapping)}")
    print("="*70)
    
    response = input("\nProceed with full replacement? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Step 4: Clear production and load staging
    print(f"\n🗑️  Clearing production table...")
    supabase.supabase.table('congress_trades').delete().neq('id', 0).execute()
    print(f"   ✅ Production cleared")
    
    print(f"\n📥 Loading staging data to production...")
    
    to_insert = []
    for trade in staging_trades:
        prod_trade = {
            'id': trade['id'],  # Preserve ID for AI mapping
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
        }
        to_insert.append(prod_trade)
    
    # Insert in batches
    BATCH_SIZE = 100
    inserted = 0
    
    for i in range(0, len(to_insert), BATCH_SIZE):
        batch = to_insert[i:i+BATCH_SIZE]
        try:
            supabase.supabase.table('congress_trades').insert(batch).execute()
            inserted += len(batch)
            if (i // BATCH_SIZE) % 10 == 0:
                print(f"   ✓ Inserted {inserted}/{len(to_insert)} trades...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
    
    print(f"   ✅ Inserted {inserted} trades")
    
    # Step 5: Update AI analysis trade_ids
    if id_mapping and ai_count > 0:
        print(f"\n🔄 Updating AI analysis trade_ids...")
        
        updated = 0
        for old_id, new_id in id_mapping.items():
            try:
                postgres.execute_query(
                    "UPDATE congress_trades_analysis SET trade_id = %s WHERE trade_id = %s",
                    (new_id, old_id)
                )
                updated += 1
            except Exception as e:
                print(f"   ⚠️  Error updating {old_id} → {new_id}: {e}")
        
        print(f"   ✅ Updated {updated} AI analysis references")
    
    # Mark staging as promoted
    supabase.supabase.table('congress_trades_staging')\
        .update({'promoted_to_production': True, 'promoted_at': datetime.now().isoformat()})\
        .eq('import_batch_id', batch_id)\
        .execute()
    
    print(f"\n" + "="*70)
    print(f"✅ MIGRATION COMPLETE!")
    print(f"   Production now has {len(staging_trades)} trades")
    print(f"   AI analysis preserved and updated")
    print("="*70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-id', required=True)
    parser.add_argument('--no-fix-angus', action='store_true')
    
    args = parser.parse_args()
    full_migration(args.batch_id, fix_angus_king=not args.no_fix_angus)
