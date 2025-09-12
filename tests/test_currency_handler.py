"""
Unit tests for currency handling module.

Tests cover currency detection, conversion, cash balance management,
and multi-currency trading support.
"""

import unittest
import tempfile
import json
from decimal import Decimal
from pathlib import Path
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial.currency_handler import (
    CashBalances,
    CurrencyHandler,
    is_canadian_ticker,
    is_us_ticker,
    get_ticker_currency,
    calculate_conversion_with_fee
)


class TestCashBalances(unittest.TestCase):
    """Test CashBalances dataclass."""
    
    def test_initialization(self):
        """Test CashBalances initialization."""
        balances = CashBalances(cad=1000.50, usd=750.25)
        self.assertEqual(balances.cad, Decimal('1000.50'))
        self.assertEqual(balances.usd, Decimal('750.25'))
    
    def test_initialization_with_strings(self):
        """Test initialization with string values."""
        balances = CashBalances(cad="1000.50", usd="750.25")
        self.assertEqual(balances.cad, Decimal('1000.50'))
        self.assertEqual(balances.usd, Decimal('750.25'))
    
    def test_total_cad_equivalent(self):
        """Test CAD equivalent calculation."""
        balances = CashBalances(cad=1000, usd=500)
        # 1000 CAD + (500 USD * 1.35) = 1000 + 675 = 1675
        total = balances.total_cad_equivalent(1.35)
        self.assertEqual(total, Decimal('1675.00'))
    
    def test_total_usd_equivalent(self):
        """Test USD equivalent calculation."""
        balances = CashBalances(cad=1000, usd=500)
        # 500 USD + (1000 CAD * 0.74) = 500 + 740 = 1240
        total = balances.total_usd_equivalent(0.74)
        self.assertEqual(total, Decimal('1240.00'))
    
    def test_can_afford_methods(self):
        """Test affordability checking methods."""
        balances = CashBalances(cad=1000, usd=500)
        
        self.assertTrue(balances.can_afford_cad(500))
        self.assertTrue(balances.can_afford_cad(1000))
        self.assertFalse(balances.can_afford_cad(1001))
        
        self.assertTrue(balances.can_afford_usd(250))
        self.assertTrue(balances.can_afford_usd(500))
        self.assertFalse(balances.can_afford_usd(501))
    
    def test_spend_methods_full_amount(self):
        """Test spending methods with full amounts."""
        balances = CashBalances(cad=1000, usd=500)
        
        # Spend CAD - full amount available
        result = balances.spend_cad(300)
        self.assertTrue(result)
        self.assertEqual(balances.cad, Decimal('700.00'))
        
        # Spend USD - full amount available
        result = balances.spend_usd(200)
        self.assertTrue(result)
        self.assertEqual(balances.usd, Decimal('300.00'))
    
    def test_spend_methods_insufficient_funds(self):
        """Test spending methods with insufficient funds."""
        balances = CashBalances(cad=100, usd=50)
        
        # Try to spend more CAD than available
        result = balances.spend_cad(200)
        self.assertFalse(result)
        self.assertEqual(balances.cad, Decimal('0.00'))
        
        # Try to spend more USD than available
        result = balances.spend_usd(100)
        self.assertFalse(result)
        self.assertEqual(balances.usd, Decimal('0.00'))
    
    def test_add_methods(self):
        """Test adding cash methods."""
        balances = CashBalances(cad=1000, usd=500)
        
        balances.add_cad(250)
        self.assertEqual(balances.cad, Decimal('1250.00'))
        
        balances.add_usd(100)
        self.assertEqual(balances.usd, Decimal('600.00'))
    
    def test_to_dict(self):
        """Test dictionary serialization."""
        balances = CashBalances(cad=1000.50, usd=750.25, id="test_id")
        result = balances.to_dict()
        
        expected = {
            'cad': 1000.50,
            'usd': 750.25,
            'id': 'test_id',
            'last_updated': None
        }
        self.assertEqual(result, expected)
    
    def test_from_dict(self):
        """Test dictionary deserialization."""
        data = {
            'cad': 1000.50,
            'usd': 750.25,
            'id': 'test_id',
            'last_updated': '2025-01-01'
        }
        balances = CashBalances.from_dict(data)
        
        self.assertEqual(balances.cad, Decimal('1000.50'))
        self.assertEqual(balances.usd, Decimal('750.25'))
        self.assertEqual(balances.id, 'test_id')
        self.assertEqual(balances.last_updated, '2025-01-01')


