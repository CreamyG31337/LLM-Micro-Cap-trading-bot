#!/usr/bin/env python3
"""
Intelligent Re-Analysis of Affected Congress Trades
====================================================

This script identifies trades that need re-analysis due to committee assignment issues:
1. Trades with "no committee assignments found" errors in their analysis
2. Trades for politicians who now have committees (after fixes)

It then deletes the old analysis records so they can be re-analyzed with correct data.

Usage:
    python web_dashboard/scripts/rerun_affected_analysis.py [--dry-run]
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Set
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient
from postgres_client import PostgresClient

# Error messages to search for (from debug_committee_assignments.py)
COMMITTEE_ERROR_MESSAGES = [
    "no committee assignments found",
    "committee assignments could not be found",
    "None (no committee assignments found)",
    "Unknown (politician",
    "Error fetching committee data",
    "No committee assignments found",
    "Unable to determine regulatory power",
    "No recognized committee assignments"
]


def find_trades_with_committee_errors(postgres: PostgresClient) -> List[int]:
    """Find trade IDs that have committee assignment errors in their analysis."""
    print("Searching for trades with committee assignment errors...")
    
    # Build SQL query to search for error messages in reasoning text
    conditions = " OR ".join([f"reasoning ILIKE '%{msg}%'" for msg in COMMITTEE_ERROR_MESSAGES])
    
    query = f"""
        SELECT DISTINCT trade_id
        FROM congress_trades_analysis
        WHERE {conditions}
    """
    
    results = postgres.execute_query(query)
    trade_ids = [row['trade_id'] for row in results] if results else []
    
    print(f"  Found {len(trade_ids)} trades with committee assignment errors")
    return trade_ids


def get_politicians_without_committees(supabase: SupabaseClient) -> List[Dict[str, Any]]:
    """Get list of politicians who don't have committee assignments."""
    print("Identifying politicians without committee assignments...")
    
    # Get all politicians
    all_politicians = supabase.supabase.table('politicians')\
        .select('id, name, bioguide_id, party, state, chamber')\
        .execute()
    
    # Get all politicians with committee assignments (handle pagination)
    pol_ids_with_committees = set()
    page_size = 1000
    offset = 0
    
    while True:
        pols_with_committees = supabase.supabase.table('committee_assignments')\
            .select('politician_id')\
            .range(offset, offset + page_size - 1)\
            .execute()
        
        if not pols_with_committees.data:
            break
        
        pol_ids_with_committees.update({ca['politician_id'] for ca in pols_with_committees.data})
        
        if len(pols_with_committees.data) < page_size:
            break
        
        offset += page_size
    
    # Find politicians without committees
    pols_without_committees = [
        p for p in all_politicians.data 
        if p['id'] not in pol_ids_with_committees
    ]
    
    print(f"  Found {len(pols_without_committees)} politicians without committees")
    return pols_without_committees


def check_politician_now_has_committees(politician_id: int, supabase: SupabaseClient) -> bool:
    """Check if a politician now has committee assignments."""
    try:
        assignments_result = supabase.supabase.table('committee_assignments')\
            .select('id')\
            .eq('politician_id', politician_id)\
            .limit(1)\
            .execute()
        
        return len(assignments_result.data) > 0
    except Exception:
        return False


