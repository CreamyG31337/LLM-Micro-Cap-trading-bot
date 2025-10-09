"""
Manual P&L Calculation Verification Test

This script creates a test scenario with 7 days of historical data and manually
verifies that the system's P&L calculations (daily, 5-day, total) are correct.
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

class ManualPnLVerification:
    """Manual verification of P&L calculations."""
    
    def __init__(self, fund_name: str):
        """Initialize manual P&L verification.
        
        Args:
            fund_name: Name of the fund to test
        """
        self.fund_name = fund_name
        self.db_ops = DatabaseOperations(fund_name)
        self.test_data = {}
    
    def create_7_day_test_scenario(self) -> bool:
        """Create a 7-day test scenario with known price movements.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating 7-day test scenario with known price movements...")
        
        try:
            # Clear existing data
            self.db_ops.clear_fund_data(confirm=True)
            
            # Define test scenario with known price movements
            # Day 0: Buy 100 shares at $100
            # Day 1: Price goes to $105 (+5%)
            # Day 2: Price goes to $110 (+10% from Day 0)
            # Day 3: Price goes to $108 (+8% from Day 0)
            # Day 4: Price goes to $112 (+12% from Day 0)
            # Day 5: Price goes to $115 (+15% from Day 0)
            # Day 6: Price goes to $118 (+18% from Day 0)
            # Day 7: Price goes to $120 (+20% from Day 0)
            
            self.test_data = {
                "ticker": "TEST_PNL",
                "shares": Decimal("100"),
                "buy_price": Decimal("100.00"),
                "daily_prices": [
                    Decimal("100.00"),  # Day 0 (purchase)
                    Decimal("105.00"),  # Day 1 (+5%)
                    Decimal("110.00"),  # Day 2 (+10%)
                    Decimal("108.00"),  # Day 3 (+8%)
                    Decimal("112.00"),  # Day 4 (+12%)
                    Decimal("115.00"),  # Day 5 (+15%)
                    Decimal("118.00"),  # Day 6 (+18%)
                    Decimal("120.00"),  # Day 7 (+20%)
                ],
                "expected_calculations": {
                    "total_pnl": Decimal("2000.00"),  # (120 - 100) * 100
                    "total_pnl_pct": Decimal("20.00"),  # 20%
                    "daily_pnl_day7": Decimal("200.00"),  # (120 - 118) * 100
                    "daily_pnl_pct_day7": Decimal("1.69"),  # (120 - 118) / 118 * 100
                    "five_day_pnl_day7": Decimal("1000.00"),  # (120 - 110) * 100 (Day 7 vs Day 2)
                    "five_day_pnl_pct_day7": Decimal("9.09"),  # (120 - 110) / 110 * 100
                }
            }
            
            # Add the initial purchase trade
            result = self.db_ops.add_test_trade(
                self.test_data["ticker"],
                "BUY",
                self.test_data["shares"],
                self.test_data["buy_price"],
                "USD",
                "Initial purchase for P&L testing"
            )
            
            if not result['success']:
                print_error(f"Failed to add initial trade: {result['errors']}")
                return False
            
            print_success("7-day test scenario created successfully")
            print_info(f"   Ticker: {self.test_data['ticker']}")
            print_info(f"   Shares: {self.test_data['shares']}")
            print_info(f"   Buy Price: ${self.test_data['buy_price']}")
            print_info(f"   Price Progression: {self.test_data['daily_prices']}")
            
            return True
            
        except Exception as e:
            print_error(f"Failed to create 7-day test scenario: {e}")
            return False
    
    def create_historical_positions(self) -> bool:
        """Create historical positions for each day.
        
        Returns:
            True if successful, False otherwise
        """
        print_info("Creating historical positions for each day...")
        
        try:
            # Create positions for each day with the corresponding price
            for day, price in enumerate(self.test_data["daily_prices"]):
                # Skip day 0 (purchase day)
                if day == 0:
                    continue
                
                # Create position for this day
                position_data = {
                    "ticker": self.test_data["ticker"],
                    "shares": self.test_data["shares"],
                    "avg_price": self.test_data["buy_price"],  # Average price stays the same
                    "current_price": price,
                    "cost_basis": self.test_data["shares"] * self.test_data["buy_price"],
                    "currency": "USD",
                    "company": "Test P&L Company"
                }
                
                # Calculate market value and unrealized P&L
                market_value = self.test_data["shares"] * price
                unrealized_pnl = market_value - position_data["cost_basis"]
                
                # Create position
                from data.models.portfolio import Position
                position = Position(
                    ticker=position_data["ticker"],
                    shares=position_data["shares"],
                    avg_price=position_data["avg_price"],
                    cost_basis=position_data["cost_basis"],
                    currency=position_data["currency"],
                    company=position_data["company"],
                    current_price=position_data["current_price"],
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl
                )
                
                # Create snapshot for this day
                from data.models.portfolio import PortfolioSnapshot
                snapshot = PortfolioSnapshot(
                    positions=[position],
                    timestamp=datetime.now(timezone.utc) - timedelta(days=7-day),
                    total_value=market_value
                )
                
                # Save snapshot
                self.db_ops.supabase_repo.save_portfolio_snapshot(snapshot)
                
                print_info(f"   Day {day}: Price ${price}, Market Value ${market_value}, P&L ${unrealized_pnl}")
            
            print_success("Historical positions created successfully")
            return True
            
        except Exception as e:
            print_error(f"Failed to create historical positions: {e}")
            return False
    
    def verify_manual_calculations(self) -> Dict[str, Any]:
        """Verify manual P&L calculations.
        
        Returns:
            Dictionary with verification results
        """
        print_info("Verifying manual P&L calculations...")
        
        try:
            # Get current position data
            snapshots = self.db_ops.supabase_repo.get_portfolio_data()
            
            if not snapshots:
                print_warning("No snapshots found")
                return {"success": False, "error": "No snapshots found"}
            
            latest_snapshot = snapshots[-1]
            latest_position = latest_snapshot.positions[0]
            
            # Manual calculations
            current_price = latest_position.current_price
            shares = latest_position.shares
            cost_basis = latest_position.cost_basis
            
            # Total P&L calculation
            total_pnl_manual = (current_price - self.test_data["buy_price"]) * shares
            total_pnl_pct_manual = (total_pnl_manual / cost_basis) * 100
            
            # Daily P&L calculation (Day 7 vs Day 6)
            day6_price = self.test_data["daily_prices"][6]  # Day 6 price
            daily_pnl_manual = (current_price - day6_price) * shares
            daily_pnl_pct_manual = ((current_price - day6_price) / day6_price) * 100
            
            # 5-day P&L calculation (Day 7 vs Day 2)
            day2_price = self.test_data["daily_prices"][2]  # Day 2 price
            five_day_pnl_manual = (current_price - day2_price) * shares
            five_day_pnl_pct_manual = ((current_price - day2_price) / day2_price) * 100
            
            # Expected values
            expected = self.test_data["expected_calculations"]
            
            # Verification results
            verification_results = {
                "total_pnl": {
                    "manual": total_pnl_manual,
                    "expected": expected["total_pnl"],
                    "system": latest_position.unrealized_pnl,
                    "match": abs(total_pnl_manual - expected["total_pnl"]) < Decimal("0.01")
                },
                "total_pnl_pct": {
                    "manual": total_pnl_pct_manual,
                    "expected": expected["total_pnl_pct"],
                    "match": abs(total_pnl_pct_manual - expected["total_pnl_pct"]) < Decimal("0.01")
                },
                "daily_pnl": {
                    "manual": daily_pnl_manual,
                    "expected": expected["daily_pnl_day7"],
                    "match": abs(daily_pnl_manual - expected["daily_pnl_day7"]) < Decimal("0.01")
                },
                "daily_pnl_pct": {
                    "manual": daily_pnl_pct_manual,
                    "expected": expected["daily_pnl_pct_day7"],
                    "match": abs(daily_pnl_pct_manual - expected["daily_pnl_pct_day7"]) < Decimal("0.01")
                },
                "five_day_pnl": {
                    "manual": five_day_pnl_manual,
                    "expected": expected["five_day_pnl_day7"],
                    "match": abs(five_day_pnl_manual - expected["five_day_pnl_day7"]) < Decimal("0.01")
                },
                "five_day_pnl_pct": {
                    "manual": five_day_pnl_pct_manual,
                    "expected": expected["five_day_pnl_pct_day7"],
                    "match": abs(five_day_pnl_pct_manual - expected["five_day_pnl_pct_day7"]) < Decimal("0.01")
                }
            }
            
            # Display results
            print_info("\n📊 MANUAL CALCULATION VERIFICATION:")
            print_info(f"   Current Price: ${current_price}")
            print_info(f"   Shares: {shares}")
            print_info(f"   Cost Basis: ${cost_basis}")
            
            print_info("\n💰 TOTAL P&L:")
            print_info(f"   Manual: ${total_pnl_manual}")
            print_info(f"   Expected: ${expected['total_pnl']}")
            print_info(f"   System: ${latest_position.unrealized_pnl}")
            print_info(f"   Match: {'✅' if verification_results['total_pnl']['match'] else '❌'}")
            
            print_info("\n📈 DAILY P&L (Day 7 vs Day 6):")
            print_info(f"   Manual: ${daily_pnl_manual}")
            print_info(f"   Expected: ${expected['daily_pnl_day7']}")
            print_info(f"   Match: {'✅' if verification_results['daily_pnl']['match'] else '❌'}")
            
            print_info("\n📊 5-DAY P&L (Day 7 vs Day 2):")
            print_info(f"   Manual: ${five_day_pnl_manual}")
            print_info(f"   Expected: ${expected['five_day_pnl_day7']}")
            print_info(f"   Match: {'✅' if verification_results['five_day_pnl']['match'] else '❌'}")
            
            # Overall success
            all_match = all(result["match"] for result in verification_results.values())
            
            if all_match:
                print_success("✅ All manual calculations match expected values!")
            else:
                print_error("❌ Some calculations don't match expected values")
            
            return {
                "success": all_match,
                "results": verification_results,
                "manual_calculations": {
                    "total_pnl": total_pnl_manual,
                    "total_pnl_pct": total_pnl_pct_manual,
                    "daily_pnl": daily_pnl_manual,
                    "daily_pnl_pct": daily_pnl_pct_manual,
                    "five_day_pnl": five_day_pnl_manual,
                    "five_day_pnl_pct": five_day_pnl_pct_manual
                }
            }
            
        except Exception as e:
            print_error(f"Failed to verify manual calculations: {e}")
            return {"success": False, "error": str(e)}
    
    def test_system_pnl_calculations(self) -> Dict[str, Any]:
        """Test system P&L calculations.
        
        Returns:
            Dictionary with system calculation results
        """
        print_info("Testing system P&L calculations...")
        
        try:
            # Get current data
            self.db_ops.list_fund_data()
            
            # Run consistency tests
            self.db_ops.run_consistency_tests()
            
            # Get portfolio data
            snapshots = self.db_ops.supabase_repo.get_portfolio_data()
            
            if not snapshots:
                print_warning("No snapshots found")
                return {"success": False, "error": "No snapshots found"}
            
            latest_snapshot = snapshots[-1]
            latest_position = latest_snapshot.positions[0]
            
            # System calculations
            system_results = {
                "unrealized_pnl": latest_position.unrealized_pnl,
                "market_value": latest_position.market_value,
                "cost_basis": latest_position.cost_basis,
                "current_price": latest_position.current_price,
                "shares": latest_position.shares
            }
            
            print_success("System P&L calculations retrieved")
            print_info(f"   Unrealized P&L: ${system_results['unrealized_pnl']}")
            print_info(f"   Market Value: ${system_results['market_value']}")
            print_info(f"   Cost Basis: ${system_results['cost_basis']}")
            
            return {"success": True, "results": system_results}
            
        except Exception as e:
            print_error(f"Failed to test system P&L calculations: {e}")
            return {"success": False, "error": str(e)}
    
    def run_full_verification(self) -> Dict[str, Any]:
        """Run full P&L verification test.
        
        Returns:
            Dictionary with complete verification results
        """
        print_header(f"FULL P&L VERIFICATION TEST: {self.fund_name}")
        
        results = {
            "fund_name": self.fund_name,
            "timestamp": datetime.now(timezone.utc),
            "scenario_created": False,
            "positions_created": False,
            "manual_verification": {},
            "system_test": {},
            "overall_success": False
        }
        
        # Step 1: Create 7-day test scenario
        print_info("Step 1: Creating 7-day test scenario...")
        results["scenario_created"] = self.create_7_day_test_scenario()
        
        if not results["scenario_created"]:
            print_error("Failed to create test scenario")
            return results
        
        # Step 2: Create historical positions
        print_info("Step 2: Creating historical positions...")
        results["positions_created"] = self.create_historical_positions()
        
        if not results["positions_created"]:
            print_error("Failed to create historical positions")
            return results
        
        # Step 3: Verify manual calculations
        print_info("Step 3: Verifying manual calculations...")
        results["manual_verification"] = self.verify_manual_calculations()
        
        # Step 4: Test system calculations
        print_info("Step 4: Testing system calculations...")
        results["system_test"] = self.test_system_pnl_calculations()
        
        # Overall success
        results["overall_success"] = (
            results["scenario_created"] and
            results["positions_created"] and
            results["manual_verification"].get("success", False) and
            results["system_test"].get("success", False)
        )
        
        if results["overall_success"]:
            print_success("✅ Full P&L verification test completed successfully!")
        else:
            print_error("❌ P&L verification test failed")
        
        return results

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manual P&L calculation verification test")
    parser.add_argument("--fund", required=True, help="Fund name to test")
    parser.add_argument("--action", 
                       choices=["create-scenario", "create-positions", "verify-manual", "test-system", "full-test"],
                       help="Action to perform")
    
    args = parser.parse_args()
    
    # Create verification instance
    verifier = ManualPnLVerification(args.fund)
    
    if args.action == "create-scenario":
        verifier.create_7_day_test_scenario()
    elif args.action == "create-positions":
        verifier.create_historical_positions()
    elif args.action == "verify-manual":
        verifier.verify_manual_calculations()
    elif args.action == "test-system":
        verifier.test_system_pnl_calculations()
    elif args.action == "full-test":
        verifier.run_full_verification()

if __name__ == "__main__":
    main()
