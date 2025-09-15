#!/usr/bin/env python3
"""
Experiment Configuration
========================

This module calculates the actual experiment start date from the first trade
in the CSV files and provides functions to calculate the current week and day.

The experiment timeline is calculated from the actual first trade date.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd

# Import timezone parsing function
from utils.timezone_utils import parse_csv_timestamp

def _get_experiment_start_date(data_dir: Path | str) -> datetime:
    """
    Calculate the experiment start date from the first trade in the trade log CSV.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        datetime: The date of the first trade
    """
    trade_log_path = Path(data_dir) / "llm_trade_log.csv"
    
    if trade_log_path.exists():
        try:
            df = pd.read_csv(trade_log_path)
            if not df.empty and 'Date' in df.columns:
                # Filter out test data (look for real trades, not test data)
                real_trades = df[~df['Reason'].str.contains('TEST', case=False, na=False)]
                if not real_trades.empty:
                    first_trade_date = parse_csv_timestamp(real_trades['Date'].iloc[0])
                    return first_trade_date.to_pydatetime()
        except Exception as e:
            raise RuntimeError(f"Failed to read trade log from {trade_log_path}: {e}")
    
    raise FileNotFoundError(f"Trade log not found: {trade_log_path}")

def get_experiment_timeline(data_dir: Path | str) -> Tuple[int, int]:
    """
    Calculate the current week and day of the experiment.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        Tuple[int, int]: (week_number, day_number)
    """
    experiment_start_date = _get_experiment_start_date(data_dir)
    today = datetime.now()
    
    # Convert both to naive datetimes for simple comparison
    if experiment_start_date.tzinfo is not None:
        experiment_start_date = experiment_start_date.replace(tzinfo=None)
    if today.tzinfo is not None:
        today = today.replace(tzinfo=None)
    
    days_since_start = (today - experiment_start_date).days
    
    # Ensure we don't go below week 1, day 1
    if days_since_start < 0:
        return 1, 1
    
    # Add 1 to make the first day of trading Day 1, not Day 0
    week_num = max(1, days_since_start // 7 + 1)
    day_num = days_since_start + 1  # First trading day is Day 1
    
    return week_num, day_num

def get_experiment_start_date(data_dir: Path | str) -> datetime:
    """Get the experiment start date.
    
    Args:
        data_dir: Directory containing the trade log CSV file
    
    Returns:
        datetime: The experiment start date
    """
    return _get_experiment_start_date(data_dir)

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

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Experiment configuration and timeline calculation")
    parser.add_argument("--data-dir", help="Data directory containing trade log (required)", required=True)
    
    args = parser.parse_args()
    
    # Test the timeline calculation
    week, day = get_experiment_timeline(args.data_dir)
    days_since = get_days_since_start(args.data_dir)
    start_date = get_experiment_start_date(args.data_dir)
    
    print(f"Experiment started: {start_date.strftime('%Y-%m-%d')}")
    print(f"Days since start: {days_since}")
    print(f"Current timeline: Week {week}, Day {day}")