def find_trades_for_fixed_politicians(supabase: SupabaseClient, postgres: PostgresClient) -> List[int]:
    """Find trades for politicians who previously had no committees but now have them.
    
    This identifies politicians who:
    1. Had trades with committee errors in analysis
    2. Now have committees in the database
    """
    print("Finding trades for politicians who now have committees...")
    
    # First, get all trade IDs with committee errors from Postgres
    error_conditions = " OR ".join([f"reasoning ILIKE '%{msg}%'" for msg in COMMITTEE_ERROR_MESSAGES])
    query = f"""
        SELECT DISTINCT trade_id
        FROM congress_trades_analysis
        WHERE {error_conditions}
    """
    
    results = postgres.execute_query(query)
    
    if not results:
        print("  No trades with errors found")
        return []
    
    error_trade_ids = [row['trade_id'] for row in results]
    print(f"  Found {len(error_trade_ids)} trades with errors")
    
    # Fetch these trades from Supabase to get politician_ids
    print("  Fetching politician IDs for these trades...")
    politician_ids = set()
    batch_size = 100
    
    for i in range(0, len(error_trade_ids), batch_size):
        batch = error_trade_ids[i:i+batch_size]
        try:
            trades_result = supabase.supabase.table('congress_trades')\
                .select('id, politician_id')\
                .in_('id', batch)\
                .execute()
            
            for trade in trades_result.data:
                politician_id = trade.get('politician_id')
                if politician_id:
                    politician_ids.add(politician_id)
        except Exception as e:
            print(f"  [WARNING] Error fetching batch: {e}")
    
    print(f"  Checking {len(politician_ids)} unique politicians...")
    
    # Check which politicians now have committees
    fixed_politician_ids = []
    for politician_id in politician_ids:
        if check_politician_now_has_committees(politician_id, supabase):
            fixed_politician_ids.append(politician_id)
    
    if not fixed_politician_ids:
        print("  No politicians found who now have committees")
        return []
    
    print(f"  Found {len(fixed_politician_ids)} politicians who now have committees")
    
    # Get ALL trades for these fixed politicians (not just the ones with errors)
    # This ensures we re-analyze all their trades with the new committee data
    print("  Fetching all trades for these politicians...")
    all_trade_ids = []
    batch_size = 1000
    offset = 0
    
    # Process politicians in batches to avoid query limits
    for i in range(0, len(fixed_politician_ids), 50):  # Process 50 politicians at a time
        politician_batch = fixed_politician_ids[i:i+50]
        offset = 0
        
        while True:
            try:
                trades_result = supabase.supabase.table('congress_trades')\
                    .select('id')\
                    .in_('politician_id', politician_batch)\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not trades_result.data:
                    break
                
                all_trade_ids.extend([trade['id'] for trade in trades_result.data])
                
                if len(trades_result.data) < batch_size:
                    break
                
                offset += batch_size
            except Exception as e:
                print(f"  [WARNING] Error fetching trades for politician batch: {e}")
                break
    
    print(f"  Found {len(all_trade_ids)} total trades for these politicians")
    
    return all_trade_ids


def delete_analysis_for_trades(postgres: PostgresClient, trade_ids: List[int], dry_run: bool = False) -> int:
    """Delete analysis records for the given trade IDs."""
    if not trade_ids:
        print("No trade IDs to delete")
        return 0
    
    if dry_run:
        print(f"\n[DRY RUN] Would delete {len(trade_ids)} analysis records")
        return 0
    
    print(f"\nDeleting analysis records for {len(trade_ids)} trades...")
    
    # Batch delete
    batch_size = 500
    total_deleted = 0
    
    chunks = [trade_ids[i:i + batch_size] for i in range(0, len(trade_ids), batch_size)]
    
    for idx, chunk in enumerate(chunks):
        try:
            query = "DELETE FROM congress_trades_analysis WHERE trade_id = ANY(%s)"
            count = postgres.execute_update(query, (chunk,))
            total_deleted += count
            print(f"  Chunk {idx+1}/{len(chunks)}: Deleted {count} analysis records")
        except Exception as e:
            print(f"  [ERROR] Chunk {idx+1} failed: {e}")
    
    return total_deleted


