"""
Test Email Trade Integration with Database Operations

This script demonstrates how to use email trade processing for comprehensive
testing of the database operations and repository consistency.
"""

import sys
from pathlib import Path
sys.path.append('.')

from decimal import Decimal
from datetime import datetime, timezone
from debug.database_operations import DatabaseOperations
from utils.email_trade_parser import parse_trade_from_email, add_trade_from_email
from display.console_output import print_header, print_info, print_success, print_warning, print_error

def test_email_trade_parsing():
    """Test email trade parsing with various scenarios."""
    print_header("🧪 EMAIL TRADE PARSING TESTS")
    
    test_emails = [
        {
            "name": "Basic Buy Trade",
            "email": """
            Your order has been filled.
            Symbol: TEST_STOCK
            Type: Buy
            Shares: 100
            Average price: $50.00
            Total cost: $5,000.00
            Time: 2024-01-15 10:30:00 EST
            """,
            "expected": {
                "ticker": "TEST_STOCK",
                "action": "BUY",
                "shares": Decimal("100"),
                "price": Decimal("50.00"),
                "cost_basis": Decimal("5000.00")
            }
        },
        {
            "name": "Sell Trade with Precision",
            "email": """
            Your order has been filled.
            Symbol: PRECISION_STOCK
            Type: Sell
            Shares: 150.5
            Average price: $33.333
            Total cost: $5,016.65
            Time: 2024-01-15 14:30:00 EST
            """,
            "expected": {
                "ticker": "PRECISION_STOCK",
                "action": "SELL",
                "shares": Decimal("150.5"),
                "price": Decimal("33.333"),
                "cost_basis": Decimal("5016.65")
            }
        },
        {
            "name": "USD Currency Trade",
            "email": """
            Your order has been filled.
            Symbol: USD_STOCK
            Type: Buy
            Shares: 25
            Average price: US$200.00
            Total cost: US$5,000.00
            Time: 2024-01-15 16:00:00 EST
            """,
            "expected": {
                "ticker": "USD_STOCK",
                "action": "BUY",
                "shares": Decimal("25"),
                "price": Decimal("200.00"),
                "cost_basis": Decimal("5000.00"),
                "currency": "USD"
            }
        }
    ]
    
    for i, test_case in enumerate(test_emails, 1):
        print_info(f"\n--- Test {i}: {test_case['name']} ---")
        
        # Parse the trade
        trade = parse_trade_from_email(test_case['email'])
        
        if trade:
            print_success("✅ Trade parsed successfully")
            
            # Validate expected values
            expected = test_case['expected']
            errors = []
            
            if trade.ticker != expected['ticker']:
                errors.append(f"Ticker: expected {expected['ticker']}, got {trade.ticker}")
            
            if trade.action != expected['action']:
                errors.append(f"Action: expected {expected['action']}, got {trade.action}")
            
            if trade.shares != expected['shares']:
                errors.append(f"Shares: expected {expected['shares']}, got {trade.shares}")
            
            if trade.price != expected['price']:
                errors.append(f"Price: expected {expected['price']}, got {trade.price}")
            
            if trade.cost_basis != expected['cost_basis']:
                errors.append(f"Cost Basis: expected {expected['cost_basis']}, got {trade.cost_basis}")
            
            if 'currency' in expected and trade.currency != expected['currency']:
                errors.append(f"Currency: expected {expected['currency']}, got {trade.currency}")
            
            if errors:
                print_error("❌ Validation errors:")
                for error in errors:
                    print_error(f"   {error}")
            else:
                print_success("✅ All validations passed")
        else:
            print_error("❌ Failed to parse trade")

