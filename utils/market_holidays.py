"""
Market holiday detection for US and Canadian stock markets.

This module provides comprehensive holiday detection for both US and Canadian
stock markets, including shared holidays and market-specific closures.
Supports dynamic calculation of holidays for any year.
"""

from datetime import datetime, date, timedelta
from typing import Set, List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

class MarketHolidays:
    """
    Market holiday detection for US and Canadian stock markets.
    
    Provides methods to check if markets are closed on specific dates,
    including weekends, holidays, and market-specific closures.
    Dynamically calculates holidays for any year.
    """
    
    def __init__(self):
        """Initialize market holiday calculator."""
        self._holiday_cache = {}  # Cache for calculated holidays by year
    
    def _get_easter_sunday(self, year: int) -> date:
        """
        Calculate Easter Sunday for a given year using the algorithm.
        
        Args:
            year: Year to calculate Easter for
            
        Returns:
            Date of Easter Sunday
        """
        # Algorithm for calculating Easter Sunday
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        n = (h + l - 7 * m + 114) // 31
        p = (h + l - 7 * m + 114) % 31
        
        return date(year, n, p + 1)
    
    def _get_good_friday(self, year: int) -> date:
        """Calculate Good Friday (2 days before Easter Sunday)."""
        easter = self._get_easter_sunday(year)
        return easter - timedelta(days=2)
    
    def _get_nth_weekday(self, year: int, month: int, weekday: int, n: int) -> date:
        """
        Get the nth occurrence of a weekday in a given month/year.
        
        Args:
            year: Year
            month: Month (1-12)
            weekday: Weekday (0=Monday, 6=Sunday)
            n: Which occurrence (1=first, 2=second, etc.)
            
        Returns:
            Date of the nth weekday
        """
        # Start with the first day of the month
        first_day = date(year, month, 1)
        
        # Find the first occurrence of the weekday
        days_ahead = weekday - first_day.weekday()
        if days_ahead < 0:
            days_ahead += 7
        
        first_occurrence = first_day + timedelta(days=days_ahead)
        
        # Add weeks to get the nth occurrence
        return first_occurrence + timedelta(weeks=n-1)
    
    def _get_last_weekday(self, year: int, month: int, weekday: int) -> date:
        """
        Get the last occurrence of a weekday in a given month/year.
        
        Args:
            year: Year
            month: Month (1-12)
            weekday: Weekday (0=Monday, 6=Sunday)
            
        Returns:
            Date of the last weekday
        """
        # Start with the last day of the month
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        
        # Find the last occurrence of the weekday
        days_back = last_day.weekday() - weekday
        if days_back < 0:
            days_back += 7
        
        return last_day - timedelta(days=days_back)
    
    def _calculate_holidays(self, year: int) -> Dict[str, Set[date]]:
        """
        Calculate all market holidays for a given year.
        
        Args:
            year: Year to calculate holidays for
            
        Returns:
            Dictionary with 'shared', 'canadian', 'us' holiday sets
        """
        holidays = {
            'shared': set(),
            'canadian': set(),
            'us': set()
        }
        
        # Shared holidays (both US and Canadian markets closed)
        holidays['shared'].add(date(year, 1, 1))  # New Year's Day
        holidays['shared'].add(self._get_good_friday(year))  # Good Friday
        holidays['shared'].add(self._get_nth_weekday(year, 9, 0, 1))  # Labour Day (first Monday in September)
        holidays['shared'].add(date(year, 12, 25))  # Christmas Day
        
        # Canadian market holidays (TSX/TSX-V)
        holidays['canadian'].add(self._get_nth_weekday(year, 2, 0, 3))  # Family Day (third Monday in February)
        holidays['canadian'].add(self._get_last_weekday(year, 5, 0))  # Victoria Day (last Monday in May)
        holidays['canadian'].add(date(year, 7, 1))  # Canada Day
        holidays['canadian'].add(self._get_nth_weekday(year, 8, 0, 1))  # Civic Holiday (first Monday in August)
        holidays['canadian'].add(self._get_nth_weekday(year, 10, 0, 2))  # Thanksgiving Day (second Monday in October)
        
        # Boxing Day - December 26th, or next Monday if it falls on weekend
        boxing_day = date(year, 12, 26)
        if boxing_day.weekday() >= 5:  # Weekend
            # Find next Monday
            days_ahead = 0 - boxing_day.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            boxing_day = boxing_day + timedelta(days=days_ahead)
        holidays['canadian'].add(boxing_day)
        
        # US market holidays (NYSE/NASDAQ)
        holidays['us'].add(self._get_nth_weekday(year, 1, 0, 3))  # Martin Luther King, Jr. Day (third Monday in January)
        holidays['us'].add(self._get_nth_weekday(year, 2, 0, 3))  # Presidents' Day (third Monday in February)
        holidays['us'].add(self._get_last_weekday(year, 5, 0))  # Memorial Day (last Monday in May)
        holidays['us'].add(date(year, 6, 19))  # Juneteenth National Independence Day
        
        # Independence Day - July 4th, or previous Friday if it falls on weekend
        independence_day = date(year, 7, 4)
        if independence_day.weekday() == 5:  # Saturday
            independence_day = independence_day - timedelta(days=1)
        elif independence_day.weekday() == 6:  # Sunday
            independence_day = independence_day - timedelta(days=2)
        holidays['us'].add(independence_day)
        
        holidays['us'].add(self._get_nth_weekday(year, 11, 3, 4))  # Thanksgiving Day (fourth Thursday in November)
        
        return holidays
    
    def _get_holidays_for_year(self, year: int) -> Dict[str, Set[date]]:
        """Get holidays for a year, using cache if available."""
        if year not in self._holiday_cache:
            self._holiday_cache[year] = self._calculate_holidays(year)
        return self._holiday_cache[year]
    
    def is_weekend(self, check_date: date) -> bool:
        """Check if the date is a weekend (Saturday or Sunday)."""
        return check_date.weekday() >= 5  # 5=Saturday, 6=Sunday
    
    def is_canadian_market_closed(self, check_date: date) -> bool:
        """Check if Canadian markets (TSX/TSX-V) are closed on this date."""
        year_holidays = self._get_holidays_for_year(check_date.year)
        return (self.is_weekend(check_date) or 
                check_date in year_holidays['shared'] or 
                check_date in year_holidays['canadian'])
    
    def is_us_market_closed(self, check_date: date) -> bool:
        """Check if US markets (NYSE/NASDAQ) are closed on this date."""
        year_holidays = self._get_holidays_for_year(check_date.year)
        return (self.is_weekend(check_date) or 
                check_date in year_holidays['shared'] or 
                check_date in year_holidays['us'])
    
    def is_trading_day(self, check_date: date, market: str = "both") -> bool:
        """
        Check if markets are open on the given date.
        
        Args:
            check_date: Date to check
            market: "us", "canadian", "both", or "any" (default)
            
        Returns:
            True if markets are open, False if closed
        """
        if market == "us":
            return not self.is_us_market_closed(check_date)
        elif market == "canadian":
            return not self.is_canadian_market_closed(check_date)
        elif market == "both":
            # Both markets must be open
            return (not self.is_us_market_closed(check_date) and 
                    not self.is_canadian_market_closed(check_date))
        elif market == "any":
            # Either market is open
            return (not self.is_us_market_closed(check_date) or 
                    not self.is_canadian_market_closed(check_date))
        else:
            raise ValueError("Market must be 'us', 'canadian', 'both', or 'any'")
    
    def get_next_trading_day(self, start_date: date, market: str = "both") -> date:
        """
        Get the next trading day after the given date.
        
        Args:
            start_date: Starting date
            market: "us", "canadian", "both", or "any"
            
        Returns:
            Next trading day
        """
        current_date = start_date + timedelta(days=1)
        while not self.is_trading_day(current_date, market):
            current_date += timedelta(days=1)
        
        return current_date
    
    def get_previous_trading_day(self, start_date: date, market: str = "both") -> date:
        """
        Get the previous trading day before the given date.
        
        Args:
            start_date: Starting date
            market: "us", "canadian", "both", or "any"
            
        Returns:
            Previous trading day
        """
        current_date = start_date - timedelta(days=1)
        while not self.is_trading_day(current_date, market):
            current_date -= timedelta(days=1)
        
        return current_date
    
    def get_trading_days_in_range(self, start_date: date, end_date: date, market: str = "both") -> List[date]:
        """
        Get all trading days in the given date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            market: "us", "canadian", "both", or "any"
            
        Returns:
            List of trading days
        """
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_trading_day(current_date, market):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days

    def get_holidays_for_range(self, start_date: date, end_date: date, market: str = "us") -> List[date]:
        """
        Get all holidays in the given date range for a specific market.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            market: "us", "canadian", "both", or "any"

        Returns:
            List of holiday dates
        """
        holidays = []
        for year in range(start_date.year, end_date.year + 1):
            year_holidays = self._get_holidays_for_year(year)

            market_holidays = set()
            if market == 'us':
                market_holidays = year_holidays['us'].union(year_holidays['shared'])
            elif market == 'canadian':
                market_holidays = year_holidays['canadian'].union(year_holidays['shared'])
            elif market == 'both':
                # Both markets closed - only shared holidays
                market_holidays = year_holidays['shared']
            elif market == 'any':
                # Either market closed - all holidays from both markets
                market_holidays = year_holidays['us'].union(year_holidays['canadian']).union(year_holidays['shared'])
            else:
                raise ValueError("Market must be 'us', 'canadian', 'both', or 'any'")

            for holiday in market_holidays:
                if start_date <= holiday <= end_date:
                    holidays.append(holiday)
        return holidays
    
    def get_holiday_name(self, check_date: date) -> Optional[str]:
        """
        Get the name of the holiday if the date is a market holiday.
        
        Args:
            check_date: Date to check
            
        Returns:
            Holiday name if it's a holiday, None otherwise
        """
        year_holidays = self._get_holidays_for_year(check_date.year)
        
        # Check shared holidays first
        if check_date in year_holidays['shared']:
            if check_date.day == 1 and check_date.month == 1:
                return "New Year's Day"
            elif check_date == self._get_good_friday(check_date.year):
                return "Good Friday"
            elif check_date == self._get_nth_weekday(check_date.year, 9, 0, 1):
                return "Labour Day"
            elif check_date.day == 25 and check_date.month == 12:
                return "Christmas Day"
        
        # Check Canadian holidays
        if check_date in year_holidays['canadian']:
            if check_date == self._get_nth_weekday(check_date.year, 2, 0, 3):
                return "Family Day"
            elif check_date == self._get_last_weekday(check_date.year, 5, 0):
                return "Victoria Day"
            elif check_date.day == 1 and check_date.month == 7:
                return "Canada Day"
            elif check_date == self._get_nth_weekday(check_date.year, 8, 0, 1):
                return "Civic Holiday"
            elif check_date == self._get_nth_weekday(check_date.year, 10, 0, 2):
                return "Thanksgiving Day"
            elif check_date.day == 26 and check_date.month == 12:
                return "Boxing Day"
        
        # Check US holidays
        if check_date in year_holidays['us']:
            if check_date == self._get_nth_weekday(check_date.year, 1, 0, 3):
                return "Martin Luther King, Jr. Day"
            elif check_date == self._get_nth_weekday(check_date.year, 2, 0, 3):
                return "Presidents' Day"
            elif check_date == self._get_last_weekday(check_date.year, 5, 0):
                return "Memorial Day"
            elif check_date.day == 19 and check_date.month == 6:
                return "Juneteenth National Independence Day"
            elif check_date.day == 4 and check_date.month == 7:
                return "Independence Day"
            elif check_date == self._get_nth_weekday(check_date.year, 11, 3, 4):
                return "Thanksgiving Day"
        
        return None


# Global instance for easy access
MARKET_HOLIDAYS = MarketHolidays()
