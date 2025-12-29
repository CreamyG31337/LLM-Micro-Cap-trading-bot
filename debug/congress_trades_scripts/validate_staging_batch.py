#!/usr/bin/env python3
"""
Quick Validation Script for Congress Trades Staging Batches
============================================================

Simple script to check staging data quality.

Usage:
    python validate_staging_batch.py <batch-id>
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient

def validate_batch(batch_id: str):
    """Quick validation of a staging batch"""
    
    client = SupabaseClient(use_service_role=True)
    
    # Get batch data
    result = client.supabase.table('congress_trades_staging')\
        .select('*')\
        .eq('import_batch_id', batch_id)\
        .execute()
    
    if not result.data:
        print(f"❌ No data found for batch {batch_id}")
        return
    
    trades = result.data
    
    print(f"\n{'='*70}")
    print(f"BATCH VALIDATION - {batch_id}")
    print(f"{'='*70}\n")
    
    print(f"📊 Total trades: {len(trades)}\n")
    
    # Data quality checks
    missing_party = sum(1 for t in trades if not t.get('party'))
    missing_state = sum(1 for t in trades if not t.get('state'))
    missing_owner = sum(1 for t in trades if not t.get('owner'))
    
    print("Data Completeness:")
    print(f"  ✓ Party:  {len(trades) - missing_party}/{len(trades)} ({100*(1-missing_party/len(trades)):.1f}%)")
    print(f"  ✓ State:  {len(trades) - missing_state}/{len(trades)} ({100*(1-missing_state/len(trades)):.1f}%)")
    print(f"  ✓ Owner:  {len(trades) - missing_owner}/{len(trades)} ({100*(1-missing_owner/len(trades)):.1f}%)")
    
    # Check for duplicates within batch
    from collections import defaultdict
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
    
    duplicates = {k: v for k, v in groups.items() if len(v) > 1}
    
    print(f"\nDuplicate Detection:")
    if duplicates:
        print(f"  ⚠️  Found {len(duplicates)} duplicate groups:")
        for i, (key, ids) in enumerate(list(duplicates.items())[:5]):
            print(f"     {i+1}. {key[0]} | {key[1]} | {key[2]} - {len(ids)} records")
    else:
        print(f"  ✅ No duplicates within batch")
    
    # Sample data
    print(f"\nSample Trades:")
    for i, trade in enumerate(trades[:5]):
        print(f"  {i+1}. {trade['politician']:20s} | {trade['ticker']:6s} | {trade['transaction_date']} | {trade['type']:8s}")
    
    print(f"\n{'='*70}")
    print(f"Batch Status: {'⚠️  NEEDS REVIEW' if (missing_party > 0 or missing_state > 0 or duplicates) else '✅ READY TO PROMOTE'}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate_staging_batch.py <batch-id>")
        sys.exit(1)
    
    validate_batch(sys.argv[1])
