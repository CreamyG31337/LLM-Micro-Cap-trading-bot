"""
Analysis of Email Trade Processing Workflow

This script analyzes how email trades are processed and what we can learn
from that workflow for our database operations and testing.
"""

import sys
from pathlib import Path
sys.path.append('.')

from decimal import Decimal
from datetime import datetime, timezone
from debug.database_operations import DatabaseOperations
from utils.email_trade_parser import parse_trade_from_email, add_trade_from_email
from display.console_output import print_header, print_info, print_success, print_warning

def analyze_email_trade_workflow():
    """Analyze the email trade processing workflow."""
    print_header("📧 EMAIL TRADE WORKFLOW ANALYSIS")
    
    # Sample email text (simulating a real trade notification)
    sample_email = """
    Your order has been filled.
    
    Symbol: AAPL
    Type: Buy
    Shares: 100
    Average price: $150.00
    Total cost: $15,000.00
    Time: 2024-01-15 10:30:00 EST
    Account: RRSP
    """
    
    print_info("📋 Sample Email Trade Notification:")
    print_info(sample_email.strip())
    
    # Parse the trade
    print_info("\n🔍 Parsing Trade from Email...")
    trade = parse_trade_from_email(sample_email)
    
    if trade:
        print_success("✅ Trade parsed successfully!")
        print_info(f"   Ticker: {trade.ticker}")
        print_info(f"   Action: {trade.action}")
        print_info(f"   Shares: {trade.shares}")
        print_info(f"   Price: {trade.price}")
        print_info(f"   Cost Basis: {trade.cost_basis}")
        print_info(f"   Currency: {trade.currency}")
        print_info(f"   Timestamp: {trade.timestamp}")
        print_info(f"   Reason: {trade.reason}")
    else:
        print_warning("❌ Failed to parse trade from email")
        return
    
    # Analyze the workflow
    print_info("\n🔍 Email Trade Processing Workflow Analysis:")
    
    print_info("\n1. 📧 EMAIL PARSING:")
    print_info("   - Uses regex patterns to extract trade data")
    print_info("   - Handles multiple email formats from different brokers")
    print_info("   - Validates required fields (ticker, shares, price, action)")
    print_info("   - Calculates cost basis if not provided")
    print_info("   - Normalizes ticker symbols and actions")
    
    print_info("\n2. 🔄 REPOSITORY SELECTION:")
    print_info("   - Uses RepositoryFactory.create_dual_write_repository() if fund_name provided")
    print_info("   - Falls back to CSVRepository if dual-write fails")
    print_info("   - Supports both CSV-only and CSV+Supabase modes")
    
    print_info("\n3. 🛡️ DUPLICATE DETECTION:")
    print_info("   - Checks for exact duplicates using is_duplicate_trade()")
    print_info("   - Compares ticker, action, shares, price, and timestamp")
    print_info("   - Uses 5-minute time window for duplicate detection")
    print_info("   - Skips insertion if duplicate found")
    
    print_info("\n4. 💰 SELL TRADE CORRECTION:")
    print_info("   - For sell trades, gets current position to calculate correct cost basis")
    print_info("   - Calculates actual cost basis from existing position")
    print_info("   - Updates trade with correct P&L calculation")
    print_info("   - Handles cases where insufficient position exists")
    
    print_info("\n5. 💾 TRADE PERSISTENCE:")
    print_info("   - Saves trade to repository using repository.save_trade()")
    print_info("   - Works with both CSV and Supabase repositories")
    print_info("   - Maintains data consistency across storage systems")
    
    print_info("\n6. 📊 PORTFOLIO UPDATES:")
    print_info("   - Uses TradeProcessor for position updates")
    print_info("   - Calls _update_position_after_buy() for buy trades")
    print_info("   - Calls _update_position_after_sell() for sell trades")
    print_info("   - Handles multiple trades per day correctly")
    
    print_info("\n7. 🎯 KEY INSIGHTS FOR DATABASE OPERATIONS:")
    print_info("   - Repository pattern allows seamless switching between CSV and Supabase")
    print_info("   - Dual-write mode provides redundancy and migration path")
    print_info("   - Duplicate detection prevents data corruption")
    print_info("   - Sell trade correction ensures accurate P&L calculations")
    print_info("   - TradeProcessor handles complex position updates")
    print_info("   - Error handling with fallback to CSV-only mode")

def demonstrate_email_trade_processing():
    """Demonstrate how to use email trade processing for testing."""
    print_header("🧪 EMAIL TRADE PROCESSING FOR TESTING")
    
    # Test fund
    test_fund = "EMAIL_TEST"
    data_dir = "trading_data/funds/TEST"
    
    print_info(f"Using test fund: {test_fund}")
    print_info(f"Data directory: {data_dir}")
    
    # Create database operations instance
    db_ops = DatabaseOperations(test_fund)
    
    # Sample email trades
    email_trades = [
        {
            "email": """
            Your order has been filled.
            Symbol: TEST_STOCK
            Type: Buy
            Shares: 100
            Average price: $50.00
            Total cost: $5,000.00
            Time: 2024-01-15 10:30:00 EST
            """,
            "description": "Basic buy trade"
        },
        {
            "email": """
            Your order has been filled.
            Symbol: TEST_STOCK
            Type: Sell
            Shares: 50
            Average price: $55.00
            Total cost: $2,750.00
            Time: 2024-01-15 14:30:00 EST
            """,
            "description": "Sell trade (partial position)"
        },
        {
            "email": """
            Your order has been filled.
            Symbol: ANOTHER_STOCK
            Type: Buy
            Shares: 25
            Average price: $200.00
            Total cost: $5,000.00
            Time: 2024-01-15 16:00:00 EST
            """,
            "description": "Another buy trade"
        }
    ]
    
    print_info("\n📧 Processing Email Trades...")
    
    for i, trade_data in enumerate(email_trades, 1):
        print_info(f"\n--- Trade {i}: {trade_data['description']} ---")
        
        # Parse trade
        trade = parse_trade_from_email(trade_data['email'])
        if trade:
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
                print_success("✅ Added to database")
            else:
                print_warning(f"❌ Failed to add: {result['errors']}")
        else:
            print_warning("❌ Failed to parse trade")
    
    # Show final data
    print_info("\n📊 Final Database State:")
    db_ops.list_fund_data()
    
    # Run consistency tests
    print_info("\n🧪 Running Consistency Tests:")
    db_ops.run_consistency_tests()

