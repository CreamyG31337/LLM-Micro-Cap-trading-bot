"""
Unit tests for P&L calculator module.

Tests cover position P&L, daily P&L, portfolio metrics, and performance calculations.
"""

import unittest
from decimal import Decimal
import sys
import os

# Add the parent directory to the path so we can import the financial modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial.pnl_calculator import (
    PnLCalculator, 
    calculate_portfolio_cost_basis, 
    calculate_portfolio_current_value,
    calculate_daily_portfolio_pnl
)


class TestPnLCalculator(unittest.TestCase):
    """Test cases for PnLCalculator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.calculator = PnLCalculator()
        
        # Sample position data for testing
        self.sample_position = {
            'current_price': Decimal('15.00'),
            'buy_price': Decimal('10.00'),
            'shares': Decimal('100')
        }
        
        self.sample_positions = [
            {'current_price': Decimal('15.00'), 'buy_price': Decimal('10.00'), 'shares': Decimal('100'), 'ticker': 'AAPL'},
            {'current_price': Decimal('25.00'), 'buy_price': Decimal('20.00'), 'shares': Decimal('50'), 'ticker': 'GOOGL'},
            {'current_price': Decimal('8.00'), 'buy_price': Decimal('12.00'), 'shares': Decimal('200'), 'ticker': 'TSLA'}
        ]
    
    def test_calculate_position_pnl(self):
        """Test position P&L calculation."""
        result = self.calculator.calculate_position_pnl(Decimal('15.00'), Decimal('10.00'), Decimal('100'))
        
        # Check absolute P&L: (15 - 10) * 100 = 500
        self.assertEqual(result['absolute_pnl'], Decimal('500.00'))
        
        # Check percentage P&L: (15 - 10) / 10 = 0.5 (50%)
        self.assertEqual(result['percentage_pnl'], Decimal('0.5000'))
        
        # Check cost basis: 10 * 100 = 1000
        self.assertEqual(result['cost_basis'], Decimal('1000.00'))
        
        # Check current value: 15 * 100 = 1500
        self.assertEqual(result['current_value'], Decimal('1500.00'))
    
    def test_calculate_position_pnl_loss(self):
        """Test position P&L calculation for a losing position."""
        result = self.calculator.calculate_position_pnl(Decimal('8.00'), Decimal('12.00'), Decimal('200'))
        
        # Check absolute P&L: (8 - 12) * 200 = -800
        self.assertEqual(result['absolute_pnl'], Decimal('-800.00'))
        
        # Check percentage P&L: (8 - 12) / 12 = -0.3333 (33.33% loss)
        self.assertAlmostEqual(float(result['percentage_pnl']), -0.3333, places=4)
    
    def test_calculate_daily_pnl(self):
        """Test daily P&L calculation."""
        result = self.calculator.calculate_daily_pnl(Decimal('15.00'), Decimal('14.00'), Decimal('100'))
        
        # Check daily absolute P&L: (15 - 14) * 100 = 100
        self.assertEqual(result['daily_absolute_pnl'], Decimal('100.00'))
        
        # Check daily percentage P&L: (15 - 14) / 14 ≈ 0.0714 (7.14%)
        self.assertAlmostEqual(float(result['daily_percentage_pnl']), 0.0714, places=4)
    
    def test_calculate_period_pnl(self):
        """Test period P&L calculation."""
        result = self.calculator.calculate_period_pnl(Decimal('15.00'), Decimal('12.00'), Decimal('100'), "five_day")
        
        # Check period absolute P&L: (15 - 12) * 100 = 300
        self.assertEqual(result['five_day_absolute_pnl'], Decimal('300.00'))
        
        # Check period percentage P&L: (15 - 12) / 12 = 0.25 (25%)
        self.assertEqual(result['five_day_percentage_pnl'], Decimal('0.2500'))
    
    def test_calculate_portfolio_pnl(self):
        """Test portfolio P&L calculation."""
        result = self.calculator.calculate_portfolio_pnl(self.sample_positions)
        
        # Expected cost basis: (10*100) + (20*50) + (12*200) = 1000 + 1000 + 2400 = 4400
        self.assertEqual(result['total_cost_basis'], Decimal('4400.00'))
        
        # Expected current value: (15*100) + (25*50) + (8*200) = 1500 + 1250 + 1600 = 4350
        self.assertEqual(result['total_current_value'], Decimal('4350.00'))
        
        # Expected absolute P&L: 4350 - 4400 = -50
        self.assertEqual(result['total_absolute_pnl'], Decimal('-50.00'))
        
        # Expected percentage P&L: -50 / 4400 ≈ -0.0114 (-1.14%)
        self.assertAlmostEqual(float(result['portfolio_percentage_pnl']), -0.0114, places=4)
        
        # Check position count
        self.assertEqual(result['position_count'], 3)
    
    def test_calculate_total_return(self):
        """Test total return calculation."""
        result = self.calculator.calculate_total_return(10000, 11500, 2000)
        
        # Total invested: 10000 + 2000 = 12000
        self.assertEqual(result['total_invested'], Decimal('12000.00'))
        
        # Absolute return: 11500 - 12000 = -500
        self.assertEqual(result['absolute_return'], Decimal('-500.00'))
        
        # Percentage return: -500 / 12000 ≈ -0.0417 (-4.17%)
        self.assertAlmostEqual(float(result['percentage_return']), -0.0417, places=4)
    
    def test_calculate_performance_metrics(self):
        """Test comprehensive performance metrics calculation."""
        result = self.calculator.calculate_performance_metrics(
            self.sample_positions, 
            cash_balance=1000, 
            total_contributions=5000
        )
        
        # Check that all expected keys are present
        expected_keys = [
            'total_cost_basis', 'total_current_value', 'cash_balance', 'total_portfolio_value',
            'total_absolute_pnl', 'portfolio_percentage_pnl', 'total_invested', 'absolute_return',
            'percentage_return', 'total_positions', 'winning_positions', 'losing_positions', 'win_rate'
        ]
        
        for key in expected_keys:
            self.assertIn(key, result)
        
        # Check total portfolio value: 4350 + 1000 = 5350
        self.assertEqual(result['total_portfolio_value'], Decimal('5350.00'))
        
        # Check position statistics
        self.assertEqual(result['total_positions'], 3)
        self.assertEqual(result['winning_positions'], 2)  # AAPL and GOOGL are winning
        self.assertEqual(result['losing_positions'], 1)   # TSLA is losing
        
        # Check win rate: 2/3 ≈ 0.6667
        self.assertAlmostEqual(float(result['win_rate']), 0.6667, places=4)
    
    def test_calculate_position_weight(self):
        """Test position weight calculation."""
        weight = self.calculator.calculate_position_weight(1500, 5000)
        
        # Expected weight: 1500 / 5000 = 0.3 (30%)
        self.assertEqual(weight, Decimal('0.3000'))
    
    def test_format_pnl_display(self):
        """Test P&L display formatting."""
        # Test positive currency value
        result = self.calculator.format_pnl_display(500.50)
        self.assertEqual(result, "+$500.50")
        
        # Test negative currency value
        result = self.calculator.format_pnl_display(-250.75)
        self.assertEqual(result, "-$250.75")
        
        # Test positive percentage
        result = self.calculator.format_pnl_display(0.15, is_percentage=True)
        self.assertEqual(result, "+15.0%")
        
        # Test negative percentage
        result = self.calculator.format_pnl_display(-0.08, is_percentage=True)
        self.assertEqual(result, "-8.0%")
    
    def test_invalid_position_handling(self):
        """Test handling of invalid position data."""
        invalid_positions = [
            {'current_price': Decimal('15.00'), 'buy_price': Decimal('10.00')},  # Missing shares
            {'current_price': Decimal('15.00'), 'shares': Decimal('100')},       # Missing buy_price
            {'buy_price': Decimal('10.00'), 'shares': Decimal('100')},           # Missing current_price
            {'current_price': Decimal('15.00'), 'buy_price': Decimal('10.00'), 'shares': Decimal('-100')},  # Negative shares
        ]
        
        for invalid_pos in invalid_positions:
            self.assertFalse(self.calculator._is_valid_position(invalid_pos))
        
        # Test valid position
        valid_position = {'current_price': Decimal('15.00'), 'buy_price': Decimal('10.00'), 'shares': Decimal('100')}
        self.assertTrue(self.calculator._is_valid_position(valid_position))


class TestConvenienceFunctions(unittest.TestCase):
    """Test cases for convenience functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.sample_positions = [
            {'current_price': Decimal('15.00'), 'buy_price': Decimal('10.00'), 'shares': Decimal('100'), 'ticker': 'AAPL'},
            {'current_price': Decimal('25.00'), 'buy_price': Decimal('20.00'), 'shares': Decimal('50'), 'ticker': 'GOOGL'}
        ]
    
    def test_calculate_portfolio_cost_basis(self):
        """Test portfolio cost basis convenience function."""
        result = calculate_portfolio_cost_basis(self.sample_positions)
        
        # Expected: (10*100) + (20*50) = 1000 + 1000 = 2000
        self.assertEqual(result, Decimal('2000.00'))
    
    def test_calculate_portfolio_current_value(self):
        """Test portfolio current value convenience function."""
        result = calculate_portfolio_current_value(self.sample_positions)
        
        # Expected: (15*100) + (25*50) = 1500 + 1250 = 2750
        self.assertEqual(result, Decimal('2750.00'))
    
    def test_calculate_daily_portfolio_pnl(self):
        """Test daily portfolio P&L convenience function."""
        previous_prices = {'AAPL': Decimal('14.00'), 'GOOGL': Decimal('24.00')}
        
        result = calculate_daily_portfolio_pnl(self.sample_positions, previous_prices)
        
        # Expected daily P&L: (15-14)*100 + (25-24)*50 = 100 + 50 = 150
        self.assertEqual(result['total_daily_absolute_pnl'], Decimal('150.00'))
        self.assertEqual(result['positions_calculated'], 2)


if __name__ == '__main__':
    unittest.main()