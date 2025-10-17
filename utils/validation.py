"""Portfolio data validation utilities."""

import logging
from datetime import date
from collections import defaultdict
from data.models.portfolio import PortfolioSnapshot

logger = logging.getLogger(__name__)


def check_duplicate_snapshots(
    snapshots: list[PortfolioSnapshot],
    strict: bool = True
) -> tuple[bool, dict[date, list]]:
    """
    Check for duplicate portfolio snapshots on the same date.

    Args:
        snapshots: List of portfolio snapshots to check
        strict: If True, raise error on duplicates. If False, just warn.

    Returns:
        Tuple of (has_duplicates: bool, duplicates_by_date: dict)

    Raises:
        ValueError: If duplicates found and strict=True
    """
    date_counts = defaultdict(list)

    for snapshot in snapshots:
        date_only = snapshot.timestamp.date()
        date_counts[date_only].append({
            'timestamp': snapshot.timestamp,
            'positions': len(snapshot.positions),
            'total_value': snapshot.total_value
        })

    # Find duplicates
    duplicates = {
        date_key: timestamps
        for date_key, timestamps in date_counts.items()
        if len(timestamps) > 1
    }

    if duplicates:
        logger.error("DUPLICATE PORTFOLIO SNAPSHOTS DETECTED:")
        for date_key, snapshots_list in duplicates.items():
            logger.error(f"\n  Date: {date_key} ({len(snapshots_list)} snapshots)")
            for snap in snapshots_list:
                logger.error(f"    - {snap['timestamp']} ({snap['positions']} positions)")

        if strict:
            raise ValueError(
                f"Found {len(duplicates)} dates with duplicate snapshots. "
                "This will cause incorrect P&L calculations. "
                "Run the rebuild script to fix: python debug/rebuild_portfolio_complete.py"
            )
        else:
            logger.warning("WARNING: Continuing despite duplicate snapshots...")

    return bool(duplicates), duplicates


def validate_snapshot_timestamps(snapshots: list[PortfolioSnapshot]) -> bool:
    """
    Validate that snapshots have proper timestamps (market close at 16:00:00).

    Args:
        snapshots: List of portfolio snapshots to validate

    Returns:
        True if all timestamps are valid, False otherwise
    """
    invalid_found = False

    for snapshot in snapshots:
        # Check if timestamp is timezone-aware
        if snapshot.timestamp.tzinfo is None:
            logger.warning(f"WARNING: Snapshot for {snapshot.timestamp.date()} has naive timestamp")
            invalid_found = True

        # Market close snapshots should be at 16:00:00
        if snapshot.timestamp.hour == 16 and snapshot.timestamp.minute == 0:
            continue  # Valid market close time
        else:
            logger.info(f"INFO: Intraday snapshot at {snapshot.timestamp} (not market close)")

    return not invalid_found


def validate_trade_data(trade) -> tuple[bool, list[str]]:
    """
    Validate trade data for integrity and correctness.

    Args:
        trade: Trade object or dictionary to validate

    Returns:
        Tuple of (is_valid: bool, errors: list)
    """
    errors = []

    try:
        # Check if trade has required fields
        if hasattr(trade, 'ticker'):
            ticker = trade.ticker
            action = getattr(trade, 'action', getattr(trade, 'Action', None))
            shares = getattr(trade, 'shares', getattr(trade, 'Shares', None))
            price = getattr(trade, 'price', getattr(trade, 'Price', None))
        else:
            # Assume it's a dictionary
            ticker = trade.get('ticker', trade.get('Ticker'))
            action = trade.get('action', trade.get('Action'))
            shares = trade.get('shares', trade.get('Shares'))
            price = trade.get('price', trade.get('Price'))

        # Validate ticker
        if not ticker or not isinstance(ticker, str) or len(ticker.strip()) == 0:
            errors.append("Ticker symbol is required and must be a non-empty string")

        # Validate action
        if action not in ['BUY', 'SELL', 'HOLD']:
            errors.append(f"Invalid action '{action}'. Must be BUY, SELL, or HOLD")

        # Validate shares
        if shares is None:
            errors.append("Shares quantity is required")
        elif not isinstance(shares, int | float) or shares <= 0:
            errors.append("Shares quantity must be a positive number")

        # Validate price
        if price is None:
            errors.append("Price is required")
        elif not isinstance(price, int | float) or price <= 0:
            errors.append("Price must be a positive number")

        # Validate timestamp if present
        timestamp = getattr(trade, 'timestamp', getattr(trade, 'Timestamp', trade.get('timestamp', trade.get('Timestamp'))))
        if timestamp:
            from datetime import datetime
            if not isinstance(timestamp, datetime):
                errors.append("Timestamp must be a datetime object")

    except Exception as e:
        errors.append(f"Error validating trade data: {e}")

    return len(errors) == 0, errors

