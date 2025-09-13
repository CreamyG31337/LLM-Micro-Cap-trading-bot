"""
Decimal formatting utilities for consistent price and share formatting.

This module provides utility functions to ensure consistent decimal formatting
across the trading bot, preventing float precision issues in CSV files.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union, Any


def format_price(value: Union[Decimal, float, int, str, None], default: float = 0.0) -> float:
    """
    Format a price value to 2 decimal places.
    
    Args:
        value: Price value to format (Decimal, float, int, str, or None)
        default: Default value if input is None or invalid
        
    Returns:
        Price formatted to 2 decimal places
    """
    if value is None:
        return round(default, 2)
    
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        return round(float(value), 2)
    except (ValueError, TypeError):
        return round(default, 2)


def format_shares(value: Union[Decimal, float, int, str, None], default: float = 0.0) -> float:
    """
    Format a shares value to 4 decimal places.
    
    Args:
        value: Shares value to format (Decimal, float, int, str, or None)
        default: Default value if input is None or invalid
        
    Returns:
        Shares formatted to 4 decimal places
    """
    if value is None:
        return round(default, 4)
    
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        return round(float(value), 4)
    except (ValueError, TypeError):
        return round(default, 4)


def format_currency(value: Union[Decimal, float, int, str, None], default: float = 0.0) -> float:
    """
    Format a currency value to 2 decimal places.
    
    Args:
        value: Currency value to format (Decimal, float, int, str, or None)
        default: Default value if input is None or invalid
        
    Returns:
        Currency formatted to 2 decimal places
    """
    return format_price(value, default)


def format_percentage(value: Union[Decimal, float, int, str, None], default: float = 0.0) -> float:
    """
    Format a percentage value to 1 decimal place.
    
    Args:
        value: Percentage value to format (Decimal, float, int, str, or None)
        default: Default value if input is None or invalid
        
    Returns:
        Percentage formatted to 1 decimal place
    """
    if value is None:
        return round(default, 1)
    
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        return round(float(value), 1)
    except (ValueError, TypeError):
        return round(default, 1)


def safe_float_conversion(value: Any, precision: int = 2, default: float = 0.0) -> float:
    """
    Safely convert any value to float with specified precision.
    
    Args:
        value: Value to convert
        precision: Number of decimal places (default: 2)
        default: Default value if conversion fails
        
    Returns:
        Float value with specified precision
    """
    if value is None:
        return round(default, precision)
    
    try:
        if isinstance(value, str):
            value = float(value)
        elif isinstance(value, Decimal):
            value = float(value)
        
        return round(float(value), precision)
    except (ValueError, TypeError):
        return round(default, precision)


def format_position_dict(position_dict: dict) -> dict:
    """
    Format all numeric values in a position dictionary with appropriate precision.
    
    Args:
        position_dict: Dictionary containing position data
        
    Returns:
        Dictionary with properly formatted numeric values
    """
    formatted = position_dict.copy()
    
    # Format shares to 4 decimal places
    if 'shares' in formatted:
        formatted['shares'] = format_shares(formatted['shares'])
    
    # Format prices to 2 decimal places
    price_fields = ['avg_price', 'current_price', 'cost_basis', 'market_value', 'unrealized_pnl', 'stop_loss']
    for field in price_fields:
        if field in formatted:
            formatted[field] = format_price(formatted[field])
    
    return formatted


def validate_decimal_precision(value: float, expected_precision: int = 2) -> bool:
    """
    Validate that a float value has the expected decimal precision.
    
    Args:
        value: Float value to validate
        expected_precision: Expected number of decimal places
        
    Returns:
        True if value has correct precision, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False
    
    # Convert to string and check decimal places
    str_value = f"{value:.10f}".rstrip('0').rstrip('.')
    if '.' in str_value:
        decimal_places = len(str_value.split('.')[1])
        return decimal_places <= expected_precision
    else:
        return True  # Integer values are fine