class TestCurrencyHandler(unittest.TestCase):
    """Test CurrencyHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = CurrencyHandler()
        # Disable live API calls for testing by clearing the cache and mocking
        self.handler.clear_exchange_rate_cache()
        # Override the live rate method to return None (use defaults)
        self.handler._get_live_exchange_rate = lambda from_curr, to_curr: None
    
    def test_is_canadian_ticker(self):
        """Test Canadian ticker detection."""
        self.assertTrue(self.handler.is_canadian_ticker("SHOP.TO"))
        self.assertTrue(self.handler.is_canadian_ticker("BB.TO"))
        self.assertTrue(self.handler.is_canadian_ticker("WEED.V"))
        self.assertTrue(self.handler.is_canadian_ticker("TEST.CN"))
        self.assertTrue(self.handler.is_canadian_ticker("EXAMPLE.TSX"))
        
        self.assertFalse(self.handler.is_canadian_ticker("AAPL"))
        self.assertFalse(self.handler.is_canadian_ticker("MSFT"))
        self.assertFalse(self.handler.is_canadian_ticker("^RUT"))
    
    def test_is_us_ticker(self):
        """Test US ticker detection."""
        self.assertTrue(self.handler.is_us_ticker("AAPL"))
        self.assertTrue(self.handler.is_us_ticker("MSFT"))
        self.assertTrue(self.handler.is_us_ticker("GOOGL"))
        
        self.assertFalse(self.handler.is_us_ticker("SHOP.TO"))
        self.assertFalse(self.handler.is_us_ticker("BB.TO"))
        self.assertFalse(self.handler.is_us_ticker("^RUT"))  # Index
        self.assertFalse(self.handler.is_us_ticker("VOD.L"))  # London
    
    def test_get_ticker_currency(self):
        """Test ticker currency detection."""
        self.assertEqual(self.handler.get_ticker_currency("SHOP.TO"), "CAD")
        self.assertEqual(self.handler.get_ticker_currency("BB.TO"), "CAD")
        self.assertEqual(self.handler.get_ticker_currency("WEED.V"), "CAD")
        
        self.assertEqual(self.handler.get_ticker_currency("AAPL"), "USD")
        self.assertEqual(self.handler.get_ticker_currency("MSFT"), "USD")
        self.assertEqual(self.handler.get_ticker_currency("^RUT"), "USD")  # Default to USD
    
    def test_detect_currency_context(self):
        """Test currency detection with price context."""
        # Standard detection should work
        self.assertEqual(self.handler.detect_currency_context("SHOP.TO"), "CAD")
        self.assertEqual(self.handler.detect_currency_context("AAPL"), "USD")
        
        # With price context (should not override ticker-based detection)
        self.assertEqual(self.handler.detect_currency_context("AAPL", 0.50), "USD")
        self.assertEqual(self.handler.detect_currency_context("SHOP.TO", 150.00), "CAD")
    
    def test_get_exchange_rate(self):
        """Test exchange rate retrieval."""
        # Test default rates
        rate_usd_to_cad = self.handler.get_exchange_rate("USD", "CAD")
        self.assertEqual(rate_usd_to_cad, Decimal('1.35'))
        
        rate_cad_to_usd = self.handler.get_exchange_rate("CAD", "USD")
        self.assertEqual(rate_cad_to_usd, Decimal('0.74'))
        
        # Same currency should be 1.0
        rate_usd_to_usd = self.handler.get_exchange_rate("USD", "USD")
        self.assertEqual(rate_usd_to_usd, Decimal('1.00'))
    
    def test_convert_currency(self):
        """Test currency conversion with fees."""
        result = self.handler.convert_currency(1000, "USD", "CAD", 0.015)
        
        # Fee is calculated on original amount: 1000 * 0.015 = 15.00 USD
        # Amount after fee in USD: 1000 - 15 = 985 USD
        # Convert to CAD: 985 * 1.35 = 1329.75 CAD
        # Amount before fee would be: 1000 * 1.35 = 1350 CAD
        self.assertEqual(result['amount_before_fee'], Decimal('1350.00'))
        self.assertEqual(result['fee_charged'], Decimal('15.00'))
        self.assertEqual(result['amount_after_fee'], Decimal('1329.75'))
        self.assertEqual(result['exchange_rate'], Decimal('1.35'))
        self.assertEqual(result['fee_rate'], Decimal('0.0150'))
    
    def test_get_trade_currency_info(self):
        """Test trade currency information."""
        info = self.handler.get_trade_currency_info("SHOP.TO", 100, 150.50)
        
        self.assertEqual(info['ticker'], "SHOP.TO")
        self.assertEqual(info['currency'], "CAD")
        self.assertEqual(info['shares'], Decimal('100.00'))
        self.assertEqual(info['price'], Decimal('150.50'))
        self.assertEqual(info['cost'], Decimal('15050.00'))
        self.assertTrue(info['is_canadian'])
        self.assertFalse(info['is_us'])
    
    def test_format_cash_display(self):
        """Test cash display formatting."""
        balances = CashBalances(cad=1000.50, usd=750.25)
        
        # Without total
        display = self.handler.format_cash_display(balances, show_total=False)
        expected = "CAD $1,000.50 | USD $750.25"
        self.assertEqual(display, expected)
        
        # With total
        display = self.handler.format_cash_display(balances, show_total=True)
        # Total: 1000.50 + (750.25 * 1.35) = 1000.50 + 1012.84 = 2013.34
        self.assertIn("CAD $1,000.50 | USD $750.25", display)
        self.assertIn("Total: CAD $2,013.34", display)


class TestCurrencyHandlerWithStorage(unittest.TestCase):
    """Test CurrencyHandler with file storage."""
    
    def setUp(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir)
        self.handler = CurrencyHandler(self.data_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_save_and_load_cash_balances(self):
        """Test saving and loading cash balances."""
        # Create balances
        original_balances = CashBalances(cad=1000.50, usd=750.25, id="test_id")
        
        # Save balances
        self.handler.save_cash_balances(original_balances)
        
        # Load balances
        loaded_balances = self.handler.load_cash_balances()
        
        # Verify they match
        self.assertEqual(loaded_balances.cad, original_balances.cad)
        self.assertEqual(loaded_balances.usd, original_balances.usd)
        self.assertEqual(loaded_balances.id, original_balances.id)
    
    def test_load_nonexistent_cash_balances(self):
        """Test loading cash balances when file doesn't exist."""
        balances = self.handler.load_cash_balances()
        
        self.assertEqual(balances.cad, Decimal('0.00'))
        self.assertEqual(balances.usd, Decimal('0.00'))
    
    def test_load_corrupted_cash_balances(self):
        """Test loading cash balances from corrupted file."""
        # Create corrupted file
        cash_file = self.data_dir / "cash_balances.json"
        cash_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cash_file, 'w') as f:
            f.write("invalid json content")
        
        # Should return default balances
        balances = self.handler.load_cash_balances()
        self.assertEqual(balances.cad, Decimal('0.00'))
        self.assertEqual(balances.usd, Decimal('0.00'))


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the live API for convenience functions too
        import financial.currency_handler as ch
        self.original_get_live = ch.CurrencyHandler._get_live_exchange_rate
        ch.CurrencyHandler._get_live_exchange_rate = lambda self, from_curr, to_curr: None
    
    def tearDown(self):
        """Restore original method."""
        import financial.currency_handler as ch
        ch.CurrencyHandler._get_live_exchange_rate = self.original_get_live
    
    def test_is_canadian_ticker_function(self):
        """Test standalone is_canadian_ticker function."""
        self.assertTrue(is_canadian_ticker("SHOP.TO"))
        self.assertFalse(is_canadian_ticker("AAPL"))
    
    def test_is_us_ticker_function(self):
        """Test standalone is_us_ticker function."""
        self.assertTrue(is_us_ticker("AAPL"))
        self.assertFalse(is_us_ticker("SHOP.TO"))
    
    def test_get_ticker_currency_function(self):
        """Test standalone get_ticker_currency function."""
        self.assertEqual(get_ticker_currency("SHOP.TO"), "CAD")
        self.assertEqual(get_ticker_currency("AAPL"), "USD")
    
    def test_calculate_conversion_with_fee_function(self):
        """Test standalone calculate_conversion_with_fee function."""
        result = calculate_conversion_with_fee(1000, "USD", "CAD", 0.015)
        
        self.assertEqual(result['amount_before_fee'], Decimal('1350.00'))
        self.assertEqual(result['fee_charged'], Decimal('15.00'))
        self.assertEqual(result['amount_after_fee'], Decimal('1329.75'))


