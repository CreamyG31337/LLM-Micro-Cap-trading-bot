"""
Test script for database operations debug suite.

This script demonstrates how to use the database operations for testing and debugging.
"""

import sys
from pathlib import Path
sys.path.append('.')

from decimal import Decimal
from debug.database_operations import DatabaseOperations
from display.console_output import print_header, print_info, print_success

def test_database_operations():
    """Test the database operations suite."""
    print_header("🧪 TESTING DATABASE OPERATIONS SUITE")
    
    # Test fund name
    test_fund = "DEBUG_TEST"
    
    print_info(f"Using test fund: {test_fund}")
    
    # Create database operations instance
    db_ops = DatabaseOperations(test_fund)
    
    # Test 1: List current data
    print_info("\n=== Test 1: List Current Data ===")
    db_ops.list_fund_data()
    
    # Test 2: Create test scenario
    print_info("\n=== Test 2: Create Test Scenario ===")
    db_ops.create_test_scenario("basic_trading")
    
    # Test 3: Add individual trade
    print_info("\n=== Test 3: Add Individual Trade ===")
    db_ops.add_test_trade("TEST_STOCK", "BUY", Decimal("100"), Decimal("50.00"), "CAD", "Individual test trade")
    
    # Test 4: Add individual position
    print_info("\n=== Test 4: Add Individual Position ===")
    db_ops.add_test_position("TEST_POSITION", Decimal("50"), Decimal("25.00"), Decimal("30.00"), "CAD", "Test Position Company")
    
    # Test 5: Run consistency tests
    print_info("\n=== Test 5: Run Consistency Tests ===")
    db_ops.run_consistency_tests()
    
    # Test 6: List data after additions
    print_info("\n=== Test 6: List Data After Additions ===")
    db_ops.list_fund_data()
    
    print_success("✅ Database operations testing completed!")
    print_info("Note: Use --confirm flag to actually clear data if needed")

def demonstrate_usage():
    """Demonstrate usage examples."""
    print_header("📚 DATABASE OPERATIONS USAGE EXAMPLES")
    
    print_info("1. List fund data:")
    print_info("   python debug/database_operations.py --fund test --action list")
    
    print_info("\n2. Clear fund data (with confirmation):")
    print_info("   python debug/database_operations.py --fund test --action clear")
    
    print_info("\n3. Add a test trade:")
    print_info("   python debug/database_operations.py --fund test --action add-trade --ticker AAPL --action-type BUY --shares 100 --price 150.00 --currency USD")
    
    print_info("\n4. Add a test position:")
    print_info("   python debug/database_operations.py --fund test --action add-position --ticker GOOGL --shares 25 --price 2800.00 --currency USD")
    
    print_info("\n5. Create a test scenario:")
    print_info("   python debug/database_operations.py --fund test --action create-scenario --scenario basic_trading")
    
    print_info("\n6. Run consistency tests:")
    print_info("   python debug/database_operations.py --fund test --action test-consistency")
    
    print_info("\n7. Clear data without confirmation:")
    print_info("   python debug/database_operations.py --fund test --action clear --confirm")

def show_available_scenarios():
    """Show available test scenarios."""
    print_header("🎭 AVAILABLE TEST SCENARIOS")
    
    scenarios = {
        "basic_trading": {
            "description": "Basic trading scenario with AAPL and GOOGL",
            "trades": ["AAPL BUY 100 @ $150", "AAPL SELL 50 @ $160", "GOOGL BUY 25 @ $2800"],
            "positions": ["AAPL 50 shares", "GOOGL 25 shares"]
        },
        "fifo_testing": {
            "description": "FIFO testing scenario for P&L calculations",
            "trades": ["FIFO_TEST BUY 100 @ $50", "FIFO_TEST BUY 50 @ $60", "FIFO_TEST SELL 75 @ $70"],
            "positions": ["FIFO_TEST 75 shares remaining"]
        },
        "precision_testing": {
            "description": "Precision testing with decimal values",
            "trades": ["PRECISION BUY 150.5 @ $33.333"],
            "positions": ["PRECISION 150.5 shares @ $35.789"]
        }
    }
    
    for scenario_name, details in scenarios.items():
        print_info(f"\n📋 {scenario_name.upper()}:")
        print_info(f"   Description: {details['description']}")
        print_info(f"   Trades: {', '.join(details['trades'])}")
        print_info(f"   Positions: {', '.join(details['positions'])}")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test database operations suite")
    parser.add_argument("--demo", action="store_true", help="Run demonstration")
    parser.add_argument("--usage", action="store_true", help="Show usage examples")
    parser.add_argument("--scenarios", action="store_true", help="Show available scenarios")
    
    args = parser.parse_args()
    
    if args.demo:
        test_database_operations()
    elif args.usage:
        demonstrate_usage()
    elif args.scenarios:
        show_available_scenarios()
    else:
        print_info("Use --demo, --usage, or --scenarios to see different options")
        print_info("Run 'python debug/test_database_operations.py --help' for more information")

if __name__ == "__main__":
    main()
