#!/usr/bin/env python3
"""
Backfill Performance Metrics Script
====================================

Populates the performance_metrics table with historical data from portfolio_positions.
This is a one-time script to catch up on past data.

Usage:
    python web_dashboard/backfill_performance_metrics.py

Options:
    --fund FUND_NAME    Only backfill for a specific fund
    --from-date DATE    Start date (YYYY-MM-DD)
    --to-date DATE      End date (YYYY-MM-DD)
"""

import sys
import os
from datetime import datetime, date, timedelta
import argparse

# Add parent directory to path for console utils
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from display.console_output import _safe_emoji

# Add web_dashboard to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

# Add scheduler to path
scheduler_path = os.path.join(os.path.dirname(__file__), 'web_dashboard', 'scheduler')
if scheduler_path not in sys.path:
    sys.path.insert(0, scheduler_path)

from supabase_client import SupabaseClient
from scheduler.jobs_metrics import populate_performance_metrics_job


def backfill_performance_metrics(
    fund_filter: str = None,
    from_date: date = None,
    to_date: date = None
) -> None:
    """Backfill performance_metrics table with historical data.
    
    Uses the consolidated populate_performance_metrics_job function.
    """
    
    print(f"{_safe_emoji('🔄')} Starting performance metrics backfill...")
    
    client = SupabaseClient()
    
    # Get all distinct dates from portfolio_positions
    query = client.supabase.table("portfolio_positions").select("date")
    
    if fund_filter:
        query = query.eq("fund", fund_filter)
    
    if from_date:
        query = query.gte("date", f"{from_date}T00:00:00")
    
    if to_date:
        query = query.lte("date", f"{to_date}T23:59:59.999999")
    
    # Fetch all dates (might be large, but we need distinct dates)
    print(f"{_safe_emoji('📊')} Fetching all position dates...")
    all_positions = query.execute().data
    
    if not all_positions:
        print(f"{_safe_emoji('⚠️')} No position data found matching criteria")
        return
    
    # Extract unique dates
    unique_dates = set()
    for pos in all_positions:
        dt = datetime.fromisoformat(pos['date'].replace('Z', '+00:00'))
        unique_dates.add(dt.date())
    
    dates_list = sorted(unique_dates)
    print(f"{_safe_emoji('📅')} Found {len(dates_list)} unique dates to process")
    print(f"   Range: {dates_list[0]} to {dates_list[-1]}")
    
    # Process each date using the consolidated job function
    successful_dates = 0
    failed = 0
    
    for target_date in dates_list:
        try:
            # Call the consolidated job function with skip_existing=True
            populate_performance_metrics_job(
                target_date=target_date,
                fund_filter=fund_filter,
                skip_existing=True
            )
            successful_dates += 1
            
            # Progress indicator
            if successful_dates % 10 == 0:
                print(f"   Processed {successful_dates}/{len(dates_list)} dates...", end='\r')
        
        except Exception as e:
            print(f"\n{_safe_emoji('❌')} Error processing {target_date}: {e}")
            failed += 1
    
    print(f"\n\n{_safe_emoji('✅')} Backfill complete!")
    print(f"   Dates processed: {successful_dates}")
    print(f"   Dates failed: {failed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill performance_metrics table')
    parser.add_argument('--fund', help='Only backfill for specific fund')
    parser.add_argument('--from-date', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--to-date', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    from_date = datetime.strptime(args.from_date, '%Y-%m-%d').date() if args.from_date else None
    to_date = datetime.strptime(args.to_date, '%Y-%m-%d').date() if args.to_date else None
    
    backfill_performance_metrics(
        fund_filter=args.fund,
        from_date=from_date,
        to_date=to_date
    )
