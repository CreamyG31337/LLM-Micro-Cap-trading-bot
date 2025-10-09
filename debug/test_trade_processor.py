#!/usr/bin/env python3
"""Test script to debug trade processor functionality."""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.repositories.csv_repository import CSVRepository
from portfolio.trade_processor import TradeProcessor
from data.models.trade import Trade
from utils.timezone_utils import get_current_trading_time

def test_trade_processor():
    """Test the trade processor with a simple buy trade."""
    print("🧪 Testing Trade Processor...")
    
    # Initialize repository
    data_dir = "trading_data/funds/TEST"
    repository = CSVRepository(data_dir)
    
    # Initialize trade processor
    processor = TradeProcessor(repository)
    
    # Create a test trade
    test_trade = Trade(
        ticker="TEST5",
        action="BUY",
        shares=Decimal("10"),
        price=Decimal("100.00"),
        timestamp=get_current_trading_time(),
        cost_basis=Decimal("1000.00"),
        reason="TEST TRADE",
        currency="CAD"
    )
    
    print(f"📊 Test trade: {test_trade.ticker} {test_trade.shares} @ {test_trade.price}")
    
    # Check current portfolio state
    print("\n📋 Current portfolio state:")
    latest_snapshot = repository.get_latest_portfolio_snapshot()
    if latest_snapshot:
        print(f"   Latest snapshot: {len(latest_snapshot.positions)} positions")
        for pos in latest_snapshot.positions:
            if pos.ticker == "TEST5":
                print(f"   TEST5: {pos.shares} shares @ {pos.avg_price}")
    else:
        print("   No existing portfolio snapshot")
    
    # Execute the trade
    print(f"\n🔄 Executing trade...")
    try:
        executed_trade = processor.execute_buy_trade(
            ticker=test_trade.ticker,
            shares=test_trade.shares,
            price=test_trade.price,
            reason=test_trade.reason,
            currency=test_trade.currency,
            validate_funds=False  # Skip fund validation for testing
        )
        print(f"✅ Trade executed successfully: {executed_trade.ticker}")
    except Exception as e:
        print(f"❌ Trade execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check portfolio state after trade
    print("\n📋 Portfolio state after trade:")
    latest_snapshot = repository.get_latest_portfolio_snapshot()
    if latest_snapshot:
        print(f"   Latest snapshot: {len(latest_snapshot.positions)} positions")
        for pos in latest_snapshot.positions:
            if pos.ticker == "TEST5":
                print(f"   TEST5: {pos.shares} shares @ {pos.avg_price} (cost: {pos.cost_basis})")
    else:
        print("   No portfolio snapshot found after trade")
    
    # Check trade log
    print("\n📝 Trade log:")
    trades = repository.get_trade_history()
    test_trades = [t for t in trades if t.ticker == "TEST5"]
    print(f"   Found {len(test_trades)} TEST5 trades in log")
    for trade in test_trades[-2:]:  # Show last 2
        print(f"   {trade.timestamp}: {trade.action} {trade.shares} @ {trade.price}")
    
    return True

if __name__ == "__main__":
    test_trade_processor()
