#!/usr/bin/env python3
"""
Unit tests for decimal formatting utilities.

This module tests the decimal formatter functions to ensure consistent
and correct decimal precision across the trading bot.
"""

import unittest
from decimal import Decimal
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.decimal_formatter import (
    format_price, format_shares, format_currency, format_percentage,
    safe_float_conversion, format_position_dict, validate_decimal_precision
)


class TestDecimalFormatter(unittest.TestCase):
    """Test cases for decimal formatting utilities."""
    
    def test_format_price(self):
        """Test price formatting to 2 decimal places."""
        # Test with various input types
        self.assertEqual(format_price(123.456789), 123.46)
        self.assertEqual(format_price(123.0), 123.0)
        self.assertEqual(format_price(123), 123.0)
        self.assertEqual(format_price("123.456789"), 123.46)
        self.assertEqual(format_price(Decimal("123.456789")), 123.46)
        
        # Test with None
        self.assertEqual(format_price(None), 0.0)
        self.assertEqual(format_price(None, 5.0), 5.0)
        
        # Test edge cases
        self.assertEqual(format_price(0.001), 0.0)  # Rounds to 0.00
        self.assertEqual(format_price(0.005), 0.01)  # Rounds up
        self.assertEqual(format_price(0.004), 0.0)   # Rounds down
        
        # Test invalid input
        self.assertEqual(format_price("invalid"), 0.0)
        self.assertEqual(format_price("invalid", 10.0), 10.0)
    
    def test_format_shares(self):
        """Test shares formatting to 4 decimal places."""
        # Test with various input types
        self.assertEqual(format_shares(123.456789), 123.4568)
        self.assertEqual(format_shares(123.0), 123.0)
        self.assertEqual(format_shares(123), 123.0)
        self.assertEqual(format_shares("123.456789"), 123.4568)
        self.assertEqual(format_shares(Decimal("123.456789")), 123.4568)
        
        # Test with None
        self.assertEqual(format_shares(None), 0.0)
        self.assertEqual(format_shares(None, 5.0), 5.0)
        
        # Test edge cases
        self.assertEqual(format_shares(0.00001), 0.0)  # Rounds to 0.0000
        self.assertEqual(format_shares(0.00005), 0.0001)  # Rounds up
        self.assertEqual(format_shares(0.00004), 0.0)   # Rounds down
        
        # Test invalid input
        self.assertEqual(format_shares("invalid"), 0.0)
        self.assertEqual(format_shares("invalid", 10.0), 10.0)
    
    def test_format_currency(self):
        """Test currency formatting (same as price formatting)."""
        self.assertEqual(format_currency(123.456789), 123.46)
        self.assertEqual(format_currency(123.0), 123.0)
        self.assertEqual(format_currency(None), 0.0)
    
    def test_format_percentage(self):
        """Test percentage formatting to 1 decimal place."""
        # Test with various input types
        self.assertEqual(format_percentage(123.456789), 123.5)
        self.assertEqual(format_percentage(123.0), 123.0)
        self.assertEqual(format_percentage(123), 123.0)
        self.assertEqual(format_percentage("123.456789"), 123.5)
        self.assertEqual(format_percentage(Decimal("123.456789")), 123.5)
        
        # Test with None
        self.assertEqual(format_percentage(None), 0.0)
        self.assertEqual(format_percentage(None, 5.0), 5.0)
        
        # Test edge cases
        self.assertEqual(format_percentage(0.01), 0.0)  # Rounds to 0.0
        self.assertEqual(format_percentage(0.05), 0.1)  # Rounds up
        self.assertEqual(format_percentage(0.04), 0.0)  # Rounds down
        
        # Test invalid input
        self.assertEqual(format_percentage("invalid"), 0.0)
        self.assertEqual(format_percentage("invalid", 10.0), 10.0)
    
    def test_safe_float_conversion(self):
        """Test safe float conversion with custom precision."""
        # Test with default precision (2)
        self.assertEqual(safe_float_conversion(123.456789), 123.46)
        self.assertEqual(safe_float_conversion(123.0), 123.0)
        self.assertEqual(safe_float_conversion(None), 0.0)
        
        # Test with custom precision
        self.assertEqual(safe_float_conversion(123.456789, precision=4), 123.4568)
        self.assertEqual(safe_float_conversion(123.456789, precision=0), 123.0)
        self.assertEqual(safe_float_conversion(123.456789, precision=1), 123.5)
        
        # Test with custom default
        self.assertEqual(safe_float_conversion(None, default=5.0), 5.0)
        self.assertEqual(safe_float_conversion("invalid", default=10.0), 10.0)
    
    def test_format_position_dict(self):
        """Test formatting of position dictionary."""
        position_dict = {
            'ticker': 'AAPL',
            'shares': 123.456789,
            'avg_price': 150.123456,
            'current_price': 155.987654,
            'cost_basis': 18500.123456,
            'market_value': 19200.987654,
            'unrealized_pnl': 700.864198,
            'stop_loss': 140.000001,
            'company': 'Apple Inc.'
        }
        
        formatted = format_position_dict(position_dict)
        
        # Check that shares are formatted to 4 decimal places
        self.assertEqual(formatted['shares'], 123.4568)
        
        # Check that prices are formatted to 2 decimal places
        self.assertEqual(formatted['avg_price'], 150.12)
        self.assertEqual(formatted['current_price'], 155.99)
        self.assertEqual(formatted['cost_basis'], 18500.12)
        self.assertEqual(formatted['market_value'], 19200.99)
        self.assertEqual(formatted['unrealized_pnl'], 700.86)
        self.assertEqual(formatted['stop_loss'], 140.0)
        
        # Check that non-numeric fields are unchanged
        self.assertEqual(formatted['ticker'], 'AAPL')
        self.assertEqual(formatted['company'], 'Apple Inc.')
    
    def test_validate_decimal_precision(self):
        """Test decimal precision validation."""
        # Test valid precision
        self.assertTrue(validate_decimal_precision(123.45, 2))
        self.assertTrue(validate_decimal_precision(123.0, 2))
        self.assertTrue(validate_decimal_precision(123, 2))
        
        # Test invalid precision
        self.assertFalse(validate_decimal_precision(123.456, 2))
        self.assertFalse(validate_decimal_precision(123.456789, 2))
        
        # Test edge cases
        self.assertTrue(validate_decimal_precision(0.0, 2))
        self.assertTrue(validate_decimal_precision(0.00, 2))
        self.assertFalse(validate_decimal_precision(0.001, 2))
        
        # Test invalid input types
        self.assertFalse(validate_decimal_precision("invalid", 2))
        self.assertFalse(validate_decimal_precision(None, 2))
    
    def test_rounding_behavior(self):
        """Test specific rounding behaviors."""
        # Test rounding behavior (Python's round function behavior)
        self.assertEqual(format_price(0.005), 0.01)  # 0.005 rounds to 0.01
        self.assertEqual(format_price(0.015), 0.01)  # 0.015 rounds to 0.01
        self.assertEqual(format_price(0.025), 0.03)  # 0.025 rounds to 0.03
        
        # Test rounding down
        self.assertEqual(format_price(0.004), 0.0)
        self.assertEqual(format_price(0.014), 0.01)
        self.assertEqual(format_price(0.024), 0.02)
        
        # Test shares rounding
        self.assertEqual(format_shares(0.00005), 0.0001)  # 0.00005 rounds to 0.0001
        self.assertEqual(format_shares(0.00004), 0.0)
        self.assertEqual(format_shares(0.00015), 0.0001)  # 0.00015 rounds to 0.0001
        self.assertEqual(format_shares(0.00014), 0.0001)
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test very small numbers
        self.assertEqual(format_price(0.0001), 0.0)
        self.assertEqual(format_shares(0.00001), 0.0)
        
        # Test very large numbers
        self.assertEqual(format_price(999999.999), 1000000.0)
        self.assertEqual(format_shares(999999.9999), 999999.9999)  # 4 decimal places preserved
        
        # Test negative numbers
        self.assertEqual(format_price(-123.456), -123.46)
        self.assertEqual(format_shares(-123.4567), -123.4567)
        
        # Test zero
        self.assertEqual(format_price(0), 0.0)
        self.assertEqual(format_shares(0), 0.0)
        
        # Test empty string
        self.assertEqual(format_price(""), 0.0)
        self.assertEqual(format_shares(""), 0.0)


