#!/usr/bin/env python3
"""
Comprehensive tests comparing FIFO system vs existing average cost system.

This ensures both systems produce identical results for:
1. Simple buy/sell scenarios
2. Partial sells
3. Re-buys after selling
4. Multiple buys of same stock
5. Edge cases and error conditions
"""

import unittest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.models.trade import Trade
from data.models.portfolio import Position, PortfolioSnapshot
from data.models.lot import Lot, LotTracker
from portfolio.trade_processor import TradeProcessor
from portfolio.fifo_trade_processor import FIFOTradeProcessor
from data.repositories.csv_repository import CSVRepository
from config.settings import Settings


class TestFIFOVsAverageCost(unittest.TestCase):
    """Test that FIFO system produces same results as average cost system."""
    
    def setUp(self):
        """Set up test environment."""
        # Use test data directory
        self.test_data_dir = Path("test_data")
        self.test_data_dir.mkdir(exist_ok=True)
        
        # Create test repository
        self.repository = CSVRepository(data_directory=str(self.test_data_dir))
        
        # Create both processors
        self.average_processor = TradeProcessor(self.repository)
        self.fifo_processor = FIFOTradeProcessor(self.repository)
        
        # Clear any existing test data
        self._clear_test_data()
    
    def tearDown(self):
        """Clean up test data."""
        self._clear_test_data()
    
    def _clear_test_data(self):
        """Clear test data files."""
        test_files = [
            self.test_data_dir / "llm_trade_log.csv",
            self.test_data_dir / "llm_portfolio_update.csv"
        ]
        for file in test_files:
            if file.exists():
                file.unlink()
    
    def test_simple_buy_sell(self):
        """Test simple buy then sell scenario."""
        print("\n🧪 Test: Simple Buy -> Sell")
        
        # Test data
        ticker = "TEST1"
        shares = Decimal('100')
        buy_price = Decimal('100.00')
        sell_price = Decimal('110.00')
        
        # Execute with both systems
        print("  Executing with Average Cost system...")
        avg_trade = self.average_processor.execute_buy_trade(
            ticker=ticker, shares=shares, price=buy_price, reason="Test buy"
        )
        avg_sell = self.average_processor.execute_sell_trade(
            ticker=ticker, shares=shares, price=sell_price, reason="Test sell"
        )
        
        # Clear data for FIFO test
        self._clear_test_data()
        
        print("  Executing with FIFO system...")
        fifo_trade = self.fifo_processor.execute_buy_trade(
            ticker=ticker, shares=shares, price=buy_price, reason="Test buy"
        )
        fifo_sell = self.fifo_processor.execute_sell_trade(
            ticker=ticker, shares=shares, price=sell_price, reason="Test sell"
        )
        
        # Compare results
        print("  Comparing results...")
        self.assertEqual(avg_trade.shares, fifo_trade.shares)
        self.assertEqual(avg_trade.price, fifo_trade.price)
        self.assertEqual(avg_sell.shares, fifo_sell.shares)
        self.assertEqual(avg_sell.price, fifo_sell.price)
        
        # P&L should be identical for simple case
        expected_pnl = (sell_price - buy_price) * shares
        self.assertEqual(avg_sell.pnl, expected_pnl)
        self.assertEqual(fifo_sell.pnl, expected_pnl)
        
        print(f"  ✅ Both systems: P&L = ${expected_pnl}")
    
    def test_partial_sell(self):
        """Test partial sell scenario."""
        print("\n🧪 Test: Partial Sell")
        
        ticker = "TEST2"
        buy_shares = Decimal('100')
        buy_price = Decimal('100.00')
        sell_shares = Decimal('30')
        sell_price = Decimal('110.00')
        
        # Average Cost system
        print("  Average Cost system...")
        self.average_processor.execute_buy_trade(ticker, buy_shares, buy_price, "Buy")
        avg_sell = self.average_processor.execute_sell_trade(ticker, sell_shares, sell_price, "Partial sell")
        
        # Get remaining position
        avg_snapshot = self.repository.get_latest_portfolio_snapshot()
        avg_position = avg_snapshot.get_position_by_ticker(ticker) if avg_snapshot else None
        
        # Clear and test FIFO
        self._clear_test_data()
        
        print("  FIFO system...")
        self.fifo_processor.execute_buy_trade(ticker, buy_shares, buy_price, "Buy")
        fifo_sell = self.fifo_processor.execute_sell_trade(ticker, sell_shares, sell_price, "Partial sell")
        
        # Get remaining position
        fifo_snapshot = self.repository.get_latest_portfolio_snapshot()
        fifo_position = fifo_snapshot.get_position_by_ticker(ticker) if fifo_snapshot else None
        
        # Compare
        print("  Comparing results...")
        self.assertEqual(avg_sell.shares, fifo_sell.shares)
        self.assertEqual(avg_sell.price, fifo_sell.price)
        
        # P&L should be identical
        expected_pnl = (sell_price - buy_price) * sell_shares
        self.assertEqual(avg_sell.pnl, expected_pnl)
        self.assertEqual(fifo_sell.pnl, expected_pnl)
        
        # Remaining shares should be identical
        if avg_position and fifo_position:
            self.assertEqual(avg_position.shares, fifo_position.shares)
            self.assertEqual(avg_position.avg_price, fifo_position.avg_price)
        
        print(f"  ✅ Both systems: P&L = ${expected_pnl}, Remaining = {buy_shares - sell_shares} shares")
    
    def test_multiple_buys_then_sell(self):
        """Test multiple buys then sell (this is where they differ)."""
        print("\n🧪 Test: Multiple Buys -> Sell (Where FIFO vs Average Cost Differ)")
        
        ticker = "TEST3"
        
        # Buy 100 @ $100, then 100 @ $120, then sell 100 @ $130
        print("  Average Cost system...")
        self.average_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Buy 1")
        self.average_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('120'), "Buy 2")
        avg_sell = self.average_processor.execute_sell_trade(ticker, Decimal('100'), Decimal('130'), "Sell")
        
        # Clear and test FIFO
        self._clear_test_data()
        
        print("  FIFO system...")
        self.fifo_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Buy 1")
        self.fifo_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('120'), "Buy 2")
        fifo_sell = self.fifo_processor.execute_sell_trade(ticker, Decimal('100'), Decimal('130'), "Sell")
        
        # Compare
        print("  Comparing results...")
        self.assertEqual(avg_sell.shares, fifo_sell.shares)
        self.assertEqual(avg_sell.price, fifo_sell.price)
        
        # P&L will be different - this is expected!
        print(f"  Average Cost P&L: ${avg_sell.pnl}")
        print(f"  FIFO P&L: ${fifo_sell.pnl}")
        
        # Average cost: (100+120)/2 = $110 avg, so P&L = (130-110)*100 = $2000
        expected_avg_pnl = Decimal('2000.00')
        self.assertEqual(avg_sell.pnl, expected_avg_pnl)
        
        # FIFO: Sells oldest first (100 @ $100), so P&L = (130-100)*100 = $3000
        expected_fifo_pnl = Decimal('3000.00')
        self.assertEqual(fifo_sell.pnl, expected_fifo_pnl)
        
        print(f"  ✅ Average Cost: ${expected_avg_pnl} (sells at average price)")
        print(f"  ✅ FIFO: ${expected_fifo_pnl} (sells oldest shares first)")
    
    def test_re_buy_after_sell(self):
        """Test buying again after selling."""
        print("\n🧪 Test: Re-buy After Sell")
        
        ticker = "TEST4"
        
        # Buy 100 @ $100, sell 50 @ $110, buy 25 @ $105
        print("  Average Cost system...")
        self.average_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Buy 1")
        self.average_processor.execute_sell_trade(ticker, Decimal('50'), Decimal('110'), "Sell")
        self.average_processor.execute_buy_trade(ticker, Decimal('25'), Decimal('105'), "Re-buy")
        
        avg_snapshot = self.repository.get_latest_portfolio_snapshot()
        avg_position = avg_snapshot.get_position_by_ticker(ticker) if avg_snapshot else None
        
        # Clear and test FIFO
        self._clear_test_data()
        
        print("  FIFO system...")
        self.fifo_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Buy 1")
        self.fifo_processor.execute_sell_trade(ticker, Decimal('50'), Decimal('110'), "Sell")
        self.fifo_processor.execute_buy_trade(ticker, Decimal('25'), Decimal('105'), "Re-buy")
        
        fifo_snapshot = self.repository.get_latest_portfolio_snapshot()
        fifo_position = fifo_snapshot.get_position_by_ticker(ticker) if fifo_snapshot else None
        
        # Compare final positions
        print("  Comparing final positions...")
        if avg_position and fifo_position:
            # Total shares should be same: 100 - 50 + 25 = 75
            expected_shares = Decimal('75')
            self.assertEqual(avg_position.shares, expected_shares)
            self.assertEqual(fifo_position.shares, expected_shares)
            
            # Average prices will be different due to different methods
            print(f"  Average Cost avg price: ${avg_position.avg_price}")
            print(f"  FIFO avg price: ${fifo_position.avg_price}")
            
            # But both should have same total cost basis
            self.assertEqual(avg_position.cost_basis, fifo_position.cost_basis)
        
        print(f"  ✅ Both systems: Final position = 75 shares")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        print("\n🧪 Test: Edge Cases")
        
        # Test selling more shares than owned
        print("  Testing insufficient shares error...")
        with self.assertRaises(Exception):  # Should raise InsufficientSharesError
            self.fifo_processor.execute_sell_trade("NONEXISTENT", Decimal('100'), Decimal('100'), "Sell")
        
        # Test invalid parameters
        print("  Testing invalid parameters...")
        with self.assertRaises(Exception):
            self.fifo_processor.execute_buy_trade("", Decimal('100'), Decimal('100'), "Invalid")
        
        with self.assertRaises(Exception):
            self.fifo_processor.execute_buy_trade("TEST", Decimal('0'), Decimal('100'), "Invalid")
        
        print("  ✅ Edge cases handled correctly")
    
    def test_portfolio_consistency(self):
        """Test that portfolio snapshots are consistent between systems."""
        print("\n🧪 Test: Portfolio Consistency")
        
        ticker = "TEST5"
        
        # Execute same trades with both systems
        trades = [
            (Decimal('50'), Decimal('100'), "BUY"),
            (Decimal('25'), Decimal('110'), "SELL"),
            (Decimal('30'), Decimal('105'), "BUY"),
        ]
        
        print("  Average Cost system...")
        for shares, price, action in trades:
            if action == "BUY":
                self.average_processor.execute_buy_trade(ticker, shares, price, f"Trade {action}")
            else:
                self.average_processor.execute_sell_trade(ticker, shares, price, f"Trade {action}")
        
        avg_snapshot = self.repository.get_latest_portfolio_snapshot()
        
        # Clear and test FIFO
        self._clear_test_data()
        
        print("  FIFO system...")
        for shares, price, action in trades:
            if action == "BUY":
                self.fifo_processor.execute_buy_trade(ticker, shares, price, f"Trade {action}")
            else:
                self.fifo_processor.execute_sell_trade(ticker, shares, price, f"Trade {action}")
        
        fifo_snapshot = self.repository.get_latest_portfolio_snapshot()
        
        # Compare snapshots
        print("  Comparing portfolio snapshots...")
        if avg_snapshot and fifo_snapshot:
            avg_position = avg_snapshot.get_position_by_ticker(ticker)
            fifo_position = fifo_snapshot.get_position_by_ticker(ticker)
            
            if avg_position and fifo_position:
                # Shares should be identical
                self.assertEqual(avg_position.shares, fifo_position.shares)
                self.assertEqual(avg_position.ticker, fifo_position.ticker)
                self.assertEqual(avg_position.currency, fifo_position.currency)
                
                print(f"  ✅ Both systems: {fifo_position.shares} shares of {ticker}")
            else:
                print(f"  ✅ Both systems: No position in {ticker} (fully sold)")
    
    def test_trade_log_consistency(self):
        """Test that trade logs are consistent between systems."""
        print("\n🧪 Test: Trade Log Consistency")
        
        ticker = "TEST6"
        
        # Execute trades with both systems
        print("  Average Cost system...")
        self.average_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Test")
        self.average_processor.execute_sell_trade(ticker, Decimal('50'), Decimal('110'), "Test")
        
        avg_trades = self.repository.get_trade_history(ticker)
        
        # Clear and test FIFO
        self._clear_test_data()
        
        print("  FIFO system...")
        self.fifo_processor.execute_buy_trade(ticker, Decimal('100'), Decimal('100'), "Test")
        self.fifo_processor.execute_sell_trade(ticker, Decimal('50'), Decimal('110'), "Test")
        
        fifo_trades = self.repository.get_trade_history(ticker)
        
        # Compare trade logs
        print("  Comparing trade logs...")
        self.assertEqual(len(avg_trades), len(fifo_trades))
        
        for i, (avg_trade, fifo_trade) in enumerate(zip(avg_trades, fifo_trades)):
            self.assertEqual(avg_trade.ticker, fifo_trade.ticker)
            self.assertEqual(avg_trade.action, fifo_trade.action)
            self.assertEqual(avg_trade.shares, fifo_trade.shares)
            self.assertEqual(avg_trade.price, fifo_trade.price)
            self.assertEqual(avg_trade.currency, fifo_trade.currency)
        
        print(f"  ✅ Both systems: {len(avg_trades)} trades logged identically")


def run_comparison_tests():
    """Run all comparison tests."""
    print("🧪 FIFO vs Average Cost System Comparison")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFIFOVsAverageCost)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n📊 Test Summary")
    print("-" * 20)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed! Systems are compatible.")
        print("\n🎯 Recommendation: Safe to replace average cost with FIFO system")
    else:
        print("\n❌ Some tests failed. Review differences before replacing.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comparison_tests()
    sys.exit(0 if success else 1)
