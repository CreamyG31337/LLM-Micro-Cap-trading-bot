"""
Financial calculations and utilities for the trading system.

This module provides precise financial calculations using Decimal arithmetic
to avoid floating-point precision issues in monetary calculations, as well as
multi-currency support for CAD/USD trading.
"""

from .calculations import (
    money_to_decimal,
    calculate_cost_basis,
    calculate_position_value,
    calculate_pnl,
    round_money,
    validate_money_precision,
    calculate_percentage_change,
    calculate_weighted_average_price
)

from .currency_handler import (
    CashBalances,
    CurrencyHandler,
    is_canadian_ticker,
    is_us_ticker,
    get_ticker_currency,
    calculate_conversion_with_fee
)

from .pnl_calculator import (
    PnLCalculator,
    calculate_portfolio_cost_basis,
    calculate_portfolio_current_value,
    calculate_daily_portfolio_pnl
)

__all__ = [
    # Calculations
    'money_to_decimal',
    'calculate_cost_basis', 
    'calculate_position_value',
    'calculate_pnl',
    'round_money',
    'validate_money_precision',
    'calculate_percentage_change',
    'calculate_weighted_average_price',
    
    # Currency handling
    'CashBalances',
    'CurrencyHandler',
    'is_canadian_ticker',
    'is_us_ticker',
    'get_ticker_currency',
    'calculate_conversion_with_fee',
    
    # P&L calculations
    'PnLCalculator',
    'calculate_portfolio_cost_basis',
    'calculate_portfolio_current_value',
    'calculate_daily_portfolio_pnl'
]