"""
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
        print_info(f"Analyzing trades for fund: {self.fund_name}")
        
        try:
            # Get trades
            trades = self.db_ops.supabase_repo.get_trade_history()
            
            if not trades:
                print_warning("No trades found")
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
                    analysis["total_buy_cost"] += trade.cost_basis or Decimal('0')
                elif trade.action == "SELL":
                    analysis["total_sell_shares"] += trade.shares
                    analysis["total_sell_proceeds"] += trade.cost_basis or Decimal('0')
            
            # Calculate current positions
            for ticker, analysis in ticker_analysis.items():
                analysis["current_shares"] = analysis["total_buy_shares"] - analysis["total_sell_shares"]
                analysis["total_cost_basis"] = analysis["total_buy_cost"] - analysis["total_sell_proceeds"]
                
                if analysis["current_shares"] > 0:
                    analysis["avg_price"] = analysis["total_cost_basis"] / analysis["current_shares"]
                else:
                    analysis["avg_price"] = Decimal('0')
            
            print_success(f"Analyzed {len(trades)} trades across {len(ticker_analysis)} tickers")
            
            # Display analysis
            for ticker, analysis in ticker_analysis.items():
                print_info(f"\n{ticker}:")
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
            print_error(f"Failed to analyze trades: {e}")
            return {"trades": [], "analysis": {}, "error": str(e)}
    
    def calculate_pnl_summary(self) -> Dict[str, Any]:
        """Calculate P&L summary for the fund.
        
        Returns:
            Dictionary with P&L summary
        """
        print_info(f"Calculating P&L summary for fund: {self.fund_name}")
        
        try:
            # Get portfolio data
            snapshots = self.db_ops.supabase_repo.get_portfolio_data()
            
            if not snapshots:
                print_warning("No portfolio snapshots found")
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
            
            print_success("P&L summary calculated")
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
            print_error(f"Failed to calculate P&L summary: {e}")
            return {"snapshots": [], "pnl_summary": {}, "error": str(e)}
    
    def compare_csv_vs_supabase(self) -> Dict[str, Any]:
        """Compare CSV vs Supabase data consistency.
        
        Returns:
            Dictionary with comparison results
        """
        print_info(f"Comparing CSV vs Supabase for fund: {self.fund_name}")
        
        try:
            # This would require implementing CSV repository access
            # For now, we'll just show the Supabase data
            print_info("Supabase data:")
            self.db_ops.list_fund_data()
            
            print_warning("CSV comparison not implemented yet")
            print_info("   This would require CSV repository access")
            
            return {"comparison": "not_implemented"}
            
        except Exception as e:
            print_error(f"Failed to compare CSV vs Supabase: {e}")
            return {"comparison": "error", "error": str(e)}
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Run full portfolio analysis.
        
        Returns:
            Dictionary with complete analysis
        """
        print_header(f"FULL PORTFOLIO ANALYSIS: {self.fund_name}")
        
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
        
        print_success("Full portfolio analysis completed")
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
