"""
Calculate Portfolio Positions from Trades

This script calculates portfolio positions and P&L from trade history,
creating proper portfolio snapshots.
"""

import sys
from pathlib import Path
sys.path.append('.')

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Any, Optional
from debug.database_operations import DatabaseOperations
from data.models.portfolio import Position, PortfolioSnapshot
from display.console_output import print_header, print_info, print_success, print_warning, print_error

def calculate_positions_from_trades(fund_name: str) -> Dict[str, Any]:
    """Calculate portfolio positions from trade history.
    
    Args:
        fund_name: Name of the fund
        
    Returns:
        Dictionary with calculated positions
    """
    print_info(f"Calculating positions from trades for fund: {fund_name}")
    
    try:
        # Create database operations instance
        db_ops = DatabaseOperations(fund_name)
        
        # Get all trades
        trades = db_ops.supabase_repo.get_trade_history()
        
        if not trades:
            print_warning("No trades found")
            return {"positions": [], "trades": []}
        
        print_info(f"Found {len(trades)} trades")
        
        # Group trades by ticker
        ticker_trades = {}
        for trade in trades:
            ticker = trade.ticker
            if ticker not in ticker_trades:
                ticker_trades[ticker] = []
            ticker_trades[ticker].append(trade)
        
        # Calculate positions for each ticker
        positions = []
        for ticker, ticker_trade_list in ticker_trades.items():
            print_info(f"\nProcessing {ticker}:")
            
            # Calculate totals
            total_buy_shares = Decimal('0')
            total_sell_shares = Decimal('0')
            total_buy_cost = Decimal('0')
            total_sell_proceeds = Decimal('0')
            
            for trade in ticker_trade_list:
                print_info(f"   {trade.action} {trade.shares} @ ${trade.price} (cost: ${trade.cost_basis or 'None'})")
                
                if trade.action == "BUY":
                    total_buy_shares += trade.shares
                    # Calculate cost basis if not provided
                    if trade.cost_basis is None:
                        trade_cost = trade.shares * trade.price
                        print_info(f"      Calculated cost basis: ${trade_cost}")
                    else:
                        trade_cost = trade.cost_basis
                    total_buy_cost += trade_cost
                elif trade.action == "SELL":
                    total_sell_shares += trade.shares
                    if trade.cost_basis is None:
                        trade_proceeds = trade.shares * trade.price
                        print_info(f"      Calculated proceeds: ${trade_proceeds}")
                    else:
                        trade_proceeds = trade.cost_basis
                    total_sell_proceeds += trade_proceeds
            
            # Calculate current position
            current_shares = total_buy_shares - total_sell_shares
            total_cost_basis = total_buy_cost - total_sell_proceeds
            
            if current_shares > 0:
                avg_price = total_cost_basis / current_shares
                print_info(f"   Current Shares: {current_shares}")
                print_info(f"   Total Cost Basis: ${total_cost_basis}")
                print_info(f"   Average Price: ${avg_price}")
                
                # Create position (we'll use current price as avg_price for now)
                position = Position(
                    ticker=ticker,
                    shares=current_shares,
                    avg_price=avg_price,
                    cost_basis=total_cost_basis,
                    currency=ticker_trade_list[0].currency,
                    company=f"{ticker} Company",  # Placeholder
                    current_price=avg_price,  # Use avg_price as current price
                    market_value=current_shares * avg_price,
                    unrealized_pnl=Decimal('0')  # No unrealized P&L since current_price = avg_price
                )
                
                positions.append(position)
                print_success(f"   Created position: {current_shares} shares @ ${avg_price}")
            else:
                print_info(f"   No current position (all shares sold)")
        
        print_success(f"Calculated {len(positions)} positions")
        return {"positions": positions, "trades": trades}
        
    except Exception as e:
        print_error(f"Failed to calculate positions: {e}")
        return {"positions": [], "trades": [], "error": str(e)}

def create_portfolio_snapshot(fund_name: str, positions: List[Position]) -> bool:
    """Create a portfolio snapshot from calculated positions.
    
    Args:
        fund_name: Name of the fund
        positions: List of positions
        
    Returns:
        True if successful, False otherwise
    """
    print_info(f"Creating portfolio snapshot for fund: {fund_name}")
    
    try:
        # Create database operations instance
        db_ops = DatabaseOperations(fund_name)
        
        if not positions:
            print_warning("No positions to create snapshot")
            return False
        
        # Calculate total value
        total_value = sum(pos.market_value or Decimal('0') for pos in positions)
        
        # Create snapshot
        snapshot = PortfolioSnapshot(
            positions=positions,
            timestamp=datetime.now(timezone.utc),
            total_value=total_value
        )
        
        # Save snapshot
        db_ops.supabase_repo.save_portfolio_snapshot(snapshot)
        
        print_success(f"Created portfolio snapshot with {len(positions)} positions")
        print_info(f"Total portfolio value: ${total_value}")
        
        return True
        
    except Exception as e:
        print_error(f"Failed to create portfolio snapshot: {e}")
        return False

def run_full_portfolio_calculation(fund_name: str) -> Dict[str, Any]:
    """Run full portfolio calculation from trades.
    
    Args:
        fund_name: Name of the fund
        
    Returns:
        Dictionary with calculation results
    """
    print_header(f"FULL PORTFOLIO CALCULATION: {fund_name}")
    
    results = {
        "fund_name": fund_name,
        "timestamp": datetime.now(timezone.utc),
        "positions": [],
        "snapshot_created": False,
        "errors": []
    }
    
    # Calculate positions from trades
    position_results = calculate_positions_from_trades(fund_name)
    results["positions"] = position_results.get("positions", [])
    
    if "error" in position_results:
        results["errors"].append(position_results["error"])
        return results
    
    # Create portfolio snapshot
    if results["positions"]:
        snapshot_created = create_portfolio_snapshot(fund_name, results["positions"])
        results["snapshot_created"] = snapshot_created
        
        if snapshot_created:
            print_success("Portfolio calculation completed successfully")
        else:
            results["errors"].append("Failed to create portfolio snapshot")
    else:
        print_warning("No positions to create snapshot")
    
    return results

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Calculate portfolio positions from trades")
    parser.add_argument("--fund", required=True, help="Fund name to calculate")
    parser.add_argument("--action", required=True,
                       choices=["calculate-positions", "create-snapshot", "full-calculation"],
                       help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "calculate-positions":
        calculate_positions_from_trades(args.fund)
    elif args.action == "create-snapshot":
        # This would require positions to be passed, so we'll do full calculation
        run_full_portfolio_calculation(args.fund)
    elif args.action == "full-calculation":
        run_full_portfolio_calculation(args.fund)

if __name__ == "__main__":
    main()
