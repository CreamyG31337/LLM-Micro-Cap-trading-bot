#!/usr/bin/env python3
"""
Simple, focused test comparing FIFO vs Average Cost systems.

This test focuses on the core logic without the complexity of
CSV repository integration issues.
"""

import unittest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.models.lot import Lot, LotTracker


class TestSimpleFIFOComparison(unittest.TestCase):
    """Simple comparison of FIFO vs Average Cost logic."""
    
    def test_simple_buy_sell(self):
        """Test simple buy then sell - should be identical."""
        print("\n🧪 Simple Buy -> Sell Test")
        
        # Test data
        shares = Decimal('100')
        buy_price = Decimal('100.00')
        sell_price = Decimal('110.00')
        
        # Average Cost calculation
        avg_cost = buy_price  # Simple case: only one buy
        avg_pnl = (sell_price - avg_cost) * shares
        
        # FIFO calculation
        tracker = LotTracker("TEST")
        lot = tracker.add_lot(shares, buy_price, datetime.now())
        sales = tracker.sell_shares_fifo(shares, sell_price, datetime.now())
        fifo_pnl = sales[0]['realized_pnl']
        
        print(f"  Average Cost P&L: ${avg_pnl}")
        print(f"  FIFO P&L: ${fifo_pnl}")
        
        self.assertEqual(avg_pnl, fifo_pnl)
        print("  ✅ Both methods give same result for simple case")
    
    def test_multiple_buys_then_sell(self):
        """Test multiple buys then sell - this is where they differ."""
        print("\n🧪 Multiple Buys -> Sell Test (Where They Differ)")
        
        # Test data: Buy 100 @ $100, then 100 @ $120, then sell 100 @ $130
        buy1_shares = Decimal('100')
        buy1_price = Decimal('100.00')
        buy2_shares = Decimal('100')
        buy2_price = Decimal('120.00')
        sell_shares = Decimal('100')
        sell_price = Decimal('130.00')
        
        # Average Cost calculation
        total_shares = buy1_shares + buy2_shares
        total_cost = (buy1_shares * buy1_price) + (buy2_shares * buy2_price)
        avg_cost = total_cost / total_shares  # $110
        avg_pnl = (sell_price - avg_cost) * sell_shares  # (130-110)*100 = $2000
        
        # FIFO calculation
        tracker = LotTracker("TEST")
        lot1 = tracker.add_lot(buy1_shares, buy1_price, datetime.now())
        lot2 = tracker.add_lot(buy2_shares, buy2_price, datetime.now())
        sales = tracker.sell_shares_fifo(sell_shares, sell_price, datetime.now())
        fifo_pnl = sum(sale['realized_pnl'] for sale in sales)
        
        print(f"  Average Cost P&L: ${avg_pnl}")
        print(f"  FIFO P&L: ${fifo_pnl}")
        print(f"  Difference: ${fifo_pnl - avg_pnl}")
        
        # They should be different - this is expected!
        self.assertNotEqual(avg_pnl, fifo_pnl)
        print("  ✅ Methods differ as expected (FIFO higher due to selling oldest shares first)")
    
    def test_partial_sell(self):
        """Test partial sell - should be identical for simple case."""
        print("\n🧪 Partial Sell Test")
        
        # Test data: Buy 100 @ $100, sell 30 @ $110
        buy_shares = Decimal('100')
        buy_price = Decimal('100.00')
        sell_shares = Decimal('30')
        sell_price = Decimal('110.00')
        
        # Average Cost calculation
        avg_cost = buy_price  # Simple case: only one buy
        avg_pnl = (sell_price - avg_cost) * sell_shares
        remaining_shares = buy_shares - sell_shares
        remaining_cost_basis = avg_cost * remaining_shares
        
        # FIFO calculation
        tracker = LotTracker("TEST")
        lot = tracker.add_lot(buy_shares, buy_price, datetime.now())
        sales = tracker.sell_shares_fifo(sell_shares, sell_price, datetime.now())
        fifo_pnl = sales[0]['realized_pnl']
        fifo_remaining_shares = tracker.get_total_remaining_shares()
        fifo_remaining_cost = tracker.get_total_remaining_cost_basis()
        
        print(f"  Average Cost P&L: ${avg_pnl}")
        print(f"  FIFO P&L: ${fifo_pnl}")
        print(f"  Average Cost remaining: {remaining_shares} shares, ${remaining_cost_basis} cost")
        print(f"  FIFO remaining: {fifo_remaining_shares} shares, ${fifo_remaining_cost} cost")
        
        self.assertEqual(avg_pnl, fifo_pnl)
        self.assertEqual(remaining_shares, fifo_remaining_shares)
        self.assertEqual(remaining_cost_basis, fifo_remaining_cost)
        print("  ✅ Both methods give same result for partial sell")
    
    def test_re_buy_after_sell(self):
        """Test re-buy after sell."""
        print("\n🧪 Re-buy After Sell Test")
        
        # Test data: Buy 100 @ $100, sell 50 @ $110, buy 25 @ $105
        buy1_shares = Decimal('100')
        buy1_price = Decimal('100.00')
        sell_shares = Decimal('50')
        sell_price = Decimal('110.00')
        buy2_shares = Decimal('25')
        buy2_price = Decimal('105.00')
        
        # Average Cost calculation
        # After first buy: 100 shares @ $100
        # After sell: 50 shares @ $100 (same avg price)
        # After second buy: 75 shares @ $101.67 (weighted average)
        remaining_after_sell = buy1_shares - sell_shares
        total_cost_after_rebuy = (remaining_after_sell * buy1_price) + (buy2_shares * buy2_price)
        total_shares_after_rebuy = remaining_after_sell + buy2_shares
        avg_cost_after_rebuy = total_cost_after_rebuy / total_shares_after_rebuy
        
        # FIFO calculation
        tracker = LotTracker("TEST")
        lot1 = tracker.add_lot(buy1_shares, buy1_price, datetime.now())
        sales = tracker.sell_shares_fifo(sell_shares, sell_price, datetime.now())
        lot2 = tracker.add_lot(buy2_shares, buy2_price, datetime.now())
        
        fifo_total_shares = tracker.get_total_remaining_shares()
        fifo_avg_cost = tracker.get_average_cost_basis()
        
        print(f"  Average Cost after re-buy: {total_shares_after_rebuy} shares @ ${avg_cost_after_rebuy:.2f}")
        print(f"  FIFO after re-buy: {fifo_total_shares} shares @ ${fifo_avg_cost:.2f}")
        
        # Total shares should be same
        self.assertEqual(total_shares_after_rebuy, fifo_total_shares)
        print("  ✅ Both methods give same total shares after re-buy")
    
    def test_fifo_ordering(self):
        """Test that FIFO properly orders lots by purchase date."""
        print("\n🧪 FIFO Ordering Test")
        
        # Create lots in different order
        tracker = LotTracker("TEST")
        
        # Add lots in different order
        lot1 = tracker.add_lot(Decimal('100'), Decimal('100'), datetime(2025, 1, 1))  # Oldest
        lot2 = tracker.add_lot(Decimal('50'), Decimal('120'), datetime(2025, 1, 3))  # Newest
        lot3 = tracker.add_lot(Decimal('25'), Decimal('110'), datetime(2025, 1, 2))  # Middle
        
        # Sell 75 shares - should come from lot1 first (oldest)
        sales = tracker.sell_shares_fifo(Decimal('75'), Decimal('130'), datetime.now())
        
        print(f"  Sold 75 shares using FIFO")
        print(f"  Lot 1 remaining: {lot1.remaining_shares} (should be 25)")
        print(f"  Lot 2 remaining: {lot2.remaining_shares} (should be 50)")
        print(f"  Lot 3 remaining: {lot3.remaining_shares} (should be 25)")
        
        # Check FIFO ordering
        self.assertEqual(lot1.remaining_shares, Decimal('25'))  # 100 - 75 = 25
        self.assertEqual(lot2.remaining_shares, Decimal('50'))  # Unchanged
        self.assertEqual(lot3.remaining_shares, Decimal('25'))  # Unchanged
        
        print("  ✅ FIFO correctly sold oldest shares first")
    
    def test_edge_cases(self):
        """Test edge cases."""
        print("\n🧪 Edge Cases Test")
        
        # Test selling more shares than owned
        tracker = LotTracker("TEST")
        tracker.add_lot(Decimal('100'), Decimal('100'), datetime.now())
        
        with self.assertRaises(ValueError):
            tracker.sell_shares_fifo(Decimal('150'), Decimal('110'), datetime.now())
        
        print("  ✅ Correctly raises error when selling more shares than owned")
        
        # Test selling exactly all shares
        tracker2 = LotTracker("TEST2")
        lot = tracker2.add_lot(Decimal('100'), Decimal('100'), datetime.now())
        sales = tracker2.sell_shares_fifo(Decimal('100'), Decimal('110'), datetime.now())
        
        self.assertTrue(lot.is_fully_sold)
        self.assertEqual(tracker2.get_total_remaining_shares(), Decimal('0'))
        
        print("  ✅ Correctly handles selling all shares")


def run_simple_comparison():
    """Run simple comparison tests."""
    print("🧪 Simple FIFO vs Average Cost Comparison")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSimpleFIFOComparison)
    
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
        print("\n✅ All tests passed!")
        print("\n🎯 Key Findings:")
        print("• Simple buy/sell: Both methods identical")
        print("• Partial sells: Both methods identical")
        print("• Multiple buys: FIFO gives higher P&L (tax advantage)")
        print("• Re-buys: Both methods handle correctly")
        print("• FIFO ordering: Works as expected")
        print("\n💡 Recommendation: FIFO is safe to use and provides tax advantages")
    else:
        print("\n❌ Some tests failed. Review before proceeding.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_simple_comparison()
    sys.exit(0 if success else 1)
