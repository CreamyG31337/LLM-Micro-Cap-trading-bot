#!/usr/bin/env python3
"""
Debug script to investigate the average cost calculation issue.
"""

import tempfile
from pathlib import Path
from decimal import Decimal
from data.repositories.csv_repository import CSVRepository
from portfolio.trade_processor import TradeProcessor

def debug_average_cost_issue():
    """Debug the average cost calculation issue."""
    print("=== Average Cost Debug Session ===")
    
    # Create temporary repository
    data_dir = Path(tempfile.mkdtemp())
    repo = CSVRepository(data_directory=str(data_dir))
    processor = TradeProcessor(repo)
    
    ticker = "TEST"
    
    print(f"\n1. Execute first buy: 100 shares @ $100")
    trade1 = processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Buy 1")
    print(f"   Trade 1 - Cost Basis: ${trade1.cost_basis}")
    
    # Check position after first trade
    snapshot1 = repo.get_latest_portfolio_snapshot()
    if snapshot1:
        position1 = snapshot1.get_position_by_ticker(ticker)
        if position1:
            print(f"   Position after trade 1:")
            print(f"     Shares: {position1.shares}")
            print(f"     Avg Price: ${position1.avg_price}")
            print(f"     Cost Basis: ${position1.cost_basis}")
        else:
            print("   ERROR: No position found after trade 1")
    else:
        print("   ERROR: No snapshot found after trade 1")
    
    print(f"\n2. Execute second buy: 100 shares @ $120")
    trade2 = processor.execute_buy_trade(ticker, Decimal('100'), Decimal('120'), "Buy 2")
    print(f"   Trade 2 - Cost Basis: ${trade2.cost_basis}")
    
    # Check position after second trade
    snapshot2 = repo.get_latest_portfolio_snapshot()
    if snapshot2:
        position2 = snapshot2.get_position_by_ticker(ticker)
        if position2:
            print(f"   Position after trade 2:")
            print(f"     Shares: {position2.shares}")
            print(f"     Avg Price: ${position2.avg_price}")
            print(f"     Cost Basis: ${position2.cost_basis}")
            
            # Manual calculation check
            expected_shares = Decimal('200')
            expected_cost_basis = Decimal('22000')  # 100*100 + 100*120
            expected_avg_price = expected_cost_basis / expected_shares  # 22000/200 = 110
            
            print(f"   Expected calculations:")
            print(f"     Expected Shares: {expected_shares}")
            print(f"     Expected Cost Basis: ${expected_cost_basis}")
            print(f"     Expected Avg Price: ${expected_avg_price}")
            
            if position2.avg_price == expected_avg_price:
                print("   ✅ Average price calculation is CORRECT")
            else:
                print("   ❌ Average price calculation is WRONG")
        else:
            print("   ERROR: No position found after trade 2")
    else:
        print("   ERROR: No snapshot found after trade 2")
    
    print(f"\n3. Execute sell: 100 shares @ $130")
    trade3 = processor.execute_sell_trade(ticker, Decimal('100'), Decimal('130'), "Sell")
    print(f"   Trade 3 - P&L: ${trade3.pnl}")
    print(f"   Trade 3 - Cost Basis: ${trade3.cost_basis}")
    
    # Expected P&L calculation
    if snapshot2 and snapshot2.get_position_by_ticker(ticker):
        position_before_sell = snapshot2.get_position_by_ticker(ticker)
        expected_cost_per_share = position_before_sell.avg_price
        expected_cost_basis = expected_cost_per_share * Decimal('100')
        expected_proceeds = Decimal('130') * Decimal('100')
        expected_pnl = expected_proceeds - expected_cost_basis
        
        print(f"   Expected P&L calculation:")
        print(f"     Avg cost per share: ${expected_cost_per_share}")
        print(f"     Expected cost basis: ${expected_cost_basis}")
        print(f"     Expected proceeds: ${expected_proceeds}")
        print(f"     Expected P&L: ${expected_pnl}")
        
        if trade3.pnl == expected_pnl:
            print("   ✅ P&L calculation is CORRECT")
        else:
            print("   ❌ P&L calculation is WRONG")
    
    # Check final position
    snapshot3 = repo.get_latest_portfolio_snapshot()
    if snapshot3:
        position3 = snapshot3.get_position_by_ticker(ticker)
        if position3:
            print(f"   Final position after sell:")
            print(f"     Shares: {position3.shares}")
            print(f"     Avg Price: ${position3.avg_price}")
            print(f"     Cost Basis: ${position3.cost_basis}")
        else:
            print("   No position remaining (sold everything)")
    
    # Cleanup
    import shutil
    shutil.rmtree(data_dir)
    
    print("\n=== Debug Session Complete ===")

if __name__ == "__main__":
    debug_average_cost_issue()