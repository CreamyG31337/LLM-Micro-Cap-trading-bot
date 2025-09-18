"""
Unit tests for financial calculations module.

Tests cover precision, edge cases, and various input types to ensure
accurate financial calculations using Decimal arithmetic.
"""

import unittest
from decimal import Decimal
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial.calculations import (
    money_to_decimal,
    calculate_cost_basis,
    calculate_position_value,
    calculate_pnl,
    round_money,
    validate_money_precision,
    calculate_percentage_change,
    calculate_weighted_average_price
)


class TestMoneyToDecimal(unittest.TestCase):
    """Test money_to_decimal function."""
    
    def test_float_input(self):
        """Test conversion from float."""
        self.assertEqual(money_to_decimal(10.99), Decimal('10.99'))
        self.assertEqual(money_to_decimal(0.01), Decimal('0.01'))
        self.assertEqual(money_to_decimal(1000.0), Decimal('1000.00'))
    
    def test_int_input(self):
        """Test conversion from int."""
        self.assertEqual(money_to_decimal(100), Decimal('100.00'))
        self.assertEqual(money_to_decimal(0), Decimal('0.00'))
        self.assertEqual(money_to_decimal(-50), Decimal('-50.00'))
    
    def test_string_input(self):
        """Test conversion from string."""
        self.assertEqual(money_to_decimal("15.75"), Decimal('15.75'))
        self.assertEqual(money_to_decimal("0.99"), Decimal('0.99'))
        self.assertEqual(money_to_decimal("1000"), Decimal('1000.00'))
    
    def test_decimal_input(self):
        """Test that Decimal input is properly rounded."""
        self.assertEqual(money_to_decimal(Decimal('10.999')), Decimal('11.00'))
        self.assertEqual(money_to_decimal(Decimal('10.994')), Decimal('10.99'))
        self.assertEqual(money_to_decimal(Decimal('10.995')), Decimal('11.00'))
    
    def test_rounding(self):
        """Test proper rounding to 2 decimal places."""
        self.assertEqual(money_to_decimal(10.999), Decimal('11.00'))
        self.assertEqual(money_to_decimal(10.994), Decimal('10.99'))
        self.assertEqual(money_to_decimal(10.995), Decimal('11.00'))
        self.assertEqual(money_to_decimal(15.555), Decimal('15.56'))
    
    def test_negative_values(self):
        """Test negative monetary values."""
        self.assertEqual(money_to_decimal(-10.99), Decimal('-10.99'))
        self.assertEqual(money_to_decimal(-0.01), Decimal('-0.01'))


class TestCalculateCostBasis(unittest.TestCase):
    """Test calculate_cost_basis function."""
    
    def test_basic_calculation(self):
        """Test basic cost basis calculation."""
        self.assertEqual(calculate_cost_basis(Decimal('10.50'), Decimal('100')), Decimal('1050.00'))
        self.assertEqual(calculate_cost_basis(Decimal('15.75'), Decimal('50')), Decimal('787.50'))
        self.assertEqual(calculate_cost_basis(Decimal('0.99'), Decimal('1000')), Decimal('990.00'))
    
    def test_decimal_precision(self):
        """Test precision with decimal inputs."""
        # 15.333 rounds to 15.33, so 15.33 * 50 = 766.50
        self.assertEqual(calculate_cost_basis(Decimal('15.333'), Decimal('50')), Decimal('766.50'))
        # 10.999 rounds to 11.00, so 11.00 * 100 = 1100.00
        self.assertEqual(calculate_cost_basis(Decimal('10.999'), Decimal('100')), Decimal('1100.00'))
    
    def test_fractional_shares(self):
        """Test with fractional shares."""
        self.assertEqual(calculate_cost_basis(Decimal('10.00'), Decimal('50.5')), Decimal('505.00'))
        self.assertEqual(calculate_cost_basis(Decimal('15.75'), Decimal('33.333')), Decimal('524.99'))
    
    def test_zero_values(self):
        """Test edge cases with zero values."""
        self.assertEqual(calculate_cost_basis(Decimal('0'), Decimal('100')), Decimal('0.00'))
        self.assertEqual(calculate_cost_basis(Decimal('10.50'), Decimal('0')), Decimal('0.00'))
        self.assertEqual(calculate_cost_basis(Decimal('0'), Decimal('0')), Decimal('0.00'))
    
    def test_mixed_input_types(self):
        """Test with mixed input types."""
        self.assertEqual(calculate_cost_basis("10.50", "100"), Decimal('1050.00'))
        self.assertEqual(calculate_cost_basis("10.50", "100"), Decimal('1050.00'))
        self.assertEqual(calculate_cost_basis(Decimal('10.50'), Decimal('100')), Decimal('1050.00'))


