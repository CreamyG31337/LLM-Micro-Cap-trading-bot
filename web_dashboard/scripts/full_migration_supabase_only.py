#!/usr/bin/env python3
"""
Full Migration: Replace Production with Staging Data (Supabase only)
====================================================================

Replaces ALL production data with clean staging data.
AI analysis update will need to be done separately via PostgreSQL.

Usage:
    python full_migration_supabase_only.py --batch-id <uuid>
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

def full_migration(fix_angus_king: bool = True):
    """Full replacement migration"""
    
    supabase = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("FULL PRODUCTION REPLACEMENT FROM STAGING")
    print("="*70)
    print("Migrating ALL staging records\n")
    
    # Get ALL staging data (paginate because Supabase has 1000 row limit)
    print("📥 Fetching all staging records...")
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
        print(f"   Fetched {len(all_staging_trades)} records...")
        
        if len(batch_result.data) < BATCH_SIZE:
            break
    
    staging_trades = all_staging_trades
    print(f"📊 Staging trades: {len(staging_trades)}")
    
    # Fix Angus King
    if fix_angus_king:
        angus_count = 0
        for trade in staging_trades:
            if trade['politician'] == 'Angus King' and not trade.get('party'):
                trade['party'] = 'Independent'
                angus_count += 1
        if angus_count > 0:
            print(f"   ✓ Fixed {angus_count} Angus King trades")
    
    # Clean duplicates
    print("\n🧹 Cleaning duplicates from staging...")
    groups = defaultdict(list)
    for trade in staging_trades:
        key = (
            trade['politician'], trade['ticker'], 
            str(trade['transaction_date']), trade['type'], 
            trade['amount'], trade.get('owner') or 'Not-Disclosed'
        )
        groups[key].append(trade)
    
    to_keep = []
    dupe_count = 0
    
    for key, trade_list in groups.items():
        # Sort by ID, keep first
        sorted_trades = sorted(trade_list, key=lambda x: x['id'])
        to_keep.append(sorted_trades[0])
        if len(trade_list) > 1:
            dupe_count += len(trade_list) - 1
    
    staging_trades = to_keep
    print(f"   ✅ Removed {dupe_count} duplicates")
    print(f"   ✅ Clean staging trades: {len(staging_trades)}")
    
    # Get production count
    prod_result = supabase.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .execute()
    
    print(f"\n📊 Current production: {prod_result.count} trades")
    
    # Confirm
    print(f"\n" + "="*70)
    print(f"READY TO MIGRATE:")
    print(f"  Current production: {prod_result.count} trades")
    print(f"  New production: {len(staging_trades)} trades")
    print(f"  Change: {len(staging_trades) - prod_result.count:+d} trades")
    print()
    print(f"⚠️  NOTE: AI analysis will need to be updated separately")
    print("="*70)
    
    response = input("\nProceed with full replacement? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Delete production
    print(f"\n🗑️  Clearing production table...")
    supabase.supabase.table('congress_trades').delete().neq('id', 0).execute()
    print(f"   ✅ Production cleared")
    
    # Load staging
    print(f"\n📥 Loading {len(staging_trades)} trades to production...")
    
    to_insert = []
    for trade in staging_trades:
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
            if (i // BATCH_SIZE) % 20 == 0:
                print(f"   ✓ Inserted {inserted}/{len(to_insert)} trades...")
        except Exception as e:
            print(f"   ❌ Error at batch {i//BATCH_SIZE}: {e}")
            print(f"   Continuing...")
    
    print(f"   ✅ Inserted {inserted} trades")
    
    # Mark ALL staging as promoted
    supabase.supabase.table('congress_trades_staging')\
        .update({'promoted_to_production': True, 'promoted_at': datetime.now().isoformat()})\
        .neq('id', 0)\
        .execute()
    
    # Get final count
    final_result = supabase.supabase.table('congress_trades')\
        .select('id', count='exact')\
        .execute()
    
    print(f"\n" + "="*70)
    print(f"✅ MIGRATION COMPLETE!")
    print(f"   Production now has {final_result.count} trades")
    print(f"\n⚠️  NEXT STEP: Update AI analysis trade_ids in PostgreSQL")
    print("="*70)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-fix-angus', action='store_true', 
                        help="Don't fix Angus King party")
    
    args = parser.parse_args()
    full_migration(fix_angus_king=not args.no_fix_angus)
