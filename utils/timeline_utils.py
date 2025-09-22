"""
Timeline utilities for the LLM Micro-Cap Trading Bot experiment.

This module provides centralized functions for calculating and formatting
experiment timeline information consistently across the application.
"""

from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd


def get_experiment_timeline(data_dir: Path | str) -> Tuple[int, int]:
    """
    Calculate the current week and day of the experiment.
    
    The timeline is calculated as:
    - Day 1 = First trading day (experiment start)
    - Week 1 = Days 1-7
    - Week 2 = Days 8-14
    - etc.
    
    Returns the day within the week (1-7), not the overall day number.
    So "Week 2, Day 1" means the 1st day of the 2nd week (which is day 8 overall).
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        Tuple[int, int]: (week_number, day_within_week)
    """
    experiment_start_date = _get_experiment_start_date(data_dir)
    today = datetime.now()
    
    # Convert both to naive datetimes for simple comparison
    if experiment_start_date.tzinfo is not None:
        experiment_start_date = experiment_start_date.replace(tzinfo=None)
    if today.tzinfo is not None:
        today = today.replace(tzinfo=None)
    
    # Calculate days since start (inclusive of both start and end dates)
    days_since_start = (today.date() - experiment_start_date.date()).days
    
    # Ensure we don't go below week 1, day 1
    if days_since_start < 0:
        return 1, 1
    
    # Calculate day number (1-based, inclusive counting)
    # If start date is Sep 8 and today is Sep 15, that's 8 days total
    day_num = days_since_start + 1
    
    # Calculate week number (1-based, so first week is Week 1)
    # Week 1 = Days 1-7, Week 2 = Days 8-14, etc.
    week_num = ((day_num - 1) // 7) + 1
    
    # Calculate day within the week (1-7)
    day_in_week = ((day_num - 1) % 7) + 1
    
    return week_num, day_in_week


def get_total_experiment_day(data_dir: Path | str) -> int:
    """Get the total day number of the experiment (1-based).
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        int: Total day number (1 = first day, 8 = 8th day, etc.)
    """
    days_since_start = get_days_since_start(data_dir)
    return days_since_start + 1


def get_days_since_start(data_dir: Path | str) -> int:
    """Get the number of days since the experiment started.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        int: Number of days since start
    """
    experiment_start_date = _get_experiment_start_date(data_dir)
    today = datetime.now()
    
    # Convert both to naive datetimes for simple comparison
    if experiment_start_date.tzinfo is not None:
        experiment_start_date = experiment_start_date.replace(tzinfo=None)
    if today.tzinfo is not None:
        today = today.replace(tzinfo=None)
    
    return max(0, (today - experiment_start_date).days)


def format_timeline_display(data_dir: Path | str) -> str:
    """
    Get a formatted timeline string for display purposes.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        str: Formatted timeline string like "Week 2 Day 1"
    """
    week_num, day_num = get_experiment_timeline(data_dir)
    return f"Week {week_num} Day {day_num}"


def format_timeline_with_parentheses(data_dir: Path | str) -> str:
    """
    Get a formatted timeline string with parentheses for display purposes.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        str: Formatted timeline string like "(Week 2 Day 1)"
    """
    return f"({format_timeline_display(data_dir)})"


def get_experiment_start_date(data_dir: Path | str) -> datetime:
    """Get the experiment start date.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        datetime: The experiment start date
    """
    return _get_experiment_start_date(data_dir)


def _get_experiment_start_date(data_dir: Path | str) -> datetime:
    """Get the experiment start date from the trade log.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        datetime: The experiment start date
    """
    trade_log_path = Path(data_dir) / "llm_trade_log.csv"
    
    if not trade_log_path.exists():
        raise FileNotFoundError(f"Trade log not found: {trade_log_path}")
    
    try:
        df = pd.read_csv(trade_log_path)
        if df.empty or 'Date' not in df.columns:
            raise ValueError("Trade log is empty or missing Date column")
        
        # Filter out test data and get the first real trade
        real_trades = df[~df['Reason'].str.contains('TEST', case=False, na=False)]
        if real_trades.empty:
            raise ValueError("No real trades found in trade log")
        
        # Get the first trade date - robust timezone handling without warnings
        try:
            # 1) Strip common tz abbreviations (PDT, PST, MDT, etc.) that pandas warns about
            date_series = real_trades['Date'].astype(str)
            cleaned = date_series.str.replace(r"\s(ADT|AST|EDT|EST|CDT|CST|MDT|MST|PDT|PST)", "", regex=True)
            # 2) Parse to naive datetimes
            first_trade_date = pd.to_datetime(cleaned, errors='coerce').min()
            # 3) Localize to trading timezone for consistency
            if pd.notna(first_trade_date):
                from utils.timezone_utils import get_trading_timezone
                tz = get_trading_timezone()
                if first_trade_date.tzinfo is None:
                    first_trade_date = tz.localize(first_trade_date)
        except Exception as _tz_e:
            # Fallback: try default parse, suppressing warnings
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                first_trade_date = pd.to_datetime(real_trades['Date'], errors='coerce').min()
        
        # Convert to datetime object
        if pd.isna(first_trade_date):
            raise ValueError("Could not parse first trade date")
        
        return first_trade_date.to_pydatetime()
        
    except Exception as e:
        raise RuntimeError(f"Failed to read trade log from {trade_log_path}: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Timeline utilities for the trading bot experiment")
    parser.add_argument("--data-dir", type=str, default="trading_data/funds/Project Chimera", 
                       help="Data directory containing trade log")
    
    args = parser.parse_args()
    
    try:
        # Test the timeline calculation
        week, day = get_experiment_timeline(args.data_dir)
        total_day = get_total_experiment_day(args.data_dir)
        days_since = get_days_since_start(args.data_dir)
        
        print(f"Experiment started: {_get_experiment_start_date(args.data_dir).strftime('%Y-%m-%d')}")
        print(f"Days since start: {days_since}")
        print(f"Total experiment day: {total_day}")
        print(f"Current timeline: {format_timeline_display(args.data_dir)}")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