class TestCalculatePositionValue(unittest.TestCase):
    """Test calculate_position_value function."""
    
    def test_basic_calculation(self):
        """Test basic position value calculation."""
        self.assertEqual(calculate_position_value(Decimal('12.75'), Decimal('100')), Decimal('1275.00'))
        # 8.999 rounds to 9.00, so 9.00 * 200 = 1800.00
        self.assertEqual(calculate_position_value(Decimal('8.999'), Decimal('200')), Decimal('1800.00'))
    
    def test_identical_to_cost_basis(self):
        """Test that position value calculation is identical to cost basis."""
        price, shares = Decimal('15.75'), Decimal('100')
        self.assertEqual(
            calculate_position_value(price, shares),
            calculate_cost_basis(price, shares)
        )


class TestCalculatePnL(unittest.TestCase):
    """Test calculate_pnl function."""
    
    def test_positive_pnl(self):
        """Test positive P&L calculation."""
        self.assertEqual(calculate_pnl(Decimal('15.00'), Decimal('10.00'), Decimal('100')), Decimal('500.00'))
        self.assertEqual(calculate_pnl(Decimal('12.50'), Decimal('10.00'), Decimal('50')), Decimal('125.00'))
    
    def test_negative_pnl(self):
        """Test negative P&L calculation."""
        self.assertEqual(calculate_pnl(Decimal('8.50'), Decimal('10.00'), Decimal('100')), Decimal('-150.00'))
        self.assertEqual(calculate_pnl(Decimal('9.00'), Decimal('12.00'), Decimal('50')), Decimal('-150.00'))
    
    def test_zero_pnl(self):
        """Test zero P&L (no change in price)."""
        self.assertEqual(calculate_pnl(Decimal('10.00'), Decimal('10.00'), Decimal('100')), Decimal('0.00'))
        self.assertEqual(calculate_pnl(Decimal('15.75'), Decimal('15.75'), Decimal('200')), Decimal('0.00'))
    
    def test_fractional_shares(self):
        """Test P&L with fractional shares."""
        self.assertEqual(calculate_pnl(Decimal('11.00'), Decimal('10.00'), Decimal('50.5')), Decimal('50.50'))
        self.assertEqual(calculate_pnl(Decimal('9.00'), Decimal('10.00'), Decimal('33.333')), Decimal('-33.33'))
    
    def test_precision_with_small_differences(self):
        """Test precision with small price differences."""
        self.assertEqual(calculate_pnl(Decimal('10.01'), Decimal('10.00'), Decimal('1000')), Decimal('10.00'))
        # 9.999 rounds to 10.00, so (10.00 - 10.00) * 1000 = 0.00
        self.assertEqual(calculate_pnl(Decimal('9.999'), Decimal('10.000'), Decimal('1000')), Decimal('0.00'))


class TestRoundMoney(unittest.TestCase):
    """Test round_money function."""
    
    def test_basic_rounding(self):
        """Test basic money rounding."""
        self.assertEqual(round_money(10.999), 11.0)
        self.assertEqual(round_money(15.555), 15.56)
        self.assertEqual(round_money(10.994), 10.99)
    
    def test_return_type(self):
        """Test that return type is float."""
        result = round_money(10.99)
        self.assertIsInstance(result, float)
    
    def test_decimal_input(self):
        """Test with Decimal input."""
        self.assertEqual(round_money(Decimal('10.999')), 11.0)
        self.assertEqual(round_money(Decimal('15.555')), 15.56)


class TestValidateMoneyPrecision(unittest.TestCase):
    """Test validate_money_precision function."""
    
    def test_precise_values(self):
        """Test values that are precisely representable."""
        self.assertTrue(validate_money_precision(10.99))
        self.assertTrue(validate_money_precision(15.75))
        self.assertTrue(validate_money_precision(0.01))
    
    def test_imprecise_values(self):
        """Test values with precision issues."""
        # This should still pass due to tolerance
        self.assertTrue(validate_money_precision(10.999999999999998))
        
        # This should fail due to significant difference (more than 0.005 tolerance)
        # Use a value that when converted to decimal and back differs significantly
        imprecise_value = 10.50123456789  # This will be rounded to 10.50 in decimal
        self.assertFalse(validate_money_precision(imprecise_value, tolerance=0.001))
    
    def test_custom_tolerance(self):
        """Test with custom tolerance values."""
        self.assertTrue(validate_money_precision(10.99, tolerance=0.1))
        # Use a value that will actually fail with strict tolerance
        self.assertFalse(validate_money_precision(10.996, tolerance=0.001))


class TestCalculatePercentageChange(unittest.TestCase):
    """Test calculate_percentage_change function."""
    
    def test_positive_change(self):
        """Test positive percentage change."""
        self.assertEqual(calculate_percentage_change(100, 115), Decimal('0.1500'))
        self.assertEqual(calculate_percentage_change(50, 75), Decimal('0.5000'))
    
    def test_negative_change(self):
        """Test negative percentage change."""
        self.assertEqual(calculate_percentage_change(100, 85), Decimal('-0.1500'))
        self.assertEqual(calculate_percentage_change(200, 150), Decimal('-0.2500'))
    
    def test_zero_change(self):
        """Test zero percentage change."""
        self.assertEqual(calculate_percentage_change(100, 100), Decimal('0.0000'))
    
    def test_zero_old_value(self):
        """Test with zero old value."""
        self.assertEqual(calculate_percentage_change(0, 100), Decimal('0.0000'))
    
    def test_precision(self):
        """Test precision of percentage calculations."""
        result = calculate_percentage_change(100, 133.33)
        self.assertEqual(result, Decimal('0.3333'))


