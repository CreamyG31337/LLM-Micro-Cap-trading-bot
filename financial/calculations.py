"""
Financial calculations module with precise Decimal arithmetic.

This module provides all core financial calculation functions using Decimal
arithmetic to ensure precision in monetary calculations and avoid floating-point
precision issues.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Union, List

# Type alias for numeric inputs that will be converted to Decimal
# Note: floats should be avoided in new code, this alias is for legacy compatibility
NumericInput = Union[float, int, str, Decimal]

# Type alias for validated financial values (should always be Decimal)
FinancialDecimal = Decimal


def validate_no_float_usage(*args, function_name: str = "financial_function") -> None:
    """Validate that no float values are being passed to financial functions.
    
    This is a runtime validation to help catch float usage during development
    and testing. Should be removed or made optional in production.
    
    Args:
        *args: Arguments to validate
        function_name: Name of the function for error messages
        
    Raises:
        ValueError: If any argument is a float
    """
    for i, arg in enumerate(args):
        if isinstance(arg, float):
            raise ValueError(
                f"Float usage detected in {function_name} (argument {i}): {arg}. "
                f"Use Decimal instead to avoid precision issues."
            )
        elif hasattr(arg, '__iter__') and not isinstance(arg, (str, bytes)):
            # Check list/tuple arguments
            try:
                for j, item in enumerate(arg):
                    if isinstance(item, float):
                        raise ValueError(
                            f"Float usage detected in {function_name} (argument {i}[{j}]): {item}. "
                            f"Use Decimal instead to avoid precision issues."
                        )
            except (TypeError, AttributeError):
                # Skip non-iterable arguments
                pass


def money_to_decimal(value: NumericInput) -> FinancialDecimal:
    """
    Convert monetary values to Decimal for precise calculations.
    
    Args:
        value: The monetary value to convert (float, int, str, or Decimal)
        
    Returns:
        Decimal: The value as a Decimal rounded to 2 decimal places
        
    Examples:
        >>> money_to_decimal(10.99)
        Decimal('10.99')
        >>> money_to_decimal("15.555")
        Decimal('15.56')
    """
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_cost_basis(price: NumericInput, shares: NumericInput) -> FinancialDecimal:
    """
    Calculate cost basis with precise decimal arithmetic.
    
    Args:
        price: The price per share
        shares: The number of shares
        
    Returns:
        Decimal: The total cost basis (price * shares) rounded to 2 decimal places
        
    Examples:
        >>> calculate_cost_basis(10.50, 100)
        Decimal('1050.00')
        >>> calculate_cost_basis(15.333, 50)
        Decimal('766.65')
    """
    # Runtime validation to catch float usage during development
    validate_no_float_usage(price, shares, function_name="calculate_cost_basis")
    
    price_dec = money_to_decimal(price)
    shares_dec = Decimal(str(shares))
    return (price_dec * shares_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_position_value(price: NumericInput, shares: NumericInput) -> FinancialDecimal:
    """
    Calculate position value with precise decimal arithmetic.
    
    This is functionally identical to calculate_cost_basis but semantically
    different - used for current market value calculations.
    
    Args:
        price: The current price per share
        shares: The number of shares held
        
    Returns:
        Decimal: The total position value (price * shares) rounded to 2 decimal places
        
    Examples:
        >>> calculate_position_value(12.75, 100)
        Decimal('1275.00')
        >>> calculate_position_value(8.999, 200)
        Decimal('1799.80')
    """
    price_dec = money_to_decimal(price)
    shares_dec = Decimal(str(shares))
    return (price_dec * shares_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calculate_pnl(current_price: NumericInput, buy_price: NumericInput, shares: NumericInput) -> FinancialDecimal:
    """
    Calculate profit/loss with precise decimal arithmetic.
    
    Args:
        current_price: The current market price per share
        buy_price: The original purchase price per share
        shares: The number of shares held
        
    Returns:
        Decimal: The unrealized P&L ((current_price - buy_price) * shares)
        
    Examples:
        >>> calculate_pnl(15.00, 10.00, 100)
        Decimal('500.00')
        >>> calculate_pnl(8.50, 10.00, 100)
        Decimal('-150.00')
    """
    # Runtime validation to catch float usage during development
    validate_no_float_usage(current_price, buy_price, shares, function_name="calculate_pnl")
    
    current_dec = money_to_decimal(current_price)
    buy_dec = money_to_decimal(buy_price)
    shares_dec = Decimal(str(shares))
    return ((current_dec - buy_dec) * shares_dec).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def round_money(value: NumericInput) -> float:
    """
    Round monetary value to 2 decimal places and return as float.
    
    This function is useful when you need to convert back to float for
    display or compatibility with systems that expect float values.
    
    Args:
        value: The monetary value to round
        
    Returns:
        float: The value rounded to 2 decimal places as a float
        
    Examples:
        >>> round_money(10.999)
        11.0
        >>> round_money(15.555)
        15.56
    """
    return float(money_to_decimal(value))


def validate_money_precision(value: float, tolerance: float = 0.005) -> bool:
    """
    Check if a float value has precision issues (far from a clean decimal).
    
    This function helps identify when floating-point arithmetic has introduced
    precision errors that might affect financial calculations.
    
    Args:
        value: The float value to check
        tolerance: The acceptable difference from the rounded decimal value
        
    Returns:
        bool: True if the value is within tolerance of its decimal representation
        
    Examples:
        >>> validate_money_precision(10.99)
        True
        >>> validate_money_precision(10.999999999999998)  # Float precision issue
        True
        >>> validate_money_precision(10.9876543)  # Significant difference
        False
    """
    dec_value = money_to_decimal(value)
    float_value = float(dec_value)
    return abs(value - float_value) < tolerance


def calculate_percentage_change(old_value: NumericInput, new_value: NumericInput) -> FinancialDecimal:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: The original value
        new_value: The new value
        
    Returns:
        Decimal: The percentage change as a decimal (e.g., 0.15 for 15%)
        
    Examples:
        >>> calculate_percentage_change(100, 115)
        Decimal('0.15')
        >>> calculate_percentage_change(100, 85)
        Decimal('-0.15')
    """
    old_dec = money_to_decimal(old_value)
    new_dec = money_to_decimal(new_value)
    
    if old_dec == 0:
        return Decimal('0')
    
    change = new_dec - old_dec
    percentage = (change / old_dec).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    return percentage


def calculate_weighted_average_price(prices: List[NumericInput], quantities: List[NumericInput]) -> FinancialDecimal:
    """
    Calculate weighted average price given prices and quantities.
    
    Args:
        prices: List of prices
        quantities: List of corresponding quantities
        
    Returns:
        Decimal: The weighted average price
        
    Raises:
        ValueError: If prices and quantities lists have different lengths
        ZeroDivisionError: If total quantity is zero
        
    Examples:
        >>> calculate_weighted_average_price([10.00, 12.00], [100, 50])
        Decimal('10.67')
    """
    if len(prices) != len(quantities):
        raise ValueError("Prices and quantities lists must have the same length")
    
    # Runtime validation to catch float usage during development
    validate_no_float_usage(prices, quantities, function_name="calculate_weighted_average_price")
    
    total_value = Decimal('0')
    total_quantity = Decimal('0')
    
    for price, quantity in zip(prices, quantities):
        price_dec = money_to_decimal(price)
        quantity_dec = Decimal(str(quantity))
        total_value += price_dec * quantity_dec
        total_quantity += quantity_dec
    
    if total_quantity == 0:
        raise ZeroDivisionError("Total quantity cannot be zero")
    
    return (total_value / total_quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
