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
                print(f"🔄 {reason}")
        else:
            if verbose:
                print(f"ℹ️ {reason}")
            return False, reason
        
        if not needs_update:
            return False, reason
        
        # Refresh portfolio prices using PriceService
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if not latest_snapshot or not latest_snapshot.positions:
            if verbose:
                print("⚠️  No portfolio positions found to refresh")
            return False, "No positions to refresh"
        
        if verbose:
            print(f"💰 Refreshing prices for {len(latest_snapshot.positions)} positions...")
        
        # Initialize PriceService
        from utils.price_service import PriceService
        price_service = PriceService(
            market_data_fetcher=market_data_fetcher,
            price_cache=price_cache,
            market_hours=market_hours
        )
        
        # Update prices for all positions (uses current prices, not historical)
        updated_positions, _, success_count = price_service.update_positions_with_prices(
            positions=latest_snapshot.positions,
            use_historical=False,  # Use current prices only
            verbose=verbose
        )
        
        # Save updated snapshot
        if updated_positions:
            # Create a NEW snapshot for today with updated prices
            # Don't modify the existing snapshot object to avoid reference issues
            from data.models.portfolio import PortfolioSnapshot
            from datetime import timezone
            
            # Check if market is closed - if so, use market close time (16:00)
            # Otherwise, use current time (can be overwritten later)
            current_time = datetime.now(timezone.utc)
            is_market_closed = not market_hours.is_market_open()
            
            if is_market_closed:
                # Use market close time (16:00:00 UTC) for final snapshot
                snapshot_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
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
                        print(f"ℹ️ Market close snapshot already exists, skipping update")
                    return False, "Market close snapshot already exists"
            
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=snapshot_time
            )
            
            repository.update_daily_portfolio_snapshot(updated_snapshot)
            if verbose:
                print(f"✅ Portfolio data refreshed successfully ({success_count}/{len(updated_positions)} prices updated)")
            
            return True, f"Updated {success_count} positions"
        else:
            return False, "No positions to update"
            
    except Exception as e:
        error_msg = f"Failed to refresh portfolio prices: {e}"
        if verbose:
            print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False, error_msg
