#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to find and clean duplicate portfolio positions.
Identifies dates with duplicates and removes them, keeping only the latest entry per ticker per date.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Add paths for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "web_dashboard"))

from dotenv import load_dotenv
load_dotenv()

from web_dashboard.supabase_client import SupabaseClient


def find_duplicates(client, fund_name: str):
    """Find all dates with duplicate positions for a fund."""
    print(f"\n{'='*60}")
    print(f"Scanning for duplicates: {fund_name}")
    print(f"{'='*60}")
    
    # Get all positions grouped by date
    all_positions = []
    batch_size = 1000
    offset = 0
    
    while True:
        result = client.supabase.table("portfolio_positions")\
            .select("id, ticker, date, shares, created_at")\
            .eq("fund", fund_name)\
            .order("date")\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not result.data:
            break
        
        all_positions.extend(result.data)
        
        if len(result.data) < batch_size:
            break
        
        offset += batch_size
    
    print(f"  Total position rows: {len(all_positions)}")
    
    # Group by date
    by_date = defaultdict(list)
    for pos in all_positions:
        date_str = pos['date'][:10]  # Just the date part
        by_date[date_str].append(pos)
    
    print(f"  Total unique dates: {len(by_date)}")
    
    # Find dates with duplicates
    dates_with_duplicates = []
    total_duplicates = 0
    
    for date_str, positions in sorted(by_date.items()):
        # Count tickers
        ticker_counts = defaultdict(list)
        for pos in positions:
            ticker_counts[pos['ticker']].append(pos)
        
        # Check for duplicates
        duplicates_on_date = {t: ps for t, ps in ticker_counts.items() if len(ps) > 1}
        
        if duplicates_on_date:
            unique_tickers = len(ticker_counts)
            total_positions = len(positions)
            dup_count = sum(len(ps) - 1 for ps in duplicates_on_date.values())
            total_duplicates += dup_count
            
            dates_with_duplicates.append({
                'date': date_str,
                'total_positions': total_positions,
                'unique_tickers': unique_tickers,
                'duplicate_count': dup_count,
                'duplicates': duplicates_on_date
            })
    
    if not dates_with_duplicates:
        print("  [OK] No duplicates found!")
        return []
    
    print(f"\n  *** FOUND {total_duplicates} DUPLICATE ENTRIES across {len(dates_with_duplicates)} dates!")
    
    # Show summary of dates with issues
    print(f"\n  Dates with duplicates:")
    for item in dates_with_duplicates[-10:]:  # Show last 10
        print(f"    {item['date']}: {item['total_positions']} total, {item['unique_tickers']} unique, {item['duplicate_count']} duplicates")
    
    if len(dates_with_duplicates) > 10:
        print(f"    ... and {len(dates_with_duplicates) - 10} more dates")
    
    return dates_with_duplicates


def clean_duplicates(client, fund_name: str, dry_run: bool = True):
    """Remove duplicate positions, keeping the one with the latest created_at timestamp."""
    duplicates_info = find_duplicates(client, fund_name)
    
    if not duplicates_info:
        return
    
    ids_to_delete = []
    
    for date_info in duplicates_info:
        for ticker, positions in date_info['duplicates'].items():
            # Sort by created_at descending, keep the most recent one
            sorted_positions = sorted(
                positions,
                key=lambda p: p.get('created_at', ''),
                reverse=True
            )
            
            # Keep the first (most recent), delete the rest
            for pos in sorted_positions[1:]:
                ids_to_delete.append(pos['id'])
    
    print(f"\n  Total positions to delete: {len(ids_to_delete)}")
    
    if dry_run:
        print("  [DRY RUN] No changes made. Run with dry_run=False to delete duplicates.")
        return ids_to_delete
    
    # Actually delete
    print("  Deleting duplicates...")
    deleted_count = 0
    
    # Delete in batches
    batch_size = 100
    for i in range(0, len(ids_to_delete), batch_size):
        batch = ids_to_delete[i:i + batch_size]
        try:
            client.supabase.table("portfolio_positions")\
                .delete()\
                .in_("id", batch)\
                .execute()
            deleted_count += len(batch)
            print(f"    Deleted batch {i//batch_size + 1}: {len(batch)} rows")
        except Exception as e:
            print(f"    Error deleting batch: {e}")
    
    print(f"  [DONE] Deleted {deleted_count} duplicate entries")
    
    return ids_to_delete


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Find and clean duplicate portfolio positions")
    parser.add_argument("--fund", default="Project Chimera", help="Fund name to check")
    parser.add_argument("--delete", action="store_true", help="Actually delete duplicates (default is dry-run)")
    parser.add_argument("--all-funds", action="store_true", help="Check all production funds")
    args = parser.parse_args()
    
    print("="*60)
    print("Portfolio Positions Duplicate Cleaner")
    print("="*60)
    
    client = SupabaseClient(use_service_role=True)
    
    if args.all_funds:
        # Get all production funds
        funds_result = client.supabase.table("funds")\
            .select("name")\
            .eq("is_production", True)\
            .execute()
        
        funds = [f['name'] for f in funds_result.data] if funds_result.data else []
        print(f"Checking {len(funds)} production funds...")
    else:
        funds = [args.fund]
    
    for fund in funds:
        clean_duplicates(client, fund, dry_run=not args.delete)


if __name__ == "__main__":
    main()
