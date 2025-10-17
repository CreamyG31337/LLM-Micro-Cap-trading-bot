"""
P&L (Profit & Loss) calculation module for portfolio performance analysis.

This module provides comprehensive P&L calculations including daily P&L,
total returns, and performance metrics. It's designed to work with both
CSV and future database backends through the repository pattern.
"""

import logging
from decimal import Decimal

from .calculations import money_to_decimal, calculate_pnl, calculate_percentage_change
from utils.market_holidays import MarketHolidays

logger = logging.getLogger(__name__)

# Type alias for numeric inputs
NumericInput = float | int | str | Decimal


def _get_ticker_market(ticker: str) -> str:
    """Determine if ticker is Canadian or US market."""
    if ticker.endswith('.TO'):
        return 'canadian'
    return 'us'


class PnLCalculator:
    """
    Handles P&L calculations and performance metrics for portfolio analysis.

    This class provides methods for calculating various types of P&L including
    unrealized P&L, realized P&L, daily performance, and total returns.
    """

    def __init__(self, repository=None):
        """
        Initialize P&L calculator.

        Args:
            repository: Data repository for accessing portfolio and trade data
        """
        self.repository = repository

    def calculate_position_pnl(self, current_price: NumericInput,
                              buy_price: NumericInput,
                              shares: NumericInput) -> dict[str, Decimal]:
        """
        Calculate P&L for a single position.

        Args:
            current_price: Current market price per share
            buy_price: Original purchase price per share
            shares: Number of shares held

        Returns:
            Dict containing P&L calculations
        """
        current_dec = money_to_decimal(current_price)
        buy_dec = money_to_decimal(buy_price)
        shares_dec = money_to_decimal(shares)

        # Calculate absolute P&L
        absolute_pnl = calculate_pnl(current_price, buy_price, shares)

        # Calculate percentage P&L
        if buy_dec != 0:
            percentage_pnl = calculate_percentage_change(buy_price, current_price)
        else:
            percentage_pnl = Decimal('0')

        # Calculate position values
        cost_basis = buy_dec * shares_dec
        current_value = current_dec * shares_dec

        return {
            'absolute_pnl': absolute_pnl,
            'percentage_pnl': percentage_pnl,
            'cost_basis': cost_basis,
            'current_value': current_value,
            'current_price': current_dec,
            'buy_price': buy_dec,
            'shares': shares_dec
        }

    def calculate_daily_pnl(self, current_price: NumericInput,
                           previous_price: NumericInput,
                           shares: NumericInput) -> dict[str, Decimal]:
        """
        Calculate daily P&L based on price change from previous day.

        Args:
            current_price: Current market price per share
            previous_price: Previous day's closing price per share
            shares: Number of shares held

        Returns:
            Dict containing daily P&L calculations
        """
        current_dec = money_to_decimal(current_price)
        prev_dec = money_to_decimal(previous_price)
        shares_dec = money_to_decimal(shares)

        # Calculate daily absolute P&L
        daily_absolute_pnl = calculate_pnl(current_price, previous_price, shares)

        # Calculate daily percentage P&L
        if prev_dec != 0:
            daily_percentage_pnl = calculate_percentage_change(previous_price, current_price)
        else:
            daily_percentage_pnl = Decimal('0')

        return {
            'daily_absolute_pnl': daily_absolute_pnl,
            'daily_percentage_pnl': daily_percentage_pnl,
            'current_price': current_dec,
            'previous_price': prev_dec,
            'shares': shares_dec
        }

    def calculate_period_pnl(self, current_price: NumericInput,
                            period_start_price: NumericInput,
                            shares: NumericInput,
                            period_name: str = "period") -> dict[str, Decimal]:
        """
        Calculate P&L for a specific time period (e.g., 5-day, 1-month).

        Args:
            current_price: Current market price per share
            period_start_price: Price at the start of the period
            shares: Number of shares held
            period_name: Name of the period for labeling

        Returns:
            Dict containing period P&L calculations
        """
        current_dec = money_to_decimal(current_price)
        start_dec = money_to_decimal(period_start_price)
        shares_dec = money_to_decimal(shares)

        # Calculate period absolute P&L
        period_absolute_pnl = calculate_pnl(current_price, period_start_price, shares)

        # Calculate period percentage P&L
        if start_dec != 0:
            period_percentage_pnl = calculate_percentage_change(period_start_price, current_price)
        else:
            period_percentage_pnl = Decimal('0')

        return {
            f'{period_name}_absolute_pnl': period_absolute_pnl,
            f'{period_name}_percentage_pnl': period_percentage_pnl,
            'current_price': current_dec,
            f'{period_name}_start_price': start_dec,
            'shares': shares_dec
        }

    def calculate_portfolio_pnl(self, positions) -> dict[str, Decimal]:
        """
        Calculate total P&L for entire portfolio.

        Args:
            positions: List of position objects or dictionaries with price and share data

        Returns:
            Dict containing portfolio-wide P&L metrics
        """
        total_cost_basis = Decimal('0')
        total_current_value = Decimal('0')
        total_absolute_pnl = Decimal('0')
        position_count = 0

        for position in positions:
            if not self._is_valid_position(position):
                continue

            # Handle both Position objects and dictionaries
            if hasattr(position, '__dict__'):
                # Position object
                current_price = position.current_price
                buy_price = position.avg_price  # Position uses avg_price, not buy_price
                shares = position.shares
            else:
                # Dictionary
                current_price = position['current_price']
                buy_price = position['buy_price']
                shares = position['shares']

            pos_pnl = self.calculate_position_pnl(
                current_price,
                buy_price,
                shares
            )

            total_cost_basis += pos_pnl['cost_basis']
            total_current_value += pos_pnl['current_value']
            total_absolute_pnl += pos_pnl['absolute_pnl']
            position_count += 1

        # Calculate portfolio percentage P&L
        if total_cost_basis != 0:
            portfolio_percentage_pnl = (total_absolute_pnl / total_cost_basis).quantize(Decimal('0.0001'))
        else:
            portfolio_percentage_pnl = Decimal('0')

        return {
            'total_cost_basis': total_cost_basis,
            'total_current_value': total_current_value,
            'total_absolute_pnl': total_absolute_pnl,
            'portfolio_percentage_pnl': portfolio_percentage_pnl,
            'position_count': position_count
        }

    def calculate_total_return(self, initial_investment: NumericInput,
                              current_value: NumericInput,
                              additional_contributions: NumericInput = 0) -> dict[str, Decimal]:
        """
        Calculate total return on investment.

        Args:
            initial_investment: Initial amount invested
            current_value: Current portfolio value
            additional_contributions: Additional money added over time

        Returns:
            Dict containing total return calculations
        """
        initial_dec = money_to_decimal(initial_investment)
        current_dec = money_to_decimal(current_value)
        contributions_dec = money_to_decimal(additional_contributions)

        total_invested = initial_dec + contributions_dec
        absolute_return = current_dec - total_invested

        if total_invested != 0:
            percentage_return = (absolute_return / total_invested).quantize(Decimal('0.0001'))
        else:
            percentage_return = Decimal('0')

        return {
            'total_invested': total_invested,
            'current_value': current_dec,
            'absolute_return': absolute_return,
            'percentage_return': percentage_return,
            'initial_investment': initial_dec,
            'additional_contributions': contributions_dec
        }

    def calculate_performance_metrics(self, positions: list[dict],
                                    cash_balance: NumericInput = 0,
                                    total_contributions: NumericInput = 0) -> dict[str, Decimal | int]:
        """
        Calculate comprehensive performance metrics for the portfolio.

        Args:
            positions: List of position dictionaries
            cash_balance: Current cash balance
            total_contributions: Total money contributed to portfolio

        Returns:
            Dict containing comprehensive performance metrics
        """
        portfolio_pnl = self.calculate_portfolio_pnl(positions)
        cash_dec = money_to_decimal(cash_balance)

        # Calculate total portfolio value (positions + cash)
        total_portfolio_value = portfolio_pnl['total_current_value'] + cash_dec

        # Calculate total return if contributions are provided
        if total_contributions > 0:
            total_return = self.calculate_total_return(
                total_contributions,
                total_portfolio_value
            )
        else:
            total_return = {
                'total_invested': portfolio_pnl['total_cost_basis'],
                'current_value': total_portfolio_value,
                'absolute_return': portfolio_pnl['total_absolute_pnl'],
                'percentage_return': portfolio_pnl['portfolio_percentage_pnl']
            }

        # Calculate position statistics
        winning_positions = 0
        losing_positions = 0

        for position in positions:
            if not self._is_valid_position(position):
                continue

            pos_pnl = self.calculate_position_pnl(
                position['current_price'],
                position['buy_price'],
                position['shares']
            )

            if pos_pnl['absolute_pnl'] > 0:
                winning_positions += 1
            elif pos_pnl['absolute_pnl'] < 0:
                losing_positions += 1

        total_positions = winning_positions + losing_positions
        win_rate = Decimal(winning_positions) / Decimal(max(total_positions, 1))

        return {
            # Portfolio totals
            'total_cost_basis': portfolio_pnl['total_cost_basis'],
            'total_current_value': portfolio_pnl['total_current_value'],
            'cash_balance': cash_dec,
            'total_portfolio_value': total_portfolio_value,

            # P&L metrics
            'total_absolute_pnl': portfolio_pnl['total_absolute_pnl'],
            'portfolio_percentage_pnl': portfolio_pnl['portfolio_percentage_pnl'],

            # Return metrics
            'total_invested': total_return['total_invested'],
            'absolute_return': total_return['absolute_return'],
            'percentage_return': total_return['percentage_return'],

            # Position statistics
            'total_positions': total_positions,
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'win_rate': win_rate
        }

    def calculate_position_weight(self, position_value: NumericInput,
                                 total_portfolio_value: NumericInput) -> Decimal:
        """
        Calculate position weight as percentage of total portfolio.

        Args:
            position_value: Current value of the position
            total_portfolio_value: Total portfolio value

        Returns:
            Position weight as decimal (e.g., 0.15 for 15%)
        """
        position_dec = money_to_decimal(position_value)
        total_dec = money_to_decimal(total_portfolio_value)

        if total_dec == 0:
            return Decimal('0')

        return (position_dec / total_dec).quantize(Decimal('0.0001'))

    def format_pnl_display(self, pnl_value: NumericInput,
                          is_percentage: bool = False) -> str:
        """
        Format P&L value for display with appropriate colors and symbols.

        Args:
            pnl_value: P&L value to format
            is_percentage: Whether the value is a percentage

        Returns:
            Formatted string for display
        """
        value_dec = money_to_decimal(pnl_value) if not is_percentage else Decimal(str(pnl_value))

        if is_percentage:
            # Convert decimal to percentage (e.g., 0.15 -> 15.0%)
            percentage = (value_dec * 100).quantize(Decimal('0.1'))
            if percentage >= 0:
                return f"+{percentage}%"
            else:
                return f"{percentage}%"
        else:
            # Format as currency
            if value_dec >= 0:
                return f"+${value_dec:,.2f}"
            else:
                return f"-${abs(value_dec):,.2f}"

    def _is_valid_position(self, position) -> bool:
        """
        Validate that a position has required fields for P&L calculation.

        Args:
            position: Position object or dictionary to validate

        Returns:
            True if position is valid, False otherwise
        """
        # Handle both Position objects and dictionaries
        if hasattr(position, '__dict__'):
            # Position object - check attributes
            if not hasattr(position, 'current_price') or position.current_price is None:
                logger.warning("Position missing current_price")
                return False
            if not hasattr(position, 'avg_price') or position.avg_price is None:
                logger.warning("Position missing avg_price")
                return False
            if not hasattr(position, 'shares') or position.shares is None:
                logger.warning("Position missing shares")
                return False

            try:
                current_price = float(position.current_price)
                avg_price = float(position.avg_price)
                shares = float(position.shares)

                if shares < 0:
                    logger.warning(f"Invalid negative shares: {shares}")
                    return False

                if current_price < 0 or avg_price < 0:
                    logger.warning(f"Invalid negative price: current={current_price}, avg={avg_price}")
                    return False

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid numeric values in position: {e}")
                return False
        else:
            # Dictionary - check keys
            required_fields = ['current_price', 'buy_price', 'shares']

            for field in required_fields:
                if field not in position:
                    logger.warning(f"Position missing required field: {field}")
                    return False

                try:
                    value = float(position[field])
                    if value < 0 and field == 'shares':
                        logger.warning(f"Invalid negative shares: {value}")
                        return False
                except (ValueError, TypeError):
                    logger.warning(f"Invalid value for field {field}: {position[field]}")
                    return False

        return True


