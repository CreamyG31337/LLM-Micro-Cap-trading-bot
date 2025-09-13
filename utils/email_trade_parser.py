"""Email trade parser utility.

This module provides functionality to parse trade information from email notifications
and convert them into Trade objects that can be added to the trading system.

Supports various email formats from different brokers and trading platforms.
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import logging

from data.models.trade import Trade
from utils.timezone_utils import parse_csv_timestamp, get_current_trading_time
from utils.ticker_utils import normalize_ticker_symbol

logger = logging.getLogger(__name__)


class EmailTradeParser:
    """Parser for extracting trade information from email notifications."""
    
    def __init__(self):
        """Initialize the email trade parser."""
        # Common patterns for different email formats
        self.patterns = {
            'symbol': [
                r'Symbol:\s*([A-Za-z0-9.]+)',
                r'Ticker:\s*([A-Za-z0-9.]+)',
                r'Stock:\s*([A-Za-z0-9.]+)',
                r'^([A-Za-z0-9.]+)\s*$',  # Standalone symbol
            ],
            'shares': [
                r'Shares:\s*([0-9,]+\.?[0-9]*)',
                r'Quantity:\s*([0-9,]+\.?[0-9]*)',
                r'Qty:\s*([0-9,]+\.?[0-9]*)',
                r'(\d+\.?\d*)\s*shares?',
            ],
            'price': [
                r'Average price:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Price:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Fill price:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Executed at:\s*\$?([0-9,]+\.?[0-9]*)',
                r'\$([0-9,]+\.?[0-9]*)',
                r'price:\s*\$?([0-9,]+\.?[0-9]*)',  # Case insensitive
            ],
            'total_cost': [
                r'Total cost:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Total value:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Total:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Amount:\s*\$?([0-9,]+\.?[0-9]*)',
                r'Value:\s*\$?([0-9,]+\.?[0-9]*)',
            ],
            'action': [
                r'Type:\s*(Market\s+)?(Buy|Sell|Bought|Sold)',
                r'Type:\s*(Fractional\s+)?(Buy|Sell|Bought|Sold)',
                r'Action:\s*(Buy|Sell|Bought|Sold)',
                r'(Buy|Sell|Bought|Sold)\s+order',
                r'Order type:\s*(Buy|Sell)',
            ],
            'time': [
                r'Time:\s*([^\\n]+)',
                r'Date:\s*([^\\n]+)',
                r'Executed:\s*([^\\n]+)',
                r'Fill time:\s*([^\\n]+)',
            ],
            'account': [
                r'Account:\s*([^\\n]+)',
                r'Account type:\s*([^\\n]+)',
            ]
        }
    
    def parse_email_trade(self, email_text: str) -> Optional[Trade]:
        """Parse trade information from email text.
        
        Args:
            email_text: Raw email text containing trade information
            
        Returns:
            Trade object if parsing successful, None otherwise
        """
        try:
            # Clean up the email text
            cleaned_text = self._clean_email_text(email_text)
            
            # Extract trade components
            symbol = self._extract_symbol(cleaned_text)
            shares = self._extract_shares(cleaned_text)
            price = self._extract_price(cleaned_text)
            action = self._extract_action(cleaned_text)
            timestamp = self._extract_timestamp(cleaned_text)
            total_cost = self._extract_total_cost(cleaned_text)
            currency = self._extract_currency(cleaned_text)
            
            # Validate required fields
            if not all([symbol, shares, price, action]):
                missing = []
                if not symbol: missing.append('symbol')
                if not shares: missing.append('shares')
                if not price: missing.append('price')
                if not action: missing.append('action')
                logger.warning(f"Missing required fields: {missing}")
                return None
            
            # Normalize action
            action = self._normalize_action(action)
            
            # Normalize ticker symbol based on currency and price context
            symbol = normalize_ticker_symbol(symbol, currency, float(price))
            
            # Use provided timestamp or current time
            if not timestamp:
                timestamp = get_current_trading_time()
            else:
                # Convert to PDT for consistent formatting
                timestamp = self._convert_to_pdt(timestamp)
            
            # Calculate cost basis if not provided
            if not total_cost:
                total_cost = float(shares) * float(price)
            
            # Create Trade object
            trade = Trade(
                ticker=symbol,
                action=action,
                shares=Decimal(str(shares)),
                price=Decimal(str(price)),
                timestamp=timestamp,
                cost_basis=Decimal(str(total_cost)),
                reason=f"EMAIL TRADE - {action}",
                currency=currency
            )
            
            logger.info(f"Successfully parsed trade: {symbol} {action} {shares} @ {price}")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to parse email trade: {e}")
            return None
    
    def _clean_email_text(self, text: str) -> str:
        """Clean and normalize email text for parsing."""
        # Remove extra whitespace and normalize line breaks
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove common email headers/footers
        text = re.sub(r'^(From:|To:|Subject:|Date:).*$', '', text, flags=re.MULTILINE)
        return text
    
    def _extract_symbol(self, text: str) -> Optional[str]:
        """Extract ticker symbol from text."""
        for pattern in self.patterns['symbol']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                symbol = match.group(1).strip()
                # Clean up the symbol (remove extra spaces, normalize)
                symbol = re.sub(r'\s+', '', symbol)
                return symbol.upper()
        return None
    
    def _extract_shares(self, text: str) -> Optional[float]:
        """Extract number of shares from text."""
        for pattern in self.patterns['shares']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                shares_str = match.group(1).replace(',', '')
                try:
                    return float(shares_str)
                except ValueError:
                    continue
        return None
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract price per share from text."""
        for pattern in self.patterns['price']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None
    
    def _extract_currency(self, text: str) -> str:
        """Extract currency from text (CAD, USD, etc.)."""
        # Look for currency indicators in the text
        if re.search(r'US\$|USD|US\s+Dollar', text, re.IGNORECASE):
            return 'USD'
        elif re.search(r'CA\$|CAD|Canadian|C\$', text, re.IGNORECASE):
            return 'CAD'
        else:
            # Default to CAD for Canadian market
            return 'CAD'
    
    
    def _extract_total_cost(self, text: str) -> Optional[float]:
        """Extract total cost from text."""
        for pattern in self.patterns['total_cost']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cost_str = match.group(1).replace(',', '')
                try:
                    return float(cost_str)
                except ValueError:
                    continue
        return None
    
    def _extract_action(self, text: str) -> Optional[str]:
        """Extract buy/sell action from text."""
        for pattern in self.patterns['action']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Get the last group (the actual action word)
                action = match.groups()[-1].strip()
                return action.upper()
        return None
    
    def _extract_timestamp(self, text: str) -> Optional[datetime]:
        """Extract timestamp from text."""
        for pattern in self.patterns['time']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time_str = match.group(1).strip()
                return self._parse_timestamp(time_str)
        return None
    
    def _parse_timestamp(self, time_str: str) -> Optional[datetime]:
        """Parse various timestamp formats."""
        # Common timestamp formats
        formats = [
            '%B %d, %Y %H:%M %Z',  # September 12, 2025 09:30 EDT
            '%B %d, %Y %H:%M %Z%z',  # September 12, 2025 09:30 EDT-0400
            '%Y-%m-%d %H:%M:%S %Z',  # 2025-09-12 09:30:00 EDT
            '%Y-%m-%d %H:%M %Z',     # 2025-09-12 09:30 EDT
            '%m/%d/%Y %H:%M %Z',     # 09/12/2025 09:30 EDT
            '%m/%d/%Y %H:%M:%S %Z',  # 09/12/2025 09:30:00 EDT
        ]
        
        # Try each format
        for fmt in formats:
            try:
                dt = datetime.strptime(time_str, fmt)
                # Convert to timezone-aware datetime
                return self._make_timezone_aware(dt, time_str)
            except ValueError:
                continue
        
        # Try using the existing CSV timestamp parser
        try:
            parsed = parse_csv_timestamp(time_str)
            if parsed is not None:
                return parsed.to_pydatetime()
        except Exception:
            pass
        
        logger.warning(f"Could not parse timestamp: {time_str}")
        return None
    
    def _make_timezone_aware(self, dt: datetime, time_str: str) -> datetime:
        """Make a naive datetime timezone-aware based on timezone info in the string."""
        # Extract timezone info
        tz_patterns = [
            r'([A-Z]{3,4})$',  # EDT, EST, PST, etc.
            r'([A-Z]{3,4})\s*$',  # EDT , EST , etc.
        ]
        
        for pattern in tz_patterns:
            match = re.search(pattern, time_str)
            if match:
                tz_abbr = match.group(1)
                # Convert timezone abbreviation to offset
                tz_offset = self._get_timezone_offset(tz_abbr)
                if tz_offset is not None:
                    from datetime import timezone, timedelta
                    tz = timezone(timedelta(hours=tz_offset))
                    return dt.replace(tzinfo=tz)
        
        # Default to current trading timezone if no timezone info
        from utils.timezone_utils import get_trading_timezone
        tz = get_trading_timezone()
        return dt.replace(tzinfo=tz)
    
    def _convert_to_pdt(self, dt: datetime) -> datetime:
        """Convert any timezone to PDT for consistent CSV formatting."""
        from utils.timezone_utils import get_trading_timezone
        tz = get_trading_timezone()
        return dt.astimezone(tz)
    
    def _get_timezone_offset(self, tz_abbr: str) -> Optional[int]:
        """Get UTC offset for timezone abbreviation."""
        tz_offsets = {
            'EST': -5, 'EDT': -4,
            'CST': -6, 'CDT': -5,
            'MST': -7, 'MDT': -6,
            'PST': -8, 'PDT': -7,
            'UTC': 0, 'GMT': 0,
        }
        return tz_offsets.get(tz_abbr.upper())
    
    def _normalize_action(self, action: str) -> str:
        """Normalize action to standard format."""
        action = action.upper().strip()
        if action in ['BUY', 'BOUGHT', 'MARKET BUY']:
            return 'BUY'
        elif action in ['SELL', 'SOLD', 'MARKET SELL']:
            return 'SELL'
        else:
            return action