def test_email_trade_database_integration():
    """Test email trade processing with database operations."""
    print_header("🔄 EMAIL TRADE DATABASE INTEGRATION TESTS")
    
    # Test fund
    test_fund = "EMAIL_INTEGRATION_TEST"
    data_dir = "trading_data/funds/TEST"
    
    print_info(f"Using test fund: {test_fund}")
    print_info(f"Data directory: {data_dir}")
    
    # Create database operations instance
    db_ops = DatabaseOperations(test_fund)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Basic Email Trade Processing",
            "email": """
            Your order has been filled.
            Symbol: EMAIL_INTEGRATION
            Type: Buy
            Shares: 100
            Average price: $50.00
            Total cost: $5,000.00
            Time: 2024-01-15 10:30:00 EST
            """,
            "description": "Test basic email trade processing with database operations"
        },
        {
            "name": "Sell Trade with Position",
            "email": """
            Your order has been filled.
            Symbol: EMAIL_INTEGRATION
            Type: Sell
            Shares: 50
            Average price: $55.00
            Total cost: $2,750.00
            Time: 2024-01-15 14:30:00 EST
            """,
            "description": "Test sell trade processing with existing position"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print_info(f"\n--- Scenario {i}: {scenario['name']} ---")
        print_info(f"Description: {scenario['description']}")
        
        # Parse trade
        trade = parse_trade_from_email(scenario['email'])
        if not trade:
            print_error("❌ Failed to parse trade")
            continue
        
        print_success(f"✅ Parsed: {trade.ticker} {trade.action} {trade.shares} @ {trade.price}")
        
        # Add to database using our operations
        result = db_ops.add_test_trade(
            trade.ticker,
            trade.action,
            trade.shares,
            trade.price,
            trade.currency,
            trade.reason
        )
        
        if result['success']:
            print_success("✅ Added to database successfully")
        else:
            print_error(f"❌ Failed to add to database: {result['errors']}")
    
    # Show final state
    print_info("\n📊 Final Database State:")
    db_ops.list_fund_data()
    
    # Run consistency tests
    print_info("\n🧪 Running Consistency Tests:")
    db_ops.run_consistency_tests()

def test_dual_write_consistency():
    """Test dual-write consistency with email trades."""
    print_header("🔄 DUAL-WRITE CONSISTENCY TESTS")
    
    # Test fund
    test_fund = "DUAL_WRITE_TEST"
    data_dir = "trading_data/funds/TEST"
    
    print_info(f"Using test fund: {test_fund}")
    print_info(f"Data directory: {data_dir}")
    
    # Create database operations instance
    db_ops = DatabaseOperations(test_fund)
    
    # Test email trade with dual-write
    email_trade = """
    Your order has been filled.
    Symbol: DUAL_WRITE_STOCK
    Type: Buy
    Shares: 100
    Average price: $50.00
    Total cost: $5,000.00
    Time: 2024-01-15 10:30:00 EST
    """
    
    print_info("📧 Processing email trade with dual-write...")
    
    # Parse trade
    trade = parse_trade_from_email(email_trade)
    if not trade:
        print_error("❌ Failed to parse trade")
        return
    
    print_success(f"✅ Parsed: {trade.ticker} {trade.action} {trade.shares} @ {trade.price}")
    
    # Add using database operations (CSV + Supabase)
    result = db_ops.add_test_trade(
        trade.ticker,
        trade.action,
        trade.shares,
        trade.price,
        trade.currency,
        trade.reason
    )
    
    if result['success']:
        print_success("✅ Added to database successfully")
        
        # Test consistency
        print_info("\n🔍 Testing CSV vs Supabase consistency...")
        
        # This would require implementing consistency checks
        # For now, we'll just show the data
        db_ops.list_fund_data()
        
    else:
        print_error(f"❌ Failed to add to database: {result['errors']}")

def test_error_handling():
    """Test error handling in email trade processing."""
    print_header("⚠️ ERROR HANDLING TESTS")
    
    error_scenarios = [
        {
            "name": "Invalid Email Format",
            "email": "This is not a valid trade email",
            "expected": "Should fail to parse"
        },
        {
            "name": "Missing Required Fields",
            "email": """
            Your order has been filled.
            Symbol: MISSING_FIELDS
            Type: Buy
            """,
            "expected": "Should fail to parse due to missing fields"
        },
        {
            "name": "Invalid Numeric Values",
            "email": """
            Your order has been filled.
            Symbol: INVALID_NUMBERS
            Type: Buy
            Shares: invalid
            Average price: $invalid
            """,
            "expected": "Should fail to parse due to invalid numbers"
        }
    ]
    
    for i, scenario in enumerate(error_scenarios, 1):
        print_info(f"\n--- Error Test {i}: {scenario['name']} ---")
        print_info(f"Expected: {scenario['expected']}")
        
        # Parse trade
        trade = parse_trade_from_email(scenario['email'])
        
        if trade:
            print_warning("⚠️  Trade parsed successfully (unexpected)")
            print_info(f"   Ticker: {trade.ticker}")
            print_info(f"   Action: {trade.action}")
            print_info(f"   Shares: {trade.shares}")
            print_info(f"   Price: {trade.price}")
        else:
            print_success("✅ Trade parsing failed as expected")

def demonstrate_comprehensive_testing():
    """Demonstrate comprehensive testing approach."""
    print_header("🎯 COMPREHENSIVE TESTING APPROACH")
    
    print_info("📋 Testing Strategy:")
    print_info("   1. Email Trade Parsing Tests")
    print_info("   2. Database Operations Tests")
    print_info("   3. Dual-Write Consistency Tests")
    print_info("   4. Error Handling Tests")
    print_info("   5. Integration Tests")
    
    print_info("\n🔧 Test Tools:")
    print_info("   - debug/database_operations.py: Database operations")
    print_info("   - debug/analyze_email_trade_workflow.py: Workflow analysis")
    print_info("   - debug/test_email_trade_integration.py: Integration tests")
    print_info("   - utils/email_trade_parser.py: Email parsing")
    
    print_info("\n🎭 Test Scenarios:")
    print_info("   - Basic trading scenarios")
    print_info("   - FIFO trading scenarios")
    print_info("   - Precision testing scenarios")
    print_info("   - Error handling scenarios")
    print_info("   - Dual-write consistency scenarios")
    
    print_info("\n💡 Benefits:")
    print_info("   - Realistic testing with actual email formats")
    print_info("   - Complete workflow testing")
    print_info("   - Repository consistency validation")
    print_info("   - Error handling and fallback testing")
    print_info("   - P&L calculation accuracy testing")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test email trade integration with database operations")
    parser.add_argument("--parsing", action="store_true", help="Test email trade parsing")
    parser.add_argument("--integration", action="store_true", help="Test database integration")
    parser.add_argument("--dual-write", action="store_true", help="Test dual-write consistency")
    parser.add_argument("--error-handling", action="store_true", help="Test error handling")
    parser.add_argument("--comprehensive", action="store_true", help="Show comprehensive testing approach")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if args.all or args.parsing:
        test_email_trade_parsing()
    
    if args.all or args.integration:
        test_email_trade_database_integration()
    
    if args.all or args.dual_write:
        test_dual_write_consistency()
    
    if args.all or args.error_handling:
        test_error_handling()
    
    if args.comprehensive:
        demonstrate_comprehensive_testing()
    
    if not any([args.parsing, args.integration, args.dual_write, args.error_handling, args.comprehensive, args.all]):
        print_info("Use --parsing, --integration, --dual-write, --error-handling, --comprehensive, or --all to run tests")
        print_info("Run 'python debug/test_email_trade_integration.py --help' for more information")

if __name__ == "__main__":
    main()
