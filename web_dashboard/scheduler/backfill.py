"""
Smart Backfill System for Portfolio Positions
==============================================

Automatically fills gaps in portfolio_positions data between first trade and today.
Runs on scheduler startup to catch downtime/reboots.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)


def startup_backfill_check() -> None:
    """
    Smart backfill: Only fills gaps between first trade and today.
    Skips weekends/holidays automatically (uses market="any" logic).
    
    Edge cases handled:
    - New installation (no trades) → Returns immediately
    - First trade → Starts from earliest trade date
    - Existing data → Starts from day after last snapshot
    - Weekends/holidays → Automatically skipped
    """
    try:
        # Add project root to path for imports (same pattern as jobs.py)
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from supabase_client import SupabaseClient
        from utils.market_holidays import MarketHolidays
        from scheduler.jobs import update_portfolio_prices_job
        
        client = SupabaseClient()
        market_holidays = MarketHolidays()
        
        logger.info("🔍 Starting smart backfill check...")
        
        # 1. Find earliest trade date across all funds
        trades_result = client.supabase.table("trade_log")\
            .select("date")\
            .order("date")\
            .limit(1)\
            .execute()
        
        if not trades_result.data:
            logger.info("✅ No trades found - skipping backfill (new installation)")
            return
        
        earliest_trade = trades_result.data[0]['date']
        earliest_date = pd.to_datetime(earliest_trade).date()
        logger.info(f"   Earliest trade: {earliest_date}")
        
        # 2. Find latest portfolio snapshot
        positions_result = client.supabase.table("portfolio_positions")\
            .select("date")\
            .order("date", desc=True)\
            .limit(1)\
            .execute()
        
        if positions_result.data:
            latest_snapshot = pd.to_datetime(positions_result.data[0]['date']).date()
            start_backfill = latest_snapshot + timedelta(days=1)
            logger.info(f"   Latest snapshot: {latest_snapshot}")
            logger.info(f"   Start backfill from: {start_backfill}")
        else:
            # No snapshots exist - start from first trade
            start_backfill = earliest_date
            logger.info(f"   No snapshots found - starting from first trade: {start_backfill}")
        
        # 3. Generate list of trading days to backfill
        today = datetime.now().date()
        missing_days = []
        
        current = start_backfill
        while current <= today:
            # Use "any" market logic: run if EITHER US or Canadian market is open
            # This matches the job's logic exactly
            if market_holidays.is_trading_day(current, market="any"):
                missing_days.append(current)
            current += timedelta(days=1)
        
        if not missing_days:
            logger.info("✅ Portfolio data is up to date - no backfill needed")
            return
        
        logger.warning(f"⚠️  Found {len(missing_days)} missing trading days")
        logger.info(f"   Date range: {missing_days[0]} to {missing_days[-1]}")
        
        # 4. Run job for each missing day (job handles all complex logic)
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
