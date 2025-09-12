"""
Unit tests for data models.

Tests cover Position, Trade, PortfolioSnapshot, and MarketData models
with serialization, validation, and edge cases.
"""

import unittest
from decimal import Decimal
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.models.portfolio import Position, PortfolioSnapshot
from data.models.trade import Trade
from data.models.market_data import MarketData


class TestPosition(unittest.TestCase):
    """Test Position data model."""
    
    def test_position_initialization(self):
        """Test Position initialization with various input types."""
        position = Position(
            ticker="AAPL",
            shares=Decimal('100.5'),
            avg_price=Decimal('150.75'),
            cost_basis=Decimal('15075.00'),
            current_price=Decimal('155.25')
        )
        
        self.assertEqual(position.ticker, "AAPL")
        self.assertEqual(position.shares, Decimal('100.5'))
        self.assertEqual(position.avg_price, Decimal('150.75'))
        self.assertEqual(position.current_price, Decimal('155.25'))
        self.assertEqual(position.cost_basis, Decimal('15075.00'))
    
    def test_position_serialization(self):
        """Test Position to_dict and from_dict methods."""
        original = Position(
            ticker="AAPL",
            shares=Decimal('100.5'),
            avg_price=Decimal('150.75'),
            cost_basis=Decimal('15075.00'),
            current_price=Decimal('155.25'),
            currency="USD",
            position_id="pos_123"
        )
        
        # Test to_dict
        data = original.to_dict()
        expected_keys = [
            'ticker', 'shares', 'avg_price', 'cost_basis', 'currency',
            'position_id', 'current_price', 'market_value', 'unrealized_pnl'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)
        
        # Test from_dict
        restored = Position.from_dict(data)
        self.assertEqual(restored.ticker, original.ticker)
        self.assertEqual(restored.shares, original.shares)
        self.assertEqual(restored.avg_price, original.avg_price)
        self.assertEqual(restored.current_price, original.current_price)
        self.assertEqual(restored.currency, original.currency)
        self.assertEqual(restored.position_id, original.position_id)
    
    def test_position_csv_serialization(self):
        """Test Position CSV serialization methods."""
        position = Position(
            ticker="AAPL",
            shares=Decimal('100'),
            avg_price=Decimal('150.00'),
            cost_basis=Decimal('15000.00'),
            current_price=Decimal('155.00'),
            market_value=Decimal('15500.00'),
            unrealized_pnl=Decimal('500.00')
        )
        
        # Test to_csv_dict
        csv_data = position.to_csv_dict()
        expected_keys = [
            'Ticker', 'Shares', 'Average Price', 'Cost Basis', 'Currency',
            'Current Price', 'Total Value', 'PnL'
        ]
        
        for key in expected_keys:
            self.assertIn(key, csv_data)
        
        # Test from_csv_dict
        restored = Position.from_csv_dict(csv_data)
        self.assertEqual(restored.ticker, position.ticker)
        self.assertEqual(restored.shares, position.shares)


