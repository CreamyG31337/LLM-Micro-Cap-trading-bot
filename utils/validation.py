"""Data validation utilities for the trading system.

This module provides validation functions for portfolio data, trade data, and data integrity
checks that work with any repository type (CSV or future database backends).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Union
import pandas as pd
import re
from datetime import datetime


def validate_money_precision(value: float, tolerance: float = 0.005) -> bool:
    """Check if a float value has precision issues (far from a clean decimal).
    
    Args:
        value: The float value to check
        tolerance: Maximum allowed difference between float and decimal representation
    
    Returns:
        bool: True if the value has acceptable precision, False if there are issues
    """
    try:
        from financial.calculations import money_to_decimal
        dec_value = money_to_decimal(value)
    except ImportError:
        # Fallback implementation if financial module not available
        dec_value = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    float_value = float(dec_value)
    return abs(value - float_value) < tolerance


def validate_ticker_format(ticker: str) -> bool:
    """Validate that a ticker symbol has the correct format.
    
    Valid tickers: start with a letter; allow letters/digits/dot/dash afterwards
    
    Args:
        ticker: The ticker symbol to validate
    
    Returns:
        bool: True if ticker format is valid, False otherwise
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    ticker = ticker.strip().upper()
    if not ticker:
        return False
    
    # Valid tickers: start with a letter; allow letters/digits/dot/dash afterwards
    pattern = r"^[A-Za-z][A-Za-z0-9\.-]*$"
    return bool(re.fullmatch(pattern, ticker))


