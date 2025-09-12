"""Abstract base repository interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from ..models.portfolio import Position, PortfolioSnapshot
from ..models.trade import Trade
from ..models.market_data import MarketData


class BaseRepository(ABC):
    """Abstract base class for data access operations.
    
    This interface defines the contract for all data access implementations,
    allowing the system to work with different backends (CSV, database, etc.)
    without changing business logic.
    """
    
    @abstractmethod
    def get_portfolio_data(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Retrieve portfolio snapshots within optional date range.
        
        Args:
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of PortfolioSnapshot objects
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Save a portfolio snapshot.
        
        Args:
            snapshot: PortfolioSnapshot to save
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    def get_latest_portfolio_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot.
        
        Returns:
            Latest PortfolioSnapshot or None if no data exists
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    def get_trade_history(self, ticker: Optional[str] = None, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Retrieve trade history with optional filtering.
        
        Args:
            ticker: Optional ticker symbol to filter by
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of Trade objects
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    def save_trade(self, trade: Trade) -> None:
        """Save a trade record.
        
        Args:
            trade: Trade to save
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        """Get all positions for a specific ticker across time.
        
        Args:
            ticker: Ticker symbol to search for
            
        Returns:
            List of Position objects for the ticker
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    def get_market_data(self, ticker: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[MarketData]:
        """Retrieve market data for a ticker within optional date range.
        
        Args:
            ticker: Ticker symbol
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of MarketData objects
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    def save_market_data(self, market_data: MarketData) -> None:
        """Save market data.
        
        Args:
            market_data: MarketData to save
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    def backup_data(self, backup_path: str) -> None:
        """Create a backup of all data.
        
        Args:
            backup_path: Path where backup should be created
            
        Raises:
            RepositoryError: If backup operation fails
        """
        pass
    
    @abstractmethod
    def restore_from_backup(self, backup_path: str) -> None:
        """Restore data from a backup.
        
        Args:
            backup_path: Path to backup file
            
        Raises:
            RepositoryError: If restore operation fails
        """
        pass
    
    @abstractmethod
    def validate_data_integrity(self) -> List[str]:
        """Validate data integrity and return list of issues found.
        
        Returns:
            List of validation error messages (empty if no issues)
            
        Raises:
            RepositoryError: If validation check fails
        """
        pass


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class DataValidationError(RepositoryError):
    """Exception raised when data validation fails."""
    pass


class DataNotFoundError(RepositoryError):
    """Exception raised when requested data is not found."""
    pass


class DataCorruptionError(RepositoryError):
    """Exception raised when data corruption is detected."""
    pass