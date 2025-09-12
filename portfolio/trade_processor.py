"""Trade processing module.

This module provides the TradeProcessor class for handling trade execution,
validation, and logging using the repository pattern. It abstracts trade
processing logic and provides high-level operations for executing trades.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

from data.repositories.base_repository import BaseRepository, RepositoryError
from data.models.portfolio import Position, PortfolioSnapshot
from data.models.trade import Trade
from utils.validation import validate_trade_data
from financial.calculations import money_to_decimal, calculate_cost_basis

logger = logging.getLogger(__name__)


class TradeProcessorError(Exception):
    """Base exception for trade processor operations."""
    pass


class InsufficientFundsError(TradeProcessorError):
    """Exception raised when insufficient funds for trade."""
    pass


class InsufficientSharesError(TradeProcessorError):
    """Exception raised when insufficient shares for sell trade."""
    pass


class TradeValidationError(TradeProcessorError):
    """Exception raised when trade validation fails."""
    pass


class TradeProcessor:
    """Processes trade execution, validation, and logging using the repository pattern.
    
    This class provides high-level trade operations while abstracting
    the underlying data storage mechanism through the repository interface.
    It supports both CSV and future database backends seamlessly.
    """
    
    def __init__(self, repository: BaseRepository):
        """Initialize trade processor.
        
        Args:
            repository: Repository implementation for data access
        """
        self.repository = repository
        logger.info(f"Trade processor initialized with {type(repository).__name__}")
    
    def execute_buy_trade(self, ticker: str, shares: Decimal, price: Decimal,
                         stop_loss: Optional[Decimal] = None,
                         reason: Optional[str] = None,
                         currency: str = "CAD",
                         validate_funds: bool = True) -> Trade:
        """Execute a buy trade with validation and logging.
        
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
            
        Raises:
            TradeProcessorError: If trade execution fails
            InsufficientFundsError: If insufficient funds (when validate_funds=True)
            TradeValidationError: If trade validation fails
        """
        try:
            logger.info(f"Executing buy trade: {ticker} {shares} shares @ {price}")
            
            # Validate trade data
            # Basic validation
            if not ticker or shares <= 0 or price <= 0:
                raise TradeValidationError("Invalid trade parameters: ticker, shares, and price must be valid")
            
            # Calculate cost basis
            cost_basis = calculate_cost_basis(price, shares)
            
            # Validate funds if requested
            if validate_funds:
                self._validate_sufficient_funds(cost_basis, currency)
            
            # Create trade record
            trade = Trade(
                ticker=ticker,
                action='BUY',
                shares=shares,
                price=price,
                timestamp=datetime.now(),
                cost_basis=cost_basis,
                reason=reason or "BUY TRADE",
                currency=currency
            )
            
            # Save trade to repository
            self.repository.save_trade(trade)
            
            # Update portfolio position
            self._update_position_after_buy(trade, stop_loss)
            
            logger.info(f"Buy trade executed successfully: {ticker} {shares} @ {price}")
            return trade
            
        except (RepositoryError, TradeValidationError, InsufficientFundsError) as e:
            logger.error(f"Failed to execute buy trade for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing buy trade for {ticker}: {e}")
            raise TradeProcessorError(f"Failed to execute buy trade for {ticker}: {e}") from e
    
    def execute_sell_trade(self, ticker: str, shares: Decimal, price: Decimal,
                          reason: Optional[str] = None,
                          currency: str = "CAD",
                          validate_shares: bool = True) -> Trade:
        """Execute a sell trade with validation and logging.
        
        Args:
            ticker: Ticker symbol
            shares: Number of shares to sell
            price: Price per share
            reason: Optional reason for the trade
            currency: Currency code
            validate_shares: Whether to validate sufficient shares
            
        Returns:
            Trade object representing the executed trade
            
        Raises:
            TradeProcessorError: If trade execution fails
            InsufficientSharesError: If insufficient shares (when validate_shares=True)
            TradeValidationError: If trade validation fails
        """
        try:
            logger.info(f"Executing sell trade: {ticker} {shares} shares @ {price}")
            
            # Validate trade data
            # Basic validation
            if not ticker or shares <= 0 or price <= 0:
                raise TradeValidationError("Invalid trade parameters: ticker, shares, and price must be valid")
            
            # Get current position for P&L calculation
            current_position = self._get_current_position(ticker)
            if validate_shares and (not current_position or current_position.shares < shares):
                available_shares = current_position.shares if current_position else Decimal('0')
                raise InsufficientSharesError(
                    f"Insufficient shares for {ticker}: need {shares}, have {available_shares}"
                )
            
            # Calculate cost basis and P&L
            if current_position:
                cost_basis_per_share = current_position.avg_price
                cost_basis = cost_basis_per_share * shares
                proceeds = price * shares
                pnl = proceeds - cost_basis
            else:
                cost_basis = Decimal('0')
                pnl = price * shares  # All proceeds if no position found
            
            # Create trade record
            trade = Trade(
                ticker=ticker,
                action='SELL',
                shares=shares,
                price=price,
                timestamp=datetime.now(),
                cost_basis=cost_basis,
                pnl=pnl,
                reason=reason or "SELL TRADE",
                currency=currency
            )
            
            # Save trade to repository
            self.repository.save_trade(trade)
            
            # Update portfolio position
            self._update_position_after_sell(trade)
            
            logger.info(f"Sell trade executed successfully: {ticker} {shares} @ {price}, P&L: {pnl}")
            return trade
            
        except (RepositoryError, TradeValidationError, InsufficientSharesError) as e:
            logger.error(f"Failed to execute sell trade for {ticker}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing sell trade for {ticker}: {e}")
            raise TradeProcessorError(f"Failed to execute sell trade for {ticker}: {e}") from e
    
    def execute_stop_loss_sell(self, ticker: str, current_price: Decimal,
                              stop_loss_price: Decimal) -> Optional[Trade]:
        """Execute a stop loss sell if triggered.
        
        Args:
            ticker: Ticker symbol
            current_price: Current market price
            stop_loss_price: Stop loss trigger price
            
        Returns:
            Trade object if stop loss was triggered, None otherwise
            
        Raises:
            TradeProcessorError: If trade execution fails
        """
        try:
            logger.info(f"Checking stop loss for {ticker}: current={current_price}, stop={stop_loss_price}")
            
            # Check if stop loss is triggered
            if current_price > stop_loss_price:
                logger.info(f"Stop loss not triggered for {ticker}")
                return None
            
            # Get current position
            current_position = self._get_current_position(ticker)
            if not current_position or current_position.shares <= 0:
                logger.warning(f"No position found for stop loss sell: {ticker}")
                return None
            
            logger.warning(f"Stop loss triggered for {ticker}: selling {current_position.shares} shares")
            
            # Execute sell trade
            trade = self.execute_sell_trade(
                ticker=ticker,
                shares=current_position.shares,
                price=current_price,
                reason="AUTOMATED SELL - STOP LOSS TRIGGERED",
                currency=current_position.currency,
                validate_shares=False  # We already validated position exists
            )
            
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute stop loss sell for {ticker}: {e}")
            raise TradeProcessorError(f"Failed to execute stop loss sell for {ticker}: {e}") from e
    
    def get_trade_history(self, ticker: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None) -> List[Trade]:
        """Get trade history with optional filtering.
        
        Args:
            ticker: Optional ticker symbol to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            List of Trade objects
            
        Raises:
            TradeProcessorError: If retrieval fails
        """
        try:
            logger.info(f"Getting trade history: ticker={ticker}, dates={start_date} to {end_date}")
            
            date_range = None
            if start_date or end_date:
                date_range = (start_date or datetime.min, end_date or datetime.max)
            
            trades = self.repository.get_trade_history(ticker, date_range)
            logger.info(f"Retrieved {len(trades)} trades")
            return trades
            
        except RepositoryError as e:
            logger.error(f"Failed to get trade history: {e}")
            raise TradeProcessorError(f"Failed to get trade history: {e}") from e
    
    def calculate_trade_metrics(self, ticker: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate trade performance metrics.
        
        Args:
            ticker: Optional ticker symbol to filter by
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            Dictionary containing trade metrics
            
        Raises:
            TradeProcessorError: If calculation fails
        """
        try:
            logger.info(f"Calculating trade metrics: ticker={ticker}")
            
            trades = self.get_trade_history(ticker, start_date, end_date)
            
            if not trades:
                return {
                    'total_trades': 0,
                    'buy_trades': 0,
                    'sell_trades': 0,
                    'total_volume': Decimal('0'),
                    'total_pnl': Decimal('0'),
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'average_pnl': Decimal('0')
                }
            
            total_trades = len(trades)
            buy_trades = sum(1 for t in trades if t.is_buy())
            sell_trades = sum(1 for t in trades if t.is_sell())
            
            total_volume = sum(t.price * t.shares for t in trades)
            total_pnl = sum(t.pnl for t in trades if t.pnl is not None)
            
            winning_trades = sum(1 for t in trades if t.pnl and t.pnl > 0)
            losing_trades = sum(1 for t in trades if t.pnl and t.pnl < 0)
            
            average_pnl = total_pnl / sell_trades if sell_trades > 0 else Decimal('0')
            
            metrics = {
                'total_trades': total_trades,
                'buy_trades': buy_trades,
                'sell_trades': sell_trades,
                'total_volume': total_volume,
                'total_pnl': total_pnl,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'average_pnl': average_pnl,
                'win_rate': (winning_trades / sell_trades * 100) if sell_trades > 0 else 0.0
            }
            
            logger.info(f"Trade metrics calculated: {total_trades} trades, P&L: {total_pnl}")
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to calculate trade metrics: {e}")
            raise TradeProcessorError(f"Failed to calculate trade metrics: {e}") from e
    
    def validate_trade_request(self, ticker: str, action: str, shares: Decimal,
                              price: Decimal, currency: str = "CAD") -> List[str]:
        """Validate a trade request and return any issues found.
        
        Args:
            ticker: Ticker symbol
            action: Trade action (BUY/SELL)
            shares: Number of shares
            price: Price per share
            currency: Currency code
            
        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        
        try:
            # Basic validation
            trade_data = {
                'ticker': ticker,
                'action': action,
                'shares': float(shares),
                'price': float(price),
                'currency': currency
            }
            
            # Basic validation
            if not ticker or shares <= 0 or price <= 0:
                issues.append("Invalid trade parameters: ticker, shares, and price must be valid")
            
            # Action-specific validation
            if action.upper() == 'BUY':
                # Check funds (non-blocking validation)
                try:
                    cost_basis = calculate_cost_basis(price, shares)
                    self._validate_sufficient_funds(cost_basis, currency)
                except InsufficientFundsError as e:
                    issues.append(str(e))
            
            elif action.upper() == 'SELL':
                # Check shares availability
                current_position = self._get_current_position(ticker)
                if not current_position:
                    issues.append(f"No position found for {ticker}")
                elif current_position.shares < shares:
                    issues.append(f"Insufficient shares: need {shares}, have {current_position.shares}")
            
        except Exception as e:
            issues.append(f"Validation error: {e}")
        
        return issues
    
    def _get_current_position(self, ticker: str) -> Optional[Position]:
        """Get current position for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Current Position or None if not found
        """
        try:
            latest_snapshot = self.repository.get_latest_portfolio_snapshot()
            if latest_snapshot:
                return latest_snapshot.get_position_by_ticker(ticker)
            return None
        except RepositoryError:
            logger.warning(f"Failed to get current position for {ticker}")
            return None
    
    def _validate_sufficient_funds(self, cost_basis: Decimal, currency: str) -> None:
        """Validate sufficient funds for a trade.
        
        Args:
            cost_basis: Required funds
            currency: Currency code
            
        Raises:
            InsufficientFundsError: If insufficient funds
        """
        # This is a placeholder implementation
        # In a real system, this would check actual cash balances
        # For now, we'll just log a warning
        logger.warning(f"Fund validation not fully implemented: need {cost_basis} {currency}")
    
    def _update_position_after_buy(self, trade: Trade, stop_loss: Optional[Decimal] = None) -> None:
        """Update portfolio position after a buy trade.
        
        Args:
            trade: Executed buy trade
            stop_loss: Optional stop loss price
        """
        try:
            # Get latest portfolio snapshot
            latest_snapshot = self.repository.get_latest_portfolio_snapshot()
            if latest_snapshot is None:
                latest_snapshot = PortfolioSnapshot(
                    positions=[],
                    timestamp=datetime.now()
                )
            
            # Get existing position or create new one
            existing_position = latest_snapshot.get_position_by_ticker(trade.ticker)
            
            if existing_position:
                # Update existing position (average down/up)
                total_shares = existing_position.shares + trade.shares
                total_cost = existing_position.cost_basis + trade.cost_basis
                new_avg_price = total_cost / total_shares if total_shares > 0 else Decimal('0')
                
                updated_position = Position(
                    ticker=trade.ticker,
                    shares=total_shares,
                    avg_price=new_avg_price,
                    cost_basis=total_cost,
                    currency=trade.currency,
                    company=existing_position.company,
                    stop_loss=stop_loss or existing_position.stop_loss
                )
            else:
                # Create new position
                updated_position = Position(
                    ticker=trade.ticker,
                    shares=trade.shares,
                    avg_price=trade.price,
                    cost_basis=trade.cost_basis,
                    currency=trade.currency,
                    stop_loss=stop_loss
                )
            
            # Update snapshot
            latest_snapshot.add_position(updated_position)
            latest_snapshot.timestamp = trade.timestamp
            
            # Save updated snapshot
            self.repository.save_portfolio_snapshot(latest_snapshot)
            
            logger.info(f"Position updated after buy: {trade.ticker}")
            
        except Exception as e:
            logger.error(f"Failed to update position after buy trade: {e}")
            # Don't raise here as the trade was already saved
    
    def _update_position_after_sell(self, trade: Trade) -> None:
        """Update portfolio position after a sell trade.
        
        Args:
            trade: Executed sell trade
        """
        try:
            # Get latest portfolio snapshot
            latest_snapshot = self.repository.get_latest_portfolio_snapshot()
            if latest_snapshot is None:
                logger.warning("No portfolio snapshot found for sell trade update")
                return
            
            # Get existing position
            existing_position = latest_snapshot.get_position_by_ticker(trade.ticker)
            if not existing_position:
                logger.warning(f"No existing position found for sell trade: {trade.ticker}")
                return
            
            # Calculate remaining shares
            remaining_shares = existing_position.shares - trade.shares
            
            if remaining_shares <= 0:
                # Remove position entirely
                latest_snapshot.remove_position(trade.ticker)
                logger.info(f"Position removed after sell: {trade.ticker}")
            else:
                # Update position with remaining shares
                remaining_cost_basis = existing_position.avg_price * remaining_shares
                
                updated_position = Position(
                    ticker=trade.ticker,
                    shares=remaining_shares,
                    avg_price=existing_position.avg_price,  # Keep same average price
                    cost_basis=remaining_cost_basis,
                    currency=trade.currency,
                    company=existing_position.company,
                    stop_loss=existing_position.stop_loss
                )
                
                latest_snapshot.add_position(updated_position)
                logger.info(f"Position updated after sell: {trade.ticker}, remaining: {remaining_shares}")
            
            # Update snapshot timestamp
            latest_snapshot.timestamp = trade.timestamp
            
            # Save updated snapshot
            self.repository.save_portfolio_snapshot(latest_snapshot)
            
        except Exception as e:
            logger.error(f"Failed to update position after sell trade: {e}")
            # Don't raise here as the trade was already saved