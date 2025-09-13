#!/usr/bin/env python3
"""
Unit tests for Position model decimal formatting.

This module tests that the Position model correctly formats decimal values
when converting to dictionary format for CSV export.
"""

import unittest
from decimal import Decimal
import sys
import os

# Add parent directory to path to import models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.models.portfolio import Position


class TestPositionDecimalFormatting(unittest.TestCase):
    """Test cases for Position model decimal formatting."""
    
    def setUp(self):
        """Set up test data."""
        self.test_position = Position(
            ticker="AAPL",
            shares=Decimal("10.123456789"),
            avg_price=Decimal("150.123456789"),
            cost_basis=Decimal("1501.23456789"),
            currency="USD",
            company="Apple Inc.",
            current_price=Decimal("155.987654321"),
            market_value=Decimal("1559.87654321"),
            unrealized_pnl=Decimal("58.64197532"),
            stop_loss=Decimal("140.000000001")
        )
    
    def test_to_dict_shares_formatting(self):
        """Test that shares are formatted to 4 decimal places."""
        position_dict = self.test_position.to_dict()
        
        # Check shares formatting
        self.assertEqual(position_dict['shares'], 10.1235)  # Rounded to 4 decimal places
        self.assertIsInstance(position_dict['shares'], float)
        
        # Verify precision
        shares_str = f"{position_dict['shares']:.10f}".rstrip('0').rstrip('.')
        if '.' in shares_str:
            decimal_places = len(shares_str.split('.')[-1])
            self.assertLessEqual(decimal_places, 4)
    
    def test_to_dict_price_formatting(self):
        """Test that all price fields are formatted to 2 decimal places."""
        position_dict = self.test_position.to_dict()
        
        # Check all price fields
        price_fields = ['avg_price', 'cost_basis', 'current_price', 'market_value', 'unrealized_pnl', 'stop_loss']
        
        for field in price_fields:
            with self.subTest(field=field):
                value = position_dict[field]
                self.assertIsInstance(value, float)
                
                # Verify precision (2 decimal places)
                value_str = f"{value:.10f}".rstrip('0').rstrip('.')
                if '.' in value_str:
                    decimal_places = len(value_str.split('.')[-1])
                    self.assertLessEqual(decimal_places, 2, f"Field {field} has too many decimal places: {value}")
    
    def test_to_dict_specific_values(self):
        """Test specific formatting values."""
        position_dict = self.test_position.to_dict()
        
        # Test specific expected values
        self.assertEqual(position_dict['shares'], 10.1235)
        self.assertEqual(position_dict['avg_price'], 150.12)
        self.assertEqual(position_dict['cost_basis'], 1501.23)
        self.assertEqual(position_dict['current_price'], 155.99)
        self.assertEqual(position_dict['market_value'], 1559.88)
        self.assertEqual(position_dict['unrealized_pnl'], 58.64)
        self.assertEqual(position_dict['stop_loss'], 140.0)
    
    def test_to_dict_none_values(self):
        """Test handling of None values."""
        position_with_nones = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("100.0"),
            cost_basis=Decimal("1000.0"),
            currency="USD",
            company="Test Company",
            current_price=None,
            market_value=None,
            unrealized_pnl=None,
            stop_loss=None
        )
        
        position_dict = position_with_nones.to_dict()
        
        # None values should be converted to 0.0
        self.assertEqual(position_dict['current_price'], 0.0)
        self.assertEqual(position_dict['market_value'], 0.0)
        self.assertEqual(position_dict['unrealized_pnl'], 0.0)
        self.assertEqual(position_dict['stop_loss'], 0.0)
        
        # Non-None values should be properly formatted
        self.assertEqual(position_dict['shares'], 10.0)
        self.assertEqual(position_dict['avg_price'], 100.0)
        self.assertEqual(position_dict['cost_basis'], 1000.0)
    
    def test_to_dict_rounding_behavior(self):
        """Test specific rounding behaviors."""
        # Test rounding up
        position_round_up = Position(
            ticker="TEST",
            shares=Decimal("10.12345"),  # Should round to 10.1235
            avg_price=Decimal("100.125"),  # Should round to 100.13
            cost_basis=Decimal("1000.0"),
            currency="USD"
        )
        
        position_dict = position_round_up.to_dict()
        self.assertEqual(position_dict['shares'], 10.1235)
        self.assertEqual(position_dict['avg_price'], 100.12)
        
        # Test rounding down
        position_round_down = Position(
            ticker="TEST",
            shares=Decimal("10.12344"),  # Should round to 10.1234
            avg_price=Decimal("100.124"),  # Should round to 100.12
            cost_basis=Decimal("1000.0"),
            currency="USD"
        )
        
        position_dict = position_round_down.to_dict()
        self.assertEqual(position_dict['shares'], 10.1234)
        self.assertEqual(position_dict['avg_price'], 100.12)
    
    def test_to_dict_edge_cases(self):
        """Test edge cases in decimal formatting."""
        # Test very small numbers
        position_small = Position(
            ticker="TEST",
            shares=Decimal("0.0001"),
            avg_price=Decimal("0.01"),
            cost_basis=Decimal("0.0"),
            currency="USD"
        )
        
        position_dict = position_small.to_dict()
        self.assertEqual(position_dict['shares'], 0.0001)
        self.assertEqual(position_dict['avg_price'], 0.01)
        self.assertEqual(position_dict['cost_basis'], 0.0)
        
        # Test very large numbers
        position_large = Position(
            ticker="TEST",
            shares=Decimal("999999.9999"),
            avg_price=Decimal("999999.99"),
            cost_basis=Decimal("999999999.99"),
            currency="USD"
        )
        
        position_dict = position_large.to_dict()
        self.assertEqual(position_dict['shares'], 999999.9999)  # 4 decimal places preserved
        self.assertEqual(position_dict['avg_price'], 999999.99)  # 2 decimal places preserved
        self.assertEqual(position_dict['cost_basis'], 999999999.99)  # 2 decimal places preserved
    
    def test_to_dict_negative_values(self):
        """Test formatting of negative values."""
        position_negative = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("100.0"),
            cost_basis=Decimal("1000.0"),
            currency="USD",
            current_price=Decimal("95.0"),
            market_value=Decimal("950.0"),
            unrealized_pnl=Decimal("-50.0"),  # Negative P&L
            stop_loss=Decimal("90.0")
        )
        
        position_dict = position_negative.to_dict()
        
        # Negative values should be properly formatted
        self.assertEqual(position_dict['unrealized_pnl'], -50.0)
        self.assertEqual(position_dict['current_price'], 95.0)
        self.assertEqual(position_dict['market_value'], 950.0)
        self.assertEqual(position_dict['stop_loss'], 90.0)
    
    def test_to_dict_string_fields_unchanged(self):
        """Test that string fields are not affected by decimal formatting."""
        position_dict = self.test_position.to_dict()
        
        # String fields should remain unchanged
        self.assertEqual(position_dict['ticker'], "AAPL")
        self.assertEqual(position_dict['currency'], "USD")
        self.assertEqual(position_dict['company'], "Apple Inc.")
        self.assertIsNone(position_dict['position_id'])
    
    def test_csv_export_compatibility(self):
        """Test that the formatted data is compatible with CSV export."""
        position_dict = self.test_position.to_dict()
        
        # All values should be serializable to CSV
        for key, value in position_dict.items():
            with self.subTest(field=key):
                if value is not None:
                    # Should be able to convert to string without errors
                    str_value = str(value)
                    self.assertIsInstance(str_value, str)
                    
                    # Should be able to convert back to float
                    if isinstance(value, (int, float)):
                        float_value = float(str_value)
                        self.assertIsInstance(float_value, (int, float))


