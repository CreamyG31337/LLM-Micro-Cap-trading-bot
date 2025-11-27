#!/usr/bin/env python3
"""
Check what dates have portfolio data in Supabase.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / 'web_dashboard' / '.env')

from data.repositories.supabase_repository import SupabaseRepository
from display.console_output import print_info, print_warning, print_success, print_error


def check_supabase_dates(fund_name: str = "Project Chimera", start_date: str = None, end_date: str = None):
    """
    Check what dates have portfolio data in Supabase.
    
    Args:
        fund_name: Fund name to check
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
    """
    print(f"Checking Supabase portfolio data for fund: {fund_name}")
    print("=" * 60)
    
    try:
        # Create Supabase repository
        supabase_repo = SupabaseRepository(fund_name=fund_name)
        
        # Get all portfolio data
        print_info("Loading portfolio data from Supabase...")
        all_snapshots = supabase_repo.get_portfolio_data()
        
        if not all_snapshots:
            print_warning("No portfolio data found in Supabase")
            return
        
        print_success(f"Found {len(all_snapshots)} portfolio snapshots")
        print()
        
        # Group by date
        dates_data = defaultdict(list)
        for snapshot in all_snapshots:
            date_key = snapshot.timestamp.date()
            dates_data[date_key].append({
                'timestamp': snapshot.timestamp,
                'positions': len(snapshot.positions),
                'total_value': snapshot.total_value
            })
        
        # Sort dates
        sorted_dates = sorted(dates_data.keys())
        
        # Filter by date range if provided
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            sorted_dates = [d for d in sorted_dates if d >= start]
        
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            sorted_dates = [d for d in sorted_dates if d <= end]
        
        print_info(f"Portfolio data dates (showing {len(sorted_dates)} dates):")
        print()
        
        # Show dates around the problematic period
        problem_start = datetime(2025, 11, 18).date()
        problem_end = datetime(2025, 11, 26).date()
        
        print(f"Dates from {problem_start} to {problem_end}:")
        print("-" * 60)
        
        for date_key in sorted_dates:
            if problem_start <= date_key <= problem_end:
                snapshots_for_date = dates_data[date_key]
                for snap in snapshots_for_date:
                    print(f"  {date_key}: {snap['positions']} positions, total_value=${snap['total_value']:.2f}, timestamp={snap['timestamp']}")
        
        print()
        print_info("All dates with portfolio data:")
        print("-" * 60)
        
        for date_key in sorted_dates[-20:]:  # Show last 20 dates
            snapshots_for_date = dates_data[date_key]
            for snap in snapshots_for_date:
                print(f"  {date_key}: {snap['positions']} positions, total_value=${snap['total_value']:.2f}")
        
        # Check for missing dates in the problem period
        print()
        print_info("Checking for missing dates in problem period:")
        print("-" * 60)
        
        from market_data.market_hours import MarketHours
        from config.settings import get_settings
        
        settings = get_settings()
        market_hours = MarketHours(settings=settings)
        
        current_date = problem_start
        missing_dates = []
        while current_date <= problem_end:
            if market_hours.is_trading_day(current_date):
                if current_date not in dates_data:
                    missing_dates.append(current_date)
                    print_warning(f"  MISSING: {current_date} (trading day)")
                else:
                    print_success(f"  EXISTS: {current_date}")
            current_date += timedelta(days=1)
        
        if missing_dates:
            print()
            print_warning(f"Found {len(missing_dates)} missing trading days: {missing_dates}")
        else:
            print()
            print_success("All trading days in the period have data")
        
    except Exception as e:
        print_error(f"Error checking Supabase: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check what dates have portfolio data in Supabase")
    parser.add_argument(
        "--fund",
        type=str,
        default="Project Chimera",
        help="Fund name (default: Project Chimera)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    check_supabase_dates(fund_name=args.fund, start_date=args.start_date, end_date=args.end_date)


if __name__ == "__main__":
    main()

