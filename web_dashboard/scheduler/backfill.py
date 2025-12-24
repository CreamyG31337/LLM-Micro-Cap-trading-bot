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
        
        # 3. Find the most recent date where DATA EXISTS (our checkpoint)
        #    We only need to process dates AFTER this checkpoint
        #    Note: We check data existence only, not job completion, because job tracking is newer
        
        # CRITICAL: Use ET timezone for 'today' to match market hours
        # Using server time (UTC) causes wrong date selection on cloud servers
        import pytz
        et = pytz.timezone('America/New_York')
        today = datetime.now(et).date()
        
        checkpoint_date = None
        
        # Start from today and work backwards to find last date with data
        check_date = today
        while check_date >= earliest_trade_date:
            if market_holidays.is_trading_day(check_date, market="any"):
                # Check if portfolio data exists for this date
                try:
                    start_of_day = datetime.combine(check_date, datetime.min.time()).isoformat()
                    end_of_day = datetime.combine(check_date, datetime.max.time()).isoformat()
                    
                    result = client.supabase.table("portfolio_positions")\
                        .select("id", count='exact')\
                        .gte("date", start_of_day)\
                        .lt("date", end_of_day)\
                        .in_("fund", fund_names)\
                        .limit(1)\
                        .execute()
                    
                    data_exists = (result.count and result.count > 0)
                except:
                    data_exists = False
                
                # Found our checkpoint - last date with data!
                if data_exists:
                    checkpoint_date = check_date
                    logger.info(f"   Found checkpoint: {checkpoint_date} (data exists)")
                    break
            
            check_date -= timedelta(days=1)
            
            # Don't search more than 30 days back (performance)
            if (today - check_date).days > 30:
                logger.info("   No data found in last 30 days - will process from earliest trade")
                checkpoint_date = earliest_trade_date - timedelta(days=1)
                break
        
        if checkpoint_date is None:
            # No checkpoint found at all
            checkpoint_date = earliest_trade_date - timedelta(days=1)
            logger.info("   No checkpoint found - will process all dates from earliest trade")
        
        # 4. Now collect all dates AFTER checkpoint that need processing
        missing_days = []
        current = checkpoint_date + timedelta(days=1)  # Start day after checkpoint
        
        # Import market hours for market open check
        from market_data.market_hours import MarketHours
        market_hours = MarketHours()
        
        while current <= today:
            if market_holidays.is_trading_day(current, market="any"):
                # CRITICAL: Skip TODAY if market hasn't opened yet
                # We should NOT create data for a date until the market has opened for that day
                if current == today:
                    now_et = datetime.now(et)
                    market_open_time = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
                    
                    # If it's before 9:30 AM ET, market hasn't opened yet - skip today
                    if now_et < market_open_time:
                        logger.info(f"   {current}: Market hasn't opened yet (current: {now_et.strftime('%I:%M %p ET')}, opens: 9:30 AM ET) - skipping")
                        # Don't add today to missing_days - we'll process it after market opens
                        current += timedelta(days=1)
                        continue
                
                # Check if this date needs processing
                job_completed = is_job_completed('update_portfolio_prices', current)
                
                # Check data existence
                data_exists = False
                try:
                    start_of_day = datetime.combine(current, datetime.min.time()).isoformat()
                    end_of_day = datetime.combine(current, datetime.max.time()).isoformat()
                    
                    result = client.supabase.table("portfolio_positions")\
                        .select("id", count='exact')\
                        .gte("date", start_of_day)\
                        .lt("date", end_of_day)\
                        .in_("fund", fund_names)\
                        .limit(1)\
                        .execute()
                    
                    data_exists = (result.count and result.count > 0)
                except Exception as e:
                    logger.warning(f"Could not check data existence for {current}: {e}")
                    data_exists = False
                
                # Re-run if job incomplete OR data missing
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