class TestExchangeRateCache(unittest.TestCase):
    """Test exchange rate caching functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = CurrencyHandler()
    
    def test_exchange_rate_caching(self):
        """Test that exchange rates are cached."""
        # First call should cache the rate
        rate1 = self.handler.get_exchange_rate("USD", "CAD")
        
        # Second call should use cached rate
        rate2 = self.handler.get_exchange_rate("USD", "CAD")
        
        self.assertEqual(rate1, rate2)
        self.assertIn(("USD", "CAD", None), self.handler._exchange_rate_cache)
    
    def test_clear_exchange_rate_cache(self):
        """Test clearing the exchange rate cache."""
        # Cache a rate
        self.handler.get_exchange_rate("USD", "CAD")
        self.assertTrue(len(self.handler._exchange_rate_cache) > 0)
        
        # Clear cache
        self.handler.clear_exchange_rate_cache()
        self.assertEqual(len(self.handler._exchange_rate_cache), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.handler = CurrencyHandler()
        # Disable live API calls for testing
        self.handler._get_live_exchange_rate = lambda from_curr, to_curr: None
    
    def test_empty_ticker(self):
        """Test handling of empty ticker."""
        self.assertEqual(self.handler.get_ticker_currency(""), "USD")  # Default
        self.assertEqual(self.handler.get_ticker_currency("   "), "USD")  # Whitespace
    
    def test_case_insensitive_ticker(self):
        """Test case insensitive ticker handling."""
        self.assertEqual(self.handler.get_ticker_currency("shop.to"), "CAD")
        self.assertEqual(self.handler.get_ticker_currency("SHOP.TO"), "CAD")
        self.assertEqual(self.handler.get_ticker_currency("Shop.To"), "CAD")
    
    def test_zero_amounts(self):
        """Test handling of zero amounts."""
        balances = CashBalances(cad=0, usd=0)
        
        self.assertFalse(balances.can_afford_cad(1))
        self.assertFalse(balances.can_afford_usd(1))
        self.assertTrue(balances.can_afford_cad(0))
        self.assertTrue(balances.can_afford_usd(0))
    
    def test_negative_amounts(self):
        """Test handling of negative amounts in calculations."""
        # Currency conversion should work with negative amounts (refunds, etc.)
        result = self.handler.convert_currency(-100, "USD", "CAD", 0.015)
        
        # Fee on original amount: -100 * 0.015 = -1.50 USD
        # Amount after fee in USD: -100 - (-1.50) = -100 + 1.50 = -98.50 USD
        # Convert to CAD: -98.50 * 1.35 = -132.975 ≈ -132.98 CAD
        # Amount before fee would be: -100 * 1.35 = -135 CAD
        self.assertEqual(result['amount_before_fee'], Decimal('-135.00'))
        self.assertEqual(result['fee_charged'], Decimal('-1.50'))
        self.assertEqual(result['amount_after_fee'], Decimal('-132.98'))


if __name__ == '__main__':
    unittest.main()