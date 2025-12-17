"""
Portfolio refresh utilities with smart price update logic.

This module provides a centralized function for refreshing portfolio prices
with intelligent logic that prevents overwriting good market close prices
with after-hours trading data.
"""

from typing import Tuple, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging
import pandas as pd
from display.console_output import _safe_emoji

logger = logging.getLogger(__name__)


def _get_historical_price_for_date(ticker: str, target_date, market_data_fetcher) -> Optional[float]:
    """
    Get historical closing price for a ticker on a specific date.
    
    This uses the same logic as the rebuild script to fetch historical prices.
    
    Args:
        ticker: Stock ticker symbol
        target_date: datetime.date object for the target date
        market_data_fetcher: MarketDataFetcher instance
        
    Returns:
        Historical close price as float, or None if not available
    """
    try:
        # Try multiple date ranges to find available data
        date_ranges = [
            (target_date, target_date + timedelta(days=1)),  # Exact day
            (target_date - timedelta(days=1), target_date + timedelta(days=2)),  # 3-day window
            (target_date - timedelta(days=3), target_date + timedelta(days=4)),  # 7-day window
        ]
        
        for start_date, end_date in date_ranges:
            result = market_data_fetcher.fetch_price_data(ticker, pd.Timestamp(start_date), pd.Timestamp(end_date))
            df = result.df
            
            if df is not None and not df.empty and 'Close' in df.columns and result.source != "empty":
                # Find row matching the target date or closest available
                day_rows = df[df.index.date == target_date]
                if not day_rows.empty:
                    return float(day_rows['Close'].iloc[0])
                # If no exact match, try to find closest date within range
                available_dates = df.index.date
                closest_dates = [d for d in available_dates if d <= target_date]
                if closest_dates:
                    closest_date = max(closest_dates)
                    closest_rows = df[df.index.date == closest_date]
                    if not closest_rows.empty:
                        return float(closest_rows['Close'].iloc[0])
        
        return None
    except Exception as e:
        logger.debug(f"Error fetching historical price for {ticker}: {e}")
        return None


