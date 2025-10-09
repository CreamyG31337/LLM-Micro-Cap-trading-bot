"""Write coordinator for dual-write operations to CSV and Supabase.

This module provides the WriteCoordinator class that handles writing data
to both CSV and Supabase repositories simultaneously, ensuring data consistency
across both storage systems.
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime

from data.models.trade import Trade
from data.models.portfolio import PortfolioSnapshot, Position
from data.repositories.base_repository import BaseRepository
from data.repositories.csv_repository import CSVRepository
from data.repositories.supabase_repository import SupabaseRepository

logger = logging.getLogger(__name__)


@dataclass
class WriteResult:
    """Result of a dual-write operation."""
    csv_success: bool
    supabase_success: bool
    csv_error: Optional[str] = None
    supabase_error: Optional[str] = None
    
    @property
    def all_successful(self) -> bool:
        """Check if both writes were successful."""
        return self.csv_success and self.supabase_success
    
    @property
    def any_successful(self) -> bool:
        """Check if at least one write was successful."""
        return self.csv_success or self.supabase_success
    
    @property
    def has_failures(self) -> bool:
        """Check if any writes failed."""
        return not self.csv_success or not self.supabase_success
    
    def get_failure_messages(self) -> List[str]:
        """Get list of failure messages."""
        failures = []
        if not self.csv_success and self.csv_error:
            failures.append(f"CSV: {self.csv_error}")
        if not self.supabase_success and self.supabase_error:
            failures.append(f"Supabase: {self.supabase_error}")
        return failures


class WriteCoordinator:
    """Coordinates dual writes to both CSV and Supabase repositories.
    
    This class ensures that all write operations are performed on both
    CSV and Supabase repositories simultaneously, providing data redundancy
    and consistency across both storage systems.
    """
    
    def __init__(self, csv_repo: CSVRepository, supabase_repo: SupabaseRepository):
        """Initialize the write coordinator.
        
        Args:
            csv_repo: CSV repository instance
            supabase_repo: Supabase repository instance
        """
        self.csv_repo = csv_repo
        self.supabase_repo = supabase_repo
        self.logger = logging.getLogger(__name__)
    
    def save_trade(self, trade: Trade) -> WriteResult:
        """Save a trade to both CSV and Supabase repositories.
        
        Args:
            trade: Trade object to save
            
        Returns:
            WriteResult indicating success/failure of both operations
        """
        self.logger.info(f"Saving trade to both repositories: {trade.ticker} {trade.action}")
        
        csv_success = False
        supabase_success = False
        csv_error = None
        supabase_error = None
        
        # Try CSV write
        try:
            self.csv_repo.save_trade(trade)
            csv_success = True
            self.logger.debug(f"CSV write successful for trade {trade.ticker}")
        except Exception as e:
            csv_error = str(e)
            self.logger.error(f"CSV write failed for trade {trade.ticker}: {e}")
        
        # Try Supabase write
        try:
            self.supabase_repo.save_trade(trade)
            supabase_success = True
            self.logger.debug(f"Supabase write successful for trade {trade.ticker}")
        except Exception as e:
            supabase_error = str(e)
            self.logger.error(f"Supabase write failed for trade {trade.ticker}: {e}")
        
        # Log results
        if csv_success and supabase_success:
            self.logger.info(f"Trade {trade.ticker} saved successfully to both repositories")
        elif csv_success or supabase_success:
            self.logger.warning(f"Trade {trade.ticker} saved to only one repository (partial success)")
        else:
            self.logger.error(f"Trade {trade.ticker} failed to save to both repositories")
        
        return WriteResult(
            csv_success=csv_success,
            supabase_success=supabase_success,
            csv_error=csv_error,
            supabase_error=supabase_error
        )
    
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> WriteResult:
        """Save a portfolio snapshot to both CSV and Supabase repositories.
        
        Args:
            snapshot: PortfolioSnapshot to save
            
        Returns:
            WriteResult indicating success/failure of both operations
        """
        self.logger.info(f"Saving portfolio snapshot to both repositories: {snapshot.timestamp}")
        
        csv_success = False
        supabase_success = False
        csv_error = None
        supabase_error = None
        
        # Try CSV write
        try:
            self.csv_repo.save_portfolio_snapshot(snapshot)
            csv_success = True
            self.logger.debug("CSV write successful for portfolio snapshot")
        except Exception as e:
            csv_error = str(e)
            self.logger.error(f"CSV write failed for portfolio snapshot: {e}")
        
        # Try Supabase write
        try:
            self.supabase_repo.save_portfolio_snapshot(snapshot)
            supabase_success = True
            self.logger.debug("Supabase write successful for portfolio snapshot")
        except Exception as e:
            supabase_error = str(e)
            self.logger.error(f"Supabase write failed for portfolio snapshot: {e}")
        
        # Log results
        if csv_success and supabase_success:
            self.logger.info("Portfolio snapshot saved successfully to both repositories")
        elif csv_success or supabase_success:
            self.logger.warning("Portfolio snapshot saved to only one repository (partial success)")
        else:
            self.logger.error("Portfolio snapshot failed to save to both repositories")
        
        return WriteResult(
            csv_success=csv_success,
            supabase_success=supabase_success,
            csv_error=csv_error,
            supabase_error=supabase_error
        )
    
    def update_daily_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> WriteResult:
        """Update daily portfolio snapshot in both repositories.
        
        Args:
            snapshot: PortfolioSnapshot to update
            
        Returns:
            WriteResult indicating success/failure of both operations
        """
        self.logger.info(f"Updating daily portfolio snapshot in both repositories: {snapshot.timestamp}")
        
        csv_success = False
        supabase_success = False
        csv_error = None
        supabase_error = None
        
        # Try CSV write
        try:
            self.csv_repo.update_daily_portfolio_snapshot(snapshot)
            csv_success = True
            self.logger.debug("CSV update successful for daily portfolio snapshot")
        except Exception as e:
            csv_error = str(e)
            self.logger.error(f"CSV update failed for daily portfolio snapshot: {e}")
        
        # Try Supabase write
        try:
            self.supabase_repo.update_daily_portfolio_snapshot(snapshot)
            supabase_success = True
            self.logger.debug("Supabase update successful for daily portfolio snapshot")
        except Exception as e:
            supabase_error = str(e)
            self.logger.error(f"Supabase update failed for daily portfolio snapshot: {e}")
        
        # Log results
        if csv_success and supabase_success:
            self.logger.info("Daily portfolio snapshot updated successfully in both repositories")
        elif csv_success or supabase_success:
            self.logger.warning("Daily portfolio snapshot updated in only one repository (partial success)")
        else:
            self.logger.error("Daily portfolio snapshot failed to update in both repositories")
        
        return WriteResult(
            csv_success=csv_success,
            supabase_success=supabase_success,
            csv_error=csv_error,
            supabase_error=supabase_error
        )
    
    def get_latest_portfolio_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the latest portfolio snapshot from the primary repository.
        
        This method uses the CSV repository as the primary source for reads.
        In the future, this could be made configurable.
        
        Returns:
            Latest PortfolioSnapshot or None if not found
        """
        try:
            return self.csv_repo.get_latest_portfolio_snapshot()
        except Exception as e:
            self.logger.error(f"Failed to get latest portfolio snapshot: {e}")
            return None
    
    def get_trade_history(self, ticker: Optional[str] = None, 
                         date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Get trade history from the primary repository.
        
        This method uses the CSV repository as the primary source for reads.
        In the future, this could be made configurable.
        
        Args:
            ticker: Optional ticker symbol to filter by
            date_range: Optional date range to filter by
            
        Returns:
            List of Trade objects
        """
        try:
            return self.csv_repo.get_trade_history(ticker, date_range)
        except Exception as e:
            self.logger.error(f"Failed to get trade history: {e}")
            return []
    
    def validate_sync(self) -> bool:
        """Validate that both repositories are in sync.
        
        This is a basic validation that checks if both repositories
        have the same number of trades and portfolio snapshots.
        
        Returns:
            True if repositories appear to be in sync, False otherwise
        """
        try:
            # Check trade counts
            csv_trades = self.csv_repo.get_trade_history()
            supabase_trades = self.supabase_repo.get_trade_history()
            
            if len(csv_trades) != len(supabase_trades):
                self.logger.warning(f"Trade count mismatch: CSV={len(csv_trades)}, Supabase={len(supabase_trades)}")
                return False
            
            # Check portfolio snapshots
            csv_snapshot = self.csv_repo.get_latest_portfolio_snapshot()
            supabase_snapshot = self.supabase_repo.get_latest_portfolio_snapshot()
            
            if csv_snapshot is None and supabase_snapshot is None:
                return True  # Both empty, considered in sync
            
            if csv_snapshot is None or supabase_snapshot is None:
                self.logger.warning("Portfolio snapshot mismatch: one repository has data, other doesn't")
                return False
            
            # Basic timestamp comparison
            if abs((csv_snapshot.timestamp - supabase_snapshot.timestamp).total_seconds()) > 60:
                self.logger.warning("Portfolio snapshot timestamps differ by more than 1 minute")
                return False
            
            self.logger.info("Repositories appear to be in sync")
            return True
            
        except Exception as e:
            self.logger.error(f"Sync validation failed: {e}")
            return False
