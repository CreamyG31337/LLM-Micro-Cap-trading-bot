"""
Test Portfolio Scenarios

This script provides utilities for testing various portfolio scenarios
with different trading patterns and P&L calculations.
"""

import sys
from pathlib import Path
sys.path.append('.')

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from debug.database_operations import DatabaseOperations
from debug.calculate_portfolio_from_trades import run_full_portfolio_calculation
from display.console_output import print_header, print_info, print_success, print_warning, print_error

class PortfolioScenarioTester:
    """Test various portfolio scenarios."""
    
    def __init__(self, fund_name: str):
        """Initialize portfolio scenario tester.
        
        Args:
            fund_name: Name of the fund to test
        """
        self.fund_name = fund_name
        self.db_ops = DatabaseOperations(fund_name)
    
    def create_basic_trading_scenario(self) -> bool:
        """Create a basic trading scenario.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating basic trading scenario...")
        
        try:
            # Clear existing data
            self.db_ops.clear_fund_data(confirm=True)
            
            # Add basic trades
            trades = [
                ("AAPL", "BUY", Decimal("100"), Decimal("150.00"), "USD", "Basic Apple purchase"),
                ("GOOGL", "BUY", Decimal("10"), Decimal("2800.00"), "USD", "Basic Google purchase"),
            ]
            
            for ticker, action, shares, price, currency, reason in trades:
                result = self.db_ops.add_test_trade(ticker, action, shares, price, currency, reason)
                if not result['success']:
                    print_error(f"Failed to add {ticker} trade: {result['errors']}")
                    return False
            
            # Calculate portfolio
            run_full_portfolio_calculation(self.fund_name)
            
            print_success("Basic trading scenario created successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to create basic trading scenario: {e}")
            return False
    
    def create_fifo_trading_scenario(self) -> bool:
        """Create a FIFO trading scenario.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating FIFO trading scenario...")
        
        try:
            # Clear existing data
            self.db_ops.clear_fund_data(confirm=True)
            
            # Add FIFO trades (multiple buys, then sells)
            trades = [
                ("FIFO_TEST", "BUY", Decimal("100"), Decimal("50.00"), "USD", "First FIFO purchase"),
                ("FIFO_TEST", "BUY", Decimal("50"), Decimal("60.00"), "USD", "Second FIFO purchase"),
                ("FIFO_TEST", "SELL", Decimal("75"), Decimal("70.00"), "USD", "FIFO sell (should use first 75 shares)"),
            ]
            
            for ticker, action, shares, price, currency, reason in trades:
                result = self.db_ops.add_test_trade(ticker, action, shares, price, currency, reason)
                if not result['success']:
                    print_error(f"Failed to add {ticker} trade: {result['errors']}")
                    return False
            
            # Calculate portfolio
            run_full_portfolio_calculation(self.fund_name)
            
            print_success("FIFO trading scenario created successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to create FIFO trading scenario: {e}")
            return False
    
    def create_precision_trading_scenario(self) -> bool:
        """Create a precision trading scenario.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating precision trading scenario...")
        
        try:
            # Clear existing data
            self.db_ops.clear_fund_data(confirm=True)
            
            # Add precision trades (decimal values)
            trades = [
                ("PRECISION_TEST", "BUY", Decimal("150.5"), Decimal("33.333"), "USD", "Precision purchase"),
                ("PRECISION_TEST", "BUY", Decimal("75.25"), Decimal("35.789"), "USD", "Another precision purchase"),
            ]
            
            for ticker, action, shares, price, currency, reason in trades:
                result = self.db_ops.add_test_trade(ticker, action, shares, price, currency, reason)
                if not result['success']:
                    print_error(f"Failed to add {ticker} trade: {result['errors']}")
                    return False
            
            # Calculate portfolio
            run_full_portfolio_calculation(self.fund_name)
            
            print_success("Precision trading scenario created successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to create precision trading scenario: {e}")
            return False
    
    def create_mixed_currency_scenario(self) -> bool:
        """Create a mixed currency scenario.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating mixed currency scenario...")
        
        try:
            # Clear existing data
            self.db_ops.clear_fund_data(confirm=True)
            
            # Add mixed currency trades
            trades = [
                ("USD_STOCK", "BUY", Decimal("100"), Decimal("200.00"), "USD", "USD stock purchase"),
                ("CAD_STOCK", "BUY", Decimal("50"), Decimal("300.00"), "CAD", "CAD stock purchase"),
                ("EUR_STOCK", "BUY", Decimal("25"), Decimal("150.00"), "EUR", "EUR stock purchase"),
            ]
            
            for ticker, action, shares, price, currency, reason in trades:
                result = self.db_ops.add_test_trade(ticker, action, shares, price, currency, reason)
                if not result['success']:
                    print_error(f"Failed to add {ticker} trade: {result['errors']}")
                    return False
            
            # Calculate portfolio
            run_full_portfolio_calculation(self.fund_name)
            
            print_success("Mixed currency scenario created successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to create mixed currency scenario: {e}")
            return False
    
    def run_scenario_analysis(self) -> Dict[str, Any]:
        """Run analysis on current scenario.
        
        Returns:
            Dictionary with analysis results
        """
        print_info("Running scenario analysis...")
        
        try:
            # Get current data
            self.db_ops.list_fund_data()
            
            # Run consistency tests
            self.db_ops.run_consistency_tests()
            
            print_success("Scenario analysis completed")
            return {"success": True}
            
        except Exception as e:
            print_error(f"Failed to run scenario analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all portfolio scenarios.
        
        Returns:
            Dictionary with results from all scenarios
        """
        print_header("RUNNING ALL PORTFOLIO SCENARIOS")
        
        scenarios = {
            "basic_trading": self.create_basic_trading_scenario,
            "fifo_trading": self.create_fifo_trading_scenario,
            "precision_trading": self.create_precision_trading_scenario,
            "mixed_currency": self.create_mixed_currency_scenario,
        }
        
        results = {}
        
        for scenario_name, scenario_func in scenarios.items():
            print_info(f"\n--- Running {scenario_name} scenario ---")
            
            try:
                success = scenario_func()
                results[scenario_name] = {"success": success}
                
                if success:
                    # Run analysis
                    analysis = self.run_scenario_analysis()
                    results[scenario_name]["analysis"] = analysis
                
            except Exception as e:
                print_error(f"Scenario {scenario_name} failed: {e}")
                results[scenario_name] = {"success": False, "error": str(e)}
        
        print_success("All scenarios completed")
        return results

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test portfolio scenarios")
    parser.add_argument("--fund", required=True, help="Fund name to test")
    parser.add_argument("--scenario", 
                       choices=["basic", "fifo", "precision", "mixed-currency", "all"],
                       help="Scenario to run")
    parser.add_argument("--analyze", action="store_true", help="Run analysis on current scenario")
    
    args = parser.parse_args()
    
    # Create scenario tester
    tester = PortfolioScenarioTester(args.fund)
    
    if args.scenario == "basic":
        tester.create_basic_trading_scenario()
    elif args.scenario == "fifo":
        tester.create_fifo_trading_scenario()
    elif args.scenario == "precision":
        tester.create_precision_trading_scenario()
    elif args.scenario == "mixed-currency":
        tester.create_mixed_currency_scenario()
    elif args.scenario == "all":
        tester.run_all_scenarios()
    
    if args.analyze:
        tester.run_scenario_analysis()

if __name__ == "__main__":
    main()
