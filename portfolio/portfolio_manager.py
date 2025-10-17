"""Portfolio management module.

This module provides the PortfolioManager class for handling portfolio CRUD operations
using the repository pattern. It abstracts portfolio data access and provides
high-level operations for loading, saving, and updating portfolio data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from data.repositories.base_repository import BaseRepository, RepositoryError
from data.models.portfolio import Position, PortfolioSnapshot
from data.models.trade import Trade
from .fund_manager import Fund

logger = logging.getLogger(__name__)


class PortfolioManagerError(Exception):
    """Base exception for portfolio manager operations."""
    pass


class PortfolioManager:
    """Manages portfolio data using the repository pattern.
    
    This class provides high-level portfolio operations while abstracting
    the underlying data storage mechanism through the repository interface.
    It supports both CSV and future database backends seamlessly.
    """
    
    def __init__(self, repository: BaseRepository, fund: Fund):
        """Initialize portfolio manager.
        
        Args:
            repository: Repository implementation for data access
            fund: The fund being managed
        """
        self.repository = repository
        self.fund = fund
        logger.info(f"Portfolio manager initialized for fund '{self.fund.name}' with {type(repository).__name__}")
    
    def load_portfolio(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Load portfolio snapshots from repository with duplicate detection.
        
        Args:
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of PortfolioSnapshot objects sorted by timestamp
            
        Raises:
            PortfolioManagerError: If loading fails
        """
        try:
            logger.info(f"Loading portfolio data with date range: {date_range}")
            snapshots = self.repository.get_portfolio_data(date_range)
            logger.info(f"Loaded {len(snapshots)} portfolio snapshots")
            
            # Validate for duplicates
            from collections import defaultdict
            date_counts = defaultdict(list)
            for snapshot in snapshots:
                date_only = snapshot.timestamp.date()
                date_counts[date_only].append(snapshot.timestamp)
            
            # Check for duplicates
            duplicates_found = False
            for date_key, timestamps in date_counts.items():
                if len(timestamps) > 1:
                    duplicates_found = True
                    logger.error(f"DUPLICATE SNAPSHOTS DETECTED for {date_key}:")
                    for ts in timestamps:
                        logger.error(f"   - {ts}")
            
            if duplicates_found:
                # Option 1: Crash the app
                raise PortfolioManagerError(
                    "Duplicate portfolio snapshots detected! "
                    "Multiple snapshots found for the same date. "
                    "This will cause incorrect P&L calculations. "
                    "Please run the rebuild script to fix."
                )
                
                # Option 2: Just warn (comment out the raise above)
                # logger.warning("⚠️  Duplicate snapshots detected but continuing...")
            
            return snapshots
            
        except RepositoryError as e:
            logger.error(f"Failed to load portfolio: {e}")
            raise PortfolioManagerError(f"Failed to load portfolio: {e}") from e
    
    def get_latest_portfolio(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot.
        
        Returns:
            Latest PortfolioSnapshot or None if no data exists
            
        Raises:
            PortfolioManagerError: If loading fails
        """
        try:
            logger.debug("Loading latest portfolio snapshot")
            snapshot = self.repository.get_latest_portfolio_snapshot()
            if snapshot:
                logger.debug(f"Loaded latest portfolio with {len(snapshot.positions)} positions")
            else:
                logger.debug("No portfolio data found")
            return snapshot
            
        except RepositoryError as e:
            logger.error(f"Failed to load latest portfolio: {e}")
            raise PortfolioManagerError(f"Failed to load latest portfolio: {e}") from e
    
    def save_portfolio(self, snapshot: PortfolioSnapshot) -> None:
        """Save portfolio snapshot to repository.
        
        Args:
            snapshot: PortfolioSnapshot to save
            
        Raises:
            PortfolioManagerError: If saving fails
        """
        try:
            logger.info(f"Saving portfolio snapshot with {len(snapshot.positions)} positions")
            
            # Validate snapshot before saving
            self._validate_portfolio_snapshot(snapshot)
            
            # Calculate total value if not set
            if snapshot.total_value is None:
                snapshot.total_value = snapshot.calculate_total_value()
            
            self.repository.save_portfolio_snapshot(snapshot)
            logger.info("Portfolio snapshot saved successfully")
            
        except RepositoryError as e:
            logger.error(f"Failed to save portfolio: {e}")
            raise PortfolioManagerError(f"Failed to save portfolio: {e}") from e
    
    def update_position(self, ticker: str, shares: Decimal, avg_price: Decimal, 
                       current_price: Optional[Decimal] = None, 
                       company: Optional[str] = None,
                       currency: str = "CAD") -> PortfolioSnapshot:
        """Update or add a position in the latest portfolio snapshot.
        
        Args:
            ticker: Ticker symbol
            shares: Number of shares
            avg_price: Average price per share
            current_price: Current market price (optional)
            company: Company name (optional)
            currency: Currency code
            
        Returns:
            Updated PortfolioSnapshot
            
        Raises:
            PortfolioManagerError: If update fails
        """
        try:
            logger.info(f"Updating position: {ticker} {shares} shares @ {avg_price}")
            
            # Get latest portfolio or create new one
            latest = self.get_latest_portfolio()
            if latest is None:
                latest = PortfolioSnapshot(
                    positions=[],
                    timestamp=datetime.now()
                )
            
            # Calculate cost basis and market value
            cost_basis = (avg_price * shares).quantize(Decimal('0.01'))
            market_value = None
            unrealized_pnl = None
            
            if current_price is not None:
                market_value = (current_price * shares).quantize(Decimal('0.01'))
                unrealized_pnl = (market_value - cost_basis).quantize(Decimal('0.01'))
            
            # Create or update position
            position = Position(
                ticker=ticker,
                shares=shares,
                avg_price=avg_price,
                cost_basis=cost_basis,
                currency=currency,
                company=company,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl
            )
            
            # Add/update position in snapshot
            latest.add_position(position)
            latest.timestamp = datetime.now()  # Update timestamp
            
            # Save updated snapshot
            self.save_portfolio(latest)
            
            logger.info(f"Position updated successfully: {ticker}")
            return latest
            
        except Exception as e:
            logger.error(f"Failed to update position {ticker}: {e}")
            raise PortfolioManagerError(f"Failed to update position {ticker}: {e}") from e
    
    def remove_position(self, ticker: str) -> Optional[PortfolioSnapshot]:
        """Remove a position from the latest portfolio snapshot.
        
        Args:
            ticker: Ticker symbol to remove
            
        Returns:
            Updated PortfolioSnapshot or None if no portfolio exists
            
        Raises:
            PortfolioManagerError: If removal fails
        """
        try:
            logger.info(f"Removing position: {ticker}")
            
            # Get latest portfolio
            latest = self.get_latest_portfolio()
            if latest is None:
                logger.warning("No portfolio found to remove position from")
                return None
            
            # Remove position
            removed = latest.remove_position(ticker)
            if not removed:
                logger.warning(f"Position {ticker} not found in portfolio")
                return latest
            
            # Update timestamp and save
            latest.timestamp = datetime.now()
            self.save_portfolio(latest)
            
            logger.info(f"Position removed successfully: {ticker}")
            return latest
            
        except Exception as e:
            logger.error(f"Failed to remove position {ticker}: {e}")
            raise PortfolioManagerError(f"Failed to remove position {ticker}: {e}") from e
    
    def get_position_history(self, ticker: str) -> List[Position]:
        """Get historical positions for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            List of Position objects for the ticker across time
            
        Raises:
            PortfolioManagerError: If retrieval fails
        """
        try:
            logger.info(f"Getting position history for: {ticker}")
            positions = self.repository.get_positions_by_ticker(ticker)
            logger.info(f"Found {len(positions)} historical positions for {ticker}")
            return positions
            
        except RepositoryError as e:
            logger.error(f"Failed to get position history for {ticker}: {e}")
            raise PortfolioManagerError(f"Failed to get position history for {ticker}: {e}") from e
    
    def calculate_portfolio_metrics(self, snapshot: Optional[PortfolioSnapshot] = None) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics.
        
        Args:
            snapshot: Portfolio snapshot to analyze (uses latest if None)
            
        Returns:
            Dictionary containing portfolio metrics
            
        Raises:
            PortfolioManagerError: If calculation fails
        """
        try:
            if snapshot is None:
                snapshot = self.get_latest_portfolio()
                if snapshot is None:
                    return {
                        'total_positions': 0,
                        'total_value': Decimal('0'),
                        'total_cost_basis': Decimal('0'),
                        'total_unrealized_pnl': Decimal('0'),
                        'positions_with_gains': 0,
                        'positions_with_losses': 0,
                        'largest_position_value': Decimal('0'),
                        'largest_position_ticker': None
                    }
            
            logger.info("Calculating portfolio metrics")
            
            total_value = Decimal('0')
            total_cost_basis = Decimal('0')
            total_unrealized_pnl = Decimal('0')
            positions_with_gains = 0
            positions_with_losses = 0
            largest_position_value = Decimal('0')
            largest_position_ticker = None
            
            for position in snapshot.positions:
                # Add to totals
                total_cost_basis += position.cost_basis
                
                if position.market_value is not None:
                    total_value += position.market_value
                    
                    # Track largest position
                    if position.market_value > largest_position_value:
                        largest_position_value = position.market_value
                        largest_position_ticker = position.ticker
                
                if position.unrealized_pnl is not None:
                    total_unrealized_pnl += position.unrealized_pnl
                    
                    # Count gains/losses
                    if position.unrealized_pnl > 0:
                        positions_with_gains += 1
                    elif position.unrealized_pnl < 0:
                        positions_with_losses += 1
            
            metrics = {
                'total_positions': len(snapshot.positions),
                'total_value': total_value,
                'total_cost_basis': total_cost_basis,
                'total_unrealized_pnl': total_unrealized_pnl,
                'positions_with_gains': positions_with_gains,
                'positions_with_losses': positions_with_losses,
                'largest_position_value': largest_position_value,
                'largest_position_ticker': largest_position_ticker,
                'snapshot_timestamp': snapshot.timestamp
            }
            
            logger.info(f"Portfolio metrics calculated: {metrics['total_positions']} positions, "
                       f"${metrics['total_value']} total value")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate portfolio metrics: {e}")
            raise PortfolioManagerError(f"Failed to calculate portfolio metrics: {e}") from e
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get a comprehensive portfolio summary.
        
        Returns:
            Dictionary containing portfolio summary information
            
        Raises:
            PortfolioManagerError: If summary generation fails
        """
        try:
            logger.info("Generating portfolio summary")
            
            latest = self.get_latest_portfolio()
            if latest is None:
                return {
                    'status': 'empty',
                    'message': 'No portfolio data found',
                    'metrics': self.calculate_portfolio_metrics(None)
                }
            
            metrics = self.calculate_portfolio_metrics(latest)
            
            # Get recent snapshots for trend analysis
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)  # Last 30 days
            recent_snapshots = self.load_portfolio((start_date, end_date))
            
            summary = {
                'status': 'active',
                'latest_update': latest.timestamp,
                'metrics': metrics,
                'recent_snapshots_count': len(recent_snapshots),
                'positions': [
                    {
                        'ticker': pos.ticker,
                        'shares': pos.shares,
                        'market_value': pos.market_value if pos.market_value else Decimal('0'),
                        'unrealized_pnl': pos.unrealized_pnl if pos.unrealized_pnl else Decimal('0'),
                        'company': pos.company
                    }
                    for pos in latest.positions
                ]
            }
            
            logger.info("Portfolio summary generated successfully")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate portfolio summary: {e}")
            raise PortfolioManagerError(f"Failed to generate portfolio summary: {e}") from e
    
    def validate_portfolio_integrity(self) -> List[str]:
        """Validate portfolio data integrity.
        
        Returns:
            List of validation issues found (empty if no issues)
            
        Raises:
            PortfolioManagerError: If validation fails
        """
        try:
            logger.info("Validating portfolio data integrity")
            
            issues = []
            
            # Check repository-level integrity
            repo_issues = self.repository.validate_data_integrity()
            issues.extend(repo_issues)
            
            # Check portfolio-specific integrity
            try:
                latest = self.get_latest_portfolio()
                if latest:
                    snapshot_issues = self._validate_portfolio_snapshot(latest)
                    issues.extend(snapshot_issues)
            except Exception as e:
                issues.append(f"Failed to load portfolio for validation: {e}")
            
            logger.info(f"Portfolio validation completed: {len(issues)} issues found")
            return issues
            
        except Exception as e:
            logger.error(f"Failed to validate portfolio integrity: {e}")
            raise PortfolioManagerError(f"Failed to validate portfolio integrity: {e}") from e
    
    def _validate_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> List[str]:
        """Validate a portfolio snapshot for consistency.
        
        Args:
            snapshot: PortfolioSnapshot to validate
            
        Returns:
            List of validation issues found
        """
        issues = []
        
        try:
            # Check for duplicate tickers
            tickers = [pos.ticker for pos in snapshot.positions]
            if len(tickers) != len(set(tickers)):
                issues.append("Portfolio contains duplicate ticker positions")
            
            # Check for negative shares
            for position in snapshot.positions:
                if position.shares < 0:
                    issues.append(f"Position {position.ticker} has negative shares: {position.shares}")
                
                # Check cost basis calculation
                expected_cost_basis = (position.avg_price * position.shares).quantize(Decimal('0.01'))
                if abs(position.cost_basis - expected_cost_basis) > Decimal('0.01'):
                    issues.append(f"Position {position.ticker} has incorrect cost basis calculation")
                
                # Check market value calculation if current price is available
                if position.current_price is not None and position.market_value is not None:
                    expected_market_value = (position.current_price * position.shares).quantize(Decimal('0.01'))
                    if abs(position.market_value - expected_market_value) > Decimal('0.01'):
                        issues.append(f"Position {position.ticker} has incorrect market value calculation")
                
                # Check unrealized P&L calculation
                if (position.market_value is not None and 
                    position.unrealized_pnl is not None):
                    expected_pnl = (position.market_value - position.cost_basis).quantize(Decimal('0.01'))
                    if abs(position.unrealized_pnl - expected_pnl) > Decimal('0.01'):
                        issues.append(f"Position {position.ticker} has incorrect unrealized P&L calculation")
            
            # Check total value calculation
            if snapshot.total_value is not None:
                calculated_total = snapshot.calculate_total_value()
                if abs(snapshot.total_value - calculated_total) > Decimal('0.01'):
                    issues.append("Portfolio total value doesn't match sum of position values")
            
        except Exception as e:
            issues.append(f"Error during snapshot validation: {e}")
        
        return issues
    
    def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """
        Save a portfolio snapshot to the repository.
        
        This is an alias for save_portfolio() to maintain compatibility
        with existing code that expects this method name.
        
        Args:
            snapshot: PortfolioSnapshot to save
            
        Raises:
            PortfolioManagerError: If saving fails
        """
        self.save_portfolio(snapshot)