class TestTrade(unittest.TestCase):
    """Test Trade data model."""
    
    def test_trade_initialization(self):
        """Test Trade initialization."""
        timestamp = datetime.now(timezone.utc)
        trade = Trade(
            ticker="AAPL",
            action="BUY",
            shares=Decimal('100'),
            price=Decimal('150.75'),
            timestamp=timestamp
        )
        
        self.assertEqual(trade.ticker, "AAPL")
        self.assertEqual(trade.action, "BUY")
        self.assertEqual(trade.shares, Decimal('100'))
        self.assertEqual(trade.price, Decimal('150.75'))
        self.assertEqual(trade.timestamp, timestamp)
        self.assertEqual(trade.currency, "CAD")  # Default
    
    def test_trade_calculated_properties(self):
        """Test Trade calculated properties."""
        trade = Trade(
            ticker="AAPL",
            action="BUY",
            shares=Decimal('100'),
            price=Decimal('150.75'),
            timestamp=datetime.now(timezone.utc)
        )
        
        # Test calculate_cost_basis method
        cost_basis = trade.calculate_cost_basis()
        self.assertEqual(cost_basis, Decimal('15075.00'))
        
        # Test is_buy and is_sell methods
        self.assertTrue(trade.is_buy())
        self.assertFalse(trade.is_sell())
        
        # Test sell trade
        sell_trade = Trade(
            ticker="AAPL",
            action="SELL",
            shares=Decimal('50'),
            price=Decimal('155.00'),
            timestamp=datetime.now(timezone.utc)
        )
        
        self.assertFalse(sell_trade.is_buy())
        self.assertTrue(sell_trade.is_sell())
    
    def test_trade_serialization(self):
        """Test Trade to_dict and from_dict methods."""
        timestamp = datetime.now(timezone.utc)
        original = Trade(
            ticker="AAPL",
            action="BUY",
            shares=Decimal('100'),
            price=Decimal('150.75'),
            timestamp=timestamp,
            currency="USD",
            trade_id="trade_123"
        )
        
        # Test to_dict
        data = original.to_dict()
        expected_keys = [
            'ticker', 'action', 'shares', 'price', 'timestamp',
            'currency', 'trade_id'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)
        
        # Test from_dict
        restored = Trade.from_dict(data)
        self.assertEqual(restored.ticker, original.ticker)
        self.assertEqual(restored.action, original.action)
        self.assertEqual(restored.shares, original.shares)
        self.assertEqual(restored.price, original.price)
        self.assertEqual(restored.currency, original.currency)
        self.assertEqual(restored.trade_id, original.trade_id)
    
    def test_trade_csv_serialization(self):
        """Test Trade CSV serialization methods."""
        timestamp = datetime.now(timezone.utc)
        trade = Trade(
            ticker="AAPL",
            action="BUY",
            shares=Decimal('100'),
            price=Decimal('150.75'),
            timestamp=timestamp,
            cost_basis=Decimal('15075.00'),
            pnl=Decimal('500.00'),
            reason="Good fundamentals"
        )
        
        # Test to_csv_dict
        csv_data = trade.to_csv_dict()
        expected_keys = [
            'Date', 'Ticker', 'Shares Bought', 'Buy Price', 'Cost Basis', 'PnL', 'Reason'
        ]
        
        for key in expected_keys:
            self.assertIn(key, csv_data)
        
        # Test from_csv_dict
        restored = Trade.from_csv_dict(csv_data, timestamp)
        self.assertEqual(restored.ticker, trade.ticker)
        self.assertEqual(restored.shares, trade.shares)


