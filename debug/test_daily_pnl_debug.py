#!/usr/bin/env python3
"""
Debug script to test the 1-Day P&L calculation issue.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from financial.pnl_calculator import calculate_daily_pnl_from_snapshots

def test_daily_pnl_calculation():
    """Test the daily P&L calculation with mock data."""
    print("🔍 Testing Daily P&L Calculation")
    print("=" * 50)
    
    # Create a mock position
    class MockPosition:
        def __init__(self, ticker, current_price, shares, avg_price):
            self.ticker = ticker
            self.current_price = current_price
            self.shares = shares
            self.avg_price = avg_price
    
    # Test with DOL.TO data from the debug output
    dol_position = MockPosition(
        ticker='DOL.TO',
        current_price=Decimal('261.67959731891995'),
        shares=Decimal('17.0'),
        avg_price=Decimal('193.43')
    )
    
    print(f"Testing DOL.TO:")
    print(f"  Current price: {dol_position.current_price}")
    print(f"  Shares: {dol_position.shares}")
    print(f"  Avg price: {dol_position.avg_price}")
    
    # Test with empty snapshots (should return $0.00)
    print(f"\n1. Testing with empty snapshots:")
    result = calculate_daily_pnl_from_snapshots(dol_position, [])
    print(f"  Result: {result}")
    
    # Test with None snapshots (should return $0.00)
    print(f"\n2. Testing with None snapshots:")
    result = calculate_daily_pnl_from_snapshots(dol_position, None)
    print(f"  Result: {result}")
    
    # Test with mock snapshots
    print(f"\n3. Testing with mock snapshots:")
    
    # Create mock snapshots
    class MockSnapshot:
        def __init__(self, timestamp, positions):
            self.timestamp = timestamp
            self.positions = positions
    
    # Mock previous day snapshot with DOL.TO
    prev_position = MockPosition(
        ticker='DOL.TO',
        current_price=Decimal('250.00'),  # Previous day price
        shares=Decimal('17.0'),
        avg_price=Decimal('193.43')
    )
    
    mock_snapshots = [
        MockSnapshot('2025-09-20', [prev_position]),  # Previous day
        MockSnapshot('2025-09-21', [dol_position])    # Current day
    ]
    
    result = calculate_daily_pnl_from_snapshots(dol_position, mock_snapshots)
    print(f"  Result: {result}")
    
    # Calculate expected result
    price_change = dol_position.current_price - prev_position.current_price
    expected_pnl = price_change * dol_position.shares
    print(f"  Expected: ${expected_pnl:.2f} (price change: ${price_change:.2f})")

if __name__ == "__main__":
    test_daily_pnl_calculation()
