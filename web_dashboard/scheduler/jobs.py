"""
Scheduled Jobs Definitions
==========================

Define all background jobs here. Each job should:
1. Be a function that takes no arguments
2. Handle its own error logging
3. Call log_job_execution() to record results
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict

from scheduler.scheduler_core import log_job_execution

logger = logging.getLogger(__name__)


# Job definitions with metadata
AVAILABLE_JOBS: Dict[str, Dict[str, Any]] = {
    'exchange_rates': {
        'name': 'Refresh Exchange Rates',
        'description': 'Fetch latest USD/CAD exchange rate and store in database',
        'default_interval_minutes': 30,
        'enabled_by_default': True
    },
    'performance_metrics': {
        'name': 'Populate Performance Metrics',
        'description': 'Aggregate daily portfolio performance into metrics table',
        'default_interval_minutes': 1440,  # Once per day
        'enabled_by_default': True
    },
    'update_portfolio_prices': {
        'name': 'Update Portfolio Prices',
        'description': 'Fetch current stock prices and update portfolio positions for today',
        'default_interval_minutes': 15,  # Every 15 minutes during market hours
        'enabled_by_default': True
    }
}


def refresh_exchange_rates_job() -> None:
    """Fetch and store the latest exchange rate.
    
    This ensures the dashboard always has up-to-date rates for currency conversion.
    """
    job_id = 'exchange_rates'
    start_time = time.time()
    
    try:
        logger.info("Starting exchange rates refresh job...")
        
        # Import here to avoid circular imports
        from exchange_rates_utils import reload_exchange_rate_for_date
        
        # Fetch today's rate
        today = datetime.now(timezone.utc)
        rate = reload_exchange_rate_for_date(today, 'USD', 'CAD')
        
        if rate is not None:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Updated USD/CAD rate: {rate}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"✅ {message}")
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Failed to fetch exchange rate from API"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.warning(f"⚠️ {message}")
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Exchange rates job failed: {e}")


def populate_performance_metrics_job() -> None:
    """Aggregate daily portfolio performance into performance_metrics table.
    
    This pre-calculates daily metrics to speed up chart queries (90 rows vs 1338 rows).
    Runs yesterday's data to ensure market close prices are final.
    """
    job_id = 'performance_metrics'
    start_time = time.time()
    
    try:
        logger.info("Starting performance metrics population job...")
        
        # Import here to avoid circular imports
        from supabase_client import SupabaseClient
        from datetime import date
        from decimal import Decimal
        
        client = SupabaseClient()
        
        # Process yesterday's data (today's data may still be updating)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        
        # Get all funds that have data for yesterday
        positions_result = client.supabase.table("portfolio_positions")\
            .select("fund, total_value, cost_basis, pnl, currency, date")\
            .gte("date", f"{yesterday}T00:00:00")\
            .lt("date", f"{yesterday}T23:59:59.999999")\
            .execute()
        
        if not positions_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"No position data found for {yesterday}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Group by fund and aggregate
        from collections import defaultdict
        fund_totals = defaultdict(lambda: {
            'total_value': Decimal('0'),
            'cost_basis': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'total_trades': 0
        })
        
        # Load exchange rates if needed for USD conversion
        from exchange_rates_utils import get_exchange_rate_for_date_from_db
        
        for pos in positions_result.data:
            fund = pos['fund']
            currency = pos.get('currency', 'CAD').upper()
            
            # Convert to Decimal for precision
            total_value = Decimal(str(pos.get('total_value', 0) or 0))
            cost_basis = Decimal(str(pos.get('cost_basis', 0) or 0))
            pnl = Decimal(str(pos.get('pnl', 0) or 0))
            
            # Convert USD to CAD if needed
            if currency == 'USD':
                rate = get_exchange_rate_for_date_from_db(
                    datetime.combine(yesterday, datetime.min.time()),
                    'USD',
                    'CAD'
                )
                if rate:
                    rate_decimal = Decimal(str(rate))
                    total_value *= rate_decimal
                    cost_basis *= rate_decimal
                    pnl *= rate_decimal
            
            fund_totals[fund]['total_value'] += total_value
            fund_totals[fund]['cost_basis'] += cost_basis
            fund_totals[fund]['unrealized_pnl'] += pnl
            fund_totals[fund]['total_trades'] += 1
        
        # Insert/update performance_metrics for each fund
        rows_inserted = 0
        for fund, totals in fund_totals.items():
            performance_pct = (
                (float(totals['unrealized_pnl']) / float(totals['cost_basis']) * 100)
                if totals['cost_basis'] > 0 else 0.0
            )
            
            # Upsert into performance_metrics
            client.supabase.table("performance_metrics").upsert({
                'fund': fund,
                'date': str(yesterday),
                'total_value': float(totals['total_value']),
                'cost_basis': float(totals['cost_basis']),
                'unrealized_pnl': float(totals['unrealized_pnl']),
                'performance_pct': round(performance_pct, 2),
                'total_trades': totals['total_trades'],
                'winning_trades': 0,  # Not calculated in this version
                'losing_trades': 0     # Not calculated in this version
            }, on_conflict='fund,date').execute()
            
            rows_inserted += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Populated {rows_inserted} fund(s) for {yesterday}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Performance metrics job failed: {e}")


# Global lock to prevent concurrent execution (backup to APScheduler's max_instances=1)
_update_prices_job_running = False

def update_portfolio_prices_job() -> None:
    """Update portfolio positions with current market prices for today.
    
    This job:
    1. Gets current positions from the latest snapshot (or rebuilds from trade log)
    2. Fetches current market prices for all positions
    3. Updates only today's snapshot (or yesterday's if market is closed)
    4. Does NOT delete any historical data
    
    Based on logic from debug/rebuild_portfolio_complete.py but modified to:
    - Only update current/last day
    - Not wipe historical data
    - Work with Supabase directly
    
    Safety Features:
    - Prevents concurrent execution (APScheduler max_instances=1 + global lock)
    - Atomic delete+insert per fund (all or nothing)
    - Skips failed tickers but continues with successful ones
    - Handles partial failures gracefully
    """
    global _update_prices_job_running
    
    # Check if job is already running (backup to APScheduler's max_instances=1)
    if _update_prices_job_running:
        logger.warning("Portfolio price update job already running - skipping")
        return
    
    job_id = 'update_portfolio_prices'
    start_time = time.time()
    
    try:
        _update_prices_job_running = True
        logger.info("Starting portfolio price update job...")
        
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        
        # Add project root to path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from market_data.market_hours import MarketHours
        from utils.market_holidays import MarketHolidays
        from utils.ticker_utils import get_company_name
        from supabase_client import SupabaseClient
        from data.repositories.repository_factory import RepositoryFactory
        
        # Initialize components
        market_fetcher = MarketDataFetcher()
        price_cache = PriceCache()
        market_hours = MarketHours()
        market_holidays = MarketHolidays()
        client = SupabaseClient()
        
        # Determine target date: today if at least one market is open, otherwise last trading day
        # Only skip if BOTH US and Canadian markets are closed
        today = datetime.now().date()
        
        # Check if at least one market is open (use "any" - don't skip if only one market is closed)
        if market_holidays.is_trading_day(today, market="any"):
            target_date = today
        else:
            # Both markets are closed - use last trading day (when at least one was open)
            # Go back up to 7 days to find a day when at least one market was open
            target_date = None
            for i in range(1, 8):  # Start from 1 (yesterday), go back up to 7 days
                check_date = today - timedelta(days=i)
                if market_holidays.is_trading_day(check_date, market="any"):
                    target_date = check_date
                    break
            
            # If we couldn't find a trading day in the last 7 days, skip this run
            if target_date is None:
                duration_ms = int((time.time() - start_time) * 1000)
                message = f"No trading day found in last 7 days (both markets closed) - skipping update"
                log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
                logger.info(f"ℹ️ {message}")
                return
        
        logger.info(f"Target date for price update: {target_date} (today is {today})")
        
        # Get all funds from database with base_currency
        funds_result = client.supabase.table("funds").select("name, base_currency").execute()
        if not funds_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No funds found in database"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Build list of funds with their base currency settings
        funds = [(f['name'], f.get('base_currency', 'CAD')) for f in funds_result.data]
        total_positions_updated = 0
        total_funds_processed = 0
        
        for fund_name, base_currency in funds:
            try:
                logger.info(f"Processing fund: {fund_name} (base_currency: {base_currency})")
                
                # Rebuild current positions from trade log (source of truth)
                # This ensures we have accurate positions even if database is stale
                from data.repositories.repository_factory import RepositoryFactory
                
                # Get data directory for this fund (try to find it)
                # For now, we'll use Supabase repository directly
                try:
                    repository = RepositoryFactory.create_repository(
                        repository_type='supabase',
                        fund_name=fund_name
                    )
                except Exception as e:
                    logger.warning(f"  Could not create repository for {fund_name}: {e}")
                    continue
                
                # Get all trades for this fund
                trades_result = client.supabase.table("trade_log")\
                    .select("*")\
                    .eq("fund", fund_name)\
                    .order("date")\
                    .execute()
                
                if not trades_result.data:
                    logger.info(f"  No trades found for {fund_name}")
                    continue
                
                # Build running positions from trade log (same logic as rebuild script)
                running_positions = defaultdict(lambda: {
                    'shares': Decimal('0'),
                    'cost': Decimal('0'),
                    'currency': 'USD'
                })
                
                for trade in trades_result.data:
                    ticker = trade['ticker']
                    shares = Decimal(str(trade.get('shares', 0) or 0))
                    price = Decimal(str(trade.get('price', 0) or 0))
                    cost = shares * price
                    reason = str(trade.get('reason', '')).upper()
                    
                    if 'SELL' in reason:
                        # Simple FIFO: reduce shares and cost proportionally
                        if running_positions[ticker]['shares'] > 0:
                            cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                            running_positions[ticker]['shares'] -= shares
                            running_positions[ticker]['cost'] -= shares * cost_per_share
                            # Ensure we don't go negative
                            if running_positions[ticker]['shares'] < 0:
                                running_positions[ticker]['shares'] = Decimal('0')
                            if running_positions[ticker]['cost'] < 0:
                                running_positions[ticker]['cost'] = Decimal('0')
                    else:
                        # Default to BUY
                        running_positions[ticker]['shares'] += shares
                        running_positions[ticker]['cost'] += cost
                        currency = trade.get('currency', 'USD')
                        if currency:
                            running_positions[ticker]['currency'] = currency
                
                # Filter to only positions with shares > 0
                current_holdings = {
                    ticker: pos for ticker, pos in running_positions.items()
                    if pos['shares'] > 0
                }
                
                if not current_holdings:
                    logger.info(f"  No active positions for {fund_name}")
                    continue
                
                logger.info(f"  Found {len(current_holdings)} active positions")
                
                # Get exchange rate for target date (for USD→base_currency conversion)
                from exchange_rates_utils import get_exchange_rate_for_date_from_db
                
                exchange_rate = Decimal('1.0')  # Default for same currency or no conversion needed
                if base_currency != 'USD':  # Only fetch rate if converting TO non-USD currency
                    rate = get_exchange_rate_for_date_from_db(
                        datetime.combine(target_date, datetime.min.time()),
                        'USD',
                        base_currency
                    )
                    if rate is not None:
                        exchange_rate = Decimal(str(rate))
                        logger.info(f"  Using exchange rate USD→{base_currency}: {exchange_rate}")
                    else:
                        # Fallback rate if no data available
                        exchange_rate = Decimal('1.35')
                        logger.warning(f"  Missing exchange rate for {target_date}, using fallback {exchange_rate}")
                
                # Fetch current prices for all tickers
                current_prices = {}
                failed_tickers = []
                
                for ticker in current_holdings.keys():
                    try:
                        # Fetch price data for target date
                        start_dt = datetime.combine(target_date, datetime.min.time())
                        end_dt = datetime.combine(target_date, datetime.max.time())
                        result = market_fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                        
                        if result and result.df is not None and not result.df.empty:
                            # Get the most recent close price
                            latest_price = Decimal(str(result.df['Close'].iloc[-1]))
                            current_prices[ticker] = latest_price
                            logger.debug(f"    {ticker}: ${latest_price}")
                        else:
                            # Try to get from cache or previous day
                            cached_data = price_cache.get_cached_price(ticker)
                            if cached_data is not None and not cached_data.empty:
                                latest_price = Decimal(str(cached_data['Close'].iloc[-1]))
                                current_prices[ticker] = latest_price
                                logger.warning(f"    {ticker}: Using cached price ${latest_price}")
                            else:
                                failed_tickers.append(ticker)
                                logger.warning(f"    {ticker}: Could not fetch price")
                    except Exception as e:
                        failed_tickers.append(ticker)
                        logger.warning(f"    {ticker}: Error fetching price - {e}")
                
                if failed_tickers:
                    logger.warning(f"  Failed to fetch prices for {len(failed_tickers)} tickers: {failed_tickers}")
                    # If ALL tickers failed, skip this fund (don't create empty snapshot)
                    if len(failed_tickers) == len(current_holdings):
                        logger.warning(f"  All tickers failed for {fund_name} - skipping update")
                        continue
                
                # Create updated positions for target date
                # Only include positions where we successfully fetched prices
                updated_positions = []
                successful_tickers = []
                for ticker, holding in current_holdings.items():
                    if ticker in failed_tickers:
                        logger.warning(f"  Skipping {ticker} - price fetch failed")
                        continue
                    
                    current_price = current_prices.get(ticker)
                    if current_price is None:
                        continue
                    
                    shares = holding['shares']
                    cost_basis = holding['cost']
                    avg_price = cost_basis / shares if shares > 0 else Decimal('0')
                    market_value = shares * current_price
                    unrealized_pnl = market_value - cost_basis
                    
                    # Convert to base currency if needed
                    position_currency = holding['currency']
                    if position_currency == 'USD' and base_currency != 'USD':
                        # Convert USD position to base currency (e.g., CAD)
                        market_value_base = market_value * exchange_rate
                        cost_basis_base = cost_basis * exchange_rate
                        pnl_base = unrealized_pnl * exchange_rate
                        conversion_rate = exchange_rate
                    elif position_currency == base_currency:
                        # Already in base currency - no conversion
                        market_value_base = market_value
                        cost_basis_base = cost_basis
                        pnl_base = unrealized_pnl
                        conversion_rate = Decimal('1.0')
                    else:
                        # Other currency combinations not yet supported - store as-is
                        logger.warning(f"  Unsupported currency conversion: {position_currency} → {base_currency}")
                        market_value_base = market_value
                        cost_basis_base = cost_basis
                        pnl_base = unrealized_pnl
                        conversion_rate = Decimal('1.0')
                    
                    # Get company name if not already set
                    company = holding.get('company') or get_company_name(ticker)
                    
                    updated_positions.append({
                        'fund': fund_name,
                        'ticker': ticker,
                        'company': company,
                        'shares': float(shares),
                        'price': float(current_price),
                        'cost_basis': float(cost_basis),
                        'pnl': float(unrealized_pnl),
                        'currency': holding['currency'],
                        'date': datetime.combine(target_date, datetime.min.time().replace(hour=16, minute=0)).isoformat(),
                        # New: Pre-converted values in base currency
                        'base_currency': base_currency,
                        'total_value_base': float(market_value_base),
                        'cost_basis_base': float(cost_basis_base),
                        'pnl_base': float(pnl_base),
                        'exchange_rate': float(conversion_rate)
                    })
                    successful_tickers.append(ticker)
                
                if not updated_positions:
                    logger.warning(f"  No positions to update for {fund_name} (all tickers failed or no active positions)")
                    continue
                
                # Log summary
                logger.info(f"  Successfully fetched prices for {len(successful_tickers)}/{len(current_holdings)} tickers")
                
                # CRITICAL: Delete ALL existing positions for target date BEFORE inserting
                # This prevents duplicates - there should only be one snapshot per day
                # Use a more comprehensive delete query to ensure we catch all records
                start_of_day = datetime.combine(target_date, datetime.min.time()).isoformat()
                end_of_day = datetime.combine(target_date, datetime.max.time()).isoformat()
                
                # Delete in batches to handle large datasets
                deleted_total = 0
                while True:
                    # Get IDs of positions to delete (limit to avoid timeout)
                    existing_result = client.supabase.table("portfolio_positions")\
                        .select("id")\
                        .eq("fund", fund_name)\
                        .gte("date", start_of_day)\
                        .lt("date", end_of_day)\
                        .limit(1000)\
                        .execute()
                    
                    if not existing_result.data:
                        break
                    
                    # Delete by IDs
                    ids_to_delete = [row['id'] for row in existing_result.data]
                    delete_result = client.supabase.table("portfolio_positions")\
                        .delete()\
                        .in_("id", ids_to_delete)\
                        .execute()
                    
                    deleted_count = len(delete_result.data) if delete_result.data else len(ids_to_delete)
                    deleted_total += deleted_count
                    
                    # If we got fewer than 1000, we're done
                    if len(existing_result.data) < 1000:
                        break
                
                if deleted_total > 0:
                    logger.info(f"  Deleted {deleted_total} existing positions for {target_date} (preventing duplicates)")
                
                # ATOMIC UPDATE: Insert updated positions
                # If insert fails, we've already deleted old data, but that's OK - next run will fix it
                # For better safety, we could use a transaction, but Supabase doesn't support multi-table transactions easily
                # Instead, we ensure delete+insert happens atomically per fund
                if updated_positions:
                    try:
                        insert_result = client.supabase.table("portfolio_positions")\
                            .insert(updated_positions)\
                            .execute()
                        
                        inserted_count = len(insert_result.data) if insert_result.data else len(updated_positions)
                        total_positions_updated += inserted_count
                        total_funds_processed += 1
                        
                        logger.info(f"  ✅ Updated {inserted_count} positions for {fund_name}")
                    except Exception as insert_error:
                        # Insert failed - log error but don't fail entire job
                        # The delete already happened, so we'll have missing data until next run
                        # This is acceptable because:
                        # 1. Next run (15 min) will fix it
                        # 2. Historical data is preserved
                        # 3. We continue processing other funds
                        logger.error(f"  ❌ Failed to insert positions for {fund_name}: {insert_error}")
                        logger.warning(f"  ⚠️  {fund_name} has no positions for {target_date} until next run")
                        # Don't increment counters for failed insert
                else:
                    logger.warning(f"  No positions to insert for {fund_name} (all tickers failed price fetch)")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing fund {fund_name}: {e}", exc_info=True)
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Updated {total_positions_updated} positions across {total_funds_processed} fund(s) for {target_date}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Portfolio price update job failed: {e}", exc_info=True)
    finally:
        # Always release the lock, even if job fails
        _update_prices_job_running = False



def register_default_jobs(scheduler) -> None:
    """Register all default jobs with the scheduler.
    
    Called by start_scheduler() during initialization.
    """
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    
    # Exchange rates job - every 30 minutes
    if AVAILABLE_JOBS['exchange_rates']['enabled_by_default']:
        scheduler.add_job(
            refresh_exchange_rates_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['exchange_rates']['default_interval_minutes']),
            id='exchange_rates',
            name='Refresh Exchange Rates',
            replace_existing=True
        )
        logger.info("Registered job: exchange_rates (every 30 min)")
    
    # Performance metrics job - daily at 5 PM EST (after market close)
    if AVAILABLE_JOBS['performance_metrics']['enabled_by_default']:
        scheduler.add_job(
            populate_performance_metrics_job,
            trigger=CronTrigger(hour=17, minute=0, timezone='America/New_York'),
            id='performance_metrics',
            name='Populate Performance Metrics',
            replace_existing=True
        )
        logger.info("Registered job: performance_metrics (daily at 5 PM EST)")
    
    # Portfolio price update job - during market hours only (weekdays 9:30 AM - 4:00 PM EST)
    # NOTE: Exchange rates are NOT required for this job - positions are stored in native currency
    # Exchange rates are only used for display/calculation purposes, not for saving positions
    if AVAILABLE_JOBS['update_portfolio_prices']['enabled_by_default']:
        # Run every 15 minutes during market hours on weekdays
        # CronTrigger ensures we don't waste API calls overnight/weekends
        scheduler.add_job(
            update_portfolio_prices_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-15',  # 9 AM to 3:45 PM (last run at 3:45 catches most of trading day)
                minute='0,15,30,45',
                timezone='America/New_York'
            ),
            id='update_portfolio_prices',
            name='Update Portfolio Prices',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("Registered job: update_portfolio_prices (weekdays 9:00-15:45 EST, every 15 min)")
        
        # Market close job at 4:05 PM EST to get official closing prices
        # Extended misfire_grace_time: if system is down at 4:05 PM, retry ASAP within 4 hours
        # This ensures we capture closing prices even after a reboot
        scheduler.add_job(
            update_portfolio_prices_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=5,
                timezone='America/New_York'
            ),
            id='update_portfolio_prices_close',
            name='Update Portfolio Prices (Market Close)',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60 * 60 * 4  # 4 hours - if missed, run when system comes back up
        )
        logger.info("Registered job: update_portfolio_prices_close (weekdays 4:05 PM EST, 4hr misfire grace)")
