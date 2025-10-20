"""Supabase dual-write repository implementation.

This repository reads from Supabase (cloud source) but writes to both CSV and Supabase.
This provides cloud-first access with local CSV backup for reliability.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import logging

from .base_repository import BaseRepository, RepositoryError, DataValidationError, DataNotFoundError
from .csv_repository import CSVRepository
from .supabase_repository import SupabaseRepository
from ..models.portfolio import Position, PortfolioSnapshot
from ..models.trade import Trade
from ..models.market_data import MarketData

logger = logging.getLogger(__name__)


class SupabaseDualWriteRepository(BaseRepository):
    """Repository that reads from Supabase but writes to both CSV and Supabase.
    
    This provides cloud-first access while maintaining CSV backup for reliability.
    """
    
    def __init__(self, fund_name: str, data_directory: str = None, **kwargs):
        """Initialize Supabase dual-write repository.
        
        Args:
            fund_name: Name of the fund
            data_directory: Optional path to CSV data directory (defaults to trading_data/funds/{fund_name})
        """
        self.fund_name = fund_name
        
        if data_directory:
            self.data_directory = data_directory
            self.data_dir = data_directory  # Alias for compatibility
        else:
            # Default to trading_data/funds/{fund_name}
            self.data_directory = f"trading_data/funds/{fund_name}"
            self.data_dir = self.data_directory
        
        # Initialize Supabase repository (primary/read source)
        self.supabase_repo = SupabaseRepository(fund_name=fund_name)
        
        # Initialize CSV repository (backup write target)
        self.csv_repo = CSVRepository(fund_name=fund_name, data_directory=self.data_directory)
        
        logger.info(f"Initialized Supabase dual-write repository: Supabase read, CSV+Supabase write")
    
    def get_portfolio_data(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Get portfolio data from Supabase (primary source)."""
        return self.supabase_repo.get_portfolio_data(date_range)
    
    def get_latest_portfolio_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get latest portfolio snapshot from Supabase."""
        return self.supabase_repo.get_latest_portfolio_snapshot()
    
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot, is_trade_execution: bool = False) -> None:
        """Save portfolio snapshot to both Supabase and CSV."""
        try:
            # Save to Supabase first (primary)
            self.supabase_repo.save_portfolio_snapshot(snapshot, is_trade_execution)
            logger.info(f"Saved portfolio snapshot to Supabase")
            
            # Save to CSV (backup)
            self.csv_repo.save_portfolio_snapshot(snapshot, is_trade_execution)
            logger.info(f"Saved portfolio snapshot to CSV")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")
            raise RepositoryError(f"Failed to save portfolio snapshot: {e}") from e
    
    def get_trade_history(self, ticker: Optional[str] = None, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Get trade history from Supabase."""
        return self.supabase_repo.get_trade_history(ticker, date_range)
    
    def save_trade(self, trade: Trade) -> None:
        """Save trade to both Supabase and CSV."""
        try:
            # Save to Supabase first (primary)
            self.supabase_repo.save_trade(trade)
            logger.info(f"Saved trade to Supabase: {trade.ticker}")
            
            # Save to CSV (backup)
            self.csv_repo.save_trade(trade)
            logger.info(f"Saved trade to CSV: {trade.ticker}")
            
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise RepositoryError(f"Failed to save trade: {e}") from e
    
    def get_cash_balance(self, date: Optional[datetime] = None) -> Decimal:
        """Get cash balance from Supabase."""
        return self.supabase_repo.get_cash_balance(date)
    
    def save_cash_balance(self, balance: Decimal, date: Optional[datetime] = None) -> None:
        """Save cash balance to both Supabase and CSV."""
        try:
            # Save to Supabase first (primary)
            self.supabase_repo.save_cash_balance(balance, date)
            logger.info(f"Saved cash balance to Supabase: {balance}")
            
            # Save to CSV (backup)
            self.csv_repo.save_cash_balance(balance, date)
            logger.info(f"Saved cash balance to CSV: {balance}")
            
        except Exception as e:
            logger.error(f"Failed to save cash balance: {e}")
            raise RepositoryError(f"Failed to save cash balance: {e}") from e
    
    def get_market_data(self, ticker: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[MarketData]:
        """Get market data from Supabase."""
        return self.supabase_repo.get_market_data(ticker, date_range)
    
    def save_market_data(self, market_data: MarketData) -> None:
        """Save market data to both Supabase and CSV."""
        try:
            # Save to Supabase first (primary)
            self.supabase_repo.save_market_data(market_data)
            logger.info(f"Saved market data to Supabase: {market_data.ticker}")
            
            # Save to CSV (backup)
            self.csv_repo.save_market_data(market_data)
            logger.info(f"Saved market data to CSV: {market_data.ticker}")
            
        except Exception as e:
            logger.error(f"Failed to save market data: {e}")
            raise RepositoryError(f"Failed to save market data: {e}") from e
    
    def test_connection(self) -> bool:
        """Test both Supabase and CSV connections."""
        supabase_ok = self.supabase_repo.test_connection()
        csv_ok = True  # CSV is always available
        
        logger.info(f"Connection test - Supabase: {supabase_ok}, CSV: {csv_ok}")
        return supabase_ok and csv_ok
    
    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        """Get positions for a specific ticker from Supabase."""
        return self.supabase_repo.get_positions_by_ticker(ticker)
    
    def backup_data(self, backup_path: str) -> bool:
        """Backup data using CSV repository."""
        return self.csv_repo.backup_data(backup_path)
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore data using CSV repository."""
        return self.csv_repo.restore_from_backup(backup_path)
    
    def validate_data_integrity(self) -> bool:
        """Validate data integrity using Supabase repository."""
        return self.supabase_repo.validate_data_integrity()
    
    def update_ticker_in_future_snapshots(self, ticker: str, trade_timestamp: datetime) -> None:
        """Update a ticker's position in all snapshots after the trade timestamp.
        
        This method calls both underlying repositories to ensure consistency.
        
        Args:
            ticker: Ticker symbol to update
            trade_timestamp: Timestamp of the backdated trade
            
        Raises:
            RepositoryError: If update operation fails
        """
        try:
            logger.info(f"Updating {ticker} positions in both Supabase and CSV repositories")
            
            # Update Supabase repository
            self.supabase_repo.update_ticker_in_future_snapshots(ticker, trade_timestamp)
            logger.info(f"Updated {ticker} positions in Supabase")
            
            # Update CSV repository
            self.csv_repo.update_ticker_in_future_snapshots(ticker, trade_timestamp)
            logger.info(f"Updated {ticker} positions in CSV")
            
        except Exception as e:
            logger.error(f"Failed to update ticker {ticker} in dual-write repositories: {e}")
            raise RepositoryError(f"Failed to update ticker {ticker} in dual-write repositories: {e}") from e