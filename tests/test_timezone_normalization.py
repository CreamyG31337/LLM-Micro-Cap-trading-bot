#!/usr/bin/env python3
"""
Test timezone normalization for portfolio CSV operations.

This test validates that the "one row per day" logic works correctly
regardless of the input timezone by normalizing everything to the 
configured trading timezone.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from decimal import Decimal
import pandas as pd
import sys
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.csv_repository import CSVRepository
from data.models.portfolio import Position, PortfolioSnapshot
from utils.timezone_utils import get_trading_timezone


class TestTimezoneNormalization(unittest.TestCase):
    """Test timezone normalization in CSV repository operations."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for test data
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_timezone_"))
        self.repository = CSVRepository(fund_name="TEST", data_directory=str(self.test_dir))
        
        # Get trading timezone for consistent testing - use pytz for localize capability
        import pytz
        self.trading_tz = pytz.timezone('US/Pacific')  # Use pytz for .localize() method
        
        # Create test position
        self.test_position = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("5.00"),
            cost_basis=Decimal("50.00"),
            current_price=Decimal("5.50"),
            market_value=Decimal("55.00"),
            unrealized_pnl=Decimal("5.00"),
            company="Test Company Inc.",
            currency="USD"
        )
    
    def tearDown(self):
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def _get_csv_row_count(self):
        """Helper to get current CSV row count."""
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        if not csv_file.exists():
            return 0
        df = pd.read_csv(csv_file)
        return len(df)
    
    def test_same_day_different_timezones_no_duplicates(self):
        """Test that different timezone inputs for the same day don't create duplicates."""
        # Create base time at 2 PM on a weekday
        base_date = datetime(2023, 11, 15, 14, 0, 0)  # Wednesday, Nov 15, 2023
        
        # Create timestamps in different timezones for the same day
        trading_tz_time = self.trading_tz.localize(base_date)
        utc_time = trading_tz_time.astimezone(pytz.UTC)
        est_time = trading_tz_time.astimezone(pytz.timezone('US/Eastern'))
        
        # Save initial snapshot in trading timezone
        snapshot1 = PortfolioSnapshot(
            positions=[self.test_position],
            timestamp=trading_tz_time
        )
        self.repository.save_portfolio_snapshot(snapshot1)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 1)
        
        # Update with UTC timestamp (same day)
        updated_position = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("5.00"),
            cost_basis=Decimal("50.00"),
            current_price=Decimal("5.75"),  # Price change
            market_value=Decimal("57.50"),
            unrealized_pnl=Decimal("7.50"),
            company="Test Company Inc.",
            currency="USD"
        )
        
        snapshot2 = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=utc_time
        )
        self.repository.update_daily_portfolio_snapshot(snapshot2)
        
        # Should still be 1 row (updated, not duplicated)
        count_after_utc = self._get_csv_row_count()
        self.assertEqual(count_after_utc, initial_count, 
                        "UTC timestamp for same day should not create duplicate")
        
        # Verify price was updated
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        current_price = float(df['Current Price'].iloc[0])
        self.assertAlmostEqual(current_price, 5.75, places=2)
        
        # Update with EST timestamp (same day)
        snapshot3 = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=est_time
        )
        self.repository.update_daily_portfolio_snapshot(snapshot3)
        
        # Should still be 1 row
        count_after_est = self._get_csv_row_count()
        self.assertEqual(count_after_est, initial_count,
                        "EST timestamp for same day should not create duplicate")
    
    def test_naive_vs_aware_timestamps_same_day(self):
        """Test that naive and timezone-aware timestamps for the same day are handled correctly."""
        base_date = datetime(2023, 11, 15, 10, 0, 0)  # Wednesday morning
        
        # Save with naive timestamp (assumed to be in trading timezone)
        naive_snapshot = PortfolioSnapshot(
            positions=[self.test_position],
            timestamp=base_date  # Naive datetime
        )
        self.repository.save_portfolio_snapshot(naive_snapshot)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 1)
        
        # Update with timezone-aware timestamp for the same day
        aware_time = self.trading_tz.localize(base_date.replace(hour=15))  # Later same day
        updated_position = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("5.00"),
            cost_basis=Decimal("50.00"),
            current_price=Decimal("5.25"),  # Price change
            market_value=Decimal("52.50"),
            unrealized_pnl=Decimal("2.50"),
            company="Test Company Inc.",
            currency="USD"
        )
        
        aware_snapshot = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=aware_time
        )
        self.repository.update_daily_portfolio_snapshot(aware_snapshot)
        
        # Should still be 1 row (same day)
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, initial_count,
                        "Timezone-aware timestamp for same day should not create duplicate")
        
        # Verify price was updated
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        current_price = float(df['Current Price'].iloc[0])
        self.assertAlmostEqual(current_price, 5.25, places=2)
    
    def test_cross_timezone_different_days(self):
        """Test that different days in different timezones create new rows appropriately."""
        # Day 1: Save in trading timezone
        day1 = datetime(2023, 11, 15, 10, 0, 0)  # Wednesday
        trading_tz_time = self.trading_tz.localize(day1)
        
        snapshot1 = PortfolioSnapshot(
            positions=[self.test_position],
            timestamp=trading_tz_time
        )
        self.repository.save_portfolio_snapshot(snapshot1)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 1)
        
        # Day 2: Update in different timezone but clearly different day
        day2 = datetime(2023, 11, 16, 10, 0, 0)  # Thursday  
        utc_time = pytz.UTC.localize(day2)
        
        updated_position = Position(
            ticker="TEST",
            shares=Decimal("15.0"),  # Different shares
            avg_price=Decimal("5.10"),
            cost_basis=Decimal("76.50"),
            current_price=Decimal("5.80"),
            market_value=Decimal("87.00"),
            unrealized_pnl=Decimal("10.50"),
            company="Test Company Inc.",
            currency="USD"
        )
        
        snapshot2 = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=utc_time
        )
        self.repository.update_daily_portfolio_snapshot(snapshot2)
        
        # Should now have 2 rows (different days)
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, 2, "Different days should create new rows")
        
        # Verify both days are present with correct data
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        shares_values = df['Shares'].tolist()
        self.assertIn(10.0, shares_values)  # Day 1
        self.assertIn(15.0, shares_values)  # Day 2
    
    def test_dst_transition_handling(self):
        """Test that DST transitions don't cause date comparison issues."""
        # Spring forward: 2 AM becomes 3 AM (PDT starts)
        # Use dates around DST transition in 2024
        before_dst = datetime(2024, 3, 9, 10, 0, 0)  # Day before spring forward
        after_dst = datetime(2024, 3, 11, 10, 0, 0)   # Day after spring forward
        
        # Create timezone-aware timestamps
        pst_tz = pytz.timezone('US/Pacific')
        before_dst_tz = pst_tz.localize(before_dst)
        after_dst_tz = pst_tz.localize(after_dst)
        
        # Save snapshot before DST
        snapshot1 = PortfolioSnapshot(
            positions=[self.test_position],
            timestamp=before_dst_tz
        )
        self.repository.save_portfolio_snapshot(snapshot1)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 1)
        
        # Save snapshot after DST (different day)
        updated_position = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("5.00"),
            cost_basis=Decimal("50.00"),
            current_price=Decimal("5.30"),
            market_value=Decimal("53.00"),
            unrealized_pnl=Decimal("3.00"),
            company="Test Company Inc.",
            currency="USD"
        )
        
        snapshot2 = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=after_dst_tz
        )
        self.repository.update_daily_portfolio_snapshot(snapshot2)
        
        # Should have 2 rows (different days, even across DST)
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, 2, "DST transition should not prevent proper day tracking")
    
    def test_midnight_boundary_handling(self):
        """Test timezone normalization around midnight boundaries."""
        # Create timestamps around midnight in different timezones
        # This tests edge cases where timezone conversion might change the date
        
        # 11:30 PM PST on Nov 15
        late_night_pst = self.trading_tz.localize(datetime(2023, 11, 15, 23, 30, 0))
        # Convert to UTC (7:30 AM Nov 16 UTC)  
        late_night_utc = late_night_pst.astimezone(pytz.UTC)
        
        # Save with PST timestamp
        snapshot1 = PortfolioSnapshot(
            positions=[self.test_position],
            timestamp=late_night_pst
        )
        self.repository.save_portfolio_snapshot(snapshot1)
        
        initial_count = self._get_csv_row_count()
        self.assertEqual(initial_count, 1)
        
        # Update with equivalent UTC timestamp (same moment, different timezone)
        updated_position = Position(
            ticker="TEST",
            shares=Decimal("10.0"),
            avg_price=Decimal("5.00"),
            cost_basis=Decimal("50.00"),
            current_price=Decimal("5.15"),  # Price change
            market_value=Decimal("51.50"),
            unrealized_pnl=Decimal("1.50"),
            company="Test Company Inc.",
            currency="USD"
        )
        
        snapshot2 = PortfolioSnapshot(
            positions=[updated_position],
            timestamp=late_night_utc
        )
        self.repository.update_daily_portfolio_snapshot(snapshot2)
        
        # Should still be 1 row (same moment, normalized to same trading day)
        final_count = self._get_csv_row_count()
        self.assertEqual(final_count, initial_count,
                        "Midnight boundary crossing should be handled by timezone normalization")
        
        # Verify price was updated
        csv_file = self.test_dir / "llm_portfolio_update.csv"
        df = pd.read_csv(csv_file)
        current_price = float(df['Current Price'].iloc[0])
        self.assertAlmostEqual(current_price, 5.15, places=2)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)