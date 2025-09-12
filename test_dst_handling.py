#!/usr/bin/env python3
"""
Test script to verify DST (Daylight Saving Time) handling works correctly.

This script tests the timezone detection logic to ensure it properly switches
between PST and PDT based on the current date and DST status.
"""

from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from market_config import _is_dst, _get_current_timezone_name, _get_current_timezone_offset, get_timezone_name, get_timezone_offset
from utils.timezone_utils import format_timestamp_for_csv, parse_csv_timestamp

def test_dst_detection():
    """Test DST detection for various dates."""
    print("=== DST Detection Tests ===\n")

    # Test dates in different seasons
    test_dates = [
        # Winter (should be PST)
        datetime(2025, 1, 15, tzinfo=timezone.utc),  # January - Standard Time
        datetime(2025, 2, 10, tzinfo=timezone.utc),  # February - Standard Time

        # Spring (transition period)
        datetime(2025, 3, 8, tzinfo=timezone.utc),   # Before DST starts
        datetime(2025, 3, 15, tzinfo=timezone.utc),  # After DST starts (second Sunday in March)

        # Summer (should be PDT)
        datetime(2025, 6, 15, tzinfo=timezone.utc),  # June - Daylight Time
        datetime(2025, 7, 20, tzinfo=timezone.utc),  # July - Daylight Time
        datetime(2025, 8, 10, tzinfo=timezone.utc),  # August - Daylight Time

        # Fall (transition period)
        datetime(2025, 11, 1, tzinfo=timezone.utc),  # Before DST ends
        datetime(2025, 11, 8, tzinfo=timezone.utc),  # After DST ends (first Sunday in November)

        # Winter again
        datetime(2025, 12, 15, tzinfo=timezone.utc), # December - Standard Time
    ]

    for test_date in test_dates:
        is_dst = _is_dst(test_date)
        expected_tz = "PDT" if is_dst else "PST"
        expected_offset = -7 if is_dst else -8

        print(f"Date: {test_date.strftime('%Y-%m-%d')} - Is DST: {is_dst} - Timezone: {expected_tz} (UTC{expected_offset:+d})")

def test_current_timezone():
    """Test current timezone detection."""
    print("\n=== Current Timezone Status ===\n")

    now = datetime.now(timezone.utc)
    tz_name = get_timezone_name()
    tz_offset = get_timezone_offset()
    is_dst = _is_dst(now)

    print(f"Current UTC time: {now}")
    print(f"Is currently DST: {is_dst}")
    print(f"Current timezone name: {tz_name}")
    print(f"Current timezone offset: UTC{tz_offset:+d}")

def test_timestamp_formatting():
    """Test timestamp formatting with DST awareness."""
    print("\n=== Timestamp Formatting Tests ===\n")

    # Test different dates to see timezone formatting
    test_dates = [
        datetime(2025, 1, 15, 14, 30, 0),  # Winter - should be PST
        datetime(2025, 6, 15, 14, 30, 0),  # Summer - should be PDT
    ]

    for dt in test_dates:
        formatted = format_timestamp_for_csv(dt)
        print(f"Input: {dt} -> Formatted: {formatted}")

def test_parsing_consistency():
    """Test that parsing and formatting are consistent."""
    print("\n=== Parsing Consistency Tests ===\n")

    test_timestamps = [
        "2025-01-15 14:30:00 PST",  # Standard time
        "2025-06-15 14:30:00 PDT",  # Daylight time
        "2025-09-12 13:10:31 PDT",  # Current format from CSV
    ]

    for timestamp_str in test_timestamps:
        print(f"Original: {timestamp_str}")

        # Parse the timestamp
        parsed = parse_csv_timestamp(timestamp_str)
        print(f"  Parsed: {parsed}")

        # Format it back
        if parsed:
            reformatted = format_timestamp_for_csv(parsed.to_pydatetime())
            print(f"  Reformatted: {reformatted}")

            # Check if they're equivalent
            is_consistent = timestamp_str.split()[0] == reformatted.split()[0]  # Compare date part
            print(f"  Consistent: {is_consistent}")
        print()

def main():
    """Main test function."""
    print("=== DST Handling Test Suite ===\n")

    test_dst_detection()
    test_current_timezone()
    test_timestamp_formatting()
    test_parsing_consistency()

    print("\n=== DST Handling Tests Complete ===")

if __name__ == "__main__":
    main()
