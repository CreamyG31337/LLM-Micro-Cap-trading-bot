#!/usr/bin/env python3
"""
Debug script to test GLO.TO daily P&L calculation issue.

This script will:
1. Load the portfolio snapshots from the TEST fund
2. Test the daily P&L calculation for GLO.TO
3. Show detailed debug information to identify why it's showing $0.00
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import datetime
import logging

# Configure logging to show debug messages
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Import the function we want to test
from financial.pnl_calculator import calculate_daily_pnl_from_snapshots

# Mock position class to simulate GLO.TO position
class MockPosition:
    def __init__(self, ticker, current_price, shares, avg_price, company, currency='CAD'):
        self.ticker = ticker
        self.current_price = Decimal(str(current_price))
        self.shares = Decimal(str(shares))
        self.avg_price = Decimal(str(avg_price))
        self.company = company
        self.currency = currency

# Mock portfolio snapshot class
class MockPortfolioSnapshot:
    def __init__(self, timestamp, positions):
        self.timestamp = timestamp
        self.positions = positions

def test_glo_daily_pnl():
    """Test the daily P&L calculation for GLO.TO with real data."""
    
    print("🔍 Testing GLO.TO Daily P&L Calculation")
    print("=" * 60)
    
    # Create GLO.TO positions with real data from your CSV
    # 2025-09-22: $0.73
    glo_sep22 = MockPosition(
        ticker="GLO.TO",
        current_price=0.73,
        shares=735.2941,
        avg_price=0.68,
        company="Global Atomic Corporation"
    )
    
    # 2025-09-23: $0.71
    glo_sep23 = MockPosition(
        ticker="GLO.TO", 
        current_price=0.71,
        shares=735.2941,
        avg_price=0.68,
        company="Global Atomic Corporation"
    )
    
    print(f"GLO.TO position data:")
    print(f"  Sep 22 price: ${glo_sep22.current_price}")
    print(f"  Sep 23 price: ${glo_sep23.current_price}")
    print(f"  Shares: {glo_sep23.shares}")
    print(f"  Expected daily P&L: ${(glo_sep23.current_price - glo_sep22.current_price) * glo_sep23.shares:.2f}")
    print()
    
    # Create portfolio snapshots
    snapshots = [
        MockPortfolioSnapshot(
            timestamp=datetime(2025, 9, 19, 13, 0, 0),
            positions=[]  # Earlier snapshot without GLO.TO
        ),
        MockPortfolioSnapshot(
            timestamp=datetime(2025, 9, 22, 13, 0, 0),
            positions=[glo_sep22]  # Sep 22 snapshot
        ),
        MockPortfolioSnapshot(
            timestamp=datetime(2025, 9, 23, 13, 0, 0), 
            positions=[glo_sep23]  # Sep 23 snapshot (current)
        )
    ]
    
    print(f"Portfolio snapshots:")
    for i, snapshot in enumerate(snapshots):
        print(f"  Snapshot {i+1}: {snapshot.timestamp}, {len(snapshot.positions)} positions")
    print()
    
    # Test the daily P&L calculation
    print("📊 Testing daily P&L calculation...")
    result = calculate_daily_pnl_from_snapshots(glo_sep23, snapshots)
    
    print(f"✅ Result: {result}")
    print()
    
    # Expected calculation
    expected_price_change = glo_sep23.current_price - glo_sep22.current_price
    expected_pnl = expected_price_change * glo_sep23.shares
    print(f"Expected calculation:")
    print(f"  Price change: ${glo_sep23.current_price} - ${glo_sep22.current_price} = ${expected_price_change}")
    print(f"  Daily P&L: ${expected_price_change} × {glo_sep23.shares} = ${expected_pnl:.2f}")
    print(f"  Expected result: ${expected_pnl:.2f}")
    print()
    
    # Check if result matches expectation
    if result == "$0.00":
        print("❌ ISSUE FOUND: Function returned $0.00 instead of expected value")
        print("   This confirms the bug you're experiencing")
        
        # Test with minimal snapshots to see if it's a snapshot issue
        print("\n🔍 Testing with minimal snapshots...")
        minimal_snapshots = [
            MockPortfolioSnapshot(
                timestamp=datetime(2025, 9, 22, 13, 0, 0),
                positions=[glo_sep22]
            ),
            MockPortfolioSnapshot(
                timestamp=datetime(2025, 9, 23, 13, 0, 0),
                positions=[glo_sep23]
            )
        ]
        
        minimal_result = calculate_daily_pnl_from_snapshots(glo_sep23, minimal_snapshots)
        print(f"Minimal snapshots result: {minimal_result}")
        
    else:
        print("✅ SUCCESS: Function returned expected value")

def test_edge_cases():
    """Test edge cases that might cause $0.00 to be returned."""
    
    print("\n🔍 Testing Edge Cases")
    print("=" * 60)
    
    # Test 1: Empty snapshots
    print("Test 1: Empty snapshots")
    glo_position = MockPosition("GLO.TO", 0.71, 735.2941, 0.68, "Global Atomic Corporation")
    result = calculate_daily_pnl_from_snapshots(glo_position, [])
    print(f"  Result: {result} (expected: $0.00)")
    
    # Test 2: None snapshots  
    print("Test 2: None snapshots")
    result = calculate_daily_pnl_from_snapshots(glo_position, None)
    print(f"  Result: {result} (expected: $0.00)")
    
    # Test 3: Snapshots without the ticker
    print("Test 3: Snapshots without GLO.TO")
    other_position = MockPosition("AAPL", 150.00, 100, 140.00, "Apple Inc")
    snapshots_no_glo = [
        MockPortfolioSnapshot(
            timestamp=datetime(2025, 9, 22, 13, 0, 0),
            positions=[other_position]
        ),
        MockPortfolioSnapshot(
            timestamp=datetime(2025, 9, 23, 13, 0, 0), 
            positions=[other_position]
        )
    ]
    result = calculate_daily_pnl_from_snapshots(glo_position, snapshots_no_glo)
    print(f"  Result: {result} (expected: $0.00)")

def main():
    """Main function to run all tests."""
    test_glo_daily_pnl()
    test_edge_cases()
    
    print("\n💡 Next Steps:")
    print("1. If the function returns $0.00, check the logic in calculate_daily_pnl_from_snapshots")
    print("2. Look for conditions that cause early return of '$0.00'") 
    print("3. Check if price comparison logic has precision issues")
    print("4. Verify that the function finds the previous day's price correctly")

if __name__ == "__main__":
    main()