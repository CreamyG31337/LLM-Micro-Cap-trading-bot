#!/usr/bin/env python3
"""Test script to debug email trade parser functionality."""

import sys
import os
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.email_trade_parser import add_trade_from_email

def test_email_trade_parser():
    """Test the email trade parser with a sample email."""
    print("🧪 Testing Email Trade Parser...")
    
    # Sample email text (similar to what user provided)
    email_text = """
Account: TFSA
Type: Market Buy
Symbol: TEST6
Shares: 5
Average price: US$50.00
Total cost: US$250.00
Time: October 06, 2025 15:00 EDT
"""
    
    print("📧 Sample email:")
    print(email_text.strip())
    
    # Test the email parser
    data_dir = "trading_data/funds/TEST"
    print(f"\n🔄 Processing email trade...")
    
    try:
        result = add_trade_from_email(email_text, data_dir)
        if result:
            print("✅ Email trade processed successfully")
        else:
            print("❌ Email trade processing failed")
            return False
    except Exception as e:
        print(f"❌ Email trade processing failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check if trade was added to log
    print("\n📝 Checking trade log...")
    from data.repositories.csv_repository import CSVRepository
    repository = CSVRepository(data_dir)
    trades = repository.get_trade_history()
    test_trades = [t for t in trades if t.ticker == "TEST6"]
    print(f"   Found {len(test_trades)} TEST6 trades in log")
    for trade in test_trades:
        print(f"   {trade.timestamp}: {trade.action} {trade.shares} @ {trade.price}")
    
    # Check if portfolio was updated
    print("\n📋 Checking portfolio...")
    latest_snapshot = repository.get_latest_portfolio_snapshot()
    if latest_snapshot:
        print(f"   Latest snapshot: {len(latest_snapshot.positions)} positions")
        test6_positions = [pos for pos in latest_snapshot.positions if pos.ticker == "TEST6"]
        if test6_positions:
            pos = test6_positions[0]
            print(f"   TEST6: {pos.shares} shares @ {pos.avg_price} (cost: {pos.cost_basis})")
        else:
            print("   ❌ TEST6 position not found in portfolio")
    else:
        print("   ❌ No portfolio snapshot found")
    
    return True

if __name__ == "__main__":
    test_email_trade_parser()
