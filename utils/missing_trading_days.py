"""
Missing trading day detection and update logic.

This module provides functionality to detect missing trading days between
the last portfolio update and the current date, and trigger updates for
those missing days. Used across portfolio management, graphing, and
prompt generator screens.

DEPRECATED: Use utils.portfolio_update_logic.PortfolioUpdateLogic instead.
This module is kept for backward compatibility.
"""

import logging
from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple

from market_data.market_hours import MarketHours
from portfolio.portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)


class MissingTradingDayDetector:
    """
    Detects missing trading days and determines if portfolio updates are needed.
    
    DEPRECATED: Use utils.portfolio_update_logic.PortfolioUpdateLogic instead.
    This class is kept for backward compatibility.
    
    Args:
        market_hours: MarketHours instance for trading day detection
        portfolio_manager: PortfolioManager instance for getting latest portfolio data
    """
    
    def __init__(self, market_hours: MarketHours, portfolio_manager: PortfolioManager):
        """
        Initialize the missing trading day detector.
        
        Args:
            market_hours: MarketHours instance for trading day detection
            portfolio_manager: PortfolioManager instance for getting latest portfolio data
        """
        self.market_hours = market_hours
        self.portfolio_manager = portfolio_manager
    
    def check_for_missing_trading_days(self, target_date: Optional[datetime] = None) -> Tuple[bool, List[datetime], Optional[datetime]]:
        """
        Check if there are missing trading days that need to be updated.
        
        Args:
            target_date: Optional specific date to check against (defaults to today)
            
        Returns:
            Tuple of:
            - bool: True if updates are needed, False otherwise
            - List[datetime]: List of missing trading days
            - Optional[datetime]: Most recent missing trading day to update
        """
        today = (target_date or datetime.now()).date()
        latest_snapshot = self.portfolio_manager.get_latest_portfolio()
        
        if not latest_snapshot:
            # No existing data - check if today is a trading day
            if self.market_hours.is_trading_day(today):
                logger.info("No existing portfolio data - today is a trading day, update needed")
                return True, [today], today
            else:
                logger.debug(f"No existing portfolio data - today ({today.strftime('%A')}) is not a trading day")
                return False, [], None
        
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
                most_recent_missing = missing_trading_days[-1]
                logger.info(f"Found {len(missing_trading_days)} missing trading days: {[d.strftime('%Y-%m-%d') for d in missing_trading_days]}")
                logger.info(f"Most recent missing trading day: {most_recent_missing.strftime('%Y-%m-%d')}")
                return True, missing_trading_days, most_recent_missing
            else:
                # No missing trading days, check if today is a trading day AND we need today's data
                if self.market_hours.is_trading_day(today):
                    # Check if we already have today's data
                    if last_update_date < today:
                        # Only update if markets are open
                        if self.market_hours.is_market_open():
                            logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are open - update needed")
                            return True, [today], today
                        else:
                            # Markets are closed - check if we have data from after the most recent market close
                            # This works for both same-day (after 4 PM today) and next-day (3 AM) scenarios
                            latest_snapshot = self.portfolio_manager.get_latest_portfolio()
                            if latest_snapshot and latest_snapshot.timestamp:
                                snapshot_date = latest_snapshot.timestamp.date()
                                snapshot_time = latest_snapshot.timestamp.time()
                                market_close_time = time(16, 0)  # 4:00 PM EST
                                
                                # Check if we have data from after market close on the most recent trading day
                                if snapshot_date == today and snapshot_time >= market_close_time:
                                    # We have data from after today's market close - we're good
                                    logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are closed - we already have post-market-close data from today, skipping update")
                                    return False, [], None
                                elif snapshot_date < today:
                                    # We have data from a previous day - check if it's from after market close
                                    if snapshot_time >= market_close_time:
                                        # We have data from after the previous day's market close - we're good
                                        logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are closed - we already have post-market-close data from {snapshot_date}, skipping update")
                                        return False, [], None
                                    else:
                                        # We have data from before market close on the previous day - we need today's data
                                        logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are closed - we need post-market-close data, update needed")
                                        return True, [today], today
                                else:
                                    # We have data from the future (shouldn't happen) - we're good
                                    logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are closed - we have future data, skipping update")
                                    return False, [], None
                            else:
                                logger.info(f"No missing trading days, but today ({today.strftime('%A')}) is a trading day and markets are closed - no existing data, update needed")
                                return True, [today], today
                    else:
                        logger.debug(f"No missing trading days and today ({today.strftime('%A')}) is a trading day but we already have today's data")
                        return False, [], None
                else:
                    logger.debug(f"No missing trading days and today ({today.strftime('%A')}) is not a trading day")
                    return False, [], None
        else:
            # Last update was today or in the future
            if last_update_date == today and self.market_hours.is_trading_day(today):
                logger.debug(f"Portfolio was updated today ({today.strftime('%A')}) - no update needed")
                return False, [], None
            else:
                logger.debug(f"Portfolio was updated on {last_update_date.strftime('%Y-%m-%d')} - no update needed")
                return False, [], None
    
    def should_skip_due_to_non_trading_day(self, target_date: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Check if the current operation should be skipped due to non-trading day.
        
        Args:
            target_date: Optional specific date to check (defaults to today)
            
        Returns:
            Tuple of:
            - bool: True if should skip, False otherwise
            - str: Reason for skipping (if applicable)
        """
        today = (target_date or datetime.now()).date()
        
        if not self.market_hours.is_trading_day(today):
            reason = f"Non-trading day detected ({today.strftime('%A')}) - no market data available"
            logger.debug(reason)
            return True, reason
        
        return False, ""
    
    def get_update_reason(self, target_date: Optional[datetime] = None) -> str:
        """
        Get a human-readable reason for why an update is or isn't needed.
        
        Args:
            target_date: Optional specific date to check (defaults to today)
            
        Returns:
            String describing the update status
        """
        should_skip, skip_reason = self.should_skip_due_to_non_trading_day(target_date)
        if should_skip:
            return skip_reason
        
        needs_update, missing_days, most_recent = self.check_for_missing_trading_days(target_date)
        
        if needs_update:
            if len(missing_days) == 1 and missing_days[0] == (target_date or datetime.now()).date():
                return "Portfolio update needed (trading day)"
            else:
                return f"Portfolio update needed ({len(missing_days)} missing trading days)"
        else:
            return "Portfolio is up to date"
