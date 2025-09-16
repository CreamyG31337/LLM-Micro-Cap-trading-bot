#!/usr/bin/env python3
"""
Experiment Configuration
========================

This module provides backward compatibility imports for timeline functions.
All timeline functionality has been moved to utils.timeline_utils for better organization.

The experiment timeline is calculated from the actual first trade date.
"""

# Import all timeline functions from the centralized location
from utils.timeline_utils import (
    get_experiment_timeline,
    get_experiment_start_date,
    get_days_since_start,
    get_total_experiment_day,
    format_timeline_display,
    format_timeline_with_parentheses
)

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