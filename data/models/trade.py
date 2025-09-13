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
        # Convert string values to Decimal for financial fields
        if isinstance(self.shares, str):
            self.shares = Decimal(self.shares)
        if isinstance(self.price, str):
            self.price = Decimal(self.price)
        if isinstance(self.cost_basis, str):
            self.cost_basis = Decimal(self.cost_basis)
        if isinstance(self.pnl, str):
            self.pnl = Decimal(self.pnl)
    
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
        reason = data.get('Reason', '').lower()
        if 'sell' in reason or 'limit sell' in reason or 'market sell' in reason:
            action = 'SELL'
            # For sell trades, use the sell price and shares sold
            shares = Decimal(str(data.get('Shares Bought', 0)))  # This should be shares sold
            price = Decimal(str(data.get('Buy Price', 0)))  # This should be sell price
        else:
            action = 'BUY'
            shares = Decimal(str(data.get('Shares Bought', 0)))
            price = Decimal(str(data.get('Buy Price', 0)))
        
        return cls(
            ticker=str(data.get('Ticker', '')),
            action=action,
            shares=shares,
            price=price,
            timestamp=timestamp,
            cost_basis=Decimal(str(data.get('Cost Basis', 0))),
            pnl=Decimal(str(data.get('PnL', 0))),
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