class TestPortfolioSnapshot(unittest.TestCase):
    """Test PortfolioSnapshot data model."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.positions = [
            Position(ticker="AAPL", shares=Decimal('100'), avg_price=Decimal('150.00'), 
                    cost_basis=Decimal('15000.00'), current_price=Decimal('155.00')),
            Position(ticker="GOOGL", shares=Decimal('50'), avg_price=Decimal('2000.00'), 
                    cost_basis=Decimal('100000.00'), current_price=Decimal('2100.00')),
        ]
        self.timestamp = datetime.now(timezone.utc)
    
    def test_portfolio_snapshot_initialization(self):
        """Test PortfolioSnapshot initialization."""
        snapshot = PortfolioSnapshot(
            positions=self.positions,
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp
        )
        
        self.assertEqual(len(snapshot.positions), 2)
        self.assertEqual(snapshot.cash_balance, Decimal('5000.00'))
        self.assertEqual(snapshot.timestamp, self.timestamp)
    
    def test_portfolio_snapshot_calculated_properties(self):
        """Test PortfolioSnapshot calculated properties."""
        # Set market values for positions
        self.positions[0].market_value = Decimal('15500.00')  # 100 * 155
        self.positions[1].market_value = Decimal('105000.00')  # 50 * 2100
        
        snapshot = PortfolioSnapshot(
            positions=self.positions,
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp
        )
        
        # Test calculate_total_value method
        total_value = snapshot.calculate_total_value()
        self.assertEqual(total_value, Decimal('120500.00'))  # 15500 + 105000
    
    def test_portfolio_snapshot_serialization(self):
        """Test PortfolioSnapshot to_dict and from_dict methods."""
        original = PortfolioSnapshot(
            positions=self.positions,
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp,
            snapshot_id="snap_123"
        )
        
        # Test to_dict
        data = original.to_dict()
        expected_keys = [
            'positions', 'cash_balance', 'timestamp', 'snapshot_id'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)
        
        # Test from_dict
        restored = PortfolioSnapshot.from_dict(data)
        self.assertEqual(len(restored.positions), len(original.positions))
        self.assertEqual(restored.cash_balance, original.cash_balance)
        self.assertEqual(restored.snapshot_id, original.snapshot_id)
    
    def test_portfolio_snapshot_get_position(self):
        """Test getting position by ticker."""
        snapshot = PortfolioSnapshot(
            positions=self.positions,
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp
        )
        
        # Test existing position
        aapl_position = snapshot.get_position_by_ticker("AAPL")
        self.assertIsNotNone(aapl_position)
        self.assertEqual(aapl_position.ticker, "AAPL")
        
        # Test non-existing position
        tsla_position = snapshot.get_position_by_ticker("TSLA")
        self.assertIsNone(tsla_position)
    
    def test_portfolio_snapshot_add_position(self):
        """Test adding position to snapshot."""
        snapshot = PortfolioSnapshot(
            positions=self.positions.copy(),
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp
        )
        
        new_position = Position(ticker="TSLA", shares=Decimal('25'), avg_price=Decimal('800.00'), 
                               cost_basis=Decimal('20000.00'), current_price=Decimal('850.00'))
        snapshot.add_position(new_position)
        
        self.assertEqual(len(snapshot.positions), 3)
        self.assertIsNotNone(snapshot.get_position_by_ticker("TSLA"))
    
    def test_portfolio_snapshot_remove_position(self):
        """Test removing position from snapshot."""
        snapshot = PortfolioSnapshot(
            positions=self.positions.copy(),
            cash_balance=Decimal('5000.00'),
            timestamp=self.timestamp
        )
        
        result = snapshot.remove_position("AAPL")
        self.assertTrue(result)
        self.assertEqual(len(snapshot.positions), 1)
        self.assertIsNone(snapshot.get_position_by_ticker("AAPL"))
        
        # Test removing non-existing position
        result = snapshot.remove_position("TSLA")
        self.assertFalse(result)


class TestMarketData(unittest.TestCase):
    """Test MarketData model."""
    
    def test_market_data_initialization(self):
        """Test MarketData initialization."""
        date = datetime.now(timezone.utc)
        market_data = MarketData(
            ticker="AAPL",
            date=date,
            open_price=Decimal('150.00'),
            high_price=Decimal('157.00'),
            low_price=Decimal('149.00'),
            close_price=Decimal('155.75'),
            volume=1000000
        )
        
        self.assertEqual(market_data.ticker, "AAPL")
        self.assertEqual(market_data.date, date)
        self.assertEqual(market_data.close_price, Decimal('155.75'))
        self.assertEqual(market_data.volume, 1000000)
    
    def test_market_data_serialization(self):
        """Test MarketData serialization."""
        date = datetime.now(timezone.utc)
        original = MarketData(
            ticker="AAPL",
            date=date,
            open_price=Decimal('150.00'),
            high_price=Decimal('157.00'),
            low_price=Decimal('149.00'),
            close_price=Decimal('155.75'),
            volume=1000000,
            source="yahoo",
            data_id="md_123"
        )
        
        # Test to_dict
        data = original.to_dict()
        expected_keys = [
            'ticker', 'date', 'open', 'high', 'low', 'close', 'volume', 'source', 'data_id'
        ]
        
        for key in expected_keys:
            self.assertIn(key, data)
        
        # Test from_dict
        restored = MarketData.from_dict(data)
        self.assertEqual(restored.ticker, original.ticker)
        self.assertEqual(restored.close_price, original.close_price)
        self.assertEqual(restored.source, original.source)
        self.assertEqual(restored.data_id, original.data_id)
    
    def test_market_data_get_price(self):
        """Test MarketData get_price method."""
        market_data = MarketData(
            ticker="AAPL",
            date=datetime.now(timezone.utc),
            open_price=Decimal('150.00'),
            high_price=Decimal('157.00'),
            low_price=Decimal('149.00'),
            close_price=Decimal('155.75')
        )
        
        self.assertEqual(market_data.get_price("open"), Decimal('150.00'))
        self.assertEqual(market_data.get_price("high"), Decimal('157.00'))
        self.assertEqual(market_data.get_price("low"), Decimal('149.00'))
        self.assertEqual(market_data.get_price("close"), Decimal('155.75'))
        self.assertIsNone(market_data.get_price("invalid"))
    
    def test_market_data_has_complete_ohlc(self):
        """Test MarketData has_complete_ohlc method."""
        # Complete OHLC data
        complete_data = MarketData(
            ticker="AAPL",
            date=datetime.now(timezone.utc),
            open_price=Decimal('150.00'),
            high_price=Decimal('157.00'),
            low_price=Decimal('149.00'),
            close_price=Decimal('155.75')
        )
        self.assertTrue(complete_data.has_complete_ohlc())
        
        # Incomplete OHLC data
        incomplete_data = MarketData(
            ticker="AAPL",
            date=datetime.now(timezone.utc),
            open_price=Decimal('150.00'),
            close_price=Decimal('155.75')
            # Missing high and low
        )
        self.assertFalse(incomplete_data.has_complete_ohlc())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def test_decimal_precision(self):
        """Test decimal precision handling."""
        position = Position(
            ticker="AAPL",
            shares=Decimal('100.123456789'),
            avg_price=Decimal('150.999999'),
            cost_basis=Decimal('15075.00'),
            current_price=Decimal('155.555555')
        )
        
        # Decimals should maintain precision as provided
        self.assertEqual(position.shares, Decimal('100.123456789'))
        self.assertEqual(position.avg_price, Decimal('150.999999'))
        self.assertEqual(position.current_price, Decimal('155.555555'))
    
    def test_zero_values(self):
        """Test handling of zero values."""
        position = Position(
            ticker="AAPL",
            shares=Decimal('0'),
            avg_price=Decimal('150.00'),
            cost_basis=Decimal('0.00'),
            current_price=Decimal('155.00')
        )
        
        self.assertEqual(position.shares, Decimal('0'))
        self.assertEqual(position.cost_basis, Decimal('0.00'))
    
    def test_large_numbers(self):
        """Test handling of large numbers."""
        position = Position(
            ticker="BRK.A",
            shares=Decimal('1'),
            avg_price=Decimal('500000.00'),
            cost_basis=Decimal('500000.00'),
            current_price=Decimal('525000.00')
        )
        
        self.assertEqual(position.avg_price, Decimal('500000.00'))
        self.assertEqual(position.current_price, Decimal('525000.00'))
        self.assertEqual(position.cost_basis, Decimal('500000.00'))
    
    def test_fractional_shares(self):
        """Test handling of fractional shares."""
        position = Position(
            ticker="AAPL",
            shares=Decimal('100.5'),
            avg_price=Decimal('150.00'),
            cost_basis=Decimal('15075.00'),
            current_price=Decimal('155.00')
        )
        
        self.assertEqual(position.shares, Decimal('100.5'))
        self.assertEqual(position.cost_basis, Decimal('15075.00'))


if __name__ == '__main__':
    unittest.main()