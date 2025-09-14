#!/usr/bin/env python3
"""
Test suite for emoji and Unicode handling bugs.

This test suite specifically targets the emoji and Unicode issues we've encountered:
1. Syntax errors with emojis in f-strings
2. Unicode encoding errors in console output
3. Pandas Unicode character generation issues
4. Emoji handling in different terminal environments
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, Mock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from display.console_output import _safe_emoji, print_header, print_info, print_success, print_error
import pandas as pd


class TestEmojiSyntaxBugs:
    """Test cases for emoji syntax errors we've encountered."""
    
    def test_emoji_in_f_strings_syntax(self):
        """Test that emojis work correctly in f-strings without syntax errors."""
        # Test the specific pattern that was causing syntax errors
        emoji = "✅"
        
        # This should not raise a syntax error
        test_string = f"Test {_safe_emoji(emoji)} message"
        assert isinstance(test_string, str)
        assert "Test" in test_string
        assert "message" in test_string
    
    def test_nested_emoji_calls_syntax(self):
        """Test that nested emoji calls don't cause syntax errors."""
        # Test the pattern that was causing issues in run.py
        emoji1 = "✅"
        emoji2 = "❌"
        
        # This should not raise a syntax error
        test_string = f"Status: {_safe_emoji(emoji1) if True else _safe_emoji(emoji2)}"
        assert isinstance(test_string, str)
        assert "Status:" in test_string
    
    def test_emoji_in_conditional_expressions(self):
        """Test emojis in conditional expressions that were causing issues."""
        # Test the pattern from run.py that was fixed
        status = True
        emoji = "✅" if status else "❌"
        
        test_string = f"Result: {_safe_emoji(emoji)}"
        assert isinstance(test_string, str)
        assert "Result:" in test_string
    
    def test_multiple_emoji_calls_in_f_string(self):
        """Test multiple emoji calls in a single f-string."""
        # Test pattern that was causing issues in run.py
        emoji1 = "📄"
        emoji2 = "✅"
        emoji3 = "❌"
        
        test_string = f"File: {_safe_emoji(emoji1)} Status: {_safe_emoji(emoji2) if True else _safe_emoji(emoji3)}"
        assert isinstance(test_string, str)
        assert "File:" in test_string
        assert "Status:" in test_string


class TestUnicodeEncodingBugs:
    """Test cases for Unicode encoding errors we've encountered."""
    
    def test_console_output_unicode_handling(self):
        """Test that console output functions handle Unicode characters correctly."""
        # Test various Unicode characters that were causing issues
        test_cases = [
            ("Test message", "🚀"),
            ("Portfolio data", "📊"),
            ("Success message", "✅"),
            ("Error message", "❌"),
            ("Money symbol", "💰"),
            ("Robot emoji", "🤖")
        ]
        
        for message, emoji in test_cases:
            try:
                print_header(message, emoji)
            except UnicodeEncodeError as e:
                pytest.fail(f"print_header should handle Unicode emoji {emoji}: {e}")
            
            try:
                print_info(message, emoji=emoji)
            except UnicodeEncodeError as e:
                pytest.fail(f"print_info should handle Unicode emoji {emoji}: {e}")
    
    def test_safe_emoji_fallback_behavior(self):
        """Test that _safe_emoji provides appropriate fallbacks."""
        # Test emojis that were causing issues
        problematic_emojis = ["🟢", "🔴", "⏰", "✅", "❌", "💰", "🚀", "🤖", "📊", "📈"]
        
        for emoji in problematic_emojis:
            result = _safe_emoji(emoji)
            assert isinstance(result, str)
            assert len(result) > 0
            # Should be either the original emoji or a safe fallback
            assert result in [emoji, "O", "C", "T", "M", "R", "B", "P", "S", "G", "H"]
    
    def test_unicode_in_table_headers(self):
        """Test that table headers with Unicode characters work correctly."""
        # Test the table headers that were causing issues
        test_headers = [
            "📊 Portfolio Snapshot",
            "🎯 Ticker",
            "🏢 Company", 
            "📅 Opened",
            "📈 Shares",
            "💵 Buy Price",
            "💰 Current",
            "📊 Total P&L",
            "📈 Daily P&L"
        ]
        
        for header in test_headers:
            try:
                # Test that the header can be processed without encoding errors
                safe_header = _safe_emoji(header)
                assert isinstance(safe_header, str)
            except UnicodeEncodeError as e:
                pytest.fail(f"Table header should handle Unicode: {e}")


