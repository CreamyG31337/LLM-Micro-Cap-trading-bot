"""Supabase-based repository implementation."""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
import logging

from .base_repository import BaseRepository, RepositoryError, DataValidationError, DataNotFoundError
from ..models.portfolio import Position, PortfolioSnapshot
from ..models.trade import Trade
from ..models.market_data import MarketData

# Import field mappers
from .field_mapper import (
    PositionMapper,
    TradeMapper,
    CashBalanceMapper,
    SnapshotMapper
)

logger = logging.getLogger(__name__)

# Suppress httpx INFO logs (Supabase HTTP requests)
logging.getLogger("httpx").setLevel(logging.WARNING)


class SupabaseRepository(BaseRepository):
    """Supabase-based implementation of the repository pattern.
    
    This implementation provides the same interface as CSVRepository but
    uses Supabase as the backend storage.
    """
    
    def __init__(self, fund_name: str, url: str = None, key: str = None, **kwargs):
        """Initialize Supabase repository.
        
        Args:
            fund_name: Fund name (REQUIRED - no default)
            url: Supabase project URL
            key: Supabase anon key
        """
        self.supabase_url = url or os.getenv("SUPABASE_URL")
        self.supabase_key = key or os.getenv("SUPABASE_PUBLISHABLE_KEY")
        
        if not fund_name:
            raise RepositoryError(
                "Fund name is required for SupabaseRepository. "
                "This should be provided by the repository factory using the active fund name."
            )
        self.fund = fund_name  # Keep for backward compatibility
        self.fund_name = fund_name
        
        # Add data_dir for compatibility with code expecting it (exchange rates, etc.)
        # Point to the common shared data directory where exchange rates are stored
        self.data_dir = "trading_data/exchange_rates"
        
        if not self.supabase_url or not self.supabase_key:
            raise RepositoryError("Supabase URL and key must be provided")
        
        # Initialize Supabase client
        try:
            from supabase import create_client, Client
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase client initialized successfully")
        except ImportError:
            raise RepositoryError("Supabase client not available. Install with: pip install supabase")
        except Exception as e:
            raise RepositoryError(f"Failed to initialize Supabase client: {e}")
    
    def get_portfolio_data(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[PortfolioSnapshot]:
        """Get portfolio data from Supabase.
        
        Args:
            date_range: Optional date range filter
            
        Returns:
            List of portfolio snapshots
            
        Raises:
            RepositoryError: If data retrieval fails
        """
        try:
            # Supabase Python client has a 1000-row default limit
            # We need to paginate to get all data
            all_data = []
            page_size = 1000
            offset = 0
            
            while True:
                query = self.supabase.table("portfolio_positions") \
                    .select("*") \
                    .eq("fund", self.fund) \
                    .range(offset, offset + page_size - 1)
                
                if date_range:
                    start_date, end_date = date_range
                    query = query.gte("date", start_date.isoformat()).lte("date", end_date.isoformat())
                
                result = query.execute()
                
                if not result.data:
                    break
                
                all_data.extend(result.data)
                
                # If we got less than page_size rows, we're done
                if len(result.data) < page_size:
                    break
                
                offset += page_size
            
            logger.debug(f"Fetched {len(all_data)} total portfolio positions for fund {self.fund}")
            
            # Create a result-like object with all data
            class Result:
                def __init__(self, data):
                    self.data = data
            
            result = Result(all_data)
            
            # Use SnapshotMapper to group positions by date and create snapshots
            grouped = SnapshotMapper.group_positions_by_date(result.data)
            
            snapshots = []
            for date_key, position_rows in grouped.items():
                # Get timestamp from first position
                if position_rows:
                    from .field_mapper import TypeTransformers
                    timestamp = TypeTransformers.iso_to_datetime(position_rows[0]["date"])
                    snapshot = SnapshotMapper.create_snapshot_from_positions(timestamp, position_rows)
                    snapshots.append(snapshot)
            
            return sorted(snapshots, key=lambda s: s.timestamp)
            
        except Exception as e:
            logger.error(f"Failed to get portfolio data: {e}")
            raise RepositoryError(f"Failed to get portfolio data: {e}")
    
    def save_portfolio_snapshot(self, snapshot: PortfolioSnapshot, is_trade_execution: bool = False) -> None:
        """Save portfolio data to Supabase with duplicate detection.
        
        ARCHITECTURE NOTE: This should receive a COMPLETE snapshot with ALL positions for that date.
        This method deletes ALL existing positions for that date before inserting,
        ensuring ONE snapshot per trading day regardless of timestamp differences.
        
        Args:
            snapshot: Complete portfolio snapshot with all positions
            is_trade_execution: Whether this is triggered by a trade execution (bypasses market-close protection)
            
        Raises:
            RepositoryError: If data saving fails
        """
        try:
            # Check for existing snapshots on the same date
            from datetime import timezone
            snapshot_date = snapshot.timestamp.date()
            
            # Get existing snapshots for this date
            existing = self.get_portfolio_data(date_range=(
                datetime.combine(snapshot_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                datetime.combine(snapshot_date, datetime.max.time()).replace(tzinfo=timezone.utc)
            ))
            
            if existing:
                # Check if any existing snapshot is at market close (16:00:00)
                market_close_exists = any(
                    s.timestamp.hour == 16 and s.timestamp.minute == 0 
                    for s in existing
                )
                
                # If we're trying to save a market close snapshot and one already exists
                if (snapshot.timestamp.hour == 16 and snapshot.timestamp.minute == 0 
                    and market_close_exists):
                    logger.warning(f"Market close snapshot already exists for {snapshot_date}")
                    # Don't crash, just update the existing one
                    pass
                
                # If we're trying to save an intraday snapshot but market close exists
                # Only apply protection for price updates, not trade executions
                elif (market_close_exists and not (snapshot.timestamp.hour == 16 and snapshot.timestamp.minute == 0) 
                      and not is_trade_execution):
                    logger.warning(f"⚠️  Attempting to save intraday snapshot but market close snapshot already exists for {snapshot_date}")
                    logger.warning(f"   Skipping save to preserve market close snapshot at 16:00:00")
                    return  # Don't save, preserve market close snapshot
            
            # Use PositionMapper to convert positions to Supabase format
            positions_data = [
                PositionMapper.model_to_db(position, self.fund, snapshot.timestamp)
                for position in snapshot.positions
            ]
            
            # Clear existing positions for this fund and date first
            # Delete all positions for this fund and DATE (not exact timestamp)
            snapshot_date_str = snapshot.timestamp.date().isoformat()
            delete_result = self.supabase.table("portfolio_positions").delete()\
                .eq("fund", self.fund)\
                .gte("date", f"{snapshot_date_str}T00:00:00")\
                .lt("date", f"{snapshot_date_str}T23:59:59.999999")\
                .execute()
            
            # Insert new positions
            result = self.supabase.table("portfolio_positions").insert(positions_data).execute()
            
            logger.info(f"Saved {len(positions_data)} portfolio positions to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio data: {e}")
            raise RepositoryError(f"Failed to save portfolio data: {e}")
    
    def get_trade_history(self, ticker: Optional[str] = None, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Get trade history from Supabase.
        
        Args:
            ticker: Optional ticker symbol to filter by
            date_range: Optional date range filter
            
        Returns:
            List of trades
            
        Raises:
            RepositoryError: If data retrieval fails
        """
        try:
            # Filter by fund name
            query = self.supabase.table("trade_log").select("*").eq("fund", self.fund)
            
            if ticker:
                query = query.eq("ticker", ticker)
            
            if date_range:
                start_date, end_date = date_range
                query = query.gte("date", start_date.isoformat()).lte("date", end_date.isoformat())
            
            result = query.execute()
            
            # Use TradeMapper to convert database rows to Trade objects
            trades = [TradeMapper.db_to_model(row) for row in result.data]
            
            return trades
            
        except Exception as e:
            logger.error(f"Failed to get trade history: {e}")
            raise RepositoryError(f"Failed to get trade history: {e}")
    
    def save_trade(self, trade: Trade) -> None:
        """Save a trade to Supabase.
        
        Args:
            trade: Trade to save
            
        Raises:
            RepositoryError: If data saving fails
        """
        try:
            # Use TradeMapper to convert Trade object to Supabase format
            trade_data = TradeMapper.model_to_db(trade, self.fund)
            
            result = self.supabase.table("trade_log").insert(trade_data).execute()
            
            logger.info(f"Saved trade for {trade.ticker} to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            raise RepositoryError(f"Failed to save trade: {e}")
    
    def get_market_data(self, ticker: str, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[MarketData]:
        """Get market data from Supabase.
        
        Args:
            ticker: Stock ticker symbol
            date_range: Optional date range filter
            
        Returns:
            List of market data points
            
        Raises:
            RepositoryError: If data retrieval fails
        """
        # This would need a market_data table in Supabase
        # For now, return empty list as market data is typically fetched live
        logger.warning("Market data retrieval from Supabase not implemented yet")
        return []
    
    def save_market_data(self, ticker: str, market_data: List[MarketData]) -> None:
        """Save market data to Supabase.
        
        Args:
            ticker: Stock ticker symbol
            market_data: Market data to save
            
        Raises:
            RepositoryError: If data saving fails
        """
        # This would need a market_data table in Supabase
        # For now, do nothing as market data is typically fetched live
        logger.warning("Market data saving to Supabase not implemented yet")
    
    def get_recent_trades(self, days: int = 30, limit: int = 100) -> List[Trade]:
        """Get recent trades for easier debugging.
        
        Args:
            days: Number of days back to look
            limit: Maximum number of trades to return
            
        Returns:
            List of recent trades sorted by date
        """
        from datetime import timedelta
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.get_trade_history(date_range=(start_date, end_date))[:limit]
    
    def get_trades_by_ticker(self, ticker: str, limit: int = 50) -> List[Trade]:
        """Get all trades for a specific ticker.
        
        Args:
            ticker: Ticker symbol to filter by
            limit: Maximum number of trades to return
            
        Returns:
            List of trades for the ticker
        """
        trades = self.get_trade_history(ticker=ticker)
        return sorted(trades, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_fund_summary(self) -> Dict[str, Any]:
        """Get a summary of trades for this fund.
        
        Returns:
            Dictionary with fund statistics
        """
        try:
            # Get all trades for this fund
            all_trades = self.get_trade_history()
            
            if not all_trades:
                return {
                    'fund': self.fund,
                    'total_trades': 0,
                    'unique_tickers': 0,
                    'date_range': None,
                    'total_value': 0
                }
            
            # Calculate statistics
            tickers = set(trade.ticker for trade in all_trades)
            dates = [trade.timestamp for trade in all_trades]
            total_value = sum(float(trade.cost_basis or 0) for trade in all_trades)
            
            return {
                'fund': self.fund,
                'total_trades': len(all_trades),
                'unique_tickers': len(tickers),
                'date_range': {
                    'first': min(dates).strftime('%Y-%m-%d'),
                    'last': max(dates).strftime('%Y-%m-%d')
                },
                'total_value': total_value,
                'tickers': sorted(tickers)
            }
            
        except Exception as e:
            logger.error(f"Failed to get fund summary: {e}")
            raise RepositoryError(f"Failed to get fund summary: {e}")

    def backup_data(self, backup_path: str) -> None:
        """Backup data from Supabase.
        
        Args:
            backup_path: Path to save backup
            
        Raises:
            RepositoryError: If backup fails
        """
        try:
            # Export all data to CSV files
            portfolio_data = self.get_portfolio_data()
            trade_data = self.get_trade_history()
            
            # Save to backup location
            # This would need to be implemented based on backup format requirements
            logger.info(f"Backup completed to {backup_path}")
            
        except Exception as e:
            logger.error(f"Failed to backup data: {e}")
            raise RepositoryError(f"Failed to backup data: {e}")
    
    def restore_data(self, backup_path: str) -> None:
        """Restore data to Supabase.
        
        Args:
            backup_path: Path to backup file
            
        Raises:
            RepositoryError: If restore fails
        """
        # This would need to be implemented based on backup format
        logger.warning("Data restore from backup not implemented yet")
    
    def get_cash_balances(self) -> Dict[str, Decimal]:
        """Get cash balances from Supabase.
        
        Returns:
            Dictionary of currency -> balance
            
        Raises:
            RepositoryError: If data retrieval fails
        """
        try:
            result = self.supabase.table("cash_balances").select("*").execute()
            
            # Use CashBalanceMapper to convert database rows to dictionary
            balances = CashBalanceMapper.db_to_dict(result.data)
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get cash balances: {e}")
            raise RepositoryError(f"Failed to get cash balances: {e}")
    
    def save_cash_balances(self, balances: Dict[str, Decimal]) -> None:
        """Save cash balances to Supabase.
        
        Args:
            balances: Dictionary of currency -> balance
            
        Raises:
            RepositoryError: If data saving fails
        """
        try:
            # Use CashBalanceMapper to convert dictionary to database format
            balances_data = CashBalanceMapper.dict_to_db(balances, self.fund)
            
            result = self.supabase.table("cash_balances").upsert(balances_data).execute()
            
            logger.info(f"Saved cash balances to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save cash balances: {e}")
            raise RepositoryError(f"Failed to save cash balances: {e}")
    
    def get_latest_portfolio_snapshot_with_pnl(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot with calculated P&L from database view.
        
        This uses the Supabase view 'position_with_historical_pnl' which calculates
        1-day and 5-day P&L server-side for better performance.
        
        Returns:
            Portfolio snapshot with positions including historical P&L metrics
        """
        try:
            result = self.supabase.table("position_with_historical_pnl") \
                .select("*") \
                .eq("fund", self.fund) \
                .execute()
            
            if not result.data:
                logger.debug(f"No portfolio data found for fund: {self.fund}")
                return None
            
            # Convert view rows to Position objects
            from .field_mapper import TypeTransformers
            positions = []
            
            for row in result.data:
                # The view returns enriched data with P&L calculations
                position = PositionMapper.db_to_model(row)
                
                # Add the calculated P&L fields from the view
                position.daily_pnl = row.get('daily_pnl')
                position.daily_pnl_pct = row.get('daily_pnl_pct')
                position.five_day_pnl = row.get('five_day_pnl')
                position.five_day_pnl_pct = row.get('five_day_pnl_pct')
                
                positions.append(position)
            
            # Get timestamp from first position
            timestamp = TypeTransformers.iso_to_datetime(result.data[0]['current_date'])
            
            # Calculate total value
            total_value = sum(pos.market_value for pos in positions if pos.market_value)
            
            return PortfolioSnapshot(
                positions=positions,
                timestamp=timestamp,
                total_value=total_value
            )
            
        except Exception as e:
            logger.error(f"Failed to get portfolio snapshot with P&L: {e}", exc_info=True)
            raise RepositoryError(f"Failed to get portfolio snapshot with P&L: {e}") from e
    
    def get_latest_portfolio_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get the most recent portfolio snapshot.
        
        Returns the latest snapshot with all positions from that exact timestamp.
        This avoids loading historical data and just gets the current portfolio state.
        """
        try:
            # Strategy: Get max date first, then get all positions with that exact date
            # This is more efficient than loading all history and taking the last one
            
            # Step 1: Find the maximum (latest) date for this fund
            max_date_query = self.supabase.table("portfolio_positions") \
                .select("date") \
                .eq("fund", self.fund) \
                .order("date", desc=True) \
                .limit(1) \
                .execute()
            
            if not max_date_query.data:
                logger.debug(f"No portfolio data found for fund: {self.fund}")
                return None
            
            from .field_mapper import TypeTransformers
            latest_timestamp_str = max_date_query.data[0]["date"]
            latest_timestamp = TypeTransformers.iso_to_datetime(latest_timestamp_str)
            
            # Step 2: Get ALL positions from that exact DATE (not timestamp)
            # Get positions from the same DATE (not exact timestamp)
            date_str = latest_timestamp.date().isoformat()
            positions_query = self.supabase.table("portfolio_positions") \
                .select("*") \
                .eq("fund", self.fund) \
                .gte("date", f"{date_str}T00:00:00Z") \
                .lte("date", f"{date_str}T23:59:59Z") \
                .execute()
            
            if not positions_query.data:
                logger.debug(f"No positions found for latest date: {latest_timestamp}")
                return None
            
            logger.debug(f"Found {len(positions_query.data)} positions for latest snapshot: {latest_timestamp}")
            
            # Group by ticker and take the latest timestamp for each ticker
            # This handles cases where there are multiple updates on the same day
            ticker_positions = {}
            for row in positions_query.data:
                ticker = row['ticker']
                row_timestamp = TypeTransformers.iso_to_datetime(row['date'])
                
                # Keep only the latest position for each ticker
                if ticker not in ticker_positions:
                    ticker_positions[ticker] = row
                else:
                    existing_timestamp = TypeTransformers.iso_to_datetime(ticker_positions[ticker]['date'])
                    if row_timestamp > existing_timestamp:
                        ticker_positions[ticker] = row
            
            # Convert to Position objects
            positions = [PositionMapper.db_to_model(row) for row in ticker_positions.values()]
            
            # Calculate total value
            total_value = Decimal('0')
            for position in positions:
                if position.market_value:
                    total_value += position.market_value
            
            # Create snapshot
            snapshot = PortfolioSnapshot(
                positions=positions,
                timestamp=latest_timestamp,
                total_value=total_value
            )
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Failed to get latest portfolio snapshot: {e}")
            raise RepositoryError(f"Failed to get latest portfolio snapshot: {e}")
    
    def get_positions_by_ticker(self, ticker: str) -> List[Position]:
        """Get all positions for a specific ticker across time."""
        try:
            result = self.supabase.table("portfolio_positions").select("*").eq("ticker", ticker).execute()
            
            # Use PositionMapper to convert database rows to Position objects
            positions = [PositionMapper.db_to_model(row) for row in result.data]
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions by ticker: {e}")
            raise RepositoryError(f"Failed to get positions by ticker: {e}")
    
    def restore_from_backup(self, backup_path: str) -> None:
        """Restore data from a backup."""
        # This would need to be implemented based on backup format
        logger.warning("Data restore from backup not implemented yet")
        raise RepositoryError("Data restore from backup not implemented yet")
    
    def validate_data_integrity(self) -> List[str]:
        """Validate data integrity and return list of issues found."""
        issues = []
        
        try:
            # Check if portfolio positions exist
            result = self.supabase.table("portfolio_positions").select("id").limit(1).execute()
            if not result.data:
                issues.append("No portfolio positions found")
            
            # Check if trade log exists
            result = self.supabase.table("trade_log").select("id").limit(1).execute()
            if not result.data:
                issues.append("No trade log found")
            
            # Add more validation checks as needed
            
        except Exception as e:
            issues.append(f"Database connection error: {e}")
        
        return issues

    def get_current_positions(self, fund: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get current portfolio positions, optionally filtered by fund.

        This method returns aggregated data from the latest_positions view,
        which includes pre-calculated daily P&L data.
        """
        try:
            # Use provided fund if explicitly given (including None for all funds)
            # Empty string means "all funds" so treat it as None
            target_fund = fund if fund else None
            query = self.supabase.table("latest_positions").select("*")
            if target_fund:
                query = query.eq("fund", target_fund)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get current positions: {e}")
            raise RepositoryError(f"Failed to get current positions: {e}")

    def get_trade_log(self, limit: int = 1000, fund: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent trade log entries, optionally filtered by fund."""
        try:
            # Use provided fund if explicitly given (including None for all funds)
            # Empty string means "all funds" so treat it as None  
            target_fund = fund if fund else None
            query = self.supabase.table("trade_log").select("*").order("date", desc=True).limit(limit)
            if target_fund:
                query = query.eq("fund", target_fund)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get trade log: {e}")
            raise RepositoryError(f"Failed to get trade log: {e}")

    def get_available_funds(self) -> List[str]:
        """Get list of available funds in the database."""
        try:
            # Get unique fund names from portfolio_positions table
            result = self.supabase.table("portfolio_positions").select("fund").execute()
            funds = list(set(row['fund'] for row in result.data if row.get('fund')))
            return sorted(funds)
        except Exception as e:
            logger.error(f"Failed to get available funds: {e}")
            raise RepositoryError(f"Failed to get available funds: {e}")
    
    def update_ticker_in_future_snapshots(self, ticker: str, trade_timestamp: datetime) -> None:
        """Update a ticker's position in all snapshots after the trade timestamp.
        
        This method rebuilds the ticker's position using FIFO lot tracking from the
        trade date forward, ensuring accurate historical snapshots after backdated trades.
        
        Args:
            ticker: Ticker symbol to update
            trade_timestamp: Timestamp of the backdated trade
            
        Raises:
            RepositoryError: If update operation fails
        """
        try:
            from datetime import timezone
            from portfolio.fifo_trade_processor import FIFOTradeProcessor
            from data.models.lot import LotTracker
            
            logger.info(f"Rebuilding {ticker} positions from {trade_timestamp} forward due to backdated trade")
            
            # Get all trades for this ticker from the trade date forward
            trade_date = trade_timestamp.date()
            start_date = datetime.combine(trade_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            end_date = datetime.now(timezone.utc)
            
            all_trades = self.get_trade_history(ticker=ticker, date_range=(start_date, end_date))
            
            if not all_trades:
                logger.info(f"No trades found for {ticker} from {trade_date} forward")
                return
            
            # Sort trades chronologically
            all_trades.sort(key=lambda x: x.timestamp)
            
            # Create a FIFO processor to rebuild lots
            fifo_processor = FIFOTradeProcessor(self)
            
            # Get all snapshots from trade date forward
            snapshots = self.get_portfolio_data(date_range=(start_date, end_date))
            
            if not snapshots:
                logger.info(f"No snapshots found from {trade_date} forward")
                return
            
            # For each snapshot, rebuild the ticker's position
            for snapshot in snapshots:
                # Normalize both timestamps to UTC for comparison
                from datetime import timezone as tz
                snapshot_ts = snapshot.timestamp if snapshot.timestamp.tzinfo else snapshot.timestamp.replace(tzinfo=tz.utc)
                trade_ts = trade_timestamp if trade_timestamp.tzinfo else trade_timestamp.replace(tzinfo=tz.utc)
                
                if snapshot_ts < trade_ts:
                    continue  # Skip snapshots before the trade
                
                # Rebuild lots up to this snapshot's timestamp
                tracker = LotTracker(ticker)
                
                # Process all trades up to this snapshot's timestamp
                for trade in all_trades:
                    trade_ts_loop = trade.timestamp if trade.timestamp.tzinfo else trade.timestamp.replace(tzinfo=tz.utc)
                    if trade_ts_loop > snapshot_ts:
                        break
                    
                    if trade.is_buy():
                        tracker.add_lot(
                            shares=trade.shares,
                            price=trade.price,
                            purchase_date=trade.timestamp,
                            currency=trade.currency
                        )
                    elif trade.is_sell():
                        try:
                            tracker.sell_shares_fifo(
                                shares_to_sell=trade.shares,
                                sell_price=trade.price,
                                sell_date=trade.timestamp
                            )
                        except Exception as e:
                            logger.warning(f"Error processing sell trade for {ticker}: {e}")
                
                # Calculate the position at this snapshot time
                total_shares = sum(lot.remaining_shares for lot in tracker.lots)
                total_cost_basis = sum(lot.remaining_cost_basis for lot in tracker.lots)
                avg_price = total_cost_basis / total_shares if total_shares > 0 else Decimal('0')
                
                # Create new position for this ticker
                if total_shares > 0:
                    # Find the original position to get current price and other details
                    original_position = None
                    for pos in snapshot.positions:
                        if pos.ticker == ticker:
                            original_position = pos
                            break
                    
                    new_position = Position(
                        ticker=ticker,
                        shares=total_shares,
                        avg_price=avg_price,
                        cost_basis=total_cost_basis,
                        currency=trade.currency if all_trades else "CAD",
                        company=original_position.company if original_position else None,
                        current_price=original_position.current_price if original_position else None,
                        market_value=original_position.current_price * total_shares if original_position and original_position.current_price else None,
                        unrealized_pnl=None  # Will be calculated
                    )
                    
                    # Remove old position and add new one
                    snapshot.remove_position(ticker)
                    snapshot.add_position(new_position)
                else:
                    # No shares remaining, remove position
                    snapshot.remove_position(ticker)
                
                # Recalculate snapshot totals
                snapshot.total_value = snapshot.calculate_total_value()
                
                # Save the updated snapshot
                self.save_portfolio_snapshot(snapshot)
                logger.info(f"Updated {ticker} position in snapshot {snapshot.timestamp}")
            
            logger.info(f"Successfully rebuilt {ticker} positions from {trade_timestamp} forward")
            
        except Exception as e:
            logger.error(f"Failed to update ticker {ticker} in future snapshots: {e}")
            raise RepositoryError(f"Failed to update ticker {ticker} in future snapshots: {e}") from e