def parse_trade_from_email(email_text: str) -> Optional[Trade]:
    """Convenience function to parse a trade from email text.
    
    Args:
        email_text: Raw email text containing trade information
        
    Returns:
        Trade object if parsing successful, None otherwise
    """
    parser = EmailTradeParser()
    return parser.parse_email_trade(email_text)


def add_trade_from_email(email_text: str, data_dir: str = "my trading") -> bool:
    """Parse email text and add the trade to the trading system.
    
    Args:
        email_text: Raw email text containing trade information
        data_dir: Directory containing trading data files
        
    Returns:
        True if trade was successfully added, False otherwise
    """
    try:
        # Parse the trade
        trade = parse_trade_from_email(email_text)
        if not trade:
            print("Failed to parse trade from email text")
            return False
        
        # Import here to avoid circular imports
        from data.repositories.csv_repository import CSVRepository
        from portfolio.trade_processor import TradeProcessor
        
        # Initialize repository and processor
        repository = CSVRepository(data_dir)
        processor = TradeProcessor(repository)
        
        # Save the trade directly to the repository with the correct timestamp
        repository.save_trade(trade)
        
        # Update portfolio position
        if trade.action == 'BUY':
            processor._update_position_after_buy(trade, None)
        elif trade.action == 'SELL':
            processor._update_position_after_sell(trade)
        else:
            print(f"Unsupported action: {trade.action}")
            return False
        
        print(f"Successfully added trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price}")
        return True
        
    except Exception as e:
        print(f"Error adding trade from email: {e}")
        logger.error(f"Error adding trade from email: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    sample_email = """
    Your order has been filled
    Account: TFSA
    Type: Market Buy
    Symbol: VEE
    Shares: 4
    Average price: $44.59
    Total cost: $178.36
    Time: September 12, 2025 09:30 EDT
    """
    
    print("Parsing sample email trade...")
    trade = parse_trade_from_email(sample_email)
    if trade:
        print(f"Parsed trade: {trade}")
    else:
        print("Failed to parse trade")
