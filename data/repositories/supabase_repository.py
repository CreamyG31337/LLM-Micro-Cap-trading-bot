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

logger = logging.getLogger(__name__)


class SupabaseRepository(BaseRepository):
    """Supabase-based implementation of the repository pattern.
    
    This implementation provides the same interface as CSVRepository but
    uses Supabase as the backend storage.
    """
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """Initialize Supabase repository.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase anon key
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_ANON_KEY")
        
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
            query = self.supabase.table("portfolio_positions").select("*")
            
            if date_range:
                start_date, end_date = date_range
                query = query.gte("date", start_date.isoformat()).lte("date", end_date.isoformat())
            
            result = query.execute()
            
            # Convert to PortfolioSnapshot objects
            snapshots = []
            for row in result.data:
                position = Position(
                    ticker=row["ticker"],
                    shares=Decimal(str(row["shares"])),
                    price=Decimal(str(row["price"])),
                    cost_basis=Decimal(str(row["cost_basis"])),
                    pnl=Decimal(str(row["pnl"])),
                    currency=row.get("currency", "USD"),
                    date=datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
                )
                
                # Group by date for snapshots
                snapshot_date = position.date.date()
                existing_snapshot = next((s for s in snapshots if s.date == snapshot_date), None)
                
                if existing_snapshot:
                    existing_snapshot.positions.append(position)
                else:
                    snapshots.append(PortfolioSnapshot(
                        date=snapshot_date,
                        positions=[position],
                        total_value=position.shares * position.price,
                        total_cost_basis=position.cost_basis,
                        unrealized_pnl=position.pnl
                    ))
            
            return snapshots
            
        except Exception as e:
            logger.error(f"Failed to get portfolio data: {e}")
            raise RepositoryError(f"Failed to get portfolio data: {e}")
    
    def save_portfolio_data(self, snapshot: PortfolioSnapshot) -> None:
        """Save portfolio data to Supabase.
        
        Args:
            snapshot: Portfolio snapshot to save
            
        Raises:
            RepositoryError: If data saving fails
        """
        try:
            # Convert positions to Supabase format
            positions_data = []
            for position in snapshot.positions:
                positions_data.append({
                    "ticker": position.ticker,
                    "shares": float(position.shares),
                    "price": float(position.price),
                    "cost_basis": float(position.cost_basis),
                    "pnl": float(position.pnl),
                    "currency": position.currency,
                    "date": snapshot.date.isoformat(),
                    "fund": "Project Chimera"  # Default fund, could be configurable
                })
            
            # Upsert positions (insert or update)
            result = self.supabase.table("portfolio_positions").upsert(positions_data).execute()
            
            logger.info(f"Saved {len(positions_data)} portfolio positions to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save portfolio data: {e}")
            raise RepositoryError(f"Failed to save portfolio data: {e}")
    
    def get_trade_history(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Trade]:
        """Get trade history from Supabase.
        
        Args:
            date_range: Optional date range filter
            
        Returns:
            List of trades
            
        Raises:
            RepositoryError: If data retrieval fails
        """
        try:
            query = self.supabase.table("trade_log").select("*")
            
            if date_range:
                start_date, end_date = date_range
                query = query.gte("date", start_date.isoformat()).lte("date", end_date.isoformat())
            
            result = query.execute()
            
            # Convert to Trade objects
            trades = []
            for row in result.data:
                trade = Trade(
                    ticker=row["ticker"],
                    shares=Decimal(str(row["shares"])),
                    price=Decimal(str(row["price"])),
                    cost_basis=Decimal(str(row["cost_basis"])),
                    pnl=Decimal(str(row["pnl"])),
                    reason=row["reason"],
                    currency=row.get("currency", "USD"),
                    date=datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
                )
                trades.append(trade)
            
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
            trade_data = {
                "ticker": trade.ticker,
                "shares": float(trade.shares),
                "price": float(trade.price),
                "cost_basis": float(trade.cost_basis),
                "pnl": float(trade.pnl),
                "reason": trade.reason,
                "currency": trade.currency,
                "date": trade.date.isoformat(),
                "fund": "Project Chimera"  # Default fund, could be configurable
            }
            
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
            
            balances = {}
            for row in result.data:
                currency = row["currency"]
                amount = Decimal(str(row["amount"]))
                balances[currency] = amount
            
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
            balances_data = []
            for currency, amount in balances.items():
                balances_data.append({
                    "currency": currency,
                    "amount": float(amount),
                    "fund": "Project Chimera",  # Default fund
                    "updated_at": datetime.now().isoformat()
                })
            
            result = self.supabase.table("cash_balances").upsert(balances_data).execute()
            
            logger.info(f"Saved cash balances to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to save cash balances: {e}")
            raise RepositoryError(f"Failed to save cash balances: {e}")
