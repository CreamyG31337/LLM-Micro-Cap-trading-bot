"""
Smart Backfill System for Portfolio Positions
==============================================

Automatically fills gaps in portfolio_positions data between first trade and today.
Runs on scheduler startup to catch downtime/reboots.

USES JOB COMPLETION TRACKING: Checks job_executions table instead of portfolio data
to detect incomplete runs where Docker was stopped mid-job.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


def startup_backfill_check() -> None:
    """
    Smart backfill: Checks job completion status for each trading day.
    Much faster than per-fund checks and detects crashed/failed jobs.
    
    Edge cases handled:
    - New installation (no trades) → Returns immediately
    - Crashed jobs → Detected by status='running' for old dates  
    - Failed jobs → Detected by status='failed'
    - Missing jobs → No record in job_executions
    """
    try:
        # Add project root to path for imports (same pattern as jobs.py)
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from supabase_client import SupabaseClient
        from utils.market_holidays import MarketHolidays
        from scheduler.jobs import update_portfolio_prices_job
        from utils.job_tracking import is_job_completed
        
        # Use service role key to bypass RLS (background job needs full access)
        client = SupabaseClient(use_service_role=True)
        market_holidays = MarketHolidays()

        
        logger.info("🔍 Starting smart backfill check (job completion validation)...")
        
        # 1. Get all production funds to find earliest trade
        funds_result = client.supabase.table("funds")\
            .select("name")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            logger.info("✅ No production funds found - skipping backfill")
            return
        
        fund_names = [f['name'] for f in funds_result.data]
        logger.info(f"   Checking {len(fund_names)} production funds: {fund_names}")
        
        # 2. Find earliest trade across ALL production funds
        earliest_trade_date = None
        for fund_name in fund_names:
            trades_result = client.supabase.table("trade_log")\
                .select("date")\
                .eq("fund", fund_name)\
                .order("date")\
                .limit(1)\
                .execute()
            
            if trades_result.data:
                fund_earliest = pd.to_datetime(trades_result.data[0]['date']).date()
                if earliest_trade_date is None or fund_earliest < earliest_trade_date:
                    earliest_trade_date = fund_earliest
        
        if earliest_trade_date is None:
            logger.info("✅ No trades found - skipping backfill (new installation)")
            return
        
        logger.info(f"   Earliest trade across all funds: {earliest_trade_date}")
        
        # 3. Check job completion status for each trading day
        #    This is MUCH faster than querying portfolio_positions per-fund!
        today = datetime.now().date()
        missing_days = []
        
        current = earliest_trade_date
        while current <= today:
            # Only check trading days (market="any" = either US or Canada open)
            if market_holidays.is_trading_day(current, market="any"):
                # Check if job completed successfully for this date
                # This detects:
                # - Crashed jobs (status='running' for old dates)
                # - Failed jobs (status='failed')
                # - Missing jobs (no record at all)
                if not is_job_completed('update_portfolio_prices', current):
                    missing_days.append(current)
            current += timedelta(days=1)
        
        if not missing_days:
            logger.info("✅ All trading days have completed jobs - no backfill needed")
            return
        
        logger.warning(f"⚠️  Found {len(missing_days)} days with incomplete/missing jobs")
        logger.info(f"   Date range: {missing_days[0]} to {missing_days[-1]}")
        
        # 4. Run job for each missing date
        success_count = 0
        fail_count = 0
        
        for day in missing_days:
            try:
                logger.info(f"   Backfilling {day}...")
                update_portfolio_prices_job(target_date=day)
                success_count += 1
            except Exception as e:
                logger.error(f"   ❌ Failed to backfill {day}: {e}")
                fail_count += 1
                # Continue with next day even if one fails
        
        logger.info(f"✅ Backfill complete: {success_count} succeeded, {fail_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Backfill check failed: {e}", exc_info=True)
        # Don't crash the scheduler if backfill fails
