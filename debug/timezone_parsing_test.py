#!/usr/bin/env python3
"""
Test that the timezone warning is fixed
"""
import pandas as pd
import os
import warnings

def test_timezone_parsing():
    """Test that timezone parsing doesn't generate warnings"""
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Test data with PDT timezone
        test_data = {
            'Date': ['2025-09-08 06:30:00 PDT', '2025-09-09 06:30:00 PDT'],
            'Ticker': ['TEST1', 'TEST2'],
            'Cost Basis': [100.0, 200.0],
            'Total Value': [105.0, 195.0],
            'Action': ['BUY', 'HOLD']
        }

        df = pd.DataFrame(test_data)

        # Test the parse_csv_timestamp function (simulate what our fixed code does)
        from trading_script import parse_csv_timestamp

        # Apply parse_csv_timestamp to the Date column
        df['Date'] = df['Date'].apply(parse_csv_timestamp)

        # Check for FutureWarnings
        future_warnings = [warning for warning in w if issubclass(warning.category, FutureWarning)]

        if future_warnings:
            print("❌ FutureWarnings still present:")
            for warning in future_warnings:
                print(f"  {warning.message}")
            return False
        else:
            print("✅ No FutureWarnings detected")
            print(f"✅ Parsed dates: {df['Date'].tolist()}")
            return True

if __name__ == "__main__":
    success = test_timezone_parsing()
    result = f"Test {'PASSED' if success else 'FAILED'}"
    print(result)

    # Also write to file for verification
    with open("debug/timezone_parsing_test_result.txt", "w") as f:
        f.write(result + "\n")
        if success:
            f.write("✅ Timezone FutureWarning has been fixed!\n")
