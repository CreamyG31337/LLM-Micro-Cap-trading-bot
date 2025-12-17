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
        
        # Get absolute paths
        project_root = Path(__file__).resolve().parent.parent.parent
        project_root_str = str(project_root)
        
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        # Also add web_dashboard to path
        web_dashboard_path = str(Path(__file__).resolve().parent.parent)
        if web_dashboard_path not in sys.path:
            sys.path.insert(0, web_dashboard_path)
        
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
        
        # 3. Check both job completion AND data existence for each trading day
        #    This ensures we re-run if EITHER:
        #    - Job didn't complete successfully (crashed/failed/missing)
        #    - Data is missing even though job says "completed"
        today = datetime.now().date()
        missing_days = []
        
        current = earliest_trade_date
        while current <= today:
            # Only check trading days (market="any" = either US or Canada open)
            if market_holidays.is_trading_day(current, market="any"):
                # Check 1: Did the job complete successfully?
                job_completed = is_job_completed('update_portfolio_prices', current)
                
                # Check 2: Does portfolio data actually exist for this date?
                # Query for ANY portfolio_positions record on this date for ANY production fund
                data_exists = False
                try:
                    # Check if we have portfolio data for this date
                    # Use a simple count query (fast)
                    start_of_day = datetime.combine(current, datetime.min.time()).isoformat()
                    end_of_day = datetime.combine(current, datetime.max.time()).isoformat()
                    
                    result = client.supabase.table("portfolio_positions")\
                        .select("id", count='exact')\
                        .gte("date", start_of_day)\
                        .lt("date", end_of_day)\
                        .in_("fund", fund_names)\
                        .limit(1)\
                        .execute()
                    
                    # If count > 0, data exists
                    data_exists = (result.count and result.count > 0)
                    logger.debug(f"Date {current}: job_completed={job_completed}, data_exists={data_exists} (count={result.count})")
                except Exception as e:
                    logger.warning(f"Could not check data existence for {current}: {e}")
                    # If check fails, treat as missing data (safe default)
                    data_exists = False
                
                # Re-run if job incomplete OR data missing
                # This handles:
                # - Crashed jobs (job incomplete)
                # - Failed jobs (job incomplete)
                # - Missing jobs (job incomplete)
                # - Data wiped (data missing even if job says complete)
                if not job_completed or not data_exists:
                    missing_days.append(current)
                    if job_completed and not data_exists:
                        logger.info(f"   {current}: Job completed but data missing - will re-run")
                    elif not job_completed and data_exists:
                        logger.info(f"   {current}: Data exists but job incomplete - will re-run")
                    elif not job_completed and not data_exists:
                        logger.info(f"   {current}: Both job and data missing - will re-run")
            current += timedelta(days=1)
        
        if not missing_days:
            logger.info("✅ All trading days have completed jobs AND data - no backfill needed")
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
