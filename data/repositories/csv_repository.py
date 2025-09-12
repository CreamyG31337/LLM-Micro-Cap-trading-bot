"""CSV-based repository implementation."""

from __future__ import annotations

import csv
import os
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
import logging

from .base_repository import BaseRepository, RepositoryError, DataValidationError, DataNotFoundError
from ..models.portfolio import Position, PortfolioSnapshot
from ..models.trade import Trade
from ..models.market_data import MarketData

logger = logging.getLogger(__name__)


class CSVRepository(BaseRepository):
    """CSV-based implementation of the repository pattern.
    
    This implementation maintains compatibility with the existing CSV file formats
    while providing the repository interface for future database migration.
    """
    
    def __init__(self, data_directory: str = "my trading"):
        """Initialize CSV repository.
        
        Args:
            data_directory: Directory containing CSV files
        """
        self.data_dir = Path(data_directory)
        self.portfolio_file = self.data_dir / "llm_portfolio_update.csv"
        self.trade_log_file = self.data_dir / "llm_trade_log.csv"
        self.cash_balances_file = self.data_dir / "cash_balances.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
    
    def get_portfolio_data(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Retrieve portfolio snapshots from CSV file.
        
        Args:
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of PortfolioSnapshot objects
        """
        try:
            if not self.portfolio_file.exists():
                logger.info(f"Portfolio file does not exist: {self.portfolio_file}")
                return []
            
            # Read CSV file
            df = pd.read_csv(self.portfolio_file)
            if df.empty:
                logger.info("Portfolio CSV file is empty")
                return []
            
            # Parse timestamps with timezone awareness
            df['Date'] = df['Date'].apply(self._parse_csv_timestamp)
            
            # Filter by date range if provided
            if date_range:
                start_date, end_date = date_range
                df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            
            # Group by date to create snapshots
            snapshots = []
            for date, group in df.groupby('Date'):
                positions = []
                total_value = Decimal('0')
                
                for _, row in group.iterrows():
                    position = Position.from_csv_dict(row.to_dict())
                    positions.append(position)
                    if position.market_value:
                        total_value += position.market_value
                
                snapshot = PortfolioSnapshot(
                    positions=positions,
                    timestamp=date,
                    total_value=total_value
                )
                snapshots.append(snapshot)
            
            return sorted(snapshots, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to load portfolio data: {e}")
            raise RepositoryError(f"Failed to load portfolio data: {e}") from e
    
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Save portfolio snapshot to CSV file.
        
        Args:
            snapshot: PortfolioSnapshot to save
        """
        try:
            # Prepare data for CSV
            rows = []
            timestamp_str = self._format_timestamp_for_csv(snapshot.timestamp)
            
            for position in snapshot.positions:
                row = position.to_csv_dict()
                row['Date'] = timestamp_str
                row['Action'] = 'HOLD'  # Default action for portfolio snapshots
                rows.append(row)
            
            # Create DataFrame
            df = pd.DataFrame(rows)
            
            # Ensure proper column order to match existing format
            expected_columns = [
                'Date', 'Ticker', 'Shares', 'Average Price', 'Cost Basis', 
                'Stop Loss', 'Current Price', 'Total Value', 'PnL', 'Action', 
                'Company', 'Currency'
            ]
            
            # Add missing columns with default values
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # Reorder columns
            df = df[expected_columns]
            
            # Append to existing file or create new one
            if self.portfolio_file.exists():
                df.to_csv(self.portfolio_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.portfolio_file, index=False)
            
            logger.info(f"Saved portfolio snapshot with {len(snapshot.positions)} positions")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio snapshot: {e}")
            raise RepositoryError(f"Failed to save portfolio snapshot: {e}") from e
    
    def get_latest_portfolio_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot.
        
        Returns:
            Latest PortfolioSnapshot or None if no data exists
        """
        snapshots = self.get_portfolio_data()
        return snapshots[-1] if snapshots else None
    
    def get_trade_history(self, ticker: Optional[str] = None, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Retrieve trade history from CSV file.
        
        Args:
            ticker: Optional ticker symbol to filter by
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            List of Trade objects
        """
        try:
            if not self.trade_log_file.exists():
                logger.info(f"Trade log file does not exist: {self.trade_log_file}")
                return []
            
            # Read CSV file
            df = pd.read_csv(self.trade_log_file)
            if df.empty:
                logger.info("Trade log CSV file is empty")
                return []
            
            # Parse timestamps
            df['Date'] = df['Date'].apply(self._parse_csv_timestamp)
            
            # Filter by ticker if provided
            if ticker:
                df = df[df['Ticker'] == ticker]
            
            # Filter by date range if provided
            if date_range:
                start_date, end_date = date_range
                df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
            
            # Convert to Trade objects
            trades = []
            for _, row in df.iterrows():
                trade = Trade.from_csv_dict(row.to_dict(), timestamp=row['Date'])
                trades.append(trade)
            
            return sorted(trades, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to load trade history: {e}")
            raise RepositoryError(f"Failed to load trade history: {e}") from e
    
    def save_trade(self, trade: Trade) -> None:
        """Save a trade record to CSV file.
        
        Args:
            trade: Trade to save
        """
        try:
            # Prepare data for CSV
            row = trade.to_csv_dict()
            
            # Create DataFrame
            df = pd.DataFrame([row])
            
            # Ensure proper column order
            expected_columns = [
                'Date', 'Ticker', 'Shares Bought', 'Buy Price', 
                'Cost Basis', 'PnL', 'Reason'
            ]
            
            # Add missing columns with default values
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = ''
            
            # Reorder columns
            df = df[expected_columns]
            
            # Append to existing file or create new one
            if self.trade_log_file.exists():
                df.to_csv(self.trade_log_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.trade_log_file, index=False)
            
            logger.info(f"Saved trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price}")
            
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise RepositoryError(f"Failed to save trade: {e}") from e
    
    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        """Get all positions for a specific ticker across time.
        
        Args:
            ticker: Ticker symbol to search for
            
        Returns:
            List of Position objects for the ticker
        """
        snapshots = self.get_portfolio_data()
        positions = []
        
        for snapshot in snapshots:
            position = snapshot.get_position_by_ticker(ticker)
            if position:
                positions.append(position)
        
        return positions
    
    def get_market_data(self, ticker: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[MarketData]:
        """Retrieve market data for a ticker.
        
        Note: CSV repository doesn't store market data separately,
        this is a placeholder for future implementation.
        
        Args:
            ticker: Ticker symbol
            date_range: Optional tuple of (start_date, end_date) to filter results
            
        Returns:
            Empty list (market data not stored in CSV format)
        """
        logger.warning("Market data retrieval not implemented for CSV repository")
        return []
    
    def save_market_data(self, market_data: MarketData) -> None:
        """Save market data.
        
        Note: CSV repository doesn't store market data separately,
        this is a placeholder for future implementation.
        
        Args:
            market_data: MarketData to save
        """
        logger.warning("Market data saving not implemented for CSV repository")
        pass
    
    def backup_data(self, backup_path: str) -> None:
        """Create a backup of all CSV files.
        
        Args:
            backup_path: Path where backup should be created
        """
        try:
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all CSV files
            files_to_backup = [
                self.portfolio_file,
                self.trade_log_file,
                self.cash_balances_file
            ]
            
            for file_path in files_to_backup:
                if file_path.exists():
                    backup_file = backup_dir / file_path.name
                    shutil.copy2(file_path, backup_file)
                    logger.info(f"Backed up {file_path.name}")
            
            logger.info(f"Backup completed to {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise RepositoryError(f"Failed to create backup: {e}") from e
    
    def restore_from_backup(self, backup_path: str) -> None:
        """Restore data from a backup.
        
        Args:
            backup_path: Path to backup directory
        """
        try:
            backup_dir = Path(backup_path)
            if not backup_dir.exists():
                raise DataNotFoundError(f"Backup directory not found: {backup_path}")
            
            # Restore all CSV files
            files_to_restore = [
                ("llm_portfolio_update.csv", self.portfolio_file),
                ("llm_trade_log.csv", self.trade_log_file),
                ("cash_balances.json", self.cash_balances_file)
            ]
            
            for backup_name, target_path in files_to_restore:
                backup_file = backup_dir / backup_name
                if backup_file.exists():
                    shutil.copy2(backup_file, target_path)
                    logger.info(f"Restored {backup_name}")
            
            logger.info(f"Restore completed from {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            raise RepositoryError(f"Failed to restore from backup: {e}") from e
    
    def validate_data_integrity(self) -> List[str]:
        """Validate CSV data integrity.
        
        Returns:
            List of validation error messages (empty if no issues)
        """
        issues = []
        
        try:
            # Check portfolio file
            if self.portfolio_file.exists():
                df = pd.read_csv(self.portfolio_file)
                required_columns = ['Date', 'Ticker', 'Shares', 'Average Price']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    issues.append(f"Portfolio file missing columns: {missing_columns}")
                
                # Check for negative shares
                if 'Shares' in df.columns and (df['Shares'] < 0).any():
                    issues.append("Portfolio file contains negative share counts")
            
            # Check trade log file
            if self.trade_log_file.exists():
                df = pd.read_csv(self.trade_log_file)
                required_columns = ['Date', 'Ticker', 'Shares Bought', 'Buy Price']
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    issues.append(f"Trade log file missing columns: {missing_columns}")
        
        except Exception as e:
            issues.append(f"Error validating data integrity: {e}")
        
        return issues
    
    def _parse_csv_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp from CSV format with comprehensive timezone handling.
        
        This function converts timezone abbreviations to pandas-compatible UTC offset formats
        to avoid FutureWarnings and ensure proper timezone handling.
        
        Args:
            timestamp_str: Timestamp string from CSV
            
        Returns:
            Parsed datetime object
        """
        if pd.isna(timestamp_str):
            return datetime.now()

        timestamp_str = str(timestamp_str).strip()

        # Handle common timezone abbreviations to prevent pandas FutureWarnings
        # Convert to pandas-compatible UTC offset format

        # Pacific Time (West Coast)
        if " PST" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" PST", "")
            timestamp_with_offset = f"{clean_timestamp}-08:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()
        elif " PDT" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" PDT", "")
            timestamp_with_offset = f"{clean_timestamp}-07:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()

        # Mountain Time (Rockies)
        elif " MST" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" MST", "")
            timestamp_with_offset = f"{clean_timestamp}-07:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()
        elif " MDT" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" MDT", "")
            timestamp_with_offset = f"{clean_timestamp}-06:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()

        # Central Time (Midwest)
        elif " CST" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" CST", "")
            timestamp_with_offset = f"{clean_timestamp}-06:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()
        elif " CDT" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" CDT", "")
            timestamp_with_offset = f"{clean_timestamp}-05:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()

        # Eastern Time (East Coast)
        elif " EST" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" EST", "")
            timestamp_with_offset = f"{clean_timestamp}-05:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()
        elif " EDT" in timestamp_str:
            clean_timestamp = timestamp_str.replace(" EDT", "")
            timestamp_with_offset = f"{clean_timestamp}-04:00"
            return pd.to_datetime(timestamp_with_offset).to_pydatetime()

        # Already pandas-compatible formats
        elif " UTC" in timestamp_str or " GMT" in timestamp_str:
            return pd.to_datetime(timestamp_str).to_pydatetime()

        # UTC offset format already present
        elif ("+" in timestamp_str or ("-" in timestamp_str and len(timestamp_str) > 6 and timestamp_str[-6:-3].replace('-', '').isdigit())):
            try:
                return pd.to_datetime(timestamp_str).to_pydatetime()
            except Exception:
                dt = pd.to_datetime(timestamp_str, utc=True)
                return dt.to_pydatetime()

        else:
            # No timezone info, assume local timezone
            try:
                dt = pd.to_datetime(timestamp_str)
                return dt.to_pydatetime()
            except Exception:
                logger.warning(f"Failed to parse timestamp: {timestamp_str}")
                return datetime.now()
    
    def _format_timestamp_for_csv(self, timestamp: datetime) -> str:
        """Format timestamp for CSV output with timezone name.
        
        Uses PST/PDT format for user readability in CSV files.
        
        Args:
            timestamp: Datetime to format
            
        Returns:
            Formatted timestamp string with timezone abbreviation
        """
        # Determine timezone abbreviation based on date
        # This is a simplified implementation - in production would use proper timezone detection
        if timestamp.month >= 3 and timestamp.month <= 10:
            # Daylight saving time (approximate)
            tz_name = "PDT"
        else:
            # Standard time
            tz_name = "PST"
        
        return timestamp.strftime(f"%Y-%m-%d %H:%M:%S {tz_name}")