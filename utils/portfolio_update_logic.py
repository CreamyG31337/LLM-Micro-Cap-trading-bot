"""
Portfolio update logic utilities.

This module provides centralized logic for determining when portfolio updates
are needed, with smart market hours awareness and timestamp checking.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Tuple, Optional

from market_data.market_hours import MarketHours
from portfolio.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


class PortfolioUpdateLogic:
    """
    Centralized logic for determining when portfolio updates are needed.
    
    This class provides smart logic that:
    - Respects market hours
    - Checks timestamps to avoid unnecessary updates
    - Works for both same-day and next-day scenarios
    - Can be used from anywhere in the system
    """
    
    def __init__(self, market_hours: MarketHours, portfolio_manager: PortfolioManager):
        """
        Initialize the portfolio update logic.
        
        Args:
            market_hours: MarketHours instance for market status checking
            portfolio_manager: PortfolioManager instance for getting portfolio data
        """
        self.market_hours = market_hours
        self.portfolio_manager = portfolio_manager
        self.market_close_time = time(16, 0)  # 4:00 PM EST
    
    def should_update_portfolio(self, target_date: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Determine if portfolio should be updated based on smart logic.
        
        Core Principle: "Get data whenever we can"
        - Only skip if: (1) not a trading day, OR (2) we already have market close data
        - Market being closed = opportunity to get official close prices (16:00 timestamp)
        - Market being open = opportunity to get live prices (current timestamp)
        
        Args:
            target_date: Optional specific date to check (defaults to today)
            
        Returns:
            Tuple of (should_update: bool, reason: str)
        """
        today = (target_date or datetime.now()).date()
        latest_snapshot = self.portfolio_manager.get_latest_portfolio()
        
        if not latest_snapshot:
            # No existing data - check if today is a trading day
            if self.market_hours.is_trading_day(today):
                return True, "No existing portfolio data - today is a trading day, update needed"
            else:
                return False, f"No existing portfolio data - today ({today.strftime('%A')}) is not a trading day"
        
        last_update_date = latest_snapshot.timestamp.date()
        
        # Check if we need to catch up on missing trading days
        if last_update_date < today:
            # Find all trading days between last update and today
            missing_trading_days = []
            current_date = last_update_date + timedelta(days=1)
            while current_date < today:
                if self.market_hours.is_trading_day(current_date):
                    missing_trading_days.append(current_date)
                current_date += timedelta(days=1)
            
            if missing_trading_days:
                return True, f"Refreshing prices for today"
            else:
                # No missing trading days, check if today is a trading day
                if self.market_hours.is_trading_day(today):
                    return self._check_today_update_needed(latest_snapshot, today)
                else:
                    return False, f"No missing trading days and today ({today.strftime('%A')}) is not a trading day"
        else:
            # Last update was today or in the future
            if last_update_date == today and self.market_hours.is_trading_day(today):
                # Check if market is currently open
                if self.market_hours.is_market_open():
                    # Market is open - always update for live prices
                    return True, f"Market is open - updating for live prices"
                else:
                    # Market is closed - check if we have a market close snapshot
                    snapshot_time = latest_snapshot.timestamp.time()
                    print(f"DEBUG: Snapshot time: {snapshot_time}, Market close time: {self.market_close_time}")
                    print(f"DEBUG: snapshot_time >= market_close_time: {snapshot_time >= self.market_close_time}")
                    if snapshot_time >= self.market_close_time:
                        # We have a market close snapshot - don't overwrite it
                        return False, f"Portfolio was updated today ({today.strftime('%A')}) with market close data - no update needed"
                    else:
                        # We have an intraday snapshot but market is closed - update to get market close prices
                        return True, f"Market is closed - updating to get market close prices"
            else:
                return False, f"Portfolio was updated on {last_update_date.strftime('%Y-%m-%d')} - no update needed"
    
    def _check_today_update_needed(self, latest_snapshot, today) -> Tuple[bool, str]:
        """
        Check if today's update is needed based on market status and timestamps.
        
        Args:
            latest_snapshot: Latest portfolio snapshot
            today: Today's date
            
        Returns:
            Tuple of (should_update: bool, reason: str)
        """
        # Check if today is a trading day
        if not self.market_hours.is_trading_day(today):
            return False, f"Today ({today.strftime('%A')}) is not a trading day"
        
        # Check if market is currently open
        if self.market_hours.is_market_open():
            return True, f"Market is open - updating for live prices"
        
        # Market is closed - check if we have recent market close data
        if latest_snapshot and latest_snapshot.timestamp:
            snapshot_date = latest_snapshot.timestamp.date()
            snapshot_time = latest_snapshot.timestamp.time()
            
            # Check if we have today's market close data
            if snapshot_date == today and snapshot_time >= self.market_close_time:
                return False, f"Already have today's market close data - no update needed"
            
            # Check if we have yesterday's market close data (and market hasn't opened today)
            if snapshot_date < today and snapshot_time >= self.market_close_time:
                return False, f"Have previous day's close data and market hasn't opened - no update needed"
            
            # We have old data but not from market close
            return True, f"Need to update with market close prices"
        
        # No existing data
        return True, f"No existing data - update needed"
    
    def get_update_reason(self, target_date: Optional[datetime] = None) -> str:
        """
        Get a human-readable reason for why an update is or isn't needed.
        
        Args:
            target_date: Optional specific date to check (defaults to today)
            
        Returns:
            String describing the update status
        """
        should_update, reason = self.should_update_portfolio(target_date)
        return reason


# Convenience functions for easy use throughout the system
def should_update_portfolio(market_hours: MarketHours, portfolio_manager: PortfolioManager, target_date: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Convenience function to check if portfolio should be updated.
    
    Args:
        market_hours: MarketHours instance
        portfolio_manager: PortfolioManager instance
        target_date: Optional specific date to check
        
    Returns:
        Tuple of (should_update: bool, reason: str)
    """
    logic = PortfolioUpdateLogic(market_hours, portfolio_manager)
    return logic.should_update_portfolio(target_date)


def get_update_reason(market_hours: MarketHours, portfolio_manager: PortfolioManager, target_date: Optional[datetime] = None) -> str:
    """
    Convenience function to get update reason.
    
    Args:
        market_hours: MarketHours instance
        portfolio_manager: PortfolioManager instance
        target_date: Optional specific date to check
        
    Returns:
        String describing the update status
    """
    logic = PortfolioUpdateLogic(market_hours, portfolio_manager)
    return logic.get_update_reason(target_date)