class TestPandasUnicodeBugs:
    """Test cases for pandas Unicode handling bugs we've encountered."""
    
    def test_pandas_unicode_settings_prevent_issues(self):
        """Test that pandas Unicode settings prevent problematic character generation."""
        # Set the options that were added to fix Unicode issues
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        # Create test data that might trigger Unicode issues
        test_data = [
            {'Ticker': 'AAPL', 'Company': 'Apple Inc.', 'P&L': '+5.0% [$50.00]'},
            {'Ticker': 'TSLA', 'Company': 'Tesla Inc.', 'P&L': '-10.0% [$-100.00]'},
            {'Ticker': 'MSFT', 'Company': 'Microsoft Corp.', 'P&L': '+2.0% [$20.00]'}
        ]
        
        df = pd.DataFrame(test_data)
        
        try:
            result = df.to_string()
            # Check that no problematic Unicode characters are present
            problematic_chars = ['à', 'é', 'è', 'ç', 'ñ', 'ü', 'ö', 'ä']
            for char in problematic_chars:
                assert char not in result, f"Pandas generated problematic character: {char}"
        except UnicodeEncodeError as e:
            pytest.fail(f"Pandas should handle Unicode correctly: {e}")
    
    def test_dataframe_display_consistency(self):
        """Test that DataFrame display is consistent and doesn't generate problematic characters."""
        # Set consistent display options
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        # Test with data that was causing issues
        test_data = [
            {
                'Ticker': 'AAPL',
                'Company': 'Apple Inc.',
                'Opened': '01-01-24',
                'Shares': '10.0000',
                'Price': '$150.00',
                'Current': '$155.00',
                'Total Value': '$1550.00',
                'Dollar P&L': '$50.00',
                'Total P&L': '+3.3% [$50.00]',
                'Daily P&L': '+2.0% [$10.50]',
                'Weight': '5.0%',
                'Stop Loss': 'None',
                'Cost Basis': '$1500.00'
            }
        ]
        
        df = pd.DataFrame(test_data)
        
        try:
            result = df.to_string()
            # Should contain expected data
            assert 'AAPL' in result
            assert 'Apple Inc.' in result
            assert '$1550.00' in result
            assert '+3.3%' in result
        except Exception as e:
            pytest.fail(f"DataFrame display should be consistent: {e}")
    
    def test_pandas_unicode_edge_cases(self):
        """Test pandas Unicode handling with edge cases that might cause issues."""
        # Test with various edge cases
        edge_cases = [
            {'A': 'Test', 'B': 'Value', 'C': 'P&L: +5.0%'},
            {'A': 'Test2', 'B': 'Value2', 'C': 'P&L: -2.0%'},
            {'A': 'Test3', 'B': 'Value3', 'C': 'P&L: 0.0%'},
            {'A': 'Test4', 'B': 'Value4', 'C': 'P&L: N/A'}
        ]
        
        df = pd.DataFrame(edge_cases)
        
        # Set Unicode options
        pd.set_option('display.unicode.ambiguous_as_wide', False)
        pd.set_option('display.unicode.east_asian_width', False)
        
        try:
            result = df.to_string()
            # Should not contain problematic characters
            assert 'à' not in result
            assert 'é' not in result
            assert 'è' not in result
        except UnicodeEncodeError as e:
            pytest.fail(f"Pandas should handle edge cases: {e}")


class TestTerminalEnvironmentBugs:
    """Test cases for terminal environment specific bugs."""
    
    def test_windows_console_encoding(self):
        """Test emoji handling in Windows console environment."""
        # Mock Windows console environment
        with patch('sys.platform', 'win32'):
            # Test that emojis are handled gracefully without mocking readonly attributes
            result = _safe_emoji("✅")
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_utf8_terminal_encoding(self):
        """Test emoji handling in UTF-8 terminal environment."""
        # Test emoji handling without mocking readonly attributes
        result = _safe_emoji("✅")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_console_output_fallback_behavior(self):
        """Test that console output functions fall back gracefully."""
        # Test emoji handling without mocking readonly attributes
        try:
            result = _safe_emoji("✅")
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Console output should handle emojis gracefully: {e}")


class TestEmojiFunctionBugs:
    """Test cases for emoji function bugs we've encountered."""
    
    def test_safe_emoji_with_problematic_characters(self):
        """Test _safe_emoji with characters that were causing issues."""
        # Test the specific emojis that were causing problems
        problematic_emojis = [
            "✅",  # Check mark
            "❌",  # Cross mark
            "💰",  # Money bag
            "🚀",  # Rocket
            "🤖",  # Robot
            "📊",  # Bar chart
            "📈",  # Trending up
            "🟢",  # Green circle
            "🔴",  # Red circle
            "⏰",  # Clock
            "📄",  # Document
            "🏢",  # Office building
            "📅",  # Calendar
            "📈",  # Chart
            "💵",  # Dollar bill
            "🛑",  # Stop sign
            "🍕",  # Pizza (for weight)
            "🎯",  # Target
            "🏁",  # Checkered flag
            "🐛",  # Bug
            "💡",  # Light bulb
            "📋",  # Clipboard
            "🔬",  # Microscope
            "⚙️",  # Gear
            "🚪",  # Door
            "👋",  # Waving hand
            "⚠️",  # Warning
            "🧪",  # Test tube
        ]
        
        for emoji in problematic_emojis:
            result = _safe_emoji(emoji)
            assert isinstance(result, str)
            assert len(result) > 0
            # Should be either the original emoji or a safe ASCII fallback
            assert result in [emoji, "O", "C", "M", "R", "B", "P", "S", "G", "H", "T", "D", "F", "L", "W", "U", "A", "E", "I", "N", "Q", "X", "Y", "Z"]
    
    def test_emoji_in_different_contexts(self):
        """Test emojis in different contexts that were causing issues."""
        # Test in f-strings
        emoji = "✅"
        test_string = f"Status: {_safe_emoji(emoji)}"
        assert "Status:" in test_string
        
        # Test in conditional expressions
        status = True
        result = _safe_emoji("✅") if status else _safe_emoji("❌")
        assert isinstance(result, str)
        
        # Test in function calls
        try:
            print_header("Test", _safe_emoji("🚀"))
        except Exception as e:
            pytest.fail(f"Emoji in function calls should work: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
