"""Market data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional, Any
import pandas as pd


@dataclass
class MarketData:
    """Represents market data for a specific ticker and date.
    
    This model is designed to work with both Yahoo Finance and Stooq data,
    providing a consistent interface for price data across different sources.
    """
    ticker: str
    date: datetime
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    adj_close_price: Optional[Decimal] = None
    volume: Optional[int] = None
    source: str = "unknown"  # "yahoo", "stooq", "manual", etc.
    data_id: Optional[str] = None  # For database primary key
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CSV/JSON serialization.
        
        Returns:
            Dictionary representation compatible with CSV format
        """
        return {
            'ticker': self.ticker,
            'date': self.date.isoformat(),
            'open': float(self.open_price) if self.open_price is not None else None,
            'high': float(self.high_price) if self.high_price is not None else None,
            'low': float(self.low_price) if self.low_price is not None else None,
            'close': float(self.close_price) if self.close_price is not None else None,
            'adj_close': float(self.adj_close_price) if self.adj_close_price is not None else None,
            'volume': self.volume,
            'source': self.source,
            'data_id': self.data_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MarketData:
        """Create MarketData from dictionary.
        
        Args:
            data: Dictionary containing market data
            
        Returns:
            MarketData instance
        """
        date = data['date']
        if isinstance(date, str):
            date = datetime.fromisoformat(date)
        
        return cls(
            ticker=str(data.get('ticker', '')),
            date=date,
            open_price=Decimal(str(data['open'])) if data.get('open') is not None else None,
            high_price=Decimal(str(data['high'])) if data.get('high') is not None else None,
            low_price=Decimal(str(data['low'])) if data.get('low') is not None else None,
            close_price=Decimal(str(data['close'])) if data.get('close') is not None else None,
            adj_close_price=Decimal(str(data['adj_close'])) if data.get('adj_close') is not None else None,
            volume=int(data['volume']) if data.get('volume') is not None else None,
            source=str(data.get('source', 'unknown')),
            data_id=data.get('data_id')
        )
    
    @classmethod
    def from_yahoo_series(cls, ticker: str, date: datetime, series: pd.Series) -> MarketData:
        """Create MarketData from Yahoo Finance pandas Series.
        
        Args:
            ticker: Ticker symbol
            date: Date for this data point
            series: Pandas Series with OHLCV data
            
        Returns:
            MarketData instance
        """
        return cls(
            ticker=ticker,
            date=date,
            open_price=Decimal(str(series.get('Open', 0))) if pd.notna(series.get('Open')) else None,
            high_price=Decimal(str(series.get('High', 0))) if pd.notna(series.get('High')) else None,
            low_price=Decimal(str(series.get('Low', 0))) if pd.notna(series.get('Low')) else None,
            close_price=Decimal(str(series.get('Close', 0))) if pd.notna(series.get('Close')) else None,
            adj_close_price=Decimal(str(series.get('Adj Close', 0))) if pd.notna(series.get('Adj Close')) else None,
            volume=int(series.get('Volume', 0)) if pd.notna(series.get('Volume')) else None,
            source="yahoo"
        )
    
    @classmethod
    def from_stooq_series(cls, ticker: str, date: datetime, series: pd.Series) -> MarketData:
        """Create MarketData from Stooq pandas Series.
        
        Args:
            ticker: Ticker symbol
            date: Date for this data point
            series: Pandas Series with OHLCV data
            
        Returns:
            MarketData instance
        """
        return cls(
            ticker=ticker,
            date=date,
            open_price=Decimal(str(series.get('Open', 0))) if pd.notna(series.get('Open')) else None,
            high_price=Decimal(str(series.get('High', 0))) if pd.notna(series.get('High')) else None,
            low_price=Decimal(str(series.get('Low', 0))) if pd.notna(series.get('Low')) else None,
            close_price=Decimal(str(series.get('Close', 0))) if pd.notna(series.get('Close')) else None,
            adj_close_price=Decimal(str(series.get('Close', 0))) if pd.notna(series.get('Close')) else None,  # Stooq: Adj Close = Close
            volume=int(series.get('Volume', 0)) if pd.notna(series.get('Volume')) else None,
            source="stooq"
        )
    
    def get_price(self, price_type: str = "close") -> Optional[Decimal]:
        """Get price by type.
        
        Args:
            price_type: Type of price to get ("open", "high", "low", "close", "adj_close")
            
        Returns:
            Price value or None if not available
        """
        price_map = {
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "adj_close": self.adj_close_price
        }
        return price_map.get(price_type.lower())
    
    def has_complete_ohlc(self) -> bool:
        """Check if this data point has complete OHLC data.
        
        Returns:
            True if all OHLC prices are available
        """
        return all([
            self.open_price is not None,
            self.high_price is not None,
            self.low_price is not None,
            self.close_price is not None
        ])