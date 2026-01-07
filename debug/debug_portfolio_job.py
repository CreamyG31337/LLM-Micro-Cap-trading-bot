#!/usr/bin/env python3
"""
Debug Script for Portfolio Price Job
====================================

This script runs the exact same code as the scheduler job for debugging purposes.
Run it from the project root directory.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Add web_dashboard to path
web_dashboard_path = Path(__file__).parent.parent / "web_dashboard"
sys.path.insert(0, str(web_dashboard_path))

# Now import the job function
from scheduler.jobs_portfolio import backfill_portfolio_prices_range

if __name__ == "__main__":
    print("🔍 Debug: Running portfolio price backfill job locally")
    print("=" * 60)
    
    # Use the same date range from the logs
    from_date = date(2025, 12, 17)
    to_date = date(2026, 1, 7)
    
    print(f"Date range: {from_date} to {to_date}")
    print(f"Starting backfill...")
    print("=" * 60)
    
    try:
        # Call the exact same function the scheduler calls
        backfill_portfolio_prices_range(from_date, to_date)
        print("\n" + "=" * 60)
        print("✅ Backfill completed - check output above for details")
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