def get_trade_details(supabase: SupabaseClient, trade_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get trade details for reporting."""
    if not trade_ids:
        return {}
    
    trades_data = {}
    batch_size = 100
    
    for i in range(0, len(trade_ids), batch_size):
        batch = trade_ids[i:i+batch_size]
        try:
            trades_result = supabase.supabase.table('congress_trades_enriched')\
                .select('id, politician, politician_id, ticker, transaction_date, chamber, party, state')\
                .in_('id', batch)\
                .execute()
        except Exception:
            # Fallback: query congress_trades directly
            trades_result = supabase.supabase.table('congress_trades')\
                .select('id, politician_id, ticker, transaction_date, chamber, party, state, politicians(name)')\
                .in_('id', batch)\
                .execute()
            # Transform to match expected format
            for trade in trades_result.data:
                politician_name = 'Unknown'
                if trade.get('politicians'):
                    politician_name = trade['politicians'].get('name', 'Unknown')
                trade['politician'] = politician_name
        
        for trade in trades_result.data:
            trades_data[trade['id']] = trade
    
    return trades_data


def print_summary_report(
    error_trade_ids: List[int],
    fixed_trade_ids: List[int],
    all_trade_ids: Set[int],
    trades_data: Dict[int, Dict[str, Any]],
    dry_run: bool = False
):
    """Print a summary report of what will be re-analyzed."""
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    
    print(f"\nTrades with committee errors: {len(error_trade_ids)}")
    print(f"Trades for fixed politicians: {len(fixed_trade_ids)}")
    print(f"Total unique trades to re-analyze: {len(all_trade_ids)}")
    
    if not all_trade_ids:
        print("\n✅ No trades need re-analysis!")
        return
    
    # Group by politician
    politician_trades = defaultdict(list)
    for trade_id in all_trade_ids:
        trade = trades_data.get(trade_id, {})
        politician = trade.get('politician', 'Unknown')
        politician_trades[politician].append(trade)
    
    print(f"\nAffected politicians: {len(politician_trades)}")
    print("\nTop 10 politicians by affected trade count:")
    print("-" * 70)
    
    sorted_politicians = sorted(politician_trades.items(), key=lambda x: len(x[1]), reverse=True)
    for politician, trades in sorted_politicians[:10]:
        print(f"  {politician}: {len(trades)} trades")
    
    if len(sorted_politicians) > 10:
        print(f"  ... and {len(sorted_politicians) - 10} more politicians")
    
    if dry_run:
        print("\n[DRY RUN] No analysis records were deleted.")
        print("Run without --dry-run to delete and re-analyze.")
    else:
        print("\n✅ Analysis records deleted. Run analyze_congress_trades_batch.py to re-analyze.")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Re-analyze affected congress trades')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()
    
    print("=" * 70)
    print("INTELLIGENT CONGRESS TRADES RE-ANALYSIS")
    print("=" * 70)
    print()
    
    if args.dry_run:
        print("[DRY RUN MODE] No changes will be made\n")
    
    try:
        # Initialize clients
        postgres = PostgresClient()
        supabase = SupabaseClient(use_service_role=True)
        
        # Step 1: Find trades with committee errors
        error_trade_ids = find_trades_with_committee_errors(postgres)
        
        # Step 2: Find trades for politicians who now have committees
        fixed_trade_ids = find_trades_for_fixed_politicians(supabase, postgres)
        
        # Step 3: Combine and deduplicate
        all_trade_ids = list(set(error_trade_ids + fixed_trade_ids))
        
        if not all_trade_ids:
            print("\n✅ No trades need re-analysis!")
            return
        
        # Step 4: Get trade details for reporting
        print("\nFetching trade details for reporting...")
        trades_data = get_trade_details(supabase, all_trade_ids)
        
        # Step 5: Print summary
        print_summary_report(error_trade_ids, fixed_trade_ids, set(all_trade_ids), trades_data, args.dry_run)
        
        # Step 6: Delete analysis records
        if all_trade_ids:
            deleted_count = delete_analysis_for_trades(postgres, all_trade_ids, args.dry_run)
            if not args.dry_run:
                print(f"\n✅ Deleted {deleted_count} analysis records")
                print("\nNext step: Run analyze_congress_trades_batch.py to re-analyze these trades")
        
        print("\n" + "=" * 70)
        print("COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