class TestDecimalFormatterIntegration(unittest.TestCase):
    """Integration tests for decimal formatter with real data scenarios."""
    
    def test_portfolio_data_formatting(self):
        """Test formatting with realistic portfolio data."""
        portfolio_data = [
            {
                'ticker': 'AAPL',
                'shares': 10.123456789,
                'avg_price': 150.123456789,
                'current_price': 155.987654321,
                'cost_basis': 1501.23456789,
                'market_value': 1559.87654321,
                'unrealized_pnl': 58.64197532,
                'stop_loss': 140.000000001
            },
            {
                'ticker': 'GOOGL',
                'shares': 5.987654321,
                'avg_price': 2800.123456789,
                'current_price': 2850.987654321,
                'cost_basis': 16760.123456789,
                'market_value': 17059.87654321,
                'unrealized_pnl': 299.753086421,
                'stop_loss': 2700.000000001
            }
        ]
        
        for position in portfolio_data:
            formatted = format_position_dict(position)
            
            # Verify shares precision
            self.assertEqual(len(str(formatted['shares']).split('.')[-1]), 4)
            
            # Verify price precision
            price_fields = ['avg_price', 'current_price', 'cost_basis', 'market_value', 'unrealized_pnl', 'stop_loss']
            for field in price_fields:
                if formatted[field] != 0:
                    decimal_places = len(str(formatted[field]).split('.')[-1])
                    self.assertLessEqual(decimal_places, 2, f"Field {field} has too many decimal places: {formatted[field]}")
    
    def test_csv_export_formatting(self):
        """Test formatting for CSV export scenarios."""
        # Simulate data that might come from calculations
        raw_calculations = {
            'shares': 9.2961 * 1.0,  # This might produce float precision issues
            'avg_price': 37.65 * 1.0,
            'current_price': 35.16999816894531,  # Typical float precision issue
            'total_value': 9.2961 * 35.16999816894531,
            'pnl': (35.16999816894531 - 37.65) * 9.2961
        }
        
        # Format the data
        formatted = {
            'shares': format_shares(raw_calculations['shares']),
            'avg_price': format_price(raw_calculations['avg_price']),
            'current_price': format_price(raw_calculations['current_price']),
            'total_value': format_price(raw_calculations['total_value']),
            'pnl': format_price(raw_calculations['pnl'])
        }
        
        # Verify all values are properly formatted
        self.assertEqual(formatted['shares'], 9.2961)
        self.assertEqual(formatted['avg_price'], 37.65)
        self.assertEqual(formatted['current_price'], 35.17)
        self.assertEqual(formatted['total_value'], 326.94)
        self.assertEqual(formatted['pnl'], -23.05)
        
        # Verify precision
        self.assertTrue(validate_decimal_precision(formatted['shares'], 4))
        for field in ['avg_price', 'current_price', 'total_value', 'pnl']:
            self.assertTrue(validate_decimal_precision(formatted[field], 2))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
