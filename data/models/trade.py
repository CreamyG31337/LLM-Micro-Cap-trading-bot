"""Trade data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Any


@dataclass
class Trade:
    """Represents a single trade transaction.
    
    This model is designed to work with both CSV and database backends,
    supporting serialization to/from dictionaries for CSV rows and JSON.
    """
    ticker: str
    action: str  # BUY/SELL/HOLD
    shares: Decimal
    price: Decimal
    timestamp: datetime
    cost_basis: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    reason: Optional[str] = None
    currency: str = "CAD"
    trade_id: Optional[str] = None  # For database primary key
    
    def __post_init__(self):
        """Convert string values to Decimal for financial fields."""
        # Convert string values to Decimal for financial fields with error handling
        def safe_decimal_convert(value, default_value=None):
            """Safely convert value to Decimal, handling errors gracefully."""
            if value is None:
                return default_value
            try:
                if isinstance(value, str):
                    # Handle empty strings and 'nan' strings
                    value = value.strip()
                    if not value or value.lower() == 'nan' or value.lower() == 'none':
                        return default_value
                return Decimal(str(value))
            except (ValueError, TypeError, ArithmeticError):
                return default_value
        
        # Convert required fields (cannot be None)
        self.shares = safe_decimal_convert(self.shares, Decimal('0'))
        self.price = safe_decimal_convert(self.price, Decimal('0'))
        
        # Convert optional fields (can be None)
        self.cost_basis = safe_decimal_convert(self.cost_basis, None) if self.cost_basis is not None else None
        self.pnl = safe_decimal_convert(self.pnl, None) if self.pnl is not None else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization.
        
        Returns:
            Dictionary representation compatible with CSV format
        """
        return {
            'ticker': self.ticker,
            'action': self.action,
            'shares': float(self.shares),
            'price': float(self.price),
            'timestamp': self.timestamp.isoformat(),
            'cost_basis': float(self.cost_basis) if self.cost_basis is not None else None,
            'pnl': float(self.pnl) if self.pnl is not None else None,
            'reason': self.reason,
            'currency': self.currency,
            'trade_id': self.trade_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Trade:
        """Create Trade from dictionary (CSV row or database record).
        
        Args:
            data: Dictionary containing trade data
            
        Returns:
            Trade instance
        """
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            ticker=str(data.get('ticker', '')),
            action=str(data.get('action', 'BUY')),
            shares=Decimal(str(data.get('shares', 0))),
            price=Decimal(str(data.get('price', 0))),
            timestamp=timestamp,
            cost_basis=Decimal(str(data['cost_basis'])) if data.get('cost_basis') is not None else None,
            pnl=Decimal(str(data['pnl'])) if data.get('pnl') is not None else None,
            reason=data.get('reason'),
            currency=str(data.get('currency', 'CAD')),
            trade_id=data.get('trade_id')
        )
    
    def to_csv_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching current CSV format.
        
        Returns:
            Dictionary with keys matching llm_trade_log.csv format
        """
        # Format timestamp with proper timezone handling
        if self.timestamp.tzinfo is not None:
            # Timezone-aware datetime - convert to PDT and format properly
            from utils.timezone_utils import get_trading_timezone, format_timestamp_for_csv
            tz = get_trading_timezone()
            dt_pdt = self.timestamp.astimezone(tz)
            date_str = format_timestamp_for_csv(dt_pdt)
        else:
            # Naive datetime - assume PST/PDT based on date
            from utils.timezone_utils import format_timestamp_for_csv
            date_str = format_timestamp_for_csv(self.timestamp)
        
        return {
            'Date': date_str,
            'Ticker': self.ticker,
            'Shares Bought': float(self.shares),
            'Buy Price': float(self.price),
            'Cost Basis': float(self.cost_basis) if self.cost_basis is not None else 0.0,
            'PnL': float(self.pnl) if self.pnl is not None else 0.0,
            'Reason': self.reason or ''
        }
    
    @classmethod
    def from_csv_dict(cls, data: Dict[str, Any], timestamp: Optional[datetime] = None) -> Trade:
        """Create Trade from CSV dictionary format.
        
        Args:
            data: Dictionary with keys from llm_trade_log.csv
            timestamp: Optional timestamp if not in data
            
        Returns:
            Trade instance
        """
        # Handle timestamp from Date column or parameter
        if timestamp is None and 'Date' in data:
            # This would need proper timezone parsing in real implementation
            timestamp = datetime.fromisoformat(str(data['Date']).replace(' PST', '').replace(' PDT', ''))
        elif timestamp is None:
            timestamp = datetime.now()
        
        # Determine action based on reason or other indicators
        reason_raw = data.get('Reason', '')
        # Handle case where Reason might be NaN/float or other non-string type
        try:
            if reason_raw is None or (hasattr(reason_raw, '__class__') and 'float' in str(reason_raw.__class__) and str(reason_raw).lower() == 'nan'):
                reason = ''
            elif isinstance(reason_raw, str):
                reason = reason_raw.lower()
            else:
                reason = str(reason_raw).lower()
        except (AttributeError, ValueError):
            reason = ''
        # Safe decimal conversion helper (define before use)
        def safe_decimal_convert(value, default_value=Decimal('0')):
            """Safely convert value to Decimal, handling errors gracefully."""
            if value is None:
                return default_value
            try:
                if isinstance(value, str):
                    value = value.strip()
                    if not value or value.lower() == 'nan' or value.lower() == 'none':
                        return default_value
                return Decimal(str(value))
            except (ValueError, TypeError, ArithmeticError):
                return default_value
        
        if 'sell' in reason or 'limit sell' in reason or 'market sell' in reason:
            action = 'SELL'
            # For sell trades, use the sell price and shares sold
            shares = safe_decimal_convert(data.get('Shares Bought', 0))  # This should be shares sold
            price = safe_decimal_convert(data.get('Buy Price', 0))  # This should be sell price
        else:
            action = 'BUY'
            shares = safe_decimal_convert(data.get('Shares Bought', 0))
            price = safe_decimal_convert(data.get('Buy Price', 0))
        
        return cls(
            ticker=str(data.get('Ticker', '')),
            action=action,
            shares=shares,
            price=price,
            timestamp=timestamp,
            cost_basis=safe_decimal_convert(data.get('Cost Basis', 0)),
            pnl=safe_decimal_convert(data.get('PnL', 0)),
            reason=data.get('Reason'),
            currency='CAD'  # Default currency
        )
    
    def calculate_cost_basis(self) -> Decimal:
        """Calculate cost basis for this trade.
        
        Returns:
            Cost basis (price * shares)
        """
        return (self.price * self.shares).quantize(Decimal('0.01'))
    
    def is_buy(self) -> bool:
        """Check if this is a buy trade.
        
        Returns:
            True if action is BUY
        """
        return self.action.upper() == 'BUY'
    
    def is_sell(self) -> bool:
        """Check if this is a sell trade.
        
        Returns:
            True if action is SELL
        """
        return self.action.upper() == 'SELL'