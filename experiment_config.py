#!/usr/bin/env python3
"""
Experiment Configuration
========================

This module calculates the actual experiment start date from the first trade
in the CSV files and provides functions to calculate the current week and day.

The experiment timeline is calculated from the actual first trade date.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd

# Import timezone parsing function from trading_script
try:
    from trading_script import parse_csv_timestamp
    _HAS_TIMEZONE_PARSING = True
except ImportError:
    _HAS_TIMEZONE_PARSING = False

def _get_experiment_start_date() -> datetime:
    """
    Calculate the experiment start date from the first trade in the trade log CSV.
    
    Returns:
        datetime: The date of the first trade
    """
    # Try production trade log first, then test data
    trade_log_paths = [
        Path("my trading/llm_trade_log.csv"),
        Path("test_data/llm_trade_log.csv")
    ]
    
    for trade_log_path in trade_log_paths:
        if trade_log_path.exists():
            try:
                df = pd.read_csv(trade_log_path)
                if not df.empty and 'Date' in df.columns:
                    # Filter out test data (look for real trades, not test data)
                    real_trades = df[~df['Reason'].str.contains('TEST', case=False, na=False)]
                    if not real_trades.empty:
                        if _HAS_TIMEZONE_PARSING:
                            first_trade_date = parse_csv_timestamp(real_trades['Date'].iloc[0])
                        else:
                            first_trade_date = pd.to_datetime(real_trades['Date'].iloc[0])
                        return first_trade_date.to_pydatetime()
            except Exception:
                continue
    
    # Ultimate fallback: return current date minus 1 day
    return datetime.now() - timedelta(days=1)

# Calculate the actual experiment start date from CSV data
EXPERIMENT_START_DATE = _get_experiment_start_date()

def get_experiment_timeline() -> Tuple[int, int]:
    """
    Calculate the current week and day of the experiment.
    
    Returns:
        Tuple[int, int]: (week_number, day_number)
    """
    today = datetime.now()
    
    # Handle timezone-aware vs timezone-naive datetime comparison
    if EXPERIMENT_START_DATE.tzinfo is not None:
        # Start date is timezone-aware, make today timezone-aware too
        from trading_script import get_trading_timezone
        tz = get_trading_timezone()
        today = today.replace(tzinfo=tz)
    elif today.tzinfo is not None:
        # Today is timezone-aware, make start date timezone-aware too
        today = today.replace(tzinfo=None)
    
    days_since_start = (today - EXPERIMENT_START_DATE).days
    
    # Ensure we don't go below week 1, day 1
    if days_since_start < 0:
        return 1, 1
    
    # Add 1 to make the first day of trading Day 1, not Day 0
    week_num = max(1, days_since_start // 7 + 1)
    day_num = days_since_start + 1  # First trading day is Day 1
    
    return week_num, day_num

def get_experiment_start_date() -> datetime:
    """Get the experiment start date."""
    return EXPERIMENT_START_DATE

def get_days_since_start() -> int:
    """Get the number of days since the experiment started."""
    today = datetime.now()
    
    # Handle timezone-aware vs timezone-naive datetime comparison
    if EXPERIMENT_START_DATE.tzinfo is not None:
        # Start date is timezone-aware, make today timezone-aware too
        from trading_script import get_trading_timezone
        tz = get_trading_timezone()
        today = today.replace(tzinfo=tz)
    elif today.tzinfo is not None:
        # Today is timezone-aware, make start date timezone-aware too
        today = today.replace(tzinfo=None)
    
    return max(0, (today - EXPERIMENT_START_DATE).days)

def update_experiment_start_date(new_date: datetime) -> None:
    """Update the experiment start date (for configuration changes)."""
    global EXPERIMENT_START_DATE
    EXPERIMENT_START_DATE = new_date

if __name__ == "__main__":
    # Test the timeline calculation
    week, day = get_experiment_timeline()
    days_since = get_days_since_start()
    start_date = get_experiment_start_date()
    
    print(f"Experiment started: {start_date.strftime('%Y-%m-%d')}")
    print(f"Days since start: {days_since}")
    print(f"Current timeline: Week {week}, Day {day}")
