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
        return {
            'ticker': position.ticker,
            'shares': float(position.shares),
            'avg_price': float(position.avg_price),
            'cost_basis': float(position.cost_basis),
            'currency': position.currency,
            'fund': fund,
            'date': timestamp.isoformat(),
            'created_at': datetime.now().isoformat()
        }

    @staticmethod
    def db_to_model(row: Dict[str, Any]) -> Any:
        """Convert database row to Position model."""
        from ..models.portfolio import Position

        return Position(
            ticker=row['ticker'],
            shares=Decimal(str(row['shares'])),
            avg_price=Decimal(str(row['avg_price'])),
            cost_basis=Decimal(str(row['cost_basis'])),
            currency=row.get('currency', 'CAD')
        )


class TradeMapper:
    """Maps between Trade domain model and database format."""

    @staticmethod
    def model_to_db(trade: Any, fund: str) -> Dict[str, Any]:
        """Convert Trade model to database format."""
        return {
            'ticker': trade.ticker,
            'action': trade.action,
            'shares': float(trade.shares),
            'price': float(trade.price),
            'currency': trade.currency,
            'fund': fund,
            'date': trade.timestamp.isoformat(),
            'created_at': datetime.now().isoformat()
        }

    @staticmethod
    def db_to_model(row: Dict[str, Any]) -> Any:
        """Convert database row to Trade model."""
        from ..models.trade import Trade

        return Trade(
            ticker=row['ticker'],
            action=row['action'],
            shares=Decimal(str(row['shares'])),
            price=Decimal(str(row['price'])),
            currency=row.get('currency', 'CAD'),
            timestamp=TypeTransformers.iso_to_datetime(row['date'])
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

        # Calculate totals
        total_value = sum(pos.cost_basis for pos in position_objects)
        total_shares = sum(pos.shares for pos in position_objects)

        return PortfolioSnapshot(
            timestamp=timestamp,
            positions=position_objects,
            total_value=total_value,
            total_shares=total_shares,
            fund=positions[0].get('fund', 'Unknown') if positions else 'Unknown'
        )