class TestCalculateWeightedAveragePrice(unittest.TestCase):
    """Test calculate_weighted_average_price function."""
    
    def test_basic_calculation(self):
        """Test basic weighted average calculation."""
        prices = [Decimal('10.00'), Decimal('12.00')]
        quantities = [Decimal('100'), Decimal('50')]
        expected = Decimal('10.67')  # (10*100 + 12*50) / (100+50) = 1600/150 = 10.67
        self.assertEqual(calculate_weighted_average_price(prices, quantities), expected)
    
    def test_equal_weights(self):
        """Test with equal quantities (simple average)."""
        prices = [Decimal('10.00'), Decimal('20.00')]
        quantities = [Decimal('100'), Decimal('100')]
        expected = Decimal('15.00')
        self.assertEqual(calculate_weighted_average_price(prices, quantities), expected)
    
    def test_single_price(self):
        """Test with single price and quantity."""
        prices = [Decimal('15.75')]
        quantities = [Decimal('100')]
        expected = Decimal('15.75')
        self.assertEqual(calculate_weighted_average_price(prices, quantities), expected)
    
    def test_multiple_prices(self):
        """Test with multiple prices and quantities."""
        prices = [Decimal('10.00'), Decimal('15.00'), Decimal('20.00')]
        quantities = [Decimal('100'), Decimal('200'), Decimal('50')]
        # (10*100 + 15*200 + 20*50) / (100+200+50) = 5000/350 = 14.29
        expected = Decimal('14.29')
        self.assertEqual(calculate_weighted_average_price(prices, quantities), expected)
    
    def test_mismatched_lengths(self):
        """Test error handling for mismatched list lengths."""
        prices = [Decimal('10.00'), Decimal('12.00')]
        quantities = [Decimal('100')]
        with self.assertRaises(ValueError):
            calculate_weighted_average_price(prices, quantities)
    
    def test_zero_total_quantity(self):
        """Test error handling for zero total quantity."""
        prices = [Decimal('10.00'), Decimal('12.00')]
        quantities = [Decimal('0'), Decimal('0')]
        with self.assertRaises(ZeroDivisionError):
            calculate_weighted_average_price(prices, quantities)
    
    def test_mixed_input_types(self):
        """Test with mixed input types."""
        prices = ["10.00", "12.00", Decimal('15.00')]
        quantities = ["100", "50", Decimal('25')]
        # (10*100 + 12*50 + 15*25) / (100+50+25) = 1975/175 = 11.29
        expected = Decimal('11.29')
        self.assertEqual(calculate_weighted_average_price(prices, quantities), expected)


class TestPrecisionAndEdgeCases(unittest.TestCase):
    """Test precision and edge cases across all functions."""
    
    def test_very_large_numbers(self):
        """Test with very large monetary values."""
        large_value = Decimal('999999999.99')
        self.assertEqual(money_to_decimal(large_value), Decimal('999999999.99'))
        self.assertEqual(calculate_cost_basis(large_value, Decimal('1')), Decimal('999999999.99'))
    
    def test_very_small_numbers(self):
        """Test with very small monetary values."""
        small_value = Decimal('0.01')
        self.assertEqual(money_to_decimal(small_value), Decimal('0.01'))
        self.assertEqual(calculate_cost_basis(small_value, Decimal('1')), Decimal('0.01'))
    
    def test_floating_point_precision_issues(self):
        """Test handling of common floating-point precision issues."""
        # Common floating-point precision issue
        problematic_value = 0.1 + 0.2  # This equals 0.30000000000000004 in float
        result = money_to_decimal(problematic_value)
        self.assertEqual(result, Decimal('0.30'))
    
    def test_chain_calculations_precision(self):
        """Test that chained calculations maintain precision."""
        # Buy 100 shares at $10.33, then sell 50 at $12.67
        cost_basis = calculate_cost_basis(Decimal('10.33'), Decimal('100'))
        remaining_cost = calculate_cost_basis(Decimal('10.33'), Decimal('50'))
        sale_proceeds = calculate_position_value(Decimal('12.67'), Decimal('50'))
        realized_pnl = sale_proceeds - remaining_cost
        
        self.assertEqual(cost_basis, Decimal('1033.00'))
        self.assertEqual(remaining_cost, Decimal('516.50'))
        self.assertEqual(sale_proceeds, Decimal('633.50'))
        self.assertEqual(realized_pnl, Decimal('117.00'))


if __name__ == '__main__':
    unittest.main()