def _create_historical_snapshots_for_missing_days(
    data_dir_path: Path,
    market_hours,
    portfolio_manager,
    repository,
    market_data_fetcher,
    verbose: bool = True
) -> None:
    """
    Create historical portfolio snapshots for ACTUAL missing trading days only.
    
    Requirements:
    1. Weekends/Holidays: Do NOT create snapshots (will be forward-filled in graph)
    2. Missing Trading Days: Create snapshots with REAL historical prices from API
    
    This uses the same historical price fetching logic as the rebuild script.
    
    CRITICAL: Always checks existing dates from repository interface, NOT from CSV files.
    This ensures the function works correctly with all repository backends (CSV, Supabase, etc.).
    
    Args:
        data_dir_path: Path to the data directory (used for fallback only)
        market_hours: MarketHours instance
        portfolio_manager: PortfolioManager instance
        repository: Repository instance (MUST use this to check existing data)
        market_data_fetcher: MarketDataFetcher instance
        verbose: Whether to print status messages
    """
    try:
        from utils.missing_trading_days import MissingTradingDayDetector
        
        detector = MissingTradingDayDetector(market_hours, portfolio_manager)
        needs_update, missing_days, most_recent = detector.check_for_missing_trading_days()
        
        if not needs_update or not missing_days:
            if verbose:
                logger.info("No missing trading days detected")
            return
        
        # CRITICAL: Always check existing dates from the repository, NOT from CSV files directly
        # This ensures the backfill works correctly with both CSV and Supabase repositories.
        # 
        # BUG PREVENTION: Reading CSV directly violates the repository pattern and causes bugs:
        # - When using Supabase, CSV may be out of date or non-existent
        # - After creating snapshots, CSV won't reflect new data until written
        # - Repository.get_portfolio_data() always returns current data from the active backend
        #
        # Always use: repository.get_portfolio_data() to check existing snapshots
        # Never use: pd.read_csv() or direct file access to check existing data
        try:
            existing_snapshots = repository.get_portfolio_data()
            existing_dates = {snapshot.timestamp.date() for snapshot in existing_snapshots}
            if verbose:
                logger.info(f"Found {len(existing_dates)} existing dates in repository")
        except Exception as e:
            logger.warning(f"Could not check repository for existing dates: {e}, falling back to CSV check")
            # Fallback to CSV check ONLY if repository check fails (should be rare)
            # This is a last resort - repository.get_portfolio_data() should always work
            csv_path = Path(data_dir_path) / "llm_portfolio_update.csv"
            if csv_path.exists():
                portfolio_df = pd.read_csv(csv_path)
                # Parse dates handling timezone info (PDT/PST)
                def parse_date_with_tz(date_str):
                    if pd.isna(date_str):
                        return pd.NaT
                    date_str = str(date_str).strip()
                    if " PDT" in date_str:
                        date_str = date_str.replace(" PDT", "").strip()
                    elif " PST" in date_str:
                        date_str = date_str.replace(" PST", "").strip()
                    return pd.to_datetime(date_str, errors='coerce')
                
                portfolio_df['Parsed_Date'] = portfolio_df['Date'].apply(parse_date_with_tz)
                
                def extract_date(dt_value):
                    if pd.isna(dt_value):
                        return None
                    if hasattr(dt_value, 'date'):
                        return dt_value.date()
                    return None
                
                existing_dates = set(filter(None, portfolio_df['Parsed_Date'].apply(extract_date).unique()))
            else:
                existing_dates = set()
        
        # Filter to only truly missing trading days (days with NO data in repository) and are trading days
        truly_missing_days = [day for day in missing_days if (day not in existing_dates and market_hours.is_trading_day(day))]
        
        if not truly_missing_days:
            if verbose:
                logger.info("No trading days need backfill - only weekends/holidays missing or already present")
            return
        
        if verbose:
            logger.info(f"Backfilling {len(truly_missing_days)} missing TRADING days with historical prices...")
            print(f"{_safe_emoji('🔄')} Backfilling {len(truly_missing_days)} missing TRADING days with historical prices...")
            
            # Import job tracking for completion detection
            from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
            
            # Process historical prices for each missing day
        
        # Get the latest portfolio positions to work with
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if not latest_snapshot or not latest_snapshot.positions:
            if verbose:
                logger.warning("No portfolio positions found to create historical snapshots")
            return
        
        # Create snapshots for each truly missing trading day
        # IMPORTANT: Each day gets its own snapshot with that day's unique historical prices
        # This prevents the bug where consecutive trading days show identical values
        for missing_day in truly_missing_days:
            try:
                if verbose:
                    print(f"   Creating snapshot for {missing_day.strftime('%Y-%m-%d')}...")
                
                # Create a new snapshot for this historical day
                historical_positions = []
                
                for position in latest_snapshot.positions:
                    # Get historical price for this position on this day
                    # Convert missing_day to date if it's a datetime
                    target_date = missing_day.date() if hasattr(missing_day, 'date') else missing_day
                    
                    try:
                        # Use the same historical price fetching logic as the rebuild script
                        historical_price = _get_historical_price_for_date(position.ticker, target_date, market_data_fetcher)
                        
                        if historical_price:
                            # Create updated position with historical price and proper calculations
                            from data.models.portfolio import Position
                            from decimal import Decimal
                            
                            hist_price_decimal = Decimal(str(historical_price))
                            market_value = position.shares * hist_price_decimal
                            unrealized_pnl = market_value - position.cost_basis
                            
                            historical_position = Position(
                                ticker=position.ticker,
                                shares=position.shares,
                                avg_price=position.avg_price,
                                cost_basis=position.cost_basis,
                                current_price=hist_price_decimal,
                                market_value=market_value,
                                unrealized_pnl=unrealized_pnl,
                                currency=position.currency,
                                company=position.company
                            )
                            historical_positions.append(historical_position)
                            if verbose:
                                print(f"     {position.ticker}: ${historical_price:.2f} (value: ${market_value:.2f}, PnL: ${unrealized_pnl:.2f})")
                        else:
                            # Keep existing position data if no historical price found
                            historical_positions.append(position)
                            if verbose:
                                print(f"     {position.ticker}: No historical price found, using last known")
                            
                    except Exception as e:
                        # Keep existing position data if there's an error
                        historical_positions.append(position)
                        if verbose:
                            print(f"     {position.ticker}: Error fetching historical price - {e}")
                
                # Create historical snapshot
                from data.models.portfolio import PortfolioSnapshot
                # Create timestamp for market close on the missing day
                if hasattr(missing_day, 'date'):
                    snapshot_date = missing_day.date()  # missing_day is datetime
                else:
                    snapshot_date = missing_day  # missing_day is already date
                    
                # Use proper timezone handling for historical snapshots
                # Market closes at 16:00 ET (Eastern Time)
                from market_config import _is_dst
                from datetime import timezone as dt_timezone
                utc_now = datetime.now(dt_timezone.utc)
                is_dst = _is_dst(utc_now)
                # 16:00 ET = 20:00 UTC during EDT, 21:00 UTC during EST
                market_close_hour_utc = 20 if is_dst else 21

                # Create timestamp for market close in Eastern timezone
                historical_timestamp = datetime.combine(
                    snapshot_date,
                    datetime.min.time().replace(hour=market_close_hour_utc, minute=0, second=0, microsecond=0)
                ).replace(tzinfo=dt_timezone.utc)
                
                historical_snapshot = PortfolioSnapshot(
                    positions=historical_positions,
                    timestamp=historical_timestamp
                )
                
                # Track job start
                fund_name = getattr(portfolio_manager, 'fund', None)
                fund_name_str = fund_name.name if hasattr(fund_name, 'name') else 'console_refresh'
                mark_job_started('portfolio_refresh', snapshot_date, fund_name_str)
                
                try:
                    # Save historical snapshot
                    repository.save_portfolio_snapshot(historical_snapshot)
                    if verbose:
                        logger.info(f"Created snapshot for {missing_day.strftime('%Y-%m-%d')} with {len(historical_positions)} positions")
                        print(f"     Created snapshot for {missing_day.strftime('%Y-%m-%d')} with {len(historical_positions)} positions")
                    
                    # Mark job as completed
                    mark_job_completed('portfolio_refresh', snapshot_date, fund_name_str, [fund_name_str])
                except Exception as save_error:
                    # Mark job as failed
                    mark_job_failed('portfolio_refresh', snapshot_date, fund_name_str, str(save_error))
                    raise
                
            except Exception as e:
                if verbose:
                    print(f"     Error creating snapshot for {missing_day.strftime('%Y-%m-%d')}: {e}")
                logger.error(f"Error creating snapshot for {missing_day}: {e}")
        
        if verbose:
            logger.info("Completed creating historical snapshots for missing trading days")
            print("Completed creating historical snapshots for missing trading days")
        
    except Exception as e:
        error_msg = f"Error creating historical snapshots: {e}"
        if verbose:
            print(f"Warning: {error_msg}")
        logger.error(error_msg, exc_info=True)


