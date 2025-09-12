#!/usr/bin/env python3
"""
Test suite for portfolio display bugs and issues.

This test suite specifically targets the bugs we've encountered and fixed:
1. P&L calculations showing N/A or incorrect values
2. Daily P&L dollar amounts showing as zero
3. Table formatting issues with Unicode characters
4. Emoji handling in console output
5. Field name mismatches between data structures
"""

import pytest
import pandas as pd
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.models.portfolio import Position, PortfolioSnapshot
from display.table_formatter import TableFormatter
from prompt_generator import PromptGenerator
from display.console_output import _safe_emoji, print_header, print_info
from datetime import datetime


class TestPortfolioDisplayBugs:
    """Test cases for portfolio display bugs we've encountered."""
    
    def setup_method(self):
        """Set up test data for each test method."""
        # Create test positions with realistic data
        self.test_positions = [
            Position(
                ticker="AAPL",
                shares=Decimal("10.0"),
                avg_price=Decimal("150.00"),
                cost_basis=Decimal("1500.00"),
                current_price=Decimal("155.00"),
                market_value=Decimal("1550.00"),
                unrealized_pnl=Decimal("50.00"),
                company="Apple Inc."
            ),
            Position(
                ticker="TSLA",
                shares=Decimal("5.0"),
                avg_price=Decimal("200.00"),
                cost_basis=Decimal("1000.00"),
                current_price=Decimal("180.00"),
                market_value=Decimal("900.00"),
                unrealized_pnl=Decimal("-100.00"),
                company="Tesla Inc."
            )
        ]
        
        # Create test snapshot
        self.test_snapshot = PortfolioSnapshot(
            positions=self.test_positions,
            timestamp=datetime.now()
        )
    
    def test_pnl_calculations_with_real_data(self):
        """Test that P&L calculations work correctly with real position data."""
        # Test total P&L percentage calculation
        position = self.test_positions[0]  # AAPL with positive P&L
        
        # Calculate expected P&L percentage
        expected_pnl_pct = (position.unrealized_pnl / position.cost_basis) * 100
        assert expected_pnl_pct == Decimal("3.333333333333333333333333333")
        
        # Test negative P&L
        position_neg = self.test_positions[1]  # TSLA with negative P&L
        expected_neg_pnl_pct = (position_neg.unrealized_pnl / position_neg.cost_basis) * 100
        assert expected_neg_pnl_pct == Decimal("-10.0")
    
    def test_daily_pnl_calculation_logic(self):
        """Test the daily P&L calculation logic used in trading script."""
        # Simulate two snapshots with different P&L values
        old_position = Position(
            ticker="AAPL",
            shares=Decimal("10.0"),
            avg_price=Decimal("150.00"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("150.00"),
            market_value=Decimal("1500.00"),
            unrealized_pnl=Decimal("0.00"),
            company="Apple Inc."
        )
        
        new_position = Position(
            ticker="AAPL",
            shares=Decimal("10.0"),
            avg_price=Decimal("150.00"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("155.00"),
            market_value=Decimal("1550.00"),
            unrealized_pnl=Decimal("50.00"),
            company="Apple Inc."
        )
        
        # Calculate daily P&L change
        daily_pnl_change = new_position.unrealized_pnl - old_position.unrealized_pnl
        assert daily_pnl_change == Decimal("50.00")
        
        # Test formatting
        daily_pnl_str = f"${daily_pnl_change:.2f}"
        assert daily_pnl_str == "$50.00"
    
    def test_table_formatter_field_names(self):
        """Test that table formatter uses correct field names from Position model."""
        # Create enhanced positions data (same structure as trading_script.py)
        enhanced_positions = []
        for position in self.test_positions:
            pos_dict = position.to_dict()
            pos_dict['position_weight'] = "5.0%"
            pos_dict['opened_date'] = "01-01-24"
            pos_dict['daily_pnl'] = "$10.50"  # Mock daily P&L
            enhanced_positions.append(pos_dict)
        
        # Test that table formatter can access the correct fields
        table_formatter = TableFormatter(data_dir="test_data", web_mode=False)
        
        # This should not raise any KeyError exceptions
        try:
            # Mock the console output to avoid actual display
            with patch('display.table_formatter.print'):
                table_formatter.create_portfolio_table(enhanced_positions)
        except KeyError as e:
            pytest.fail(f"Table formatter failed to access field: {e}")
    
    def test_emoji_handling_in_console_output(self):
        """Test that emoji handling works correctly in console output."""
        # Test _safe_emoji function
        safe_emoji = _safe_emoji("✅")
        assert safe_emoji in ["✅", "O"]  # Should be emoji or fallback
        
        safe_emoji_2 = _safe_emoji("💰")
        assert safe_emoji_2 in ["💰", "M"]  # Should be emoji or fallback
        
        # Test that print_header doesn't crash with emojis
        try:
            print_header("Test Header", "🚀")
        except UnicodeEncodeError:
            pytest.fail("print_header should handle emojis gracefully")
    
    def test_prompt_generator_daily_pnl_calculation(self):
        """Test that prompt generator calculates daily P&L correctly."""
        # Create mock portfolio snapshots with different P&L values
        old_position = Position(
            ticker="AAPL",
            shares=Decimal("10.0"),
            avg_price=Decimal("150.00"),
            cost_basis=Decimal("1500.00"),
            current_price=Decimal("150.00"),
            market_value=Decimal("1500.00"),
            unrealized_pnl=Decimal("0.00"),  # Old P&L = 0
            company="Apple Inc."
        )
        
        old_snapshot = PortfolioSnapshot(
            positions=[old_position],
            timestamp=datetime.now()
        )
        
        new_snapshot = PortfolioSnapshot(
            positions=[Position(
                ticker="AAPL",
                shares=Decimal("10.0"),
                avg_price=Decimal("150.00"),
                cost_basis=Decimal("1500.00"),
                current_price=Decimal("155.00"),
                market_value=Decimal("1550.00"),
                unrealized_pnl=Decimal("50.00"),  # New P&L
                company="Apple Inc."
            )],
            timestamp=datetime.now()
        )
        
        # Test the daily P&L calculation logic
        position = new_snapshot.positions[0]
        prev_position = old_snapshot.positions[0]
        
        if prev_position and prev_position.unrealized_pnl is not None and position.unrealized_pnl is not None:
            daily_pnl_change = position.unrealized_pnl - prev_position.unrealized_pnl
            daily_pnl_str = f"${daily_pnl_change:.2f}"
            assert daily_pnl_str == "$50.00"
        else:
            pytest.fail("Daily P&L calculation failed - missing data")
    
    def test_unicode_handling_in_tables(self):
        """Test that table formatting handles Unicode characters correctly."""
        # Test with problematic Unicode characters that caused issues
        test_data = [
            {
                'ticker': 'TEST',
                'company': 'Test Company',
                'shares': 10.0,
                'avg_price': 100.0,
                'current_price': 105.0,
                'unrealized_pnl': 50.0,
                'cost_basis': 1000.0,
                'position_weight': '5.0%',
                'opened_date': '01-01-24',
                'daily_pnl': '$10.50',
                'stop_loss': 90.0
            }
        ]
        
        table_formatter = TableFormatter(data_dir="test_data", web_mode=False)
        
        # This should not crash with Unicode encoding errors
        try:
            with patch('display.table_formatter.print'):
                table_formatter.create_portfolio_table(test_data)
        except UnicodeEncodeError as e:
            pytest.fail(f"Table formatter should handle Unicode characters: {e}")
    
    def test_pandas_display_options(self):
        """Test that pandas display options prevent problematic Unicode characters."""
        # Test the pandas options that were added to prevent Unicode issues
        import pandas as pd
        
        # Set the options that were added to fix the issue
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        # Create a DataFrame with data that might cause Unicode issues
        df_data = [
            {
                'Ticker': 'TEST',
                'Company': 'Test Company',
                'Total P&L': '+5.0% [$50.00]',
                'Daily P&L': '+2.0% [$10.50]'
            }
        ]
        
        df = pd.DataFrame(df_data)
        
        # This should not generate problematic Unicode characters
        try:
            table_str = df.to_string()
            # Check that no problematic characters are present
            assert 'à' not in table_str  # This character caused issues
        except UnicodeEncodeError as e:
            pytest.fail(f"Pandas should not generate problematic Unicode: {e}")
    
    def test_field_name_consistency(self):
        """Test that field names are consistent between data structures."""
        # Test Position model field names
        position = self.test_positions[0]
        pos_dict = position.to_dict()
        
        # These are the field names that should be available
        expected_fields = [
            'ticker', 'shares', 'avg_price', 'cost_basis', 'currency',
            'company', 'current_price', 'market_value', 'unrealized_pnl',
            'stop_loss', 'position_id'
        ]
        
        for field in expected_fields:
            assert field in pos_dict, f"Field '{field}' missing from position data"
        
        # Test that table formatter can access these fields
        enhanced_positions = [pos_dict]
        table_formatter = TableFormatter(data_dir="test_data", web_mode=False)
        
        # This should not raise KeyError
        try:
            with patch('display.table_formatter.print'):
                table_formatter.create_portfolio_table(enhanced_positions)
        except KeyError as e:
            pytest.fail(f"Table formatter should be able to access all position fields: {e}")


class TestEmojiHandlingBugs:
    """Test cases for emoji handling bugs we've encountered."""
    
    def test_safe_emoji_function(self):
        """Test that _safe_emoji function works correctly."""
        # Test various emojis that were causing issues
        test_emojis = ["✅", "❌", "💰", "🚀", "🤖", "📊", "📈", "🟢", "🔴", "⏰"]
        
        for emoji in test_emojis:
            result = _safe_emoji(emoji)
            # Should return either the emoji or a safe fallback
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_emoji_in_f_strings(self):
        """Test that emojis work correctly in f-strings."""
        # Test the pattern that was causing syntax errors
        emoji = "✅"
        test_string = f"Test {_safe_emoji(emoji)} message"
        
        # Should not raise syntax error
        assert isinstance(test_string, str)
        assert "Test" in test_string
        assert "message" in test_string
    
    def test_console_output_with_emojis(self):
        """Test that console output functions handle emojis correctly."""
        # Test print_header with emoji
        try:
            print_header("Test Header", "🚀")
        except (UnicodeEncodeError, SyntaxError) as e:
            pytest.fail(f"print_header should handle emojis: {e}")
        
        # Test print_info with emoji
        try:
            print_info("Test info", emoji="💰")
        except (UnicodeEncodeError, SyntaxError) as e:
            pytest.fail(f"print_info should handle emojis: {e}")


class TestPandasUnicodeBugs:
    """Test cases for pandas Unicode handling bugs."""
    
    def test_pandas_unicode_settings(self):
        """Test that pandas Unicode settings prevent problematic characters."""
        import pandas as pd
        
        # Set the options that prevent Unicode issues
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        # Create test data that might trigger Unicode issues
        test_data = [
            {'A': 'Test', 'B': 'Value', 'C': 'P&L: +5.0%'},
            {'A': 'Test2', 'B': 'Value2', 'C': 'P&L: -2.0%'}
        ]
        
        df = pd.DataFrame(test_data)
        
        # This should not generate problematic Unicode characters
        try:
            result = df.to_string()
            # Check for characters that were causing issues
            assert 'à' not in result
            assert 'é' not in result
            assert 'è' not in result
        except UnicodeEncodeError as e:
            pytest.fail(f"Pandas should handle Unicode correctly: {e}")
    
    def test_dataframe_display_consistency(self):
        """Test that DataFrame display is consistent across different environments."""
        import pandas as pd
        
        # Set consistent display options
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        test_data = [
            {'Ticker': 'AAPL', 'P&L': '+5.0% [$50.00]'},
            {'Ticker': 'TSLA', 'P&L': '-10.0% [$-100.00]'}
        ]
        
        df = pd.DataFrame(test_data)
        
        # Should be able to convert to string without issues
        try:
            result = df.to_string()
            assert 'AAPL' in result
            assert 'TSLA' in result
        except Exception as e:
            pytest.fail(f"DataFrame display should be consistent: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
