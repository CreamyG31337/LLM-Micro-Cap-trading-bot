"""Portfolio data models."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
import json


@dataclass
class Position:
    """Represents a single position in the portfolio.
    
    This model is designed to work with both CSV and database backends,
    supporting serialization to/from dictionaries for CSV rows and JSON.
    """
    ticker: str
    shares: Decimal
    avg_price: Decimal
    cost_basis: Decimal
    currency: str = "CAD"
    company: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    position_id: Optional[str] = None  # For database primary key
    
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
        self.avg_price = safe_decimal_convert(self.avg_price, Decimal('0'))
        self.cost_basis = safe_decimal_convert(self.cost_basis, Decimal('0'))
        
        # Convert optional fields (can be None)
        self.current_price = safe_decimal_convert(self.current_price, None) if self.current_price is not None else None
        self.market_value = safe_decimal_convert(self.market_value, None) if self.market_value is not None else None
        self.unrealized_pnl = safe_decimal_convert(self.unrealized_pnl, None) if self.unrealized_pnl is not None else None
        self.stop_loss = safe_decimal_convert(self.stop_loss, None) if self.stop_loss is not None else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization.
        
        Returns:
            Dictionary representation compatible with CSV format
        """
        from decimal import ROUND_HALF_UP
        
        return {
            'ticker': self.ticker,
            'shares': float(self.shares.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),  # 4 decimal places for shares
            'avg_price': float(self.avg_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),  # 2 decimal places for prices
            'cost_basis': float(self.cost_basis.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'currency': self.currency,
            'company': self.company or '',
            'current_price': float(self.current_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.current_price is not None else 0.0,
            'market_value': float(self.market_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.market_value is not None else 0.0,
            'unrealized_pnl': float(self.unrealized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.unrealized_pnl is not None else 0.0,
            'stop_loss': float(self.stop_loss.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.stop_loss is not None else 0.0,
            'position_id': self.position_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Position:
        """Create Position from dictionary (CSV row or database record).
        
        Args:
            data: Dictionary containing position data
            
        Returns:
            Position instance
        """
        return cls(
            ticker=str(data.get('ticker', '')),
            shares=Decimal(str(data.get('shares', 0))),
            avg_price=Decimal(str(data.get('avg_price', 0))),
            cost_basis=Decimal(str(data.get('cost_basis', 0))),
            currency=str(data.get('currency', 'CAD')),
            company=data.get('company'),
            current_price=Decimal(str(data['current_price'])) if data.get('current_price') else None,
            market_value=Decimal(str(data['market_value'])) if data.get('market_value') else None,
            unrealized_pnl=Decimal(str(data['unrealized_pnl'])) if data.get('unrealized_pnl') else None,
            stop_loss=Decimal(str(data['stop_loss'])) if data.get('stop_loss') else None,
            position_id=data.get('position_id')
        )
    
    def to_csv_dict(self) -> Dict[str, Any]:
        """Convert to dictionary matching current CSV format.
        
        Returns:
            Dictionary with keys matching llm_portfolio_update.csv format
        """
        from decimal import ROUND_HALF_UP
        
        return {
            'Ticker': self.ticker,
            'Shares': float(self.shares.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)),  # 4 decimal places for shares
            'Average Price': float(self.avg_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),  # 2 decimal places for prices
            'Cost Basis': float(self.cost_basis.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'Currency': self.currency,
            'Company': self.company or '',
            'Current Price': float(self.current_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.current_price is not None else 0.0,
            'Total Value': float(self.market_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.market_value is not None else 0.0,
            'PnL': float(self.unrealized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.unrealized_pnl is not None else 0.0,
            'Stop Loss': float(self.stop_loss.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) if self.stop_loss is not None else 0.0
        }
    
    @classmethod
    def from_csv_dict(cls, data: Dict[str, Any]) -> Position:
        """Create Position from CSV dictionary format.

        Args:
            data: Dictionary with keys from llm_portfolio_update.csv

        Returns:
            Position instance
        """
        shares = Decimal(str(data.get('Shares', 0)))
        avg_price = Decimal(str(data.get('Average Price', 0)))
        current_price = Decimal(str(data['Current Price'])) if data.get('Current Price') else None

        # Calculate proper unrealized P&L instead of using the potentially incorrect CSV value
        unrealized_pnl = None
        market_value = None
        if current_price is not None:
            unrealized_pnl = (current_price - avg_price) * shares
            market_value = current_price * shares

        return cls(
            ticker=str(data.get('Ticker', '')),
            shares=shares,
            avg_price=avg_price,
            cost_basis=Decimal(str(data.get('Cost Basis', 0))),
            currency=str(data.get('Currency', 'CAD')),
            company=data.get('Company'),
            current_price=current_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            stop_loss=Decimal(str(data['Stop Loss'])) if data.get('Stop Loss') else None
        )


@dataclass
class PortfolioSnapshot:
    """Represents a complete portfolio snapshot at a specific point in time.
    
    This model aggregates all positions and metadata for a portfolio state,
    designed for both CSV and database storage.
    """
    positions: List[Position]
    timestamp: datetime
    total_value: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    snapshot_id: Optional[str] = None  # For database primary key
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (web API).
        
        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            'positions': [pos.to_dict() for pos in self.positions],
            'timestamp': self.timestamp.isoformat(),
            'total_value': float(self.total_value) if self.total_value is not None else None,
            'cash_balance': float(self.cash_balance) if self.cash_balance is not None else None,
            'snapshot_id': self.snapshot_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PortfolioSnapshot:
        """Create PortfolioSnapshot from dictionary.
        
        Args:
            data: Dictionary containing snapshot data
            
        Returns:
            PortfolioSnapshot instance
        """
        positions = [Position.from_dict(pos_data) for pos_data in data.get('positions', [])]
        timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            positions=positions,
            timestamp=timestamp,
            total_value=Decimal(str(data['total_value'])) if data.get('total_value') is not None else None,
            cash_balance=Decimal(str(data['cash_balance'])) if data.get('cash_balance') is not None else None,
            snapshot_id=data.get('snapshot_id')
        )
    
    def calculate_total_value(self) -> Decimal:
        """Calculate total portfolio value from positions.
        
        Returns:
            Total value of all positions
        """
        total = Decimal('0')
        for position in self.positions:
            if position.market_value is not None:
                total += position.market_value
        return total
    
    def get_position_by_ticker(self, ticker: str) -> Optional[Position]:
        """Get position by ticker symbol.
        
        Args:
            ticker: Ticker symbol to search for
            
        Returns:
            Position if found, None otherwise
        """
        for position in self.positions:
            if position.ticker == ticker:
                return position
        return None
    
    def add_position(self, position: Position) -> None:
        """Add a position to the snapshot.
        
        Args:
            position: Position to add
        """
        # Check if position already exists and update it
        existing = self.get_position_by_ticker(position.ticker)
        if existing:
            # Update existing position
            idx = self.positions.index(existing)
            self.positions[idx] = position
        else:
            # Add new position
            self.positions.append(position)
    
    def remove_position(self, ticker: str) -> bool:
        """Remove position by ticker.
        
        Args:
            ticker: Ticker symbol to remove
            
        Returns:
            True if position was removed, False if not found
        """
        position = self.get_position_by_ticker(ticker)
        if position:
            self.positions.remove(position)
            return True
        return False