def filter_valid_tickers_df(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Filter out invalid/blank tickers from a DataFrame.
    
    Args:
        df: The DataFrame to filter
        col_name: The name of the ticker column
    
    Returns:
        pd.DataFrame: Filtered DataFrame with only valid tickers
    """
    if col_name not in df.columns:
        return df
    
    s = df[col_name].astype(str)
    upper = s.str.upper()
    
    # Valid tickers: start with a letter; allow letters/digits/dot/dash afterwards
    pattern = r"^[A-Za-z][A-Za-z0-9\.-]*$"
    mask_valid = (
        df[col_name].notna()
        & (s.str.strip() != "")
        & (upper != "NAN")
        & (upper != "NONE")
        & (upper != "NULL")
        & s.str.fullmatch(pattern, na=False)
    )
    return df[mask_valid].copy()


def validate_portfolio_data(portfolio_df: pd.DataFrame) -> List[str]:
    """Validate portfolio data integrity.
    
    Args:
        portfolio_df: The portfolio DataFrame to validate
    
    Returns:
        List[str]: List of validation error messages (empty if no issues)
    """
    issues = []
    
    if portfolio_df.empty:
        return issues  # Empty portfolio is valid
    
    # Check required columns
    required_columns = ['Date', 'Ticker', 'Shares', 'Average Price']
    missing_columns = [col for col in required_columns if col not in portfolio_df.columns]
    if missing_columns:
        issues.append(f"Portfolio data missing required columns: {missing_columns}")
        return issues  # Can't continue validation without required columns
    
    # Check for negative shares
    if (portfolio_df['Shares'] < 0).any():
        negative_count = (portfolio_df['Shares'] < 0).sum()
        issues.append(f"Portfolio contains {negative_count} positions with negative share counts")
    
    # Check for zero or negative prices
    if (portfolio_df['Average Price'] <= 0).any():
        invalid_price_count = (portfolio_df['Average Price'] <= 0).sum()
        issues.append(f"Portfolio contains {invalid_price_count} positions with zero or negative prices")
    
    # Check for invalid tickers
    invalid_tickers = []
    for idx, ticker in portfolio_df['Ticker'].items():
        if not validate_ticker_format(str(ticker)):
            invalid_tickers.append(f"Row {idx}: '{ticker}'")
    
    if invalid_tickers:
        issues.append(f"Portfolio contains invalid ticker symbols: {invalid_tickers[:5]}")  # Limit to first 5
        if len(invalid_tickers) > 5:
            issues.append(f"... and {len(invalid_tickers) - 5} more invalid tickers")
    
    # Check for precision issues in monetary columns
    monetary_columns = ['Average Price', 'Cost Basis', 'Stop Loss', 'Current Price', 'Total Value', 'PnL']
    for col in monetary_columns:
        if col in portfolio_df.columns:
            precision_issues = []
            for idx, value in portfolio_df[col].items():
                if pd.notna(value) and isinstance(value, (int, float)):
                    if not validate_money_precision(float(value)):
                        precision_issues.append(f"Row {idx}: {value}")
            
            if precision_issues:
                issues.append(f"Column '{col}' has precision issues: {precision_issues[:3]}")  # Limit to first 3
                if len(precision_issues) > 3:
                    issues.append(f"... and {len(precision_issues) - 3} more precision issues in '{col}'")
    
    # Check for duplicate positions (same ticker, same date)
    if len(portfolio_df) > 1:
        duplicates = portfolio_df.duplicated(subset=['Date', 'Ticker'], keep=False)
        if duplicates.any():
            duplicate_count = duplicates.sum()
            issues.append(f"Portfolio contains {duplicate_count} duplicate positions (same ticker and date)")
    
    return issues


def validate_trade_data(trade_df: pd.DataFrame) -> List[str]:
    """Validate trade data integrity.
    
    Args:
        trade_df: The trade DataFrame to validate
    
    Returns:
        List[str]: List of validation error messages (empty if no issues)
    """
    issues = []
    
    if trade_df.empty:
        return issues  # Empty trade log is valid
    
    # Check required columns
    required_columns = ['Date', 'Ticker', 'Shares Bought', 'Buy Price']
    missing_columns = [col for col in required_columns if col not in trade_df.columns]
    if missing_columns:
        issues.append(f"Trade data missing required columns: {missing_columns}")
        return issues  # Can't continue validation without required columns
    
    # Check for zero or negative shares
    if (trade_df['Shares Bought'] <= 0).any():
        invalid_shares_count = (trade_df['Shares Bought'] <= 0).sum()
        issues.append(f"Trade log contains {invalid_shares_count} trades with zero or negative shares")
    
    # Check for zero or negative prices
    if (trade_df['Buy Price'] <= 0).any():
        invalid_price_count = (trade_df['Buy Price'] <= 0).sum()
        issues.append(f"Trade log contains {invalid_price_count} trades with zero or negative prices")
    
    # Check for invalid tickers
    invalid_tickers = []
    for idx, ticker in trade_df['Ticker'].items():
        if not validate_ticker_format(str(ticker)):
            invalid_tickers.append(f"Row {idx}: '{ticker}'")
    
    if invalid_tickers:
        issues.append(f"Trade log contains invalid ticker symbols: {invalid_tickers[:5]}")  # Limit to first 5
        if len(invalid_tickers) > 5:
            issues.append(f"... and {len(invalid_tickers) - 5} more invalid tickers")
    
    # Check for precision issues in monetary columns
    monetary_columns = ['Buy Price', 'Stop Loss', 'Current Price', 'Total Value', 'PnL']
    for col in monetary_columns:
        if col in trade_df.columns:
            precision_issues = []
            for idx, value in trade_df[col].items():
                if pd.notna(value) and isinstance(value, (int, float)):
                    if not validate_money_precision(float(value)):
                        precision_issues.append(f"Row {idx}: {value}")
            
            if precision_issues:
                issues.append(f"Column '{col}' has precision issues: {precision_issues[:3]}")  # Limit to first 3
                if len(precision_issues) > 3:
                    issues.append(f"... and {len(precision_issues) - 3} more precision issues in '{col}'")
    
    return issues


def validate_cash_balance_data(cash_data: Dict[str, Any]) -> List[str]:
    """Validate cash balance data integrity.
    
    Args:
        cash_data: Dictionary containing cash balance information
    
    Returns:
        List[str]: List of validation error messages (empty if no issues)
    """
    issues = []
    
    if not isinstance(cash_data, dict):
        issues.append("Cash balance data must be a dictionary")
        return issues
    
    # Check for required fields
    required_fields = ['cad_balance', 'usd_balance']
    for field in required_fields:
        if field not in cash_data:
            issues.append(f"Cash balance data missing required field: '{field}'")
    
    # Validate balance values
    for field in ['cad_balance', 'usd_balance']:
        if field in cash_data:
            value = cash_data[field]
            if not isinstance(value, (int, float)):
                try:
                    float(value)
                except (ValueError, TypeError):
                    issues.append(f"Cash balance '{field}' must be a number, got: {type(value).__name__}")
            else:
                if value < 0:
                    issues.append(f"Cash balance '{field}' cannot be negative: {value}")
                elif not validate_money_precision(float(value)):
                    issues.append(f"Cash balance '{field}' has precision issues: {value}")
    
    return issues


def validate_date_format(date_str: str, expected_format: str = "%Y-%m-%d") -> bool:
    """Validate that a date string matches the expected format.
    
    Args:
        date_str: The date string to validate
        expected_format: The expected date format (default: YYYY-MM-DD)
    
    Returns:
        bool: True if date format is valid, False otherwise
    """
    if not isinstance(date_str, str):
        return False
    
    try:
        datetime.strptime(date_str, expected_format)
        return True
    except ValueError:
        return False


def validate_numeric_range(value: Union[int, float], min_value: Optional[float] = None, 
                          max_value: Optional[float] = None) -> bool:
    """Validate that a numeric value is within the specified range.
    
    Args:
        value: The numeric value to validate
        min_value: Minimum allowed value (inclusive), None for no minimum
        max_value: Maximum allowed value (inclusive), None for no maximum
    
    Returns:
        bool: True if value is within range, False otherwise
    """
    if not isinstance(value, (int, float)):
        return False
    
    if min_value is not None and value < min_value:
        return False
    
    if max_value is not None and value > max_value:
        return False
    
    return True


def check_data_integrity(portfolio_df: Optional[pd.DataFrame] = None, 
                        trade_df: Optional[pd.DataFrame] = None,
                        cash_data: Optional[Dict[str, Any]] = None) -> Dict[str, List[str]]:
    """Perform comprehensive data integrity checks across all data types.
    
    This function works with any repository type by accepting the data directly
    rather than accessing files or databases directly.
    
    Args:
        portfolio_df: Portfolio DataFrame to validate (optional)
        trade_df: Trade DataFrame to validate (optional)
        cash_data: Cash balance data to validate (optional)
    
    Returns:
        Dict[str, List[str]]: Dictionary with validation results for each data type
    """
    results = {
        'portfolio': [],
        'trades': [],
        'cash': [],
        'cross_validation': []
    }
    
    # Validate individual data types
    if portfolio_df is not None:
        results['portfolio'] = validate_portfolio_data(portfolio_df)
    
    if trade_df is not None:
        results['trades'] = validate_trade_data(trade_df)
    
    if cash_data is not None:
        results['cash'] = validate_cash_balance_data(cash_data)
    
    # Cross-validation checks (if multiple data sources provided)
    if portfolio_df is not None and trade_df is not None:
        # Check if all portfolio tickers have corresponding trades
        if not portfolio_df.empty and not trade_df.empty:
            portfolio_tickers = set(portfolio_df['Ticker'].unique())
            trade_tickers = set(trade_df['Ticker'].unique())
            
            orphaned_positions = portfolio_tickers - trade_tickers
            if orphaned_positions:
                results['cross_validation'].append(
                    f"Portfolio contains positions without trade history: {list(orphaned_positions)[:5]}"
                )
                if len(orphaned_positions) > 5:
                    results['cross_validation'].append(
                        f"... and {len(orphaned_positions) - 5} more orphaned positions"
                    )
    
    return results


def fix_monetary_precision_issues(df: pd.DataFrame, monetary_columns: List[str]) -> pd.DataFrame:
    """Fix precision issues in monetary columns by converting to proper Decimal format.
    
    Args:
        df: The DataFrame to fix
        monetary_columns: List of column names that contain monetary values
    
    Returns:
        pd.DataFrame: DataFrame with fixed precision issues
    """
    df_fixed = df.copy()
    
    try:
        from financial.calculations import money_to_decimal
    except ImportError:
        # Fallback implementation if financial module not available
        def money_to_decimal(value):
            return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    for col in monetary_columns:
        if col in df_fixed.columns:
            # Apply precision fix to non-null values
            mask = df_fixed[col].notna()
            df_fixed.loc[mask, col] = df_fixed.loc[mask, col].apply(
                lambda x: float(money_to_decimal(x)) if isinstance(x, (int, float)) else x
            )
    
    return df_fixed