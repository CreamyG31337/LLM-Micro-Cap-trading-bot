"""
Portfolio refresh utilities with smart price update logic.

This module provides a centralized function for refreshing portfolio prices
with intelligent logic that prevents overwriting good market close prices
with after-hours trading data.
"""

from typing import Tuple, Optional
from pathlib import Path
from datetime import datetime
import logging
from display.console_output import _safe_emoji

logger = logging.getLogger(__name__)


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
        from utils.missing_trading_days import MissingTradingDayDetector
        
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
        
        # Refresh portfolio prices using PriceService
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
                snapshot_time = current_time.replace(hour=market_close_hour_utc, minute=0, second=0, microsecond=0)
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
