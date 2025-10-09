"""
Create Test Fund with Historical Data

This script creates a blank test fund and adds historical trades to test
portfolio calculations and P&L tracking.
"""

import sys
from pathlib import Path
sys.path.append('.')

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from debug.database_operations import DatabaseOperations
from display.console_output import print_header, print_info, print_success, print_warning, print_error

def create_test_fund_structure(fund_name: str, data_dir: str = "trading_data/funds/TEST") -> bool:
    """Create the directory structure for a test fund.
    
    Args:
        fund_name: Name of the test fund
        data_dir: Base data directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        fund_path = Path(data_dir) / fund_name
        fund_path.mkdir(parents=True, exist_ok=True)
        
        # Create necessary subdirectories
        (fund_path / "trades").mkdir(exist_ok=True)
        (fund_path / "positions").mkdir(exist_ok=True)
        (fund_path / "snapshots").mkdir(exist_ok=True)
        (fund_path / "cash").mkdir(exist_ok=True)
        
        print_success(f"✅ Created test fund structure: {fund_path}")
        return True
        
    except Exception as e:
        print_error(f"❌ Failed to create test fund structure: {e}")
        return False

def add_historical_trades(fund_name: str, data_dir: str = "trading_data/funds/TEST") -> bool:
    """Add historical trades to the test fund.
    
    Args:
        fund_name: Name of the test fund
        data_dir: Base data directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create database operations instance
        db_ops = DatabaseOperations(fund_name)
        
        # Calculate dates (a week ago)
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        week_ago_plus_1 = week_ago + timedelta(hours=1)
        week_ago_plus_2 = week_ago + timedelta(hours=2)
        
        print_info(f"📅 Adding trades from: {week_ago.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Tesla trades
        tesla_trades = [
            {
                "ticker": "TSLA",
                "action": "BUY",
                "shares": Decimal("10"),
                "price": Decimal("250.00"),
                "currency": "USD",
                "reason": "Historical Tesla purchase",
                "timestamp": week_ago
            },
            {
                "ticker": "TSLA", 
                "action": "BUY",
                "shares": Decimal("5"),
                "price": Decimal("255.00"),
                "currency": "USD",
                "reason": "Additional Tesla purchase",
                "timestamp": week_ago_plus_1
            }
        ]
        
        # Apple trades
        apple_trades = [
            {
                "ticker": "AAPL",
                "action": "BUY", 
                "shares": Decimal("20"),
                "price": Decimal("180.00"),
                "currency": "USD",
                "reason": "Historical Apple purchase",
                "timestamp": week_ago_plus_2
            }
        ]
        
        all_trades = tesla_trades + apple_trades
        
        print_info(f"📈 Adding {len(all_trades)} historical trades...")
        
        for i, trade_data in enumerate(all_trades, 1):
            print_info(f"   Trade {i}: {trade_data['ticker']} {trade_data['action']} {trade_data['shares']} @ ${trade_data['price']}")
            
            result = db_ops.add_test_trade(
                trade_data["ticker"],
                trade_data["action"], 
                trade_data["shares"],
                trade_data["price"],
                trade_data["currency"],
                trade_data["reason"]
            )
            
            if result['success']:
                print_success(f"   ✅ Added {trade_data['ticker']} trade")
            else:
                print_error(f"   ❌ Failed to add {trade_data['ticker']} trade: {result['errors']}")
                return False
        
        print_success("✅ All historical trades added successfully")
        return True
        
    except Exception as e:
        print_error(f"❌ Failed to add historical trades: {e}")
        return False

def calculate_portfolio_positions(fund_name: str, data_dir: str = "trading_data/funds/TEST") -> bool:
    """Calculate portfolio positions from trades.
    
    Args:
        fund_name: Name of the test fund
        data_dir: Base data directory
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print_info("📊 Calculating portfolio positions...")
        
        # Create database operations instance
        db_ops = DatabaseOperations(fund_name)
        
        # Get current data
        print_info("📋 Current fund data:")
        db_ops.list_fund_data()
        
        # Run consistency tests
        print_info("\n🧪 Running portfolio consistency tests:")
        db_ops.run_consistency_tests()
        
        return True
        
    except Exception as e:
        print_error(f"❌ Failed to calculate portfolio positions: {e}")
        return False

def create_portfolio_debug_utilities():
    """Create debug utilities for portfolio calculations."""
    print_header("🛠️ CREATING PORTFOLIO DEBUG UTILITIES")
    
    # Create portfolio calculation utility
    utility_code = '''"""
Portfolio Calculation Debug Utilities

This module provides utilities for debugging portfolio calculations,
P&L tracking, and position management.
"""

import sys
from pathlib import Path
sys.path.append('.')

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from debug.database_operations import DatabaseOperations
from display.console_output import print_header, print_info, print_success, print_warning, print_error

class PortfolioDebugger:
    """Debug utilities for portfolio calculations."""
    
    def __init__(self, fund_name: str):
        """Initialize portfolio debugger.
        
        Args:
            fund_name: Name of the fund to debug
        """
        self.fund_name = fund_name
        self.db_ops = DatabaseOperations(fund_name)
    
    def analyze_trades(self) -> Dict[str, Any]:
        """Analyze all trades for a fund.
        
        Returns:
            Dictionary with trade analysis
        """
        print_info(f"🔍 Analyzing trades for fund: {self.fund_name}")
        
        try:
            # Get trades
            trades = self.db_ops.supabase_repo.get_trade_history()
            
            if not trades:
                print_warning("⚠️  No trades found")
                return {"trades": [], "analysis": {}}
            
            # Analyze trades by ticker
            ticker_analysis = {}
            for trade in trades:
                ticker = trade.ticker
                if ticker not in ticker_analysis:
                    ticker_analysis[ticker] = {
                        "total_buy_shares": Decimal('0'),
                        "total_sell_shares": Decimal('0'),
                        "total_buy_cost": Decimal('0'),
                        "total_sell_proceeds": Decimal('0'),
                        "trades": []
                    }
                
                analysis = ticker_analysis[ticker]
                analysis["trades"].append(trade)
                
                if trade.action == "BUY":
                    analysis["total_buy_shares"] += trade.shares
                    analysis["total_buy_cost"] += trade.cost_basis
                elif trade.action == "SELL":
                    analysis["total_sell_shares"] += trade.shares
                    analysis["total_sell_proceeds"] += trade.cost_basis
            
            # Calculate current positions
            for ticker, analysis in ticker_analysis.items():
                analysis["current_shares"] = analysis["total_buy_shares"] - analysis["total_sell_shares"]
                analysis["total_cost_basis"] = analysis["total_buy_cost"] - analysis["total_sell_proceeds"]
                
                if analysis["current_shares"] > 0:
                    analysis["avg_price"] = analysis["total_cost_basis"] / analysis["current_shares"]
                else:
                    analysis["avg_price"] = Decimal('0')
            
            print_success(f"✅ Analyzed {len(trades)} trades across {len(ticker_analysis)} tickers")
            
            # Display analysis
            for ticker, analysis in ticker_analysis.items():
                print_info(f"\\n📈 {ticker}:")
                print_info(f"   Current Shares: {analysis['current_shares']}")
                print_info(f"   Total Cost Basis: ${analysis['total_cost_basis']}")
                print_info(f"   Average Price: ${analysis['avg_price']}")
                print_info(f"   Total Buy Shares: {analysis['total_buy_shares']}")
                print_info(f"   Total Sell Shares: {analysis['total_sell_shares']}")
                print_info(f"   Number of Trades: {len(analysis['trades'])}")
            
            return {
                "trades": trades,
                "analysis": ticker_analysis
            }
            
        except Exception as e:
            print_error(f"❌ Failed to analyze trades: {e}")
            return {"trades": [], "analysis": {}, "error": str(e)}
    
    def calculate_pnl_summary(self) -> Dict[str, Any]:
        """Calculate P&L summary for the fund.
        
        Returns:
            Dictionary with P&L summary
        """
        print_info(f"💰 Calculating P&L summary for fund: {self.fund_name}")
        
        try:
            # Get portfolio data
            snapshots = self.db_ops.supabase_repo.get_portfolio_data()
            
            if not snapshots:
                print_warning("⚠️  No portfolio snapshots found")
                return {"snapshots": [], "pnl_summary": {}}
            
            latest_snapshot = snapshots[-1]
            
            # Calculate P&L
            total_unrealized_pnl = Decimal('0')
            total_market_value = Decimal('0')
            total_cost_basis = Decimal('0')
            
            for position in latest_snapshot.positions:
                if position.unrealized_pnl:
                    total_unrealized_pnl += position.unrealized_pnl
                if position.market_value:
                    total_market_value += position.market_value
                if position.cost_basis:
                    total_cost_basis += position.cost_basis
            
            pnl_summary = {
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_market_value": total_market_value,
                "total_cost_basis": total_cost_basis,
                "pnl_percentage": (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else Decimal('0'),
                "positions_count": len(latest_snapshot.positions)
            }
            
            print_success("✅ P&L summary calculated")
            print_info(f"   Total Unrealized P&L: ${total_unrealized_pnl}")
            print_info(f"   Total Market Value: ${total_market_value}")
            print_info(f"   Total Cost Basis: ${total_cost_basis}")
            print_info(f"   P&L Percentage: {pnl_summary['pnl_percentage']:.2f}%")
            print_info(f"   Positions: {pnl_summary['positions_count']}")
            
            return {
                "snapshots": snapshots,
                "pnl_summary": pnl_summary
            }
            
        except Exception as e:
            print_error(f"❌ Failed to calculate P&L summary: {e}")
            return {"snapshots": [], "pnl_summary": {}, "error": str(e)}
    
    def compare_csv_vs_supabase(self) -> Dict[str, Any]:
        """Compare CSV vs Supabase data consistency.
        
        Returns:
            Dictionary with comparison results
        """
        print_info(f"🔄 Comparing CSV vs Supabase for fund: {self.fund_name}")
        
        try:
            # This would require implementing CSV repository access
            # For now, we'll just show the Supabase data
            print_info("📊 Supabase data:")
            self.db_ops.list_fund_data()
            
            print_warning("⚠️  CSV comparison not implemented yet")
            print_info("   This would require CSV repository access")
            
            return {"comparison": "not_implemented"}
            
        except Exception as e:
            print_error(f"❌ Failed to compare CSV vs Supabase: {e}")
            return {"comparison": "error", "error": str(e)}
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Run full portfolio analysis.
        
        Returns:
            Dictionary with complete analysis
        """
        print_header(f"🔍 FULL PORTFOLIO ANALYSIS: {self.fund_name}")
        
        results = {
            "fund_name": self.fund_name,
            "timestamp": datetime.now(timezone.utc),
            "trade_analysis": {},
            "pnl_summary": {},
            "comparison": {}
        }
        
        # Analyze trades
        results["trade_analysis"] = self.analyze_trades()
        
        # Calculate P&L
        results["pnl_summary"] = self.calculate_pnl_summary()
        
        # Compare repositories
        results["comparison"] = self.compare_csv_vs_supabase()
        
        print_success("✅ Full portfolio analysis completed")
        return results

def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Portfolio calculation debug utilities")
    parser.add_argument("--fund", required=True, help="Fund name to analyze")
    parser.add_argument("--action", required=True,
                       choices=["analyze-trades", "calculate-pnl", "compare-repos", "full-analysis"],
                       help="Action to perform")
    
    args = parser.parse_args()
    
    # Create portfolio debugger
    debugger = PortfolioDebugger(args.fund)
    
    if args.action == "analyze-trades":
        debugger.analyze_trades()
    elif args.action == "calculate-pnl":
        debugger.calculate_pnl_summary()
    elif args.action == "compare-repos":
        debugger.compare_csv_vs_supabase()
    elif args.action == "full-analysis":
        debugger.run_full_analysis()

if __name__ == "__main__":
    main()
'''
    
    # Write the utility file
    utility_path = Path("debug/portfolio_debug_utilities.py")
    utility_path.write_text(utility_code, encoding='utf-8')
    
    print_success("✅ Created portfolio debug utilities")
    print_info(f"   File: {utility_path}")
    print_info("   Usage: python debug/portfolio_debug_utilities.py --fund <fund_name> --action <action>")

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create test fund with historical data")
    parser.add_argument("--fund", default="TEST_FUND_A", help="Name of the test fund")
    parser.add_argument("--data-dir", default="trading_data/funds/TEST", help="Base data directory")
    parser.add_argument("--create-structure", action="store_true", help="Create fund directory structure")
    parser.add_argument("--add-trades", action="store_true", help="Add historical trades")
    parser.add_argument("--calculate-portfolio", action="store_true", help="Calculate portfolio positions")
    parser.add_argument("--create-utilities", action="store_true", help="Create debug utilities")
    parser.add_argument("--all", action="store_true", help="Run all operations")
    
    args = parser.parse_args()
    
    if args.all:
        args.create_structure = True
        args.add_trades = True
        args.calculate_portfolio = True
        args.create_utilities = True
    
    print_header(f"🧪 CREATING TEST FUND: {args.fund}")
    
    success = True
    
    if args.create_structure:
        print_info("1. Creating fund structure...")
        if not create_test_fund_structure(args.fund, args.data_dir):
            success = False
    
    if args.add_trades:
        print_info("2. Adding historical trades...")
        if not add_historical_trades(args.fund, args.data_dir):
            success = False
    
    if args.calculate_portfolio:
        print_info("3. Calculating portfolio positions...")
        if not calculate_portfolio_positions(args.fund, args.data_dir):
            success = False
    
    if args.create_utilities:
        print_info("4. Creating debug utilities...")
        create_portfolio_debug_utilities()
    
    if success:
        print_success("✅ Test fund creation completed successfully")
    else:
        print_error("❌ Some operations failed")

if __name__ == "__main__":
    main()