# Convenience functions for backward compatibility
def calculate_portfolio_cost_basis(positions: list[dict]) -> Decimal:
    """
    Calculate total cost basis for a list of positions.

    Args:
        positions: List of position dictionaries

    Returns:
        Total cost basis as Decimal
    """
    calculator = PnLCalculator()
    portfolio_pnl = calculator.calculate_portfolio_pnl(positions)
    return portfolio_pnl['total_cost_basis']


def calculate_portfolio_current_value(positions: list[dict]) -> Decimal:
    """
    Calculate total current value for a list of positions.

    Args:
        positions: List of position dictionaries

    Returns:
        Total current value as Decimal
    """
    calculator = PnLCalculator()
    portfolio_pnl = calculator.calculate_portfolio_pnl(positions)
    return portfolio_pnl['total_current_value']


def calculate_daily_portfolio_pnl(positions: list[dict],
                                 previous_prices: dict[str, NumericInput]) -> dict[str, Decimal]:
    """
    Calculate daily P&L for entire portfolio.

    Args:
        positions: List of position dictionaries
        previous_prices: Dict mapping ticker to previous day's price

    Returns:
        Dict containing daily portfolio P&L
    """
    calculator = PnLCalculator()
    total_daily_pnl = Decimal('0')

    for position in positions:
        if not calculator._is_valid_position(position):
            continue

        ticker = position.get('ticker', '')
        if ticker not in previous_prices:
            continue

        daily_pnl = calculator.calculate_daily_pnl(
            position['current_price'],
            previous_prices[ticker],
            position['shares']
        )

        total_daily_pnl += daily_pnl['daily_absolute_pnl']

    return {
        'total_daily_absolute_pnl': total_daily_pnl,
        'positions_calculated': len([p for p in positions if calculator._is_valid_position(p)])
    }


