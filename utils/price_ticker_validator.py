"""
Price-based ticker validation for Canadian and US markets.

This module validates ticker symbols by comparing fetched prices with
actual trade prices to determine the correct market variant.
"""

import logging
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal
import yfinance as yf
from datetime import timedelta  # Needed for history date ranges

logger = logging.getLogger(__name__)

class PriceTickerValidator:
    """
    Validates ticker symbols by comparing fetched prices with trade prices.
    
    This class helps determine whether a ticker should use .TO suffix
    (Canadian) or no suffix (US) by comparing market prices with actual
    trade execution prices.
    """
    
    def __init__(self, price_tolerance: float = 0.05):
        """
        Initialize the price validator.
        
        Args:
            price_tolerance: Maximum price difference to consider a match (default 5%)
        """
        self.price_tolerance = price_tolerance
        self._cache = {}
    
    def validate_ticker_with_price(
        self, 
        ticker: str, 
        trade_price: float, 
        trade_date: str,
        currency: str = "CAD"
    ) -> Tuple[str, bool]:
        """
        Validate ticker by comparing fetched price with trade price.
        
        Args:
            ticker: Base ticker symbol (e.g., 'ZEA')
            trade_price: Actual price from trade execution
            trade_date: Date of the trade
            currency: Expected currency ('CAD' or 'USD')
            
        Returns:
            Tuple of (corrected_ticker, is_valid)
        """
        # Check cache first
        cache_key = f"{ticker}_{trade_price}_{trade_date}_{currency}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Determine which variants to test based on currency
        if currency.upper() == "CAD":
            variants_to_test = [
                f"{ticker}.TO",   # TSX (prioritized for CAD)
                f"{ticker}.V",    # TSX Venture
                ticker,           # US (fallback)
            ]
        else:
            variants_to_test = [
                ticker,           # US (prioritized for USD)
                f"{ticker}.TO",   # TSX
                f"{ticker}.V",    # TSX Venture
            ]
        
        best_match = None
        best_price_diff = float('inf')
        
        for variant in variants_to_test:
            try:
                # Suppress yfinance warnings
                logging.getLogger("yfinance").setLevel(logging.CRITICAL)
                
                stock = yf.Ticker(variant)
                info = stock.info
                
                # Check if we get valid info
                if not info or not info.get('symbol') or info.get('symbol') == 'N/A':
                    continue
                
                # Get historical price for the trade date
                historical_price = self._get_historical_price(variant, trade_date)
                if historical_price is None:
                    continue
                
                # Calculate price difference percentage
                price_diff = abs(historical_price - trade_price) / trade_price
                
                # Check if this is a better match
                if price_diff < best_price_diff and price_diff <= self.price_tolerance:
                    best_match = variant
                    best_price_diff = price_diff
                    
                    logger.debug(f"Price match found: {variant} @ ${historical_price:.2f} vs trade @ ${trade_price:.2f} (diff: {price_diff:.1%})")
                
            except Exception as e:
                logger.debug(f"Error testing variant {variant}: {e}")
                continue
        
        # Cache the result
        result = (best_match or ticker, best_match is not None)
        self._cache[cache_key] = result
        
        if best_match:
            logger.info(f"Validated {ticker} -> {best_match} (price diff: {best_price_diff:.1%})")
        else:
            logger.warning(f"No price match found for {ticker} @ ${trade_price:.2f}")
        
        return result
    
    def _get_historical_price(self, ticker: str, trade_date: str) -> Optional[float]:
        """
        Get historical price for a ticker on a specific date.
        
        Args:
            ticker: Ticker symbol
            trade_date: Date string in format 'YYYY-MM-DD HH:MM:SS TZ'
            
        Returns:
            Historical close price or None if not found
        """
        try:
            from utils.timezone_utils import parse_csv_timestamp
            
            # Parse the trade date
            date_obj = parse_csv_timestamp(trade_date)
            if not date_obj:
                return None
            
            # Get stock data for the date
            stock = yf.Ticker(ticker)
            hist = stock.history(start=date_obj.date(), end=date_obj.date() + timedelta(days=1))
            
            if not hist.empty and 'Close' in hist.columns:
                return float(hist['Close'].iloc[0])
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting historical price for {ticker} on {trade_date}: {e}")
            return None
    
    def validate_ticker_batch(
        self, 
        ticker_price_pairs: list[Tuple[str, float, str, str]]
    ) -> Dict[str, str]:
        """
        Validate multiple tickers in batch.
        
        Args:
            ticker_price_pairs: List of (ticker, price, date, currency) tuples
            
        Returns:
            Dictionary mapping original tickers to corrected tickers
        """
        results = {}
        
        for ticker, price, date, currency in ticker_price_pairs:
            corrected_ticker, is_valid = self.validate_ticker_with_price(
                ticker, price, date, currency
            )
            results[ticker] = corrected_ticker
        
        return results


# Global instance for easy access
PRICE_VALIDATOR = PriceTickerValidator()
