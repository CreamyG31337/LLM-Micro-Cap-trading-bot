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
        
        # Check if we need to refresh portfolio prices
        detector = MissingTradingDayDetector(market_hours, portfolio_manager)
        
        if market_hours.is_market_open():
            if verbose:
                print("🔄 Market is open - refreshing portfolio prices for current market data")
            needs_update = True
            reason = "Market is open - refreshing prices"
        else:
            # Market is closed - check if we need to update based on missing trading days
            needs_update, missing_days, most_recent = detector.check_for_missing_trading_days()
            if needs_update:
                if verbose:
                    print(f"🔄 Missing trading days detected: {missing_days} - refreshing to get official market close prices")
                reason = f"Missing trading days: {missing_days}"
            else:
                if verbose:
                    print("ℹ️ Market is closed and portfolio is up to date - using existing market close prices")
                reason = "Portfolio is up to date"
                return False, reason
        
        if not needs_update:
            return False, reason
        
        # Refresh portfolio prices
        latest_snapshot = portfolio_manager.get_latest_portfolio()
        if not latest_snapshot or not latest_snapshot.positions:
            if verbose:
                print("⚠️  No portfolio positions found to refresh")
            return False, "No positions to refresh"
        
        if verbose:
            print(f"💰 Refreshing prices for {len(latest_snapshot.positions)} positions...")
        
        # Update prices for all positions
        updated_positions = []
        success_count = 0
        
        for position in latest_snapshot.positions:
            try:
                current_price = market_data_fetcher.get_current_price(position.ticker)
                if current_price:
                    # Update position with current market data
                    position.current_price = current_price
                    position.market_value = current_price * position.shares
                    position.unrealized_pnl = position.market_value - position.cost_basis
                    updated_positions.append(position)
                    success_count += 1
                    if verbose:
                        print(f"✅ {position.ticker}: ${current_price:.2f}")
                else:
                    if verbose:
                        print(f"⚠️  {position.ticker}: Could not fetch current price")
                    updated_positions.append(position)  # Keep existing data
            except Exception as e:
                if verbose:
                    print(f"⚠️  {position.ticker}: Error fetching price - {e}")
                updated_positions.append(position)  # Keep existing data
        
        # Save updated snapshot
        if updated_positions:
            updated_snapshot = latest_snapshot
            updated_snapshot.positions = updated_positions
            updated_snapshot.timestamp = datetime.now()
            
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
