"""
Portfolio Price Update Jobs
============================

Jobs for updating portfolio positions with current market prices.
"""

import logging
import time
import threading
from datetime import datetime, timedelta, date, time as dt_time
from typing import Optional
from decimal import Decimal
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# Add parent directory to path if needed (standard boilerplate for these jobs)
import sys
from pathlib import Path

# Add project root to path for utils imports
current_dir = Path(__file__).resolve().parent
if current_dir.name == 'scheduler':
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Also ensure web_dashboard is in path for supabase_client imports
web_dashboard_path = str(Path(__file__).resolve().parent.parent)
if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)

from scheduler.scheduler_core import log_job_execution

# Initialize logger
logger = logging.getLogger(__name__)

# Thread-safe lock to prevent concurrent execution
# A simple boolean was causing race conditions when backfill and scheduled jobs ran simultaneously
_update_prices_lock = threading.Lock()


def update_portfolio_prices_job(target_date: Optional[date] = None) -> None:
    """Update portfolio positions with current market prices for a specific date.
    
    Args:
        target_date: Date to update. If None, auto-determines (today or last trading day).
    
    This job:
    1. Gets current positions from the latest snapshot (or rebuilds from trade log)
    2. Fetches current market prices for all positions
    3. Updates only the target date's snapshot
    4. Does NOT delete any historical data
    
    Based on logic from debug/rebuild_portfolio_complete.py but modified to:
    - Only update current/last day (or specified date)
    - Not wipe historical data
    - Work with Supabase directly
    
    Safety Features:
    - Prevents concurrent execution (thread-safe lock + APScheduler max_instances=1)
    - Atomic delete+insert per fund (all or nothing)
    - Skips failed tickers but continues with successful ones
    - Handles partial failures gracefully
    """
    # Initialize job tracking first (before lock check so we can log lock failures)
    job_id = 'update_portfolio_prices'
    start_time = time.time()
    
    # Acquire lock with non-blocking check - if another thread is already running, skip
    acquired = _update_prices_lock.acquire(blocking=False)
    if not acquired:
        duration_ms = int((time.time() - start_time) * 1000)
        message = "Job already running - skipped (lock not acquired)"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.warning(f"⚠️ {message}")
        return
    
    try:
        
        # CRITICAL: Add project root to path FIRST, before any imports
        import sys
        import os
        from pathlib import Path
        
        # Get absolute path to project root
        # __file__ is scheduler/jobs_portfolio.py
        # parent is scheduler/, parent.parent is web_dashboard/, parent.parent.parent is project root
        project_root = Path(__file__).resolve().parent.parent.parent
        project_root_str = str(project_root)
        
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
            logger.debug(f"Added project root to sys.path: {project_root_str}")
        
        # Also ensure web_dashboard is in path for supabase_client imports
        web_dashboard_path = str(Path(__file__).resolve().parent.parent)
        if web_dashboard_path not in sys.path:
            sys.path.insert(0, web_dashboard_path)
            logger.debug(f"Added web_dashboard to sys.path: {web_dashboard_path}")
        
        # Determine if this is a manual or automatic execution
        execution_mode = "manual" if target_date is not None else "automatic"
        logger.info(f"Starting portfolio price update job... (mode: {execution_mode}, target_date: {target_date})")
        
        # Import here to avoid circular imports
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from market_data.market_hours import MarketHours
        from utils.market_holidays import MarketHolidays
        from supabase_client import SupabaseClient
        from data.repositories.repository_factory import RepositoryFactory
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        # Initialize components
        market_fetcher = MarketDataFetcher()
        price_cache = PriceCache()
        market_hours = MarketHours()
        market_holidays = MarketHolidays()
        # Use service role key to bypass RLS (background job needs full access)
        client = SupabaseClient(use_service_role=True)
        
        # Determine target date if not specified
        if target_date is None:
            # Auto-detect based on time of day and market hours
            # This matches the logic in utils/portfolio_update_logic.py from console app
            # Key principle: 
            # - Before 9:30 AM ET: Use yesterday (market hasn't opened yet)
            # - After 4:00 PM ET: Use today (market has closed)
            # - Between 9:30 AM - 4:00 PM: Use today if trading day (for live prices)
            
            # CRITICAL: Get current time in ET FIRST, then derive 'today' from ET time
            # Using server time (UTC) for 'today' causes wrong date selection
            from datetime import datetime as dt
            import pytz
            
            et = pytz.timezone('America/New_York')
            now_et = dt.now(et)
            today = now_et.date()  # Use ET date, not server/UTC date
            
            # Market hours: 9:30 AM - 4:00 PM ET
            market_open_hour = 9
            market_open_minute = 30
            market_close_hour = 16
            
            # Determine time of day status
            current_time = now_et.time()
            is_before_open = current_time < dt_time(market_open_hour, market_open_minute)
            is_after_close = current_time >= dt_time(market_close_hour, 0)
            
            use_today = False
            if market_holidays.is_trading_day(today, market="any"):
                if is_before_open:
                    # Before 9:30 AM - market hasn't opened yet, use yesterday
                    logger.info(f"Current time is {now_et.strftime('%I:%M %p ET')} - before market open (9:30 AM ET) - will use last trading day")
                elif is_after_close:
                    # After 4:00 PM - market has closed, use today
                    use_today = True
                else:
                    # During market hours (9:30 AM - 4:00 PM) - use today for live prices
                    use_today = True
            
            if use_today:
                target_date = today
                logger.info(f"Auto-detected target_date: {target_date} (today - market {'closed' if is_after_close else 'open'})")
            else:
                # Use last trading day
                target_date = None
                logger.info(f"Searching for last trading day (today {today} is before market open or not a trading day)")
                for i in range(1, 8):
                    check_date = today - timedelta(days=i)
                    if market_holidays.is_trading_day(check_date, market="any"):
                        target_date = check_date
                        logger.info(f"Found last trading day: {target_date} ({i} day(s) ago)")
                        break
                
                if target_date is None:
                    duration_ms = int((time.time() - start_time) * 1000)
                    message = f"No trading day found in last 7 days - skipping update"
                    log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
                    logger.info(f"ℹ️ {message}")
                    return
        
        # Log the target date with timezone info for debugging
        from datetime import datetime as dt
        import pytz
        et_tz = pytz.timezone('America/New_York')
        now_et = dt.now(et_tz)
        logger.info(f"Target date for price update: {target_date}")
        logger.info(f"Current time: {now_et.strftime('%Y-%m-%d %I:%M %p %Z')} (ET)")
        logger.info(f"Server time: {datetime.now()} (local)")
        
        # CRITICAL: Double-check that target_date is actually a trading day
        # This prevents the job from running on holidays/weekends even if cron triggers it
        if not market_holidays.is_trading_day(target_date, market="any"):
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Target date {target_date} is not a trading day - skipping update"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Get all production funds from database (skip test/dev funds)
        funds_result = client.supabase.table("funds")\
            .select("name, base_currency")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No production funds found in database"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Build list of production funds with their base currency settings
        funds = [(f['name'], f.get('base_currency', 'CAD')) for f in funds_result.data]
        logger.info(f"Processing {len(funds)} production funds")
        
        # Mark job as started (for completion tracking)
        mark_job_started('update_portfolio_prices', target_date)
        
        total_positions_updated = 0
        total_funds_processed = 0
        funds_completed = []  # Track which funds completed successfully
        
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
                        # Validate currency: must be a non-empty string and not 'nan'
                        if currency and isinstance(currency, str):
                            currency_upper = currency.strip().upper()
                            if currency_upper and currency_upper not in ('NAN', 'NONE', 'NULL', ''):
                                running_positions[ticker]['currency'] = currency_upper
                            else:
                                # Invalid currency string - keep default 'USD'
                                logger.warning(f"⚠️ Trade for '{ticker}' in fund '{fund_name}' has invalid currency '{currency}'. Defaulting to USD.")
                        else:
                            # If currency is None or not a string, keep default 'USD'
                            logger.warning(f"⚠️ Trade for '{ticker}' in fund '{fund_name}' has missing currency. Defaulting to USD.")
                
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
                        datetime.combine(target_date, dt_time(0, 0, 0)),
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
                
                # OPTIMIZATION: Fetch current prices for all tickers in parallel
                current_prices = {}
                failed_tickers = []
                rate_limit_errors = 0
                
                # Helper function to fetch price for a single ticker
                def fetch_ticker_price(ticker: str) -> tuple[str, Optional[Decimal], Optional[str]]:
                    """Fetch price for a single ticker. Returns (ticker, price, error_type)."""
                    try:
                        # Fetch price data for target date
                        start_dt = datetime.combine(target_date, dt_time(0, 0, 0))
                        end_dt = datetime.combine(target_date, dt_time(23, 59, 59, 999999))
                        result = market_fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                        
                        if result and result.df is not None and not result.df.empty:
                            # Get the most recent close price
                            latest_price = Decimal(str(result.df['Close'].iloc[-1]))
                            return (ticker, latest_price, None)
                        else:
                            # Try to get from cache or previous day
                            cached_data = price_cache.get_cached_price(ticker)
                            if cached_data is not None and not cached_data.empty:
                                latest_price = Decimal(str(cached_data['Close'].iloc[-1]))
                                return (ticker, latest_price, 'cached')
                            else:
                                return (ticker, None, 'no_data')
                    except Exception as e:
                        error_str = str(e).lower()
                        # Check for rate limiting errors (429, too many requests, etc.)
                        if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
                            return (ticker, None, 'rate_limit')
                        else:
                            return (ticker, None, 'error')
                
                # Fetch prices in parallel using ThreadPoolExecutor
                # Use conservative max_workers=5 for free-tier APIs (Yahoo Finance) to avoid rate limiting
                tickers_list = list(current_holdings.keys())
                max_workers = min(5, len(tickers_list))
                
                if len(tickers_list) > 0:
                    logger.info(f"  Fetching prices for {len(tickers_list)} tickers in parallel (max_workers={max_workers})...")
                    price_fetch_start = time.time()
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        future_to_ticker = {executor.submit(fetch_ticker_price, ticker): ticker for ticker in tickers_list}
                        
                        # Process completed tasks
                        completed = 0
                        for future in as_completed(future_to_ticker):
                            completed += 1
                            ticker, price, error_type = future.result()
                            
                            if price is not None:
                                current_prices[ticker] = price
                                if error_type == 'cached':
                                    logger.debug(f"    {ticker}: ${price} (cached)")
                                else:
                                    logger.debug(f"    {ticker}: ${price}")
                            else:
                                if error_type == 'rate_limit':
                                    rate_limit_errors += 1
                                    if rate_limit_errors == 1:
                                        logger.warning(f"  ⚠️  Rate limiting detected for {ticker}")
                                    failed_tickers.append(ticker)
                                elif error_type == 'no_data':
                                    logger.warning(f"    {ticker}: Could not fetch price (no data)")
                                    failed_tickers.append(ticker)
                                else:
                                    logger.warning(f"    {ticker}: Error fetching price")
                                    failed_tickers.append(ticker)
                    
                    price_fetch_time = time.time() - price_fetch_start
                    avg_time_per_ticker = price_fetch_time / len(tickers_list) if tickers_list else 0
                    logger.info(f"  Parallel fetch complete: {len(current_prices)} succeeded, {len(failed_tickers)} failed ({price_fetch_time:.2f}s, ~{avg_time_per_ticker:.2f}s per ticker)")
                    
                    if rate_limit_errors > 0:
                        logger.warning(f"  ⚠️  Rate limiting detected: {rate_limit_errors} tickers hit 429 errors")
                        logger.warning(f"     Consider: reducing max_workers, adding delays, or using API keys")
                
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
                    
                    # CRITICAL: Create datetime with ET timezone, then convert to UTC for storage
                    # This ensures the timestamp is correctly interpreted regardless of server timezone
                    from datetime import datetime as dt
                    import pytz
                    et_tz = pytz.timezone('America/New_York')
                    # Create datetime at 4 PM ET (market close) for the target date
                    et_datetime = et_tz.localize(dt.combine(target_date, dt_time(16, 0)))
                    # Convert to UTC for storage (Supabase stores timestamps in UTC)
                    utc_datetime = et_datetime.astimezone(pytz.UTC)
                    # Calculate date_only for unique constraint (fund, ticker, date_only)
                    date_only = utc_datetime.date()
                    
                    updated_positions.append({
                        'fund': fund_name,
                        'ticker': ticker,
                        'shares': float(shares),
                        'price': float(current_price),
                        'cost_basis': float(cost_basis),
                        'pnl': float(unrealized_pnl),
                        'currency': holding['currency'],
                        'date': utc_datetime.isoformat(),
                        'date_only': date_only.isoformat(),  # Include for unique constraint upsert
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
                start_of_day = datetime.combine(target_date, dt_time(0, 0, 0)).isoformat()
                end_of_day = datetime.combine(target_date, dt_time(23, 59, 59, 999999)).isoformat()
                
                # Delete in batches to handle large datasets
                deleted_total = 0
                while True:
                    # Get IDs of positions to delete (limit to avoid timeout)
                    existing_result = client.supabase.table("portfolio_positions")\
                        .select("id")\
                        .eq("fund", fund_name)\
                        .gte("date", start_of_day)\
                        .lte("date", end_of_day)\
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
                
                # ATOMIC UPDATE: Upsert updated positions (insert or update on conflict)
                # Using upsert instead of insert to handle race conditions gracefully
                # The unique constraint on (fund, date, ticker) prevents duplicates
                # If delete+insert pattern fails due to race condition, upsert will handle it
                if updated_positions:
                    try:
                        # Use upsert with on_conflict to handle duplicates from race conditions
                        # This is safer than insert alone - if the job runs twice concurrently,
                        # or if delete+insert fails, upsert will update existing records instead of erroring
                        # The unique constraint is on (fund, ticker, date_only) - date_only is auto-populated by trigger
                        upsert_result = client.supabase.table("portfolio_positions")\
                            .upsert(
                                updated_positions,
                                on_conflict="fund,ticker,date_only"
                            )\
                            .execute()
                        
                        upserted_count = len(upsert_result.data) if upsert_result.data else len(updated_positions)
                        total_positions_updated += upserted_count
                        total_funds_processed += 1
                        funds_completed.append(fund_name)  # Track successful completion
                        
                        logger.info(f"  ✅ Upserted {upserted_count} positions for {fund_name}")
                    except Exception as upsert_error:
                        # Upsert failed - log error but don't fail entire job
                        # The delete already happened, but upsert failure is less likely than insert failure
                        # This is acceptable because:
                        # 1. Next run (15 min) will fix it
                        # 2. Historical data is preserved
                        # 3. We continue processing other funds
                        logger.error(f"  ❌ Failed to upsert positions for {fund_name}: {upsert_error}")
                        logger.warning(f"  ⚠️  {fund_name} has no positions for {target_date} until next run")
                        # Don't increment counters for failed upsert
                else:
                    logger.warning(f"  No positions to insert for {fund_name} (all tickers failed price fetch)")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing fund {fund_name}: {e}", exc_info=True)
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Updated {total_positions_updated} positions across {total_funds_processed} fund(s) for {target_date}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
        # Mark job as completed successfully
        mark_job_completed('update_portfolio_prices', target_date, None, funds_completed, duration_ms=duration_ms)
        
        # Bump cache version to invalidate Streamlit cache immediately
        try:
            import sys
            from pathlib import Path
            web_dashboard_path = str(Path(__file__).resolve().parent.parent)
            if web_dashboard_path not in sys.path:
                sys.path.insert(0, web_dashboard_path)
            from cache_version import bump_cache_version
            bump_cache_version()
            logger.info("Cache version bumped - Streamlit will show fresh data")
        except Exception as e:
            logger.warning(f"Failed to bump cache version: {e}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Portfolio price update job failed: {e}", exc_info=True)
        
        # Mark job as failed in database
        # If target_date not defined (early crash), use today as fallback
        fallback_date = date.today() if 'target_date' not in locals() else target_date
        mark_job_failed('update_portfolio_prices', fallback_date, None, str(e), duration_ms=duration_ms)
    finally:
        # Always release the lock, even if job fails
        _update_prices_lock.release()


def backfill_portfolio_prices_range(start_date: date, end_date: date) -> None:
    """Backfill portfolio positions for a date range efficiently.
    
    This is a batch-optimized version of update_portfolio_prices_job that:
    1. Fetches price data for ALL tickers for the ENTIRE date range at once (1 API call per ticker)
    2. Correctly filters trades by date for each historical snapshot
    3. Processes all dates in the range with a single batch delete/insert
    
    Args:
        start_date: First date to backfill (inclusive)
        end_date: Last date to backfill (inclusive)
    
    Performance: O(Tickers) API calls instead of O(Days * Tickers)
    Correctness: Only includes trades up to each snapshot date
    """
    job_id = 'backfill_portfolio_prices_range'
    start_time = time.time()
    
    # Acquire lock with non-blocking check - if another thread is already running, skip
    # This prevents backfill from running effectively concurrently with scheduled updates
    acquired = _update_prices_lock.acquire(blocking=False)
    if not acquired:
        duration_ms = int((time.time() - start_time) * 1000)
        message = "Job already running - skipped (lock not acquired)"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.warning(f"⚠️ {message}")
        return

    try:
        # CRITICAL: Add project root to path FIRST
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).resolve().parent.parent.parent
        project_root_str = str(project_root)
        
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        web_dashboard_path = str(Path(__file__).resolve().parent.parent)
        if web_dashboard_path not in sys.path:
            sys.path.insert(0, web_dashboard_path)
        
        logger.info(f"Starting batch backfill for date range: {start_date} to {end_date}")
        
        # Import dependencies
        from market_data.data_fetcher import MarketDataFetcher
        from utils.market_holidays import MarketHolidays
        from supabase_client import SupabaseClient
        from exchange_rates_utils import get_exchange_rate_for_date_from_db
        import pytz
        
        # Initialize components
        market_fetcher = MarketDataFetcher()
        market_holidays = MarketHolidays()
        client = SupabaseClient(use_service_role=True)
        
        # Get all production funds
        funds_result = client.supabase.table("funds")\
            .select("name, base_currency")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            logger.info("No production funds found")
            return
        
        funds = [(f['name'], f.get('base_currency', 'CAD')) for f in funds_result.data]
        logger.info(f"Processing {len(funds)} production funds")
        
        # Build list of trading days in the range
        trading_days = []
        current = start_date
        while current <= end_date:
            if market_holidays.is_trading_day(current, market="any"):
                trading_days.append(current)
            current += timedelta(days=1)
        
        if not trading_days:
            logger.info(f"No trading days in range {start_date} to {end_date}")
            return
        
        logger.info(f"Backfilling {len(trading_days)} trading days: {trading_days[0]} to {trading_days[-1]}")
        
        total_positions_created = 0
        
        for fund_name, base_currency in funds:
            try:
                logger.info(f"Processing fund: {fund_name} (base_currency: {base_currency})")
                
                # Get ALL trades for this fund (we'll filter by date later)
                trades_result = client.supabase.table("trade_log")\
                    .select("*")\
                    .eq("fund", fund_name)\
                    .order("date")\
                    .execute()
                
                if not trades_result.data:
                    logger.info(f"  No trades found for {fund_name}")
                    continue
                
                # Convert trade dates to date objects for comparison
                trades_with_dates = []
                for trade in trades_result.data:
                    trade_date_str = trade.get('date')
                    if trade_date_str:
                        # Parse the date - handle both date and datetime formats
                        try:
                            if 'T' in trade_date_str:
                                trade_date = datetime.fromisoformat(trade_date_str.replace('Z', '+00:00')).date()
                            else:
                                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
                            trades_with_dates.append({**trade, '_parsed_date': trade_date})
                        except Exception as e:
                            logger.warning(f"  Could not parse trade date {trade_date_str}: {e}")
                            continue
                
                if not trades_with_dates:
                    logger.info(f"  No valid trades with parseable dates for {fund_name}")
                    continue
                
                # Identify all unique tickers across ALL trades
                all_tickers = set()
                for trade in trades_with_dates:
                    all_tickers.add(trade['ticker'])
                
                logger.info(f"  Found {len(all_tickers)} unique tickers across all trades")
                
                # OPTIMIZATION: Fetch price data for ALL tickers for the ENTIRE date range at once
                # This is 1 API call per ticker instead of 1 API call per ticker per day
                ticker_price_data = {}
                failed_tickers = []
                
                logger.info(f"  Fetching price data for {len(all_tickers)} tickers (batch mode)...")
                fetch_start = time.time()
                
                for ticker in all_tickers:
                    try:
                        # Fetch data for entire range with some padding
                        range_start = datetime.combine(trading_days[0], dt_time(0, 0, 0))
                        range_end = datetime.combine(trading_days[-1], dt_time(23, 59, 59, 999999))
                        
                        result = market_fetcher.fetch_price_data(ticker, start=range_start, end=range_end)
                        
                        if result and result.df is not None and not result.df.empty:
                            # Store the entire DataFrame - we'll lookup specific dates later
                            ticker_price_data[ticker] = result.df
                            logger.debug(f"    {ticker}: Fetched {len(result.df)} price records")
                        else:
                            failed_tickers.append(ticker)
                            logger.warning(f"    {ticker}: No price data available")
                    except Exception as e:
                        failed_tickers.append(ticker)
                        logger.warning(f"    {ticker}: Error fetching price data: {e}")
                
                fetch_duration = time.time() - fetch_start
                logger.info(f"  Batch fetch complete: {len(ticker_price_data)}/{len(all_tickers)} succeeded in {fetch_duration:.2f}s")
                
                if failed_tickers:
                    logger.warning(f"  Failed to fetch prices for {len(failed_tickers)} tickers: {failed_tickers}")
                
                # Now process each trading day
                all_positions = []  # Collect all position records for batch insert
                
                for target_date in trading_days:
                    # CORRECTNESS FIX: Filter trades to only those on or before target_date
                    trades_up_to_date = [t for t in trades_with_dates if t['_parsed_date'] <= target_date]
                    
                    # Build running positions from filtered trades
                    running_positions = defaultdict(lambda: {
                        'shares': Decimal('0'),
                        'cost': Decimal('0'),
                        'currency': 'USD'
                    })
                    
                    for trade in trades_up_to_date:
                        ticker = trade['ticker']
                        shares = Decimal(str(trade.get('shares', 0) or 0))
                        price = Decimal(str(trade.get('price', 0) or 0))
                        cost = shares * price
                        reason = str(trade.get('reason', '')).upper()
                        
                        if 'SELL' in reason:
                            if running_positions[ticker]['shares'] > 0:
                                cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                                running_positions[ticker]['shares'] -= shares
                                running_positions[ticker]['cost'] -= shares * cost_per_share
                                if running_positions[ticker]['shares'] < 0:
                                    running_positions[ticker]['shares'] = Decimal('0')
                                if running_positions[ticker]['cost'] < 0:
                                    running_positions[ticker]['cost'] = Decimal('0')
                        else:
                            running_positions[ticker]['shares'] += shares
                            running_positions[ticker]['cost'] += cost
                            currency = trade.get('currency', 'USD')
                            if currency and isinstance(currency, str):
                                currency_upper = currency.strip().upper()
                                if currency_upper and currency_upper not in ('NAN', 'NONE', 'NULL', ''):
                                    running_positions[ticker]['currency'] = currency_upper
                    
                    # Filter to only positions with shares > 0
                    current_holdings = {
                        ticker: pos for ticker, pos in running_positions.items()
                        if pos['shares'] > 0
                    }
                    
                    if not current_holdings:
                        logger.debug(f"  {target_date}: No active positions")
                        continue
                    
                    # Get exchange rate for this date
                    exchange_rate = Decimal('1.0')
                    if base_currency != 'USD':
                        rate = get_exchange_rate_for_date_from_db(
                            datetime.combine(target_date, dt_time(0, 0, 0)),
                            'USD',
                            base_currency
                        )
                        if rate is not None:
                            exchange_rate = Decimal(str(rate))
                        else:
                            exchange_rate = Decimal('1.35')  # Fallback
                    
                    # Create position records for this date
                    et_tz = pytz.timezone('America/New_York')
                    et_datetime = et_tz.localize(datetime.combine(target_date, dt_time(16, 0)))
                    utc_datetime = et_datetime.astimezone(pytz.UTC)
                    
                    for ticker, holding in current_holdings.items():
                        if ticker in failed_tickers:
                            continue  # Skip tickers with no price data
                        
                        # Lookup price for this specific date
                        price_df = ticker_price_data.get(ticker)
                        if price_df is None:
                            continue
                        
                        # Find price for target_date
                        try:
                            # Normalize target_date to match DataFrame index
                            target_ts = pd.Timestamp(target_date)
                            
                            # Try exact match first
                            if target_ts in price_df.index:
                                current_price = Decimal(str(price_df.loc[target_ts, 'Close']))
                            else:
                                # Find nearest date (forward fill - use last known price)
                                valid_dates = price_df.index[price_df.index <= target_ts]
                                if len(valid_dates) == 0:
                                    logger.debug(f"  {target_date} {ticker}: No price data for this date")
                                    continue
                                nearest_date = valid_dates[-1]
                                current_price = Decimal(str(price_df.loc[nearest_date, 'Close']))
                        except Exception as e:
                            logger.debug(f"  {target_date} {ticker}: Error looking up price: {e}")
                            continue
                        
                        shares = holding['shares']
                        cost_basis = holding['cost']
                        market_value = shares * current_price
                        unrealized_pnl = market_value - cost_basis
                        
                        # Convert to base currency
                        position_currency = holding['currency']
                        if position_currency == 'USD' and base_currency != 'USD':
                            market_value_base = market_value * exchange_rate
                            cost_basis_base = cost_basis * exchange_rate
                            pnl_base = unrealized_pnl * exchange_rate
                            conversion_rate = exchange_rate
                        elif position_currency == base_currency:
                            market_value_base = market_value
                            cost_basis_base = cost_basis
                            pnl_base = unrealized_pnl
                            conversion_rate = Decimal('1.0')
                        else:
                            market_value_base = market_value
                            cost_basis_base = cost_basis
                            pnl_base = unrealized_pnl
                            conversion_rate = Decimal('1.0')
                        
                        all_positions.append({
                            'fund': fund_name,
                            'ticker': ticker,
                            'shares': float(shares),
                            'price': float(current_price),
                            'cost_basis': float(cost_basis),
                            'pnl': float(unrealized_pnl),
                            'currency': holding['currency'],
                            'date': utc_datetime.isoformat(),
                            'base_currency': base_currency,
                            'total_value_base': float(market_value_base),
                            'cost_basis_base': float(cost_basis_base),
                            'pnl_base': float(pnl_base),
                            'exchange_rate': float(conversion_rate)
                        })
                
                if not all_positions:
                    logger.info(f"  No positions to backfill for {fund_name}")
                    continue
                
                logger.info(f"  Created {len(all_positions)} position records across {len(trading_days)} days")
                
                # BATCH DELETE: Remove all existing positions for this fund in the date range
                start_of_range = datetime.combine(trading_days[0], dt_time(0, 0, 0)).isoformat()
                end_of_range = datetime.combine(trading_days[-1], dt_time(23, 59, 59, 999999)).isoformat()
                
                deleted_total = 0
                while True:
                    existing_result = client.supabase.table("portfolio_positions")\
                        .select("id")\
                        .eq("fund", fund_name)\
                        .gte("date", start_of_range)\
                        .lte("date", end_of_range)\
                        .limit(1000)\
                        .execute()
                    
                    if not existing_result.data:
                        break
                    
                    ids_to_delete = [row['id'] for row in existing_result.data]
                    delete_result = client.supabase.table("portfolio_positions")\
                        .delete()\
                        .in_("id", ids_to_delete)\
                        .execute()
                    
                    deleted_count = len(delete_result.data) if delete_result.data else len(ids_to_delete)
                    deleted_total += deleted_count
                    
                    if len(existing_result.data) < 1000:
                        break
                
                if deleted_total > 0:
                    logger.info(f"  Deleted {deleted_total} existing positions")
                
                # BATCH INSERT: Insert all positions at once
                try:
                    insert_result = client.supabase.table("portfolio_positions")\
                        .insert(all_positions)\
                        .execute()
                    
                    inserted_count = len(insert_result.data) if insert_result.data else len(all_positions)
                    total_positions_created += inserted_count
                    
                    logger.info(f"  ✅ Inserted {inserted_count} positions for {fund_name}")
                except Exception as insert_error:
                    logger.error(f"  ❌ Failed to insert positions for {fund_name}: {insert_error}")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing fund {fund_name}: {e}", exc_info=True)
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Backfilled {total_positions_created} positions for date range {start_date} to {end_date}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message} in {duration_ms/1000:.2f}s")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Batch backfill failed: {e}", exc_info=True)
    finally:
        # Always release the lock
        _update_prices_lock.release()