def create_email_trade_test_scenarios():
    """Create test scenarios based on email trade processing."""
    print_header("🎭 EMAIL TRADE TEST SCENARIOS")
    
    scenarios = {
        "email_basic_trading": {
            "description": "Basic email trading scenario",
            "trades": [
                {
                    "email": "Symbol: EMAIL_TEST\nType: Buy\nShares: 100\nAverage price: $50.00\nTotal cost: $5,000.00",
                    "expected": "EMAIL_TEST BUY 100 @ $50.00"
                },
                {
                    "email": "Symbol: EMAIL_TEST\nType: Sell\nShares: 50\nAverage price: $55.00\nTotal cost: $2,750.00",
                    "expected": "EMAIL_TEST SELL 50 @ $55.00"
                }
            ]
        },
        "email_fifo_trading": {
            "description": "FIFO email trading scenario",
            "trades": [
                {
                    "email": "Symbol: FIFO_EMAIL\nType: Buy\nShares: 100\nAverage price: $50.00\nTotal cost: $5,000.00",
                    "expected": "FIFO_EMAIL BUY 100 @ $50.00"
                },
                {
                    "email": "Symbol: FIFO_EMAIL\nType: Buy\nShares: 50\nAverage price: $60.00\nTotal cost: $3,000.00",
                    "expected": "FIFO_EMAIL BUY 50 @ $60.00"
                },
                {
                    "email": "Symbol: FIFO_EMAIL\nType: Sell\nShares: 75\nAverage price: $70.00\nTotal cost: $5,250.00",
                    "expected": "FIFO_EMAIL SELL 75 @ $70.00"
                }
            ]
        },
        "email_precision_trading": {
            "description": "Precision email trading scenario",
            "trades": [
                {
                    "email": "Symbol: PRECISION_EMAIL\nType: Buy\nShares: 150.5\nAverage price: $33.333\nTotal cost: $5,016.65",
                    "expected": "PRECISION_EMAIL BUY 150.5 @ $33.333"
                }
            ]
        }
    }
    
    for scenario_name, details in scenarios.items():
        print_info(f"\n📋 {scenario_name.upper()}:")
        print_info(f"   Description: {details['description']}")
        print_info("   Trades:")
        for trade in details['trades']:
            print_info(f"     - {trade['expected']}")
    
    print_info("\n💡 USAGE:")
    print_info("   These scenarios can be used to test email trade processing")
    print_info("   with realistic email formats and edge cases")
    print_info("   They complement the existing database operations scenarios")

def show_email_trade_benefits():
    """Show benefits of using email trade processing for testing."""
    print_header("✨ EMAIL TRADE PROCESSING BENEFITS")
    
    benefits = [
        "🎯 REALISTIC TESTING: Uses actual email formats from brokers",
        "🔄 COMPLETE WORKFLOW: Tests parsing, validation, and persistence",
        "🛡️ DUPLICATE HANDLING: Tests idempotency and data integrity",
        "💰 P&L ACCURACY: Tests sell trade correction and cost basis calculation",
        "📊 POSITION UPDATES: Tests portfolio position management",
        "🔄 REPOSITORY SWITCHING: Tests CSV vs Supabase consistency",
        "⚡ ERROR HANDLING: Tests fallback mechanisms and error recovery",
        "🎭 EDGE CASES: Tests precision, currency, and timestamp handling"
    ]
    
    for benefit in benefits:
        print_info(f"   {benefit}")
    
    print_info("\n🎯 RECOMMENDATIONS:")
    print_info("   1. Use email trade processing for integration testing")
    print_info("   2. Combine with database operations for comprehensive testing")
    print_info("   3. Test both CSV-only and dual-write modes")
    print_info("   4. Validate P&L calculations across different scenarios")
    print_info("   5. Test error handling and fallback mechanisms")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze email trade processing workflow")
    parser.add_argument("--analyze", action="store_true", help="Analyze the workflow")
    parser.add_argument("--demonstrate", action="store_true", help="Demonstrate processing")
    parser.add_argument("--scenarios", action="store_true", help="Show test scenarios")
    parser.add_argument("--benefits", action="store_true", help="Show benefits")
    
    args = parser.parse_args()
    
    if args.analyze:
        analyze_email_trade_workflow()
    elif args.demonstrate:
        demonstrate_email_trade_processing()
    elif args.scenarios:
        create_email_trade_test_scenarios()
    elif args.benefits:
        show_email_trade_benefits()
    else:
        print_info("Use --analyze, --demonstrate, --scenarios, or --benefits to see different options")
        print_info("Run 'python debug/analyze_email_trade_workflow.py --help' for more information")

if __name__ == "__main__":
    main()
