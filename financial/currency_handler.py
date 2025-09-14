"""
Currency handling module for multi-currency trading support.

This module provides currency detection, conversion, and handling functionality
for both CAD and USD trading. It's designed to work with both CSV and future
database storage systems.
"""

import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
from dataclasses import dataclass

from .calculations import money_to_decimal

logger = logging.getLogger(__name__)

# Type alias for numeric inputs
NumericInput = Union[float, int, str, Decimal]


@dataclass
class CashBalances:
    """Container for dual currency cash balances with database-ready fields."""
    cad: Decimal
    usd: Decimal
    id: Optional[str] = None  # For future database primary key
    last_updated: Optional[str] = None  # For future database timestamp
    
    def __post_init__(self):
        """Ensure cash balances are Decimal objects."""
        self.cad = money_to_decimal(self.cad)
        self.usd = money_to_decimal(self.usd)
    
    def total_cad_equivalent(self, usd_to_cad_rate: NumericInput = 1.35) -> Decimal:
        """Calculate total cash in CAD equivalent."""
        rate = money_to_decimal(usd_to_cad_rate)
        return self.cad + (self.usd * rate)
    
    def total_usd_equivalent(self, cad_to_usd_rate: NumericInput = 0.74) -> Decimal:
        """Calculate total cash in USD equivalent."""
        rate = money_to_decimal(cad_to_usd_rate)
        return self.usd + (self.cad * rate)
    
    def can_afford_cad(self, amount: NumericInput) -> bool:
        """Check if we have enough CAD cash."""
        amount_dec = money_to_decimal(amount)
        return self.cad >= amount_dec

    def can_afford_usd(self, amount: NumericInput) -> bool:
        """Check if we have enough USD cash."""
        amount_dec = money_to_decimal(amount)
        return self.usd >= amount_dec
    
    def spend_cad(self, amount: NumericInput) -> bool:
        """
        Spend CAD cash - only spends available amount, prevents negative balance.
        
        Returns:
            bool: True if full amount was spent, False if partial/none
        """
        amount_dec = money_to_decimal(amount)
        if self.cad >= amount_dec:
            self.cad -= amount_dec
            return True  # Full amount spent
        else:
            # Spend only what's available, balance goes to 0
            self.cad = Decimal('0.00')
            return False  # Partial amount spent (or none if already 0)
    
    def spend_usd(self, amount: NumericInput) -> bool:
        """
        Spend USD cash - only spends available amount, prevents negative balance.
        
        Returns:
            bool: True if full amount was spent, False if partial/none
        """
        amount_dec = money_to_decimal(amount)
        if self.usd >= amount_dec:
            self.usd -= amount_dec
            return True  # Full amount spent
        else:
            # Spend only what's available, balance goes to 0
            self.usd = Decimal('0.00')
            return False  # Partial amount spent (or none if already 0)
    
    def add_cad(self, amount: NumericInput) -> None:
        """Add CAD cash (from sales, etc.)."""
        amount_dec = money_to_decimal(amount)
        self.cad += amount_dec
    
    def add_usd(self, amount: NumericInput) -> None:
        """Add USD cash (from sales, etc.)."""
        amount_dec = money_to_decimal(amount)
        self.usd += amount_dec
    
    def to_dict(self) -> Dict[str, Union[str, float]]:
        """Convert to dictionary for CSV/JSON serialization."""
        return {
            'cad': float(self.cad),
            'usd': float(self.usd),
            'id': self.id,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, float]]) -> 'CashBalances':
        """Create from dictionary (CSV row or database record)."""
        return cls(
            cad=data.get('cad', 0.0),
            usd=data.get('usd', 0.0),
            id=data.get('id'),
            last_updated=data.get('last_updated')
        )