def calculate_daily_pnl_from_snapshots(current_position, portfolio_snapshots):
    """
    SHARED FUNCTION: Used by both trading_script.py and prompt_generator.py

    Calculate 1-Day P&L for a position by comparing current_price with previous trading day's closing price.

    For new trades (first day), we compare current price with the buy price to show intraday P&L.
    For existing positions, we compare with the previous trading day's closing price.
    This works on weekends too - showing Friday's performance on Saturday/Sunday.

    Args:
        current_position: Current position object with current_price
        portfolio_snapshots: List of historical portfolio snapshots (from portfolio_manager.load_portfolio())

    Returns:
        str: Formatted 1-Day P&L string (e.g., "$123.45", "$0.00")
    """
    try:
        # logger.debug(f"Calculating daily P&L for {current_position.ticker}")
        logger.debug(f"  Current position price: {current_position.current_price}")
        logger.debug(f"  Current position shares: {current_position.shares}")
        logger.debug(f"  Current position avg_price: {current_position.avg_price}")
        logger.debug(f"  Number of snapshots: {len(portfolio_snapshots)}")

        if not portfolio_snapshots or len(portfolio_snapshots) < 1:
            logger.debug("  No portfolio snapshots available")
            return "$0.00"

        current_price = current_position.current_price
        if current_price is None:
            logger.debug("  Current position has no price data")
            return "$0.00"

        # Note: We always calculate P&L vs previous trading day, even on weekends
        # This shows Friday's performance on Saturday/Sunday, which is more useful
        # than showing $0.00 when markets are closed

        # For new trades (first day), compare current price with buy price for intraday P&L
        # For existing positions, compare with previous day's closing price

        # Check if this is a new position (doesn't exist in any previous snapshot)
        ticker_exists_in_previous_days = False
        for i in range(len(portfolio_snapshots) - 1):  # Check all snapshots except the latest
            previous_snapshot = portfolio_snapshots[i]
            if any(pos.ticker == current_position.ticker for pos in previous_snapshot.positions):
                ticker_exists_in_previous_days = True
                logger.debug(f"  Found {current_position.ticker} in previous snapshots")
                break

        if not ticker_exists_in_previous_days:
            logger.debug(f"  {current_position.ticker} is a new position")
            # This is a new trade on its first day - compare with buy price for intraday P&L
            buy_price = current_position.avg_price
            logger.debug(f"  Buy price: {buy_price}")
            if buy_price and abs(current_price - buy_price) > 0.01:
                daily_price_change = current_price - buy_price
                daily_pnl_amount = daily_price_change * current_position.shares
                logger.debug(f"  New position daily P&L: ${daily_pnl_amount:.2f}")
                return f"${daily_pnl_amount:.2f}"
            else:
                logger.debug("  New position: no significant price change")
                return "$0.00"

        # For existing positions, find the previous day's closing price
        # Need to check market-specific holidays
        market_holidays = MarketHolidays()
        ticker_market = _get_ticker_market(current_position.ticker)
        logger.debug(f"  Looking for previous day data for {current_position.ticker} ({ticker_market} market)")

        for i in range(1, len(portfolio_snapshots)):
            previous_snapshot = portfolio_snapshots[-(i+1)]
            snapshot_date = previous_snapshot.timestamp.date()
            logger.debug(f"  Checking snapshot from {previous_snapshot.timestamp}")

            # Check if this stock's market was open on this date
            if not market_holidays.is_trading_day(snapshot_date, market=ticker_market):
                logger.debug(f"  Skipping {snapshot_date} - {ticker_market} market was closed")
                continue

            # Find the same ticker in previous snapshot
            prev_position = None
            for prev_pos in previous_snapshot.positions:
                if prev_pos.ticker == current_position.ticker:
                    prev_position = prev_pos
                    break

            if prev_position and prev_position.current_price is not None:
                prev_price = prev_position.current_price
                logger.debug(f"  Found previous price from {snapshot_date}: ${prev_price}")

                # Calculate P&L from previous day's closing price
                if abs(current_price - prev_price) > 0.01:  # More than 1 cent difference
                    daily_price_change = current_price - prev_price
                    daily_pnl_amount = daily_price_change * current_position.shares
                    logger.debug(f"  Existing position daily P&L: ${daily_pnl_amount:.2f}")
                    return f"${daily_pnl_amount:.2f}"
                else:
                    logger.debug("  No significant price change from previous trading day")
                    return "$0.00"

        # If no previous day data found, show $0.00
        logger.debug("  No previous day data found")
        return "$0.00"

    except Exception as e:
        logger.debug(f"Could not calculate daily P&L for {current_position.ticker}: {e}")
        return "$0.00"

