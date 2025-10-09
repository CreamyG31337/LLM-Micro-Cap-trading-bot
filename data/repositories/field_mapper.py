"""Field mapping utilities for converting between domain models and database formats."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TypeTransformers:
    """Type conversion utilities."""

    @staticmethod
    def iso_to_datetime(iso_string: str) -> datetime:
        """Convert ISO format string to datetime object."""
        try:
            return datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse datetime '{iso_string}': {e}")
            return datetime.now()


class PositionMapper:
    """Maps between Position domain model and database format."""

    @staticmethod
    def model_to_db(position: Any, fund: str, timestamp: datetime) -> Dict[str, Any]:
        """Convert Position model to database format."""
        # Use current_price if available, otherwise fall back to avg_price
        price = float(position.current_price) if position.current_price is not None else float(position.avg_price)
        
        return {
            'ticker': position.ticker,
            'company': position.company,
            'shares': float(position.shares),
            'price': price,  # Current market price (or avg_price if current not available)
            'cost_basis': float(position.cost_basis),
            'pnl': float(position.unrealized_pnl or position.calculated_unrealized_pnl),
            'currency': position.currency,
            'fund': fund,
            'date': timestamp.isoformat(),
            'created_at': datetime.now().isoformat()
        }

    @staticmethod
    def db_to_model(row: Dict[str, Any]) -> Any:
        """Convert database row to Position model."""
        from ..models.portfolio import Position

        # Handle avg_price field - use 'avg_price' if available (from views), otherwise calculate from cost_basis
        avg_price = row.get('avg_price')
        if avg_price is None:
            # Calculate avg_price from cost_basis and shares (DON'T use 'price' field - that's current price!)
            shares = Decimal(str(row.get('shares', row.get('total_shares', 0))))
            cost_basis = Decimal(str(row.get('cost_basis', row.get('total_cost_basis', 0))))
            avg_price = cost_basis / shares if shares > 0 else Decimal('0')
        else:
            avg_price = Decimal(str(avg_price))

        # Handle market_value and current_price mapping
        market_value = row.get('total_market_value') or row.get('market_value')
        current_price = row.get('current_price') or row.get('price')  # Also check 'price' field

        # If we don't have market_value but have current_price and shares, calculate it
        if market_value is None and current_price is not None:
            shares = Decimal(str(row.get('shares', row.get('total_shares', 0))))
            if shares > 0:
                market_value = Decimal(str(current_price)) * shares
        
        # If we don't have current_price but have market_value and shares, calculate it
        if current_price is None and market_value is not None:
            shares = Decimal(str(row.get('shares', row.get('total_shares', 0))))
            if shares > 0:
                current_price = Decimal(str(market_value)) / shares

        # Handle pnl mapping (use pnl field from database)
        pnl = row.get('pnl')

        # Handle company field
        company = row.get('company')

        return Position(
            ticker=row['ticker'],
            shares=Decimal(str(row.get('shares', row.get('total_shares', 0)))),
            avg_price=avg_price,
            cost_basis=Decimal(str(row.get('cost_basis', row.get('total_cost_basis', 0)))),
            currency=row.get('currency', 'CAD'),
            company=company,
            current_price=Decimal(str(current_price)) if current_price is not None else None,
            market_value=Decimal(str(market_value)) if market_value is not None else None,
            unrealized_pnl=Decimal(str(pnl)) if pnl is not None else None,
            stop_loss=None  # Not stored in database
        )


class TradeMapper:
    """Maps between Trade domain model and database format."""

    @staticmethod
    def model_to_db(trade: Any, fund: str) -> Dict[str, Any]:
        """Convert Trade model to database format."""
        # Base fields that should always be present
        db_data = {
            'ticker': trade.ticker,
            'shares': float(trade.shares),
            'price': float(trade.price),
            'cost_basis': float(trade.cost_basis) if trade.cost_basis else 0.0,
            'pnl': float(trade.pnl) if trade.pnl else 0.0,
            'reason': trade.reason or '',
            'currency': trade.currency,
            'fund': fund,
            'date': trade.timestamp.isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        # Note: action field is not included as it's not in the current database schema
        # TODO: Add action column to trade_log table in Supabase
        
        return db_data

    @staticmethod
    def db_to_model(row: Dict[str, Any]) -> Any:
        """Convert database row to Trade model."""
        from ..models.trade import Trade

        # Handle missing 'action' field - derive from reason or other indicators
        action = row.get('action')
        if not action:
            # Try to derive action from reason field
            reason = row.get('reason', '').lower()
            if 'sell' in reason or 'limit sell' in reason or 'market sell' in reason:
                action = 'SELL'
            else:
                action = 'BUY'  # Default to BUY for trades

        return Trade(
            ticker=row['ticker'],
            action=action,
            shares=Decimal(str(row['shares'])),
            price=Decimal(str(row['price'])),
            currency=row.get('currency', 'CAD'),
            timestamp=TypeTransformers.iso_to_datetime(row['date']),
            cost_basis=Decimal(str(row.get('cost_basis', 0))) if row.get('cost_basis') else None,
            pnl=Decimal(str(row.get('pnl', 0))) if row.get('pnl') else None,
            reason=row.get('reason')
        )


class CashBalanceMapper:
    """Maps between cash balance data and database format."""

    @staticmethod
    def db_to_dict(data: List[Dict[str, Any]]) -> Dict[str, Decimal]:
        """Convert database rows to cash balance dictionary."""
        balances = {}
        for row in data:
            currency = row.get('currency', 'CAD')
            amount = Decimal(str(row.get('amount', 0)))
            balances[currency] = amount
        return balances

    @staticmethod
    def dict_to_db(balances: Dict[str, Decimal], fund: str) -> List[Dict[str, Any]]:
        """Convert cash balance dictionary to database format."""
        result = []
        for currency, amount in balances.items():
            result.append({
                'currency': currency,
                'amount': float(amount),
                'fund': fund,
                'created_at': datetime.now().isoformat()
            })
        return result


class SnapshotMapper:
    """Maps between portfolio snapshots and database format."""

    @staticmethod
    def group_positions_by_date(positions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group positions by date for snapshot creation."""
        grouped = {}
        for position in positions:
            date = position.get('date', '')
            if date not in grouped:
                grouped[date] = []
            grouped[date].append(position)
        return grouped

    @staticmethod
    def create_snapshot_from_positions(timestamp: datetime, positions: List[Dict[str, Any]]) -> Any:
        """Create snapshot from database position data."""
        from ..models.portfolio import PortfolioSnapshot

        # Convert positions to domain models
        position_objects = [PositionMapper.db_to_model(pos) for pos in positions]

        # Create snapshot and calculate totals
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            positions=position_objects
        )

        # Calculate and set totals
        snapshot.total_value = snapshot.calculate_total_value()
        snapshot.total_shares = snapshot.calculate_total_shares()

        return snapshot
