"""
Database Operations Debug Suite

This module provides utility functions for database operations during testing and debugging.
These functions are NOT for production use and should only be used in test environments.
"""

import os
import sys
from pathlib import Path
sys.path.append('.')

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from data.repositories.supabase_repository import SupabaseRepository
from data.models.trade import Trade
from data.models.portfolio import Position, PortfolioSnapshot
from display.console_output import print_success, print_error, print_warning, print_info, print_header

# Load Supabase credentials
load_dotenv("web_dashboard/.env")

class DatabaseOperations:
    """Database operations for testing and debugging."""
    
    def __init__(self, fund_name: str):
        """Initialize database operations for a specific fund.
        
        Args:
            fund_name: Name of the fund to operate on
        """
        self.fund_name = fund_name
        self.supabase_repo = SupabaseRepository(fund=fund_name)
        print_info(f"Initialized database operations for fund: {fund_name}")
    
    def clear_fund_data(self, confirm: bool = False) -> Dict[str, Any]:
        """Clear all data for a specific fund from the database.
        
        Args:
            confirm: Whether to skip confirmation prompt
            
        Returns:
            Dictionary with results of the clearing operation
        """
        results = {
            "fund_name": self.fund_name,
            "trades_deleted": 0,
            "positions_deleted": 0,
            "snapshots_deleted": 0,
            "cash_balances_deleted": 0,
            "errors": []
        }
        
        print_header(f"🗄️ CLEARING DATABASE DATA: {self.fund_name}")
        print_warning("⚠️  This will permanently delete ALL database records for this fund!")
        print_warning("   - All trades will be deleted")
        print_warning("   - All positions will be deleted")
        print_warning("   - All snapshots will be deleted")
        print_warning("   - All cash balances will be deleted")
        print_warning("   - This action cannot be undone!")
        
        if not confirm:
            response = input("\nAre you sure you want to continue? (type 'CLEAR_DB' to confirm): ").strip()
            if response != "CLEAR_DB":
                print_info("❌ Operation cancelled by user")
                return results
        
        try:
            # Note: We need to implement delete methods in the repository
            # For now, we'll provide instructions for manual cleanup
            print_info("🔧 Manual database cleanup required")
            print_info("Execute the following SQL commands in Supabase dashboard:")
            print_info("")
            print_info(f"DELETE FROM trade_log WHERE fund = '{self.fund_name}';")
            print_info(f"DELETE FROM portfolio_positions WHERE fund = '{self.fund_name}';")
            print_info(f"DELETE FROM portfolio_snapshots WHERE fund = '{self.fund_name}';")
            print_info(f"DELETE FROM cash_balances WHERE fund = '{self.fund_name}';")
            print_info("")
            print_warning("⚠️  Manual cleanup required - implement delete methods in repository")
            
            results["success"] = True
            print_success(f"✅ Database cleanup instructions provided for fund '{self.fund_name}'")
            
        except Exception as e:
            error_msg = f"Error during database cleanup: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results
    
    def list_fund_data(self) -> Dict[str, Any]:
        """List all data for a specific fund.
        
        Returns:
            Dictionary with data summary
        """
        results = {
            "fund_name": self.fund_name,
            "trades": [],
            "positions": [],
            "snapshots": [],
            "cash_balances": [],
            "errors": []
        }
        
        print_header(f"📊 DATABASE DATA SUMMARY: {self.fund_name}")
        
        try:
            # Get trades
            trades = self.supabase_repo.get_trade_history()
            results["trades"] = trades
            print_info(f"📈 Trades: {len(trades)}")
            for trade in trades[:5]:  # Show first 5
                print_info(f"   {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
            if len(trades) > 5:
                print_info(f"   ... and {len(trades) - 5} more")
            
            # Get positions (from snapshots)
            snapshots = self.supabase_repo.get_portfolio_data()
            results["snapshots"] = snapshots
            print_info(f"📊 Snapshots: {len(snapshots)}")
            
            # Count positions
            total_positions = sum(len(snapshot.positions) for snapshot in snapshots)
            print_info(f"📈 Total Positions: {total_positions}")
            
            # Get cash balances
            cash_balances = self.supabase_repo.get_cash_balances()
            results["cash_balances"] = cash_balances
            print_info(f"💰 Cash Balances: {len(cash_balances)}")
            for cb in cash_balances:
                print_info(f"   {cb.currency}: {cb.amount}")
            
        except Exception as e:
            error_msg = f"Error listing fund data: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results
    
    def add_test_trade(self, ticker: str, action: str, shares: Decimal, price: Decimal, 
                      currency: str = "CAD", reason: str = "Test trade") -> Dict[str, Any]:
        """Add a test trade to the database.
        
        Args:
            ticker: Stock ticker symbol
            action: BUY or SELL
            shares: Number of shares
            price: Price per share
            currency: Currency code
            reason: Trade reason
            
        Returns:
            Dictionary with results
        """
        results = {
            "success": False,
            "trade": None,
            "errors": []
        }
        
        print_info(f"➕ Adding test trade: {action} {shares} {ticker} @ {price} {currency}")
        
        try:
            # Create trade
            trade = Trade(
                ticker=ticker,
                action=action,
                shares=shares,
                price=price,
                currency=currency,
                timestamp=datetime.now(timezone.utc),
                reason=reason
            )
            
            # Save trade
            self.supabase_repo.save_trade(trade)
            results["trade"] = trade
            results["success"] = True
            
            print_success(f"✅ Test trade added successfully")
            
        except Exception as e:
            error_msg = f"Error adding test trade: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results
    
    def add_test_position(self, ticker: str, shares: Decimal, avg_price: Decimal,
                         current_price: Decimal, currency: str = "CAD", 
                         company: str = "Test Company") -> Dict[str, Any]:
        """Add a test position to the database.
        
        Args:
            ticker: Stock ticker symbol
            shares: Number of shares
            avg_price: Average purchase price
            current_price: Current market price
            currency: Currency code
            company: Company name
            
        Returns:
            Dictionary with results
        """
        results = {
            "success": False,
            "position": None,
            "errors": []
        }
        
        print_info(f"➕ Adding test position: {shares} {ticker} @ {current_price} {currency}")
        
        try:
            # Calculate derived values
            cost_basis = shares * avg_price
            market_value = shares * current_price
            unrealized_pnl = market_value - cost_basis
            
            # Create position
            position = Position(
                ticker=ticker,
                shares=shares,
                avg_price=avg_price,
                cost_basis=cost_basis,
                currency=currency,
                company=company,
                current_price=current_price,
                market_value=market_value,
                unrealized_pnl=unrealized_pnl
            )
            
            # Create snapshot with position
            snapshot = PortfolioSnapshot(
                positions=[position],
                timestamp=datetime.now(timezone.utc),
                total_value=market_value
            )
            
            # Save snapshot
            self.supabase_repo.save_portfolio_snapshot(snapshot)
            results["position"] = position
            results["success"] = True
            
            print_success(f"✅ Test position added successfully")
            print_info(f"   Cost Basis: {cost_basis}")
            print_info(f"   Market Value: {market_value}")
            print_info(f"   Unrealized P&L: {unrealized_pnl}")
            
        except Exception as e:
            error_msg = f"Error adding test position: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results
    
    def create_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """Create a predefined test scenario.
        
        Args:
            scenario_name: Name of the test scenario
            
        Returns:
            Dictionary with results
        """
        results = {
            "success": False,
            "scenario": scenario_name,
            "trades_added": 0,
            "positions_added": 0,
            "errors": []
        }
        
        print_info(f"🎭 Creating test scenario: {scenario_name}")
        
        try:
            if scenario_name == "basic_trading":
                # Basic trading scenario
                trades = [
                    ("AAPL", "BUY", Decimal("100"), Decimal("150.00"), "USD"),
                    ("AAPL", "SELL", Decimal("50"), Decimal("160.00"), "USD"),
                    ("GOOGL", "BUY", Decimal("25"), Decimal("2800.00"), "USD"),
                ]
                
                for ticker, action, shares, price, currency in trades:
                    self.add_test_trade(ticker, action, shares, price, currency)
                    results["trades_added"] += 1
                
                # Add positions
                positions = [
                    ("AAPL", Decimal("50"), Decimal("150.00"), Decimal("155.00"), "USD", "Apple Inc."),
                    ("GOOGL", Decimal("25"), Decimal("2800.00"), Decimal("2850.00"), "USD", "Alphabet Inc."),
                ]
                
                for ticker, shares, avg_price, current_price, currency, company in positions:
                    self.add_test_position(ticker, shares, avg_price, current_price, currency, company)
                    results["positions_added"] += 1
                
            elif scenario_name == "fifo_testing":
                # FIFO testing scenario
                trades = [
                    ("FIFO_TEST", "BUY", Decimal("100"), Decimal("50.00"), "CAD"),
                    ("FIFO_TEST", "BUY", Decimal("50"), Decimal("60.00"), "CAD"),
                    ("FIFO_TEST", "SELL", Decimal("75"), Decimal("70.00"), "CAD"),
                ]
                
                for ticker, action, shares, price, currency in trades:
                    self.add_test_trade(ticker, action, shares, price, currency)
                    results["trades_added"] += 1
                
            elif scenario_name == "precision_testing":
                # Precision testing scenario
                trades = [
                    ("PRECISION", "BUY", Decimal("150.5"), Decimal("33.333"), "CAD"),
                ]
                
                for ticker, action, shares, price, currency in trades:
                    self.add_test_trade(ticker, action, shares, price, currency)
                    results["trades_added"] += 1
                
                # Add position with precise decimals
                self.add_test_position(
                    "PRECISION", 
                    Decimal("150.5"), 
                    Decimal("33.333"), 
                    Decimal("35.789"), 
                    "CAD", 
                    "Precision Test Company"
                )
                results["positions_added"] += 1
                
            else:
                raise ValueError(f"Unknown scenario: {scenario_name}")
            
            results["success"] = True
            print_success(f"✅ Test scenario '{scenario_name}' created successfully")
            print_info(f"   Trades added: {results['trades_added']}")
            print_info(f"   Positions added: {results['positions_added']}")
            
        except Exception as e:
            error_msg = f"Error creating test scenario: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results
    
    def run_consistency_tests(self) -> Dict[str, Any]:
        """Run consistency tests on the fund data.
        
        Returns:
            Dictionary with test results
        """
        results = {
            "success": False,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }
        
        print_header(f"🧪 RUNNING CONSISTENCY TESTS: {self.fund_name}")
        
        try:
            # Test 1: Data retrieval
            print_info("Test 1: Data retrieval")
            trades = self.supabase_repo.get_trade_history()
            snapshots = self.supabase_repo.get_portfolio_data()
            cash_balances = self.supabase_repo.get_cash_balances()
            
            print_success(f"   ✅ Retrieved {len(trades)} trades, {len(snapshots)} snapshots, {len(cash_balances)} cash balances")
            results["tests_passed"] += 1
            
            # Test 2: P&L calculations
            print_info("Test 2: P&L calculations")
            if snapshots:
                latest_snapshot = snapshots[-1]
                total_pnl = sum(pos.unrealized_pnl or Decimal('0') for pos in latest_snapshot.positions)
                total_value = sum(pos.market_value or Decimal('0') for pos in latest_snapshot.positions)
                
                print_success(f"   ✅ Total P&L: {total_pnl}, Total Value: {total_value}")
                results["tests_passed"] += 1
            else:
                print_warning("   ⚠️  No snapshots found for P&L testing")
                results["tests_failed"] += 1
            
            # Test 3: Trade consistency
            print_info("Test 3: Trade consistency")
            if trades:
                buy_trades = [t for t in trades if t.action == "BUY"]
                sell_trades = [t for t in trades if t.action == "SELL"]
                
                print_success(f"   ✅ {len(buy_trades)} buy trades, {len(sell_trades)} sell trades")
                results["tests_passed"] += 1
            else:
                print_warning("   ⚠️  No trades found for consistency testing")
                results["tests_failed"] += 1
            
            results["success"] = results["tests_failed"] == 0
            print_success(f"✅ Consistency tests completed: {results['tests_passed']} passed, {results['tests_failed']} failed")
            
        except Exception as e:
            error_msg = f"Error running consistency tests: {e}"
            results["errors"].append(error_msg)
            print_error(error_msg)
        
        return results


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database operations for testing and debugging")
    parser.add_argument("--fund", required=True, help="Fund name to operate on")
    parser.add_argument("--action", required=True, 
                       choices=["list", "clear", "add-trade", "add-position", "create-scenario", "test-consistency"],
                       help="Action to perform")
    parser.add_argument("--ticker", help="Ticker symbol for trade/position operations")
    parser.add_argument("--action-type", help="BUY or SELL for trade operations")
    parser.add_argument("--shares", type=float, help="Number of shares")
    parser.add_argument("--price", type=float, help="Price per share")
    parser.add_argument("--currency", default="CAD", help="Currency code")
    parser.add_argument("--scenario", help="Test scenario name")
    parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompts")
    
    args = parser.parse_args()
    
    # Create database operations instance
    db_ops = DatabaseOperations(args.fund)
    
    if args.action == "list":
        db_ops.list_fund_data()
    elif args.action == "clear":
        db_ops.clear_fund_data(args.confirm)
    elif args.action == "add-trade":
        if not all([args.ticker, args.action_type, args.shares, args.price]):
            print_error("❌ --ticker, --action-type, --shares, and --price are required for add-trade")
            return
        db_ops.add_test_trade(args.ticker, args.action_type, Decimal(str(args.shares)), 
                             Decimal(str(args.price)), args.currency)
    elif args.action == "add-position":
        if not all([args.ticker, args.shares, args.price]):
            print_error("❌ --ticker, --shares, and --price are required for add-position")
            return
        # Use price as both avg_price and current_price for simplicity
        db_ops.add_test_position(args.ticker, Decimal(str(args.shares)), 
                               Decimal(str(args.price)), Decimal(str(args.price)), 
                               args.currency)
    elif args.action == "create-scenario":
        if not args.scenario:
            print_error("❌ --scenario is required for create-scenario")
            return
        db_ops.create_test_scenario(args.scenario)
    elif args.action == "test-consistency":
        db_ops.run_consistency_tests()


if __name__ == "__main__":
    main()
