#!/usr/bin/env python3
"""
Comprehensive Duplicate Prevention Test Suite

This test suite validates that portfolio CSV updates don't create duplicate rows
under various market conditions and timing scenarios.

The tests simulate different times of day and market status to ensure the
duplicate prevention logic works correctly across all scenarios.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
import sys
from unittest.mock import patch, MagicMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.csv_repository import CSVRepository
from data.models.portfolio import Position, PortfolioSnapshot
from market_data.market_hours import MarketHours
import pytz


class MockMarketHours:
    """Mock market hours class for testing different time scenarios."""
    
    def __init__(self, is_open=False, current_time=None, timezone="US/Pacific"):
        self._is_open = is_open
        self._current_time = current_time or datetime.now(pytz.timezone(timezone))
        self._timezone = timezone
    
    def is_market_open(self, target_time=None):
        """Return mocked market status."""
        return self._is_open
    
    def get_trading_timezone(self):
        """Return mocked timezone."""
        return pytz.timezone(self._timezone)
    
    def last_trading_date(self, today=None):
        """Return mocked last trading date."""
        return pd.Timestamp(self._current_time.date())


class TestDuplicatePrevention(unittest.TestCase):
    """Test portfolio CSV duplicate prevention under various scenarios."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_duplicate_"))
        self.repository = CSVRepository(fund_name="TEST", data_directory=str(self.test_dir))
        
        # Create test positions
        self.test_positions = [
            Position(
                ticker="ABEO",
                shares=Decimal("4.0"),
                avg_price=Decimal("5.77"),
                cost_basis=Decimal("23.08"),
                current_price=Decimal("6.89"),
                market_value=Decimal("27.56"),
                unrealized_pnl=Decimal("4.48"),
                company="Abeona Therapeutics Inc.",
                currency="USD"
            ),
            Position(
                ticker="ATYR",
                shares=Decimal("12.0"),
                avg_price=Decimal("5.21"),
                cost_basis=Decimal("62.48"),
                current_price=Decimal("5.61"),
                market_value=Decimal("67.32"),
                unrealized_pnl=Decimal("4.84"),
                company="aTyr Pharma Inc.",
                currency="USD"
            )
        ]
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _create_initial_snapshot(self, timestamp=None):
        """Helper to create initial portfolio snapshot."""
        timestamp = timestamp or datetime.now()
        return PortfolioSnapshot(
            positions=self.test_positions.copy(),
            timestamp=timestamp
        )
    
    def _update_positions_prices(self, positions, price_change=0.05):
        """Helper to update positions with new prices."""
        updated_positions = []
        for pos in positions:
            new_price = pos.current_price + Decimal(str(price_change))
            updated_pos = Position(
                ticker=pos.ticker,
                shares=pos.shares,
                avg_price=pos.avg_price,
                cost_basis=pos.cost_basis,
                current_price=new_price,
                market_value=new_price * pos.shares,
                unrealized_pnl=(new_price - pos.avg_price) * pos.shares,
                company=pos.company,
                currency=pos.currency
            )
            updated_positions.append(updated_pos)
        return updated_positions
    
    def _get_csv_row_count(self):
        """Helper to get current CSV row count."""
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        if not csv_file.exists():
            return 0
        df = pd.read_csv(csv_file)
        return len(df)
    
    def _get_csv_tickers(self):
        """Helper to get tickers from CSV."""
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        if not csv_file.exists():
            return []
        df = pd.read_csv(csv_file)
        return df['Ticker'].tolist()

    def test_basic_duplicate_prevention(self):
        """Test basic duplicate prevention functionality."""
        # Create initial snapshot
        initial_snapshot = self._create_initial_snapshot()
        self.repository.save_portfolio_snapshot(initial_snapshot)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 2)  # Two positions
        
        # Update prices (simulate refreshing portfolio)
        updated_positions = self._update_positions_prices(self.test_positions)
        updated_snapshot = PortfolioSnapshot(
            positions=updated_positions,
            timestamp=datetime.now()
        )
        
        # This should UPDATE existing rows, not ADD new ones
        self.repository.update_daily_portfolio_snapshot(updated_snapshot)
        
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, initial_count, 
                        "update_daily_portfolio_snapshot should not create duplicate rows")
        
        # Verify prices were actually updated
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        abeo_row = df[df['Ticker'] == 'ABEO'].iloc[0]
        self.assertAlmostEqual(float(abeo_row['Current Price']), 6.94, places=2)

    def test_market_open_scenario(self):
        """Test duplicate prevention during market hours."""
        # Mock market as open
        mock_market_hours = MockMarketHours(is_open=True)
        
        with patch('market_data.market_hours.MarketHours', return_value=mock_market_hours):
            # Create initial snapshot
            initial_snapshot = self._create_initial_snapshot()
            self.repository.save_portfolio_snapshot(initial_snapshot)
            
            initial_count = self._get_csv_row_count()
            
            # Simulate multiple price refreshes during market hours
            for i in range(3):
                updated_positions = self._update_positions_prices(
                    self.test_positions, price_change=0.01 * (i + 1)
                )
                updated_snapshot = PortfolioSnapshot(
                    positions=updated_positions,
                    timestamp=datetime.now()
                )
                self.repository.update_daily_portfolio_snapshot(updated_snapshot)
                
                current_count = self._get_csv_row_count()
                self.assertEqual(current_count, initial_count,
                               f"Market open refresh #{i+1} should not create duplicates")

    def test_market_closed_scenario(self):
        """Test duplicate prevention after market close."""
        # Mock market as closed
        mock_market_hours = MockMarketHours(is_open=False)
        
        with patch('market_data.market_hours.MarketHours', return_value=mock_market_hours):
            # Create initial snapshot
            initial_snapshot = self._create_initial_snapshot()
            self.repository.save_portfolio_snapshot(initial_snapshot)
            
            initial_count = self._get_csv_row_count()
            
            # Simulate price refresh after market close
            updated_positions = self._update_positions_prices(self.test_positions)
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=datetime.now()
            )
            self.repository.update_daily_portfolio_snapshot(updated_snapshot)
            
            final_count = self._get_csv_row_count()
            self.assertEqual(final_count, initial_count,
                           "After-hours refresh should not create duplicates")

    def test_same_day_multiple_refreshes(self):
        """Test multiple refreshes on the same day don't create duplicates."""
        base_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        
        # Create initial snapshot at 10 AM
        initial_snapshot = self._create_initial_snapshot(base_time)
        self.repository.save_portfolio_snapshot(initial_snapshot)
        
        initial_count = self._get_csv_row_count()
        
        # Simulate refreshes throughout the day
        times = [
            base_time.replace(hour=11),  # 11 AM
            base_time.replace(hour=12),  # 12 PM  
            base_time.replace(hour=13),  # 1 PM (market close)
            base_time.replace(hour=14),  # 2 PM (after hours)
        ]
        
        for i, refresh_time in enumerate(times):
            updated_positions = self._update_positions_prices(
                self.test_positions, price_change=0.01 * (i + 2)
            )
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=refresh_time
            )
            self.repository.update_daily_portfolio_snapshot(updated_snapshot)
            
            current_count = self._get_csv_row_count()
            self.assertEqual(current_count, initial_count,
                           f"Same-day refresh at {refresh_time.hour}:00 should not create duplicates")

    def test_new_position_added(self):
        """Test that genuinely new positions are added correctly."""
        # Create initial snapshot
        initial_snapshot = self._create_initial_snapshot()
        self.repository.save_portfolio_snapshot(initial_snapshot)
        
        initial_count = self._get_csv_row_count()
        initial_tickers = set(self._get_csv_tickers())
        
        # Add a new position
        new_position = Position(
            ticker="NEWCO",
            shares=Decimal("10.0"),
            avg_price=Decimal("2.50"),
            cost_basis=Decimal("25.00"),
            current_price=Decimal("2.75"),
            market_value=Decimal("27.50"),
            unrealized_pnl=Decimal("2.50"),
            company="New Company Inc.",
            currency="USD"
        )
        
        all_positions = self.test_positions + [new_position]
        updated_snapshot = PortfolioSnapshot(
            positions=all_positions,
            timestamp=datetime.now()
        )
        
        self.repository.update_daily_portfolio_snapshot(updated_snapshot)
        
        final_count = self._get_csv_row_count()
        final_tickers = set(self._get_csv_tickers())
        
        # Should have one more row (new position)
        self.assertEqual(final_count, initial_count + 1,
                        "New position should add exactly one row")
        
        # Should have all original tickers plus the new one
        expected_tickers = initial_tickers | {"NEWCO"}
        self.assertEqual(final_tickers, expected_tickers,
                        "Should have all original tickers plus new ticker")

    def test_position_removed_then_readded(self):
        """Test position that was sold and then bought again."""
        # Create initial snapshot with two positions
        initial_snapshot = self._create_initial_snapshot()
        self.repository.save_portfolio_snapshot(initial_snapshot)
        
        # Remove one position (simulate selling)
        remaining_positions = [pos for pos in self.test_positions if pos.ticker != "ATYR"]
        reduced_snapshot = PortfolioSnapshot(
            positions=remaining_positions,
            timestamp=datetime.now()
        )
        self.repository.update_daily_portfolio_snapshot(reduced_snapshot)
        
        # Add the position back (simulate re-buying)
        atyr_position = Position(
            ticker="ATYR",
            shares=Decimal("5.0"),  # Different quantity
            avg_price=Decimal("6.00"),  # Different price
            cost_basis=Decimal("30.00"),
            current_price=Decimal("6.25"),
            market_value=Decimal("31.25"),
            unrealized_pnl=Decimal("1.25"),
            company="aTyr Pharma Inc.",
            currency="USD"
        )
        
        full_positions = remaining_positions + [atyr_position]
        restored_snapshot = PortfolioSnapshot(
            positions=full_positions,
            timestamp=datetime.now()
        )
        self.repository.update_daily_portfolio_snapshot(restored_snapshot)
        
        # Should have original number of positions
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, 2, "Re-added position should not create duplicates")
        
        # Verify ATYR is back with new values
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        atyr_rows = df[df['Ticker'] == 'ATYR']
        self.assertEqual(len(atyr_rows), 1, "Should have exactly one ATYR row")
        
        atyr_row = atyr_rows.iloc[0]
        self.assertEqual(float(atyr_row['Shares']), 5.0)
        self.assertAlmostEqual(float(atyr_row['Average Price']), 6.00, places=2)

    def test_weekend_portfolio_refresh(self):
        """Test portfolio refresh on weekends doesn't create duplicates."""
        # Create snapshot on Friday
        friday = datetime.now()
        friday = friday.replace(hour=13, minute=0, second=0, microsecond=0)  # After market close
        
        friday_snapshot = self._create_initial_snapshot(friday)
        self.repository.save_portfolio_snapshot(friday_snapshot)
        
        initial_count = self._get_csv_row_count()
        
        # Simulate weekend refresh (Saturday)
        saturday = friday + timedelta(days=1)
        updated_positions = self._update_positions_prices(self.test_positions)
        weekend_snapshot = PortfolioSnapshot(
            positions=updated_positions,
            timestamp=saturday
        )
        
        # This should create new rows for Saturday (different date)
        self.repository.update_daily_portfolio_snapshot(weekend_snapshot)
        
        weekend_count = self._get_csv_row_count()
        self.assertEqual(weekend_count, initial_count + 2,  # New date = new rows
                        "Weekend refresh should add rows for new date")
        
        # But additional refreshes on Saturday should not create more duplicates
        updated_positions_2 = self._update_positions_prices(self.test_positions, 0.10)
        weekend_snapshot_2 = PortfolioSnapshot(
            positions=updated_positions_2,
            timestamp=saturday
        )
        self.repository.update_daily_portfolio_snapshot(weekend_snapshot_2)
        
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, weekend_count,
                        "Second weekend refresh should not create more duplicates")

    def test_cross_function_consistency(self):
        """Test that save_portfolio_snapshot and update_daily_portfolio_snapshot are consistent."""
        timestamp = datetime.now()
        
        # Create snapshot using save_portfolio_snapshot
        snapshot1 = self._create_initial_snapshot(timestamp)
        self.repository.save_portfolio_snapshot(snapshot1)
        
        count_after_save = self._get_csv_row_count()
        
        # Try to "update" with same data using update_daily_portfolio_snapshot
        snapshot2 = self._create_initial_snapshot(timestamp)  # Same timestamp, same data
        self.repository.update_daily_portfolio_snapshot(snapshot2)
        
        count_after_update = self._get_csv_row_count()
        
        # Should not have added duplicates
        self.assertEqual(count_after_update, count_after_save,
                        "update_daily_portfolio_snapshot should not duplicate save_portfolio_snapshot data")

    def test_rapid_successive_updates(self):
        """Test rapid successive updates don't create race condition duplicates."""
        # Create initial snapshot
        initial_snapshot = self._create_initial_snapshot()
        self.repository.save_portfolio_snapshot(initial_snapshot)
        
        initial_count = self._get_csv_row_count()
        
        # Simulate rapid successive updates (like user clicking refresh repeatedly)
        for i in range(10):
            updated_positions = self._update_positions_prices(
                self.test_positions, price_change=0.001 * i  # Very small changes
            )
            updated_snapshot = PortfolioSnapshot(
                positions=updated_positions,
                timestamp=datetime.now()  # All same day
            )
            self.repository.update_daily_portfolio_snapshot(updated_snapshot)
            
            current_count = self._get_csv_row_count()
            self.assertEqual(current_count, initial_count,
                           f"Rapid update #{i+1} should not create duplicates")

    def test_timezone_consistency(self):
        """Test that different timezone inputs don't create duplicate issues."""
        # Create timestamps in different timezones but same actual time
        utc_time = datetime.now(pytz.UTC)
        pst_time = utc_time.astimezone(pytz.timezone('US/Pacific'))
        est_time = utc_time.astimezone(pytz.timezone('US/Eastern'))
        
        # Create snapshot with UTC timestamp
        utc_snapshot = PortfolioSnapshot(
            positions=self.test_positions.copy(),
            timestamp=utc_time
        )
        self.repository.save_portfolio_snapshot(utc_snapshot)
        
        initial_count = self._get_csv_row_count()
        
        # Update with PST timestamp (same actual time)
        updated_positions = self._update_positions_prices(self.test_positions)
        pst_snapshot = PortfolioSnapshot(
            positions=updated_positions,
            timestamp=pst_time
        )
        self.repository.update_daily_portfolio_snapshot(pst_snapshot)
        
        count_after_pst = self._get_csv_row_count()
        self.assertEqual(count_after_pst, initial_count,
                        "Same-day update with different timezone should not create duplicates")


class TestDuplicatePreventionIntegration(unittest.TestCase):
    """Integration tests with actual market hours and timing components."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_duplicate_integration_"))
        self.repository = CSVRepository(fund_name="TEST", data_directory=str(self.test_dir))
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_with_real_market_hours(self):
        """Test duplicate prevention with real MarketHours component."""
        from market_data.market_hours import MarketHours
        
        market_hours = MarketHours()
        
        # Test that the market hours component integrates correctly
        is_open = market_hours.is_market_open()
        self.assertIsInstance(is_open, bool)
        
        # Test that we can get timezone info
        tz = market_hours.get_trading_timezone()
        self.assertIsNotNone(tz)
        
        # Test last trading date functionality
        last_date = market_hours.last_trading_date()
        self.assertIsNotNone(last_date)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)