def refresh_portfolio_prices_if_needed(
    market_hours,
    portfolio_manager,
    repository,
    market_data_fetcher=None,
    price_cache=None,
    verbose: bool = True
) -> Tuple[bool, str]:
    """
    Smart portfolio price refresh with intelligent update logic.
    
    Price Refresh Strategy:
    - During market hours: Always refresh with live prices for real-time accuracy
    - After market close: Only refresh if missing today's data (gets official close prices)
    - Prevents overwriting good market close prices with after-hours trading data
    
    Core Principle: "Get data whenever we can"
    - Uses centralized logic from utils.portfolio_update_logic
    - Only skips if: (1) not a trading day, OR (2) we already have market close data
    - Market being closed = opportunity to get official close prices (16:00 timestamp)
    
    Args:
        market_hours: MarketHours instance for market status
        portfolio_manager: PortfolioManager instance
        repository: Repository instance for saving updates
        market_data_fetcher: Optional MarketDataFetcher instance
        price_cache: Optional PriceCache instance
        verbose: Whether to print status messages
        
    Returns:
        Tuple of (was_updated: bool, reason: str)
    """
    try:
        # Initialize components if not provided
        if market_data_fetcher is None:
            from market_data.data_fetcher import MarketDataFetcher
            from market_data.price_cache import PriceCache
            if price_cache is None:
                price_cache = PriceCache()
            market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
        
        # Use centralized portfolio update logic
        from utils.portfolio_update_logic import should_update_portfolio
        
        needs_update, reason = should_update_portfolio(market_hours, portfolio_manager)
        
        if needs_update:
            if verbose:
                print(f"{_safe_emoji('🔄')} {reason}")
        else:
            if verbose:
                print(f"{_safe_emoji('ℹ️')} {reason}")
            return False, reason
        
        if not needs_update:
            return False, reason
        
        # STEP 1: Backfill missing trading days with historical prices
        # This ensures we have complete data before refreshing current prices
        #
        # NOTE: We need data_dir_path only for the fallback CSV check (if repository check fails).
        # The primary data check uses repository.get_portfolio_data() which works with all backends.
        # Get data directory from repository (for fallback CSV parsing only)
        try:
            data_dir_path = None
            # Try to get from repository directly
            if hasattr(repository, 'data_dir'):
                data_dir_path = Path(repository.data_dir)
            elif hasattr(repository, 'data_directory'):
                data_dir_path = Path(repository.data_directory)
            # Try to get from CSV repo if repository is a wrapper
            elif hasattr(repository, 'csv_repo'):
                if hasattr(repository.csv_repo, 'data_dir'):
                    data_dir_path = Path(repository.csv_repo.data_dir)
                elif hasattr(repository.csv_repo, 'data_directory'):
                    data_dir_path = Path(repository.csv_repo.data_directory)
            # Try to get from portfolio manager's fund
            elif hasattr(portfolio_manager, 'fund') and hasattr(portfolio_manager.fund, 'repository'):
                repo_settings = portfolio_manager.fund.repository.settings
                if 'data_directory' in repo_settings:
                    data_dir_path = Path(repo_settings['data_directory'])
            
            if data_dir_path and data_dir_path.exists():
                # Check for missing trading days and backfill them
                from utils.missing_trading_days import MissingTradingDayDetector
                detector = MissingTradingDayDetector(market_hours, portfolio_manager)
                needs_backfill, missing_days, _ = detector.check_for_missing_trading_days()
                
                if needs_backfill and missing_days:
                    if verbose:
                        logger.info(f"Detected {len(missing_days)} missing trading days, backfilling historical snapshots...")
                    
                    # Backfill missing trading days
                    _create_historical_snapshots_for_missing_days(
                        data_dir_path=data_dir_path,
                        market_hours=market_hours,
                        portfolio_manager=portfolio_manager,
                        repository=repository,
                        market_data_fetcher=market_data_fetcher,
                        verbose=verbose
                    )
                    
                    # Reload portfolio manager to pick up the backfilled data
                    # This ensures the refresh logic sees the freshly backfilled data
                    from portfolio.portfolio_manager import PortfolioManager
                    from portfolio.fund_manager import Fund, RepositorySettings
                    
                    # Recreate portfolio manager with same fund
                    if hasattr(portfolio_manager, 'fund'):
                        portfolio_manager = PortfolioManager(repository, portfolio_manager.fund)
                    else:
                        # Fallback: try to recreate from repository
                        portfolio_manager = PortfolioManager(repository, None)
                    
                    # Clear price cache to ensure fresh prices are fetched for today
                    # This prevents reusing historical prices from the backfill step
                    if hasattr(price_cache, '_price_cache'):
                        price_cache._price_cache = {}
        except Exception as e:
            # Don't fail the entire refresh if backfill fails
            logger.warning(f"Failed to backfill missing trading days: {e}")
            if verbose:
                print(f"{_safe_emoji('⚠️')} Warning: Could not backfill missing days: {e}")
        
        # STEP 2: Refresh portfolio prices using PriceService
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if not latest_snapshot or not latest_snapshot.positions:
            if verbose:
                print(f"{_safe_emoji('⚠️')}  No portfolio positions found to refresh")
            return False, "No positions to refresh"
        
        if verbose:
            print(f"{_safe_emoji('💰')} Refreshing prices for {len(latest_snapshot.positions)} positions...")
        
        # Initialize PriceService
        from utils.price_service import PriceService
        price_service = PriceService(
            market_data_fetcher=market_data_fetcher,
            price_cache=price_cache,
            market_hours=market_hours
        )
        
        # Update prices for all positions
        # When market is closed, use historical close prices (official end-of-day)
        # When market is open, use current prices (real-time)
        use_historical = not market_hours.is_market_open()

        # For historical mode, we need to provide start_date and end_date
        if use_historical:
            from utils.timezone_utils import get_current_trading_time
            current_time = get_current_trading_time()
            # Use today as both start and end date for historical close prices
            start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = current_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            start_date = None
            end_date = None

        updated_positions, _, success_count = price_service.update_positions_with_prices(
            positions=latest_snapshot.positions,
            use_historical=use_historical,  # Use historical close prices when market closed
            start_date=start_date,  # Required for historical mode
            end_date=end_date,      # Required for historical mode
            verbose=verbose
        )
        
        # Save updated snapshot
        if updated_positions:
            # Create a NEW snapshot for today with updated prices
            # Don't modify the existing snapshot object to avoid reference issues
            from data.models.portfolio import PortfolioSnapshot
            from datetime import timezone
            
            # Check if market is closed - if so, use market close time in user's timezone
            # Otherwise, use current time (can be overwritten later)
            from utils.timezone_utils import get_current_trading_time
            current_time = get_current_trading_time()  # Gets current time in user's timezone
            is_market_closed = not market_hours.is_market_open()
            
            if is_market_closed:
                # Use market close time in Eastern timezone for proper historical price fetching
                # Market closes at 16:00 ET (Eastern Time)
                # During EDT (March-November): 16:00 ET = 20:00 UTC
                # During EST (November-March): 16:00 ET = 21:00 UTC
                from market_config import _is_dst
                from datetime import timezone as dt_timezone
                utc_now = datetime.now(dt_timezone.utc)
                is_dst = _is_dst(utc_now)
                # 16:00 ET = 20:00 UTC during EDT, 21:00 UTC during EST
                market_close_hour_utc = 20 if is_dst else 21
                
                # FIXED: Create market close time in UTC, then convert to user's timezone
                # This prevents the bug where .replace() on timezone-aware datetime creates wrong date
                current_date = current_time.date()
                market_close_utc = datetime.combine(
                    current_date,
                    datetime.min.time().replace(hour=market_close_hour_utc, minute=0, second=0, microsecond=0)
                ).replace(tzinfo=dt_timezone.utc)
                
                # Convert to user's timezone
                snapshot_time = market_close_utc.astimezone(current_time.tzinfo)
            else:
                # Use current time for intraday snapshot (can be overwritten)
                snapshot_time = current_time
            
            # Check if we should overwrite existing snapshot
            existing_snapshot = portfolio_manager.get_latest_portfolio()
            if existing_snapshot and existing_snapshot.timestamp.date() == snapshot_time.date():
                # Check if existing snapshot is at market close (16:00:00)
                if existing_snapshot.timestamp.hour == 16 and existing_snapshot.timestamp.minute == 0:
                    # Don't overwrite market close snapshot
                    if verbose:
                        print(f"{_safe_emoji('ℹ️')} Market close snapshot already exists, skipping update")
                    return False, "Market close snapshot already exists"
            
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=snapshot_time
            )
            
            repository.update_daily_portfolio_snapshot(updated_snapshot)
            if verbose:
                print(f"{_safe_emoji('✅')} Portfolio data refreshed successfully ({success_count}/{len(updated_positions)} prices updated)")
            
            return True, f"Updated {success_count} positions"
        else:
            return False, "No positions to update"
            
    except Exception as e:
        error_msg = f"Failed to refresh portfolio prices: {e}"
        if verbose:
            print(f"{_safe_emoji('❌')} {error_msg}")
        logger.error(error_msg)
        return False, error_msg