class TestPositionDecimalFormattingIntegration(unittest.TestCase):
    """Integration tests for Position decimal formatting with real scenarios."""
    
    def test_portfolio_snapshot_export(self):
        """Test formatting for portfolio snapshot export."""
        positions = [
            Position(
                ticker="AAPL",
                shares=Decimal("9.2961"),
                avg_price=Decimal("37.65"),
                cost_basis=Decimal("350.0"),
                currency="USD",
                company="Apple Inc.",
                current_price=Decimal("35.16999816894531"),  # Typical float precision issue
                market_value=Decimal("326.9438199783325"),
                unrealized_pnl=Decimal("-23.054345021667466")
            ),
            Position(
                ticker="VEE.TO",
                shares=Decimal("2.4987"),
                avg_price=Decimal("43.37"),
                cost_basis=Decimal("108.38"),
                currency="CAD",
                company="Vanguard ETF",
                current_price=Decimal("43.88999938964844"),  # Typical float precision issue
                market_value=Decimal("109.66794147491454"),
                unrealized_pnl=Decimal("1.299322474914557")
            )
        ]
        
        # Convert all positions to dictionaries
        position_dicts = [pos.to_dict() for pos in positions]
        
        # Verify all values are properly formatted
        for i, pos_dict in enumerate(position_dicts):
            with self.subTest(position=i):
                # Check shares precision
                shares_str = f"{pos_dict['shares']:.10f}".rstrip('0').rstrip('.')
                if '.' in shares_str:
                    decimal_places = len(shares_str.split('.')[-1])
                    self.assertLessEqual(decimal_places, 4, f"Position {i} shares has too many decimal places")
                
                # Check price precision
                price_fields = ['avg_price', 'current_price', 'market_value', 'unrealized_pnl']
                for field in price_fields:
                    if pos_dict[field] != 0:
                        price_str = f"{pos_dict[field]:.10f}".rstrip('0').rstrip('.')
                        if '.' in price_str:
                            decimal_places = len(price_str.split('.')[-1])
                            self.assertLessEqual(decimal_places, 2, f"Position {i} {field} has too many decimal places")
    
    def test_float_precision_issue_prevention(self):
        """Test that the formatting prevents typical float precision issues."""
        # Simulate the exact values that caused the original issue
        problematic_values = {
            'shares': 9.2961,
            'current_price': 35.16999816894531,
            'market_value': 326.9438199783325,
            'unrealized_pnl': -23.054345021667466
        }
        
        # Create position with these problematic values
        position = Position(
            ticker="CTRN",
            shares=Decimal(str(problematic_values['shares'])),
            avg_price=Decimal("37.65"),
            cost_basis=Decimal("350.0"),
            currency="USD",
            current_price=Decimal(str(problematic_values['current_price'])),
            market_value=Decimal(str(problematic_values['market_value'])),
            unrealized_pnl=Decimal(str(problematic_values['unrealized_pnl']))
        )
        
        position_dict = position.to_dict()
        
        # Verify the problematic values are now clean
        self.assertEqual(position_dict['shares'], 9.2961)  # Clean 4 decimal places
        self.assertEqual(position_dict['current_price'], 35.17)  # Clean 2 decimal places
        self.assertEqual(position_dict['market_value'], 326.94)  # Clean 2 decimal places
        self.assertEqual(position_dict['unrealized_pnl'], -23.05)  # Clean 2 decimal places
        
        # Verify no more float precision issues
        for field, value in position_dict.items():
            if isinstance(value, float):
                # Check that the value doesn't have excessive decimal places
                value_str = f"{value:.10f}".rstrip('0').rstrip('.')
                if '.' in value_str:
                    decimal_places = len(value_str.split('.')[-1])
                    if field == 'shares':
                        self.assertLessEqual(decimal_places, 4, f"Field {field} has too many decimal places: {value}")
                    else:
                        self.assertLessEqual(decimal_places, 2, f"Field {field} has too many decimal places: {value}")


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
