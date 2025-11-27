#!/usr/bin/env python3
"""
Test script for backfill missing days functionality.

This script:
1. Deletes the last week of portfolio data from Supabase
2. Then you can test graph generation to verify backfill works
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / 'web_dashboard' / '.env')

from data.repositories.supabase_repository import SupabaseRepository
from display.console_output import print_info, print_warning, print_success, print_error, _safe_emoji


def delete_last_week_from_supabase(fund_name: str = "Project Chimera", days: int = 7, auto_confirm: bool = False):
    """
    Delete the last N days of portfolio data from Supabase for testing backfill.
    
    Args:
        fund_name: Fund name to delete data from
        days: Number of days to delete (default: 7 for last week)
    """
    print("Testing Backfill Missing Days Functionality")
    print("=" * 60)
    print(f"Fund: {fund_name}")
    print(f"Deleting last {days} days of data")
    print()
    
    try:
        # Create Supabase repository
        supabase_repo = SupabaseRepository(fund_name=fund_name)
        
        # Get current data to see what we have
        print_info("Loading current portfolio data...")
        all_snapshots = supabase_repo.get_portfolio_data()
        
        if not all_snapshots:
            print_warning("No portfolio data found in Supabase")
            return False
        
        # Get date range for deletion
        latest_snapshot = max(all_snapshots, key=lambda s: s.timestamp)
        latest_date = latest_snapshot.timestamp.date()
        cutoff_date = latest_date - timedelta(days=days)
        
        print_info(f"Latest snapshot date: {latest_date}")
        print_info(f"Will delete data from: {cutoff_date} to {latest_date}")
        print()
        
        # Count positions that will be deleted
        positions_to_delete = [
            pos for snapshot in all_snapshots
            for pos in snapshot.positions
            if snapshot.timestamp.date() >= cutoff_date
        ]
        
        print_warning(f"About to delete {len(positions_to_delete)} portfolio positions")
        print_warning(f"This will remove data from {cutoff_date} to {latest_date}")
        print()
        
        # Confirm deletion (skip if auto_confirm is True)
        if not auto_confirm:
            response = input("Continue with deletion? (yes/no): ").strip().lower()
            if response != 'yes':
                print_info("Deletion cancelled")
                return False
        else:
            print_warning("Auto-confirming deletion (--yes flag provided)")
        
        # Delete portfolio positions for the date range
        print_info(f"Deleting portfolio positions from {cutoff_date} to {latest_date}...")
        
        # Format dates for Supabase query
        start_date_str = cutoff_date.isoformat()
        end_date_str = latest_date.isoformat()
        
        # Delete using Supabase client
        delete_result = supabase_repo.supabase.table("portfolio_positions").delete()\
            .eq("fund", fund_name)\
            .gte("date", f"{start_date_str}T00:00:00")\
            .lte("date", f"{end_date_str}T23:59:59.999999")\
            .execute()
        
        deleted_count = len(delete_result.data) if delete_result.data else 0
        print_success(f"Deleted {deleted_count} portfolio positions")
        
        # Verify deletion
        print_info("Verifying deletion...")
        remaining_snapshots = supabase_repo.get_portfolio_data()
        if remaining_snapshots:
            new_latest = max(remaining_snapshots, key=lambda s: s.timestamp)
            print_info(f"New latest snapshot date: {new_latest.timestamp.date()}")
        else:
            print_warning("No portfolio data remaining")
        
        print()
        print_success("Test data deletion complete!")
        print_info("Next steps:")
        print_info("   1. Run the graph generation script")
        print_info("   2. Verify that missing days are automatically backfilled")
        print_info("   3. Check that the graph shows continuous data points")
        
        return True
        
    except Exception as e:
        print_error(f"Error deleting data: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Delete last week of data from Supabase for testing backfill")
    parser.add_argument(
        "--fund",
        type=str,
        default="Project Chimera",
        help="Fund name (default: Project Chimera)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to delete (default: 7)"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-confirm deletion without prompting"
    )
    
    args = parser.parse_args()
    
    success = delete_last_week_from_supabase(fund_name=args.fund, days=args.days, auto_confirm=args.yes)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

