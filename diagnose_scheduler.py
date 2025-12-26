#!/usr/bin/env python3
"""
Diagnostic Script: Market Data Jobs Investigation
==================================================

This script tests market hours detection logic and scheduler status
to diagnose why market data jobs are not running on December 26, 2025.
"""

import sys
from pathlib import Path
from datetime import date, datetime

# Add parent directory to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

web_dashboard_path = project_root / "web_dashboard"
sys.path.insert(0, str(web_dashboard_path))

print("=" * 70)
print("MARKET DATA JOBS DIAGNOSTIC")
print("=" * 70)
print()

# Test 1: Market Hours Detection
print("[1/4] Testing Market Hours Detection for December 26, 2025")
print("-" * 70)

try:
    from utils.market_holidays import MarketHolidays
    
    mh = MarketHolidays()
    test_date = date(2025, 12, 26)  # Friday, December 26, 2025
    
    print(f"Test date: {test_date.strftime('%A, %B %d, %Y')}")
    print()
    
    # Test individual market closures
    us_closed = mh.is_us_market_closed(test_date)
    canadian_closed = mh.is_canadian_market_closed(test_date)
    
    print(f"  US market closed:       {us_closed}")
    print(f"  Canadian market closed: {canadian_closed}")
    print()
    
    # Test trading day logic with different market parameters
    print("  Trading day checks:")
    print(f"    market='us':       {mh.is_trading_day(test_date, market='us')}")
    print(f"    market='canadian': {mh.is_trading_day(test_date, market='canadian')}")
    print(f"    market='both':     {mh.is_trading_day(test_date, market='both')}")
    print(f"    market='any':      {mh.is_trading_day(test_date, market='any')}")  # Used by jobs
    print()
    
    # Check holiday name
    holiday_name = mh.get_holiday_name(test_date)
    if holiday_name:
        print(f"  Holiday: {holiday_name}")
    else:
        print(f"  Holiday: None")
    print()
    
    # Expected result
    expected = not us_closed or not canadian_closed  # At least one market open
    actual = mh.is_trading_day(test_date, market='any')
    
    if actual == expected:
        print("  [PASS] market='any' logic is CORRECT")
        print(f"     Expected: {expected}, Got: {actual}")
    else:
        print("  [FAIL] market='any' logic is BROKEN")
        print(f"     Expected: {expected}, Got: {actual}")
    
    print()
    
except Exception as e:
    print(f"  [ERROR] {e}")

    import traceback
    traceback.print_exc()
    print()

# Test 2: Scheduler Status
print("[2/4] Checking Scheduler Status")
print("-" * 70)

try:
    from scheduler import get_scheduler
    from scheduler.scheduler_core import get_all_jobs_status
    
    scheduler = get_scheduler()
    
    print(f"  Scheduler running: {scheduler.running}")
    
    if scheduler.running:
        jobs = scheduler.get_jobs()
        print(f"  Registered jobs:   {len(jobs)}")
        print()
        
        if jobs:
            print("  Job list:")
            for job in jobs:
                print(f"    - {job.id}: {job.name}")
                if job.next_run_time:
                    print(f"      Next run: {job.next_run_time}")
                else:
                    print(f"      Next run: PAUSED")
        print()
    else:
        print("  [WARNING] Scheduler is NOT RUNNING")
        print()
        
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 3: Job Configuration
print("[3/4] Checking Job Configuration")
print("-" * 70)

try:
    from scheduler.jobs import AVAILABLE_JOBS
    
    print(f"  Total jobs configured: {len(AVAILABLE_JOBS)}")
    print()
    
    # Check market data jobs specifically
    market_data_jobs = [
        'update_portfolio_prices',
        'market_research',
        'ticker_research',
        'opportunity_discovery'
    ]
    
    for job_id in market_data_jobs:
        if job_id in AVAILABLE_JOBS:
            job_config = AVAILABLE_JOBS[job_id]
            enabled = job_config.get('enabled_by_default', False)
            status = "[ENABLED]" if enabled else "[DISABLED]"
            print(f"  {job_id}: {status}")
        else:
            print(f"  {job_id}: [NOT FOUND]")
    
    print()
    
except Exception as e:
    print(f"  [ERROR] {e}")
    import traceback
    traceback.print_exc()
    print()

# Test 4: Recent Job Executions
print("[4/4] Checking Recent Job Executions")
print("-" * 70)

try:
    from supabase_client import SupabaseClient
    
    client = SupabaseClient(use_service_role=True)
    
    # Query recent job executions (last 24 hours)
    cutoff_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = client.supabase.table("job_executions")\
        .select("job_name, status, completed_at")\
        .gte("completed_at", cutoff_time.isoformat())\
        .order("completed_at", desc=True)\
        .limit(10)\
        .execute()
    
    if result.data:
        print(f"  Recent executions (last 24h): {len(result.data)}")
        print()
        for record in result.data[:5]:
            job_name = record.get('job_name', 'Unknown')
            status = record.get('status', 'Unknown')
            completed_at = record.get('completed_at', 'Unknown')
            status_icon = "[OK]" if status == "success" else "[FAIL]"
            print(f"    {status_icon} {job_name}: {completed_at}")
        print()
    else:
        print("  [WARNING] No job executions found in last 24 hours")
        print()
        print("  This confirms the bug - jobs are NOT running!")
        print()
        
except Exception as e:
    print(f"  [WARNING] Could not check job executions: {e}")

    print()

# Summary
print("=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print()
print("Next steps:")
print("  1. Review the output above to identify the root cause")
print("  2. If scheduler is not running, start it via Admin UI or code")
print("  3. If market='any' logic is broken, fix MarketHolidays class")
print("  4. If jobs are disabled, enable them in AVAILABLE_JOBS config")
print()
