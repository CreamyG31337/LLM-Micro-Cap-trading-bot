#!/usr/bin/env python3
"""
Migrate Congress Trades: Staging → Production (Preserving AI Analysis)
=======================================================================

Safely migrates new trades from staging to production while preserving
existing AI conflict scores and analysis notes.

Strategy:
- For NEW trades: Insert directly
- For EXISTING trades (already analyzed): Skip to preserve AI data
- Update Angus King's party to "Independent"

Usage:
    python migrate_staging_to_production.py --batch-id <uuid>
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

def migrate_batch(batch_id: str, fix_angus_king: bool = True):
    """Migrate staging batch to production, preserving AI analysis"""
    
    client = SupabaseClient(use_service_role=True)
    
    print("="*70)
    print("STAGING → PRODUCTION MIGRATION")
    print("="*70)
    print(f"Batch ID: {batch_id}\n")
    
    # Get staging data
    staging_result = client.supabase.table('congress_trades_staging')\
        .select('*')\
        .eq('import_batch_id', batch_id)\
        .execute()
    
    staging_trades = staging_result.data
    print(f"📊 Staging trades: {len(staging_trades)}")
    
    # Fix Angus King party if requested
    if fix_angus_king:
        angus_count = 0
        for trade in staging_trades:
            if trade['politician'] == 'Angus King' and not trade.get('party'):
                trade['party'] = 'Independent'
                angus_count += 1
        
        if angus_count > 0:
            print(f"✓ Fixed {angus_count} Angus King trades (set party to 'Independent')")
    
    # Get existing production data
    prod_result = client.supabase.table('congress_trades')\
        .select('politician,ticker,transaction_date,type,amount,owner,conflict_score,notes')\
        .execute()
    
    print(f"📊 Production trades: {len(prod_result.data)}")
    
    # Build production lookup by business key
    prod_keys = {}
    prod_analyzed = 0
    
    for trade in prod_result.data:
        key = (
            trade['politician'],
            trade['ticker'],
            str(trade['transaction_date']),
            trade['type'],
            trade['amount'],
            trade.get('owner') or 'Not-Disclosed'
        )
        prod_keys[key] = {
            'analyzed': trade.get('conflict_score') is not None,
            'score': trade.get('conflict_score'),
            'notes': trade.get('notes')
        }
        if trade.get('conflict_score') is not None:
            prod_analyzed += 1
    
    print(f"   - {prod_analyzed} have AI analysis ({100*prod_analyzed/len(prod_result.data):.1f}%)\n")
    
    # Categorize staging trades
    new_trades = []
    existing_unanalyzed = []
    existing_analyzed = []
    
    for trade in staging_trades:
        key = (
            trade['politician'],
            trade['ticker'],
            str(trade['transaction_date']),
            trade['type'],
            trade['amount'],
            trade.get('owner') or 'Not-Disclosed'
        )
        
        if key not in prod_keys:
            # Completely new trade
            new_trades.append(trade)
        elif prod_keys[key]['analyzed']:
            # Exists and has AI analysis - skip to preserve
            existing_analyzed.append(trade)
        else:
            # Exists but no AI analysis - could update
            existing_unanalyzed.append(trade)
    
    print("Trade Categorization:")
    print(f"   ✅ New trades (will insert): {len(new_trades)}")
    print(f"   ⏭️  Existing with AI (will skip): {len(existing_analyzed)}")
    print(f"   ⚠️  Existing without AI (will skip): {len(existing_unanalyzed)}")
    print()
    
    if len(new_trades) == 0:
        print("⚠️  No new trades to insert. All trades already exist in production.")
        return
    
    # Prepare new trades for insertion
    to_insert = []
    for trade in new_trades:
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
    
    # Confirm migration
    print(f"Ready to insert {len(to_insert)} new trades to production.")
    response = input("Proceed? (yes/no): ")
    
    if response.lower() != 'yes':
        print("Aborted.")
        return
    
    # Insert in batches
    BATCH_SIZE = 100
    inserted = 0
    
    for i in range(0, len(to_insert), BATCH_SIZE):
        batch = to_insert[i:i+BATCH_SIZE]
        try:
            client.supabase.table('congress_trades').insert(batch).execute()
            inserted += len(batch)
            print(f"   ✓ Inserted batch {i//BATCH_SIZE + 1}/{(len(to_insert) + BATCH_SIZE - 1)//BATCH_SIZE}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break
    
    print(f"\n✅ Migration complete!")
    print(f"   Inserted: {inserted} new trades")
    print(f"   Preserved: {len(existing_analyzed)} trades with AI analysis")
    print(f"   Skipped: {len(existing_unanalyzed)} duplicate trades without analysis")
    
    # Mark staging as promoted
    try:
        client.supabase.table('congress_trades_staging')\
            .update({'promoted_to_production': True, 'promoted_at': datetime.now().isoformat()})\
            .eq('import_batch_id', batch_id)\
            .execute()
        print(f"   ✓ Marked staging batch as promoted")
    except Exception as e:
        print(f"   ⚠️  Could not mark staging: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-id', required=True, help='Staging batch ID')
    parser.add_argument('--no-fix-angus', action='store_true', help="Don't fix Angus King party")
    
    args = parser.parse_args()
    migrate_batch(args.batch_id, fix_angus_king=not args.no_fix_angus)