class CurrencyHandler:
    """
    Handles currency detection, conversion, and exchange rate management.
    
    Designed to work with both CSV files and future database backends.
    """
    
    # Default exchange rates (in production, these would come from an API)
    DEFAULT_RATES = {
        ('USD', 'CAD'): 1.35,
        ('CAD', 'USD'): 0.74,
        ('USD', 'USD'): 1.0,
        ('CAD', 'CAD'): 1.0
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize currency handler.
        
        Args:
            data_dir: Directory for storing cash balances and exchange rate cache
        """
        self.data_dir = data_dir
        self._exchange_rate_cache = {}
        
    def is_canadian_ticker(self, ticker: str) -> bool:
        """Determine if ticker is Canadian based on suffix."""
        ticker = ticker.upper().strip()
        return (ticker.endswith('.TO') or 
                ticker.endswith('.V') or 
                ticker.endswith('.CN') or
                ticker.endswith('.TSX'))

    def is_us_ticker(self, ticker: str) -> bool:
        """Determine if ticker is US based on format."""
        ticker = ticker.upper().strip()
        # US tickers typically have no suffix, or specific US suffixes
        return (not self.is_canadian_ticker(ticker) and 
                not ticker.startswith('^') and
                not ticker.endswith('.L'))  # London Stock Exchange

    def get_ticker_currency(self, ticker: str) -> str:
        """
        Get the currency for a ticker.
        
        Args:
            ticker: The stock ticker symbol
            
        Returns:
            str: 'CAD' for Canadian tickers, 'USD' for US tickers
        """
        if self.is_canadian_ticker(ticker):
            return 'CAD'
        elif self.is_us_ticker(ticker):
            return 'USD'
        else:
            # Default to USD for unknown formats (indices, etc.)
            return 'USD'
    
    def detect_currency_context(self, ticker: str, price: Optional[NumericInput] = None) -> str:
        """
        Detect currency based on ticker and price context clues.
        
        This is an enhanced version that considers price ranges typical
        for different markets.
        
        Args:
            ticker: The stock ticker symbol
            price: Optional price to help with currency detection
            
        Returns:
            str: Detected currency ('CAD' or 'USD')
        """
        # First, try standard ticker-based detection
        currency = self.get_ticker_currency(ticker)
        
        # If we have a price, use it as additional context
        if price is not None:
            price_dec = money_to_decimal(price)
            
            # Very low prices (< $1) are more common in Canadian penny stocks
            if price_dec < Decimal('1.00') and currency == 'USD':
                logger.debug(f"Low price {price_dec} for {ticker}, considering CAD context")
                # Don't override USD detection, but log for analysis
        
        return currency
    
    def get_exchange_rate(self, from_currency: str, to_currency: str, 
                         date: Optional[str] = None) -> Decimal:
        """
        Get exchange rate between currencies.
        
        Args:
            from_currency: Source currency ('CAD' or 'USD')
            to_currency: Target currency ('CAD' or 'USD')
            date: Optional date for historical rates (future feature)
            
        Returns:
            Decimal: Exchange rate
        """
        cache_key = (from_currency, to_currency, date)
        
        # Check cache first
        if cache_key in self._exchange_rate_cache:
            return self._exchange_rate_cache[cache_key]
        
        # Get rate from default rates or API
        rate = self._fetch_exchange_rate(from_currency, to_currency, date)
        
        # Cache the result
        self._exchange_rate_cache[cache_key] = rate
        
        return rate
    
    def _fetch_exchange_rate(self, from_currency: str, to_currency: str, 
                           date: Optional[str] = None) -> Decimal:
        """
        Fetch exchange rate from API or default rates.
        
        This method can be extended to fetch from real APIs in the future.
        """
        # Try to get live rate first (if implemented)
        try:
            live_rate = self._get_live_exchange_rate(from_currency, to_currency)
            if live_rate is not None:
                from decimal import Decimal
                return Decimal(str(live_rate)).quantize(Decimal('0.0001'))
        except Exception as e:
            logger.debug(f"Failed to get live exchange rate: {e}")
        
        # Fall back to default rates
        rate = self.DEFAULT_RATES.get((from_currency, to_currency), 1.0)
        from decimal import Decimal
        return Decimal(str(rate)).quantize(Decimal('0.0001'))
    
    def _get_live_exchange_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get live exchange rate from API (optional feature).
        
        Returns None if API is not available or fails.
        """
        try:
            import requests
            
            # Try Bank of Canada API first (most accurate for CAD rates)
            if from_currency == 'USD' and to_currency == 'CAD':
                try:
                    url = "https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json"
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'observations' in data and data['observations']:
                            # Get the latest observation
                            latest = data['observations'][-1]
                            if 'FXUSDCAD' in latest and 'v' in latest['FXUSDCAD']:
                                rate = float(latest['FXUSDCAD']['v'])
                                logger.debug(f"Using Bank of Canada rate: {rate}")
                                return rate
                except Exception as e:
                    logger.debug(f"Bank of Canada API failed: {e}")
            
            # Fallback to exchangerate-api.com
            url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                rate = data['rates'].get(to_currency)
                if rate:
                    logger.debug(f"Using exchangerate-api.com rate: {rate}")
                return rate
            
        except ImportError:
            logger.debug("requests library not available for live exchange rates")
        except Exception as e:
            logger.debug(f"Error fetching live exchange rate: {e}")
        
        return None
    
    def convert_currency(self, amount: NumericInput, from_currency: str, 
                        to_currency: str, fee_rate: NumericInput = 0.015) -> Dict[str, Decimal]:
        """
        Convert currency amount with fee calculation.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency
            fee_rate: Conversion fee rate (default 1.5%)
            
        Returns:
            Dict with conversion details: amount_before_fee, fee_charged, 
            amount_after_fee, exchange_rate, fee_rate
        """
        amount_dec = money_to_decimal(amount)
        # Fee rate needs more precision than monetary values
        fee_rate_dec = Decimal(str(fee_rate)).quantize(Decimal('0.0001'))
        exchange_rate = self.get_exchange_rate(from_currency, to_currency)
        
        # Calculate fee on the original amount (before conversion)
        fee_charged = (amount_dec * fee_rate_dec).quantize(Decimal('0.01'))
        
        # Convert the amount after deducting the fee
        amount_after_fee_in_source = amount_dec - fee_charged
        amount_after_fee = (amount_after_fee_in_source * exchange_rate).quantize(Decimal('0.01'))
        
        # For reporting, also calculate what the amount would be before fee
        amount_before_fee = (amount_dec * exchange_rate).quantize(Decimal('0.01'))
        
        return {
            'amount_before_fee': amount_before_fee,
            'fee_charged': fee_charged,
            'amount_after_fee': amount_after_fee,
            'exchange_rate': exchange_rate,
            'fee_rate': fee_rate_dec
        }
    
    def convert_cash_balances(self, balances: CashBalances, cad_amount: NumericInput, 
                            to_currency: str, fee_rate: NumericInput = 0.015) -> Tuple[Decimal, Decimal]:
        """
        Convert cash between currencies and update balances.
        
        Args:
            balances: CashBalances object to update
            cad_amount: Amount to convert (if converting from CAD)
            to_currency: Target currency ('CAD' or 'USD')
            fee_rate: Conversion fee rate
            
        Returns:
            Tuple of (amount_received, fee_charged)
        """
        if to_currency == 'USD':
            # Converting CAD to USD
            conversion = self.convert_currency(cad_amount, 'CAD', 'USD', fee_rate)
            amount_received = conversion['amount_after_fee']
            fee_charged = conversion['fee_charged']
            
            # Update balances
            balances.spend_cad(cad_amount)
            balances.add_usd(amount_received)
            
        else:
            # Converting USD to CAD
            conversion = self.convert_currency(cad_amount, 'USD', 'CAD', fee_rate)
            amount_received = conversion['amount_after_fee']
            fee_charged = conversion['fee_charged']
            
            # Update balances
            balances.spend_usd(cad_amount)
            balances.add_cad(amount_received)
        
        return amount_received, fee_charged
    
    def get_trade_currency_info(self, ticker: str, shares: NumericInput, 
                               price: NumericInput) -> Dict[str, Union[str, Decimal, bool]]:
        """
        Get comprehensive currency info for a trade.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            price: Price per share
            
        Returns:
            Dict with trade currency information
        """
        currency = self.detect_currency_context(ticker, price)
        shares_dec = money_to_decimal(shares)
        price_dec = money_to_decimal(price)
        cost = shares_dec * price_dec
        
        return {
            'ticker': ticker,
            'currency': currency,
            'shares': shares_dec,
            'price': price_dec,
            'cost': cost,
            'is_canadian': currency == 'CAD',
            'is_us': currency == 'USD'
        }
    
    def load_cash_balances(self) -> CashBalances:
        """
        Load cash balances from storage.
        
        Works with both CSV files and future database backends.
        """
        if self.data_dir is None:
            return CashBalances(cad=Decimal('0.00'), usd=Decimal('0.00'))
        
        cash_file = self.data_dir / "cash_balances.json"
        
        if not cash_file.exists():
            return CashBalances(cad=Decimal('0.00'), usd=Decimal('0.00'))
        
        try:
            with open(cash_file, 'r') as f:
                data = json.load(f)
            return CashBalances.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading cash balances: {e}")
            return CashBalances(cad=Decimal('0.00'), usd=Decimal('0.00'))
    
    def save_cash_balances(self, balances: CashBalances) -> None:
        """
        Save cash balances to storage.
        
        Works with both CSV files and future database backends.
        """
        if self.data_dir is None:
            logger.warning("No data directory specified, cannot save cash balances")
            return
        
        cash_file = self.data_dir / "cash_balances.json"
        
        try:
            # Ensure directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to JSON file
            with open(cash_file, 'w') as f:
                json.dump(balances.to_dict(), f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving cash balances: {e}")
    
    def format_cash_display(self, balances: CashBalances, 
                           show_total: bool = True) -> str:
        """
        Format cash balances for display.
        
        Args:
            balances: CashBalances object
            show_total: Whether to show total in CAD equivalent
            
        Returns:
            str: Formatted cash display string
        """
        display = f"CAD ${balances.cad:,.2f} | USD ${balances.usd:,.2f}"
        
        if show_total:
            total_cad = balances.total_cad_equivalent()
            display += f" (Total: CAD ${total_cad:,.2f})"
        
        return display
    
    def clear_exchange_rate_cache(self) -> None:
        """Clear the exchange rate cache to force fresh rates."""
        self._exchange_rate_cache.clear()
    
    def update_exchange_rates_csv(self) -> None:
        """
        Update the exchange rates CSV file with current rates.
        
        This method checks if today's exchange rate is missing and adds it.
        """
        if self.data_dir is None:
            logger.debug("No data directory specified, cannot update exchange rates CSV")
            return
        
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            import pytz
            from utils.timezone_utils import format_timestamp_for_csv
            
            exchange_rates_file = self.data_dir / "exchange_rates.csv"
            trading_tz = pytz.timezone('America/Los_Angeles')
            now = datetime.now(trading_tz)
            today = now.date()
            
            # Load existing CSV
            if exchange_rates_file.exists():
                df = pd.read_csv(exchange_rates_file)
                # Check if today's entry exists
                df['Date_Only'] = df['Date'].str.split(' ').str[0]
                today_str = today.strftime('%Y-%m-%d')
                
                if today_str in df['Date_Only'].values:
                    logger.debug("Today's exchange rate already exists in CSV")
                    return
            else:
                df = pd.DataFrame(columns=['Date', 'USD_CAD_Rate'])
            
            # Get current exchange rate
            current_rate = self._get_live_exchange_rate('USD', 'CAD')
            if current_rate is None:
                # Fall back to default rate
                current_rate = self.DEFAULT_RATES.get(('USD', 'CAD'), 1.38)
                logger.warning("Using fallback exchange rate for CSV update")
            else:
                logger.info(f"Using live exchange rate: {current_rate}")
            
            # Add today's entry
            timestamp = trading_tz.localize(
                datetime.combine(today, datetime.min.time().replace(hour=6, minute=30))
            )
            
            new_entry = pd.DataFrame([{
                'Date': format_timestamp_for_csv(timestamp),
                'USD_CAD_Rate': f'{current_rate:.4f}'  # Format to 4 decimal places like existing entries
            }])
            
            df = pd.concat([df, new_entry], ignore_index=True)
            df = df.drop('Date_Only', axis=1, errors='ignore')  # Remove helper column
            df = df.sort_values('Date')
            
            # Save updated CSV
            df.to_csv(exchange_rates_file, index=False)
            logger.info(f"Updated exchange rates CSV with rate {current_rate} for {today}")
            
        except Exception as e:
            logger.error(f"Failed to update exchange rates CSV: {e}")
    
    def get_exchange_rate_with_csv_update(self, from_currency: str, to_currency: str, 
                                        date: Optional[str] = None) -> Decimal:
        """
        Get exchange rate and update CSV if needed.
        
        This method ensures the exchange rates CSV is updated with today's rate
        before returning the requested rate.
        """
        # Update CSV with current rates if needed
        self.update_exchange_rates_csv()
        
        # Return the exchange rate using the existing method
        return self.get_exchange_rate(from_currency, to_currency, date)


# Convenience functions for backward compatibility
def is_canadian_ticker(ticker: str) -> bool:
    """Convenience function for ticker currency detection."""
    handler = CurrencyHandler()
    return handler.is_canadian_ticker(ticker)


def is_us_ticker(ticker: str) -> bool:
    """Convenience function for ticker currency detection."""
    handler = CurrencyHandler()
    return handler.is_us_ticker(ticker)


def get_ticker_currency(ticker: str) -> str:
    """Convenience function for ticker currency detection."""
    handler = CurrencyHandler()
    return handler.get_ticker_currency(ticker)


def calculate_conversion_with_fee(amount: NumericInput, from_currency: str, 
                                 to_currency: str, fee_rate: NumericInput = 0.015) -> Dict[str, Decimal]:
    """Convenience function for currency conversion calculations."""
    handler = CurrencyHandler()
    return handler.convert_currency(amount, from_currency, to_currency, fee_rate)