#!/usr/bin/env python3
"""
Test script to debug 1-day P&L calculation issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from portfolio.portfolio_manager import PortfolioManager
from data.repositories.csv_repository import CSVRepository
from portfolio.fund_manager import Fund, RepositorySettings

def test_portfolio_snapshots():
    """Test loading portfolio snapshots and check their data."""
    print("🔍 Testing portfolio snapshots...")

    try:
        # Create a simple fund for testing
        dev_fund = Fund(
            id="dev",
            name="Development Fund",
            description="Development and testing fund",
            repository=RepositorySettings(type="csv", settings={"directory": "trading_data/funds/TEST"})
        )

        print(f"📁 Using fund: {dev_fund.name}")
        fund_data_dir = f"trading_data/funds/{dev_fund.name}"
        print(f"📁 Repository directory: {fund_data_dir}")

        # Initialize portfolio manager
        repo = CSVRepository(fund_data_dir)
        pm = PortfolioManager(repo, dev_fund)

        # Load portfolio snapshots
        snapshots = pm.load_portfolio()
        print(f"📊 Found {len(snapshots)} snapshots")

        if not snapshots:
            print("❌ No portfolio snapshots found")
            return

        # Print details about each snapshot
        for i, snapshot in enumerate(snapshots):
            print(f"📅 Snapshot {i}: {snapshot.timestamp} - {len(snapshot.positions)} positions")

            for pos in snapshot.positions:
                print(f"   📈 {pos.ticker}: {pos.current_price} (shares: {pos.shares})")

        # Test the 1-day P&L calculation logic
        if len(snapshots) >= 2:
            print("\n🔍 Testing 1-day P&L logic...")
            latest = snapshots[-1]
            previous = snapshots[-2]

            print(f"📊 Latest snapshot: {latest.timestamp}")
            print(f"📊 Previous snapshot: {previous.timestamp}")

            # Find common tickers
            latest_tickers = {pos.ticker for pos in latest.positions}
            prev_tickers = {pos.ticker for pos in previous.positions}
            common_tickers = latest_tickers.intersection(prev_tickers)

            print(f"🔗 Common tickers: {common_tickers}")

            for ticker in common_tickers:
                # Find positions in both snapshots
                latest_pos = next(pos for pos in latest.positions if pos.ticker == ticker)
                prev_pos = next(pos for pos in previous.positions if pos.ticker == ticker)

                if latest_pos.current_price and prev_pos.current_price:
                    price_change = latest_pos.current_price - prev_pos.current_price
                    daily_pnl = price_change * latest_pos.shares
                    print(f"   💰 {ticker}: ${daily_pnl:.2f} ({price_change:.2f} per share)")
                else:
                    print(f"   ❌ {ticker}: Missing price data")

        else:
            print("❌ Need at least 2 snapshots for 1-day P&L calculation")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_portfolio_snapshots()
