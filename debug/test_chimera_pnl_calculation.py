#!/usr/bin/env python3
"""Test daily P&L calculation with real Project Chimera data."""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

from data.repositories.csv_repository import CSVRepository
from financial.pnl_calculator import calculate_daily_pnl_from_snapshots

def main():
    data_dir = Path("trading_data/funds/Project Chimera")
    repository = CSVRepository(data_dir)
    
    # Load all snapshots from CSV
    snapshots = repository.get_portfolio_data()
    
    print(f"=== SNAPSHOTS LOADED ===")
    print(f"Total snapshots: {len(snapshots)}")
    
    if len(snapshots) > 0:
        print(f"\nSnapshot dates:")
        for i, snap in enumerate(snapshots):
            print(f"  [{i}] {snap.timestamp.date()} - {len(snap.positions)} positions")
        
        # Get the latest snapshot (should be Monday Sept 29)
        latest_snapshot = snapshots[-1]
        print(f"\n=== LATEST SNAPSHOT ===")
        print(f"Date: {latest_snapshot.timestamp}")
        print(f"Positions: {len(latest_snapshot.positions)}")
        
        # Test with CTRN
        ctrn_position = None
        for pos in latest_snapshot.positions:
            if pos.ticker == 'CTRN':
                ctrn_position = pos
                break
        
        if ctrn_position:
            print(f"\n=== TESTING CTRN ===")
            print(f"Current price: ${ctrn_position.current_price}")
            print(f"Shares: {ctrn_position.shares}")
            print(f"Avg price: ${ctrn_position.avg_price}")
            
            # Check previous snapshots for CTRN
            print(f"\n=== CTRN PRICE HISTORY ===")
            for i, snap in enumerate(snapshots[-5:]):  # Last 5 snapshots
                for pos in snap.positions:
                    if pos.ticker == 'CTRN':
                        print(f"  [{len(snapshots)-5+i}] {snap.timestamp.date()}: ${pos.current_price}")
                        break
            
            # Calculate daily P&L
            print(f"\n=== CALCULATING DAILY P&L ===")
            daily_pnl = calculate_daily_pnl_from_snapshots(ctrn_position, snapshots)
            print(f"Result: {daily_pnl}")
            
            # Manual calculation
            if len(snapshots) >= 2:
                prev_snapshot = snapshots[-2]
                prev_ctrn = None
                for pos in prev_snapshot.positions:
                    if pos.ticker == 'CTRN':
                        prev_ctrn = pos
                        break
                
                if prev_ctrn:
                    price_change = ctrn_position.current_price - prev_ctrn.current_price
                    pnl_amount = price_change * ctrn_position.shares
                    print(f"\n=== MANUAL CALCULATION ===")
                    print(f"Previous price (${prev_snapshot.timestamp.date()}): ${prev_ctrn.current_price}")
                    print(f"Current price: ${ctrn_position.current_price}")
                    print(f"Price change: ${price_change}")
                    print(f"Shares: {ctrn_position.shares}")
                    print(f"Expected P&L: ${pnl_amount:.2f}")

if __name__ == "__main__":
    main()