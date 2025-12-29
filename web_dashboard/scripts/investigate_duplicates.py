#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Duplicate Trades in Staging Batch
============================================

Shows detailed information about duplicate trades to help determine
if they're real duplicates or legitimate separate trades.

Usage:
    python investigate_duplicates.py <batch-id>
    python investigate_duplicates.py --latest
"""

import sys
import argparse
import io
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from supabase_client import SupabaseClient
import pandas as pd


def get_batch_data(client: SupabaseClient, batch_id: str) -> pd.DataFrame:
    """Fetch all trades for a batch with pagination"""
    print(f"Fetching all trades for batch {batch_id}...")
    all_trades = []
    batch_size = 1000
    offset = 0
    
    while True:
        result = client.supabase.table('congress_trades_staging')\
            .select('*')\
            .eq('import_batch_id', batch_id)\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not result.data:
            break
        
        all_trades.extend(result.data)
        
        if len(result.data) < batch_size:
            break
        
        offset += batch_size
        
        if offset % 5000 == 0:
            print(f"  Fetched {len(all_trades)} rows so far...")
        
        if offset > 100000:
            print(f"Warning: Reached 100,000 row safety limit")
            break
    
    print(f"Total rows fetched: {len(all_trades)}\n")
    return pd.DataFrame(all_trades)


def find_duplicates(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """Find duplicate trades grouped by business key"""
    # Create business key (same as production unique constraint)
    df['business_key'] = df.apply(lambda x: (
        str(x['politician']),
        str(x['ticker']),
        str(x['transaction_date']),
        str(x['type']),
        str(x.get('amount', '')),
        str(x.get('owner') or 'Not-Disclosed')
    ), axis=1)
    
    # Find duplicates
    duplicates = df[df.duplicated(subset='business_key', keep=False)].copy()
    
    # Group by business key
    duplicate_groups = defaultdict(list)
    for idx, row in duplicates.iterrows():
        key = row['business_key']
        duplicate_groups[key].append({
            'id': row['id'],
            'politician': row['politician'],
            'ticker': row['ticker'],
            'transaction_date': str(row['transaction_date']),
            'disclosure_date': str(row.get('disclosure_date', '')),
            'type': row['type'],
            'amount': row.get('amount', ''),
            'owner': row.get('owner', 'Not-Disclosed'),
            'chamber': row.get('chamber', ''),
            'party': row.get('party', ''),
            'state': row.get('state', ''),
            'price': row.get('price'),
            'asset_type': row.get('asset_type', ''),
            'source_url': row.get('source_url', ''),
            'import_timestamp': str(row.get('import_timestamp', ''))
        })
    
    return dict(duplicate_groups)


def print_duplicate_analysis(duplicate_groups: Dict[str, List[Dict[str, Any]]], 
                             show_all: bool = False):
    """Print detailed analysis of duplicates"""
    
    print("="*80)
    print("DUPLICATE TRADES ANALYSIS")
    print("="*80)
    print(f"\nTotal duplicate groups: {len(duplicate_groups)}")
    
    total_duplicate_records = sum(len(records) for records in duplicate_groups.values())
    print(f"Total duplicate records: {total_duplicate_records}")
    print(f"  (Each group has 2+ records with identical business key)")
    
    print("\n" + "-"*80)
    print("BUSINESS KEY DEFINITION")
    print("-"*80)
    print("Trades are considered duplicates if they have the same:")
    print("  • Politician name")
    print("  • Ticker symbol")
    print("  • Transaction date")
    print("  • Transaction type (Purchase/Sale/Exchange/Received)")
    print("  • Amount range")
    print("  • Owner (Self/Spouse/Child/Joint/Not-Disclosed)")
    
    # Analyze patterns
    print("\n" + "-"*80)
    print("DUPLICATE PATTERNS")
    print("-"*80)
    
    # Count duplicates per politician
    politician_counts = defaultdict(int)
    for records in duplicate_groups.values():
        if records:
            politician_counts[records[0]['politician']] += len(records)
    
    print("\nTop 10 Politicians with Most Duplicates:")
    sorted_politicians = sorted(politician_counts.items(), key=lambda x: x[1], reverse=True)
    for politician, count in sorted_politicians[:10]:
        print(f"  {politician}: {count} duplicate records")
    
    # Count by number of duplicates per group
    group_sizes = defaultdict(int)
    for records in duplicate_groups.values():
        group_sizes[len(records)] += 1
    
    print("\nDuplicate Group Sizes:")
    for size, count in sorted(group_sizes.items()):
        print(f"  {size} records per group: {count} groups")
    
    # Show examples
    print("\n" + "-"*80)
    print("DETAILED EXAMPLES")
    print("-"*80)
    
    # Show first N groups in detail
    max_groups = len(duplicate_groups) if show_all else 20
    shown = 0
    
    for i, (key, records) in enumerate(duplicate_groups.items()):
        if shown >= max_groups:
            break
        
        print(f"\n{'='*80}")
        print(f"DUPLICATE GROUP {i+1} ({len(records)} records)")
        print(f"{'='*80}")
        
        # Show the key (it's a tuple)
        if isinstance(key, tuple):
            print(f"Politician: {key[0]}")
            print(f"Ticker: {key[1]}")
            print(f"Transaction Date: {key[2]}")
            print(f"Type: {key[3]}")
            print(f"Amount: {key[4]}")
            print(f"Owner: {key[5]}")
        else:
            # Fallback for string keys
            key_parts = str(key).split(", ")
            print(f"Politician: {key_parts[0] if len(key_parts) > 0 else 'N/A'}")
            print(f"Ticker: {key_parts[1] if len(key_parts) > 1 else 'N/A'}")
            print(f"Transaction Date: {key_parts[2] if len(key_parts) > 2 else 'N/A'}")
            print(f"Type: {key_parts[3] if len(key_parts) > 3 else 'N/A'}")
            print(f"Amount: {key_parts[4] if len(key_parts) > 4 else 'N/A'}")
            print(f"Owner: {key_parts[5] if len(key_parts) > 5 else 'N/A'}")
        
        print(f"\nRecords in this group:")
        for j, record in enumerate(records, 1):
            print(f"\n  Record {j} (ID: {record['id']}):")
            print(f"    Disclosure Date: {record['disclosure_date']}")
            print(f"    Chamber: {record['chamber']}")
            print(f"    Party: {record['party'] or 'NULL'}")
            print(f"    State: {record['state'] or 'NULL'}")
            print(f"    Price: {record['price'] or 'NULL'}")
            print(f"    Asset Type: {record['asset_type'] or 'NULL'}")
            print(f"    Source URL: {record['source_url'] or 'NULL'}")
            print(f"    Import Timestamp: {record['import_timestamp']}")
        
        # Check if records are truly identical
        if len(records) > 1:
            first = records[0]
            all_same = all(
                r['disclosure_date'] == first['disclosure_date'] and
                r['chamber'] == first['chamber'] and
                r['party'] == first['party'] and
                r['state'] == first['state'] and
                r['price'] == first['price'] and
                r['asset_type'] == first['asset_type']
                for r in records[1:]
            )
            
            if all_same:
                print(f"\n  ⚠️  WARNING: All {len(records)} records are IDENTICAL in all fields!")
                print(f"     These are likely true duplicates and should be deduplicated.")
            else:
                print(f"\n  ℹ️  Records differ in some fields (disclosure_date, price, etc.)")
                print(f"     Review to determine if these are legitimate separate trades.")
        
        shown += 1
    
    if not show_all and len(duplicate_groups) > max_groups:
        print(f"\n{'='*80}")
        print(f"Showing first {max_groups} of {len(duplicate_groups)} duplicate groups.")
        print(f"Use --all flag to show all groups.")
        print(f"{'='*80}")
    
    # Summary recommendations
    print("\n" + "-"*80)
    print("RECOMMENDATIONS")
    print("-"*80)
    print("\n1. Review the examples above to understand the duplicate patterns")
    print("2. Check if duplicates have:")
    print("   • Same disclosure_date, price, source_url → Likely true duplicates")
    print("   • Different disclosure_date or price → Might be legitimate separate trades")
    print("3. If true duplicates, you can:")
    print("   • Delete duplicate records keeping only one")
    print("   • Or let the promotion script handle it (it will skip duplicates)")
    print("4. Consider investigating why duplicates were created:")
    print("   • Scraper issue (same trade scraped twice)?")
    print("   • Data source issue (duplicate entries in source)?")
    print("   • Import process issue (batch imported multiple times)?")


def export_duplicates_csv(duplicate_groups: Dict[Any, List[Dict[str, Any]]], 
                          output_file: str):
    """Export duplicate records to CSV for analysis"""
    all_records = []
    for key, records in duplicate_groups.items():
        for record in records:
            record['duplicate_group_key'] = str(key)
            record['duplicate_count'] = len(records)
            all_records.append(record)
    
    df = pd.DataFrame(all_records)
    df.to_csv(output_file, index=False)
    print(f"\n✅ Exported {len(all_records)} duplicate records to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Investigate duplicate trades in staging batch')
    parser.add_argument('batch_id', nargs='?', help='Batch ID to investigate')
    parser.add_argument('--latest', action='store_true', help='Investigate most recent batch')
    parser.add_argument('--all', action='store_true', help='Show all duplicate groups (default: first 20)')
    parser.add_argument('--export', help='Export duplicates to CSV file')
    
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
        print(f"Investigating latest batch: {batch_id}\n")
    elif args.batch_id:
        batch_id = args.batch_id
    else:
        print("Error: Must provide batch_id or --latest")
        parser.print_help()
        sys.exit(1)
    
    # Get data
    df = get_batch_data(client, batch_id)
    
    if len(df) == 0:
        print(f"❌ No data found for batch {batch_id}")
        return
    
    # Find duplicates
    print("Analyzing duplicates...")
    duplicate_groups = find_duplicates(df)
    
    if not duplicate_groups:
        print("\n✅ No duplicates found in this batch!")
        return
    
    # Print analysis
    print_duplicate_analysis(duplicate_groups, show_all=args.all)
    
    # Export if requested
    if args.export:
        export_duplicates_csv(duplicate_groups, args.export)


if __name__ == '__main__':
    main()

