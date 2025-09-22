"""
Market hours and trading day calculations.

This module provides the MarketHours class for determining market status,
trading days, and market timing calculations. Supports configuration for
different market timezones and is designed to work with both current CSV
storage and future database backends.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any

import pandas as pd
import pytz

from config.settings import Settings
from display.console_output import _safe_emoji
from utils.market_holidays import MarketHolidays

logger = logging.getLogger(__name__)


class MarketHours:
    """
    Market timing and trading day calculations.
    
    Handles market open/close detection, trading day calculations,
    and timezone-aware market timing operations.
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize market hours calculator.
        
        Args:
            settings: Optional settings instance for configuration
        """
        self.settings = settings or Settings()
        self._timezone_cache = {}
        self.holidays = MarketHolidays()
    
    def is_market_open(self, target_time: Optional[datetime] = None) -> bool:
        """
        Check if the market is currently open.
        
        Market hours: 6:30 AM to 1:00 PM PST (9:30 AM to 4:00 PM EST)
        Considers weekdays (Monday-Friday) and market holidays.
        
        Args:
            target_time: Optional specific time to check (defaults to now)
            
        Returns:
            True if market is open, False otherwise
        """
        # Get current time in trading timezone
        tz = self.get_trading_timezone()
        now = target_time or datetime.now(tz)
        
        # Ensure we're working in the trading timezone
        if now.tzinfo != tz:
            now = now.astimezone(tz)
        
        # Check if it's a trading day (weekday and not a holiday)
        if not self.holidays.is_trading_day(now.date(), market="both"):
            return False
        
        # Market hours: 6:30 AM to 1:00 PM PST (9:30 AM to 4:00 PM EST)
        market_open = now.replace(hour=6, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=13, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def get_market_open_time(self, date: Optional[datetime] = None) -> datetime:
        """
        Get market open time (6:30 AM) in the configured timezone for the given date.
        
        Args:
            date: Optional date to get market open time for (defaults to today)
            
        Returns:
            Market open time as timezone-aware datetime
        """
        tz = self.get_trading_timezone()
        target_date = date or datetime.now(tz)
        
        # Ensure we're working in the trading timezone
        if target_date.tzinfo != tz:
            target_date = target_date.astimezone(tz)
        
        # Set to market open time (6:30 AM PST)
        market_open_time = target_date.replace(
            hour=6, minute=30, second=0, microsecond=0
        )
        
        return market_open_time
    
    def get_market_close_time(self, date: Optional[datetime] = None) -> datetime:
        """
        Get market close time (1:00 PM) in the configured timezone for the given date.
        
        Args:
            date: Optional date to get market close time for (defaults to today)
            
        Returns:
            Market close time as timezone-aware datetime
        """
        tz = self.get_trading_timezone()
        target_date = date or datetime.now(tz)
        
        # Ensure we're working in the trading timezone
        if target_date.tzinfo != tz:
            target_date = target_date.astimezone(tz)
        
        # Set to market close time (1:00 PM PST)
        market_close_time = target_date.replace(
            hour=13, minute=0, second=0, microsecond=0
        )
        
        return market_close_time
    
    def last_trading_date(self, today: Optional[datetime] = None) -> pd.Timestamp:
        """
        Return last trading date (Mon–Fri), considering market hours.
        
        On Monday before market open (6:30 AM PT), returns Friday.
        On Monday after market open, returns Monday.
        
        Args:
            today: Optional date to calculate from (defaults to now)
            
        Returns:
            Last trading date as pandas Timestamp
        """
        dt = pd.Timestamp(today or self._effective_now())
        
        # If it's Saturday (5) or Sunday (6), go back to Friday
        if dt.weekday() >= 5:
            days_back = dt.weekday() - 4  # Friday is weekday 4
            return dt - pd.Timedelta(days=days_back)
        
        # If it's Monday before market open, return Friday instead
        if dt.weekday() == 0:  # Monday = 0
            market_open = self.get_market_open_time(dt)
            if dt < market_open:
                # Before market open on Monday, use Friday's data
                return dt - pd.Timedelta(days=3)  # Go back 3 days to Friday
        
        # For Tuesday-Friday, or Monday after market open, return as-is
        return dt
    
    def last_trading_date_str(self, today: Optional[datetime] = None) -> str:
        """
        Return last trading date as ISO string.
        
        Args:
            today: Optional date to calculate from (defaults to now)
            
        Returns:
            Last trading date as ISO date string (YYYY-MM-DD)
        """
        return self.last_trading_date(today).date().isoformat()
    
    def trading_day_window(
        self, 
        target: Optional[datetime] = None
    ) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """
        Get [start, end) window for the last trading day (Fri on weekends).
        
        Args:
            target: Optional target date (defaults to now)
            
        Returns:
            Tuple of (start_timestamp, end_timestamp) for the trading day
        """
        trading_date = self.last_trading_date(target)
        start = trading_date.normalize()  # Start of day (00:00:00)
        end = start + pd.Timedelta(days=1)  # Start of next day (exclusive)
        
        return start, end
    
    def get_trading_timezone(self) -> pytz.BaseTzInfo:
        """
        Get the configured trading timezone.
        
        Returns:
            Trading timezone (defaults to US/Pacific)
        """
        tz_name = self.settings.get('timezone.name', 'US/Pacific') if self.settings else "US/Pacific"
        # Normalize common abbreviations to canonical pytz names
        if tz_name in {"PST", "PDT"}:
            tz_name = "US/Pacific"
        
        # Cache timezone objects for performance
        if tz_name not in self._timezone_cache:
            try:
                self._timezone_cache[tz_name] = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone {tz_name}, falling back to US/Pacific")
                self._timezone_cache[tz_name] = pytz.timezone("US/Pacific")
        
        return self._timezone_cache[tz_name]
    
    def get_timezone_name(self) -> str:
        """
        Get the display name for the trading timezone.
        
        Returns:
            Timezone display name (e.g., "PST", "PDT")
        """
        tz = self.get_trading_timezone()
        now = datetime.now(tz)
        return now.strftime("%Z")
    
    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        Check if the given date is a trading day (weekday and not a holiday).
        
        Args:
            date: Optional date to check (defaults to today)
            
        Returns:
            True if it's a trading day, False otherwise
        """
        target_date = date or datetime.now()
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        return self.holidays.is_trading_day(target_date, market="both")
    
    def next_trading_day(self, date: Optional[datetime] = None) -> pd.Timestamp:
        """
        Get the next trading day from the given date.
        
        Args:
            date: Optional starting date (defaults to today)
            
        Returns:
            Next trading day as pandas Timestamp
        """
        start_date = pd.Timestamp(date or datetime.now())
        
        # Start checking from the next day
        next_day = start_date + pd.Timedelta(days=1)
        
        # Keep advancing until we find a weekday
        while next_day.weekday() >= 5:
            next_day += pd.Timedelta(days=1)
        
        return next_day
    
    def previous_trading_day(self, date: Optional[datetime] = None) -> pd.Timestamp:
        """
        Get the previous trading day from the given date.
        
        Args:
            date: Optional starting date (defaults to today)
            
        Returns:
            Previous trading day as pandas Timestamp
        """
        start_date = pd.Timestamp(date or datetime.now())
        
        # Start checking from the previous day
        prev_day = start_date - pd.Timedelta(days=1)
        
        # Keep going back until we find a weekday
        while prev_day.weekday() >= 5:
            prev_day -= pd.Timedelta(days=1)
        
        return prev_day
    
    def trading_days_between(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> int:
        """
        Count trading days between two dates (inclusive).
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Number of trading days between the dates
        """
        start = pd.Timestamp(start_date)
        end = pd.Timestamp(end_date)
        
        # Ensure start <= end
        if start > end:
            start, end = end, start
        
        # Count weekdays
        trading_days = 0
        current = start
        
        while current <= end:
            if current.weekday() < 5:  # Monday=0, Friday=4
                trading_days += 1
            current += pd.Timedelta(days=1)
        
        return trading_days
    
    def _effective_now(self) -> datetime:
        """Get current time in trading timezone."""
        tz = self.get_trading_timezone()
        return datetime.now(tz)
    
    def display_market_time_header(self) -> str:
        """
        Generate market time header string for display.
        
        Returns:
            Formatted string showing current time and market status
        """
        tz = self.get_trading_timezone()
        tz_name = self.get_timezone_name()
        now = datetime.now(tz)
        
        # Format current time
        time_str = now.strftime(f"%Y-%m-%d %H:%M:%S {tz_name}")
        
        # Market status
        # Use emojis if Unicode is supported
        try:
            # Test if we can encode emojis
            "🟢".encode('utf-8')
            if self.is_market_open(now):
                status = f"{_safe_emoji('🟢')} MARKET OPEN"
            else:
                status = f"{_safe_emoji('🔴')} MARKET CLOSED"
        except (UnicodeEncodeError, LookupError):
            # Fallback to plain text
            if self.is_market_open(now):
                status = "MARKET OPEN"
            else:
                status = "MARKET CLOSED"
        
        return f"{time_str} | {status}"


class MarketTimer:
    """
    Market timer that shows countdown to market open/close.

    Provides real-time countdown display for market events and
    integrates with the existing display system.
    """

    def __init__(self, market_hours: Optional[MarketHours] = None):
        """
        Initialize market timer.

        Args:
            market_hours: Optional MarketHours instance to use
        """
        self.market_hours = market_hours or MarketHours()

    def get_next_market_event(self) -> Tuple[datetime, str]:
        """
        Get the next market event (open or close) and its type.

        Returns:
            Tuple of (next_event_time, event_type) where event_type is 'open' or 'close'
        """
        tz = self.market_hours.get_trading_timezone()
        now = datetime.now(tz)

        # Check if market is currently open
        if self.market_hours.is_market_open(now):
            # Market is open, next event is close
            next_event = self.market_hours.get_market_close_time(now)
            event_type = "close"
        else:
            # Market is closed, next event is open
            next_event = self.market_hours.get_market_open_time(now)
            event_type = "open"

            # If we've passed today's open time, get tomorrow's open time
            if now > next_event:
                next_event = self.market_hours.get_market_open_time(
                    self.market_hours.next_trading_day(now).to_pydatetime()
                )
                event_type = "open"

        return next_event, event_type

    def format_countdown(self, target_time: datetime) -> str:
        """
        Format countdown to target time.

        Args:
            target_time: The target datetime to count down to

        Returns:
            Formatted countdown string (e.g., "02:30:45")
        """
        tz = self.market_hours.get_trading_timezone()
        now = datetime.now(tz)

        time_diff = target_time - now

        # Handle if target is in the past (shouldn't happen with get_next_market_event)
        if time_diff.total_seconds() <= 0:
            return "00:00:00"

        # Calculate hours, minutes, seconds
        total_seconds = int(time_diff.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def get_market_timer_display(self) -> Dict[str, Any]:
        """
        Get complete market timer information for display.

        Returns:
            Dictionary with timer information including countdown, next event, etc.
        """
        next_event_time, event_type = self.get_next_market_event()
        countdown = self.format_countdown(next_event_time)

        # Get current market status
        tz = self.market_hours.get_trading_timezone()
        now = datetime.now(tz)
        is_open = self.market_hours.is_market_open(now)

        # Format current time
        time_str = now.strftime("%H:%M:%S %Z")

        return {
            'current_time': time_str,
            'market_status': 'OPEN' if is_open else 'CLOSED',
            'next_event': event_type.upper(),
            'next_event_time': next_event_time.strftime("%H:%M:%S %Z"),
            'countdown': countdown,
            'countdown_label': f"until market {event_type}",
            'is_market_open': is_open
        }

    def display_market_timer(self, compact: bool = False) -> str:
        """
        Generate formatted market timer string for display.

        Args:
            compact: If True, use compact format for header integration

        Returns:
            Formatted timer string
        """
        timer_info = self.get_market_timer_display()

        if compact:
            # Compact format for headers: "⏰ 14:30:25 PST | 🟢 OPEN | Closes in 02:30:45"
            status_emoji = "🟢" if timer_info['is_market_open'] else "🔴"
            safe_status_emoji = _safe_emoji(status_emoji)
            return (f"{_safe_emoji('⏰')} {timer_info['current_time']} | "
                   f"{safe_status_emoji} {timer_info['market_status']} | "
                   f"{timer_info['next_event']} in {timer_info['countdown']}")
        else:
            # Full format for dedicated display
            lines = [
                f"{_safe_emoji('⏰')} Current Time: {timer_info['current_time']}",
                f"{_safe_emoji('📊')} Market Status: {timer_info['market_status']}",
                f"{_safe_emoji('🎯')} Next Event: {timer_info['next_event']} at {timer_info['next_event_time']}",
                f"{_safe_emoji('⏱️')} {timer_info['countdown_label']}: {timer_info['countdown']}"
            ]
            return "\n".join(lines)