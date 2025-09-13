"""FIFO-based trade processor for industry-standard P&L calculation.

This module implements FIFO (First-In, First-Out) lot tracking for accurate
profit/loss calculation with partial sells and re-buys.
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any

from data.models.trade import Trade
from data.models.lot import Lot, LotTracker
from data.models.portfolio import Position, PortfolioSnapshot
from data.repositories.base_repository import BaseRepository
from portfolio.trade_processor import TradeProcessorError, TradeValidationError, InsufficientSharesError

logger = logging.getLogger(__name__)


class FIFOTradeProcessor:
    """FIFO-based trade processor for accurate P&L calculation."""
    
    def __init__(self, repository: BaseRepository):
        """Initialize FIFO trade processor.
        
        Args:
            repository: Repository for data access
        """
        self.repository = repository
        self.lot_trackers: Dict[str, LotTracker] = {}
        self._load_existing_lots()
    
    def _load_existing_lots(self) -> None:
        """Load existing lots from trade history."""
        try:
            # Get all trades for all tickers
            all_trades = self.repository.get_trade_history()
            
            # Group trades by ticker
            trades_by_ticker = {}
            for trade in all_trades:
                if trade.ticker not in trades_by_ticker:
                    trades_by_ticker[trade.ticker] = []
                trades_by_ticker[trade.ticker].append(trade)
            
            # Process each ticker's trades to build lot history
            for ticker, trades in trades_by_ticker.items():
                self._rebuild_lots_from_trades(ticker, trades)
                
        except Exception as e:
            logger.warning(f"Could not load existing lots: {e}")
    
    def _rebuild_lots_from_trades(self, ticker: str, trades: List[Trade]) -> None:
        """Rebuild lot history from trade log.
        
        This is a simplified implementation that assumes:
        1. All buy trades create new lots
        2. Sell trades consume lots in FIFO order
        """
        tracker = LotTracker(ticker)
        
        # Sort trades by timestamp
        sorted_trades = sorted(trades, key=lambda x: x.timestamp)
        
        for trade in sorted_trades:
            if trade.is_buy():
                # Create new lot
                tracker.add_lot(
                    shares=trade.shares,
                    price=trade.price,
                    purchase_date=trade.timestamp,
                    currency=trade.currency
                )
            elif trade.is_sell():
                # Sell from lots (FIFO)
                try:
                    tracker.sell_shares_fifo(
                        shares_to_sell=trade.shares,
                        sell_price=trade.price,
                        sell_date=trade.timestamp
                    )
                except ValueError as e:
                    logger.warning(f"Could not process sell trade for {ticker}: {e}")
        
        self.lot_trackers[ticker] = tracker
    
    def execute_buy_trade(self, ticker: str, shares: Decimal, price: Decimal,
                         stop_loss: Optional[Decimal] = None,
                         reason: Optional[str] = None,
                         currency: str = "CAD",
                         validate_funds: bool = True,
                         trade_timestamp: Optional[datetime] = None) -> Trade:
        """Execute a buy trade with FIFO lot tracking.
        
        Args:
            ticker: Ticker symbol
            shares: Number of shares to buy
            price: Price per share
            stop_loss: Optional stop loss price
            reason: Optional reason for the trade
            currency: Currency code
            validate_funds: Whether to validate sufficient funds
            
        Returns:
            Trade object representing the executed trade
        """
        try:
            logger.info(f"Executing FIFO buy trade: {ticker} {shares} shares @ {price}")
            
            # Validate trade data
            if not ticker or shares <= 0 or price <= 0:
                raise TradeValidationError("Invalid trade parameters")
            
            # Calculate cost basis
            cost_basis = shares * price
            
            # Validate funds if requested
            if validate_funds:
                self._validate_sufficient_funds(cost_basis, currency)
            
            # Use custom timestamp or current time
            timestamp = trade_timestamp or datetime.now()

            # Create trade record
            trade = Trade(
                ticker=ticker,
                action='BUY',
                shares=shares,
                price=price,
                timestamp=timestamp,
                cost_basis=cost_basis,
                reason=reason or "FIFO BUY TRADE",
                currency=currency
            )
            
            # Save trade to repository
            self.repository.save_trade(trade)
            
            # Add lot to tracker
            if ticker not in self.lot_trackers:
                self.lot_trackers[ticker] = LotTracker(ticker)
            
            lot = self.lot_trackers[ticker].add_lot(
                shares=shares,
                price=price,
                purchase_date=trade.timestamp,
                currency=currency
            )
            
            # Update portfolio position
            self._update_position_after_buy(ticker, trade, stop_loss, timestamp)
            
            logger.info(f"FIFO buy trade executed: {ticker} {shares} @ {price} (Lot: {lot.lot_id})")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute FIFO buy trade for {ticker}: {e}")
            raise TradeProcessorError(f"Failed to execute FIFO buy trade for {ticker}: {e}") from e
    
    def execute_sell_trade(self, ticker: str, shares: Decimal, price: Decimal,
                          reason: Optional[str] = None,
                          currency: str = "CAD",
                          validate_shares: bool = True,
                          trade_timestamp: Optional[datetime] = None) -> Trade:
        """Execute a sell trade with FIFO lot tracking.
        
        Args:
            ticker: Ticker symbol
            shares: Number of shares to sell
            price: Price per share
            reason: Optional reason for the trade
            currency: Currency code
            validate_shares: Whether to validate sufficient shares
            
        Returns:
            Trade object representing the executed trade
        """
        try:
            logger.info(f"Executing FIFO sell trade: {ticker} {shares} shares @ {price}")
            
            # Validate trade data
            if not ticker or shares <= 0 or price <= 0:
                raise TradeValidationError("Invalid trade parameters")
            
            # Check if we have a lot tracker for this ticker
            if ticker not in self.lot_trackers:
                raise InsufficientSharesError(f"No position found for {ticker}")
            
            tracker = self.lot_trackers[ticker]
            
            # Validate sufficient shares
            if validate_shares:
                total_remaining = tracker.get_total_remaining_shares()
                if total_remaining < shares:
                    raise InsufficientSharesError(
                        f"Insufficient shares for {ticker}: need {shares}, have {total_remaining}"
                    )
            
            # Use custom timestamp or current time
            timestamp = trade_timestamp or datetime.now()

            # Execute FIFO sell
            sales = tracker.sell_shares_fifo(shares, price, timestamp)

            # Calculate total realized P&L
            total_realized_pnl = sum(sale['realized_pnl'] for sale in sales)
            total_proceeds = sum(sale['proceeds'] for sale in sales)

            # Create trade record
            trade = Trade(
                ticker=ticker,
                action='SELL',
                shares=shares,
                price=price,
                timestamp=timestamp,
                cost_basis=total_proceeds - total_realized_pnl,  # Cost basis of sold shares
                pnl=total_realized_pnl,
                reason=reason or "FIFO SELL TRADE",
                currency=currency
            )
            
            # Save trade to repository
            self.repository.save_trade(trade)
            
            # Update portfolio position
            self._update_position_after_sell(ticker, trade, timestamp)
            
            logger.info(f"FIFO sell trade executed: {ticker} {shares} @ {price} "
                       f"(Realized P&L: ${total_realized_pnl:.2f})")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute FIFO sell trade for {ticker}: {e}")
            raise TradeProcessorError(f"Failed to execute FIFO sell trade for {ticker}: {e}") from e
    
    def _update_position_after_buy(self, ticker: str, trade: Trade,
                                  stop_loss: Optional[Decimal] = None,
                                  timestamp: Optional[datetime] = None) -> None:
        """Update portfolio position after a buy trade."""
        try:
            # Get latest portfolio snapshot
            latest_snapshot = self.repository.get_latest_portfolio_snapshot()
            if latest_snapshot is None:
                latest_snapshot = PortfolioSnapshot(
                    positions=[],
                    timestamp=datetime.now()
                )
            
            # Get or create lot tracker
            if ticker not in self.lot_trackers:
                self.lot_trackers[ticker] = LotTracker(ticker)
            
            tracker = self.lot_trackers[ticker]
            
            # Create or update position
            if tracker.get_total_remaining_shares() > 0:
                position = Position(
                    ticker=ticker,
                    shares=tracker.get_total_remaining_shares(),
                    avg_price=tracker.get_average_cost_basis(),
                    cost_basis=tracker.get_total_remaining_cost_basis(),
                    currency=trade.currency,
                    stop_loss=stop_loss
                )
                
                # Update snapshot
                latest_snapshot.add_position(position)
                latest_snapshot.timestamp = timestamp or trade.timestamp
                
                # Save updated snapshot
                self.repository.save_portfolio_snapshot(latest_snapshot)
                
                logger.info(f"Position updated after FIFO buy: {ticker}")
            
        except Exception as e:
            logger.error(f"Failed to update position after FIFO buy trade: {e}")
    
    def _update_position_after_sell(self, ticker: str, trade: Trade, timestamp: Optional[datetime] = None) -> None:
        """Update portfolio position after a sell trade."""
        try:
            # Get latest portfolio snapshot
            latest_snapshot = self.repository.get_latest_portfolio_snapshot()
            if latest_snapshot is None:
                logger.warning("No portfolio snapshot found for sell trade update")
                return
            
            # Get lot tracker
            if ticker not in self.lot_trackers:
                logger.warning(f"No lot tracker found for {ticker}")
                return
            
            tracker = self.lot_trackers[ticker]
            
            # Update or remove position
            if tracker.get_total_remaining_shares() > 0:
                # Update position with remaining shares
                position = Position(
                    ticker=ticker,
                    shares=tracker.get_total_remaining_shares(),
                    avg_price=tracker.get_average_cost_basis(),
                    cost_basis=tracker.get_total_remaining_cost_basis(),
                    currency=trade.currency
                )
                
                latest_snapshot.add_position(position)
            else:
                # Remove position entirely
                latest_snapshot.remove_position(ticker)
                logger.info(f"Position removed after FIFO sell: {ticker}")
            
            # Update snapshot timestamp
            latest_snapshot.timestamp = timestamp or trade.timestamp
            
            # Save updated snapshot
            self.repository.save_portfolio_snapshot(latest_snapshot)
            
            logger.info(f"Position updated after FIFO sell: {ticker}")
            
        except Exception as e:
            logger.error(f"Failed to update position after FIFO sell trade: {e}")
    
    def get_realized_pnl_summary(self, ticker: Optional[str] = None) -> Dict[str, Any]:
        """Get realized P&L summary for ticker or all tickers.
        
        Args:
            ticker: Optional ticker to filter by
            
        Returns:
            Dictionary with realized P&L summary
        """
        try:
            if ticker:
                # Get trades for specific ticker
                trades = self.repository.get_trade_history(ticker=ticker)
            else:
                # Get all trades
                trades = self.repository.get_trade_history()
            
            # Filter sell trades
            sell_trades = [t for t in trades if t.is_sell() and t.pnl is not None]
            
            total_realized_pnl = sum(t.pnl for t in sell_trades)
            total_shares_sold = sum(t.shares for t in sell_trades)
            total_proceeds = sum(t.shares * t.price for t in sell_trades)
            
            average_sell_price = total_proceeds / total_shares_sold if total_shares_sold > 0 else Decimal('0')
            
            return {
                'ticker': ticker or 'ALL',
                'total_realized_pnl': total_realized_pnl,
                'total_shares_sold': total_shares_sold,
                'total_proceeds': total_proceeds,
                'average_sell_price': average_sell_price,
                'number_of_sales': len(sell_trades)
            }
            
        except Exception as e:
            logger.error(f"Failed to get realized P&L summary: {e}")
            return {
                'ticker': ticker or 'ALL',
                'total_realized_pnl': Decimal('0'),
                'total_shares_sold': Decimal('0'),
                'total_proceeds': Decimal('0'),
                'average_sell_price': Decimal('0'),
                'number_of_sales': 0
            }
    
    def _validate_sufficient_funds(self, cost_basis: Decimal, currency: str) -> None:
        """Validate sufficient funds for trade.
        
        This is a placeholder - in a real implementation, you'd check
        cash balances against the cost basis.
        """
        # For now, just log a warning
        logger.warning(f"Fund validation not fully implemented: need {cost_basis} {currency}")
